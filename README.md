# Vector The Arm

Open-source 5-DOF printable robotic arm with vision-guided pick-and-place. Built on Feetech STS bus servos, ROS 2, MoveIt, and an Intel RealSense depth camera.

> **Status:** Work in progress. Mechanical assembly is complete (5-DOF arm), 4 joints fully calibrated, gripper and wrist roll module pending design.

## Features

- **5-DOF kinematic chain** + gripper 
- **Smart serial bus servos** (Feetech STS3215) with position + current sensing for force-aware gripping
- **Depth-camera perception** via Intel RealSense for vision-guided picking
- **ROS 2** integration with MoveIt for motion planning
- **Fully 3D-printable** structural parts 

## Documentation

- [CALIBRATION.md](CALIBRATION.md) — end-to-end servo calibration procedure

## Repo layout

```
scripts/    Servo SDK tools, calibration utilities, manual control GUI
ros2/       ROS 2 packages (URDF description, bridge node, MoveIt config — WIP)
docs/       Reference data (calibration chart, per-joint parameters)
cad/        CAD source files (forthcoming)
```

## License

TBD
