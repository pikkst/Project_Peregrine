"""
Update ros2_ws/src/peregrine_launch/config/vio_config.yaml with IMU and
camera parameters extracted from the drone hardware profile.

Fields updated
--------------
  imu.acc_noise_density
  imu.gyro_noise_density
  imu.acc_random_walk
  imu.gyro_random_walk
  imu.rate
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

_DEFAULT_VIO: dict = {
    "camera": {
        "type": "pinhole",
        "width": 640,
        "height": 480,
        "fx": 320.0,
        "fy": 320.0,
        "cx": 320.0,
        "cy": 240.0,
        "k1": 0.0,
        "k2": 0.0,
        "p1": 0.0,
        "p2": 0.0,
        "baseline_m": 0.12,
    },
    "imu": {
        "rate": 200.0,
        "acc_noise_density":  1.4e-3,
        "gyro_noise_density": 8.7e-5,
        "acc_random_walk":    1.0e-4,
        "gyro_random_walk":   2.2e-6,
    },
    "vio": {
        "max_features":       200,
        "min_features":       60,
        "keyframe_frequency": 2.0,
    },
}


def apply_to_vio(profile: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """
    Merge IMU (and optional camera) parameters into vio_config.yaml.
    Returns {"ok": True} or {"ok": False, "error": str}.
    """
    if yaml is None:
        return {"ok": False, "error": "pyyaml not installed — run: pip install pyyaml"}

    try:
        if config_path.exists():
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
        else:
            import copy
            cfg = copy.deepcopy(_DEFAULT_VIO)

        imu = profile.get("imu", {})

        cfg.setdefault("imu", {})
        cfg["imu"]["acc_noise_density"]  = imu.get("acc_noise_density",  1.4e-3)
        cfg["imu"]["gyro_noise_density"] = imu.get("gyro_noise_density", 8.7e-5)
        cfg["imu"]["acc_random_walk"]    = imu.get("acc_random_walk",    1.0e-4)
        cfg["imu"]["gyro_random_walk"]   = imu.get("gyro_random_walk",   2.2e-6)
        cfg["imu"]["rate"]               = float(imu.get("rate_hz", 200))
        cfg["imu"]["_sensor"]            = imu.get("sensor", "unknown")

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

        return {"ok": True, "path": str(config_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
