#!/usr/bin/env python3
"""KNX031: inspect a saved KNX014 UART byte trace; NEVER connect to a device.

This is an offline forensic reader. A byte dump has no timestamps/direction,
so it CANNOT establish 400ms request/reply deadlines, 100ms byte gaps,
15-second link liveness, physical sensor measurements or KNX bus acceptance.

Commands:
    plan                                      No file or subprocess activity
    inspect --input saved.bin --format binary
    inspect --input saved.txt --format hex
Optional --max-records 1..500 (diagnostics only; counters always complete).

No serial/COM sockets, GPIO, picotool, pymcuprog, KNX, USB reset or flash.
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

SCHEMA = "openknx-valvecontrol/knx031-uart-trace-v1"
SYNC = b"\xA5\x5A"
VERSION = 1
GET_SNAPSHOT = 0x01
SNAPSHOT_RESPONSE = 0x81
CHANNELS = 9
PAYLOAD_BYTES = 59
MAX_FRAME_BYTES = 67
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 500
FAULTS = (
    "None", "NoSensor", "ParasitePower", "ReadFailed", "PowerOn85",
    "OutsideRange", "SampleStale", "NoSample", "Recovering"
)
FLAGS = (("HasSample", 0x01), ("Valid", 0x02), ("Converting", 0x04),
         ("Stale", 0x08), ("Error", 0x10))


class TraceError(ValueError):
    pass


def plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "offline_byte_file_inspector_no_device_access",
        "supports": ["plan", "inspect"],
        "input_formats": ["binary", "hex"],
        "protocol": "KNX014 v1: A5 5A, 8-byte request, 67-byte response, CRC16/CCITT-FALSE",
        "channels": "T0 Vorlauf, T1..T8 Ruecklauf; not room air temperatures",
        "max_input_bytes": MAX_INPUT_BYTES,
        "no_serial_or_knx_io": True,
        "no_firmware_upload": True,
        "no_telemetry_liveness_claim": True,
        "no_motor_authority": True,
    }


def local_trace_file(filename: str, fmt: str) -> Path:
    # Reject magic device names, UNC/network paths and web-like input.
    if not filename or fmt not in ("binary", "hex"):
        raise TraceError("Supply a local binary/hex file explicitly")
    if filename.startswith(("\\\\", "//", "\\\\.\\")) or "://" in filename:
        raise TraceError("Network/OS-device paths are forbidden")
    name = Path(filename)
    # Windows aliases like COM1.bin or LPT1.txt may still resolve to OS
    # character devices despite their harmless-looking extensions.
    reserved = name.name.split(".")[0].upper()
    if reserved in ("CON", "PRN", "AUX", "NUL") or re.fullmatch(
            r"(COM|LPT)[1-9]", reserved):
        raise TraceError("Windows reserved device name is not a trace file")
    if name.suffix.lower() not in ((".bin", ".dat") if fmt == "binary" else
                                   (".hex", ".txt")):
        raise TraceError("Only .bin/.dat raw files or .hex/.txt hex dumps are supported")
    if name.is_symlink() or not name.is_file():
        raise TraceError("Input must be an existing ordinary local file (no symlink)")
    path = name.resolve()
    if path.is_symlink():
        raise TraceError("Symlinked input not allowed")
    size = path.stat().st_size
    if not 0 < size <= MAX_INPUT_BYTES:
        raise TraceError("Input size out of safe 1..8MiB range")
    return path


def read_trace(pathname: str, fmt: str) -> bytes:
    file = local_trace_file(pathname, fmt)
    data = file.read_bytes()
    if fmt == "binary":
        return data
    try:
        source = data.decode("ascii")
    except UnicodeError as exc:
        raise TraceError("Hex trace must be plain ASCII") from exc
    source = re.sub(r"(?i)0x", "", source)
    if re.fullmatch(r"[0-9a-fA-F\s,:;]*", source) is None:
        raise TraceError("Hex trace contains non-hex characters")
    source = re.sub(r"[\s,:;]", "", source)
    if not source or len(source) % 2:
        raise TraceError("Hex trace contains no bytes or an odd number of hex digits")
    try:
        return binascii.unhexlify(source)
    except (binascii.Error, ValueError) as exc:
        raise TraceError("Malformed hexadecimal byte dump") from exc


def crc16_ccitt_false(data: bytes) -> int:
    """Matches TemperatureProtocol::crc16, init 0xffff/poly 0x1021, no xor."""
    crc = 0xFFFF
    for octet in data:
        crc ^= octet << 8
        for _ in range(8):
            crc = (((crc << 1) ^ 0x1021) if crc & 0x8000 else
                   (crc << 1)) & 0xFFFF
    return crc


def decode_snapshot(payload: bytes) -> dict[str, Any]:
    """Exact validity checks from TemperatureProtocol::decodeSnapshot."""
    if len(payload) != PAYLOAD_BYTES or payload[4] != 0:
        raise TraceError("Invalid SNAPSHOT length or reserved module_status")
    uptime_ms = struct.unpack_from("<I", payload)[0]
    values: list[dict[str, Any]] = []
    for i in range(CHANNELS):
        centic, age, flags, fault = struct.unpack_from(
            "<hHBB", payload, 5 + 6 * i)
        if flags & ~0x1F or fault > 8:
            raise TraceError("Channel T%d has invalid flags/fault" % i)
        if flags & 0x02 and (not flags & 0x01 or flags & 0x18 or fault != 0):
            raise TraceError("Channel T%d falsely declares Valid" % i)
        if not flags & 0x01 and age != 0xFFFF:
            raise TraceError("Channel T%d has age but no sample" % i)
        flag_names = [name for name, bit in FLAGS if flags & bit]
        sample_flag_usable = bool(flags & 0x02 and fault == 0)
        # These are payload reports, not physical measurement verification.
        values.append({
            "channel": "T" + str(i),
            "role": "Vorlauf" if i == 0 else "Ruecklauf M" + str(i),
            "reported_centiC": centic,
            "reported_age_seconds": None if age == 0xFFFF else age,
            "flags": flags,
            "flag_names": flag_names,
            "fault_code": fault,
            "fault_name": FAULTS[fault],
            "payload_valid_flag": sample_flag_usable,
            "reported_celsius_if_valid": (centic / 100.0 if
                                           sample_flag_usable else None),
            "physical_measurement_verified": False,
        })
    return {
        "uptime_ms": uptime_ms,
        "module_status": 0,
        "channels": values,
        "source": "reported_payload_only_no_real_sensor_verification",
    }


class Scanner:
    """Parser state progression matches TemperatureProtocol::Parser::feed.

    Bad CRC/version/length discards current candidate, then seeks new sync.
    Byte timestamps are absent, so there is no interbyte timeout simulation.
    """
    def __init__(self, max_records: int) -> None:
        self.max_records = max_records
        self.phase = 0
        self.start = 0
        self.buffer = bytearray()
        self.target = 4
        self.entries: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {
            "good_crc_frames": 0, "bad_crc_frames": 0,
            "invalid_header": 0, "snapshot_valid": 0,
            "snapshot_payload_rejected": 0, "get_snapshot_requests": 0,
            "malformed_requests": 0, "unknown_frame_type": 0,
            "unpaired_response_sequences": 0, "noise_bytes": 0,
        }
        self.requests: set[int] = set()

    def record(self, item: dict[str, Any]) -> None:
        if len(self.entries) < self.max_records:
            self.entries.append(item)

    def reset(self) -> None:
        self.phase = 0
        self.buffer.clear()
        self.target = 4

    def feed(self, byte: int, offset: int) -> None:
        if self.phase == 0:
            if byte == SYNC[0]:
                self.start = offset
                self.phase = 1
            else:
                self.counts["noise_bytes"] += 1
            return
        if self.phase == 1:
            if byte == SYNC[1]:
                self.phase = 2
                self.buffer.clear()
                self.target = 4
            elif byte != SYNC[0]:
                self.reset()
                self.counts["noise_bytes"] += 1
            else:
                self.start = offset
            return

        self.buffer.append(byte)
        if len(self.buffer) == 4:
            version, kind, sequence, payload_length = self.buffer
            if version != VERSION or payload_length > PAYLOAD_BYTES:
                self.counts["invalid_header"] += 1
                self.record({
                    "offset": self.start, "status": "invalid_header",
                    "version": version, "type": kind, "sequence": sequence,
                    "declared_payload_bytes": payload_length,
                })
                self.reset()
                return
            self.target = 4 + payload_length + 2
        if len(self.buffer) < self.target:
            return

        v, kind, sequence, length = self.buffer[:4]
        payload = bytes(self.buffer[4:4 + length])
        actual_crc = int.from_bytes(self.buffer[4 + length:6 + length],
                                    "little")
        expected_crc = crc16_ccitt_false(bytes(self.buffer[:4 + length]))
        event: dict[str, Any] = {
            "offset": self.start, "sequence": sequence, "type": kind,
            "declared_payload_bytes": length,
        }
        if actual_crc != expected_crc:
            self.counts["bad_crc_frames"] += 1
            event["status"] = "crc_rejected"
        else:
            self.counts["good_crc_frames"] += 1
            if kind == GET_SNAPSHOT:
                if length:
                    self.counts["malformed_requests"] += 1
                    event["status"] = "malformed_request"
                else:
                    self.counts["get_snapshot_requests"] += 1
                    self.requests.add(sequence)
                    event["status"] = "request_observed"
            elif kind == SNAPSHOT_RESPONSE:
                if sequence not in self.requests:
                    self.counts["unpaired_response_sequences"] += 1
                event["prior_same_sequence_request_seen"] = (
                    sequence in self.requests)
                try:
                    event["snapshot"] = decode_snapshot(payload)
                except TraceError as exc:
                    self.counts["snapshot_payload_rejected"] += 1
                    event["status"] = "snapshot_payload_rejected"
                    event["reason"] = str(exc)
                else:
                    self.counts["snapshot_valid"] += 1
                    event["status"] = "snapshot_decoded"
            else:
                self.counts["unknown_frame_type"] += 1
                event["status"] = "unknown_frame_type"
        self.record(event)
        self.reset()

    def result(self, raw: bytes) -> dict[str, Any]:
        for position, b in enumerate(raw):
            self.feed(b, position)
        return {
            "schema": SCHEMA,
            "input_sha256": hashlib.sha256(raw).hexdigest(),
            "total_bytes": len(raw),
            "stats": self.counts,
            "truncated_tail_bytes": (
                len(raw) - self.start if self.phase else 0),
            "records": self.entries,
            "records_limited": (sum(self.counts[k] for k in (
                "good_crc_frames", "bad_crc_frames", "invalid_header"))
                > len(self.entries)),
            "no_device_or_knx_access": True,
            "raw_dump_cannot_verify": [
                "400ms request timeout", "100ms interbyte gap",
                "15s link online", "capture direction",
                "physical temperature accuracy", "KNX bus ACK",
                "physical or motor safety",
            ],
            "physical_release_gates": {
                "usb_flash_authorized": False,
                "updi_flash_authorized": False,
                "knx_telegram_authorized": False,
                "motor_enable_authorized": False,
            },
        }


def inspect(raw: bytes, max_records: int = 100) -> dict[str, Any]:
    if not 1 <= max_records <= MAX_RECORDS:
        raise TraceError("max-records must be within 1..500")
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise TraceError("Trace bytes empty or exceed 8 MiB")
    return Scanner(max_records).result(raw)


def cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action")
    sub.add_parser("plan", help="Offline contract; no files/devices accessed")
    inp = sub.add_parser("inspect", help="Inspect SAVED local bytes, never COM")
    inp.add_argument("--input", required=True)
    inp.add_argument("--format", required=True, choices=("binary", "hex"))
    inp.add_argument("--max-records", type=int, default=100)
    inp.add_argument("--summary-only", action="store_true",
                     help="compact statistics without per-channel records")
    return p


def main(argv: list[str] | None = None) -> int:
    args = cli().parse_args(argv)
    try:
        if args.action in (None, "plan"):
            obj = plan()
        elif args.action == "inspect":
            obj = inspect(read_trace(args.input, args.format), args.max_records)
            obj["input_format"] = args.format
            if args.summary_only:
                obj["records"] = []
                obj["records_suppressed"] = True
        else:
            raise TraceError("Unsupported action")
        print(json.dumps(obj, indent=2, sort_keys=True))
        return 0
    except (OSError, TraceError) as exc:
        print("KNX031 OFFLINE INPUT REJECTED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
