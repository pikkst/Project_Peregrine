"""
API endpoint smoke tests.

Covered endpoints
-----------------
  GET  /api/health
  GET  /api/system/status
  GET  /api/ml/status
  GET  /api/mission/status
  POST /api/mission/waypoints
  POST /api/mission/start   (expects error — ROS 2 not running)
  POST /api/mission/stop

Authentication
--------------
  Verifies that 401 is returned when a key is required but absent.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── System ────────────────────────────────────────────────────────────────────

def test_system_status_schema(client):
    r = client.get("/api/system/status")
    assert r.status_code == 200
    data = r.json()
    for key in ("ros2", "simulation", "ml", "mission"):
        assert key in data, f"Missing key: {key}"


def test_system_status_ros2_stopped(client):
    r = client.get("/api/system/status")
    assert r.json()["ros2"] == "stopped"


# ── ML ────────────────────────────────────────────────────────────────────────

def test_ml_status_schema(client):
    r = client.get("/api/ml/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data
    assert "step" in data
    assert "dataset_count" in data


def test_ml_status_idle(client):
    r = client.get("/api/ml/status")
    assert r.json()["running"] is False
    assert r.json()["step"] is None


# ── Mission ───────────────────────────────────────────────────────────────────

def test_mission_status_schema(client):
    r = client.get("/api/mission/status")
    assert r.status_code == 200
    data = r.json()
    for key in ("running", "current_wp", "total", "waypoints"):
        assert key in data

def test_mission_status_not_running(client):
    r = client.get("/api/mission/status")
    assert r.json()["running"] is False


def test_set_waypoints_valid(client):
    payload = [
        {"x": 1.0, "y": 0.0, "z": -2.0},
        {"x": 2.0, "y": 1.0, "z": -2.0},
        {"x": 0.0, "y": 2.0, "z": -2.0},
    ]
    r = client.post("/api/mission/waypoints", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 3


def test_set_waypoints_empty(client):
    r = client.post("/api/mission/waypoints", json=[])
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["count"] == 0


def test_start_mission_without_ros2(client):
    # Seed a waypoint so "no waypoints" error is not triggered
    client.post("/api/mission/waypoints", json=[{"x": 1.0, "y": 0.0, "z": -2.0}])
    r = client.post("/api/mission/start")
    assert r.status_code == 200
    # ROS 2 is not running — should return an error
    assert r.json()["ok"] is False


def test_stop_mission(client):
    r = client.post("/api/mission/stop")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Authentication ────────────────────────────────────────────────────────────

def test_auth_disabled_by_default(client):
    """Without PEREGRINE_API_KEY set, all requests are allowed."""
    r = client.get("/api/system/status")
    assert r.status_code == 200


def test_auth_rejects_missing_key():
    """When PEREGRINE_API_KEY is set, requests without Bearer token → 401."""
    import auth as auth_mod
    import main as main_mod
    original = auth_mod.API_KEY
    try:
        auth_mod.API_KEY = "secret-key"
        from fastapi.testclient import TestClient
        # Re-import to pick up patched auth module
        importlib.reload(main_mod)
        with TestClient(main_mod.app) as c:
            r = c.get("/api/system/status")
            assert r.status_code == 401
    finally:
        auth_mod.API_KEY = original
        importlib.reload(main_mod)


def test_auth_accepts_valid_key():
    """Requests with the correct Bearer token are accepted."""
    import auth as auth_mod
    import main as main_mod
    original = auth_mod.API_KEY
    try:
        auth_mod.API_KEY = "secret-key"
        importlib.reload(main_mod)
        from fastapi.testclient import TestClient
        with TestClient(main_mod.app) as c:
            r = c.get("/api/system/status",
                      headers={"Authorization": "Bearer secret-key"})
            assert r.status_code == 200
    finally:
        auth_mod.API_KEY = original
        importlib.reload(main_mod)
