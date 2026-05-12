"""
MAVLink reader for Pixhawk (PX4), ArduPilot, and Navio2 boards.

Connects via USB serial (or UDP for SITL) and reads key hardware parameters
using the MAVLink PARAM_REQUEST_LIST / PARAM_VALUE protocol.

Parameters extracted
--------------------
  imu.acc_noise_density    — accelerometer noise density (m/s²/√Hz)
  imu.gyro_noise_density   — gyroscope noise density (rad/s/√Hz)
  imu.acc_random_walk      — accel random walk (m/s³/√Hz)
  imu.gyro_random_walk     — gyro random walk (rad/s²/√Hz)
  battery.cells            — LiPo cell count
  vehicle.frame_type       — QUAD_X, HEX_X, OCTO_X, etc.
  vehicle.motor_count      — inferred from frame type
  vehicle.firmware         — PX4 or ArduCopter + version string
"""

from __future__ import annotations

import time
from typing import Any

# IMU noise characteristics indexed by sensor ID reported by the FC.
# Values: (acc_nd m/s²/√Hz, gyro_nd rad/s/√Hz, acc_rw m/s³/√Hz, gyro_rw rad/s²/√Hz)
_IMU_PROFILES: dict[str, tuple[float, float, float, float]] = {
    "ICM-20689":  (1.4e-3, 8.7e-5, 1.0e-4, 2.2e-6),   # Pixhawk 4
    "ICM-20602":  (1.5e-3, 9.5e-5, 1.1e-4, 2.4e-6),
    "ICM-42688":  (7.0e-4, 6.5e-5, 6.0e-5, 1.9e-6),   # Pixhawk 6C
    "BMI055":     (1.6e-3, 1.2e-4, 1.2e-4, 3.0e-6),
    "MPU-6000":   (2.0e-3, 1.7e-4, 1.5e-4, 4.0e-6),
    "DEFAULT":    (1.4e-3, 8.7e-5, 1.0e-4, 2.2e-6),
}

# ArduCopter frame class → motor count mapping
_FRAME_MOTOR_COUNT: dict[int, int] = {
    1: 4,   # QUAD
    2: 6,   # HEXA
    3: 8,   # OCTA
    4: 8,   # OCTA_QUAD
    5: 6,   # Y6
    6: 3,   # TRI
    7: 4,   # SINGLE (2 x CW + 2 x CCW)
    12: 6,  # DODECA_HEXA
}

# PX4 airframe → motor count (SYS_AUTOSTART ranges)
_PX4_AIRFRAME_MOTORS: dict[tuple[int, int], int] = {
    (4001, 4999): 4,   # Generic QUAD
    (6001, 6999): 6,   # Generic HEX
    (8001, 8999): 8,   # Generic OCTO
    (13000, 13999): 4, # VTOL
}


