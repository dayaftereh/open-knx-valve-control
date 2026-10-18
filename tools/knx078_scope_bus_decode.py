#!/usr/bin/env python3
"""KNX078 offline physical KNX+ analog capture TP1 frame + ACK decoder.

Read-only decode of PicoScope channel A data, independent of GPIO0 channel B
or firmware serial status, to establish actual bus-standard byte/frame encoding.
"""
from __future__ import annotations
import argparse
import array
import json
from pathlib import Path
from tools.knx070_tp1_decode import read_char,parse_l_data
from tools.knx078_tp1_frame import build_frame


def decode_analog_bus(scope_json:Path) -> dict:
    d=json.loads(scope_json.read_text(encoding="utf-8"))
    raw=d["path_a"]
    values=array.array("h");values.frombytes(Path(raw).read_bytes())
    scale=50.0/d["adc_max"]
    dt=d["dt_us"]
    tx_start=d["first_tx_sample"]
    if dt>2 or dt<=0:
        raise ValueError("Decode requires scope sample resolution <=2us")
    threshold=(d["A_bus_idle_baseline_V"]-4.0)/scale
    left=max(0,tx_start-35//dt)
    right=min(len(values),tx_start+int(16000/dt))
    pulses=[]
    leading=None
    for i in range(left,right):
        low=values[i]<threshold
        if low and leading is None:leading=i
        if not low and leading is not None:
            width=(i-leading)*dt
            if 25<=width<=42:
                pulses.append(((leading-tx_start)*dt,width))
            leading=None
    if not pulses:
        raise RuntimeError("No physical bus impulses on Channel A")
    base=pulses[0][0]
    rises=[time-base for time,_ in pulses]
    chars=[]
    for idx in range(9):
        c=read_char(rises,idx*13*104,104)
        chars.append(c)
    bytes_=bytes(c["byte"] for c in chars)
    decode=parse_l_data(list(bytes_))
    checksum=0
    for c in bytes_:checksum^=c
    expect=10*13*104
    ack_near=[rise for rise in rises if abs(rise-expect)<=60]
    ack=read_char(rises,ack_near[0],104) if ack_near else None
    valid_frame=all(x["valid"] for x in chars) and checksum==0xFF
    expected_match=bytes_==build_frame()
    ack_ok=bool(ack and ack["valid"] and ack["byte"]==0xCC)
    return {
        "source_scope_json":str(scope_json),
        "analogue_channel":"A KNX+",
        "sampling_us":dt,
        "bus_baseline_V":d["A_bus_idle_baseline_V"],
        "threshold_V":round(threshold*scale,3),
        "physical_active_pulses_total":len(pulses),
        "physical_frame_pulses":sum(1 for rise in rises if rise<12168),
        "physical_ack_pulses":sum(1 for rise in rises if 13300<rise<15000),
        "frame_hex":bytes_.hex(" ").upper(),
        "expected_frame_hex":build_frame().hex(" ").upper(),
        "frame_valid":valid_frame,
        "frame_matches_intended":expected_match,
        "checksum_XOR":f"{checksum:02X}",
        "all_even_parity":all(x["parity_even"] for x in chars),
        "all_start_stop":all(x["start"] and x["stop"] for x in chars),
        "decoded":decode,
        "ack_byte":ack["hex"] if ack else None,
        "ack_valid_cc":ack_ok,
        "ack_start_offset_us":round(ack_near[0]-expect,2) if ack_near else None,
        "frame_and_ack_pass":valid_frame and expected_match and ack_ok,
        "dropped_samples":d["pico_overflow"],
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope",required=True,type=Path)
    ap.add_argument("--ip-jsonl",type=Path)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    result=decode_analog_bus(a.scope)
    if a.ip_jsonl:
        recs=[json.loads(line) for line in a.ip_jsonl.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        matches=[r for r in recs if
             r.get("source")=="1.0.250" and r.get("destination")=="29/7/241"
             and r.get("apci")=="GroupValueWrite" ]
        result["KNX_IP_tunnel_total_group_telegrams"]=len(recs)
        result["KNX_IP_tunnel_matching_telegrams"]=len(matches)
        result["KNX_IP_tunnel_matched"]=bool(matches)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                             encoding="utf-8")
    summary={k:result[k] for k in (
        "physical_active_pulses_total","frame_hex","checksum_XOR",
        "frame_valid","frame_matches_intended","ack_byte","ack_valid_cc",
        "ack_start_offset_us","frame_and_ack_pass")}
    if "KNX_IP_tunnel_matched" in result:
        summary["KNX_IP_tunnel_matched"]=result["KNX_IP_tunnel_matched"]
        summary["KNX_IP_tunnel_total"]=result["KNX_IP_tunnel_total_group_telegrams"]
    print("KNX078_INDEPENDENT_ANALOG_FRAME_DECODER",
          json.dumps(summary,ensure_ascii=True),flush=True)
    return 0 if result["frame_and_ack_pass"] else 2

if __name__=="__main__":
    raise SystemExit(main())
