#!/usr/bin/env python3
"""Set the runtime Torque Limit (addr 48) on a Feetech STS servo, 0-1000.

Caps how hard the servo can push -- use it to limit gripper grip force so it
can't crush what it grabs. This is a runtime (SRAM) value: it resets to the
servo's Max Torque (EEPROM addr 16) on power cycle, so set it each session
(or have the ROS bridge / GUI set it on startup).

Usage:
    python3 set_torque_limit.py --port /dev/ttyACM0 --id 6 --limit 300
    python3 set_torque_limit.py --port /dev/ttyACM0 --id 6 --read
"""
import argparse

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_TORQUE_LIMIT = 48   # 2 bytes, 0-1000, runtime (SRAM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--id", type=int, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--limit", type=int, help="torque limit 0-1000 (lower = gentler)")
    g.add_argument("--read", action="store_true", help="just read the current limit")
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    if args.read:
        val, _, _ = pkt.read2ByteTxRx(port, args.id, ADDR_TORQUE_LIMIT)
        print(f"ID={args.id}: torque limit = {val}  (0-1000)")
        port.closePort()
        return

    limit = max(0, min(1000, args.limit))
    pkt.write2ByteTxRx(port, args.id, ADDR_TORQUE_LIMIT, limit)
    val, _, _ = pkt.read2ByteTxRx(port, args.id, ADDR_TORQUE_LIMIT)
    print(f"ID={args.id}: torque limit set to {val}  (0-1000)  [runtime; resets on power cycle]")
    port.closePort()


if __name__ == "__main__":
    main()
