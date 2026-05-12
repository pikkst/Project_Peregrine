cmake_minimum_required(VERSION 3.8)
project(sim)

find_package(ament_cmake_python REQUIRED)

install(
  DIRECTORY data_collection/
  DESTINATION share/${PROJECT_NAME}/data_collection
  FILES_MATCHING PATTERN "*.py"
)

install(
  FILES airsim_settings.json
  DESTINATION share/${PROJECT_NAME}
)

ament_python_install_package(${PROJECT_NAME})