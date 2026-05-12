cmake_minimum_required(VERSION 3.8)
project(savepoint_agent)

# Find Python and ROS 2 dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)

# Install Python package (empty __init__.py for namespace)
install(
  FILES __init__.py
  DESTINATION lib/python3.10/site-packages/${PROJECT_NAME}
)

# Install Python scripts with executable permissions
install(
  PROGRAMS
    ros_node/savepoint_node.py
    inference/vpr_inference.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files
install(
  DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Create empty __init__.py for Python namespace
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/__init__.py "")
install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/__init__.py
  DESTINATION lib/python3.10/site-packages/${PROJECT_NAME}
)

ament_package()
