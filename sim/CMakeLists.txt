cmake_minimum_required(VERSION 3.5)
project(sim)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(cv_bridge REQUIRED)

# Python executable
ament_python_install_package(
  TYPE ament_python
)

# Install the ROS2 node
install(PROGRAMS
  ros_node/airsim_bridge.py
  DESTINATION lib/
)

ament_package()

