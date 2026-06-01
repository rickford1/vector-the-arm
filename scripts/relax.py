#!/usr/bin/env python3
"""Release torque on one or all Feetech STS servos.

Usage:
    python3 relax.py --id 1            # release a single servo
    python3 relax.py --ids 1,2,3,4     # release multiple
"""
import argparse

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_ENABLE = 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", type=int)
    g.add_argument("--ids", help="comma-separated list, e.g. 1,2,3,4")
    args = ap.parse_args()

    ids = [args.id] if args.id is not None else [int(x) for x in args.ids.split(",")]

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    for sid in ids:
        comm, _ = pkt.write1ByteTxRx(port, sid, ADDR_TORQUE_ENABLE, 0)
        print(f"  ID={sid}: {'relaxed' if comm == COMM_SUCCESS else 'NO RESPONSE'}")

    port.closePort()


if __name__ == "__main__":
    main()
