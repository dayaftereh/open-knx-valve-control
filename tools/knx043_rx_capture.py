#!/usr/bin/env python3
"""KNX043 STKNX RX-only USB capture. Not a KNX transmitter or ETS programmer.

USB commands are only: STATUS, STOP, ARM LISTEN_ONLY, START LISTEN.
KNX_RX edge capture is only appropriate after physical safety review:
R17 removed, U9/U11 electrical hazard resolved, reset/brownout TX LOW
measured, rail/backfeed protected, isolated KNX bench supply/interface.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import knx042_motor_led_control as usb
import knx043_home_knx_preflight as preflight

READY = "KNX043 PASSIVE RX READY"
START_ACK = "KNX043 LISTENING RX_ONLY 120s TX_LOW"
ARM_ACK = "KNX043 ARMED LISTEN_ONLY 15s TX_LOW"
EDGE = re.compile(r"^KNX043 RX_EDGE time_us=(\d+) level=([01])$")
MAX_CAPTURE_S = 120


def parse_edge(line: str) -> dict[str, int] | None:
    m = EDGE.fullmatch(line.strip())
    if not m:
        return None
    return {"time_us": int(m[1]), "level": int(m[2])}


def pulse_widths(edges: list[dict[str, int]]) -> list[int]:
    """Offline widths of successive high->low STKNX RX pulses in us.

    Raw edges are not by themselves a validated KNX telegram/ETS exchange.
    MCU micros() wraps about every 71.6 min: subtract modulo uint32.
    """
    high_since = None
    widths = []
    for edge in edges:
        t, level = edge["time_us"], edge["level"]
        if level == 1:
            high_since = t
        elif level == 0 and high_since is not None:
            widths.append((t - high_since) & 0xFFFFFFFF)
            high_since = None
    return widths


def require_physical_gate(path: Path, independently_reviewed: bool, isolated_testbus: bool) -> None:
    state = preflight.load_gate(path)
    result = preflight.classify_gate(state)
    if result["unverified_items"]:
        raise ValueError("KNX bench hardware gate not complete: " + ", ".join(result["unverified_items"]))
    if not independently_reviewed or not isolated_testbus:
        raise ValueError("Two explicit independent physical-review and isolated-testbus confirmations required")
    # Tool cannot verify the electricity. The human must independently review.
    # It never automatically authorizes bus power.


def find_serial_port(args):
    from serial.tools import list_ports
    return usb.identify_port(list(list_ports.comports()), args.port, args.expect_serial)


def command(conn, cmd: str, expect: str) -> str:
    return usb.send(conn, cmd, expect)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("probe", "status", "stop", "capture"))
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--gate", type=Path, default=Path(__file__).resolve().parent.parent / "docs" / "KNX043_HOME_KNX_GATE.json")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--output", type=Path, help="Capture as JSONL, outside repository")
    parser.add_argument("--independent-electrical-review-complete", action="store_true")
    parser.add_argument("--isolated-knx-testbus", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "capture":
        if not 1 <= args.seconds <= MAX_CAPTURE_S:
            parser.error("RX-only capture duration must be 1-120 seconds")
        if args.output is None:
            parser.error("capture requires explicit --output path")
        require_physical_gate(args.gate, args.independent_electrical_review_complete, args.isolated_knx_testbus)

    device = find_serial_port(args)
    if args.action == "probe":
        print(json.dumps({"port": device.device, "serial": device.serial_number,
                          "opened": False, "knx_bus_access": False}))
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
    recording = False
    conn.open()
    try:
        conn.dtr = True
        usb.await_line(conn, READY, 10.5)
        recognized = True
        if args.action == "status":
            # STATUS must never turn off a running capture.
            state = command(conn, "STATUS", "KNX043 STATUS")
            print(json.dumps({"port": device.device, "read_only_status": state}))
            return 0
        if args.action == "stop":
            result = command(conn, "STOP", "KNX043 STOPPED RX_ONLY")
            print(json.dumps({"port": device.device, "stop": result}))
            return 0

        current = command(conn, "STATUS", "KNX043 STATUS")
        if "listen=0" not in current:
            raise RuntimeError("Refusing duplicate capture while another listener is active")
        command(conn, "ARM LISTEN_ONLY", ARM_ACK)
        ack = command(conn, "START LISTEN", START_ACK)
        recording = True
        header = {
            "kind": "knx043/passive-capture/v1",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "usb_port": device.device,
            "usb_serial": device.serial_number,
            "start_ack": ack,
            "seconds_requested": args.seconds,
            "knx_tx_sent": False,
            "motor_output_commanded": False,
            "warning": "Physical RX pulses only; not validated KNX telegrams",
        }
        edges = []
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as report:
            report.write(json.dumps(header) + "\n")
            end = time.monotonic() + args.seconds
            while time.monotonic() < end:
                line = conn.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                parsed = parse_edge(line)
                if parsed is not None:
                    edges.append(parsed)
                    report.write(json.dumps({"kind": "edge", **parsed}) + "\n")
                elif line.startswith("KNX043 "):
                    report.write(json.dumps({"kind": "firmware", "line": line}) + "\n")
            stopped = command(conn, "STOP", "KNX043 STOPPED RX_ONLY")
            recording = False
            result = command(conn, "STATUS", "KNX043 STATUS")
            if "listen=0" not in result:
                raise RuntimeError("Firmware still reports capture active after STOP: " + result)
            widths = pulse_widths(edges)
            summary = {
                "kind": "summary",
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "edge_count": len(edges),
                "pulse_count": len(widths),
                "pulse_widths_us": widths,
                "nominal_35us_pulses_25to55us": sum(25 <= w <= 55 for w in widths),
                "stop": stopped,
                "final_status": result,
                "note": "No bit/frame/ETS decode; any dropped edges invalidate waveform coverage",
            }
            report.write(json.dumps(summary) + "\n")
        public_summary = {k: v for k, v in summary.items()
                          if k != "pulse_widths_us"}
        public_summary["pulse_widths_sample_us"] = widths[:12]
        print(json.dumps({"capture_path": str(args.output),
                          "usb_port": device.device, **public_summary}, indent=2))
        return 0
    finally:
        # A read-only STATUS must NOT send STOP. A failed capture must.
        try:
            if recognized and args.action == "capture" and recording:
                conn.write(b"STOP\n")
                conn.flush()
        finally:
            conn.dtr = False
            conn.close()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (ValueError, RuntimeError, OSError) as exc:
        print("KNX043 REFUSED: " + str(exc), file=sys.stderr)
        sys.exit(2)
