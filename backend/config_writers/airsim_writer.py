"""
Write drone hardware profile parameters to unreal/AirSim/settings.json.

Fields updated
--------------
  Vehicles.Drone1.MotorDirections    — CW/CCW pattern from frame type
  Vehicles.Drone1.Rotors             — motor count
  SimMode                            — always "Multirotor"
  Comment field added with profile source
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# CW/CCW rotation direction per motor index for common frame types.
# 1 = CW, -1 = CCW viewed from top. Order: front-right, rear-left, front-left, rear-right
_MOTOR_DIRS: dict[str, list[int]] = {
    "QUAD_X":  [1, 1, -1, -1],
    "QUAD_P":  [1, -1, 1, -1],
    "HEX":     [1, -1, 1, -1, 1, -1],
    "OCTO":    [1, -1, 1, -1, 1, -1, 1, -1],
    "DEFAULT": [1, 1, -1, -1],
}

# Default SimpleFlight rotor config for a single motor
_DEFAULT_ROTOR = {
    "ArmLength": 0.2275,
    "MaxRPM": 6396.667,
    "PropDiameter": 0.2286,
    "PropHeight": 0.1,
    "CalculateMax": True,
}


def apply_to_airsim(profile: dict[str, Any], settings_path: Path) -> dict[str, Any]:
    """
    Merge drone profile into AirSim settings.json.
    Creates the file with defaults if it doesn't exist.
    Returns {"ok": True, "path": str} or {"ok": False, "error": str}.
    """
    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
        else:
            settings = _default_settings()

        vehicle   = profile.get("vehicle", {})
        battery   = profile.get("battery", {})
        frame     = vehicle.get("frame_type", "QUAD_X")
        n_motors  = vehicle.get("motor_count", 4)

        # Ensure Multirotor mode
        settings["SimMode"] = "Multirotor"
        settings.setdefault("Vehicles", {})
        settings["Vehicles"].setdefault("Drone1", _default_vehicle())

        drone = settings["Vehicles"]["Drone1"]
        drone["VehicleType"] = "SimpleFlight"

        # Build rotor list
        dirs = _MOTOR_DIRS.get(frame, _MOTOR_DIRS["DEFAULT"])
        if len(dirs) < n_motors:
            dirs = (dirs * (n_motors // len(dirs) + 1))[:n_motors]

        rotors: list[dict] = []
        for i in range(n_motors):
            r = dict(_DEFAULT_ROTOR)
            r["NormalX"] = 0.0
            r["NormalY"] = 0.0
            r["NormalZ"] = -1.0
            r["Direction"] = dirs[i]
            rotors.append(r)
        drone["Rotors"] = rotors

        # Battery cells → nominal voltage (hint only, SimpleFlight ignores it)
        cells = battery.get("cells", 4)
        drone["BatteryCells"] = cells

        # Tag with profile source
        drone["_PeregrineProfile"] = profile.get("firmware", {}).get("board", "unknown")

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2))
        return {"ok": True, "path": str(settings_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _default_settings() -> dict:
    return {
        "SettingsVersion": 1.2,
        "SimMode": "Multirotor",
        "Vehicles": {},
        "CameraDefaults": {
            "CaptureSettings": [{
                "ImageType": 0,
                "Width": 640,
                "Height": 480,
                "FOV_Degrees": 90,
                "MotionBlurAmount": 0,
            }]
        },
    }


def _default_vehicle() -> dict:
    return {
        "VehicleType": "SimpleFlight",
        "X": 0, "Y": 0, "Z": 0,
        "AllowAPIAlways": True,
        "AutoCreate": True,
    }
