#!/bin/bash
# Launch RealSense D415 at 640x480 (avoids USB bandwidth saturation on
# current cable; upgrade cable later if 1280x720 is needed).
#
# Run:
#   ./launch_camera.sh

ros2 launch realsense2_camera rs_launch.py \
  enable_color:=true \
  enable_depth:=true \
  pointcloud.enable:=true \
  rgb_camera.color_profile:=640x480x30 \
  depth_module.depth_profile:=640x480x30
