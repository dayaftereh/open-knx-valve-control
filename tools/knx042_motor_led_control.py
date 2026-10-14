#!/usr/bin/env python3
"""KNX042 USB-only motor LED pulse diagnostic. NEVER with KNX/motors connected.

The diagnostic image refuses pulses unless its own ARM LEDS_ONLY command was
received. The CLI requires four independent physical preflight confirmations.
No test or probe command here can flash hardware or enable a KNX PHY.
"""
import argparse
import json
import sys
import time

USB_VID = 0x2E8A
USB_PID = 0x000A
READY_LINE = "KNX042 USB MOTOR-LED diagnostic"


def identify_port(ports, name: str, serial_number: str):
    for p in ports:
        if (p.device.upper() == name.upper() and p.vid == USB_VID and
                p.pid == USB_PID and
                (p.serial_number or "").upper() == serial_number.upper()):
            return p
    raise RuntimeError("RP2040 USB VID/PID, COM and serial mismatch: refusing")


def await_line(connection, startswith: str, seconds: float) -> str:
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        line = connection.readline().decode("ascii", "replace").strip()
        if line.startswith(startswith):
            return line
    raise RuntimeError("No USB diagnostic acknowledgment: " + startswith)


def send(connection, command: str, expected: str, seconds: float = 3.0):
    connection.write((command + "\n").encode("ascii"))
    connection.flush()
    return await_line(connection, expected, seconds)


def run(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["probe", "status", "pulse"])
    p.add_argument("--port", required=False, default="COM7")
    p.add_argument("--expect-serial", required=True)
    p.add_argument("--channel", type=int, choices=range(1, 9))
    p.add_argument("--direction", choices=["F", "R"])
    p.add_argument("--knx-disconnected", action="store_true")
    p.add_argument("--motors-unplugged", action="store_true")
    p.add_argument("--usb-only", action="store_true")
    p.add_argument("--leds-current-limited", action="store_true")
    args = p.parse_args(argv)
    from serial.tools import list_ports
    devices = list(list_ports.comports())
    found = identify_port(devices, args.port, args.expect_serial)
    if args.action == "probe":
        print(json.dumps({"port": found.device, "serial": found.serial_number,
                          "vidpid": "2E8A:000A", "opened": False}))
        return 0
    if args.action == "pulse":
        if args.channel is None or args.direction is None:
            p.error("pulse needs --channel 1..8 and --direction F|R")
        if not all((args.knx_disconnected, args.motors_unplugged,
                    args.usb_only, args.leds_current_limited)):
            p.error("pulse requires explicit confirmation of KNX disconnected, "
                    "motor absence, USB-only power and current-limited LEDs")
    import serial
    conn = serial.Serial()
    conn.port = found.device
    conn.baudrate = 115200
    conn.timeout = 0.15
    conn.write_timeout = 0.5
    conn.dtr = False
    conn.rts = False
    conn.open()
    try:
        conn.dtr = True
        ready = await_line(conn, READY_LINE, 10.5)
        if args.action == "status":
            status = send(conn, "STATUS", "KNX042 STATUS")
            print(json.dumps({"identity": ready, "status": status}))
            return 0
        # Always stop before requesting a new arming token.
        send(conn, "STOP", "KNX042 STOPPED")
        armed = send(conn, "ARM LEDS_ONLY", "KNX042 ARMED")
        pulse = send(conn, f"PULSE {args.channel} {args.direction}",
                     f"KNX042 PULSE M{args.channel} {args.direction}")
        stopped = await_line(conn, "KNX042 AUTO-STOP", 2.5)
        print(json.dumps({"identity": ready, "armed": armed,
                          "pulse": pulse, "stopped": stopped}))
        return 0
    finally:
        # Attempt safe disarm on every error path. No blind command if
        # identity hasn't been established by a matching USB diagnostic.
        try:
            if 'ready' in locals():
                conn.write(b"STOP\n")
                conn.flush()
        finally:
            conn.dtr = False
            conn.close()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (RuntimeError, OSError) as exc:
        print("KNX042 REFUSED: " + str(exc), file=sys.stderr)
        sys.exit(2)
