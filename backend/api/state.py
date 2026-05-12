import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ROS2_WS      = PROJECT_ROOT / "ros2_ws"

# ── Persistent log file ───────────────────────────────────────────────────────
_LOG_DIR = PROJECT_ROOT / "backend" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_file_logger = logging.getLogger("peregrine.log")
_file_logger.setLevel(logging.DEBUG)
_file_logger.propagate = False

_fh = RotatingFileHandler(
    _LOG_DIR / "peregrine.log",
    maxBytes=10 * 1024 * 1024,   # 10 MB per file
    backupCount=5,
    encoding="utf-8",
)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_file_logger.addHandler(_fh)

# ── In-memory state ───────────────────────────────────────────────────────────
state: dict = {
    "ros2_process":    None,
    "sim_process":     None,
    "ml_process":      None,
    "ml_step":         None,
    "mission_running": False,
    "current_wp_idx":  0,
    "waypoints": [
        {"x": 1.0, "y": 0.0, "z": -2.0},
        {"x": 1.0, "y": 1.0, "z": -2.0},
        {"x": 0.0, "y": 1.0, "z": -2.0},
    ],
    "telemetry": {
        "x": 0.0, "y": 0.0, "z": 0.0,
        "vx": 0.0, "vy": 0.0, "vz": 0.0,
        "yaw": 0.0, "t": 0.0,
        "wp_idx": 0, "mission_running": False,
    },
    "log_queue": [],
    "hardware_config": {},
    "hardware_status": "disconnected",
}

_log_lock = threading.Lock()


def add_log(source: str, line: str) -> dict:
    """Append a log entry to the in-memory queue and persist it to disk."""
    text = line.strip()
    entry = {"source": source, "text": text}

    with _log_lock:
        state["log_queue"].append(entry)
        if len(state["log_queue"]) > 1000:
            state["log_queue"].pop(0)

    # Write to rotating log file (non-blocking — uses the existing handler thread)
    _file_logger.info("[%s] %s", source, text)

    return entry
