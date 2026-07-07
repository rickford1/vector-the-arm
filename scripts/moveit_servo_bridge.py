#!/usr/bin/env python3
"""FollowJointTrajectory bridge: drive the real Feetech arm from MoveIt.

Owns the serial bus. Publishes /joint_states from live encoder reads (so
MoveIt's start state matches the real arm), and serves the
/arm_controller/follow_joint_trajectory action that MoveIt's
moveit_simple_controller_manager sends planned trajectories to.

Radian<->encoder mapping and soft limits come from calibration.yaml.
Every commanded position is clamped to the joint's soft_min/soft_max, so a
plan can never drive a joint into a hard stop.

Safety:
  - On startup, each servo's goal is set to its *current* position before
    torque is enabled, so nothing snaps when the bridge comes up.
  - Ctrl+C disables torque on all joints (software E-stop).

Run (with ROS + workspace sourced, arm powered):
    python3 scripts/moveit_servo_bridge.py
"""
import math
import os
import threading
import time

import yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import JointState
from control_msgs.action import FollowJointTrajectory

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_ACC = 41
ADDR_GOAL_POSITION = 42
ADDR_GOAL_SPEED = 46
ADDR_PRESENT_POSITION = 56

STEPS_PER_RAD = 4096.0 / (2 * math.pi)
SERVO_TO_JOINT = {1: "Joint1", 2: "Joint2", 3: "Joint3", 4: "Joint4",
                  5: "Joint5", 6: "gripper_joint"}

DEFAULT_SPEED = 400   # conservative; RViz velocity scaling limits the plan too
DEFAULT_ACC = 20

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "calibration.yaml")


class MoveItServoBridge(Node):
    def __init__(self, cfg):
        super().__init__("moveit_servo_bridge")

        self.servos = {}  # joint_name -> servo dict
        for s in cfg["servos"]:
            if s["id"] in SERVO_TO_JOINT and s.get("type") != "uncalibrated":
                self.servos[SERVO_TO_JOINT[s["id"]]] = s

        self.port = PortHandler(cfg["port"])
        self.pkt = PacketHandler(0)
        if not self.port.openPort():
            raise RuntimeError(f"could not open {cfg['port']}")
        self.port.setBaudRate(cfg["baud"])
        self.lock = threading.Lock()

        # Hold current position, then enable torque (no snap on startup).
        for jn, s in self.servos.items():
            with self.lock:
                pos, comm, _ = self.pkt.read2ByteTxRx(self.port, s["id"], ADDR_PRESENT_POSITION)
                self.pkt.write1ByteTxRx(self.port, s["id"], ADDR_GOAL_ACC, DEFAULT_ACC)
                self.pkt.write2ByteTxRx(self.port, s["id"], ADDR_GOAL_SPEED, DEFAULT_SPEED)
                if comm == COMM_SUCCESS:
                    self.pkt.write2ByteTxRx(self.port, s["id"], ADDR_GOAL_POSITION, pos)
                self.pkt.write1ByteTxRx(self.port, s["id"], ADDR_TORQUE_ENABLE, 1)

        cb = ReentrantCallbackGroup()
        self.js_pub = self.create_publisher(JointState, "joint_states", 10)
        self.create_timer(0.05, self._publish_js, callback_group=cb)
        self._action = ActionServer(
            self, FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory",
            execute_callback=self._execute,
            callback_group=cb,
        )
        self.get_logger().info("bridge ready: torque ON, holding position, serving FollowJointTrajectory")

    def _angle_to_enc(self, s, angle):
        pos = int(round(s["encoder_center"] + s.get("direction", 1) * angle * STEPS_PER_RAD))
        return max(s["soft_min"], min(s["soft_max"], pos))  # clamp to soft limits

    def _enc_to_angle(self, s, pos):
        return (pos - s["encoder_center"]) / STEPS_PER_RAD * s.get("direction", 1)

    def _publish_js(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        for jn, s in self.servos.items():
            with self.lock:
                pos, comm, _ = self.pkt.read2ByteTxRx(self.port, s["id"], ADDR_PRESENT_POSITION)
            if comm != COMM_SUCCESS:
                continue
            msg.name.append(jn)
            msg.position.append(self._enc_to_angle(s, pos))
        if msg.name:
            self.js_pub.publish(msg)

    def _execute(self, goal_handle):
        traj = goal_handle.request.trajectory
        names = traj.joint_names
        start = time.monotonic()
        for pt in traj.points:
            t = pt.time_from_start.sec + pt.time_from_start.nanosec * 1e-9
            while (time.monotonic() - start) < t:
                if not goal_handle.is_active:
                    return FollowJointTrajectory.Result()
                time.sleep(0.002)
            for i, jn in enumerate(names):
                s = self.servos.get(jn)
                if s is None:
                    continue
                enc = self._angle_to_enc(s, pt.positions[i])
                with self.lock:
                    self.pkt.write2ByteTxRx(self.port, s["id"], ADDR_GOAL_POSITION, enc)
        goal_handle.succeed()
        result = FollowJointTrajectory.Result()
        result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
        return result

    def shutdown(self):
        for jn, s in self.servos.items():
            with self.lock:
                self.pkt.write1ByteTxRx(self.port, s["id"], ADDR_TORQUE_ENABLE, 0)
        self.port.closePort()


def main():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    rclpy.init()
    node = MoveItServoBridge(cfg)
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
