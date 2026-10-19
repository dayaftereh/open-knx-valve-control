#!/usr/bin/env python3
"""KNX085 single M1 current-profiling bench tool; plan/probe are nonactuating.
Never flash. Motor testing requires KNX PHYSICALLY disconnected and USB
as ONLY power, with physical USB-off access. One brief pulse at a time.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import time
from datetime import datetime
import serial
from serial.tools import list_ports

PORT="COM8"
SERIAL="E464401787522D33"
STATUS=re.compile(r"KNX085 STATUS tx_low=(\d+) motors_low=(\d+) uart_ready=(\d+) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+) motor_gate=(\d+) motor_state=(\w+)")
INA=re.compile(r"KNX085 INA read_ok=(\d+) bus_mv=(\d+) current_ma_assuming_R29_200mohm=(-?\d+) overflow=(\d+) idle_ok=(\d+)")
INA_CONFIG=re.compile(r"KNX085 INA addr=0x([0-9a-fA-F]+) config=0x([0-9a-fA-F]+) config_ok=(\d+) good_idle_samples=(\d+)")
TRACE=re.compile(r"KNX085 TRACE t_ms=(\d+) shunt_raw=(-?\d+) shunt_uv=(-?\d+) bus_mv=(\d+) valid=(\d+)")
TEMP=re.compile(r"KNX085 CH T([0-3]) valid=(\d) temp_c=(NA|-?\d+(?:\.\d+)?) flags=(\d+) fault=(\d+) fault_name=(\w+) age_s=(\d+)")
MAX_PULSE_MS=250

def validate_board(port, serial_expected):
    rows=[p for p in list_ports.comports() if p.vid==0x2e8a and p.pid==0x000a]
    if len(rows)!=1:
        raise RuntimeError(f"Exactly one RP2040 2E8A:000A is required, found {len(rows)}")
    p=rows[0]
    if p.device.upper()!=port.upper() or (p.serial_number or "").upper()!=serial_expected.upper():
        raise RuntimeError("RP2040 COM port or hardware serial mismatch")
    return p

def collect(ser, duration, lines, until=None):
    end=time.monotonic()+duration
    while time.monotonic()<end:
        try:
            raw=ser.readline()
        except serial.SerialException as exc:
            raise RuntimeError("USB serial lost; hardware must fail safe") from exc
        if not raw:
            continue
        line=raw.decode("ascii","replace").strip()
        if line:
            lines.append(line)
            if until and until(line):
                return True
    return False

def latest(lines,pattern):
    matches=[pattern.match(line) for line in lines]
    return next((m for m in reversed(matches) if m is not None),None)

def check_status(lines,gate_required=False,require_temps=True):
    m=latest(lines,STATUS)
    if not m:
        raise RuntimeError("No KNX085 firmware STATUS")
    tx,motors,uart,snap,timeout,reject,edges,gate,state=m.groups()
    if (tx,motors,uart,state)!=("1","1","1","IDLE"):
        raise RuntimeError("Unsafe KNX_TX/motor/UART status")
    if gate_required and gate!="1":
        raise RuntimeError("Motor outputs are compile-time locked")
    if require_temps:
        for n in range(4):
            readings=[TEMP.fullmatch(line) for line in lines]
            channel=[v for v in readings if v and v.group(1)==str(n)]
            if not channel or channel[-1].group(2)!="1" or channel[-1].group(5)!="0":
                raise RuntimeError(f"T{n} temperature snapshot missing/invalid")
    return {"snapshots":int(snap),"knx_rx_edges":int(edges),
            "gate":int(gate),"temperature_uart_ok":True}

def check_ina(lines):
    cfg=latest(lines,INA_CONFIG)
    m=latest(lines,INA)
    if not cfg or not m:
        raise RuntimeError("No INA219 register readback")
    address,config,ok,good=cfg.groups()
    readok,bus,ma,overflow,idle=m.groups()
    if address.lower()!="40" or ok!="1" or int(good)<5 or readok!="1" or overflow!="0":
        raise RuntimeError("INA219 presence/config/stable-sample gate FAILED")
    v=int(bus)
    cur=int(ma)
    if v<3100 or v>3450 or cur<(-5) or cur>25 or idle!="1":
        raise RuntimeError("INA219 motor supply/current outside preliminary window")
    return {"ina_address":address,"config":config,"idle_good_samples":int(good),
            "bus_mv":v,"nominal_ma_assuming_0_2ohm":cur}

def send(ser,cmd):
    ser.write((cmd+"\n").encode("ascii"))
    ser.flush()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["plan","probe","pulse"],nargs="?",default="plan")
    p.add_argument("--port",default=PORT)
    p.add_argument("--expected-serial",default=SERIAL)
    p.add_argument("--duration-ms",type=int,default=150)
    p.add_argument("--direction",choices=["F","R"],default="F")
    p.add_argument("--knx-physically-unplugged",action="store_true")
    p.add_argument("--usb-only-supply",action="store_true")
    p.add_argument("--updi-unplugged",action="store_true")
    p.add_argument("--physical-usb-off-ready",action="store_true")
    p.add_argument("--output",type=Path,default=Path.home()/"Downloads")
    args=p.parse_args()
    plan={"bench":"ONLY M1, one bounded pulse", "fw":"KNX085 on RP2040",
          "pulse_ms_range":[50,250],"no_autonomous_homing":True,
          "INA_shunt_nominal_ohm":0.2,"must_isolate_KNX_during_flash":True,
          "no_motor_without_all_physical_confirmations":True}
    if args.action=="plan":
        print(json.dumps(plan,indent=2));return 0
    if args.action=="pulse":
        if not all((args.knx_physically_unplugged,args.usb_only_supply,args.updi_unplugged,args.physical_usb_off_ready)):
            raise RuntimeError("Motor pulse refused: physically unplug KNX and UPDI programmer, use USB-only RP supply, and verify accessible emergency USB power-off")
        if not 50<=args.duration_ms<=MAX_PULSE_MS:
            raise RuntimeError("Pulse length outside bounded limit")
    if args.action=="pulse":
        other=[p.device for p in list_ports.comports() if p.vid==0x1a86 and p.pid==0x7523]
        if other:
            raise RuntimeError(f"CH340/UPDI still enumerated: {other}; unplug UPDI before motor test")
    validate_board(args.port,args.expected_serial)
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/("KNX085_"+args.action.upper()+"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
    lines=[]
    with serial.Serial(args.port,115200,timeout=.15,write_timeout=.5,rtscts=False,dsrdtr=False) as ser:
        try:
            ser.reset_input_buffer()
            send(ser,"STATUS")
            send(ser,"INA")
            send(ser,"TEMPS")
            collect(ser,4,lines)
            result={"action":args.action,"port":args.port,"usb_serial":args.expected_serial}
            result["baseline"]=check_status(lines,gate_required=args.action=="pulse")
            if args.action=="pulse":
                # At idle data sample interval >=200ms, require 5 good readings.
                for _ in range(8):
                    send(ser,"INA")
                    collect(ser,.3,lines)
                    if latest(lines,INA_CONFIG) and int(latest(lines,INA_CONFIG).group(4))>=5: break
                result["ina_before"]=check_ina(lines)
                send(ser,"ARM MOTORS")
                if not collect(ser,1,lines,lambda s:s in ("KNX085 ARMED_5S","KNX085 REFUSED_ARM_HARDWARE_OR_POWER_GATE")):
                    raise RuntimeError("Missing ARM ACK")
                if "KNX085 ARMED_5S" not in lines[-6:]:
                    raise RuntimeError("Motor arming rejected")
                cmd=f"PULSE M1 {args.direction} {args.duration_ms}"
                send(ser,cmd)
                if not collect(ser,1,lines,lambda s:s.startswith("KNX085 PULSE_STARTED ") or s.startswith("KNX085 REFUSED_")):
                    raise RuntimeError("Missing pulse start ACK")
                if not any(s.startswith("KNX085 PULSE_STARTED M1 ") for s in lines[-8:]):
                    raise RuntimeError("Motor pulse not started")
                if not collect(ser,2,lines,lambda s:s.startswith("KNX085 MOTOR_ENDED state=")):
                    raise RuntimeError("No bounded STOP completion")
                if not any(s=="KNX085 MOTOR_ENDED state=IDLE" for s in lines[-8:]):
                    raise RuntimeError("Motor ended with a fault, not a clean stop")
                send(ser,"STATUS")
                send(ser,"INA")
                send(ser,"TRACE")
                collect(ser,2,lines,lambda s:s=="KNX085 TRACE_END")
                result["after"]=check_status(lines,gate_required=True,require_temps=False)
                result["trace"]=[{"ms":int(m.group(1)),"shunt_raw":int(m.group(2)),
                       "shunt_uV":int(m.group(3)),"bus_mV":int(m.group(4)),
                       "valid":m.group(5)=="1",
                       "nominal_mA":round(int(m.group(3))/200,3)}
                     for line in lines if (m:=TRACE.fullmatch(line))]
                if not result["trace"]:
                    raise RuntimeError("Motor pulse ran without INA trace data")
                result["max_nominal_mA"]=max(r["nominal_mA"] for r in result["trace"] if r["valid"])
            else:
                result["read_only_ina"]=latest(lines,INA).groups() if latest(lines,INA) else None
            result["raw_lines"]=lines
            path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
            print(json.dumps({k:v for k,v in result.items() if k not in ("raw_lines","trace")},
                             indent=2,ensure_ascii=False))
            print("EVIDENCE",path)
            return 0
        finally:
            if args.action=="pulse":
                # Redundant STOP; firmware must separately auto-stop within 250ms.
                try: send(ser,"STOP")
                except Exception: pass
if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print("KNX085_BENCH_ABORT:",str(exc))
        raise SystemExit(5)
