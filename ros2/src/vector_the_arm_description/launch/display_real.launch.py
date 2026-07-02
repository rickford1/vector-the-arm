#!/usr/bin/env python3
"""RViz visualization driven by real servo positions.

Run the servo bridge separately before launching:
    python3 scripts/servo_joint_state_publisher.py

Then:
    ros2 launch vector_the_arm_description display_real.launch.py
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
            package="rviz2",
            executable="rviz2",
            output="screen",
            arguments=["-d", rviz_cfg] if os.path.exists(rviz_cfg) else [],
        ),
    ])
