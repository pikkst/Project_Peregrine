# Peregrine Launch Package

This package contains launch files for the Peregrine robotics system, integrating all agents and subsystems.

## Overview

The `peregrine_launch` package provides the main launch file (`peregrine_all.launch.py`) that starts all components of the Peregrine system:

- **VIO (Visual Inertial Odometry)**: High-frequency pose estimation from camera and IMU
- **VPR (Visual Place Recognition)**: Loop closure detection using deep learning
- **EKF (Extended Kalman Filter)**: Sensor fusion for state estimation
- **Fusion**: Combines all sensor data into a unified state estimate
- **Mission Agent**: Waypoint navigation and mission execution

## Usage

### Basic Launch

To launch the entire system:

```bash
# Source the workspace
source install/setup.bash

# Launch all components
ros2 launch peregrine_launch peregrine_all.launch.py
```

### With Simulation Time

To use simulation time (for Gazebo/Unreal/AirSim):

```bash
ros2 launch peregrine_launch peregrine_all.launch.py use_sim_time:=true
```

### Custom Configuration Files

You can specify custom configuration files:

```bash
ros2 launch peregrine_launch peregrine_all.launch.py \
  vio_config_path:=/path/to/vio_config.yaml \
  ekf_config_path:=/path/to/ekf_config.yaml \
  vpr_model_path:=/path/to/vpr_model.bin
```

## Launch Arguments

- `use_sim_time` (default: `false`): Use simulation clock instead of system time
- `vio_config_path`: Path to VIO configuration YAML file
- `ekf_config_path`: Path to EKF configuration YAML file
- `vpr_model_path`: Path to VPR model file

## Components

### VIO Node
Publishes high-frequency odometry from camera and IMU data.

- **Input**: `/sensors/imu`, `/sensors/camera/image_raw`
- **Output**: `/vio/pose`

### VPR Node
Performs visual place recognition for loop closure detection.

- **Input**: `/sensors/camera/image_raw`
- **Output**: `/vpr/match`

### EKF Node
Fuses multiple sensor streams using an Extended Kalman Filter.

- **Input**: `/sensors/imu`, `/sensors/gps`, `/vio/pose`
- **Output**: `/estimation/odometry`, `/estimation/state`

### Fusion Node
Combines all estimates into a unified state.

- **Input**: `/vio/pose`, `/vpr/match`, `/ekf/state`
- **Output**: `/estimation/fused_state`

## Monitoring

To monitor the system:

```bash
# List active topics
ros2 topic list

# View specific topic
ros2 topic echo /estimation/fused_state

# View diagnostics
ros2 diagnostics
```

## Run All System

For a complete startup script that includes environment checks, workspace building, and system launch:

```bash
python3 scripts/run_all.py
```

See the [run_all.py](../scripts/run_all.py) script for more options.

## Configuration Files

Configuration files are located in:

- `config/vio_config.yaml`: VIO parameters
- `config/ekf_config.yaml`: EKF parameters
- `models/vpr_model.bin`: VPR model file

## Troubleshooting

### Nodes Not Starting
- Ensure all dependencies are built: `colcon build`
- Check that all required topics are available: `ros2 topic list`

### Poor Localization
- Verify camera and IMU calibration parameters
- Check that VIO config matches your sensors
- Ensure sufficient lighting for visual features

### High CPU Usage
- Reduce camera frame rate or resolution
- Adjust VIO and VPR feature counts
- Lower EKF update frequency

## Requirements

- ROS 2 Humble or later
- `rclpy`
- `launch` and `launch_ros`
- `geometry_msgs`, `nav_msgs`, `std_msgs`

## License

MIT License