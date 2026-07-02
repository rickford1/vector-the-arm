#!/usr/bin/env python3
"""Simple tkinter GUI to manually drive the arm joints within their
calibrated ranges. Reads calibration.yaml for safe limits.

Per-joint row:
  - Joint name + ID
  - Live current position
  - Slider (soft_min to soft_max)
  - Torque enable toggle

Global controls:
  - All torque OFF (emergency stop)
  - All to center (drives each joint to its encoder_center)

If ROS 2 is sourced, also publishes /joint_states and launches
robot_state_publisher + RViz so the real arm is mirrored live.

Run:
    python3 arm_gui.py
"""
import math
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml not installed -- run: pip install pyyaml")

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "calibration.yaml")
PKG_DIR = os.path.join(SCRIPT_DIR, "..", "ros2", "src", "vector_the_arm_description")

ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_ACC = 41
ADDR_GOAL_POSITION = 42
ADDR_GOAL_SPEED = 46
ADDR_PRESENT_POSITION = 56

DEFAULT_SPEED = 400
DEFAULT_ACC = 20
POLL_MS = 200

SERVO_TO_JOINT = {1: "Joint1", 2: "Joint2", 3: "Joint3", 4: "Joint4"}
STEPS_PER_RAD = 4096.0 / (2 * math.pi)


class ServoRow:
    def __init__(self, parent, servo, pkt, port, lock):
        self.servo = servo
        self.pkt = pkt
        self.port = port
        self.lock = lock
        self.torque_var = tk.BooleanVar(value=False)
        self.current_var = tk.StringVar(value="---")
        self.goal_var = tk.IntVar(value=servo.get("encoder_center", 2048))
        self.last_pos = None
        self._dragging = False

        frame = ttk.LabelFrame(parent, text=f'ID {servo["id"]} — {servo["joint_name"]}', padding=8)
        frame.pack(fill="x", padx=8, pady=4)

        info = f'range {servo.get("soft_min", "?")} – {servo.get("soft_max", "?")}'
        ttk.Label(frame, text=info, foreground="gray").pack(anchor="w")

        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=4)
        ttk.Label(bar, text="current:", width=8).pack(side="left")
        ttk.Label(bar, textvariable=self.current_var, width=8, foreground="blue").pack(side="left")
        ttk.Checkbutton(bar, text="torque on", variable=self.torque_var,
                        command=self._toggle_torque).pack(side="right")

        if servo.get("type") == "uncalibrated":
            ttk.Label(frame, text="(uncalibrated — controls disabled)",
                      foreground="red").pack()
            return

        s_min = servo["soft_min"]
        s_max = servo["soft_max"]
        slider = ttk.Scale(frame, from_=s_min, to=s_max, orient="horizontal",
                           variable=self.goal_var, command=self._on_slider)
        slider.pack(fill="x")
        slider.bind("<ButtonPress-1>", lambda e: setattr(self, "_dragging", True))
        slider.bind("<ButtonRelease-1>", lambda e: self._on_release())

        ttk.Label(frame, textvariable=self.goal_var, foreground="green").pack(anchor="e")

    def _toggle_torque(self):
        with self.lock:
            val = 1 if self.torque_var.get() else 0
            if val == 1:
                self.pkt.write1ByteTxRx(self.port, self.servo["id"], ADDR_GOAL_ACC, DEFAULT_ACC)
                self.pkt.write2ByteTxRx(self.port, self.servo["id"], ADDR_GOAL_SPEED, DEFAULT_SPEED)
            self.pkt.write1ByteTxRx(self.port, self.servo["id"], ADDR_TORQUE_ENABLE, val)

    def _on_slider(self, _):
        if not self.torque_var.get():
            return
        if not self._dragging:
            return

    def _on_release(self):
        self._dragging = False
        if not self.torque_var.get():
            return
        with self.lock:
            self.pkt.write2ByteTxRx(self.port, self.servo["id"],
                                    ADDR_GOAL_POSITION, int(self.goal_var.get()))

    def poll(self):
        if self.servo.get("type") == "uncalibrated":
            return
        with self.lock:
            pos, comm, _ = self.pkt.read2ByteTxRx(self.port, self.servo["id"],
                                                   ADDR_PRESENT_POSITION)
        if comm == COMM_SUCCESS:
            self.last_pos = pos
            self.current_var.set(str(pos))


def launch_rviz():
    return [subprocess.Popen(["ros2", "launch", "vector_the_arm_description", "display_real.launch.py"])]


def main():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    port = PortHandler(cfg["port"])
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {cfg['port']}")
    port.setBaudRate(cfg["baud"])
    bus_lock = threading.Lock()

    # ROS setup
    ros_node = None
    js_pub = None
    subprocs = []
    if ROS_AVAILABLE:
        rclpy.init()
        ros_node = rclpy.create_node("arm_gui")
        js_pub = ros_node.create_publisher(JointState, "joint_states", 10)
        threading.Thread(target=rclpy.spin, args=(ros_node,), daemon=True).start()
        subprocs = list(launch_rviz())

    root = tk.Tk()
    root.title("Arm — manual joint control")
    root.geometry("560x800")

    outer = ttk.Frame(root)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    rows = [ServoRow(scroll_frame, s, pkt, port, bus_lock) for s in cfg["servos"]]

    globals_frame = ttk.Frame(root, padding=8)
    globals_frame.pack(fill="x", pady=8, side="bottom")

    def all_torque_off():
        for r in rows:
            r.torque_var.set(False)
            r._toggle_torque()

    def all_to_center():
        for r in rows:
            if r.servo.get("type") == "uncalibrated":
                continue
            if not r.torque_var.get():
                continue
            r.goal_var.set(r.servo.get("encoder_center", 2048))
            r._on_release()

    ttk.Button(globals_frame, text="ALL TORQUE OFF (E-STOP)",
               command=all_torque_off).pack(side="left", padx=4)
    ttk.Button(globals_frame, text="All to center",
               command=all_to_center).pack(side="left", padx=4)

    def poll_loop():
        for r in rows:
            r.poll()

        if js_pub is not None and ros_node is not None:
            msg = JointState()
            msg.header.stamp = ros_node.get_clock().now().to_msg()
            for r in rows:
                sid = r.servo["id"]
                if r.last_pos is None or sid not in SERVO_TO_JOINT:
                    continue
                center = r.servo.get("encoder_center", 2048)
                direction = r.servo.get("direction", 1)
                angle = (r.last_pos - center) / STEPS_PER_RAD * direction
                msg.name.append(SERVO_TO_JOINT[sid])
                msg.position.append(angle)
            if msg.name:
                js_pub.publish(msg)

        root.after(POLL_MS, poll_loop)

    root.after(POLL_MS, poll_loop)

    def on_close():
        all_torque_off()
        port.closePort()
        if ros_node is not None:
            ros_node.destroy_node()
            rclpy.shutdown()
        for p in subprocs:
            p.terminate()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
