import os
import json
import glob

INPUT_DIR = "sim/data_collection/output"
DB_DIR = "sim/savepoint_database"
os.makedirs(DB_DIR, exist_ok=True)

db_index = []

for img_path in sorted(glob.glob(os.path.join(INPUT_DIR, "rgb_*.png"))):
    idx = os.path.basename(img_path).split("_")[1].split(".")[0]
    pose = {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "qx": 0.0,
        "qy": 0.0,
        "qz": 0.0,
        "qw": 1.0
    }
    entry = {
        "image": os.path.basename(img_path),
        "pose": pose
    }
    db_index.append(entry)

with open(os.path.join(DB_DIR, "savepoints.json"), "w") as f:
    json.dump(db_index, f, indent=2)
