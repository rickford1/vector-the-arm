#!/usr/bin/env python3
"""Record the mechanical travel range of a joint by hand-rotating it.

Disables torque on the servo, then continuously reads the present position
while you manually move the joint through its full range. Prints live
min/max and final summary when you press Ctrl+C.

Usage:
    python3 range_record.py --port /dev/ttyACM0 --id 1
"""
import argparse
import time

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_ENABLE = 40
ADDR_PRESENT_POSITION = 56

STEPS_PER_DEG = 4096.0 / 360.0


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

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    # release torque so the user can hand-rotate
    pkt.write1ByteTxRx(port, args.id, ADDR_TORQUE_ENABLE, 0)
    print(f"ID={args.id}: torque OFF.  Move the joint through its full range.")
    print("Press Ctrl+C when done.\n")

    pos, _, _ = pkt.read2ByteTxRx(port, args.id, ADDR_PRESENT_POSITION)
    lo = hi = pos
    try:
        while True:
            time.sleep(0.05)
            p, comm, _ = pkt.read2ByteTxRx(port, args.id, ADDR_PRESENT_POSITION)
            if comm != COMM_SUCCESS:
                continue
            lo = min(lo, p)
            hi = max(hi, p)
            print(f"\r  current={p:>5}  min={lo:>5}  max={hi:>5}  "
                  f"range={hi - lo:>5} steps  ({(hi - lo)/STEPS_PER_DEG:>5.1f} deg)   ",
                  end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n=== Summary ===")
        print(f"  ID         : {args.id}")
        print(f"  min        : {lo}  ({lo/STEPS_PER_DEG:.1f} deg)")
        print(f"  max        : {hi}  ({hi/STEPS_PER_DEG:.1f} deg)")
        print(f"  range      : {hi - lo} steps  ({(hi - lo)/STEPS_PER_DEG:.1f} deg)")
        print(f"  center     : {(lo + hi) // 2}")
        if lo == hi:
            print("  (no movement detected -- did torque actually release?)")
    finally:
        port.closePort()


if __name__ == "__main__":
    main()
