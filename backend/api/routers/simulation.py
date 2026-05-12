"""
Simulation router — start/stop Unreal+AirSim and manage settings.

Launch order:
  1. If user set a custom exe/bat path via POST /sim-path → use that directly.
  2. Otherwise try the project's scripts/run_unreal_sim.bat.

Status tracking: bat files spawn Unreal detached and exit immediately, so we
check running state via Windows tasklist (process name), not the subprocess handle.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter
from state import state, add_log, PROJECT_ROOT
from ws_manager import log_manager

router = APIRouter()

UNREAL_BAT      = PROJECT_ROOT / "scripts" / "run_unreal_sim.bat"
AIRSIM_SETTINGS = PROJECT_ROOT / "unreal" / "AirSim" / "settings.json"
_SIM_CONFIG     = PROJECT_ROOT / "backend" / "sim_config.json"

_UNREAL_PROC_NAMES = {
    "UnrealEditor.exe", "UnrealEditor-Win64-Shipping.exe",
    "AirSimExe.exe", "UE4Editor.exe",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_sim_config() -> dict:
    try:
        return json.loads(_SIM_CONFIG.read_text()) if _SIM_CONFIG.exists() else {}
    except Exception:
        return {}


def _save_sim_config(cfg: dict) -> None:
    _SIM_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _SIM_CONFIG.write_text(json.dumps(cfg, indent=2))


def _unreal_is_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True, stderr=subprocess.DEVNULL, timeout=3,
        )
        return any(n.lower() in out.lower() for n in _UNREAL_PROC_NAMES)
    except Exception:
        return False


def _get_launch_target() -> tuple[Path | None, str]:
    """
    Return (path, kind) where kind is 'bat' | 'exe' | 'none'.
    Checks user-configured path first, then default bat.
    """
    cfg = _load_sim_config()
    custom = cfg.get("sim_exe_path", "").strip()
    if custom:
        p = Path(custom)
        if p.exists():
            kind = "bat" if p.suffix.lower() == ".bat" else "exe"
            return p, kind
        return None, "missing"

    if UNREAL_BAT.exists():
        return UNREAL_BAT, "bat"
    return None, "none"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/launch-info")
async def get_launch_info():
    """Return setup state: configured path, whether it exists, bat default path."""
    cfg = _load_sim_config()
    custom = cfg.get("sim_exe_path", "").strip()
    target, kind = _get_launch_target()

    # Check default bat's project path too
    unreal_project = (PROJECT_ROOT / "unreal" / "Peregrine.uproject").exists()

    return {
        "ok":             True,
        "custom_path":    custom,
        "target":         str(target) if target else None,
        "target_kind":    kind,
        "default_bat":    str(UNREAL_BAT),
        "default_bat_exists": UNREAL_BAT.exists(),
        "unreal_project_exists": unreal_project,
        "is_configured":  kind in ("bat", "exe"),
    }


@router.post("/sim-path")
async def set_sim_path(body: dict):
    """Save the user-configured launch executable/bat path."""
    path = body.get("path", "").strip()
    cfg = _load_sim_config()
    cfg["sim_exe_path"] = path
    _save_sim_config(cfg)
    return {"ok": True, "path": path}


@router.post("/start")
async def start_simulation():
    if _unreal_is_running():
        return {"ok": False, "error": "Unreal/AirSim is already running"}

    target, kind = _get_launch_target()

    if kind == "missing":
        cfg = _load_sim_config()
        path = cfg.get("sim_exe_path", "")
        return {"ok": False, "error": f"Configured path not found: {path}"}

    if kind == "none":
        return {
            "ok": False,
            "error": (
                "No launch target configured. "
                "Set the path to your AirSim .exe or Unreal .bat in the Simulation page."
            ),
        }

    try:
        if kind == "bat":
            p = subprocess.Popen(
                [str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            try:
                out, _ = p.communicate(timeout=10)
                for line in (out or "").strip().splitlines():
                    entry = add_log("sim", line)
                    await log_manager.broadcast(json.dumps(entry))
            except subprocess.TimeoutExpired:
                pass
        else:
            # Direct .exe launch (AirSim binary, UE packaged game, etc.)
            p = subprocess.Popen(
                [str(target), "-windowed"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

        state["sim_process"] = p

        if _unreal_is_running():
            msg = "Unreal/AirSim launched successfully"
        else:
            msg = "Launch script ran — if Unreal didn't open, check the configured path"
        entry = add_log("sim", msg)
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": True, "pid": p.pid}

    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/stop")
async def stop_simulation():
    try:
        for name in ["UnrealEditor.exe", "AirSimExe.exe",
                     "UnrealEditor-Win64-Shipping.exe"]:
            subprocess.run(
                ["taskkill", "/f", "/im", name],
                check=False, capture_output=True,
            )
    except Exception:
        pass
    state["sim_process"] = None
    entry = add_log("sim", "Stop signal sent to Unreal/AirSim")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True}


@router.get("/status")
async def sim_status():
    running = _unreal_is_running()
    if not running:
        state["sim_process"] = None
    return {"running": running}


@router.get("/settings")
async def get_airsim_settings():
    for candidate in [
        AIRSIM_SETTINGS,
        PROJECT_ROOT / "ros2_ws" / "src" / "sim" / "airsim_settings.json",
    ]:
        if candidate.exists():
            return {"ok": True, "content": candidate.read_text(encoding="utf-8")}
    return {"ok": True, "content": "{\n  \"SettingsVersion\": 1.2,\n  \"SimMode\": \"Multirotor\"\n}"}


@router.post("/settings")
async def save_airsim_settings(body: dict):
    import json as _json
    try:
        content = body.get("content", "")
        _json.loads(content)
        AIRSIM_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        AIRSIM_SETTINGS.write_text(content, encoding="utf-8")
        entry = add_log("sim", "AirSim settings saved")
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
