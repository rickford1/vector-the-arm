# Vector The Arm

Open-source 5-DOF printable robotic arm with vision-guided pick-and-place. Built on Feetech STS bus servos, ROS 2, MoveIt, and an Intel RealSense depth camera.

> **Status:** Work in progress. Mechanical assembly is complete (5-DOF arm).
> Joints 1–4 are fully calibrated and mirror live into RViz, and **MoveIt plans
> and executes motions on both the simulated and the real arm**. Wrist roll and
> gripper modules are pending design; perception is not yet integrated.

## Features

- **5-DOF kinematic chain** + gripper
- **Smart serial bus servos** (Feetech STS3215) with position + current sensing for force-aware gripping
- **ROS 2 + MoveIt** motion planning — runs in simulation *and* drives the real arm
- **Live RViz mirroring** of the physical arm from the servo bus
- **Depth-camera perception** via Intel RealSense for vision-guided picking (planned)
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

## Motion planning with MoveIt

One-time install of MoveIt and ros2_control:

```bash
sudo apt install ros-humble-moveit ros-humble-ros2-control ros-humble-ros2-controllers
```

Build the MoveIt config once:

```bash
source /opt/ros/humble/setup.bash
cd ros2
colcon build --packages-select vector_the_arm_moveit_config
source install/setup.bash
```

### Simulation (mock hardware)

```bash
ros2 launch vector_the_arm_moveit_config demo.launch.py
```

Plans and executes against a simulated arm — no hardware needed. Good for
trying plans before running them on the real servos.

### Drive the real arm

`scripts/moveit_servo_bridge.py` is a `FollowJointTrajectory` action server that
replaces the mock hardware: it owns the serial bus, publishes `/joint_states`
from live encoder reads (so MoveIt's start state matches the real arm), and
streams planned trajectories to the servos — mapping radians→encoder and
**clamping every goal to each joint's `soft_min`/`soft_max`** via
`calibration.yaml`.

Run in two terminals, both with ROS + workspace sourced, arm powered:

```bash
# Terminal 1 — bridge (start first; takes the bus, enables torque holding the
# current pose, publishes joint states, serves the trajectory action)
python3 scripts/moveit_servo_bridge.py

# Terminal 2 — MoveIt (rsp + move_group + RViz, no mock hardware)
ros2 launch vector_the_arm_moveit_config bringup_real.launch.py
```

In the **MotionPlanning** panel the start state already matches the real arm.
Set a goal (Joints tab), **Plan**, then **Execute** — the servos follow.

**Safety:**
- Start with **Velocity Scaling 0.10** and small joint moves.
- Goals are clamped to soft limits, so a plan can't drive into a hard stop.
- **Ctrl+C the bridge terminal is the E-stop** — it disables torque on exit.

**4-DOF note:** the arm currently has 4 actuated joints (base yaw + 3 pitch), so
full 6-DOF pose goals won't solve. Use **joint-space** or **position-only**
goals. This lifts once the wrist roll and gripper are built.

## Documentation

- [CALIBRATION.md](CALIBRATION.md) — end-to-end servo calibration procedure

## Repo layout

```
scripts/    Servo SDK tools, calibration utilities, manual-control + live-mirror
            GUI, and the MoveIt→Feetech trajectory bridge
ros2/       ROS 2 packages:
              vector_the_arm_description   URDF, meshes, display launches
              vector_the_arm_moveit_config MoveIt config (SRDF, controllers,
                                           demo + real-hardware bringup)
docs/       Reference data (calibration chart, per-joint parameters)
cad/        CAD source files (forthcoming)
```

## License

TBD
