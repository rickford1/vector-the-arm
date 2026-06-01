#!/usr/bin/env python3
"""Gentle movement test for a single Feetech STS servo.

Enables torque, sweeps the servo a small amount around center, and reads
back the position so you can confirm the motor + encoder both work.

Usage:
    python3 move_test.py --port /dev/ttyACM0 --id 1
"""
import argparse
import time

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_ACC = 41      # acceleration, units of 100 steps/s^2
ADDR_GOAL_POSITION = 42  # 2 bytes, 0-4095
ADDR_GOAL_SPEED = 46     # 2 bytes, steps/s
ADDR_PRESENT_POSITION = 56  # 2 bytes

CENTER = 2048
SWING = 400          # +/- steps around center (~35 deg)
SPEED = 600          # steps/s -- gentle
ACC = 30             # gentle acceleration


def move_to(pkt, port, sid, target, tol=15, timeout=6.0):
    """Command a move, then poll position until it arrives or stalls."""
    pkt.write2ByteTxRx(port, sid, ADDR_GOAL_POSITION, target)
    start = time.time()
    last = None
    while time.time() - start < timeout:
        time.sleep(0.15)
        pos, comm, err = pkt.read2ByteTxRx(port, sid, ADDR_PRESENT_POSITION)
        if comm != COMM_SUCCESS:
            continue
        if abs(pos - target) <= tol:
            break
        if last is not None and abs(pos - last) <= 1:
            break  # stopped moving (stalled or blocked)
        last = pos
    print(f"  target={target:4d}  ->  present={pos:4d}  (err={pos - target:+d})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", type=int, required=True)
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    model, comm, err = pkt.ping(port, args.id)
    if comm != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")
    print(f"Testing servo ID={args.id}, model={model}")

    pkt.write1ByteTxRx(port, args.id, ADDR_GOAL_ACC, ACC)
    pkt.write2ByteTxRx(port, args.id, ADDR_GOAL_SPEED, SPEED)
    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 1)

    print("Sweeping...")
    move_to(pkt, port, args.id, CENTER)
    move_to(pkt, port, args.id, CENTER - SWING)
    move_to(pkt, port, args.id, CENTER + SWING)
    move_to(pkt, port, args.id, CENTER)

    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 0)  # relax
    port.closePort()
    print("Done -- torque released.")


if __name__ == "__main__":
    main()