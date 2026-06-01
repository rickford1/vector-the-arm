#!/usr/bin/env python3
"""Set the STS Position Correction register (addr 31) so the joint's current
physical pose reads as a chosen target encoder value.

Use to shift the encoder zero away from the joint's mechanical range when
the joint's travel crosses the 0/4095 boundary.

Workflow:
  1. With torque OFF, hand-rotate the joint to its physical midpoint
     (between the two hard stops, by feel).
  2. python3 set_correction.py --port /dev/ttyACM0 --id 2 --target 2048
  3. Verify with diag.py and re-run range_record.py.

Usage:
    python3 set_correction.py --port /dev/ttyACM0 --id 2 --target 2048
    python3 set_correction.py --port /dev/ttyACM0 --id 2 --read   # just show current correction
    python3 set_correction.py --port /dev/ttyACM0 --id 2 --clear  # zero the correction
"""
import argparse
import time

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_POSITION_CORRECTION = 31  # 2 bytes, signed
ADDR_LOCK = 55
ADDR_TORQUE_ENABLE = 40
ADDR_PRESENT_POSITION = 56


def s16(v):
    """Convert raw 2-byte read to signed 16-bit."""
    return v - 65536 if v & 0x8000 else v


def u16(v):
    """Convert signed int to raw 2-byte unsigned for writing."""
    return v + 65536 if v < 0 else v


def read_pos(pkt, port, sid):
    v, comm, _ = pkt.read2ByteTxRx(port, sid, ADDR_PRESENT_POSITION)
    return v if comm == COMM_SUCCESS else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", type=int, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--target", type=int, help="target encoder value for current physical pose (0-4095)")
    g.add_argument("--read", action="store_true", help="just read current correction value")
    g.add_argument("--clear", action="store_true", help="zero the correction register")
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    # read current correction
    raw, comm, _ = pkt.read2ByteTxRx(port, args.id, ADDR_POSITION_CORRECTION)
    current_corr = s16(raw)
    print(f"ID={args.id}: current Position Correction = {current_corr}")

    if args.read:
        port.closePort()
        return

    if args.clear:
        new_corr = 0
        print("Clearing correction (writing 0)...")
    else:
        current_pos = read_pos(pkt, port, args.id)
        delta = args.target - current_pos
        new_corr = current_corr - delta
        print(f"Current displayed position : {current_pos}")
        print(f"Target displayed position  : {args.target}")
        print(f"Delta needed               : {delta:+d}")
        print(f"New correction value       : {new_corr}")
        print()
        print("WARNING: this writes to EEPROM and persists.")
        confirm = input("Proceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("aborted")
            port.closePort()
            return

    # ensure torque off before correction change
    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 0)
    # unlock EEPROM
    pkt.write1ByteTxRx(port, args.id, ADDR_LOCK, 0)
    # write correction
    pkt.write2ByteTxRx(port, args.id, ADDR_POSITION_CORRECTION, u16(new_corr))
    # relock
    pkt.write1ByteTxRx(port, args.id, ADDR_LOCK, 1)
    time.sleep(0.1)

    # verify (retry -- read right after EEPROM lock can short-read)
    raw = None
    for _ in range(5):
        time.sleep(0.1)
        try:
            raw, comm, _ = pkt.read2ByteTxRx(port, args.id, ADDR_POSITION_CORRECTION)
            if comm == COMM_SUCCESS:
                break
        except IndexError:
            continue
    if raw is not None:
        print(f"\nReadback correction: {s16(raw)}")
    else:
        print("\nReadback failed (write probably still landed). Run diag.py to check.")
    pos = read_pos(pkt, port, args.id)
    if pos is not None:
        print(f"Present position now: {pos}")
    print("If displayed position doesn't match target, the sign convention may be")
    print("opposite for your firmware -- re-run with the same target to converge.")

    port.closePort()


if __name__ == "__main__":
    main()