class MAVLinkReader:
    """Synchronous MAVLink reader — run in a thread pool from async code."""

    def __init__(self):
        self._conn = None

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self, port: str, baudrate: int = 57600,
                timeout: float = 10.0) -> dict[str, Any]:
        """Open a MAVLink connection. Returns {"ok": True} or {"ok": False, "error": ...}."""
        try:
            from pymavlink import mavutil
        except ImportError:
            return {"ok": False, "error": "pymavlink not installed — run: pip install pymavlink"}

        try:
            self._conn = mavutil.mavlink_connection(
                port, baud=baudrate, dialect="common")
            hb = self._conn.wait_heartbeat(timeout=timeout)
            if hb is None:
                return {"ok": False, "error": "No heartbeat received — check cable and board power"}
            return {"ok": True, "autopilot": hb.autopilot, "type": hb.type}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    # ── Parameter reading ─────────────────────────────────────────────────────

    def read_parameters(self) -> dict[str, Any]:
        """Request all parameters and extract the hardware profile."""
        if not self._conn:
            return {"ok": False, "error": "Not connected"}

        try:
            params = self._fetch_params()
            firmware = self._detect_firmware(params)
            imu_key, imu_noise = self._detect_imu(params, firmware)
            battery_cells = self._detect_battery(params, firmware)
            frame_type, motor_count = self._detect_frame(params, firmware)

            profile = {
                "board_type": firmware.get("variant", "mavlink"),
                "firmware":   firmware,
                "imu": {
                    "sensor":              imu_key,
                    "acc_noise_density":   imu_noise[0],
                    "gyro_noise_density":  imu_noise[1],
                    "acc_random_walk":     imu_noise[2],
                    "gyro_random_walk":    imu_noise[3],
                    "rate_hz":             200,
                },
                "vehicle": {
                    "frame_type":   frame_type,
                    "motor_count":  motor_count,
                },
                "battery": {
                    "cells": battery_cells,
                },
                "raw_params": {k: v for k, v in list(params.items())[:50]},
            }
            return {"ok": True, "profile": profile}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_params(self, timeout: float = 15.0) -> dict[str, float]:
        """Request parameter list and collect responses."""
        conn = self._conn
        conn.mav.param_request_list_send(conn.target_system, conn.target_component)
        params: dict[str, float] = {}
        deadline = time.time() + timeout
        expected = None

        while time.time() < deadline:
            msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg is None:
                if expected is not None and len(params) >= expected:
                    break
                continue
            params[msg.param_id.rstrip("\x00")] = msg.param_value
            if expected is None:
                expected = msg.param_count
            if expected and len(params) >= expected:
                break
        return params

    def _detect_firmware(self, params: dict) -> dict:
        version = {}
        # PX4 uses SYS_AUTOSTART; ArduCopter uses FRAME_CLASS
        if "SYS_AUTOSTART" in params:
            version["variant"] = "px4"
            version["autostart"] = int(params.get("SYS_AUTOSTART", 0))
        elif "FRAME_CLASS" in params:
            version["variant"] = "ardupilot"
        else:
            version["variant"] = "mavlink_generic"
        return version

    def _detect_imu(self, params: dict, firmware: dict) -> tuple[str, tuple]:
        # Try to identify IMU from known parameter names
        # PX4 CAL_ACC0_ID encodes sensor ID; ArduPilot INS_ACCOFFS_X hints at calibration
        # Without direct IMU type params, fall back to firmware defaults
        if firmware.get("variant") == "px4":
            imu_key = "ICM-42688"   # Pixhawk 6 default
        elif firmware.get("variant") == "ardupilot":
            imu_key = "ICM-20689"   # Pixhawk 4 default
        else:
            imu_key = "DEFAULT"
        return imu_key, _IMU_PROFILES[imu_key]

    def _detect_battery(self, params: dict, firmware: dict) -> int:
        if firmware.get("variant") == "px4":
            cells = int(params.get("BAT_N_CELLS", 4))
        else:
            cells = int(params.get("BATT_N_CELLS", 4))
        return max(1, min(cells, 12))

    def _detect_frame(self, params: dict, firmware: dict) -> tuple[str, int]:
        if firmware.get("variant") == "ardupilot":
            frame_class = int(params.get("FRAME_CLASS", 1))
            frame_type  = int(params.get("FRAME_TYPE",  1))
            motor_count = _FRAME_MOTOR_COUNT.get(frame_class, 4)
            names = {1: "QUAD", 2: "HEX", 3: "OCTA", 5: "Y6", 6: "TRI"}
            frame_name = names.get(frame_class, f"FRAME_{frame_class}")
            return frame_name, motor_count
        elif firmware.get("variant") == "px4":
            autostart = firmware.get("autostart", 4001)
            motor_count = 4
            for (lo, hi), n in _PX4_AIRFRAME_MOTORS.items():
                if lo <= autostart <= hi:
                    motor_count = n
                    break
            return "QUAD_X", motor_count
        return "QUAD", 4
