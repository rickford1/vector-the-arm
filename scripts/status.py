#!/usr/bin/env python3
"""Read-only status check for Feetech STS servos -- no movement."""
import argparse

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_PRESENT_POSITION = 56   # 2 bytes
ADDR_PRESENT_VOLTAGE = 62    # 1 byte, units of 0.1 V
ADDR_PRESENT_TEMP = 63       # 1 byte, degrees C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--ids", default="1,2,3,4")
    args = ap.parse_args()

    port = PortHandler(args.port)
    pkt = PacketHandler(0)
    if not port.openPort():
        raise SystemExit(f"could not open {args.port}")
    port.setBaudRate(1000000)

    print(f"{'ID':>3}  {'pos':>5}  {'deg':>6}  {'volt':>5}  {'temp':>5}")
    for sid in (int(x) for x in args.ids.split(",")):
        pos, comm, err = pkt.read2ByteTxRx(port, sid, ADDR_PRESENT_POSITION)
        if comm != COMM_SUCCESS:
            print(f"{sid:>3}  -- no response --")
            continue
        volt, _, _ = pkt.read1ByteTxRx(port, sid, ADDR_PRESENT_VOLTAGE)
        temp, _, _ = pkt.read1ByteTxRx(port, sid, ADDR_PRESENT_TEMP)
        deg = pos * 360.0 / 4096.0
        print(f"{sid:>3}  {pos:>5}  {deg:>6.1f}  {volt/10:>4.1f}V  {temp:>4d}C")

    port.closePort()


if __name__ == "__main__":
    main()
