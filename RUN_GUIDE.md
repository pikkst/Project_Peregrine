# Peregrine Run Guide

## Table of Contents
1. [Build ROS 2 Workspace](#1-build-ros-2-workspace)
2. [Start Unreal + AirSim](#2-start-unreal--airsim)
3. [Launch ROS 2 Stack](#3-launch-ros-2-stack)
4. [Verify Topics](#4-verify-topics)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Build ROS 2 Workspace

### Prerequisites
- WSL2 Ubuntu 22.04 with ROS 2 Humble
- colcon, CMake, GCC 11

```bash
# Navigate to workspace (WSL2)
cd /mnt/c/Users/PC/Desktop/Project_Peregrine/ros2_ws

# Source ROS 2
source /opt/ros/humble/setup.bash

# Install Python dependencies
pip3 install -r src/savepoint_agent/requirements.txt
pip3 install -r src/mission_agent/requirements.txt

# Build
colcon build --symlink-install

# Source the built workspace
source install/setup.bash

# Verify packages are present
ros2 pkg list | grep peregrine
```

Expected packages: `nav_agent`, `savepoint_agent`, `mission_agent`, `fusion`, `sim`, `peregrine_launch`

---

## 2. Start Unreal + AirSim

### Prerequisites (Windows)
- Unreal Engine 4.27 installed via Epic Games Launcher
- AirSim plugin at `unreal/AirSim/`

### Steps

Open the Unreal project:
```
C:\Users\PC\Desktop\Project_Peregrine\unreal\Peregrine.uproject
```

Or from PowerShell:
```powershell
& "C:\Program Files\Epic Games\Launcher\Engine\Binaries\Win64\UnrealVersionSelector.exe" "C:\Users\PC\Desktop\Project_Peregrine\unreal\Peregrine.uproject"
```

1. Unreal Editor opens — verify AirSim plugin is enabled under **Edit > Plugins**
2. Press **Play** (F9 or toolbar Play button)
3. AirSim server starts automatically on `127.0.0.1:41451`

### AirSim settings (`unreal/AirSim/settings.json`)
```json
{
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0,
      "AllowAPIAlways": true,
      "AutoCreate": true
    }
  },
  "CameraDefaults": {
    "CaptureSettings": [
      {
        "ImageType": 0,
        "Width": 640,
        "Height": 480,
        "FOV_Degrees": 90,
        "MotionBlurAmount": 0
      }
    ]
  }
}
```

---

## 3. Launch ROS 2 Stack

### Option A — Full stack at once (recommended)

```bash
source install/setup.bash

# Standard launch
ros2 launch peregrine_launch peregrine_all.launch.py

# With AirSim simulation clock
ros2 launch peregrine_launch peregrine_all.launch.py use_sim_time:=true
```

### Option B — Individual nodes (debug mode)

```bash
# Terminal 1 — AirSim bridge
source install/setup.bash
ros2 launch sim airsim_bridge.launch.py

# Terminal 2 — Nav Agent (VIO)
source install/setup.bash
ros2 launch nav_agent nav_agent.launch.py

# Terminal 3 — Savepoint Agent (VPR)
source install/setup.bash
ros2 launch savepoint_agent savepoint_agent.launch.py

# Terminal 4 — Mission Agent
source install/setup.bash
ros2 launch mission_agent mission_agent.launch.py

# Terminal 5 — EKF Fusion
source install/setup.bash
ros2 launch fusion ekf.launch.py
```

### Option C — Automated script

```bash
python3 scripts/run_all.py
# Flags: --force-build  --skip-ros-check  --no-sim  --sim-time
```

---

## 4. Verify Topics

```bash
# AirSim bridge output
ros2 topic echo /airsim/camera/front_left/image_raw
ros2 topic echo /airsim/imu

# VIO odometry (30-50 Hz)
ros2 topic echo /odom/vio_high_freq

# Savepoint drift corrections (0.5-2 Hz)
ros2 topic echo /localization/landmark_fix

# EKF fused global odometry
ros2 topic echo /odometry/filtered

# Velocity commands to flight controller
ros2 topic echo /cmd_vel

# Monitor rates
ros2 topic hz /odom/vio_high_freq
ros2 topic hz /odometry/filtered
```

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `VIO node crashes on start` | Missing VIO library or bad camera calibration | Install OpenVINS/ORB-SLAM3 deps; check `nav_agent/config/vio_params.yaml` |
| No images on `/airsim/...` topics | AirSim bridge not running or wrong IP/port | Start bridge; verify `unreal/AirSim/settings.json` |
| `Savepoint agent high latency (>300 ms)` | Model too heavy for CPU; no TensorRT engine | Use TensorRT + FP16/INT8; reduce input resolution |
| `EKF output diverges` | Covariance too optimistic | Increase measurement noise in `fusion/ekf_config.yaml` |
| `Commands not reaching flight controller` | Bridge misconfigured | Verify MAVROS or custom AirSim control bridge |
| `colcon build fails` | Missing dependencies | `sudo apt install ros-humble-desktop python3-colcon-common-extensions` |
| `ImportError: No module named 'rclpy'` | ROS 2 not sourced | `source /opt/ros/humble/setup.bash` |

### Useful diagnostic commands

```bash
# List running nodes
ros2 node list

# List all active topics
ros2 topic list

# Inspect a node
ros2 node info /nav_agent

# View transform tree
ros2 run tf2_ros tf2_echo map odom
```
