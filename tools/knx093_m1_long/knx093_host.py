#!/usr/bin/env python3
"""KNX093 one-shot office M1 reverse 800ms listening test.

Stages:
  preflight: exact USB RP2040 COM7, KNX085 gate1, sane INA219 idle
  flash: verified new KNX093 UF2 via RP2040 BOOTSEL/picotool, no motion
  verify: KNX093 firmware signature, motor idle, INA219 healthy
  pulse: exactly one ARM + M1 R 800, read INA trace, STOP, save JSON+CSV
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import knx092_office_usb_m1 as old

IMAGE=HERE/".pio"/"build"/"knx093_m1_reverse_800"/"firmware.uf2"
IMAGE_SHA256="f10743ac5b5e33e0969a04e34c53d353ec832ffb2009a29fcdfd90417447d619"
OUT=Path(r"C:\ASH\Workspace\Runtime\KNX093")
ROMTOOL=old.PICOTOOL
SIGNATURE=("KNX093 M1_R_ONLY duration_ms=800 motor_gate=1 "
           "limit_ma=120 stall_ma=90 after_ms=100 consecutive=4 latched=")
DURATION_MS=800
TRACE=old.TRACE
STATUS=old.STATUS
INA=old.INA
MOTOR=re.compile(r"KNX085 MOTOR gate=1 state=(\w+) channel=(\d+) direction=(.) duration_ms=(\d+) peak_ma=(\d+)")

def fail_unless(x,msg):
    if not x:raise old.Refused(msg)

def output_report(stem,doc):
    OUT.mkdir(parents=True,exist_ok=True)
    name=OUT/(stem+"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
    name.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("EVIDENCE",name)
    return name

def confirm_image():
    fail_unless(IMAGE.is_file(),"Missing verified firmware UF2")
    blob=IMAGE.read_bytes()
    sha=hashlib.sha256(blob).hexdigest()
    fail_unless(sha==IMAGE_SHA256 and len(blob)>150000 and len(blob)<350000,
                "UNPINNED new KNX093 UF2: "+sha)
    fail_unless(blob[:4]==bytes.fromhex("5546320a"),"Invalid UF2 header")
    return {"image":str(IMAGE),"bytes":len(blob),"sha256":sha}

def verify_new(port):
    baseline=old.read_baseline(port,gate=1)
    samples=[]
    with old.open_usb(port) as ser:
        ser.reset_input_buffer()
        for i in range(3):
            old.command(ser,"KNX093")
            old.command(ser,"MSTATUS")
            old.gather(ser,.5,samples)
    good=[x for x in samples if x.startswith(SIGNATURE)]
    fail_unless(len(good)>=2 and all(x==SIGNATURE+"0" for x in good),
                "Wrong KNX093 firmware build, stall guard or armed history")
    motor=[m for x in samples if (m:=MOTOR.match(x))]
    fail_unless(motor and motor[-1].group(1)=="IDLE",
                "M1 firmware not IDLE")
    baseline["knx093_version_verified"]=good[-1]
    return baseline

def rom_flash_once():
    approved=confirm_image()
    port=old.board()
    baseline=old.read_baseline(port,gate=1)
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/"KNX093_FLASH_STARTED.flag"
    fail_unless(not marker.exists(),"KNX093 flash has already been attempted, do not retry")
    fail_unless(old.rom_volume() is None,"Already in ROM, no 1200 baud reset")
    report={"stage":"flash","time":datetime.now().isoformat(),
            "old_baseline":baseline,"approved_image":approved,
            "motor_cmd_count":0,"programmed":False}
    marker.write_text("KNX093 one-time UF2 flashing commenced\n",encoding="utf8")
    try:
        try:old.enter_rom(port)
        except (OSError,Exception) as exc:
            report["cdc_exception"]=str(exc)
        # COM7 disappears; on Windows RP2 Boot may enumerate as 2E8A:0003
        disk=None
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            disk=old.rom_volume()
            if disk:break
            time.sleep(.15)
        if disk:
            target=disk/"KNX093_M1_R_800.uf2"
            fail_unless(not target.exists(),"Unexpected existing UF2 target")
            import shutil
            shutil.copyfile(IMAGE,target)
            report["loader"]="verified RPI-RP2 UF2 disk"
        else:
            fail_unless(ROMTOOL.is_file(),"No RP2 disk and picotool missing")
            from serial.tools import list_ports
            boots=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2e8a,0x0003)]
            fail_unless(len(boots)==1,"Not exactly one ROM RP2040 boot device")
            info=subprocess.run([str(ROMTOOL),"info","-a"],capture_output=True,
                                text=True,errors="replace",timeout=20)
            m=re.search(r"flash id:\s*0x([0-9A-Fa-f]+)",info.stdout)
            fail_unless(info.returncode==0 and m and
                        m.group(1).upper()==old.BOARD_SERIAL and
                        re.search(r"type:\s+RP2040",info.stdout),
                        "ROM flash identity did not match source USB RP2040")
            report["rom_identity"]={"flash_id":m.group(1).upper(),"port":boots[0].device}
            loaded=subprocess.run([str(ROMTOOL),"load","-v","-x",str(IMAGE)],
                                  capture_output=True,text=True,errors="replace",
                                  timeout=50)
            fail_unless(loaded.returncode==0 and "OK" in loaded.stdout and
                        "rebooted to start the application" in loaded.stdout,
                        "RP2040 ROM programming failed or unverified")
            report["loader"]="picotool load -v -x"
        report["programmed"]=True
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            try:
                port=old.board()
                break
            except old.Refused:time.sleep(.2)
        else:
            raise old.Refused("COM7 RP2040 did not return after flashing")
        report["after"]=verify_new(port)
        report["verified"]=True
        print("FLASH_PASS KNX093 firmware, GPIO low, INA healthy")
    finally:
        output_report("KNX093_FLASH",report)

def one_pulse():
    port=old.board()
    before=verify_new(port)
    marker=OUT/"KNX093_M1_R800_STARTED.flag"
    fail_unless(not marker.exists(),"This 800ms M1 attempt already started. No automatic repeat")
    data={"stage":"M1_R_800","time":datetime.now().isoformat(),
          "before":before,"command_sent":False,
          "start_acknowledged":False,"finished_state":None,
          "motor_mechanically_seen":None,"motor_trace":[],
          "raw_lines":[]}
    marker.write_text("KNX093 M1 R 800ms one-shot started\n",encoding="utf8")
    lines=data["raw_lines"]
    try:
        with old.open_usb(port) as ser:
            ser.reset_input_buffer()
            try:
                old.command(ser,"INA")
                old.gather(ser,.6,lines)
                sample=old.latest(lines,INA)
                fail_unless(sample and sample.group(1)=="1" and
                            sample.group(5)=="1" and -5<=int(sample.group(3))<=3,
                            "INA current not idle at the moment of ARM")
                old.command(ser,"ARM MOTORS")
                ack=old.gather(ser,1.1,lines,lambda s:
                               s=="KNX085 ARMED_5S" or s.startswith("KNX085 REFUSED_ARM"))
                fail_unless(ack and any(s=="KNX085 ARMED_5S" for s in lines[-7:]),
                            "ARM refused")
                old.command(ser,"PULSE M1 R 800")
                data["command_sent"]=True
                ack=old.gather(ser,1.2,lines,lambda s:
                               s.startswith("KNX085 PULSE_STARTED") or
                               s.startswith(("KNX085 REFUSED_","KNX093 REFUSED_")))
                fail_unless(ack and any(s.startswith("KNX085 PULSE_STARTED M1 R duration_ms=800")
                                        for s in lines[-8:]),
                            "Pulse not acknowledged, no retry")
                data["start_acknowledged"]=True
                done=old.gather(ser,2.0,lines,lambda s:
                                s.startswith("KNX085 MOTOR_ENDED state="))
                fail_unless(done,"No STOP/FAULT completion within USB timeout")
                data["finished_state"]=next((s.split("state=",1)[1]
                          for s in reversed(lines)
                          if s.startswith("KNX085 MOTOR_ENDED state=")),None)
            finally:
                try:
                    old.command(ser,"STOP")
                    old.command(ser,"STATUS")
                    old.command(ser,"MSTATUS")
                    old.command(ser,"INA")
                    old.command(ser,"KNX093")
                    old.command(ser,"TRACE")
                    old.gather(ser,4.2,lines,lambda s:s=="KNX085 TRACE_END")
                except Exception as exc:
                    lines.append("KNX093 STOP_OR_TRACE_READBACK_ERROR "+repr(exc))
    except Exception as exc:
        data["error"]=str(exc)
    finally:
        data["motor_trace"]=[{"ms":int(m.group(1)),"shunt_raw":int(m.group(2)),
              "shunt_uV":int(m.group(3)),"bus_mv":int(m.group(4)),
              "valid":m.group(5)=="1",
              "ma_at_R29_200mohm":round(int(m.group(3))/200,3)}
              for x in lines if (m:=TRACE.match(x))]
        t=data["motor_trace"]
        data["peak_ma"]=max((s["ma_at_R29_200mohm"] for s in t if s["valid"]),default=None)
        data["trace_complete"]="KNX085 TRACE_END" in lines
        data["stop_ack"]="KNX085 STOPPED_ALL_OFF" in lines
        data["motor_status"]=next((s for s in reversed(lines)
               if s.startswith("KNX085 MOTOR gate=")),None)
        data["after_gpio"]=next((s for s in reversed(lines)
               if s.startswith("KNX085 STATUS")),None)
        data["after_ina"]=next((s for s in reversed(lines)
               if s.startswith("KNX085 INA read_ok=")),None)
        data["knx093_signature"]=next((s for s in reversed(lines)
               if s.startswith(SIGNATURE)),None)
        saved=output_report("KNX093_M1_R800",data)
        if t:
            csvpath=saved.with_suffix(".csv")
            with csvpath.open("w",encoding="utf8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=list(t[0]))
                writer.writeheader()
                writer.writerows(t)
            print("CSV",csvpath)
        print("M1_R800_RESULT",json.dumps({k:v for k,v in data.items()
              if k in ("start_acknowledged","finished_state","peak_ma",
              "stop_ack","trace_complete","after_gpio","after_ina",
              "knx093_signature","error")},ensure_ascii=False))
    fail_unless(data["start_acknowledged"],"No valid M1 start ACK")
    fail_unless(data["stop_ack"] and data["after_gpio"] and
                "motors_low=1" in data["after_gpio"] and
                "tx_low=1" in data["after_gpio"],"M1 output off unverified")
    fail_unless(data["trace_complete"] and data["motor_trace"],"No valid current trace")
    fail_unless(data["finished_state"]=="IDLE",
                "Stall/overcurrent fault indicated; DO NOT REPEAT")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["preflight","flash","verify","pulse"])
    args=parser.parse_args()
    try:
        if args.action=="preflight":
            print("PREFLIGHT",json.dumps(old.read_baseline(old.board(),gate=1)))
        elif args.action=="flash":
            rom_flash_once()
        elif args.action=="verify":
            print("VERIFY",json.dumps(verify_new(old.board())))
        elif args.action=="pulse":
            one_pulse()
        return 0
    except Exception as exc:
        print("KNX093_ABORT",type(exc).__name__,str(exc),file=sys.stderr)
        return 5
if __name__=="__main__":raise SystemExit(main())
