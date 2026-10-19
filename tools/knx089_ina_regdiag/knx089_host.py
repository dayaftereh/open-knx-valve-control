#!/usr/bin/env python3
"""KNX089 read-only INA219 register identity/bus check; optional ADC config reset.

TARGET: KNX089 diagnostic firmware with ALL motor outputs compile-time disabled.
Never issues ARM/PULSE/KNX TX. Never reflashes. --reset-adc writes only INA219
configuration register reset bit; excludes MCU reboot and all motor outputs.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import time
import serial
from serial.tools import list_ports

BOARD="E464401787522D33"
PORT="COM8"
OUT=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX089_R29_0MV")
REG=re.compile(r"KNX089 REG addr=0x40 reg=0x([0-5]) restart_ok=(\d) restart_hex=0x([0-9A-F]+) stop_ok=(\d) stop_hex=0x([0-9A-F]+)")
STATUS=re.compile(r"KNX085 STATUS tx_low=(\d) motors_low=(\d) uart_ready=(\d) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+) motor_gate=(\d) motor_state=(\w+)(?: .*)?")
RESET=re.compile(r"KNX089 ADC_RESET i2c_code=(\d+) config_ok=(\d) config=0x([0-9A-F]+)")
INA=re.compile(r"KNX085 INA read_ok=(\d) bus_mv=(\d+) current_ma_assuming_R29_200mohm=(-?\d+) overflow=(\d) idle_ok=(\d)(?: .*)?")
class DiagnosticError(RuntimeError): pass

def require(flag, msg):
    if not flag:raise DiagnosticError(msg)
def port_check():
    p=[x for x in list_ports.comports() if (x.vid,x.pid)==(0x2e8a,0x000a)]
    require(len(p)==1 and p[0].device.upper()==PORT and (p[0].serial_number or "").upper()==BOARD,
            "USB board identity mismatch; no serial command")
    return p[0].device

def query(s,command,seconds,lines,stop=None):
    s.write((command+"\n").encode("ascii"))
    s.flush()
    limit=time.monotonic()+seconds
    while time.monotonic()<limit:
        ln=s.readline().decode("ascii","replace").strip()
        if ln:
            lines.append(ln)
            if stop and stop(ln):break

def regset(lines):
    data={}
    for l in lines:
        m=REG.fullmatch(l)
        if not m:continue
        a,ok1,v1,ok2,v2=m.groups()
        idx=int(a,16)
        raw1,raw2=int(v1,16),int(v2,16)
        # INA219 continually updates its ADC registers (~0.5ms/convert).
        # Two correct I2C transactions can report different samples:
        # shunt <=0.2mV delta is normal, bus <=4mV after masking flags.
        close=(abs((raw1 if raw1<0x8000 else raw1-0x10000) -
                   (raw2 if raw2<0x8000 else raw2-0x10000))<=20
               if idx==1 else
               abs((raw1>>3)-(raw2>>3))<=1 if idx==2 else
               raw1==raw2)
        data[idx]={"restart_ok":ok1=="1","restart_hex":f"0x{raw1:04X}",
                   "stop_ok":ok2=="1","stop_hex":f"0x{raw2:04X}",
                   "same":raw1==raw2,"within_tolerance":close}
    return data

def validate(lines):
    sts=[m for l in lines if (m:=STATUS.fullmatch(l))]
    require(sts and all(m.group(1,2,3,8,9)==("1","1","1","0","IDLE") for m in sts),
            "KNX089 ROM must have motor_gate=0, TX=LOW, motor pins LOW, IDLE")
    registers=regset(lines)
    require(len(registers)==6,"Missing one or more 0x00..0x05 register readouts")
    require(all(d["restart_ok"] and d["stop_ok"] and d["within_tolerance"] for d in registers.values()),
            "I2C read methods disagree/NAK - no reliable register data")
    require(registers[0]["restart_hex"]=="0x399F",
            "Actual CONFIG register differs from expected 0x399F")
    vals=[m for l in lines if (m:=INA.fullmatch(l))]
    require(vals and vals[-1].group(1)=="1","INA shunt/bus data missing")
    shunt=int(registers[1]["restart_hex"],16)
    if shunt>=0x8000:shunt-=0x10000
    v_bus_raw=int(registers[2]["restart_hex"],16)
    bus_mv=(v_bus_raw>>3)*4
    common_ma=shunt*0.05
    return {"motor_gate":0,"config":registers[0]["restart_hex"],
            "reg_calibration":registers[5]["restart_hex"],
            "shunt_raw_signed":shunt,
            "shunt_mv":round(shunt*0.01,4),"ma_at_200mohm":round(common_ma,2),
            "bus_mv":bus_mv,
            "high_level_ina_report_ma":int(vals[-1].group(3)),
            "reported_bus_mv":int(vals[-1].group(2)),
            "registers":registers}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reset-adc",action="store_true",
                    help="Explicitly reset only INA219 ADC 0x00 config, motor gate locked")
    args=ap.parse_args()
    port=port_check()
    lines=[]
    result={"created":datetime.now().isoformat(),"usb_serial":BOARD,
            "port":port,"user_dmm_r29_mv":0.0,"motor_activated":False,
            "reset_requested":args.reset_adc}
    try:
        with serial.Serial(port,115200,timeout=.13,write_timeout=.5,rtscts=False,dsrdtr=False) as ser:
            ser.reset_input_buffer()
            query(ser,"STATUS",1.5,lines,lambda ln:ln.startswith("KNX085 STATUS"))
            query(ser,"INA_REGS",2.5,lines,lambda ln:ln=="KNX089 REGDUMP_END")
            query(ser,"INA",.7,lines,lambda ln:ln.startswith("KNX085 INA read_ok="))
            result["before"]=validate(lines)
            if args.reset_adc:
                require(result["before"]["motor_gate"]==0,"Motor lock missing")
                query(ser,"INA_ADC_RESET",2,lines,lambda ln:ln.startswith("KNX089 ADC_RESET"))
                reset=next((m for l in reversed(lines) if (m:=RESET.fullmatch(l))),None)
                require(reset and reset.group(1,2,3)==("0","1","399F"),
                        "INA ADC reset failed or config unreadable")
                post=[]
                time.sleep(.05)
                query(ser,"STATUS",1,post,lambda ln:ln.startswith("KNX085 STATUS"))
                query(ser,"INA_REGS",2,post,lambda ln:ln=="KNX089 REGDUMP_END")
                query(ser,"INA",.7,post,lambda ln:ln.startswith("KNX085 INA read_ok="))
                result["after"]=validate(post)
                result["after_lines"]=post
            result["ok"]=True
    except Exception as exc:
        result["error"]=str(exc)
        raise
    finally:
        OUT.mkdir(parents=True,exist_ok=True)
        result["raw_lines"]=lines
        path=OUT/("KNX089_REGISTER_DIAG_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
        path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        print("KNX089_EVIDENCE",path)
        for stage in ("before","after"):
            if stage in result:
                d=result[stage]
                print("KNX089",stage,"config",d["config"],"shunt_raw",d["shunt_raw_signed"],
                      "shunt_mv",d["shunt_mv"],"bus_mv",d["bus_mv"],
                      "calib",d["reg_calibration"],"i2c_methods_agree",
                      all(v["within_tolerance"] for v in d["registers"].values()))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
