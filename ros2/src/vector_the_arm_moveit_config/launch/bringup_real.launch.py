"""MoveIt on the REAL arm.

Same as demo.launch.py but WITHOUT the mock ros2_control hardware and its
spawners. MoveIt's FollowJointTrajectory controller instead talks to the
scripts/moveit_servo_bridge.py node, which drives the Feetech servos.

Start the bridge FIRST (it owns the serial bus and publishes /joint_states):
    python3 scripts/moveit_servo_bridge.py

Then:
    ros2 launch vector_the_arm_moveit_config bringup_real.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    launch_dir = os.path.join(
        get_package_share_directory("vector_the_arm_moveit_config"), "launch"
    )

    def include(name):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, name))
        )

    # rsp + static TF + move_group + rviz. No ros2_control_node, no spawners —
    # the bridge provides /joint_states and the FollowJointTrajectory action.
    return LaunchDescription([
        include("rsp.launch.py"),
        include("static_virtual_joint_tfs.launch.py"),
        include("move_group.launch.py"),
        include("moveit_rviz.launch.py"),
    ])
