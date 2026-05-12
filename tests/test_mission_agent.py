"""
Unit tests for mission agent navigation logic.

Tests compute_velocity() in isolation — no ROS 2 required.
"""

import math
import sys
from pathlib import Path

# Ensure the script is importable without rclpy by importing only
# the pure-Python helpers that live before the Node class.
sys.path.insert(
    0,
    str(Path(__file__).parent.parent
        / "ros2_ws" / "src" / "mission_agent" / "scripts"),
)

import pytest

# Import with rclpy mocked so we can test on Windows / CI without ROS 2.
import types, unittest.mock as mock

_rclpy_mock = types.ModuleType("rclpy")
_rclpy_mock.node = types.ModuleType("rclpy.node")
_rclpy_mock.node.Node = object
_rclpy_mock.init = mock.MagicMock()
_rclpy_mock.spin = mock.MagicMock()
_rclpy_mock.shutdown = mock.MagicMock()

_geometry_msgs = types.ModuleType("geometry_msgs")
_geometry_msgs.msg = types.ModuleType("geometry_msgs.msg")
_geometry_msgs.msg.Twist = mock.MagicMock
_nav_msgs = types.ModuleType("nav_msgs")
_nav_msgs.msg = types.ModuleType("nav_msgs.msg")
_nav_msgs.msg.Odometry = mock.MagicMock

sys.modules.setdefault("rclpy", _rclpy_mock)
sys.modules.setdefault("rclpy.node", _rclpy_mock.node)
sys.modules.setdefault("geometry_msgs", _geometry_msgs)
sys.modules.setdefault("geometry_msgs.msg", _geometry_msgs.msg)
sys.modules.setdefault("nav_msgs", _nav_msgs)
sys.modules.setdefault("nav_msgs.msg", _nav_msgs.msg)

from mission_agent import MAX_SPEED, ARRIVAL_THRESHOLD, compute_velocity


# ── compute_velocity ──────────────────────────────────────────────────────────

def test_proportional_output():
    vx, vy = compute_velocity(1.0, 0.0, gain=0.3)
    assert abs(vx - 0.3) < 1e-9
    assert abs(vy - 0.0) < 1e-9


def test_proportional_diagonal():
    vx, vy = compute_velocity(1.0, 1.0, gain=0.3)
    assert abs(vx - 0.3) < 1e-9
    assert abs(vy - 0.3) < 1e-9


def test_max_speed_clamped():
    """Speed must never exceed MAX_SPEED."""
    vx, vy = compute_velocity(100.0, 100.0)
    speed = math.hypot(vx, vy)
    assert speed <= MAX_SPEED + 1e-9


def test_max_speed_direction_preserved():
    """After clamping, direction must be unchanged."""
    dx, dy = 5.0, 3.0
    vx, vy = compute_velocity(dx, dy)
    angle_in  = math.atan2(dy, dx)
    angle_out = math.atan2(vy, vx)
    assert abs(angle_in - angle_out) < 1e-6


def test_zero_displacement():
    vx, vy = compute_velocity(0.0, 0.0)
    assert vx == 0.0
    assert vy == 0.0


def test_negative_displacement():
    vx, vy = compute_velocity(-1.0, -1.0, gain=0.3)
    assert vx < 0.0
    assert vy < 0.0


def test_custom_gain():
    vx, vy = compute_velocity(2.0, 0.0, gain=0.5)
    assert abs(vx - 1.0) < 1e-9


def test_custom_max_speed():
    vx, vy = compute_velocity(10.0, 0.0, max_speed=1.0)
    assert abs(vx - 1.0) < 1e-9
    assert abs(vy - 0.0) < 1e-9


# ── Constants ─────────────────────────────────────────────────────────────────

def test_max_speed_positive():
    assert MAX_SPEED > 0


def test_arrival_threshold_positive():
    assert ARRIVAL_THRESHOLD > 0


def test_arrival_threshold_less_than_one_meter():
    # Arrival threshold should be a small value (< 1 m) for accurate navigation.
    assert ARRIVAL_THRESHOLD < 1.0
