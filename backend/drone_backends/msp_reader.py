"""
Betaflight / Cleanflight MSP reader.

Implements a minimal subset of the MultiWii Serial Protocol v1 to read
hardware configuration from Betaflight flight controllers over USB serial.

MSP commands used
-----------------
  MSP_API_VERSION   (1)  — firmware version
  MSP_FC_VARIANT    (2)  — "BTFL", "CLFL", etc.
  MSP_FC_VERSION    (3)  — major.minor.patch
  MSP_BOARD_INFO    (4)  — board name
  MSP_STATUS_EX    (150) — cycle time, features, arming flags
  MSP_RAW_IMU      (102) — raw acc/gyro/mag counts
  MSP_MOTOR_CONFIG (192) — motor poles, min/max throttle
  MSP_FEATURE_CONFIG (36)— enabled features bitmask
"""

from __future__ import annotations

import struct
import time
from typing import Any

# IMU profiles for common Betaflight IMU chips
_IMU_PROFILES: dict[str, tuple[float, float, float, float]] = {
    "MPU-6000": (2.0e-3, 1.7e-4, 1.5e-4, 4.0e-6),
    "MPU-6500": (1.8e-3, 1.4e-4, 1.2e-4, 3.5e-6),
    "ICM-20601": (1.5e-3, 1.0e-4, 1.2e-4, 3.0e-6),
    "ICM-20689": (1.4e-3, 8.7e-5, 1.0e-4, 2.2e-6),
    "BMI270":   (7.0e-4, 6.5e-5, 6.0e-5, 1.9e-6),
    "BMI160":   (1.2e-3, 9.0e-5, 1.0e-4, 2.8e-6),
    "DEFAULT":  (1.6e-3, 1.2e-4, 1.2e-4, 3.0e-6),
}

# Known boards and their primary IMU
_BOARD_IMU: dict[str, str] = {
    "KAKUTEF7":  "ICM-20689",
    "KAKUTEF4":  "MPU-6000",
    "MATEKF722": "MPU-6000",
    "MATEKF405": "ICM-20689",
    "OMNIBUSF4": "MPU-6000",
    "CRAZYBEEF4": "MPU-6000",
    "HOLYBRO":   "ICM-42688",
}

MSP_API_VERSION    = 1
MSP_FC_VARIANT     = 2
MSP_FC_VERSION     = 3
MSP_BOARD_INFO     = 4
MSP_STATUS_EX      = 150
MSP_RAW_IMU        = 102
MSP_MOTOR_CONFIG   = 192
MSP_FEATURE_CONFIG = 36


class MSPReader:
    """Synchronous Betaflight MSP reader — run in a thread pool from async code."""

    def __init__(self):
        self._serial = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, port: str, baudrate: int = 115200,
                timeout: float = 3.0) -> dict[str, Any]:
        try:
            import serial
        except ImportError:
            return {"ok": False, "error": "pyserial not installed — run: pip install pyserial"}
        try:
            self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            time.sleep(0.5)          # let FC settle after DTR reset
            # Probe with API version request
            resp = self._request(MSP_API_VERSION)
            if resp is None:
                self._serial.close()
                self._serial = None
                return {"ok": False, "error": "No response — check port and board power"}
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ── Read ──────────────────────────────────────────────────────────────────

    def read_parameters(self) -> dict[str, Any]:
        if not self.connected:
            return {"ok": False, "error": "Not connected"}
        try:
            fc_variant = self._read_fc_variant()
            board_name = self._read_board_info()
            fc_version = self._read_fc_version()
            motor_cfg   = self._read_motor_config()
            features    = self._read_features()

            imu_key = _BOARD_IMU.get(board_name.upper(), "DEFAULT")
            imu_noise = _IMU_PROFILES[imu_key]

            profile = {
                "board_type": "betaflight",
                "firmware": {
                    "variant": fc_variant,
                    "version": fc_version,
                    "board":   board_name,
                },
                "imu": {
                    "sensor":             imu_key,
                    "acc_noise_density":  imu_noise[0],
                    "gyro_noise_density": imu_noise[1],
                    "acc_random_walk":    imu_noise[2],
                    "gyro_random_walk":   imu_noise[3],
                    "rate_hz":            8000 if features.get("gyro_32khz") else 1000,
                },
                "vehicle": {
                    "frame_type":  "QUAD_X",
                    "motor_count": 4,
                    "motor_poles": motor_cfg.get("motor_poles", 14),
                    "min_throttle": motor_cfg.get("min_throttle", 1070),
                    "max_throttle": motor_cfg.get("max_throttle", 2000),
                },
                "battery": {
                    "cells": features.get("battery_cells", 4),
                },
            }
            return {"ok": True, "profile": profile}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── MSP protocol helpers ──────────────────────────────────────────────────

    def _request(self, cmd: int, data: bytes = b"") -> bytes | None:
        """Send an MSP request and return the response payload, or None on timeout."""
        pkt = self._build_request(cmd, data)
        self._serial.write(pkt)
        return self._read_response(cmd)

    @staticmethod
    def _build_request(cmd: int, data: bytes = b"") -> bytes:
        size = len(data)
        chk = size ^ cmd
        for b in data:
            chk ^= b
        return b"$M<" + bytes([size, cmd]) + data + bytes([chk])

    def _read_response(self, expected_cmd: int, timeout: float = 1.0) -> bytes | None:
        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            byte = self._serial.read(1)
            if not byte:
                continue
            buf += byte
            # Look for header
            if len(buf) >= 3 and buf[-3:] == b"$M>":
                # Read: size, cmd, [data], checksum
                header = self._serial.read(2)
                if len(header) < 2:
                    continue
                size, cmd = header[0], header[1]
                payload = self._serial.read(size) if size else b""
                chk_byte = self._serial.read(1)
                if len(chk_byte) < 1:
                    continue
                # Validate checksum
                chk = size ^ cmd
                for b in payload:
                    chk ^= b
                if chk != chk_byte[0]:
                    continue
                if cmd == expected_cmd:
                    return payload
                buf = b""
        return None

    def _read_fc_variant(self) -> str:
        resp = self._request(MSP_FC_VARIANT)
        if resp and len(resp) >= 4:
            return resp[:4].decode("ascii", errors="replace")
        return "BTFL"

    def _read_fc_version(self) -> str:
        resp = self._request(MSP_FC_VERSION)
        if resp and len(resp) >= 3:
            return f"{resp[0]}.{resp[1]}.{resp[2]}"
        return "unknown"

    def _read_board_info(self) -> str:
        resp = self._request(MSP_BOARD_INFO)
        if resp and len(resp) >= 4:
            return resp[:4].decode("ascii", errors="replace").rstrip("\x00")
        return "UNKN"

    def _read_motor_config(self) -> dict:
        resp = self._request(MSP_MOTOR_CONFIG)
        if resp and len(resp) >= 6:
            min_t, max_t = struct.unpack_from("<HH", resp, 0)
            poles = resp[4] if len(resp) > 4 else 14
            return {"min_throttle": min_t, "max_throttle": max_t, "motor_poles": poles}
        return {"min_throttle": 1070, "max_throttle": 2000, "motor_poles": 14}

    def _read_features(self) -> dict:
        resp = self._request(MSP_FEATURE_CONFIG)
        if resp and len(resp) >= 4:
            mask = struct.unpack_from("<I", resp, 0)[0]
            return {
                "motor_stop":     bool(mask & (1 << 4)),
                "gyro_32khz":     bool(mask & (1 << 27)),
                "battery_cells":  4,       # not exposed via MSP, assume 4S
            }
        return {"battery_cells": 4}
