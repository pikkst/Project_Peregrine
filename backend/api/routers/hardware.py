"""
Hardware profile router — connect real drone boards, read parameters,
and apply them to simulation and ROS2 configs.

Supported boards
----------------
  MAVLink  — Pixhawk, PX4, ArduPilot, Navio2 (via pymavlink)
  MSP      — Betaflight / Cleanflight (Kakute, Matek, Holybro, …)
  Jetson   — NVIDIA Jetson Orin / AGX (via SSH / paramiko)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter
from pydantic import BaseModel
from state import state, add_log, PROJECT_ROOT
from ws_manager import log_manager

router = APIRouter()

# ── Paths ─────────────────────────────────────────────────────────────────────

_PROFILES_DIR = PROJECT_ROOT / "backend" / "hardware_profiles"

_AIRSIM_SETTINGS = PROJECT_ROOT / "unreal" / "AirSim" / "settings.json"
_EKF_CONFIG      = (PROJECT_ROOT / "ros2_ws" / "src" / "fusion" /
                    "ekf_config.yaml")
_VIO_CONFIG      = (PROJECT_ROOT / "ros2_ws" / "src" / "peregrine_launch" /
                    "config" / "vio_config.yaml")

# ── Supported board catalogue ─────────────────────────────────────────────────

BOARD_TYPES: list[dict] = [
    # MAVLink family
    {"id": "pixhawk",   "label": "Pixhawk / PX4",      "proto": "mavlink",  "default_baud": 57600},
    {"id": "ardupilot", "label": "ArduPilot",           "proto": "mavlink",  "default_baud": 57600},
    {"id": "navio2",    "label": "Navio2 (RPi)",        "proto": "mavlink",  "default_baud": 921600},
    # MSP family
    {"id": "betaflight","label": "Betaflight",          "proto": "msp",      "default_baud": 115200},
    {"id": "cleanflight","label": "Cleanflight",        "proto": "msp",      "default_baud": 115200},
    # Jetson
    {"id": "jetson",    "label": "NVIDIA Jetson",       "proto": "ssh",      "default_baud": None},
]

# ── Pydantic request models ───────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    board_type: str
    # Serial (MAVLink / MSP)
    port:     Optional[str] = None
    baudrate: Optional[int] = None
    # SSH (Jetson)
    host:     Optional[str] = None
    username: Optional[str] = "jetson"
    password: Optional[str] = None
    key_path: Optional[str] = None
    ssh_port: Optional[int] = 22

class SaveProfileRequest(BaseModel):
    name: str


# ── Helper: _reader() ─────────────────────────────────────────────────────────

def _get_reader():
    """Return the cached reader object stored in state, or None."""
    return state.get("_hardware_reader")


def _set_reader(reader):
    state["_hardware_reader"] = reader


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/board-types")
async def list_board_types():
    """Return all supported board types."""
    return {"boards": BOARD_TYPES}


@router.get("/ports")
async def list_ports():
    """List available serial ports (cross-platform)."""
    try:
        import serial.tools.list_ports
        ports = [
            {"port": p.device, "description": p.description or ""}
            for p in serial.tools.list_ports.comports()
        ]
        return {"ok": True, "ports": ports}
    except ImportError:
        return {"ok": False, "error": "pyserial not installed — run: pip install pyserial",
                "ports": []}
    except Exception as e:
        return {"ok": False, "error": str(e), "ports": []}


@router.get("/status")
async def hardware_status():
    """Return current connection state and active profile summary."""
    hw_status = state.get("hardware_status", "disconnected")
    cfg = state.get("hardware_config", {})
    summary: dict[str, Any] = {"status": hw_status}

    if cfg:
        summary["board_type"] = cfg.get("board_type", "unknown")
        imu = cfg.get("imu", {})
        summary["imu_sensor"] = imu.get("sensor", "unknown")
        summary["firmware"]   = cfg.get("firmware", {})
        summary["vehicle"]    = cfg.get("vehicle", {})

    return summary


@router.post("/connect")
async def connect_board(req: ConnectRequest):
    """Connect to a drone board.  Stores the reader in state."""
    # Disconnect any existing reader first
    await _do_disconnect(silent=True)

    loop = asyncio.get_running_loop()
    proto = next((b["proto"] for b in BOARD_TYPES if b["id"] == req.board_type), None)
    if proto is None:
        return {"ok": False, "error": f"Unknown board type: {req.board_type}"}

    try:
        if proto == "mavlink":
            if not req.port:
                return {"ok": False, "error": "port is required for MAVLink boards"}
            from drone_backends.mavlink_reader import MAVLinkReader
            reader = MAVLinkReader()
            result = await loop.run_in_executor(
                None,
                lambda: reader.connect(
                    req.port,
                    baudrate=req.baudrate or 57600,
                ),
            )

        elif proto == "msp":
            if not req.port:
                return {"ok": False, "error": "port is required for MSP boards"}
            from drone_backends.msp_reader import MSPReader
            reader = MSPReader()
            result = await loop.run_in_executor(
                None,
                lambda: reader.connect(
                    req.port,
                    baudrate=req.baudrate or 115200,
                ),
            )

        elif proto == "ssh":
            if not req.host:
                return {"ok": False, "error": "host is required for Jetson boards"}
            from drone_backends.jetson_reader import JetsonReader
            reader = JetsonReader()
            result = await loop.run_in_executor(
                None,
                lambda: reader.connect(
                    host=req.host,
                    username=req.username or "jetson",
                    password=req.password or None,
                    key_path=req.key_path or None,
                    port=req.ssh_port or 22,
                ),
            )
        else:
            return {"ok": False, "error": f"Unsupported protocol: {proto}"}

        if not result.get("ok"):
            return result

        _set_reader(reader)
        state["hardware_status"] = "connected"
        state["_hardware_board_type"] = req.board_type

        entry = add_log("hardware", f"Connected to {req.board_type}")
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": True, "board_type": req.board_type}

    except Exception as e:
        state["hardware_status"] = "disconnected"
        return {"ok": False, "error": str(e)}


@router.post("/disconnect")
async def disconnect_board():
    result = await _do_disconnect(silent=False)
    return result


async def _do_disconnect(silent: bool = False) -> dict:
    reader = _get_reader()
    if reader is None:
        if silent:
            return {"ok": True}
        return {"ok": False, "error": "Not connected"}

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, reader.disconnect)
    except Exception:
        pass

    _set_reader(None)
    state["hardware_status"] = "disconnected"
    state.pop("_hardware_board_type", None)

    if not silent:
        entry = add_log("hardware", "Disconnected from board")
        await log_manager.broadcast(json.dumps(entry))

    return {"ok": True}


@router.post("/read")
async def read_parameters():
    """Read hardware parameters from the connected board."""
    reader = _get_reader()
    if reader is None:
        return {"ok": False, "error": "Not connected — call /connect first"}

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, reader.read_parameters)
        if result.get("ok"):
            state["hardware_config"]  = result["profile"]
            state["hardware_status"]  = "ready"
            entry = add_log("hardware", "Parameters read successfully")
            await log_manager.broadcast(json.dumps(entry))
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/apply")
async def apply_parameters():
    """Apply the active hardware profile to AirSim, EKF, and VIO configs."""
    profile = state.get("hardware_config")
    if not profile:
        return {"ok": False, "error": "No profile loaded — call /read first"}

    from config_writers import apply_to_airsim, apply_to_ekf, apply_to_vio

    results: dict[str, Any] = {}
    loop = asyncio.get_running_loop()

    r = await loop.run_in_executor(
        None, lambda: apply_to_airsim(profile, _AIRSIM_SETTINGS))
    results["airsim"] = r

    r = await loop.run_in_executor(
        None, lambda: apply_to_ekf(profile, _EKF_CONFIG))
    results["ekf"] = r

    r = await loop.run_in_executor(
        None, lambda: apply_to_vio(profile, _VIO_CONFIG))
    results["vio"] = r

    all_ok = all(v.get("ok") for v in results.values())
    msg = "All configs updated" if all_ok else "Some configs failed — check results"
    entry = add_log("hardware", msg)
    await log_manager.broadcast(json.dumps(entry))

    return {"ok": all_ok, "results": results}


# ── Saved profiles ────────────────────────────────────────────────────────────

@router.get("/profiles")
async def list_profiles():
    """List all saved hardware profiles."""
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = [
        {"name": p.stem, "path": str(p)}
        for p in sorted(_PROFILES_DIR.glob("*.json"))
    ]
    return {"ok": True, "profiles": profiles}


@router.post("/profiles")
async def save_profile(req: SaveProfileRequest):
    """Save the active hardware profile under the given name."""
    profile = state.get("hardware_config")
    if not profile:
        return {"ok": False, "error": "No active profile to save"}

    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in req.name if c.isalnum() or c in "-_ ")
    path = _PROFILES_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(profile, indent=2))

    entry = add_log("hardware", f"Profile saved: {safe_name}")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True, "name": safe_name}


@router.post("/profiles/{name}/load")
async def load_profile(name: str):
    """Load a saved profile into the active hardware config."""
    path = _PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return {"ok": False, "error": f"Profile not found: {name}"}
    try:
        profile = json.loads(path.read_text())
        state["hardware_config"] = profile
        state["hardware_status"] = "ready"
        entry = add_log("hardware", f"Profile loaded: {name}")
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": True, "profile": profile}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.delete("/profiles/{name}")
async def delete_profile(name: str):
    """Delete a saved profile."""
    path = _PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return {"ok": False, "error": f"Profile not found: {name}"}
    path.unlink()
    return {"ok": True}
