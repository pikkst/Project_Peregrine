"""
Update ros2_ws/src/fusion/ekf_config.yaml with IMU noise parameters
extracted from the drone hardware profile.

Fields updated
--------------
  process_noise_covariance    — diagonal [x,y,z, roll,pitch,yaw, vx,vy,vz, ...]
  imu0_config                 — topic and configuration flags
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

# Default EKF config used when the file doesn't yet exist.
_DEFAULT_EKF: dict = {
    "ekf_filter_node": {
        "ros__parameters": {
            "frequency": 30.0,
            "sensor_timeout": 0.1,
            "two_d_mode": False,
            "publish_tf": True,
            "map_frame": "map",
            "odom_frame": "odom",
            "base_link_frame": "base_link",
            "world_frame": "odom",
            "odom0": "/vio/odom",
            "odom0_config": [True,  True,  True,
                             False, False, False,
                             True,  True,  True,
                             False, False, False,
                             False, False, False],
            "pose0": "/localization/landmark_fix",
            "pose0_config": [True, True, True,
                             True, True, True,
                             False, False, False,
                             False, False, False,
                             False, False, False],
            "imu0": "/airsim/imu",
            "imu0_config": [False, False, False,
                            True,  True,  True,
                            False, False, False,
                            True,  True,  True,
                            True,  True,  True],
            "imu0_remove_gravitational_acceleration": True,
        }
    }
}


def apply_to_ekf(profile: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """
    Merge IMU noise parameters from a drone profile into ekf_config.yaml.
    Returns {"ok": True} or {"ok": False, "error": str}.
    """
    if yaml is None:
        return {"ok": False, "error": "pyyaml not installed — run: pip install pyyaml"}

    try:
        if config_path.exists():
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
        else:
            cfg = copy.deepcopy(_DEFAULT_EKF)

        imu = profile.get("imu", {})
        acc_nd  = imu.get("acc_noise_density",  1.4e-3)
        gyro_nd = imu.get("gyro_noise_density", 8.7e-5)
        acc_rw  = imu.get("acc_random_walk",    1.0e-4)
        gyro_rw = imu.get("gyro_random_walk",   2.2e-6)

        # Derive EKF process noise covariance diagonal from sensor noise specs.
        # The covariance is a 15-element flat array (x,y,z, r,p,y, vx,vy,vz,
        # vrx,vry,vrz, ax,ay,az) ordered as in robot_localization.
        pos_var = (acc_nd * 10) ** 2      # approximate position drift
        rot_var = (gyro_nd * 10) ** 2     # approximate orientation drift
        vel_var = acc_nd ** 2
        acc_var = acc_rw ** 2

        pnc = [
            pos_var, pos_var, pos_var,
            rot_var, rot_var, rot_var,
            vel_var, vel_var, vel_var,
            gyro_rw**2, gyro_rw**2, gyro_rw**2,
            acc_var,    acc_var,    acc_var,
        ]

        # Navigate into the YAML structure (handles both flat and nested forms)
        params_node = _find_ros_params(cfg)
        if params_node is not None:
            params_node["process_noise_covariance"] = pnc
            params_node["_peregrine_imu_sensor"] = imu.get("sensor", "unknown")
        else:
            cfg["process_noise_covariance"] = pnc

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

        return {"ok": True, "path": str(config_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _find_ros_params(cfg: dict) -> dict | None:
    """Return the ros__parameters node regardless of top-level node name."""
    for v in cfg.values():
        if isinstance(v, dict) and "ros__parameters" in v:
            return v["ros__parameters"]
    return None
