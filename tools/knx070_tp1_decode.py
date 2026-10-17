#!/usr/bin/env python3
"""KNX070 offline KNX TP1 9600-bit/s RX-edge telegram decoder.

Input: KNX043/KNX048 firmware USB serial log: 'E <micros> <level>'.
The STKNX RX pin emits a 35-us HIGH pulse for a TP1 logical 0, and LOW
between pulses. Every normal character is 1 start(0), 8 LSB data bits,
1 even parity bit, 1 stop(1), 2 idle(1) = 13 * ~104 us. An ACK (0xCC)
follows 15 idle bit-times after the last character (26 start-to-start).
Input is FILE ONLY. NO USB, network, GPIO, KNX sends, or imports.
"""
from __future__ import annotations

import argparse
import bisect
from datetime import date, datetime
import json
from pathlib import Path
import re
import statistics
from typing import Any

BIT_US = 104.0
CELL_US = BIT_US * 13
GROUP_GAP_US = 4000
START_TOLERANCE_US = 55
PULSE_TOLERANCE_US = 24

EDGE_PATTERN = re.compile(r"(?:(\d\d:\d\d:\d\d\.\d+)\s+)?E\s+(\d+)\s+([01])$")
SERVICES = {
    0: "GroupValueRead",
    1: "GroupValueResponse",
    2: "GroupValueWrite",
    3: "IndividualAddrWrite",
}


def read_edge_log(path: Path) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        m = EDGE_PATTERN.search(line.strip())
        if m:
            edges.append({"time_text": m.group(1), "microseconds": int(m.group(2)),
                          "level": int(m.group(3))})
    return edges


def pulses_from_edges(edges: list[dict[str, Any]]) -> list[tuple[int, int, str | None]]:
    pulses = []
    begin = None
    begin_text = None
    for e in edges:
        level = int(e["level"])
        t = int(e["microseconds"])
        if level:
            begin = t
            begin_text = e.get("time_text")
        elif begin is not None and 0 < t - begin < 110:
            pulses.append((begin, t, begin_text))
            begin = None
        else:
            begin = None
    return pulses


def group_pulses(pulses: list[tuple[int, int, str | None]]) -> list[list[tuple[int, int, str | None]]]:
    groups: list[list[tuple[int, int, str | None]]] = []
    for p in pulses:
        if not groups or p[0] - groups[-1][-1][0] > GROUP_GAP_US:
            groups.append([p])
        else:
            groups[-1].append(p)
    return groups


def nearest_pulse(rises: list[int], wanted: float) -> tuple[int, float]:
    i = bisect.bisect_left(rises, wanted)
    options = [rises[k] for k in (i - 1, i) if 0 <= k < len(rises)]
    if not options:
        return -1, float("inf")
    hit = min(options, key=lambda t: abs(t - wanted))
    return hit, abs(hit - wanted)


def read_char(rises: list[int], start: int, bit_time: float) -> dict[str, Any]:
    bits = []
    for i in range(11):
        _closest, dist = nearest_pulse(rises, start + i * bit_time)
        bits.append(0 if dist <= PULSE_TOLERANCE_US else 1)
    value = sum(bits[i + 1] << i for i in range(8))
    return {
        "byte": value, "hex": f"{value:02X}",
        "start": bits[0] == 0,
        "parity_even": sum(bits[1:10]) % 2 == 0,
        "stop": bits[10] == 1,
        "valid": bits[0] == 0 and sum(bits[1:10]) % 2 == 0 and bits[10] == 1,
    }


def format_source(value: int) -> str:
    return f"{(value >> 12) & 15}.{(value >> 8) & 15}.{value & 255}"


def format_group(value: int) -> str:
    return f"{value >> 11}/{(value >> 8) & 7}/{value & 255}"


