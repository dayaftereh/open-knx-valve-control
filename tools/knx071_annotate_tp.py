#!/usr/bin/env python3
"""Annotate decoded KNX TP1 telegrams with ETS group names, DPT and values.

Offline only: no KNXnet/IP, serial I/O or bus transmissions.
Consumes KNX070 decoder JSON and KNX071 ETS map JSON.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path


def dpt9(data_hex: str) -> float:
    if len(data_hex) != 4:
        raise ValueError("KNX 2-byte float must contain two bytes")
    data = int(data_hex, 16)
    exp = (data >> 11) & 0xF
    mantissa = data & 0x07FF
    if data & 0x8000:
        mantissa -= 0x800
    return round(0.01 * mantissa * (2 ** exp), 4)


def readable_value(frame: dict, dpt: str) -> str:
    if frame.get("service") == "GroupValueRead":
        return "Read request"
    payload = frame.get("payload_hex") or ""
    value = frame.get("short_value")
    if dpt in ("DPT 9.1", "DPT 9.7") and len(payload) == 4:
        unit = "degC" if dpt == "DPT 9.1" else "%RH"
        try:
            return f"{dpt9(payload):g} {unit}"
        except ValueError:
            pass
    if dpt.startswith("DPT 1.") and value is not None:
        return f"{value} (binary)"
    if dpt == "DPT 5.1" and len(payload) == 2:
        return f"{round(int(payload, 16) * 100 / 255, 2):g}%"
    if value is not None:
        return str(value)
    return payload or "(no application data)"


def annotate(frame_data: dict, ets_map: dict) -> list[dict]:
    by_ga = {r["group_address"]: r for r in ets_map["groups"]}
    out = []
    for f in frame_data["frames"]:
        dest = f.get("destination", "")
        meta = by_ga.get(dest)
        dpt = meta.get("dpt", "") if meta else ""
        validity = f.get("quality", {})
        row = {
            "time_local": f.get("host_time", ""),
            "source": f.get("source", ""),
            "destination": dest,
            "main_group": meta.get("main", "") if meta else "ETS UNASSIGNED",
            "middle_group": meta.get("middle", "") if meta else "",
            "name": meta.get("name", "") if meta else "ETS UNASSIGNED",
            "dpt": dpt,
            "service": f.get("service", ""),
            "decoded_value": readable_value(f, dpt),
            "raw_payload": f.get("payload_hex") or "",
            "short_value": f.get("short_value"),
            "valid": bool(validity.get("checksum_ok") and validity.get("even_parity_ok")
                          and validity.get("start_stop_ok") and validity.get("ack_valid")),
            "ack": validity.get("ack_code"),
            "frame_hex": f.get("frame_hex", ""),
            "ets_linked_devices": meta.get("linked_devices", "") if meta else "",
        }
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tp-json", required=True, type=Path)
    ap.add_argument("--ets-json", required=True, type=Path)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    frames = json.loads(args.tp_json.read_text(encoding="utf-8"))
    ets = json.loads(args.ets_json.read_text(encoding="utf-8"))
    rows = annotate(frames, ets)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0]) if rows else []
    with args.csv.open("w", newline="", encoding="utf-8-sig") as out:
        wr = csv.DictWriter(out, fieldnames=cols, delimiter=";")
        wr.writeheader()
        wr.writerows(rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    valid=sum(row["valid"] for row in rows)
    named=sum(row["name"]!="ETS UNASSIGNED" for row in rows)
    print(f"ETS_ANNOTATE frames={len(rows)} valid={valid} ETS_NAMED={named} UNASSIGNED={len(rows)-named}")
    for x in rows[:35]:
        print("FRAME",
              x["time_local"],x["source"],">",x["destination"],
              x["service"],"name="+x["name"].encode("unicode_escape").decode("ascii"),
              "dpt="+x["dpt"],"value="+x["decoded_value"])
    print("SAVED_CSV",args.csv, "bytes",args.csv.stat().st_size)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
