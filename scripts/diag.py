#!/usr/bin/env python3
"""Read-only diagnostic snapshot for a Feetech STS servo. No movement.

Usage:
    python3 diag.py --port /dev/ttyACM0 --id 1
"""
import argparse

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

# EEPROM
ADDR_MODE = 33
ADDR_MIN_ANGLE = 9
ADDR_MAX_ANGLE = 11
ADDR_MAX_TORQUE = 16
# SRAM
ADDR_TORQUE_ENABLE = 40
ADDR_ACC = 41
ADDR_GOAL_POSITION = 42
ADDR_GOAL_SPEED = 46
ADDR_TORQUE_LIMIT = 48
ADDR_PRESENT_POSITION = 56
ADDR_PRESENT_SPEED = 58
ADDR_PRESENT_LOAD = 60
ADDR_PRESENT_VOLTAGE = 62
ADDR_PRESENT_TEMP = 63
ADDR_STATUS = 65
ADDR_MOVING = 66
ADDR_PRESENT_CURRENT = 69

MODE_NAMES = {0: "position/servo", 1: "wheel/continuous", 2: "PWM", 3: "step"}


def signed10(v):
    """Feetech load/speed: bit 10 = sign, bits 0-9 = magnitude."""
    mag = v & 0x3FF
    return -mag if (v & 0x400) else mag


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

    def r1(addr):
        v, comm, _ = pkt.read1ByteTxRx(port, args.id, addr)
        return v if comm == COMM_SUCCESS else None

    def r2(addr):
        v, comm, _ = pkt.read2ByteTxRx(port, args.id, addr)
        return v if comm == COMM_SUCCESS else None

    if pkt.ping(port, args.id)[1] != COMM_SUCCESS:
        port.closePort()
        raise SystemExit(f"no response from ID={args.id}")

    print(f"=== Servo ID={args.id} ===")
    mode = r1(ADDR_MODE)
    print(f"  Operating mode  : {mode}  ({MODE_NAMES.get(mode, '?')})")
    lo, hi = r2(ADDR_MIN_ANGLE), r2(ADDR_MAX_ANGLE)
    print(f"  Angle limits    : min={lo}  max={hi}"
          + ("   <-- both 0 = wheel mode!" if lo == 0 and hi == 0 else ""))
    print(f"  Max torque      : {r2(ADDR_MAX_TORQUE)}  (0-1000)")
    print(f"  Torque limit    : {r2(ADDR_TORQUE_LIMIT)}  (runtime, 0-1000)")
    print(f"  Torque enable   : {r1(ADDR_TORQUE_ENABLE)}")
    print(f"  Acceleration    : {r1(ADDR_ACC)}")
    print(f"  Goal position   : {r2(ADDR_GOAL_POSITION)}")
    print(f"  Goal speed      : {r2(ADDR_GOAL_SPEED)}")
    print(f"  Present position: {r2(ADDR_PRESENT_POSITION)}")
    print(f"  Present speed   : {signed10(r2(ADDR_PRESENT_SPEED) or 0)}")
    print(f"  Present load    : {signed10(r2(ADDR_PRESENT_LOAD) or 0)}  (0-1000)")
    print(f"  Present current : {r2(ADDR_PRESENT_CURRENT)}  (~6.5 mA/unit)")
    print(f"  Voltage         : {(r1(ADDR_PRESENT_VOLTAGE) or 0)/10:.1f} V")
    print(f"  Temperature     : {r1(ADDR_PRESENT_TEMP)} C")
    print(f"  Moving flag     : {r1(ADDR_MOVING)}")
    status = r1(ADDR_STATUS)
    bits = []
    if status:
        if status & 0x01: bits.append("voltage")
        if status & 0x02: bits.append("sensor/angle")
        if status & 0x04: bits.append("overheat")
        if status & 0x08: bits.append("overcurrent")
        if status & 0x20: bits.append("overload")
    print(f"  Status byte     : {status}  {bits if bits else '(no errors)'}")

    port.closePort()


if __name__ == "__main__":
    main()
