@echo off
echo Starting Peregrine System...
cd /d "%~dp0..\ros2_ws"
call colcon build --symlink-install
call install\setup.bat
ros2 launch peregrine_launch peregrine_all.launch.py