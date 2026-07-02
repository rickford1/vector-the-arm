#!/usr/bin/env python3
"""Read live servo positions and publish them as ROS 2 JointState messages.

Bridges the Feetech bus to /joint_states so RViz can mirror the real arm.

Usage (source ROS first):
    python3 scripts/servo_joint_state_publisher.py
"""
import math
import os
import threading

import yaml
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_PRESENT_POSITION = 56
STEPS_PER_RAD = 4096.0 / (2 * math.pi)

# Servo ID → URDF joint name (must match the joint names in the URDF)
SERVO_TO_JOINT = {1: "Joint1", 2: "Joint2", 3: "Joint3", 4: "Joint4"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "calibration.yaml")


class ServoJointStatePublisher(Node):
    def __init__(self, cfg):
        super().__init__("servo_joint_state_publisher")

        self.servos = {
            s["id"]: s for s in cfg["servos"]
            if s.get("type") not in ("uncalibrated",) and s["id"] in SERVO_TO_JOINT
        }

        self.port = PortHandler(cfg["port"])
        self.pkt = PacketHandler(0)
        if not self.port.openPort():
            raise RuntimeError(f"could not open {cfg['port']}")
        self.port.setBaudRate(cfg["baud"])
        self.lock = threading.Lock()

        self.pub = self.create_publisher(JointState, "joint_states", 10)
        self.create_timer(0.05, self._publish)  # 20 Hz

    def _publish(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()

        for sid, servo in self.servos.items():
            with self.lock:
                pos, comm, _ = self.pkt.read2ByteTxRx(self.port, sid, ADDR_PRESENT_POSITION)
            if comm != COMM_SUCCESS:
                continue
            center = servo["encoder_center"]
            direction = servo.get("direction", 1)
            angle = (pos - center) / STEPS_PER_RAD * direction
            msg.name.append(SERVO_TO_JOINT[sid])
            msg.position.append(angle)

        if msg.name:
            self.pub.publish(msg)

    def destroy_node(self):
        self.port.closePort()
        super().destroy_node()


def main():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    rclpy.init()
    node = ServoJointStatePublisher(cfg)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