def parse_l_data(raw: list[int]) -> dict[str, Any]:
    if len(raw) < 9:
        return {"parse_error": "too-short"}
    ctrl = raw[0]
    # Standard frame first control-byte bit7 is 1.
    if not ctrl & 0x80:
        return {"parse_error": "extended-frame-not-implemented"}
    src = raw[1] << 8 | raw[2]
    dst = raw[3] << 8 | raw[4]
    ctrllen = raw[5]
    is_group = bool(ctrllen & 0x80)
    apdu = raw[6:-1]
    expected_apdu_length = (ctrllen & 0x0F) + 1
    if len(apdu) != expected_apdu_length:
        return {"parse_error": "length-mismatch", "expected_apdu": expected_apdu_length,
                "actual_apdu": len(apdu)}
    apci = ((apdu[0] & 3) << 2 | apdu[1] >> 6) if len(apdu) >= 2 else None
    data = list(apdu[2:]) if len(apdu) > 2 else []
    one_bit = (apdu[1] & 0x3F) if len(apdu) == 2 else None
    # DPT9.XXX candidate; the ETS group address mapping determines units.
    dpt9_candidate = None
    if len(data) == 2:
        floating_raw = (data[0] << 8) | data[1]
        exponent = (floating_raw >> 11) & 0x0F
        mantissa = floating_raw & 0x7FF
        if floating_raw & 0x8000:
            mantissa -= 2048
        dpt9_candidate = round(0.01 * mantissa * (1 << exponent), 2)
    return {
        "source": format_source(src),
        "destination": format_group(dst) if is_group else format_source(dst),
        "destination_type": "group" if is_group else "individual",
        "hop_count": (ctrllen >> 4) & 7,
        "service": SERVICES.get(apci, f"APCI_{apci}"),
        "apci": apci, "payload_hex": "".join(f"{v:02X}" for v in data),
        "short_value": one_bit, "dpt9_candidate": dpt9_candidate,
        "control_hex": f"{ctrl:02X}",
        "routing_hex": f"{ctrllen:02X}",
    }


def decode_group(group: list[tuple[int, int, str | None]]) -> dict[str, Any]:
    rises = [p[0] for p in group]
    origin = rises[0]
    starts: list[int] = [origin]
    # Detect byte start(0) pulse at 13-bit intervals. The blank 13-bit
    # slot between last data byte and ACK is the reliable frame boundary.
    for i in range(1,44):
        period = (statistics.median((t-origin)/j for j,t in enumerate(starts) if j)
                  if len(starts) >= 2 else CELL_US)
        _pulse, distance = nearest_pulse(rises, origin + i * period)
        if distance > START_TOLERANCE_US:
            break
        starts.append(_pulse)
    bit_time = (statistics.median((t-origin)/j for j,t in enumerate(starts) if j)
                / 13 if len(starts) > 1 else BIT_US)
    chars = [read_char(rises, t, bit_time) for t in starts]
    raw = [item["byte"] for item in chars]
    ack_expected = origin + (len(starts) + 1) * bit_time * 13
    ack_t, ack_dist = nearest_pulse(rises, ack_expected)
    ack_char = read_char(rises, ack_t, bit_time) if ack_dist <= 60 else None
    checksum = 0
    for byte in raw:
        checksum ^= byte
    quality = {
        "even_parity_ok": all(x["parity_even"] for x in chars),
        "start_stop_ok": all(x["start"] and x["stop"] for x in chars),
        "checksum_ok": checksum == 0xFF,
        "ack_valid": ack_char is not None and ack_char["valid"] and ack_char["byte"] in (0xCC, 0x0C, 0xC0, 0x00),
        "ack_code": f"{ack_char['byte']:02X}" if ack_char is not None else None,
    }
    return {
        "host_time": group[0][2],
        "first_edge_microseconds": origin,
        "duration_ms": round((group[-1][1]-origin) / 1000, 3),
        "bit_time_us": round(bit_time, 3),
        "rx_pulse_count": len(group),
        "length_bytes": len(raw), "frame_hex": " ".join(f"{v:02X}" for v in raw),
        "frame": raw,
        "quality": quality,
        **parse_l_data(raw),
    }


def decode_log(path: Path) -> list[dict[str, Any]]:
    edges = read_edge_log(path)
    return [decode_group(g) for g in group_pulses(pulses_from_edges(edges))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-print", type=int, default=30)
    args = parser.parse_args()
    frames = decode_log(args.input)
    valid = sum(1 for x in frames
                if x["quality"]["checksum_ok"] and x["quality"]["even_parity_ok"]
                and x["quality"]["ack_valid"])
    print(f"TP1_DECODE file={args.input.name} frames={len(frames)} "
          f"checksum_parity_ack_ok={valid}")
    for index, f in enumerate(frames[:args.max_print]):
        print(f"{index + 1:02} {f['host_time']} "
              f"{f.get('source', '?')} -> {f.get('destination', '?')} "
              f"{f.get('service', '?')} data={f.get('payload_hex', '')} "
              f"short={f.get('short_value')} ACK={f['quality']['ack_code']} "
              f"CRC={'OK' if f['quality']['checksum_ok'] else 'BAD'}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "source_file": str(args.input), "decoder_version": "KNX070-1",
            "frames": frames, "valid_frame_count": valid,
            "total_frame_count": len(frames)
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print("SAVED=" + str(args.output))
    return 0 if valid == len(frames) and valid > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
