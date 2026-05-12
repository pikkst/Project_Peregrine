"""
Peregrine Control Center — FastAPI Backend
Run from project root: python backend/api/main.py
"""

import asyncio
import json
import math
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

_api_dir = Path(__file__).parent
sys.path.insert(0, str(_api_dir))

import uvicorn
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from auth import require_api_key, require_ws_token
from state import state, PROJECT_ROOT
from ws_manager import log_manager, telemetry_manager

UI_DIST        = PROJECT_ROOT / "ui" / "dist"
TELEMETRY_FILE = PROJECT_ROOT / "backend" / "tmp" / "telemetry.json"
# Telemetry file is considered stale after this many seconds.
_TELEMETRY_STALE_SEC = 2.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_telemetry_loop())
    yield
    task.cancel()
    for key in ("ros2_process", "sim_process", "ml_process"):
        p = state.get(key)
        if p and p.poll() is None:
            p.terminate()


app = FastAPI(
    title="Peregrine Control Center",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import system as system_router
from routers import simulation as sim_router
from routers import mission as mission_router
from routers import ml as ml_router
from routers import hardware as hardware_router

# All /api/* routes require a valid API key when PEREGRINE_API_KEY is set.
_auth_dep = [Depends(require_api_key)]

app.include_router(system_router.router,  prefix="/api/system",     tags=["system"],     dependencies=_auth_dep)
app.include_router(sim_router.router,     prefix="/api/simulation",  tags=["simulation"], dependencies=_auth_dep)
app.include_router(mission_router.router, prefix="/api/mission",     tags=["mission"],    dependencies=_auth_dep)
app.include_router(ml_router.router,      prefix="/api/ml",          tags=["ml"],         dependencies=_auth_dep)
app.include_router(hardware_router.router, prefix="/api/hardware",   tags=["hardware"],   dependencies=_auth_dep)


@app.get("/api/health")
async def health():
    """Public health-check endpoint — no auth required."""
    return {"status": "ok"}


# ── WebSocket endpoints ───────────────────────────────────────────────────────

@app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket, _: None = Depends(require_ws_token)):
    await log_manager.connect(ws)
    try:
        for entry in list(state["log_queue"])[-100:]:
            await ws.send_text(json.dumps(entry))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)


@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket, _: None = Depends(require_ws_token)):
    await telemetry_manager.connect(ws)
    try:
        await ws.send_text(json.dumps(state["telemetry"]))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        telemetry_manager.disconnect(ws)


# ── Telemetry loop ────────────────────────────────────────────────────────────

def _read_bridge_telemetry() -> dict | None:
    """
    Try to read telemetry written by backend/ros2_bridge/telemetry_bridge.py.
    Returns None if the file is absent or older than _TELEMETRY_STALE_SEC.
    """
    try:
        if not TELEMETRY_FILE.exists():
            return None
        age = time.time() - TELEMETRY_FILE.stat().st_mtime
        if age > _TELEMETRY_STALE_SEC:
            return None
        return json.loads(TELEMETRY_FILE.read_text())
    except Exception:
        return None


async def _telemetry_loop():
    t = 0.0
    while True:
        await asyncio.sleep(0.2)  # 5 Hz

        ros_running = bool(state.get("ros2_process") and
                           state["ros2_process"].poll() is None)

        # Prefer live telemetry from the ROS 2 bridge file.
        bridge = _read_bridge_telemetry() if ros_running else None

        if bridge is not None:
            tel = {
                "x":   bridge.get("x", 0.0),
                "y":   bridge.get("y", 0.0),
                "z":   bridge.get("z", 0.0),
                "vx":  bridge.get("vx", 0.0),
                "vy":  bridge.get("vy", 0.0),
                "vz":  bridge.get("vz", 0.0),
                "yaw": bridge.get("yaw", 0.0),
                "t":   round(bridge.get("ts", 0.0), 1),
                "wp_idx":         state.get("current_wp_idx", 0),
                "mission_running": state.get("mission_running", False),
            }
        elif ros_running:
            # ROS 2 is running but bridge file not available — use mock
            # (sinusoidal simulation) so the UI shows activity.
            t += 0.2
            tel = {
                "x":   round(0.5 * math.sin(t * 0.5), 3),
                "y":   round(0.5 * math.cos(t * 0.3), 3),
                "z":   round(-2.0 + 0.1 * math.sin(t), 3),
                "vx":  round(0.1 * math.cos(t * 0.5), 3),
                "vy":  round(-0.1 * math.sin(t * 0.3), 3),
                "vz":  0.0,
                "yaw": round(math.degrees(math.atan2(math.sin(t * 0.2),
                                                      math.cos(t * 0.2))), 1),
                "t":   round(t, 1),
                "wp_idx":          state.get("current_wp_idx", 0),
                "mission_running": state.get("mission_running", False),
            }
        else:
            t = 0.0
            tel = {
                "x": 0.0, "y": 0.0, "z": 0.0,
                "vx": 0.0, "vy": 0.0, "vz": 0.0,
                "yaw": 0.0, "t": 0.0,
                "wp_idx": 0, "mission_running": False,
            }

        state["telemetry"] = tel
        await telemetry_manager.broadcast(json.dumps(tel))


# ── Serve React build in production ──────────────────────────────────────────
if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
