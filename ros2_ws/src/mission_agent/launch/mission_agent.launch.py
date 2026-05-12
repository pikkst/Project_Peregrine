from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='mission_agent',
            executable='mission_agent.py',
            name='mission_agent',
            output='screen'
        )
    ])
