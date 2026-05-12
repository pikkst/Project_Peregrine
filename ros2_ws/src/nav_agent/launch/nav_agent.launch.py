from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nav_agent',
            executable='nav_agent_node',
            name='nav_agent',
            output='screen'
        )
    ])
