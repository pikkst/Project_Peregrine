cmake_minimum_required(VERSION 3.8)
project(nav_agent)

# Require C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake  REQUIRED)
find_package(rclcpp       REQUIRED)
find_package(sensor_msgs  REQUIRED)
find_package(nav_msgs     REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(cv_bridge    REQUIRED)
find_package(image_transport REQUIRED)
find_package(tf2_ros      REQUIRED)
find_package(tf2          REQUIRED)
find_package(Eigen3       REQUIRED)
find_package(OpenCV       REQUIRED)

include_directories(include)

add_executable(nav_agent_node
  src/nav_agent_node.cpp
  src/vio_wrapper.cpp
)

ament_target_dependencies(nav_agent_node
  rclcpp
  sensor_msgs
  nav_msgs
  geometry_msgs
  cv_bridge
  image_transport
  tf2_ros
  tf2
)

target_link_libraries(nav_agent_node
  Eigen3::Eigen
  ${OpenCV_LIBS}
)

# ── Optional: OpenVINS backend ────────────────────────────────────────────────
# Build with: colcon build --cmake-args -DUSE_OPENVINS=ON
option(USE_OPENVINS "Build with OpenVINS VIO backend" OFF)
if(USE_OPENVINS)
  find_package(ov_core REQUIRED)
  find_package(ov_msckf REQUIRED)
  target_compile_definitions(nav_agent_node PRIVATE USE_OPENVINS)
  ament_target_dependencies(nav_agent_node ov_core ov_msckf)
  message(STATUS "nav_agent: OpenVINS backend ENABLED")
else()
  # Try to auto-detect even without the flag
  find_package(ov_core QUIET)
  find_package(ov_msckf QUIET)
  if(ov_core_FOUND AND ov_msckf_FOUND)
    target_compile_definitions(nav_agent_node PRIVATE USE_OPENVINS)
    ament_target_dependencies(nav_agent_node ov_core ov_msckf)
    message(STATUS "nav_agent: OpenVINS auto-detected and enabled")
  endif()
endif()

# ── Optional: ORB-SLAM3 backend ───────────────────────────────────────────────
# Build with: colcon build --cmake-args -DUSE_ORBSLAM3=ON
option(USE_ORBSLAM3 "Build with ORB-SLAM3 VIO backend" OFF)
if(USE_ORBSLAM3)
  find_library(ORBSLAM3_LIB ORB_SLAM3
    PATHS /usr/local/lib /opt/ORB_SLAM3/lib
    REQUIRED
  )
  find_path(ORBSLAM3_INCLUDE System.h
    PATHS /usr/local/include/ORB_SLAM3 /opt/ORB_SLAM3/include
    REQUIRED
  )
  target_compile_definitions(nav_agent_node PRIVATE USE_ORBSLAM3)
  target_include_directories(nav_agent_node PRIVATE ${ORBSLAM3_INCLUDE})
  target_link_libraries(nav_agent_node ${ORBSLAM3_LIB})
  message(STATUS "nav_agent: ORB-SLAM3 backend ENABLED (${ORBSLAM3_LIB})")
else()
  # Auto-detect
  find_library(ORBSLAM3_LIB ORB_SLAM3
    PATHS /usr/local/lib /opt/ORB_SLAM3/lib
    NO_DEFAULT_PATH QUIET
  )
  if(ORBSLAM3_LIB)
    find_path(ORBSLAM3_INCLUDE System.h
      PATHS /usr/local/include/ORB_SLAM3 /opt/ORB_SLAM3/include
      NO_DEFAULT_PATH QUIET
    )
    if(ORBSLAM3_INCLUDE AND NOT ov_msckf_FOUND)
      target_compile_definitions(nav_agent_node PRIVATE USE_ORBSLAM3)
      target_include_directories(nav_agent_node PRIVATE ${ORBSLAM3_INCLUDE})
      target_link_libraries(nav_agent_node ${ORBSLAM3_LIB})
      message(STATUS "nav_agent: ORB-SLAM3 auto-detected and enabled")
    endif()
  endif()
endif()

if(NOT USE_OPENVINS AND NOT USE_ORBSLAM3 AND NOT ov_msckf_FOUND AND NOT ORBSLAM3_LIB)
  message(WARNING
    "nav_agent: No VIO backend found. The node will compile and run but will "
    "publish identity pose only.\n"
    "  • OpenVINS: install ov_core + ov_msckf and rebuild\n"
    "  • ORB-SLAM3: install to /usr/local or /opt/ORB_SLAM3 and rebuild\n"
    "  • Or pass -DUSE_OPENVINS=ON / -DUSE_ORBSLAM3=ON to colcon")
endif()

# ── Install ───────────────────────────────────────────────────────────────────
install(TARGETS
  nav_agent_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

ament_package()
