# Robot Arm Servo Calibration Guide

End-to-end calibration procedure for a Feetech STS3215-based robot arm. This is the procedure used to bring this arm from a box of parts to a fully-calibrated 5-DOF + gripper system ready for ROS 2 / MoveIt. Reading time ~15 min. Working time ~1–2 hours for a 4–6 joint arm.

## What "calibration" means here

For each servo, calibration produces four things stored in `calibration.yaml`:

1. **A unique bus ID** — so multi-drop bus addressing works
2. **A known horn orientation** — encoder pos 2048 corresponds to a known physical pose ("neutral")
3. **Mechanical range** — the encoder min/max for the joint's physical travel between hard stops
4. **Soft limits** — software-enforced bounds inside the mechanical range, with a safety margin

Plus, if needed: a **Position Correction** value written to EEPROM to fix encoder wraparound (when a joint's travel crosses encoder 0/4095).

The result: every script and ROS node in this project knows where each joint is in physical space and what range it can safely move through.

---

## Prerequisites

### Hardware

- Feetech STS3215 servos (any quantity; tested with 6)
- Waveshare bus servo driver board (or equivalent USB-to-TTL bus adapter)
- 12 V DC power supply, **≥5 A recommended** (10 A for stalling margin)
- USB cable to driver board
- Servos pre-assembled into arm (or bench setup if pre-assembly)

### Software

```bash
pip install feetech-servo-sdk pyyaml
```

This project uses the lower-level `protocol_packet_handler` API (the higher-level `sms_sts` class is not in the PyPI package — don't try to import it).

### Permissions

You'll need access to the serial device:

```bash
sudo usermod -a -G dialout $USER
# log out and back in
```

Otherwise, every script will fail with permission errors on `/dev/ttyACM*`.

### Find your bus device

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Most setups show `/dev/ttyACM0`. The Waveshare board uses USB CDC-ACM, so it's `ttyACM*`, not `ttyUSB*`. **Note**: the number can shuffle between reboots — see [Troubleshooting → Port Shuffling](#port-shuffling) for a permanent fix.

### ⚠️ Verify PSU voltage before any servo work

STS3215 absolute max is ~14 V. Some "12 V" supplies (especially adjustable lab supplies and cheap bricks) drift high. **Check with a multimeter before plugging in servos.** A 14+ V supply will damage servos over time.

---

## The procedure

### Phase 1 — Assign unique IDs (one servo at a time)

**Every Feetech servo ships with factory ID = 1.** Plugging multiple new servos onto the same bus causes ID collisions: both servos respond to every ping simultaneously, the protocol corrupts, and you get inconsistent or no responses.

**Always assign IDs one servo at a time on an otherwise empty bus.**

For each servo:

1. **Power down** the bus (turn off the 12 V supply for safety, even though it's not strictly required for ID changes)
2. **Disconnect all other servos** from the bus. Leave only the servo you're about to flash.
3. **Power on**, then run:
   ```bash
   python3 scripts/scan.py --port /dev/ttyACM0 --max-id 10
   ```
   Confirm: only ID 1 responds (the factory default of the lone servo).
4. **Flash to the target ID**:
   ```bash
   python3 scripts/servo_id_setup.py --port /dev/ttyACM0 --new-id <N>
   ```
   Where `<N>` is the desired ID (1–253). For an arm, use sequential IDs starting at 1 from base to gripper.
5. **Verify**:
   ```bash
   python3 scripts/scan.py --port /dev/ttyACM0 --max-id 10
   ```
   Should now show only ID `<N>`.
6. **Power down**, disconnect this servo, connect the next factory-fresh one, repeat.

After all servos are flashed: power down, connect the full daisy chain (or split across both ports if your bus board has two), power up, and run the full scan. You should see every assigned ID respond.

> **If you see a collision** (servos showing intermittently or missing): one of your servos is at the same ID as another. Disconnect the most recently added one and the original should reappear. See [Troubleshooting → Bus collision recovery](#bus-collision-recovery).

> **If you accidentally renamed the wrong servo** (very easy mistake): the script defaults to `--current-id 1`. If you ran it on a populated bus, the script targeted whichever servo was at ID 1 — often the wrong one. Recover by disconnecting all but the renamed servo, identifying its current ID with `scan.py`, then using `--current-id <wrong_id> --new-id <correct_id>` to rename it back.

### Phase 2 — Mount horns at the calibration reference position

For each servo, we want **encoder pos 2048** (the middle of the encoder's 0–4095 range) to correspond to a known physical pose — usually the midpoint of the joint's mechanical travel for a bounded joint, or "facing forward" for a continuous-rotation base joint.

This isn't pixel-perfect: STS3215 has a 25-tooth output spline (~14.4° between mountable horn positions), so you'll mount as close as the spline allows and absorb the remaining offset in software.

For each servo:

1. **Drive to encoder pos 2048** with torque holding:
   ```bash
   python3 scripts/set_pos.py --port /dev/ttyACM0 --id <N> --pos 2048
   ```
   The script keeps torque on after the move so the shaft stays put while you align the horn.

2. **Mount the horn** at the closest spline position to the desired physical neutral. For a bounded joint, eyeball/measure the midpoint between the two mechanical hard stops. For the base joint (continuous), pick a "facing forward" or "joint angle 0" orientation that matches your kinematic convention.

3. **Tighten the horn screw firmly** before releasing torque — a loose horn slips under load, shifting your calibration.

4. **Release torque**:
   ```bash
   python3 scripts/relax.py --id <N>
   ```

5. Optionally photograph each horn orientation for future reference.

> For an arm assembled around already-mounted servos, you can skip this phase if the horns are already at sensible positions — Phase 3 (range capture) and Phase 4 (correction) handle any offset in software.

### Phase 3 — Capture mechanical range per joint

With horns mounted and the arm assembled, capture each joint's mechanical limits by hand-rotating between its hard stops:

For each joint:

1. **Release torque** (so you can rotate by hand):
   ```bash
   python3 scripts/relax.py --id <N>
   ```

2. **Start the recorder**:
   ```bash
   python3 scripts/range_record.py --port /dev/ttyACM0 --id <N>
   ```

3. **Hand-rotate the joint deliberately**:
   - Slowly to one hard stop, pause for ~1 second
   - Slowly back through center to the other hard stop, pause for ~1 second
   - Slowly to center

4. **Press Ctrl+C** to print the summary.

The summary shows `min`, `max`, `range`, and `center` in encoder steps and degrees.

> **Continuous-rotation joints** (e.g., base joints with slip rings or no hard stops): the recorded "range" will be ~360° because the joint can spin freely. Note these as `type: continuous` in `calibration.yaml`, and define software soft limits (typically ±180° from your chosen zero) to prevent wire twist.

### Phase 4 — Fix encoder wraparound (when needed)

If `range_record.py` reports a range close to **360° (min near 0, max near 4095)** on a joint that **physically cannot rotate that much**, the joint's mechanical range is crossing the encoder's 0↔4095 boundary. The encoder counts up to 4095, wraps to 0, and continues — making the recording show the full 0–4095 span even though the actual physical travel is smaller.

The fix: shift the encoder's reading via the **Position Correction register** (EEPROM addr 31) so the joint's range fits cleanly within 0–4095.

For each affected joint:

1. **Hand-rotate the joint to its physical midpoint** between the two hard stops (by feel, no software needed).

2. **Run the correction**:
   ```bash
   python3 scripts/set_correction.py --port /dev/ttyACM0 --id <N> --target 2048
   ```
   This reads the current encoder value, computes the offset needed to make this pose read 2048, and writes it to EEPROM. You'll be prompted to confirm (type `y`).

3. **Re-run `range_record.py`** to verify a clean range:
   ```bash
   python3 scripts/range_record.py --port /dev/ttyACM0 --id <N>
   ```
   Should now show a sensible physical range (e.g. 1029–3059, ~178°) with `min` and `max` both well clear of 0 and 4095.

> **Critical rule**: only run `set_correction.py` when wraparound is *actually present*. If `range_record.py` already shows a clean range, do not run it — applying an unnecessary correction can create a wraparound where there wasn't one.

### Phase 5 — Save the calibration data

Update `calibration.yaml` with each joint's results. Template:

```yaml
port: /dev/ttyACM0
baud: 1000000

servos:
  - id: 1
    joint_name: base
    type: continuous           # or "bounded" for joints with hard stops
    encoder_min: 0             # for continuous, use full encoder range
    encoder_max: 4095
    encoder_center: 2048       # from range_record summary
    soft_min: 1024             # for continuous, set ±90° from center initially
    soft_max: 3072
    position_correction: 0     # if no correction was applied
    direction: 1               # +1 or -1, depending on URDF convention
    model: 777
    notes: continuous rotation; soft-limited to ±90° to avoid wire twist

  - id: 2
    joint_name: joint2
    type: bounded
    encoder_min: 902           # from range_record "min"
    encoder_max: 3280          # from range_record "max"
    encoder_center: 2091       # from range_record "center"
    soft_min: 952              # add 50-step margin from hard stops
    soft_max: 3230
    position_correction: -1937 # informational; actual value lives in servo EEPROM
    direction: 1
    model: 2825                # firmware variants exist; harmless
    notes: 209° range
```

The `soft_min` / `soft_max` values are what the GUI and ROS bridge use as bounds. Default to a ~50-step margin (~4°) inside the hard stops to prevent driving the joint into a physical stop under torque.

### Phase 6 — Verify with the GUI

```bash
python3 scripts/arm_gui.py
```

A window opens with one row per servo: live position display, slider bounded by soft limits, per-joint torque toggle, and global E-STOP. For each calibrated joint:

1. **Enable torque** via the checkbox
2. **Move the slider** slowly — the joint should smoothly track the slider value
3. **Watch the live position** — should match the slider value within a few steps
4. **Try the endpoints** of the slider — joint should reach near the soft limits without straining
5. **Hit E-STOP** at any point to release torque on all joints

If a joint strains, fights the slider, or refuses to move, see [Troubleshooting](#troubleshooting).

When you close the window, all torque is released automatically.

---

## Troubleshooting

### Port shuffling

The `/dev/ttyACM*` number can change between reboots (e.g., `ttyACM0` becomes `ttyACM2`). Permanent fix via a udev rule:

1. Find the board's USB IDs:
   ```bash
   udevadm info -a -n /dev/ttyACM0 | grep -E 'idVendor|idProduct' | head -4
   ```

2. Create `/etc/udev/rules.d/99-feetech.rules`:
   ```
   SUBSYSTEM=="tty", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", SYMLINK+="feetech-bus", MODE="0666"
   ```

3. Reload:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

Now `/dev/feetech-bus` always points to your board. Set `port: /dev/feetech-bus` in `calibration.yaml`.

### Bus collision recovery

If two servos end up at the same ID, neither will respond cleanly (both try to answer every ping → protocol corruption → timeout).

1. **Disconnect one of the colliding servos** physically — usually the one you most recently added.
2. **Scan the remaining bus**:
   ```bash
   python3 scripts/scan.py --port /dev/ttyACM0 --max-id 10
   ```
   The remaining servo should now respond at the disputed ID.
3. **Rename it** to its proper ID:
   ```bash
   python3 scripts/servo_id_setup.py --port /dev/ttyACM0 --current-id <wrong> --new-id <correct>
   ```
4. **Reconnect the other servo** alone on the bus (without the first one) and flash it to its correct ID.
5. **Reconnect everything**, scan again to verify.

### Voltage error (status byte = 1)

If `diag.py` reports `Status byte: 1 ['voltage']`, the servo's firmware detected over-voltage. Check the PSU output with a multimeter:

- Should read **12.0 V ± 0.3 V**
- 13 V or higher: dial down the supply (if adjustable) or replace it (if fixed). 14+ V will damage servos cumulatively.

### Joint strains / moves slowly

This happens when the servo is fighting a load it doesn't have enough torque for — common on base joints supporting the full arm mass. Distinguish from a faulty servo:

1. **Run `diag.py`** — verify Mode is 0 (position), torque limit is 1000/1000, status byte is 0 (no errors)
2. **Bench-test off the arm**: unbolt the servo and run `nudge.py` with no load
   - If it moves cleanly → arm load is the issue (mechanical, not the servo)
   - If it still strains → real servo issue (gear damage, low PSU current, voltage sag under load)

Common arm-load fixes: lighter end-effector, more PSU current capacity, mechanical advantage in design (gear reduction, counterbalance).

### "No response" on a known-good servo

- **Power cycle the 12 V supply** — servo firmware can hang
- **Verify the bus connection** — daisy-chain connectors are easy to dislodge
- **Try a different baud** with `scan.py` — defaults to 1 Mbaud but factory or modified servos may be different

---

## Script reference

| Script | Purpose | Modifies hardware? |
|---|---|---|
| `scan.py` | Sweep IDs at all common baud rates, list found servos | Read-only |
| `status.py` | Show position / voltage / temperature for given IDs | Read-only |
| `diag.py` | Full per-servo state snapshot | Read-only |
| `servo_id_setup.py` | Change a servo's bus ID (EEPROM write) | Yes — EEPROM |
| `set_pos.py` | Drive a servo to a target encoder position, keeps torque on | Yes — torque + motion |
| `nudge.py` | Small relative move from current position | Yes — torque + motion |
| `relax.py` | Disable torque on one or many servos | Yes — torque off |
| `range_record.py` | Disable torque, log min/max during hand rotation | Yes — torque off |
| `set_correction.py` | Write Position Correction register (EEPROM) to shift encoder readout | Yes — EEPROM |
| `arm_gui.py` | Interactive GUI for manual joint control within soft limits | Yes — torque + motion (user-controlled) |

All scripts accept `--port <device>` (default `/dev/ttyACM0`) and `--id <N>` where applicable. Run any with `--help` for full argument list.

---

## What's next

After calibration is complete and verified with the GUI:

1. **Build the URDF** from your CAD assembly (or the included `urdf/` files if cloning this repo)
2. **Build the ROS 2 bridge node** that translates between `sensor_msgs/JointState` topics and the Feetech bus, using `calibration.yaml` for per-joint scale/offset/limits
3. **Integrate with MoveIt** for motion planning
4. **Add perception** (e.g., RealSense + object detection) for vision-guided tasks

Each of these is covered in separate guides (`URDF.md`, `ROS2_BRIDGE.md`, `MOVEIT.md`, `PERCEPTION.md`). The calibration data you generated here flows through all of them.

---

## Open questions / known caveats

- **Continuous-rotation joints** need software multi-turn tracking if you want to count revolutions, or soft limits at ±180° to avoid wraparound during operation.
- **Position Correction values are informational in `calibration.yaml`** — the actual correction lives in servo EEPROM. Editing the YAML doesn't change the servo's behavior; use `set_correction.py` to update it.
- **Direction sign per joint** is left as `TBD` until the URDF is built — it depends on your kinematic frame conventions. Easily flipped later in `calibration.yaml`.
- **Motor mass for accurate dynamics**: STS3215 datasheet says ~60 g. For Gazebo simulation or dynamics-aware planning, override mass in your CAD before exporting the URDF; the raw STEP file usually computes wrong from solid-density math.
