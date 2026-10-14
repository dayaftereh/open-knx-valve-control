#!/usr/bin/env python3
"""Isolated KNX042 motor enable and common-direction LED blink (NO KNX bus or motors).

This helper uses the *already installed* firmware's time-bounded 400 ms
forward/reverse pulses and never asks for a continuous hold or new firmware.
100 pulses at 400ms on/200ms off give ~60 seconds for visible channel LED + OPEN or CLOSE blinking.
"""
import argparse
from datetime import datetime
import json
import sys
import time

import knx042_motor_led_control as host

MAX_CYCLES = 120
INTER_PULSE_PAUSE_S = 0.20


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--channel", type=int, required=True, choices=range(1, 9))
    parser.add_argument("--direction", choices=("F", "R"), required=True)
    for flag in ("knx-disconnected", "motors-unplugged", "usb-only",
                 "leds-current-limited"):
        parser.add_argument("--" + flag, action="store_true")
    args = parser.parse_args(argv)
    pulse_command = f"PULSE {args.channel} {args.direction}"
    pulse_ack = f"KNX042 PULSE M{args.channel} {args.direction} 400ms"
    if args.cycles < 1 or args.cycles > MAX_CYCLES:
        parser.error("cycles must be in 1..120 (400ms maximum each)")
    if not all((args.knx_disconnected, args.motors_unplugged, args.usb_only,
                args.leds_current_limited)):
        parser.error("Must verify: KNX disconnected, motors unplugged, USB only, "
                     "current-limited onboard LEDs")

    from serial.tools import list_ports
    device = host.identify_port(list(list_ports.comports()),
                                args.port, args.expect_serial)
    import serial
    conn = serial.Serial()
    conn.port = device.device
    conn.baudrate = 115200
    conn.timeout = 0.15
    conn.write_timeout = 0.5
    conn.dtr = False
    conn.rts = False
    verified = False
    successful = 0
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    conn.open()
    try:
        conn.dtr = True
        banner = host.await_line(conn, host.READY_LINE, 10.5)
        verified = True
        host.send(conn, "STOP", "KNX042 STOPPED")
        status = host.send(conn, "STATUS", "KNX042 STATUS")
        if "armed=0 active=0" not in status:
            raise RuntimeError("Output not off before LED test: " + status)
        for _ in range(args.cycles):
            host.send(conn, "ARM LEDS_ONLY", "KNX042 ARMED")
            host.send(conn, pulse_command, pulse_ack)
            host.await_line(conn, "KNX042 AUTO-STOP", 2.5)
            successful += 1
            time.sleep(INTER_PULSE_PAUSE_S)
        host.send(conn, "STOP", "KNX042 STOPPED")
        result = host.send(conn, "STATUS", "KNX042 STATUS")
        if "armed=0 active=0" not in result:
            raise RuntimeError("Output not off after LED test: " + result)
        print(json.dumps({
            "result": "PASS",
            "started_local": started,
            "ended_local": datetime.now().astimezone().isoformat(timespec="seconds"),
            "device": device.device,
            "serial": device.serial_number,
            "command": pulse_command,
            "pulses_completed": successful,
            "maximum_per_pulse_ms": 400,
            "off_gap_nominal_ms": 200,
            "initial_state": status,
            "final_state": result,
            "terminal_voltage_measured": False,
            "physical_led_observation": "PENDING_USER"
        }, indent=2))
        return 0
    finally:
        # Fail shut on errors/interrupts. NEVER transmit to an unverified device.
        try:
            if verified:
                conn.write(b"STOP\n")
                conn.flush()
        finally:
            conn.dtr = False
            conn.close()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (RuntimeError, OSError) as exc:
        print("KNX042 MOTOR LED TEST REFUSED: " + str(exc), file=sys.stderr)
        sys.exit(2)
