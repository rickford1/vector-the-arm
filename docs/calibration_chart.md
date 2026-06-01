# Servo Calibration

Reference pos: `2048` (encoder midpoint) for all servos.
Bus: `/dev/ttyACM0`, baud `1000000`, protocol STS.

## Per-servo calibration

| ID | Joint | Model | Range type | Mounted at | Min (steps) | Max (steps) | Range (steps) | Range (deg) | Mech midpoint (steps) | Offset from 2048 | Direction | Notes |
|----|-------|-------|------------|------------|-------------|-------------|---------------|-------------|------------------------|-------------------|-----------|-------|
| 1  | base       | 777  | continuous | 2048 | n/a         | n/a         | n/a           | n/a         | 2044 (centered)        | -4                | TBD       | **continuous rotation — no hard stops**. Horn well-centered (offset -4). Need software multi-turn tracking or soft limits at e.g. ±180° from 2048. |
| 2  | (joint?)   | 2825 | 209° | 2048 | 902         | 3280        | 2378          | 209.0       | 2091                   | +43               | TBD       | model 2825 variant. Position Correction set via set_correction.py; raw was crossing 0/4095 boundary |
| 3  | (joint?)   | 777  | 183° | 2048 | 981         | 3064        | 2083          | 183.1       | 2022                   | -26               | TBD       | recalibrated post-reassembly; existing Position Correction retained; clean range |
| 4  | joint4     | 777  | 178° | 2048 | 1029        | 3059        | 2030          | 178.4       | 2044                   | -4                | TBD       | additional arm joint; clean range, Position Correction set |
| 5  | wrist_roll | 777  | TBD  | TBD  | ---         | ---         | ---           | ---         | ---                    | ---               | TBD       | new servo, ID flashed; bare on bench; calibrate when wrist roll module is built |
| 6  | gripper    | TBD  | TBD  | TBD  | ---         | ---         | ---           | ---         | ---                    | ---               | TBD       | not yet purchased; will be 6th servo |

## Field meanings

- **Mounted at**: encoder pos the horn was aligned at during calibration (always 2048 here)
- **Min / Max (steps)**: encoder values at each mechanical hard stop, captured via `range_record.py`
- **Range (steps)**: max − min
- **Range (deg)**: range × (360 / 4096)
- **Mech midpoint (steps)**: (min + max) / 2 — the true physical midpoint, in encoder steps
- **Offset from 2048**: mech_midpoint − 2048 — how far the actual midpoint sits from the nominal reference. Goes into the per-joint software calibration as `encoder_zero`.
- **Direction**: +1 or -1 — sign of joint angle relative to increasing encoder position (decide per joint based on your URDF / right-hand-rule convention)

## Verification notes per servo

- **ID 1** — comms OK (model 777), bench-test clean unloaded. Strained when mounted under arm load (expected for base joint).
- **ID 2** — comms OK (model **2825** — variant), nudge ±17° clean (err -3 / +0).
- **ID 3** — comms OK (model 777), motion test deferred (was electrically pinned near top of range, only ~1° of room in mechanically-free direction).
- **ID 4** — comms OK (model 777), nudge -20° clean (err +15 / -1).
