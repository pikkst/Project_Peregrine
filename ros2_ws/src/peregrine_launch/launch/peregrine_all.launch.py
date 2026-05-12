from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os

def generate_launch_description():
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true'
    )

    ekf_config_path = os.path.join(
        get_package_share_directory('fusion'),
        'ekf_config.yaml'
    )

    start_vio = Node(
        package='nav_agent',
        executable='nav_agent_node',
        name='nav_agent',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    start_vpr = Node(
        package='savepoint_agent',
        executable='savepoint_node',
        name='savepoint_agent',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    start_ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_fusion',
        output='screen',
        parameters=[ekf_config_path],
        remappings=[('/odometry/filtered', '/odometry/filtered')]
    )

    start_airsim_bridge = Node(
        package='sim',
        executable='airsim_bridge',
        name='airsim_bridge',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    start_mission = Node(
        package='mission_agent',
        executable='mission_agent',
        name='mission_agent',
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    return LaunchDescription([
        use_sim_time,
        start_vio,
        start_vpr,
        start_ekf,
        start_airsim_bridge,
        start_mission,
    ])