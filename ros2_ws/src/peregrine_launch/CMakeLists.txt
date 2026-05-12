cmake_minimum_required(VERSION 3.8)
project(peregrine_launch)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES Clang)
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  PATTERN *.yaml
)

install(DIRECTORY models/
  DESTINATION share/${PROJECT_NAME}/models
  PATTERN *.bin
  PATTERN *.yaml
)

ament_python_install_package(${PROJECT_NAME})

ament_package()
