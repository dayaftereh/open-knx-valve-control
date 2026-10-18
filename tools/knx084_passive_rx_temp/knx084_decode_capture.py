#!/usr/bin/env python3
"""Offline-only KNX084 RXEDGE decode using verified KNX070 TP1 parser.

Does not access USB, KNX/IP gateway, motor pins or ATtiny programmer.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from tools.knx070_tp1_decode import pulses_from_edges,group_pulses,decode_group
EDGE=re.compile(r"KNX084 RXEDGE t_us=(\d+) level=([01])$")

def decode_log(path:Path)->dict:
    edges=[]
    for line in path.read_text(encoding='utf8',errors='replace').splitlines():
        match=EDGE.fullmatch(line.strip())
        if match:
            edges.append({"time_text":None,"microseconds":int(match.group(1)),
                          "level":int(match.group(2))})
    pulses=pulses_from_edges(edges)
    groups=group_pulses(pulses)
    decoded=[]
    for group in groups:
        try:
            report=decode_group(group)
        except Exception as exc:
            decoded.append({"error_type":type(exc).__name__,
                            "message":str(exc)[:120],
                            "pulses":len(group)})
            continue
        parsed={key:report.get(key) for key in (
           "source","destination","service","checksum","checksum_ok",
           "length_bytes","ack","ack_code","byte_hex","raw_hex",
           "parse_error","quality")}
        parsed["pulses"]=len(group)
        decoded.append(parsed)
    return {"log":str(path),"edges":len(edges),"valid_physical_pulses":len(pulses),
            "groups":len(groups),"decoded":decoded}

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("serial_log",type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    r=decode_log(args.serial_log)
    if args.output:
        args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("KNX084_PASSIVE_BUS_OFFLINE_DECODE",json.dumps({"edges":r["edges"],"pulses":r["valid_physical_pulses"],"groups":r["groups"],"first6":r["decoded"][:6]},ensure_ascii=False),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
