import asyncio
import glob
import io
import json
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from state import state, add_log, PROJECT_ROOT
from ws_manager import log_manager

router = APIRouter()

COLLECT_SCRIPT      = PROJECT_ROOT / "ros2_ws" / "src" / "sim" / "data_collection" / "collect_rgb_depth_seg.py"
BUILD_DB_SCRIPT     = PROJECT_ROOT / "ros2_ws" / "src" / "sim" / "data_collection" / "build_savepoint_db.py"
OUTPUT_DIR          = PROJECT_ROOT / "ros2_ws" / "src" / "sim" / "data_collection" / "output"
TRAIN_SCRIPT        = PROJECT_ROOT / "ml" / "training" / "train.py"
TRAIN_CKPT_SCRIPT   = PROJECT_ROOT / "ml" / "training" / "train_checkpoint.py"
CHECKPOINT_DATA_DIR = PROJECT_ROOT / "ml" / "datasets" / "checkpoints"


def _stream_output(proc: subprocess.Popen, source: str, loop: asyncio.AbstractEventLoop) -> None:
    """Stream subprocess stdout to the log WebSocket, then clean up state."""
    for line in iter(proc.stdout.readline, ""):
        if line:
            entry = add_log(source, line.strip())
            asyncio.run_coroutine_threadsafe(
                log_manager.broadcast(json.dumps(entry)), loop
            )
    proc.wait()
    state["ml_process"] = None
    state["ml_step"] = None
    done = add_log(source, f"Done (exit {proc.returncode})")
    asyncio.run_coroutine_threadsafe(
        log_manager.broadcast(json.dumps(done)), loop
    )


def _start_script(script: Path, source: str, loop: asyncio.AbstractEventLoop) -> subprocess.Popen:
    """Create the subprocess and register it in state before returning."""
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # Set state["ml_process"] here (in the calling async context) before spawning
    # the streaming thread, eliminating the race condition where status could
    # return "idle" between thread spawn and first iteration of _stream_output.
    state["ml_process"] = proc
    threading.Thread(
        target=_stream_output, args=(proc, source, loop), daemon=True
    ).start()
    return proc


def _dataset_count() -> int:
    if not OUTPUT_DIR.exists():
        return 0
    return len(glob.glob(str(OUTPUT_DIR / "rgb_*.png")))


@router.get("/status")
async def ml_status():
    proc = state.get("ml_process")
    return {
        "running":       bool(proc and proc.poll() is None),
        "step":          state.get("ml_step"),
        "dataset_count": _dataset_count(),
    }


@router.post("/collect")
async def collect_data():
    if state.get("ml_process") and state["ml_process"].poll() is None:
        return {"ok": False, "error": "ML task already running"}
    state["ml_step"] = "collect"
    loop = asyncio.get_running_loop()
    proc = _start_script(COLLECT_SCRIPT, "collect", loop)
    return {"ok": True, "step": "collect", "pid": proc.pid}


@router.post("/build-db")
async def build_db():
    if state.get("ml_process") and state["ml_process"].poll() is None:
        return {"ok": False, "error": "ML task already running"}
    state["ml_step"] = "build_db"
    loop = asyncio.get_running_loop()
    proc = _start_script(BUILD_DB_SCRIPT, "build_db", loop)
    return {"ok": True, "step": "build_db", "pid": proc.pid}


@router.post("/train")
async def train_model():
    if state.get("ml_process") and state["ml_process"].poll() is None:
        return {"ok": False, "error": "ML task already running"}
    if not TRAIN_SCRIPT.exists():
        entry = add_log("train", "No training script at ml/training/train.py -- create one first")
        await log_manager.broadcast(json.dumps(entry))
        return {"ok": False, "error": "Training script not found"}
    state["ml_step"] = "train"
    loop = asyncio.get_running_loop()
    proc = _start_script(TRAIN_SCRIPT, "train", loop)
    return {"ok": True, "step": "train", "pid": proc.pid}


@router.post("/stop")
async def stop_ml():
    proc = state.get("ml_process")
    if not proc or proc.poll() is not None:
        return {"ok": False, "error": "Not running"}
    proc.terminate()
    state["ml_process"] = None
    state["ml_step"] = None
    entry = add_log("ml", "ML task stopped")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True}


# ── Checkpoint object recognition ─────────────────────────────────────────────

def _checkpoint_classes() -> list[dict]:
    """Return list of {label, count} for all checkpoint label folders."""
    if not CHECKPOINT_DATA_DIR.exists():
        return []
    result = []
    for d in sorted(CHECKPOINT_DATA_DIR.iterdir()):
        if d.is_dir():
            imgs = [f for f in d.iterdir()
                    if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}]
            result.append({"label": d.name, "count": len(imgs)})
    return result


@router.get("/checkpoints")
async def list_checkpoints():
    """Return all uploaded checkpoint labels and image counts."""
    classes = _checkpoint_classes()
    model_exists = (PROJECT_ROOT / "ml" / "models" / "checkpoint_classifier.pt").exists()
    labels_path  = PROJECT_ROOT / "ml" / "models" / "checkpoint_labels.txt"
    labels = labels_path.read_text().splitlines() if labels_path.exists() else []
    return {
        "ok":          True,
        "classes":     classes,
        "total_images": sum(c["count"] for c in classes),
        "model_exists": model_exists,
        "labels":       labels,
    }


@router.post("/checkpoints/upload")
async def upload_checkpoint_images(
    label: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """Upload one or more images for a checkpoint label."""
    if not label.strip():
        return {"ok": False, "error": "label is required"}

    safe_label = "".join(c for c in label.strip() if c.isalnum() or c in "-_ ")
    label_dir = CHECKPOINT_DATA_DIR / safe_label
    label_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    errors = []
    for upload in files:
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            errors.append(f"Skipped {upload.filename}: not an image")
            continue
        # Find a unique filename
        idx = len(list(label_dir.iterdir())) + 1
        dest = label_dir / f"img_{idx:04d}{suffix}"
        content = await upload.read()
        dest.write_bytes(content)
        saved += 1

    entry = add_log("checkpoint", f"Uploaded {saved} images for label '{safe_label}'")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True, "saved": saved, "label": safe_label, "errors": errors}


@router.delete("/checkpoints/{label}")
async def delete_checkpoint_label(label: str):
    """Delete all images for a checkpoint label."""
    import shutil
    label_dir = CHECKPOINT_DATA_DIR / label
    if not label_dir.exists():
        return {"ok": False, "error": f"Label '{label}' not found"}
    shutil.rmtree(label_dir)
    return {"ok": True}


@router.post("/checkpoints/train")
async def train_checkpoint_classifier():
    """Fine-tune ResNet-18 on uploaded checkpoint images."""
    if state.get("ml_process") and state["ml_process"].poll() is None:
        return {"ok": False, "error": "ML task already running"}

    classes = _checkpoint_classes()
    if len(classes) == 0:
        return {"ok": False, "error": "No checkpoint images uploaded yet"}
    total = sum(c["count"] for c in classes)
    if total < 4:
        return {"ok": False, "error": f"Need at least 4 images total, have {total}"}

    state["ml_step"] = "checkpoint_train"
    loop = asyncio.get_running_loop()
    proc = _start_script(TRAIN_CKPT_SCRIPT, "checkpoint", loop)
    entry = add_log("checkpoint", f"Training checkpoint classifier on {len(classes)} classes, {total} images")
    await log_manager.broadcast(json.dumps(entry))
    return {"ok": True, "step": "checkpoint_train", "pid": proc.pid}
