#!/usr/bin/env python3
"""One-shot Feetech STS servo ID configurator.

Connect ONE servo at a time, then run:
    python servo_id_setup.py --new-id 2

All factory-new servos default to ID=1 at 1Mbaud. This script:
  1. Pings the servo at its current ID to confirm comms.
  2. Unlocks EEPROM, writes the new ID, re-locks.
  3. Pings the new ID to verify the change persisted.
"""
import argparse
import sys
import time

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_ID = 5        # EEPROM address: servo ID (1 byte)
ADDR_LOCK = 55     # EEPROM address: lock flag (0=unlocked, 1=locked)
DEFAULT_BAUD = 1000000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--current-id", type=int, default=1,
                    help="ID the servo currently has (default: 1, factory)")
    ap.add_argument("--new-id", type=int, required=True,
                    help="ID to assign (1-253)")
    args = ap.parse_args()

    if not 1 <= args.new_id <= 253:
        sys.exit("new-id must be 1-253")

    port = PortHandler(args.port)
    pkt = PacketHandler(0)  # 0 = STS (little-endian); 1 = SCS (big-endian)
    if not port.openPort():
        sys.exit(f"could not open {args.port}")
    port.setBaudRate(args.baud)

    print(f"Pinging ID={args.current_id} at {args.baud} baud...")
    model, comm, err = pkt.ping(port, args.current_id)
    if comm != COMM_SUCCESS:
        port.closePort()
        sys.exit(f"no response from ID={args.current_id} (comm={comm}, err={err})")
    print(f"  found servo, model={model}")

    if args.new_id == args.current_id:
        print("new-id == current-id, nothing to do")
        port.closePort()
        return

    print(f"Writing ID {args.current_id} -> {args.new_id}...")
    pkt.write1ByteTxRx(port, args.current_id, ADDR_LOCK, 0)     # unlock EEPROM
    pkt.write1ByteTxRx(port, args.current_id, ADDR_ID, args.new_id)
    pkt.write1ByteTxRx(port, args.new_id, ADDR_LOCK, 1)         # re-lock (with NEW id)
    time.sleep(0.1)

    print(f"Verifying new ID={args.new_id}...")
    model, comm, err = pkt.ping(port, args.new_id)
    port.closePort()
    if comm == COMM_SUCCESS:
        print(f"  ok -- servo responds at ID={args.new_id}")
    else:
        sys.exit("  FAILED -- power cycle and re-ping manually")


if __name__ == "__main__":
    main()