"""
Peregrine Telemetry Bridge
==========================
ROS 2 node that subscribes to /odometry/filtered and writes the latest pose
as a JSON file that the FastAPI backend can read directly.

Designed to run inside WSL2 alongside the ROS 2 stack.

Usage (WSL2)
------------
  source /opt/ros/humble/setup.bash
  source /mnt/c/Users/PC/Desktop/Project_Peregrine/ros2_ws/install/setup.bash
  python3 /mnt/c/Users/PC/Desktop/Project_Peregrine/backend/ros2_bridge/telemetry_bridge.py

Output file
-----------
  Written to:  <project_root>/backend/tmp/telemetry.json
  Content:     {"x": 1.2, "y": 0.3, "z": -1.9,
                "vx": 0.0, "vy": 0.0, "vz": 0.0,
                "yaw": 45.0, "wp_idx": 0, "mission_running": false,
                "ts": 1234567890.123}

The backend reads this file in its telemetry loop. If the file is absent or
its timestamp is more than 2 seconds old, the backend falls back to mock data.
"""

import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────────────────────
# Works whether launched from Windows (C:\ path) or WSL2 (/mnt/c/... path).
_THIS_DIR    = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent
_OUT_DIR      = _PROJECT_ROOT / "backend" / "tmp"

# ── ROS 2 availability check ──────────────────────────────────────────────────
try:
    import rclpy
    from rclpy.node import Node
    from nav_msgs.msg import Odometry
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False


def _quat_to_yaw(qx: float, qy: float, qz: float, qw: float) -> float:
    """Convert quaternion to yaw angle in degrees (rotation around Z)."""
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


class TelemetryBridgeNode(Node):
    def __init__(self, out_file: Path):
        super().__init__("telemetry_bridge")
        self._out_file = out_file
        self._out_file.parent.mkdir(parents=True, exist_ok=True)

        self._sub = self.create_subscription(
            Odometry,
            "/odometry/filtered",
            self._odom_cb,
            10,
        )
        self.get_logger().info(
            f"Telemetry bridge started — writing to {self._out_file}")

    def _odom_cb(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        v = msg.twist.twist.linear
        o = msg.pose.pose.orientation
        payload = {
            "x":   round(p.x, 4),
            "y":   round(p.y, 4),
            "z":   round(p.z, 4),
            "vx":  round(v.x, 4),
            "vy":  round(v.y, 4),
            "vz":  round(v.z, 4),
            "yaw": round(_quat_to_yaw(o.x, o.y, o.z, o.w), 2),
            "wp_idx": 0,              # updated by mission_agent separately
            "mission_running": False,  # updated by mission_agent separately
            "ts":  time.time(),
        }
        # Atomic write: write to temp then rename to avoid partial reads.
        tmp = self._out_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(self._out_file)


def main() -> None:
    out_file = _OUT_DIR / "telemetry.json"

    if not _ROS2_AVAILABLE:
        print("ERROR: rclpy not available. Source ROS 2 before running this script.",
              file=sys.stderr)
        sys.exit(1)

    rclpy.init()
    node = TelemetryBridgeNode(out_file)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
