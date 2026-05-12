#!/bin/bash
echo "Starting Peregrine System..."
cd "$(dirname "$0")/../ros2_ws"
colcon build --symlink-install
source install/setup.bash
ros2 launch peregrine_launch peregrine_all.launch.py