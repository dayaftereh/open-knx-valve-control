#!/usr/bin/env python3
"""KNX070 offline comparison of TP1-decoded frames vs KNXnet/IP tunnel log.

No COM ports, network sockets, GPIO, send commands or hardware access.
Timestamp comparison uses the Windows serial host log clock, NOT RP2040 micros.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
from typing import Any


def tp_time(frame: dict[str, Any], when: date, offset: timezone) -> datetime:
    clock = frame["host_time"]
    return datetime.combine(when, datetime.strptime(clock, "%H:%M:%S.%f").time(), offset)


def ip_value_key(item: dict[str, Any]) -> tuple[str, str]:
    value = item.get("value")
    if isinstance(value, list) and all(isinstance(x, int) and 0 <= x < 256 for x in value):
        return "bytes", "".join(f"{b:02X}" for b in value)
    if item.get("apci") == "GroupValueRead":
        return "none", ""
    if isinstance(value, (int, bool)):
        return "short", str(int(value))
    return "raw", str(value)


def tp_value_key(item: dict[str, Any]) -> tuple[str, str]:
    if item.get("payload_hex"):
        return "bytes", item["payload_hex"].upper()
    if item.get("service") == "GroupValueRead":
        return "none", ""
    if item.get("short_value") is not None:
        return "short", str(item["short_value"])
    return "none", ""


def normal_key(source: str, destination: str, service: str, value: tuple[str, str]) -> tuple[str, ...]:
    return (source, destination, service, *value)


def is_valid_tp(f: dict[str, Any]) -> bool:
    q = f["quality"]
    return bool(q["checksum_ok"] and q["even_parity_ok"] and q["start_stop_ok"]
                and q["ack_valid"])


def match_frames(tp: list[dict[str, Any]], ip: list[dict[str, Any]],
                 when: date, offset_minutes: int, tolerance_ms: float,
                 serial_window: tuple[datetime, datetime] | None = None) -> dict[str, Any]:
    zone = timezone(timedelta(minutes=offset_minutes))
    tp_ok = [(i, f) for i, f in enumerate(tp) if is_valid_tp(f)]
    ip_datetimes = [datetime.fromisoformat(x["time_utc"]) for x in ip]
    available = set(range(len(ip)))
    matched: list[dict[str, Any]] = []
    no_match = []
    for tidx, frame in tp_ok:
        ft = tp_time(frame, when, zone)
        key = normal_key(frame["source"], frame["destination"],
                         frame["service"], tp_value_key(frame))
        choices = []
        for j in available:
            rec = ip[j]
            if normal_key(rec["source"], rec["destination"],
                          rec["apci"], ip_value_key(rec)) != key:
                continue
            delta_ms = (ip_datetimes[j] - ft).total_seconds() * 1000
            if abs(delta_ms) <= tolerance_ms:
                choices.append((abs(delta_ms), j, delta_ms))
        if choices:
            _dist, j, lag = min(choices)
            available.remove(j)
            matched.append({
                "tp_index": tidx, "ip_index": j, "source": frame["source"],
                "destination": frame["destination"], "service": frame["service"],
                "value": key[-1], "value_type": key[-2],
                "tp_host_time": ft.isoformat(timespec="milliseconds"),
                "ip_time": ip_datetimes[j].isoformat(timespec="milliseconds"),
                "ip_minus_tp_ms": round(lag, 2),
            })
        else:
            no_match.append({
                "tp_index": tidx, "source": frame["source"],
                "destination": frame["destination"], "service": frame["service"],
                "value": key[-1], "tp_host_time": ft.isoformat(timespec="milliseconds")
            })
    if serial_window is not None:
        ip_during_window = sum(serial_window[0] <= t <= serial_window[1]
                               for t in ip_datetimes)
        ip_unmatched_during = sum(serial_window[0] <= ip_datetimes[j] <= serial_window[1]
                                  for j in available)
    else:
        ip_during_window = None
        ip_unmatched_during = None
    return {
        "tp_frames_total": len(tp),
        "tp_checksum_parity_ack_ok": len(tp_ok),
        "ip_frames_total": len(ip),
        "matched_count": len(matched),
        "tp_unmatched_count": len(no_match),
        "ip_frames_during_serial_listen": ip_during_window,
        "ip_unmatched_during_serial_listen": ip_unmatched_during,
        "ip_outside_serial_listen": (len(ip)-ip_during_window
                                     if ip_during_window is not None else None),
        "timing_tolerance_ms": tolerance_ms,
        "median_abs_time_delta_ms": (round(statistics.median(
            abs(m["ip_minus_tp_ms"]) for m in matched), 2) if matched else None),
        "max_abs_time_delta_ms": (round(max(
            abs(m["ip_minus_tp_ms"]) for m in matched), 2) if matched else None),
        "matched": matched,
        "tp_unmatched": no_match,
    }


def parse_serial_window(path: Path, when: date,
                        offset_minutes: int) -> tuple[datetime, datetime] | None:
    zone = timezone(timedelta(minutes=offset_minutes))
    start = end = None
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if len(line) < 12:
            continue
        try:
            clock = datetime.strptime(line[:12], "%H:%M:%S.%f").time()
        except ValueError:
            continue
        t = datetime.combine(when, clock, zone)
        if "KNX043 LISTENING RX_ONLY" in line:
            start = t
        if "STOP_REPLY KNX043 STOPPED RX_ONLY" in line or "KNX043 AUTO_STOP RX_ONLY" in line:
            end = t
    return (start, end) if start and end and start <= end else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tp-json", type=Path, required=True)
    ap.add_argument("--ip-jsonl", type=Path, required=True)
    ap.add_argument("--serial-log", type=Path)
    ap.add_argument("--date", type=date.fromisoformat, required=True)
    ap.add_argument("--utc-offset-minutes", type=int, required=True)
    ap.add_argument("--window-ms", type=float, default=250)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--matched-csv", type=Path)
    args = ap.parse_args()
    tp = json.loads(args.tp_json.read_text(encoding="utf-8"))["frames"]
    ip = [json.loads(line) for line in args.ip_jsonl.read_text(encoding="utf-8").splitlines()
          if line.strip()]
    window = (parse_serial_window(args.serial_log, args.date, args.utc_offset_minutes)
              if args.serial_log else None)
    result = match_frames(tp, ip, args.date, args.utc_offset_minutes,
                          args.window_ms, window)
    for key in ("tp_frames_total", "tp_checksum_parity_ack_ok", "ip_frames_total",
                "ip_frames_during_serial_listen", "ip_outside_serial_listen",
                "matched_count", "tp_unmatched_count", "ip_unmatched_during_serial_listen",
                "median_abs_time_delta_ms", "max_abs_time_delta_ms"):
        print(f"{key}={result[key]}")
    for m in result["matched"][:24]:
        print("MATCH", m["source"], "->", m["destination"], m["service"],
              m["value"], "delta_ms", m["ip_minus_tp_ms"])
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print("SAVED=" + str(args.output))
    if args.matched_csv:
        with args.matched_csv.open("w", encoding="utf-8", newline="") as handle:
            cols = ("tp_host_time", "ip_time", "ip_minus_tp_ms",
                    "source", "destination", "service", "value_type", "value")
            writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(result["matched"])
        print("SAVED_CSV=" + str(args.matched_csv))
    return 0 if result["tp_unmatched_count"] == 0 and result["matched_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
