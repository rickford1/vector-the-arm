#!/usr/bin/env python3
"""Drive a single STS servo to a target position and HOLD with torque on.

For calibration: drive the output shaft to a known reference value (e.g.
2048 = mid-range) so you can mount the horn at the desired joint zero.

After mounting the horn, run:  python3 relax.py --id <N>

Usage:
    python3 set_pos.py --port /dev/ttyACM0 --id 1 --pos 2048
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


def read_pos(pkt, port, sid):
    v, comm, _ = pkt.read2ByteTxRx(port, sid, ADDR_PRESENT_POSITION)
    return v if comm == COMM_SUCCESS else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--pos", type=int, default=2048, help="target position 0-4095 (default 2048 = center)")
    ap.add_argument("--speed", type=int, default=300, help="steps/s, gentle")
    ap.add_argument("--acc", type=int, default=15)
    args = ap.parse_args()

    if not 0 <= args.pos <= 4095:
        raise SystemExit("--pos must be 0-4095")

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    start = read_pos(pkt, port, args.id)
    delta = args.pos - start
    print(f"ID={args.id}: current={start} ({start/STEPS_PER_DEG:.1f} deg) "
          f"-> target={args.pos} ({args.pos/STEPS_PER_DEG:.1f} deg) "
          f"[delta {delta:+d}, {delta/STEPS_PER_DEG:+.1f} deg]")

    pkt.write1ByteTxRx(port, args.id, ADDR_GOAL_ACC, args.acc)
    pkt.write2ByteTxRx(port, args.id, ADDR_GOAL_SPEED, args.speed)
    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 1)
    pkt.write2ByteTxRx(port, args.id, ADDR_GOAL_POSITION, args.pos)

    last, t0 = None, time.time()
    while time.time() - t0 < 10.0:
        time.sleep(0.15)
        pos = read_pos(pkt, port, args.id)
        if pos is None:
            continue
        if abs(pos - args.pos) <= 10:
            break
        if last is not None and abs(pos - last) <= 1:
            break
        last = pos

    pos = read_pos(pkt, port, args.id)
    print(f"  arrived at {pos}  (err={pos - args.pos:+d})")
    print("  TORQUE STILL ON -- servo is holding position.")
    print(f"  Mount horn now, then run:  python3 relax.py --id {args.id}")

    port.closePort()


if __name__ == "__main__":
    main()
