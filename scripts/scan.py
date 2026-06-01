#!/usr/bin/env python3
"""Scan all common baud rates and IDs to find connected Feetech servos."""
import argparse
from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

BAUDS = [1000000, 500000, 250000, 128000, 115200, 57600]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--max-id", type=int, default=20)
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")

    found = False
    for baud in BAUDS:
        port.setBaudRate(baud)
        print(f"-- baud {baud} --")
        for sid in range(1, args.max_id + 1):
            model, comm, err = pkt.ping(port, sid)
            if comm == COMM_SUCCESS:
                print(f"   FOUND servo ID={sid}, model={model}")
                found = True
    port.closePort()
    if not found:
        print("\nNo servos found at any baud. Check 12V power and bus wiring.")


if __name__ == "__main__":
    main()
