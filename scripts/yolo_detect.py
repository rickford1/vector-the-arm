#!/usr/bin/env python3
"""Quick object-detection test on the RealSense color stream.

Subscribes to the camera's color image, runs a YOLO model, and shows the
annotated frame in a window. Default is YOLOv8n (COCO classes — keyboard,
mouse, laptop, cell phone, person are all in your scene). Switch to a
YOLO-World model for open-vocabulary text prompts.

Run (ROS + workspace sourced, with realsense2_camera already publishing):
    python3 scripts/yolo_detect.py
"""
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

COLOR_TOPIC = "/camera/camera/color/image_raw"

# --- Standard YOLOv8 (COCO classes) — instant win, your scene is full of them.
MODEL = "yolov8n.pt"
PROMPTS = None

# --- Open-vocabulary instead: comment the two lines above, uncomment these.
# MODEL = "yolov8s-world.pt"
# PROMPTS = ["yellow marker", "coffee mug", "pretzel"]


class YoloView(Node):
    def __init__(self):
        super().__init__("yolo_detect")
        self.model = YOLO(MODEL)
        if PROMPTS:
            self.model.set_classes(PROMPTS)      # YOLO-World text prompts
        self.bridge = CvBridge()
        self.create_subscription(Image, COLOR_TOPIC, self._on_image, 10)
        self.get_logger().info(f"running {MODEL} on {COLOR_TOPIC}")

    def _on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        results = self.model(frame, verbose=False)
        cv2.imshow("YOLO - RealSense", results[0].plot())
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = YoloView()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
