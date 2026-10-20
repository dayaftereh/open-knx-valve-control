#!/usr/bin/env python3
"""KNX092 office USB-only bench: COM7 RP2040 + INA219 + M1, no KNX/UPDI/DS18B20.

Stages: preflight (KNX089 read-only), flash (one exact SHA256-pinned KNX085
unlocked UF2), verify (KNX085 read-only), pulse (one 150 ms M1 F test).
No host-wide CH340 exclusion: COM8/9/10 can belong to unrelated equipment.
No hidden retries. Motor 120 mA firmware current limit, 250 ms FW watchdog.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import serial
from serial.tools import list_ports

BOARD_SERIAL="E464401787522D33"
IMAGE=Path(r"C:\ASH\Workspace\Runtime\KNX092\knx085_bench_unlocked.uf2")
SHA256="86cbf6942fd12eba07402c52842ba7543cabd2c2a557a329607c954388a54750"
PICOTOOL=Path(r"C:\Users\llo\.platformio\packages\tool-picotool-rp2040-earlephilhower\picotool.exe")
OUT=Path(r"C:\ASH\Workspace\Runtime\KNX092")
STATUS=re.compile(r"KNX085 STATUS tx_low=(\d) motors_low=(\d) uart_ready=(\d) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+) motor_gate=(\d) motor_state=(\w+)")
INA=re.compile(r"KNX085 INA read_ok=(\d) bus_mv=(\d+) current_ma_assuming_R29_200mohm=(-?\d+) overflow=(\d) idle_ok=(\d)")
CONFIG=re.compile(r"KNX085 INA addr=0x40 config=0x([0-9A-F]+) config_ok=(\d) good_idle_samples=(\d+)")
TRACE=re.compile(r"KNX085 TRACE t_ms=(\d+) shunt_raw=(-?\d+) shunt_uv=(-?\d+) bus_mv=(\d+) valid=(\d+)")
REG=re.compile(r"KNX089 REG addr=0x40 reg=0x([0-5]) restart_ok=(\d) restart_hex=0x([0-9A-F]+) stop_ok=(\d) stop_hex=0x([0-9A-F]+)")
class Refused(RuntimeError):pass
def insist(ok,message):
    if not ok:raise Refused(message)
def board():
    rows=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2e8a,0x000a)]
    insist(len(rows)==1,"Expected exactly one RP2040, not other USB serial adapters")
    p=rows[0]
    insist((p.serial_number or "").upper()==BOARD_SERIAL,
           "RP2040 hardware identity mismatch")
    insist(p.device.upper()=="COM7","Expected RP2040 COM7, got "+p.device)
    return p.device
def open_usb(port):
    return serial.Serial(port,115200,timeout=.12,write_timeout=.5,rtscts=False,dsrdtr=False)
def command(ser,text):
    ser.write((text+"\n").encode("ascii"));ser.flush()
def gather(ser,seconds,lines,end=None):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        raw=ser.readline()
        if raw:
            line=raw.decode("ascii","replace").strip()
            if line:
                lines.append(line)
                if end and end(line):return True
    return False
def write_report(prefix,data):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/(prefix+"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("REPORT",p)
    return p
def latest(lines,pattern):
    for text in reversed(lines):
        m=pattern.match(text)
        if m:return m
    return None
def read_baseline(port,gate,seconds=3.2):
    lines=[]
    with open_usb(port) as ser:
        ser.reset_input_buffer()
        for _ in range(10):
            command(ser,"STATUS")
            command(ser,"INA")
            if gate==0:command(ser,"INA_REGS")
            gather(ser,seconds/10,lines)
    statuses=[m for line in lines if (m:=STATUS.match(line))]
    insist(len(statuses)>=3,"Insufficient USB STATUS responses")
    insist(all(m.group(1,2,3,8,9)==("1","1","1",str(gate),"IDLE") for m in statuses),
           "KNX_TX/motor pins or firmware gate not as expected")
    samples=[m for line in lines if (m:=INA.match(line))]
    insist(len(samples)>=5,"Insufficient INA readings")
    cfg=latest(lines,CONFIG)
    insist(cfg and cfg.group(1)=="399F" and cfg.group(2)=="1",
           "INA219 config is not 0x399F")
    good=[{"bus_mv":int(m.group(2)),"nominal_ma":int(m.group(3)),
           "read_ok":m.group(1)=="1","overflow":m.group(4)=="1","idle_ok":m.group(5)=="1"}
          for m in samples]
    insist(all(x["read_ok"] and not x["overflow"] and x["idle_ok"] and
                3100<=x["bus_mv"]<=3450 and -5<=x["nominal_ma"]<=3 for x in good),
           "INA219 not stable near zero on USB-only bench")
    if gate==1:
        insist(int(cfg.group(3))>=5,"Firmware has <5 good idle samples; no motor")
    if gate==0:
        regs=[m for line in lines if (m:=REG.match(line)) and m.group(1)=="1"]
        insist(len(regs)>=5,"No INA219 shunt raw register 0x01 data")
        raw=[int(m.group(3),16) for m in regs]
        signed=[v if v<32768 else v-65536 for v in raw]
        insist(all(-100<=x<=100 for x in signed),
               "Shunt raw beyond +/-1.00mV; new 10 ohm resistors not validated")
    return {"port":port,"serial":BOARD_SERIAL,"motor_gate":gate,
            "source":"live RP2040 USB CDC","motor_idle":True,
            "ina219_config":"0x399F",
            "ina_samples":len(good),
            "bus_mv_min":min(x["bus_mv"] for x in good),
            "bus_mv_max":max(x["bus_mv"] for x in good),
            "nominal_ma_min":min(x["nominal_ma"] for x in good),
            "nominal_ma_max":max(x["nominal_ma"] for x in good),
            "raw_lines_tail":lines[-35:]}
def image_check():
    insist(IMAGE.is_file(),"Missing pinned UF2 at "+str(IMAGE))
    blob=IMAGE.read_bytes()
    insist(len(blob)==242688 and hashlib.sha256(blob).hexdigest()==SHA256,
           "Unexpected UF2 binary checksum/size")
    insist(blob[:4]==bytes.fromhex("5546320A"),"UF2 magic mismatch")
    return {"sha256":SHA256,"bytes":len(blob)}
def rom_volume():
    drives=[]
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        p=Path(letter+":\\INFO_UF2.TXT")
        try:
            if p.is_file() and "Board-ID: RPI-RP2" in p.read_text("ascii",errors="replace"):
                drives.append(p.parent)
        except OSError:continue
    insist(len(drives)<=1,"Multiple BOOTSEL volumes")
    return drives[0] if drives else None
def enter_rom(port):
    ser=serial.Serial()
    ser.port=port
    ser.baudrate=1200
    ser.timeout=.2
    ser.write_timeout=.2
    ser.rts=False
    ser.dtr=True
    try:
        ser.open()
        time.sleep(.15)
        ser.dtr=False
    finally:
        if ser.is_open:ser.close()
def load_via_picotool():
    """Fallback when Windows binds RP2040 ROM as RP2 Boot COM, no MSC drive."""
    insist(PICOTOOL.is_file(),"RPI-RP2 volume absent and picotool unavailable")
    boots=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2e8a,0x0003)]
    insist(len(boots)==1,"Need exactly one RP2040 ROM USB device")
    detail=subprocess.run([str(PICOTOOL),"info","-a"],capture_output=True,
                          text=True,errors="replace",timeout=15,check=False)
    m=re.search(r"flash id:\s*0x([0-9a-fA-F]+)",detail.stdout)
    insist(detail.returncode==0 and m and
           m.group(1).upper()==BOARD_SERIAL and
           re.search(r"type:\s+RP2040",detail.stdout),
           "ROM boot flash ID does not match the original COM7 board")
    result=subprocess.run([str(PICOTOOL),"load","-v","-x",str(IMAGE)],
                          capture_output=True,text=True,errors="replace",
                          timeout=45,check=False)
    insist(result.returncode==0 and "OK" in result.stdout and
           "rebooted to start the application" in result.stdout,
           "picotool flash verify/execute did not complete cleanly")
    return {"method":"picotool verified boot ROM","boot_port":boots[0].device,
            "flash_id":m.group(1).upper(),"uf2_programmed_once":True}

def flash():
    image=image_check()
    port=board()
    baseline=read_baseline(port,gate=0)
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/"KNX092_FLASH_STARTED.flag"
    insist(not marker.exists(),"Firmware flash already attempted here; no retry")
    insist(rom_volume() is None,"Already in RP2040 ROM mode")
    report={"stage":"flash","started":datetime.now().isoformat(),"before":baseline,
            "uf2":image,"motor_commands_sent":0,"flash_completed":False}
    marker.write_text("KNX092 firmware flashing started\n",encoding="utf8")
    try:
        try:enter_rom(port)
        except (serial.SerialException,OSError) as exc:
            report["cdc_exception"]=str(exc)
        until=time.monotonic()+15
        disk=None
        while time.monotonic()<until:
            disk=rom_volume()
            if disk:break
            time.sleep(.2)
        if disk is None:
            # Only if ROM is present and its hardware flash ID matches
            # the SAME pre-reset COM7 RP2040. Never try another CDC reset.
            report["alternate_bootloader"]=load_via_picotool()
        else:
            target=disk/"KNX092_M1.uf2"
            insist(not target.exists(),"ROM target already exists")
            try:shutil.copyfile(IMAGE,target)
            except OSError as exc:
                raise Refused("UF2 copy ambiguous, do not retry automatically: "+str(exc)) from exc
            report["uf2_submitted_once"]=True
        until=time.monotonic()+25
        while time.monotonic()<until:
            try:port=board();break
            except Refused:time.sleep(.25)
        else:raise Refused("RP2040 USB COM7 did not return")
        report["after"]=read_baseline(port,gate=1)
        report["flash_completed"]=True
        print("FLASH_OK",json.dumps({"board":BOARD_SERIAL,"port":port,
                                     "motor_gate":1,"ina_good":True}))
    finally:write_report("KNX092_FLASH",report)
def pulse(ms):
    insist(ms==150,"Only original authorized 150ms forward M1 pulse allowed")
    port=board()
    baseline=read_baseline(port,gate=1)
    marker=OUT/"KNX092_M1_PULSE_STARTED.flag"
    insist(not marker.exists(),"M1 pulse already attempted, manual review required before another")
    data={"stage":"M1_F_150","before":baseline,"triggered":False,
          "motor_physical_movement_confirmed":None,"trace":[],"raw_lines":[]}
    marker.write_text("KNX092 M1 F 150ms first attempt\n",encoding="utf8")
    lines=data["raw_lines"]
    try:
        with open_usb(port) as ser:
            ser.reset_input_buffer()
            try:
                command(ser,"INA")
                gather(ser,.6,lines)
                ma=latest(lines,INA)
                insist(ma and ma.group(1)=="1" and ma.group(5)=="1" and
                       -5<=int(ma.group(3))<=3,
                       "INA idle check changed immediately before MOTOR ARM")
                command(ser,"ARM MOTORS")
                armed=gather(ser,1.1,lines,lambda x:
                             x=="KNX085 ARMED_5S" or x.startswith("KNX085 REFUSED_ARM"))
                insist(armed and "KNX085 ARMED_5S" in lines,
                       "Motor arming refused")
                command(ser,"PULSE M1 F 150")
                got=gather(ser,1.0,lines,lambda x:
                            x.startswith("KNX085 PULSE_STARTED") or x.startswith("KNX085 REFUSED_"))
                insist(got and any(x.startswith("KNX085 PULSE_STARTED M1 F") for x in lines),
                       "M1 activation refused/no acknowledgment")
                data["triggered"]=True
                ended=gather(ser,1.2,lines,lambda x:x.startswith("KNX085 MOTOR_ENDED state="))
                insist(ended,"No automatic motor END confirmation")
                data["firmware_terminal_state"]=next(
                    (x.rsplit("=",1)[1] for x in reversed(lines)
                     if x.startswith("KNX085 MOTOR_ENDED state=")),None)
            finally:
                try:
                    command(ser,"STOP")
                    command(ser,"STATUS")
                    command(ser,"MSTATUS")
                    command(ser,"INA")
                    command(ser,"TRACE")
                    gather(ser,2.0,lines,lambda x:x=="KNX085 TRACE_END")
                except Exception as exc:
                    lines.append("KNX092_READBACK_EXCEPTION "+repr(exc))
    except Exception as exc:
        data["error"]=str(exc)
        raise
    finally:
        data["trace"]=[{"ms":int(m.group(1)),"shunt_raw":int(m.group(2)),
           "shunt_uV":int(m.group(3)),"bus_mv":int(m.group(4)),
           "valid":m.group(5)=="1",
           "current_ma_at_0_2ohm":round(int(m.group(3))/200,2)}
           for line in lines if (m:=TRACE.match(line))]
        data["trace_complete"]="KNX085 TRACE_END" in lines
        data["stop_ack"]="KNX085 STOPPED_ALL_OFF" in lines
        data["last_status"]=next((x for x in reversed(lines)
                                 if x.startswith("KNX085 STATUS")),None)
        data["after_motor"]=next((x for x in reversed(lines)
                                 if x.startswith("KNX085 MOTOR gate=")),None)
        data["peak_ma"]=max((x["current_ma_at_0_2ohm"] for x in data["trace"] if x["valid"]),default=None)
        report=write_report("KNX092_M1",data)
        if data["trace"]:
            csvpath=report.with_suffix(".csv")
            with csvpath.open("w",encoding="utf8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=list(data["trace"][0]))
                writer.writeheader()
                writer.writerows(data["trace"])
            print("TRACE_CSV",csvpath)
        print("M1_RESULT",json.dumps({k:v for k,v in data.items()
               if k in ("triggered","firmware_terminal_state","trace_complete",
                        "stop_ack","peak_ma","last_status","after_motor","error")}))
    insist(data["stop_ack"] and data["last_status"] and
           "tx_low=1 motors_low=1" in data["last_status"],
           "Post-pulse all-output-off verification not achieved")
    insist(data["trace_complete"] and len(data["trace"])>0,
           "Motor trace incomplete; inspect logs")
    insist(data.get("firmware_terminal_state")=="IDLE",
           "Firmware ended M1 in FAULT; logged protected cutoff, no repeat")
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["preflight","flash","verify","pulse"])
    parser.add_argument("--duration-ms",type=int,default=150)
    a=parser.parse_args()
    try:
        if a.action=="preflight":print("PREFLIGHT",json.dumps(read_baseline(board(),gate=0)))
        elif a.action=="flash":flash()
        elif a.action=="verify":print("VERIFY",json.dumps(read_baseline(board(),gate=1)))
        else:pulse(a.duration_ms)
        return 0
    except Exception as exc:
        print("KNX092_ABORT",type(exc).__name__,str(exc),file=sys.stderr)
        return 5
if __name__=="__main__":raise SystemExit(main())
