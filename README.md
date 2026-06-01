# Vector The Arm

Open-source 5-DOF printable robotic arm with vision-guided pick-and-place. Built on Feetech STS bus servos, ROS 2, MoveIt, and an Intel RealSense depth camera.

> **Status:** Work in progress. Mechanical assembly is complete (5-DOF arm), 4 joints fully calibrated, gripper and wrist roll module pending design.

## Features

- **5-DOF kinematic chain** + gripper (6-DOF total when complete)
- **Smart serial bus servos** (Feetech STS3215) with position + current sensing for force-aware gripping
- **Depth-camera perception** via Intel RealSense for vision-guided picking
- **ROS 2** integration with MoveIt for motion planning
- **Fully 3D-printable** structural parts (designs forthcoming)
- **Documented calibration workflow** including encoder wraparound handling — see [CALIBRATION.md](CALIBRATION.md)

## Documentation

- [CALIBRATION.md](CALIBRATION.md) — end-to-end servo calibration procedure
- More guides (HARDWARE, SETUP, ARCHITECTURE, TROUBLESHOOTING) coming as the project matures

## Repo layout

```
scripts/    Servo SDK tools, calibration utilities, manual control GUI
ros2/       ROS 2 packages (URDF description, bridge node, MoveIt config — WIP)
docs/       Reference data (calibration chart, per-joint parameters)
cad/        CAD source files (forthcoming)
```

## License

TBD — likely Apache 2.0 or MIT, to be finalized before first release tag.
