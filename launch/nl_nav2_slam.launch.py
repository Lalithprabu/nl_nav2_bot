"""Bring up TurtleBot3 in Gazebo with SLAM (builds a map live) instead of
using the pre-built map + AMCL. Drive the robot around (keyboard teleop
or nl_command with a coordinate you know is safe), then save the map with:

    ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/nl_nav2_bot/config/my_map

Usage:
    ros2 launch nl_nav2_bot nl_nav2_slam.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    slam_toolbox_dir = get_package_share_directory('slam_toolbox')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'turtlebot3_world.launch.py')
        ),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox_dir, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    teleop_hint = Node(
        package='nl_nav2_bot',
        executable='nl_command_node',
        name='nl_command_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'waypoints_file': os.path.join(
                get_package_share_directory('nl_nav2_bot'), 'config', 'waypoints.yaml'),
        }],
    )

    return LaunchDescription([gazebo, slam, teleop_hint])
