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
COMPACT_EDGE = re.compile(r"^E (\d+) ([01])$")
STATUS_FIELDS = re.compile(r"([a-z_]+)=(\d+)")
MAX_CAPTURE_S = 120


def parse_edge(line: str) -> dict[str, int] | None:
    m = EDGE.fullmatch(line.strip()) or COMPACT_EDGE.fullmatch(line.strip())
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



def parse_status(line: str) -> dict[str, int]:
    if not line.startswith("KNX043 STATUS "):
        raise ValueError("Not a KNX043 STATUS line")
    return {key: int(value) for key, value in STATUS_FIELDS.findall(line)}


class EdgeStatistics:
    """Incremental pulse checks: bounded PC memory even for a large capture."""

    def __init__(self) -> None:
        self.edge_count = 0
        self.pulse_count = 0
        self.nominal_count = 0
        self.pulse_widths_sample_us: list[int] = []
        self.last_high: int | None = None
        self.last_level: int | None = None
        self.sequence_errors = 0
        self.unrecognized_lines = 0

    def add(self, edge: dict[str, int]) -> None:
        t, level = edge["time_us"], edge["level"]
        self.edge_count += 1
        if self.last_level is not None and self.last_level == level:
            self.sequence_errors += 1
        self.last_level = level
        if level == 1:
            self.last_high = t
        elif self.last_high is not None:
            width = (t - self.last_high) & 0xFFFFFFFF
            self.last_high = None
            self.pulse_count += 1
            self.nominal_count += 25 <= width <= 55
            if len(self.pulse_widths_sample_us) < 12:
                self.pulse_widths_sample_us.append(width)


class BufferedSerialLines:
    """Read USB CDC in chunks instead of one Windows serial read per byte."""

    def __init__(self, connection: Any):
        self.connection = connection
        self.pending = bytearray()

    def readline(self) -> str:
        while True:
            marker = self.pending.find(b"\n")
            if marker != -1:
                data = bytes(self.pending[:marker])
                del self.pending[:marker + 1]
                return data.decode("ascii", errors="replace").strip()
            if len(self.pending) > 1024:
                raise RuntimeError("Oversized or incomplete USB diagnostic record")
            waiting = max(1, min(int(getattr(self.connection, "in_waiting", 0)), 8192))
            data = self.connection.read(waiting)
            if not data:
                return ""
            self.pending.extend(data)


def send_collect(connection: Any, reader: BufferedSerialLines, cmd: str,
                 expected: str, callback, seconds: float = 15.0) -> str:
    """Do not silently discard RX_EDGE lines when waiting for STOP/STATUS."""
    connection.write((cmd + "\n").encode("ascii"))
    connection.flush()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        line = reader.readline()
        if not line:
            continue
        if line.startswith(expected):
            return line
        callback(line)
    raise RuntimeError("No USB diagnostic acknowledgment: " + expected)

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
        stats = EdgeStatistics()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", buffering=1024 * 1024) as report:
            report.write(json.dumps(header) + "\n")
            reader = BufferedSerialLines(conn)

            def record_line(line: str) -> None:
                edge = parse_edge(line)
                if edge is not None:
                    stats.add(edge)
                    report.write(json.dumps({"kind": "edge", **edge}) + "\n")
                elif line.startswith("KNX043 "):
                    report.write(json.dumps({"kind": "firmware", "line": line}) + "\n")
                else:
                    stats.unrecognized_lines += 1
                    report.write(json.dumps({"kind": "unrecognized", "line": line}) + "\n")

            end = time.monotonic() + args.seconds
            while time.monotonic() < end:
                line = reader.readline()
                if line:
                    record_line(line)

            stopped = send_collect(conn, reader, "STOP", "KNX043 STOPPED RX_ONLY",
                                   record_line)
            recording = False
            # STOP inhibits new samples, but a full RP2040 ring and/or USB
            # output queue may still hold samples. Drain until STATUS says
            # buffered=0. Never use the legacy usb.send: it discards edges.
            drained = False
            result = ""
            final_fields: dict[str, int] = {}
            for _ in range(40):
                result = send_collect(conn, reader, "STATUS", "KNX043 STATUS",
                                      record_line)
                final_fields = parse_status(result)
                if final_fields.get("listen") != 0:
                    raise RuntimeError("Firmware still listening after STOP: " + result)
                if final_fields.get("buffered") == 0:
                    drained = True
                    break

            firmware_dropped = final_fields.get("dropped")
            firmware_observed = final_fields.get("observed")
            expected_delivered = (firmware_observed - firmware_dropped
                                  if firmware_observed is not None and firmware_dropped is not None
                                  else None)
            count_verified = (expected_delivered is not None
                              and expected_delivered == stats.edge_count)
            complete = (drained and firmware_dropped == 0 and count_verified
                        and stats.unrecognized_lines == 0
                        and stats.sequence_errors == 0)
            summary = {
                "kind": "summary",
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "edge_count": stats.edge_count,
                "pulse_count": stats.pulse_count,
                "nominal_35us_pulses_25to55us": stats.nominal_count,
                "pulse_widths_sample_us": stats.pulse_widths_sample_us,
                "edge_sequence_errors": stats.sequence_errors,
                "unrecognized_usb_lines": stats.unrecognized_lines,
                "firmware_dropped": firmware_dropped,
                "firmware_observed": firmware_observed,
                "firmware_ring_capacity": final_fields.get("capacity"),
                "firmware_ring_high_water": final_fields.get("high_water"),
                "expected_delivered": expected_delivered,
                "pc_delivery_count_verified": count_verified,
                "ring_and_usb_drained": drained,
                "capture_coverage_complete": complete,
                "stop": stopped,
                "final_status": result,
                "note": "Raw GPIO edges only, NOT decoded KNX telegrams. "
                        "Legacy firmware lacks observed counters and cannot prove complete coverage.",
            }
            report.write(json.dumps(summary) + "\n")
        print(json.dumps({"capture_path": str(args.output),
                          "usb_port": device.device, **summary}, indent=2))
        return 0 if complete else 2
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
