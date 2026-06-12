#!/usr/bin/env python3
"""RViz visualization for vector_the_arm_description.

    ros2 launch vector_the_arm_description display.launch.py   # if built with colcon
    ros2 launch /abs/path/to/launch/display.launch.py          # also works unbuilt

Starts robot_state_publisher (URDF as robot_description),
joint_state_publisher_gui (sliders), and rviz2. Meshes render once the package
is colcon-built; unbuilt, links show as TF frames (enough to check joint axes).
"""
import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    urdf_path = os.path.join(pkg_share, "urdf", "vector_the_arm_description.urdf")
    rviz_cfg = os.path.join(pkg_share, "config", "display.rviz")

    with open(urdf_path, "r") as f:
        robot_description = f.read()

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            output="screen",
            arguments=["-d", rviz_cfg] if os.path.exists(rviz_cfg) else [],
        ),
    ])
