from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='savepoint_agent',
            executable='savepoint_node.py',
            name='savepoint_agent',
            output='screen'
        )
    ])
