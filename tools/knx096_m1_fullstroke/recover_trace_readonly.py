#!/usr/bin/env python3
"""KNX096 SAFE USB-only recovery of RAM trace; NEVER arms or moves a motor.

The first F endstop run saved 2,837 samples in MCU RAM, but the original
serial line-by-line dump lost one contiguous block of 413 samples.
This tool re-reads TRACE with buffered raw serial reads and merges samples.
It must not reboot or flash the RP2040 because that would erase the trace.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time

from serial.tools import list_ports
import serial

OUT=Path(r"C:\ASH\Workspace\Runtime\KNX096")
FIRST=OUT/"KNX096B_M1_F30000_20261020_102101.json"
BOARD="E464401787522D33"
TRACE=re.compile(r"KNX085 TRACE t_ms=(\d+) shunt_raw=(-?\d+) shunt_uv=(-?\d+) bus_mv=(\d+) valid=(\d+)")
HDR=re.compile(r"KNX085 TRACE_BEGIN count=(\d+)")

def verify_board():
    rp=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2E8A,0x000A)]
    assert len(rp)==1 and rp[0].device.upper()=="COM7" and (rp[0].serial_number or "").upper()==BOARD, "Wrong USB RP2040 identity"
    return "COM7"

def sample(line):
    m=TRACE.fullmatch(line)
    if not m:return None
    t,raw,uv,bus,ok=map(int,m.groups())
    assert raw*10==uv,("Shunt raw voltage mismatch",line)
    return {"ms":t,"shunt_raw":raw,"shunt_uV":uv,"bus_mv":bus,
            "valid":ok==1,"ma_at_R29_200mohm":round(uv/200,3)}

def safe_status(port):
    lines=[]
    with serial.Serial(port,115200,timeout=.08,write_timeout=.5,rtscts=False,dsrdtr=False) as ser:
        ser.reset_input_buffer()
        ser.write(b"STATUS\nKNX096\nINA\n");ser.flush()
        end=time.monotonic()+2.5
        while time.monotonic()<end:
            l=ser.readline().decode("ascii","replace").strip()
            if l:lines.append(l)
    motor=[x for x in lines if x.startswith("KNX085 STATUS ")]
    firmware=[x for x in lines if x.startswith("KNX096 M1_F_SEARCH ")]
    ina=[x for x in lines if x.startswith("KNX085 INA read_ok=")]
    assert motor and "tx_low=1 motors_low=1" in motor[-1] and "motor_state=IDLE" in motor[-1], "Motor must be idle and all outputs LOW"
    assert firmware and "endstop=LOAD_RISE" in firmware[-1] and "duration_ms=30000" in firmware[-1], "Expected KNX096 F-endstop-latched firmware not present"
    assert ina and "read_ok=1" in ina[-1] and "idle_ok=1" in ina[-1], "INA219 idle invalid"
    return {"motor":motor[-1],"firmware":firmware[-1],"ina":ina[-1]}

def read_trace_buffered(port):
    lines=[]
    data=bytearray()
    with serial.Serial(port,115200,timeout=.08,write_timeout=.5,rtscts=False,dsrdtr=False) as ser:
        ser.reset_input_buffer()
        ser.write(b"TRACE\n");ser.flush()
        stop=time.monotonic()+45
        while time.monotonic()<stop:
            raw=ser.read(8192)
            if raw:
                data.extend(raw)
                if b"KNX085 TRACE_END" in data:break
        else:
            raise RuntimeError("No complete TRACE_END; no motor command was issued")
    lines=data.decode("ascii","replace").splitlines()
    headers=[m for l in lines if (m:=HDR.fullmatch(l))]
    assert headers and any(x=="KNX085 TRACE_END" for x in lines),"Missing TRACE_BEGIN/END"
    reported=int(headers[-1].group(1))
    samples={}
    for l in lines:
        s=sample(l)
        if s:
            old=samples.get(s["ms"])
            assert old is None or old==s,"Conflicting duplicate entry in one passive read"
            samples[s["ms"]]=s
    return reported,samples,{"total_bytes":len(data),"total_lines":len(lines),"sample_lines":len(samples)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--passes",type=int,default=3)
    args=ap.parse_args()
    assert 1<=args.passes<=4
    orig=json.loads(FIRST.read_text("utf8"))
    assert orig.get("search_result")=="ENDSTOP_CANDIDATE_LOAD_RISE" and orig.get("stop_ack") is True
    begin=[m for l in orig["raw_lines"] if (m:=HDR.fullmatch(l))]
    assert len(begin)==1
    target=int(begin[0].group(1))
    assert target==2837,"Wrong prior trace count; no recovery"
    combined={r["ms"]:r for r in orig["motor_trace"]}
    assert len(combined)==2424
    assert all(r["valid"] for r in combined.values())
    expected={7+8*i for i in range(target)}
    assert set(combined).issubset(expected)
    port=verify_board()
    status=safe_status(port)
    passes=[]
    for n in range(args.passes):
        count,recovered,meta=read_trace_buffered(port)
        assert count==target,"Firmware RAM trace count has changed"
        for t,row in recovered.items():
            old=combined.get(t)
            assert old is None or old==row,("Inconsistent RAM trace row",t,old,row)
            combined[t]=row
        missing=expected-set(combined)
        info={"pass":n+1,**meta,"unique_merged":len(combined),"missing":len(missing)}
        passes.append(info)
        print("READ_ONLY_TRACE_PASS",json.dumps(info),flush=True)
        if not missing:break
    rows=sorted(combined.values(),key=lambda r:r["ms"])
    missing=sorted(expected-set(combined))
    result={"time":datetime.now().isoformat(),"board":BOARD,"port":port,
            "motor_action":False,"source_trace_report":str(FIRST),
            "status":status,"firmware_reported_trace_rows":target,
            "restored_rows":len(rows),"complete":len(missing)==0,
            "missing_t_ms":missing,"passes":passes,
            "endstop_candidate":orig.get("endstop_candidates"),
            "recovered_samples":rows}
    OUT.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    dst=OUT/("KNX096_RECOVERED_TRACE_"+stamp+".json")
    dst.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n","utf8")
    c=dst.with_suffix(".csv")
    with c.open("w",encoding="utf8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    print("RECOVERY",json.dumps({"complete":result["complete"],"samples":len(rows),
           "expected":target,"first_ms":rows[0]["ms"],"last_ms":rows[-1]["ms"],
           "passes":passes},ensure_ascii=True),flush=True)
    print("SAVED_JSON",dst,flush=True)
    print("SAVED_CSV",c,flush=True)
    assert result["complete"],f"Missing {len(missing)} samples; review passive recovery logs"
if __name__=="__main__":
    raise SystemExit(main())
