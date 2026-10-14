#!/usr/bin/env python3
"""Start/inspect/stop the isolated KNX042 8-motor LED-sequence firmware.

ONLY for a physically USB-powered board with KNX bus and actual motor loads
disconnected. The flash image is deliberately inert at boot. This program
cannot flash firmware. Sequence must be explicitly armed and started once.
"""
import argparse
from datetime import datetime
import json
import sys

import knx042_motor_led_control as usb

READY = "KNX042 LED SEQUENCE READY"
STARTED = "KNX042 SEQ START rounds=5 on_ms=1000 off_ms=1000"
ROUNDS = 5
ON_MS = 1000
OFF_MS = 1000


def run(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("probe", "start", "status", "stop"))
    cli.add_argument("--port", default="COM7")
    cli.add_argument("--expect-serial", required=True)
    cli.add_argument("--knx-disconnected", action="store_true")
    cli.add_argument("--motors-unplugged", action="store_true")
    cli.add_argument("--usb-only", action="store_true")
    cli.add_argument("--leds-current-limited", action="store_true")
    args = cli.parse_args(argv)

    if args.action == "start" and not all((
        args.knx_disconnected,
        args.motors_unplugged,
        args.usb_only,
        args.leds_current_limited,
    )):
        cli.error("start requires explicit KNX disconnected, motors unplugged, "
                  "USB-only power, current-limited onboard LEDs confirmations")

    from serial.tools import list_ports
    device = usb.identify_port(list(list_ports.comports()),
                               args.port, args.expect_serial)
    if args.action == "probe":
        print(json.dumps({"device":device.device, "serial":device.serial_number,
                          "vidpid":"2E8A:000A", "opened":False}))
        return 0

    import serial
    conn = serial.Serial()
    conn.port = device.device
    conn.baudrate = 115200
    conn.timeout = 0.15
    conn.write_timeout = 0.5
    conn.dtr = False
    conn.rts = False
    recognized = False
    started = False
    conn.open()
    try:
        conn.dtr = True
        banner = usb.await_line(conn, READY, 10.5)
        recognized = True
        if args.action == "status":
            status = usb.send(conn, "STATUS", "KNX042 STATUS")
            print(json.dumps({"device":device.device, "status":status,
                              "observation":"internal firmware state only"}))
            return 0
        if args.action == "stop":
            stopped = usb.send(conn, "STOP", "KNX042 SEQ STOPPED")
            state = usb.send(conn, "STATUS", "KNX042 STATUS")
            print(json.dumps({"device":device.device, "stop":stopped, "status":state}))
            return 0

        # START never interrupts an already running sequence.
        state = usb.send(conn, "STATUS", "KNX042 STATUS")
        if "seq=0" not in state or "active=0" not in state:
            raise RuntimeError("Refusing to interrupt already active sequence: "+state)
        armed = usb.send(conn, "ARM LEDS_ONLY", "KNX042 ARMED 15s")
        ack = usb.send(conn, "START ALL 5", STARTED)
        started = True
        print(json.dumps({
            "device":device.device,
            "serial":device.serial_number,
            "started_at_local":datetime.now().astimezone().isoformat(timespec="seconds"),
            "armed_ack":armed,
            "start_ack":ack,
            "rounds":ROUNDS,
            "order":"M1 CLOSE, M1 OPEN, ..., M8 CLOSE, M8 OPEN",
            "on_ms":ON_MS,
            "off_ms":OFF_MS,
            "nominal_total_seconds": ROUNDS * 8 * 2 * (ON_MS+OFF_MS)//1000,
            "maximum_software_run_seconds":180,
            "autostart_after_boot":False,
            "motor_connected":False,
            "knx_connected":False
        },indent=2))
        return 0
    finally:
        # Never do anything on read-only STATUS. On an aborted START only,
        # deliberately stop outputs from a verified sequence firmware.
        try:
            if args.action == "start" and recognized and not started:
                conn.write(b"STOP\n")
                conn.flush()
        finally:
            conn.dtr = False
            conn.close()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (RuntimeError, OSError) as exc:
        print("KNX042 LED-SEQUENCE REFUSED: "+str(exc),file=sys.stderr)
        sys.exit(2)
