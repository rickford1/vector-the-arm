#!/usr/bin/env python3
"""Small relative movement test for one Feetech STS servo.

Reads the servo's current position, nudges it a few degrees, confirms it
tracked, then returns it to where it started. Safe for unsecured servos.

Usage:
    python3 nudge.py --port /dev/ttyACM0 --id 1 --deg 20
"""
import argparse
import time

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_ACC = 41
ADDR_GOAL_POSITION = 42
ADDR_GOAL_SPEED = 46
ADDR_PRESENT_POSITION = 56

STEPS_PER_DEG = 4096.0 / 360.0
POS_MIN, POS_MAX = 30, 4065   # stay clear of hard limits
SPEED = 400                    # gentle
ACC = 20


def read_pos(pkt, port, sid):
    pos, comm, err = pkt.read2ByteTxRx(port, sid, ADDR_PRESENT_POSITION)
    return pos if comm == COMM_SUCCESS else None


def move_to(pkt, port, sid, target, tol=15, timeout=5.0):
    pkt.write2ByteTxRx(port, sid, ADDR_GOAL_POSITION, target)
    start, last = time.time(), None
    pos = None
    while time.time() - start < timeout:
        time.sleep(0.15)
        pos = read_pos(pkt, port, sid)
        if pos is None:
            continue
        if abs(pos - target) <= tol:
            break
        if last is not None and abs(pos - last) <= 1:
            break
        last = pos
    return pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--deg", type=float, default=20.0,
                    help="degrees to nudge; negative = other direction")
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    start = read_pos(pkt, port, args.id)
    delta = int(args.deg * STEPS_PER_DEG)
    # honor the sign of --deg; you pick the mechanically-free direction
    target = max(POS_MIN, min(POS_MAX, start + delta))
    actual_deg = (target - start) / STEPS_PER_DEG
    if abs((target - start) - delta) > 2:
        print(f"  WARNING: clipped to electronic limit -- only {actual_deg:.1f} deg of room")
    print(f"ID={args.id}: start={start} ({start/STEPS_PER_DEG:.1f} deg), "
          f"nudging {actual_deg:+.1f} deg to {target} ({target/STEPS_PER_DEG:.1f} deg)")

    pkt.write1ByteTxRx(port, args.id, ADDR_GOAL_ACC, ACC)
    pkt.write2ByteTxRx(port, args.id, ADDR_GOAL_SPEED, SPEED)
    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 1)

    pos = move_to(pkt, port, args.id, target)
    print(f"  reached {pos}  (err={pos - target:+d})")

    pos = move_to(pkt, port, args.id, start)
    print(f"  returned {pos}  (err={pos - start:+d})")

    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 0)
    port.closePort()
    print("Done -- torque released.")


if __name__ == "__main__":
    main()
