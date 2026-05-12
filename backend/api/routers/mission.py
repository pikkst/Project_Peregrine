import asyncio
import json
from typing import List
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter
from pydantic import BaseModel
from state import state, add_log
from ws_manager import log_manager

router = APIRouter()


class Waypoint(BaseModel):
    x: float
    y: float
    z: float = -2.0


@router.get("/status")
async def mission_status():
    return {
        "running":      state["mission_running"],
        "current_wp":   state.get("current_wp_idx", 0),
        "total":        len(state["waypoints"]),
        "waypoints":    state["waypoints"],
    }


@router.post("/waypoints")
async def set_waypoints(waypoints: List[Waypoint]):
    state["waypoints"] = [wp.model_dump() for wp in waypoints]
    entry = add_log("mission", f"Waypoints updated ({len(waypoints)} points)")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True, "count": len(waypoints)}


@router.post("/start")
async def start_mission():
    if not (state.get("ros2_process") and state["ros2_process"].poll() is None):
        return {"ok": False, "error": "Launch ROS2 first"}
    if not state["waypoints"]:
        return {"ok": False, "error": "No waypoints defined"}
    state["mission_running"] = True
    state["current_wp_idx"] = 0
    entry = add_log("mission", f"Mission started — {len(state['waypoints'])} waypoints")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True}


@router.post("/stop")
async def stop_mission():
    state["mission_running"] = False
    entry = add_log("mission", "Mission stopped")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True}
