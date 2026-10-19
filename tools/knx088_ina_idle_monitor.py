#!/usr/bin/env python3
"""KNX088 passive INA219/R29 idle monitor; only READ-ONLY USB commands.

Never flashes or issues ARM, PULSE, STOP, or changes outputs. Uses the
currently loaded KNX085 COM8 firmware on known RP2040 USB serial.
Logs reported common-rail shunt current against KNX RX, status and temps.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import statistics
import time
from serial.tools import list_ports
import serial
import re

SERIAL="E464401787522D33"
PORT="COM8"
DEST=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX088_INA_IDLE")
INA=re.compile(r"KNX085 INA read_ok=(\d+) bus_mv=(\d+) current_ma_assuming_R29_200mohm=(-?\d+) overflow=(\d+) idle_ok=(\d+)")
STATUS=re.compile(r"KNX085 STATUS tx_low=(\d+) motors_low=(\d+) uart_ready=(\d+) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+) motor_gate=(\d+) motor_state=(\w+)")
RX=re.compile(r"KNX085 RXSTATS edges=(\d+) rises=(\d+) falls=(\d+) lost=(\d+) buffered=(\d+) last_us=(\d+) current_level=(\d+)")
TEMP=re.compile(r"KNX085 CH T([0-3]) valid=(\d) temp_c=(NA|-?\d+(?:\.\d+)?) flags=(\d+) fault=(\d+)")

def demand(x,msg):
    if not x:raise RuntimeError(msg)
def find_port():
    matches=[p for p in list_ports.comports() if p.vid==0x2e8a and p.pid==0x000a]
    demand(len(matches)==1 and matches[0].device.upper()==PORT and
           (matches[0].serial_number or "").upper()==SERIAL,
           "Expected one exact KNX085 RP2040 COM8 USB serial; no other COM touched")
    return matches[0].device
def run(seconds:int):
    demand(10<=seconds<=90,"Bounded passive monitor duration 10..90 seconds")
    port=find_port()
    samples=[]
    all_lines=[]
    temps={}
    statuses=[]
    rxrows=[]
    begin=time.monotonic()
    with serial.Serial(port,115200,timeout=.15,write_timeout=.5,
                       rtscts=False,dsrdtr=False) as dev:
        dev.reset_input_buffer()
        dev.write(b"STATUS\nMSTATUS\nINA\nRXSTATS\nTEMPS\n")
        verified=False
        next_request=begin+1.0
        while time.monotonic()-begin<seconds:
            line=dev.readline().decode("ascii","replace").strip()
            if line:
                all_lines.append(line)
                st=STATUS.match(line)
                if st:
                    values=st.groups()
                    valid=(values[0:3]==("1","1","1") and values[8]=="IDLE")
                    demand(valid,"KNX085 motor or GPIO unexpectedly active: STOP MONITOR")
                    verified=True
                    statuses.append({"elapsed_s":round(time.monotonic()-begin,3),
                                     "rx_edges":int(values[6]),"temps_snapshots":int(values[3]),
                                     "temperature_uart_timeouts":int(values[4]),
                                     "temperature_uart_rejected":int(values[5])})
                m=INA.match(line)
                if m:
                    readok,voltage,cur,overflow,idle=m.groups()
                    current=int(cur)
                    samples.append({"elapsed_s":round(time.monotonic()-begin,3),
                                    "read_ok":readok=="1","bus_mv":int(voltage),
                                    "ma_common_rail":current,
                                    "shunt_mv_inferred":round(current*.2,3),
                                    "ina_overflow":overflow=="1",
                                    "idle_ok":idle=="1"})
                rx=RX.match(line)
                if rx:
                    vals=rx.groups()
                    rxrows.append({"elapsed_s":round(time.monotonic()-begin,3),
                                   "rx_edges":int(vals[0]),"lost":int(vals[3])})
                t=TEMP.match(line)
                if t:
                    ch,ok,c,flags,fault=t.groups()
                    temps[ch]={"valid":ok=="1","c":None if c=="NA" else float(c),
                               "fault":int(fault)}
            now=time.monotonic()
            if now>=next_request:
                demand(verified,"Expected KNX085 STATUS before monitoring")
                command=b"INA\n"
                if len(samples)%4==0:command+=b"STATUS\nRXSTATS\n"
                if len(samples)%12==0:command+=b"TEMPS\n"
                dev.write(command)
                next_request=now+1.05
    demand(len(samples)>=8 and verified,"Not enough valid passive INA readings")
    cur=[s["ma_common_rail"] for s in samples if s["read_ok"] and not s["ina_overflow"]]
    bus=[s["bus_mv"] for s in samples if s["read_ok"] and not s["ina_overflow"]]
    demand(cur and bus,"No healthy INA samples")
    report={"schema":"openknx-knx088-ina219-r29-passive-v1",
            "captured_local":datetime.now().isoformat(),
            "board_usb_serial":SERIAL,"duration_s":seconds,
            "motor_commands_sent":False,"shunt_ohms_user_confirmed":0.2,
            "sample_count":len(samples),"good_sample_count":len(cur),
            "idle_gate_good_samples":sum(s["idle_ok"] for s in samples),
            "reported_ma":{"min":min(cur),"median":statistics.median(cur),
                           "max":max(cur),"stdev":round(statistics.pstdev(cur),3)},
            "ina_bus_mv":{"min":min(bus),"median":statistics.median(bus),"max":max(bus)},
            "shunt_mv_at_median":round(statistics.median(cur)*.2,3),
            "r29_w_at_median":round((statistics.median(cur)/1000)**2*.2,5),
            "inferred_vin_plus_mv":round(statistics.median(bus)+statistics.median(cur)*.2,3),
            "rx_total_delta":(rxrows[-1]["rx_edges"]-rxrows[0]["rx_edges"]) if len(rxrows)>=2 else None,
            "status_checks":len(statuses),"last_status":statuses[-1] if statuses else None,
            "temps":temps,"samples":samples,"rxstats":rxrows,"status_rows":statuses,
            "raw_lines":all_lines}
    DEST.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    path=DEST/f"KNX088_PASSIVE_INA_{stamp}.json"
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    csvpath=path.with_suffix(".csv")
    with csvpath.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=list(samples[0]))
        writer.writeheader();writer.writerows(samples)
    print("PASSIVE_MONITOR_RESULT",json.dumps({k:v for k,v in report.items() if k not in
          ("samples","raw_lines","rxstats","status_rows")},ensure_ascii=False))
    print("JSON",path);print("CSV",csvpath)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seconds",type=int,default=45)
    a=p.parse_args()
    try:run(a.seconds)
    except Exception as exc:
        print("KNX088_PASSIVE_MONITOR_FAILED",exc)
        raise SystemExit(5)
if __name__=="__main__":
    main()
