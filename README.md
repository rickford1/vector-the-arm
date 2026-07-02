# Vector The Arm

Open-source 5-DOF printable robotic arm with vision-guided pick-and-place. Built on Feetech STS bus servos, ROS 2, MoveIt, and an Intel RealSense depth camera.

> **Status:** Work in progress. Mechanical assembly is complete (5-DOF arm).
> Joints 1–4 are fully calibrated and mirror live into RViz; motion planning
> runs in MoveIt (simulation / mock hardware). Wrist roll and gripper modules
> are pending design. Driving the real servos from MoveIt is not yet wired up.

## Features

- **5-DOF kinematic chain** + gripper
- **Smart serial bus servos** (Feetech STS3215) with position + current sensing for force-aware gripping
- **Depth-camera perception** via Intel RealSense for vision-guided picking
- **ROS 2** integration with MoveIt for motion planning (sim working; hardware execution WIP)
- **Live RViz mirroring** of the physical arm from the servo bus
- **Fully 3D-printable** structural parts

## Visualize the URDF

Requires ROS 2 Humble and the joint-slider GUI (one-time install):

```bash
sudo apt install ros-humble-joint-state-publisher-gui
```

Build the description package once, then launch RViz with joint sliders:

```bash
source /opt/ros/humble/setup.bash
cd ros2
colcon build --packages-select vector_the_arm_description
source install/setup.bash
ros2 launch vector_the_arm_description display.launch.py
```

Joint limits in the URDF are the calibrated ranges from
[docs/calibration_chart.md](docs/calibration_chart.md). If you edit the
URDF, re-run `colcon build` before launching by package name.

## Mirror the real arm in RViz

`scripts/arm_gui.py` owns the serial bus, publishes live encoder positions as
`/joint_states` (using `calibration.yaml` for the per-joint encoder→radian
mapping), and launches `robot_state_publisher` + RViz so the model tracks the
physical arm in real time. It also gives you per-joint sliders and an E-stop.

```bash
source /opt/ros/humble/setup.bash
source ros2/install/setup.bash          # so RViz can launch by package name
python3 scripts/arm_gui.py
```

Set `port:` in `calibration.yaml` to your bus device (e.g. `/dev/ttyACM0`).
Move the arm by hand (torque off) or drive joints from the GUI — RViz mirrors it.

## Motion planning with MoveIt (simulation)

One-time install of MoveIt and ros2_control:

```bash
sudo apt install ros-humble-moveit ros-humble-ros2-control ros-humble-ros2-controllers
```

Build and launch the MoveIt config on mock hardware:

```bash
source /opt/ros/humble/setup.bash
cd ros2
colcon build --packages-select vector_the_arm_moveit_config
source install/setup.bash
ros2 launch vector_the_arm_moveit_config demo.launch.py
```

In the **MotionPlanning** panel, set a goal (Joints tab), then **Plan & Execute**.

> **Note:** this runs on *mock hardware* — it moves a simulated arm, not the
> servos. Also, the arm is currently 4 actuated joints (base yaw + 3 pitch), so
> full 6-DOF pose goals won't solve — use joint-space or position-only goals.
> A `FollowJointTrajectory` → Feetech bridge to drive the real arm from MoveIt
> is the next step.

## Documentation

- [CALIBRATION.md](CALIBRATION.md) — end-to-end servo calibration procedure

## Repo layout

```
scripts/    Servo SDK tools, calibration utilities, manual control + live-mirror GUI
ros2/       ROS 2 packages:
              vector_the_arm_description   URDF, meshes, display launches
              vector_the_arm_moveit_config MoveIt config (SRDF, controllers, demo)
docs/       Reference data (calibration chart, per-joint parameters)
cad/        CAD source files (forthcoming)
```

## License

TBD
