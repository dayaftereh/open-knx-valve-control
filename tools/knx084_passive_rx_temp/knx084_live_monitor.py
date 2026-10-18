#!/usr/bin/env python3
"""KNX084: read-only serial USB monitor, parse four sensor channels and KNX RX edges.

Only safe STATUS/TEMPS/RXSTATS/RXDUMP commands are sent.
No UF2, UPDI, KNX output or motor action.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time
import serial
from serial.tools import list_ports

DEVICE_VID=0x2e8a
DEVICE_PID=0x000a
CH=re.compile(r"KNX084 CH T([0-3]) valid=([01]) temp_c=(NA|-?\d+(?:\.\d+)?) flags=(\d+) fault=(\d+) fault_name=(\w+) age_s=(\d+)")
STATUS=re.compile(r"KNX084 STATUS tx_low=(\d+) motors_low=(\d+) uart_ready=(\d+) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+)")
STATS=re.compile(r"KNX084 RXSTATS edges=(\d+) rises=(\d+) falls=(\d+) lost=(\d+) buffered=(\d+) last_us=(\d+) current_level=(\d+)")

def find_board(port_arg:str|None)->str:
    found=[x for x in list_ports.comports() if x.vid==DEVICE_VID and x.pid==DEVICE_PID]
    if port_arg:
        selected=[x for x in found if x.device.lower()==port_arg.lower()]
        if len(selected)!=1:
            raise RuntimeError(f"requested RP2040 port {port_arg} not unique/present, candidates={[x.device for x in found]}")
        return selected[0].device
    if len(found)!=1:
        raise RuntimeError(f"expected exactly one RP2040 runtime CDC, found {[x.device for x in found]}")
    return found[0].device

def run(args)->int:
    port=find_board(args.port)
    args.output.mkdir(parents=True,exist_ok=True)
    stem="KNX084_LIVE_"+datetime.now().strftime("%Y%m%d_%H%M%S")
    logpath=args.output/(stem+".txt")
    jsonpath=args.output/(stem+"_summary.json")
    channel={f"T{i}":{"valid_seen":0,"latest":None} for i in range(4)}
    latest_status=None
    latest_rxstats=None
    snapshots=0
    rx_dump_events=0
    refusal_lines=[]
    begin=time.monotonic()
    nextquery=0
    nextdump=0.0  # drain immediately on monitor connect, then every 8s
    last_progress=-1
    partial=bytearray()
    count=0
    print(f"KNX084_MONITOR_CONNECTED port={port} duration={args.seconds}s output={logpath}",flush=True)
    ser=serial.Serial(port,115200,timeout=.15,write_timeout=1,rtscts=False,dsrdtr=False)
    try:
        ser.reset_input_buffer()
        ser.write(b"STATUS\nTEMPS\nRXSTATS\n")
        with logpath.open("w",encoding="utf-8",buffering=1) as file:
            while time.monotonic()-begin<args.seconds:
                elapsed=time.monotonic()-begin
                if elapsed>=nextquery:
                    ser.write(b"STATUS\nTEMPS\nRXSTATS\n")
                    nextquery=elapsed+15
                if elapsed>=nextdump:
                    ser.write(b"RXDUMP\n")
                    nextdump=elapsed+8.0
                raw=ser.read(2048)
                if raw:
                    partial.extend(raw)
                if len(partial)>32768:
                    partial=partial[-4096:]
                    print("KNX084_WARN_SERIAL_BUFFER_TRUNCATED",flush=True)
                while b"\n" in partial:
                    bline,_,rest=partial.partition(b"\n")
                    partial=bytearray(rest)
                    line=bline.decode("ascii","replace").strip()
                    if not line:continue
                    file.write(line+"\n")
                    count+=1
                    if line.startswith("KNX084 SNAPSHOT seq="):
                        snapshots+=1
                    m=CH.fullmatch(line)
                    if m:
                        n,valid,temp,flags,fault,reason,age=m.groups()
                        key=f"T{n}"
                        val={"valid":valid=="1","temp_c":float(temp) if temp!="NA" else None,
                             "flags":int(flags),"fault":int(fault),
                             "fault_name":reason,"age_s":int(age)}
                        channel[key]["latest"]=val
                        if val["valid"]:
                            channel[key]["valid_seen"]+=1
                    m=STATUS.match(line)  # STATUS carries a trailing NO_KNX_TX_NO_MOTOR_ACTUATION marker
                    if m:
                        latest_status=dict(zip(("tx_low","motors_low","uart_ready","snapshots","timeouts","rejected","rx_edges"),map(int,m.groups())))
                    m=STATS.fullmatch(line)
                    if m:
                        latest_rxstats=dict(zip(("edges","rises","falls","lost","buffered","last_us","current_level"),map(int,m.groups())))
                    if line.startswith("KNX084 RXEDGE "):
                        rx_dump_events+=1
                    if "REFUSED" in line or "TIMEOUT" in line:
                        if len(refusal_lines)<14:refusal_lines.append(line)
                    if line.startswith("KNX084 CH ") and (
                            snapshots<=2 or (m and False)):
                        print("KNX084_INITIAL",line,flush=True)
                mark=int(elapsed)//15
                if mark>last_progress and elapsed>=3:
                    last_progress=mark
                    print("KNX084_PROGRESS",int(elapsed),"s snapshots",snapshots,
                          "status",latest_status,
                          "temps",{k:v["latest"] for k,v in channel.items()},flush=True)
            # Do not send any commands after observation interval
    finally:
        ser.close()
    summary={
        "port":port,"duration_seconds":args.seconds,"raw_serial_lines":count,
        "snapshots_observed":snapshots,"status":latest_status,
        "rxstats":latest_rxstats,"rx_dump_events":rx_dump_events,
        "T0_to_T3":channel,"warnings":refusal_lines,
        "log":str(logpath),"note":"All commands read-only for KNX/motors. UART snapshot request to ATtiny only.",
    }
    summary["passive_outputs_low"]=bool(latest_status and latest_status["tx_low"]==1 and latest_status["motors_low"]==1)
    summary["sensor_uart_responses_valid"]=bool(latest_status and latest_status["uart_ready"]==1 and snapshots>0)
    jsonpath.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("KNX084_LIVE_SUMMARY",json.dumps({
        "port":port,"snapshots":snapshots,"passive_outputs_low":summary["passive_outputs_low"],
        "temp_uart_ok":summary["sensor_uart_responses_valid"],
        "rxstats":latest_rxstats,
        "channels":channel,"warnings":refusal_lines[:3],"log":str(logpath),"json":str(jsonpath)},
        ensure_ascii=False),flush=True)
    return 0 if summary["passive_outputs_low"] and summary["sensor_uart_responses_valid"] else 5

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port")
    p.add_argument("--seconds",type=int,default=65)
    p.add_argument("--output",type=Path,default=Path.home()/"Downloads")
    args=p.parse_args()
    if not 15<=args.seconds<=150:p.error("seconds must be in [15,150]")
    return run(args)

if __name__=="__main__":
    raise SystemExit(main())
