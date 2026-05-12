# Peregrine: GNSS-Denied Autonomous Drone Navigation Stack

## 📚 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites & Installation](#prerequisites--installation)
- [Quick Start](#quick-start)
- [ROS 2 Workspace Setup](#ros-2-workspace-setup)
- [Unreal Engine + AirSim Setup](#unreal-engine--airsim-setup)
- [ML Pipeline Setup](#ml-pipeline-setup)
- [Running the System](#running-the-system)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

Peregrine is a complete autonomous navigation system for drones in GNSS-denied environments, based on visual navigation (VIO), visual place recognition (VPR), and data fusion.

The system consists of three autonomous agents that operate together in real-time:

- **Nav Agent (VIO)** — C++ based, responsible for high-frequency (30–50 Hz) stereo and tri‑ocular visual inertial odometry. Provides low latency and stable poses.
- **Savepoint Agent (VPR)** — Python based, deep learning-based visual place recognition (Visual Place Recognition). Compares real-time camera views with a pre-recorded savepoint database and corrects VIO drift through absolute positioning data.
- **Mission Agent (waypoint navigation)** — Python based, high-level waypoint navigation. Consumes globally fused poses resulting from fusion and outputs /cmd_vel velocity commands to the aircraft.

An Extended Kalman Filter (robot_localization ROS 2 package) is used for sensor fusion, which combines the fast VIO signal and sparse savepoint corrections into a consistent global pose.

## System Architecture

### Agents

```
┌─────────────────────┐    ┌──────────────────────┐    ┌──────────────────┐
│   Nav Agent (VIO)   │    │ Savepoint Agent (VPR)│    │ Mission Agent    │
│      (C++)          │    │      (Python)        │    │    (Python)      │
│ 30–50 Hz odom/vio  │────┤ 0.5–2 Hz landmark    │────┤ Waypoint logic   │
│ OpenVINS/ORB-SLAM3  │    │ SuperPoint/NetVLAD   │    │ /cmd_vel         │
└─────────────────────┘    └──────────────────────┘    └──────────────────┘
            │                         │                         │
            └─────────────┬───────────┼─────────────────────────┘
                          │           │
                 ┌────────▼──────────▼─────────┐
                 │  EKF Fusion (robot_localization)          │
                 │  /odometry/global_filtered               │
                 └───────────────────────────────────────────┘
```

### Data Flow

- **Inputs:**
   - Stereo camera (RGB) and IMU from AirSim/sim
   - Savepoint database (images + ground-truth pose)
   - Waypoint paths
- **Processes:**
   - VIO provides fast, but largely drifting poses
   - VPR provides slow, but absolute corrections
   - EKF combines these into a coordinated pose
- **Outputs:**
   - `/odometry/global_filtered` — filtered global pose
   - `/cmd_vel` — velocity commands sent to aircraft

## Project Structure

```
Project Peregrine/
├── ros2_ws/                       # ROS 2 workspace
│   └── src/
│       ├── nav_agent/             # VIO (C++) — OpenVINS / ORB-SLAM3 wrapper
│       ├── savepoint_agent/       # VPR (Python) — Deep learning landmark matching
│       ├── mission_agent/         # Waypoint navigation (Python)
│       ├── fusion/                # EKF configuration & launch files
│       ├── sim/                   # AirSim bridge, sim utilities
│       └── peregrine_launch/      # Top-level launch files
├── unreal/                        # Unreal Engine project
│   ├── Peregrine.uproject
│   └── AirSim/                    # AirSim plugin & config
├── ml/                            # ML pipeline
│   ├── datasets/                  # Synthetic + real data
│   ├── training/                  # VPR model training scripts
│   ├── models/                    # Trained models (SuperPoint, NetVLAD, ...)
│   └── inference/                 # TensorRT engines, inference nodes
├── backend/                       # Backend services
│   ├── api/                       # REST/WebSocket API
│   └── websocket/                 # WS bridge for telemetry
└── ui/                            # Frontend UI
    └── src/
```

## Prerequisites & Installation

### OS
- **Host (dev/sim):** Windows 10/11 (recommended for Unreal + AirSim GPU training)
- **ROS 2 runtime:** WSL2 Ubuntu 22.04 (Humble)
- **Deploy target (optional):** Nvidia Jetson Orin NX/AGX (Ubuntu 20.04/22.04, ROS 2 Humble)

### Core Dependencies
| Component        | Requirement                                  |
|------------------|----------------------------------------------|
| ROS 2            | Humble (desktop or humble-desktop-full)      |
| VIO backend      | OpenVINS **or** ORB‑SLAM3 (stereo‑inertial) |
| Python           | 3.10 (+ pip/venv)                            |
| Build system     | colcon, CMake, GCC 11                       |
| ML frameworks    | PyTorch, CUDA 11.x (optional), TensorRT      |
| Simulation       | Unreal Engine 5, AirSim plugin               |
| Image transport  | ROS 2 image_transport, compressed_depth      |

### Quick Install (Ubuntu/WSL2)
```bash
# 1) Install ROS 2 Humble (desktop)
sudo apt update && sudo apt install -y ros-humble-desktop

# 2) Create colcon workspace
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws

# 3) Clone this repo into src (or copy Project Peregrine/ros2_ws/src contents)
cp -r /path/to/Project\ Peregrine/ros2_ws/src/* src/

# 4) Install VIO dependencies (example: OpenVINS)
# See nav_agent/README.md for detailed build steps
sudo apt install -y libopencv-dev libsuitesparse-dev

# 5) Install Python deps for agents
cd src/savepoint_agent && pip3 install -r requirements.txt
cd ../mission_agent && pip3 install -r requirements.txt

# 6) Build workspace
cd ~/ros2_ws
colcon build --symlink-install

# 7) Source
source install/setup.bash
```

### Frontend Setup
```bash
cd ui
npm install
npm run dev
```

### Frontend Production Build
```bash
cd ui
npm install
npm run build
```

### Backend API Setup
```bash
python -m pip install -r backend/requirements.txt
python backend/api/main.py
```

### Frontend / Backend Auth
If you enable `PEREGRINE_API_KEY` for the backend, set `VITE_API_KEY` in `ui/.env` or use the example file:
```bash
cp ui/.env.example ui/.env
# Edit ui/.env to set VITE_API_KEY
```

### Windows Setup (for Unreal + AirSim)
1. Clone repo to `C:\Users\PC\Desktop\Project Peregrine`
2. Install Unreal Engine 5 (Epic Games Launcher)
3. Build AirSim from source or use prebuilt plugin in `unreal/AirSim/`
4. Open `Peregrine.uproject`, enable AirSim plugin
5. Use WSL2 for ROS 2 — bridge AirSim to ROS 2 via TCP/ROS bridge in `ros2_ws/src/sim/`

## Quick Start

### 1) Build ROS 2 Workspace
```bash
cd ros2_ws
colcon build
source install/setup.bash
```

### 2) Launch Simulation (Unreal + AirSim)
- Open Unreal project, press **Play** in desired mode (FLY/Sim).
- Ensure AirSim server is running (see `unreal/AirSim/settings.json`).

### 3) Start ROS 2 Stack
```bash
# Terminal 1 — AirSim bridge (publishes /airsim/camera/..., /airsim/imu)
ros2 launch sim airsim_bridge.launch.py

# Terminal 2 — Nav Agent (VIO)
ros2 launch nav_agent nav_agent.launch.py

# Terminal 3 — Savepoint Agent (VPR)
ros2 launch savepoint_agent savepoint_agent.launch.py

# Terminal 4 — Mission Agent
ros2 launch mission_agent mission_agent.launch.py

# Terminal 5 — EKF fusion
ros2 launch fusion ekf.launch.py

# Or launch all agents at once:
ros2 launch peregrine_launch peregrine_all.launch.py
```

### 4) Verify Topics
```bash
# Check VIO output
ros2 topic echo /odom/vio_high_freq

# Check landmark fixes
ros2 topic echo /localization/landmark_fix

# Check fused global odometry
ros2 topic echo /odometry/global_filtered

# Check velocity commands to flight controller
ros2 topic echo /cmd_vel
```

## ROS 2 Workspace Setup

The ROS 2 workspace (`ros2_ws/`) is organized as a standard colcon workspace:
- `src/` — source packages (git-tracked)
- `build/` — colcon build artifacts
- `install/` — installed packages & setup scripts

Each agent is a standalone ROS 2 package with its own `package.xml`, `CMakeLists.txt` (C++) or `setup.py` (Python), and launch/config files.

### Nav Agent (C++)
- **Purpose:** High-frequency VIO using OpenVINS or ORB‑SLAM3.
- **Key launch:** `nav_agent/launch/nav_agent.launch.py`
- **Dependencies:** OpenVINS/ORB‑SLAM3 libs, OpenCV, Eigen, ROS 2 image_transport.
- **Config:** `nav_agent/config/vio_params.yaml`

### Savepoint Agent (Python)
- **Purpose:** VPR inference and landmark fixes.
- **Key launch:** `savepoint_agent/launch/savepoint_agent.launch.py`
- **Dependencies:** PyTorch, TorchVision, onnxruntime/tensorrt, OpenCV.
- **Config:** `savepoint_agent/config/vpr.yaml`, database path.
- **Model formats:** PyTorch (.pt), ONNX, TensorRT engine (.plan).

### Mission Agent (Python)
- **Purpose:** Waypoint navigation & high-level autonomy.
- **Key launch:** `mission_agent/launch/mission_agent.launch.py`
- **Dependencies:** NumPy, transforms3d, simple-pid or similar.
- **Config:** `mission_agent/config/waypoints.yaml`, control gains.

### Fusion Package
- **Purpose:** EKF configuration & launch.
- **Config:** `fusion/config/ekf.yaml` (robot_localization params).
- **Launch:** `fusion/launch/ekf.launch.py`

### Sim Package
- **Purpose:** AirSim bridge, synthetic data collection scripts.
- **Scripts:** `sim/scripts/airsim_bridge.py`, `sim/scripts/collect_trajectory.py`

### Peregrine Launch
- **Purpose:** Top-level convenience launches.
- `peregrine_launch/launch/peregrine_all.launch.py` — starts entire stack.

## Unreal Engine + AirSim Setup

### Prerequisites
- Epic Games Launcher + Unreal Engine 5 (5.2+ recommended)
- AirSim compiled plugin or binary release

### Build AirSim (recommended)
```bash
# Clone AirSim
git clone https://github.com/microsoft/AirSim.git
cd AirSim
./Build.sh        # Linux (for Unreal plugin build)
# Or use prebuilt binaries for Windows
```

### Configure Peregrine Project
1. Place AirSim plugin under `unreal/AirSim/`
2. Open `Peregrine.uproject` → enable AirSim plugin in Plugins menu.
3. Configure `unreal/AirSim/settings.json`:
   - Set IP/port for ROS bridge (`127.0.0.1:41451` default)
   - Define vehicle type (simple flight), camera config (stereo + IMU)
   - Scene settings (weather, lighting, domain randomization options)

### Data Collection (Synthetic)
```bash
# Python control via AirSim Python client
python3 sim/scripts/collect_trajectory.py --output-dir ml/datasets/sim/001 --path predefined/orbit
```
Script automates takeoff, follows predefined trajectory, publishes camera/IMU/gt to ROS 2 topics and saves aligned data for VPR database creation.

### Domain Randomization (optional)
Use Unreal material parameter collections and AirSim weather APIs to randomize:
- Lighting, shadows, exposure
- Fog, rain, wind
- Texture swaps & object placement

## ML Pipeline Setup

### Directory layout
- `ml/datasets/` — raw synthetic + real flight logs; organized by run ID
- `ml/training/` — VPR training scripts (SuperPoint/SuperGlue, NetVLAD, CosPlace, DINOv2 fine-tune)
- `ml/models/` — trained checkpoints, exported formats (.onnx, .pt, .plan)
- `ml/inference/` — ROS 2 inference nodes (Python), TensorRT engine generation scripts

### Example: Train VPR Model
```bash
cd ml/training/vpr
# Use synthetic dataset exported from AirSim
python train.py --dataset-path ../../datasets/sim/001 --model superpoint_superglue --epochs 50
```

### Export to TensorRT (Jetson deployment)
```bash
python export_onnx.py --ckpt model_best.pt --output model.onnx
python convert_to_trt.py --onnx model.onnx --fp16 --output model_fp16.plan
```

### Inference Node
- `ml/inference/savepoint_inference.py` — ROS 2 node wrapping TensorRT engine.
- Subscribers: `/camera/front/image_raw`
- Publishers: `/localization/landmark_fix`
- Configurable batch size, input resolution, quantization.

## Running the System

### End-to-end (sim + stack)
1. Start Unreal + AirSim (Play mode).
2. Run the full ROS 2 launch:
   ```bash
   source install/setup.bash
   ros2 launch peregrine_launch peregrine_all.launch.py
   ```
3. Observe:
   - VIO publishes high-rate pose (`/odom/vio_high_freq`)
   - Savepoint agent publishes drift corrections (`/localization/landmark_fix`)
   - EKF produces stable global pose (`/odometry/global_filtered`)
   - Mission agent navigates waypoints (`/cmd_vel`)

### Performance Monitoring
```bash
# Plot topics
ros2 topic hz /odom/vio_high_freq
ros2 topic hz /localization/landmark_fix

# Latency & drift checks
ros2 run tf2_ros tf2_echo map odom  # or use RViz2 for visualization
```

### Expected Behavior
- VIO drifts gradually with time/distance.
- Savepoint corrections snap global pose to near-truth when landmarks observed.
- Mission agent continues smooth navigation using corrected pose.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| VIO node crashes on start | Missing VIO library or invalid camera calibration | Install OpenVINS/ORB‑SLAM3 deps; check camera yaml in config |
| No images on `/airsim/...` topics | AirSim bridge not running or wrong IP/port | Start bridge; verify AirSim settings.json match |
| Savepoint agent high latency (>300 ms) | Model too heavy for CPU/GPU; no TensorRT engine | Use TensorRT + FP16/INT8; resize input; check GPU usage |
| EKF output diverges | Covariance tunes too optimistic | Increase measurement noise in `ekf.yaml` for VIO or savepoint topics |
| Commands not reaching flight controller (in sim) | Flight controller bridge misconfigured | Verify MAVROS or custom bridge mapping to AirSim control API |
| Sim/real mismatch in deployment | Domain gap (lighting, lens, motion blur) | Domain randomization; real fine‑tuning; exposure lock; IMU bias cal |

## Contributing

Pull requests welcome. Focus areas:
- VIO wrappers (OpenVINS / ORB‑SLAM3 ROS 2 integration)
- VPR model improvements (lighter backbones, better retrieval)
- EKF tuning & observability analysis
- Real‑world dataset collection & sim‑to‑real pipelines
- Jetson deployment automation

### Workflow
1. Branch from `main`.
2. Keep changes scoped (one agent/feature per PR).
3. Add/Update launch/config docs.
4. Update this README if interfaces or dependencies change.

---  
*Peregrine — production‑grade visual autonomy for GNSS‑denied flight.*