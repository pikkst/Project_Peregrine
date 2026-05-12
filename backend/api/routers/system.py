import asyncio
import json
import subprocess
import threading
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter
from state import state, add_log, ROS2_WS
from ws_manager import log_manager

router = APIRouter()


def _stream_process(proc, source: str, loop):
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        entry = add_log(source, line.strip())
        asyncio.run_coroutine_threadsafe(
            log_manager.broadcast(json.dumps(entry)), loop
        )


@router.post("/build")
async def build_ros2():
    if state.get("ros2_process") and state["ros2_process"].poll() is None:
        return {"ok": False, "error": "Stop ROS2 before rebuilding"}
    loop = asyncio.get_running_loop()

    async def _run():
        entry = add_log("build", "Starting colcon build...")
        await log_manager.broadcast(json.dumps(entry))
        proc = subprocess.Popen(
            ["colcon", "build", "--symlink-install"],
            cwd=str(ROS2_WS),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        t = threading.Thread(target=_stream_process, args=(proc, "build", loop), daemon=True)
        t.start()
        await asyncio.get_running_loop().run_in_executor(None, proc.wait)
        msg = "Build succeeded" if proc.returncode == 0 else f"Build failed (exit {proc.returncode})"
        entry = add_log("build", msg)
        await log_manager.broadcast(json.dumps(entry))

    asyncio.create_task(_run())
    return {"ok": True, "message": "Build started — check Logs"}


@router.post("/launch")
async def launch_ros2(use_sim_time: bool = False):
    if state.get("ros2_process") and state["ros2_process"].poll() is None:
        return {"ok": False, "error": "Already running"}
    launch_file = ROS2_WS / "src" / "peregrine_launch" / "launch" / "peregrine_all.launch.py"
    if not launch_file.exists():
        return {"ok": False, "error": f"Launch file not found: {launch_file}"}

    cmd = ["ros2", "launch", str(launch_file)]
    if use_sim_time:
        cmd.append("use_sim_time:=true")

    loop = asyncio.get_running_loop()
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(ROS2_WS),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        state["ros2_process"] = proc
        t = threading.Thread(target=_stream_process, args=(proc, "ros2", loop), daemon=True)
        t.start()
        entry = add_log("system", f"ROS2 launched (PID {proc.pid})")
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": True, "pid": proc.pid}
    except FileNotFoundError:
        return {"ok": False, "error": "'ros2' command not found — source ROS2 setup first"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/stop")
async def stop_ros2():
    proc = state.get("ros2_process")
    if not proc or proc.poll() is not None:
        return {"ok": False, "error": "Not running"}
    proc.terminate()
    state["ros2_process"] = None
    state["mission_running"] = False
    entry = add_log("system", "ROS2 stopped")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True}


@router.get("/status")
async def get_status():
    ros2 = state.get("ros2_process")
    sim  = state.get("sim_process")
    ml   = state.get("ml_process")
    return {
        "ros2":       "running" if (ros2 and ros2.poll() is None) else "stopped",
        "simulation": "running" if (sim  and sim.poll()  is None) else "stopped",
        "ml":         "running" if (ml   and ml.poll()   is None) else "idle",
        "ml_step":    state.get("ml_step"),
        "mission":    "running" if state["mission_running"] else "idle",
        "hardware":   state.get("hardware_status", "disconnected"),
        "build_exists": (ROS2_WS / "install").exists(),
    }
