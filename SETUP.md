# Peregrine Setup Guide

## 1. ROS 2 Humble Installation

### Ubuntu 22.04 / WSL2

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install locale settings
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# 3. Install dependencies
sudo apt install -y curl gnupg lsb-release

# 4. Add ROS 2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# 5. Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 6. Install ROS 2 Humble
sudo apt update
sudo apt install -y ros-humble-desktop

# 7. Install colcon build tools
sudo apt install -y python3-colcon-common-extensions python3-argcomplete python3-vcstool

# 8. Initialize rosdep
sudo apt install -y python3-rosdep
sudo rosdep init
rosdep update

# 9. Source ROS 2 in bashrc
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

### Windows (WSL2) - Additional Setup

```bash
# Install additional packages for ROS 2
sudo apt install -y python3-pip python3-venv build-essential cmake git

# Verify installation
ros2 --version
```

## 2. Unreal Engine + AirSim Setup

### Prerequisites
- Windows 10/11
- Epic Games Launcher
- Visual Studio 2022 (with C++ development tools)
- Unreal Engine 4.27

### Unreal Engine Installation

1. Install Epic Games Launcher from https://www.epicgames.com/store/en-US/download
2. Install Unreal Engine 4.27 through the launcher
3. Launch Unreal Engine once to complete installation

### AirSim Plugin Setup

```powershell
# 1. Clone AirSim repository
cd ~/Project\ Peregrine
# or on Windows:
# cd "C:\Users\PC\Desktop\Project Peregrine"
git clone https://github.com/microsoft/AirSim.git unreal/AirSim

# 2. Build AirSim plugin
cd unreal/AirSim
.\Build.cmd  # Windows build script

# Alternative: Use prebuilt binaries
# Download from https://github.com/microsoft/AirSim/releases
```

### Configure Peregrine Unreal Project

1. Open `Peregrine.uproject` in Unreal Editor
2. Go to **Edit > Plugins**
3. Enable **AirSim** plugin
4. Restart Unreal Editor
5. Copy `unreal/AirSim/settings.json` to project root if not present

### AirSim Settings Configuration

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
        "AutoExposureSpeed": 100,
        "AutoExposureBias": 0,
        "AutoExposureMaxBrightness": 0.6,
        "AutoExposureMinBrightness": 0.3,
        "MotionBlurAmount": 0,
        "FreeCameraRotation": 0
      }
    ]
  }
}
```

## 3. ML Environment Setup

### Conda Environment (Recommended)

```bash
# 1. Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 2. Create conda environment
conda create -n peregrine python=3.10 -y
conda activate peregrine

# 3. Install PyTorch (adjust for CUDA version)
conda install pytorch torchvision torchaudio cudatoolkit=11.8 -c pytorch -c nvidia

# 4. Install additional ML dependencies
pip install numpy opencv-python onnxruntime-gpu tensorrt
```

### Virtual Environment (Lightweight Alternative)

```bash
# 1. Create venv
python3 -m venv ~/peregrine_venv
source ~/peregrine_venv/bin/activate

# 2. Upgrade pip
pip install --upgrade pip

# 3. Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install numpy opencv-python onnxruntime-gpu tensorrt
```

## 4. Installing Dependencies

### ROS 2 Workspace Dependencies

```bash
cd ~/ros2_ws
# or on Windows/WSL:
# cd /mnt/c/Users/PC/Desktop/Project/Peregrine/ros2_ws

# Install Python dependencies for each agent
pip3 install -r src/savepoint_agent/requirements.txt
pip3 install -r src/mission_agent/requirements.txt

# Install VIO dependencies
sudo apt install -y libopencv-dev libsuitesparse-dev libeigen3-dev
```

### Build Workspace

```bash
cd ~/ros2_ws
# or on Windows/WSL:
# cd /mnt/c/Users/PC/Desktop/Project\ Peregrine/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### Verify Installation

```bash
# Check ROS 2 nodes
ros2 node list

# Expected: nodes should appear after running launch files
```

## 5. Quick Commands

| Command | Description |
|---------|-------------|
| `colcon build --symlink-install` | Build ROS 2 workspace |
| `source install/setup.bash` | Source workspace |
| `ros2 launch peregrine_launch peregrine_all.launch.py` | Start full system |
| `conda activate peregrine` | Activate ML environment |