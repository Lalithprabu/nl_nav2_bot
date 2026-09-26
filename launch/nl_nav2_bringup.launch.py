"""Bring up TurtleBot3 in Gazebo + Nav2 + the natural-language commander.

Usage:
    export TURTLEBOT3_MODEL=waffle
    ros2 launch nl_nav2_bot nl_nav2_bringup.launch.py

Then in another terminal:
    ros2 run nl_nav2_bot text_input_node
    > go to the kitchen
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
    tb3_nav2_dir = get_package_share_directory('turtlebot3_navigation2')
    nl_nav2_bot_dir = get_package_share_directory('nl_nav2_bot')

    # TurtleBot3's own Nav2 launch file needs an explicit params file and
    # map file - its defaults don't always resolve cleanly across releases.
    tb3_model = os.environ.get('TURTLEBOT3_MODEL', 'waffle')
    params_file = os.path.join(nl_nav2_bot_dir, 'config', 'waffle_custom.yaml')
    map_yaml_file = os.path.join(tb3_nav2_dir, 'map', 'map.yaml')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'turtlebot3_world.launch.py')
        ),
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_nav2_dir, 'launch', 'navigation2.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map': map_yaml_file,
            'params_file': params_file,
        }.items(),
    )

    commander = Node(
        package='nl_nav2_bot',
        executable='nl_command_node',
        name='nl_command_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'waypoints_file': os.path.join(nl_nav2_bot_dir, 'config', 'waypoints.yaml'),
        }],
    )

    return LaunchDescription([gazebo, nav2, commander])
