#!/usr/bin/env python3
"""KNX096 one-shot office M1 bounded 30s opposite end full stroke.

Stages:
  preflight: exact USB RP2040 COM7, KNX085 gate1, sane INA219 idle
  flash: verified new KNX096 UF2 via RP2040 BOOTSEL/picotool, no motion
  verify: KNX096 firmware signature, motor idle, INA219 healthy
  pulse: exactly one ARM + M1 F 30000, record load-rise/cutoff candidate and trace, STOP, save JSON+CSV
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

IMAGE=HERE/".pio"/"build"/"knx096_m1_fullstroke_30000"/"firmware.uf2"
IMAGE_SHA256="4ac733f5a8ad72c4ab3685042f1f390546d66b1b3bb306a0bf8e14db41ffa45c"
OUT=Path(r"C:\ASH\Workspace\Runtime\KNX096")
ROMTOOL=old.PICOTOOL
SIGNATURE=("KNX096 M1_F_SEARCH duration_ms=30000 motor_gate=1 "
           "limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop=")
DURATION_MS=30000
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
                "UNPINNED new KNX096 UF2: "+sha)
    fail_unless(blob[:4]==bytes.fromhex("5546320a"),"Invalid UF2 header")
    return {"image":str(IMAGE),"bytes":len(blob),"sha256":sha}

def verify_new(port,require_fresh=False):
    baseline=old.read_baseline(port,gate=1)
    samples=[]
    with old.open_usb(port) as ser:
        ser.reset_input_buffer()
        for i in range(3):
            old.command(ser,"KNX096")
            old.command(ser,"MSTATUS")
            old.gather(ser,.5,samples)
    good=[x for x in samples if x.startswith(SIGNATURE)]
    endstop_statuses=[x[len(SIGNATURE):] for x in good]
    fail_unless(len(good)>=2 and len(set(endstop_statuses))==1 and
                endstop_statuses[0] in ("NONE","LOAD_RISE","CURRENT_CUT"),
                "Wrong KNX096 firmware build or unexpected endstop state")
    if require_fresh:
        fail_unless(endstop_statuses[0]=="NONE",
                    "M1 reference-search history exists; no automatic re-drive")
    motor=[m for x in samples if (m:=MOTOR.match(x))]
    fail_unless(motor and motor[-1].group(1)=="IDLE",
                "M1 firmware not IDLE")
    baseline["knx096_version_verified"]=good[-1]
    baseline["endstop_status"]=endstop_statuses[0]
    return baseline

def rom_flash_once():
    approved=confirm_image()
    port=old.board()
    baseline=old.read_baseline(port,gate=1)
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/"KNX096_FLASH_STARTED.flag"
    fail_unless(not marker.exists(),"KNX096 flash has already been attempted, do not retry")
    fail_unless(old.rom_volume() is None,"Already in ROM, no 1200 baud reset")
    report={"stage":"flash","time":datetime.now().isoformat(),
            "old_baseline":baseline,"approved_image":approved,
            "motor_cmd_count":0,"programmed":False}
    marker.write_text("KNX096 one-time UF2 flashing commenced\n",encoding="utf8")
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
            target=disk/"KNX096_M1_F_30000.uf2"
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
        report["after"]=verify_new(port,require_fresh=True)
        report["verified"]=True
        print("FLASH_PASS KNX096 firmware, GPIO low, INA healthy")
    finally:
        output_report("KNX096_FLASH",report)

LIVE_LINE=re.compile(r"KNX096 LIVE t_ms=(\d+) current_ma=(-?\d+) shunt_raw=(-?\d+) bus_mv=(\d+)")
ENDSTOP_CANDIDATE=re.compile(
    r"KNX096 ENDSTOP_CANDIDATE kind=(LOAD_RISE|CURRENT_CUT) t_ms=(\d+) current_ma=(-?\d+) bus_mv=(\d+)")
def await_limited_motor_run(ser,lines,seconds):
    """Wait on MCU-timed 10s motor stop, log LIVE samples as they arrive."""
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        line=ser.readline().decode("ascii","replace").strip()
        if not line:continue
        lines.append(line)
        match=LIVE_LINE.fullmatch(line)
        if match:
            print("KNX096_MOTOR_LIVE",line,flush=True)
            # This host is not the primary current protection; firmware
            # independently samples 8ms, cuts on >120mA or >=60mA x6.
            # If USB sees an unexpectedly high single value, STOP too.
            elapsed,ma,raw,bus=map(int,match.groups())
            if elapsed>400 and (ma>=115 or bus<3100 or bus>3450):
                print("KNX096_HOST_STOP_GUARD",line,flush=True)
                old.command(ser,"STOP")
                # The trace will reveal whether a MCU cutoff was earlier.
                return True
        stop=ENDSTOP_CANDIDATE.fullmatch(line)
        if stop:print("KNX096_ENDSTOP_CURRENT_CANDIDATE",line,flush=True)
        if line.startswith("KNX085 MOTOR_ENDED state="):
            return True
    return False

def one_pulse():
    port=old.board()
    before=verify_new(port,require_fresh=True)
    marker=OUT/"KNX096B_M1_F30000_STARTED.flag"
    fail_unless(not marker.exists(),"This 800ms M1 attempt already started. No automatic repeat")
    data={"stage":"M1_F_30000","time":datetime.now().isoformat(),
          "before":before,"command_sent":False,
          "start_acknowledged":False,"finished_state":None,
          "motor_mechanically_seen":None,"motor_trace":[],
          "raw_lines":[]}
    marker.write_text("KNX096 M1 F 30000ms one-shot started\n",encoding="utf8")
    first=OUT/"KNX096_M1_F30000_20261020_101611.json"
    prior_marker=OUT/"KNX096_M1_F30000_STARTED.flag"
    fail_unless(first.is_file() and prior_marker.is_file(),
                "Missing preserved evidence of first stopped test")
    failure=json.loads(first.read_text(encoding="utf8"))
    fail_unless(failure.get("command_sent") is True and
                failure.get("start_acknowledged") is False and
                failure.get("stop_ack") is True and
                len(failure.get("motor_trace",[]))==0 and
                "motors_low=1" in str(failure.get("after_gpio","")),
                "First failed F attempt is not a verified safe pre-sample STOP")
    data["review_of_first_aborted_attempt"]=str(first)
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
                old.command(ser,"PULSE M1 F 30000")
                data["command_sent"]=True
                ack=old.gather(ser,1.2,lines,lambda s:
                               s.startswith("KNX085 PULSE_STARTED") or
                               s.startswith(("KNX085 REFUSED_","KNX096 REFUSED_")))
                fail_unless(ack and any(s.startswith("KNX085 PULSE_STARTED M1 F duration_ms=30000")
                                        for s in lines[-8:]),
                            "Pulse not acknowledged, no retry")
                data["start_acknowledged"]=True
                done=await_limited_motor_run(ser,lines,33.0)
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
                    old.command(ser,"KNX096")
                    old.command(ser,"TRACE")
                    old.gather(ser,140.0,lines,lambda s:s=="KNX085 TRACE_END")
                except Exception as exc:
                    lines.append("KNX096 STOP_OR_TRACE_READBACK_ERROR "+repr(exc))
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
        data["knx096_signature"]=next((s for s in reversed(lines)
               if s.startswith(SIGNATURE)),None)
        live=[]
        for l in lines:
            m=LIVE_LINE.fullmatch(l)
            if m:
                ms,ma,raw,mv=map(int,m.groups())
                live.append({"ms":ms,"ma":ma,"shunt_raw":raw,"bus_mv":mv})
        data["live_updates"]=live
        candidates=[{"kind":m.group(1),"ms":int(m.group(2)),
                     "ma":int(m.group(3)),"bus_mv":int(m.group(4))}
                    for l in lines if (m:=ENDSTOP_CANDIDATE.fullmatch(l))]
        data["endstop_candidates"]=candidates
        data["search_result"]=(
            "ENDSTOP_CANDIDATE_"+candidates[0]["kind"]
            if candidates and data.get("finished_state")=="FAULT"
            else "TIME_LIMIT_NO_ENDSTOP"
            if data.get("finished_state")=="IDLE"
            else "UNCLASSIFIED_FAULT")
        data["position_zero_committed"]=False
        data["position_fullstroke_committed"]=False
        data["stalled_or_overcurrent"]=data.get("finished_state")=="FAULT"
        data["actual_sampled_duration_ms"]=t[-1]["ms"] if t else 0
        saved=output_report("KNX096B_M1_F30000",data)
        if t:
            csvpath=saved.with_suffix(".csv")
            with csvpath.open("w",encoding="utf8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=list(t[0]))
                writer.writeheader()
                writer.writerows(t)
            print("CSV",csvpath)
        print("KNX096_REFERENCE_SEARCH_RESULT",json.dumps({k:v for k,v in data.items()
              if k in ("start_acknowledged","finished_state","search_result",
              "endstop_candidates","position_zero_committed","position_fullstroke_committed","peak_ma",
              "stop_ack","trace_complete","after_gpio","after_ina",
              "knx096_signature","error")},ensure_ascii=False),flush=True)
    fail_unless(data["start_acknowledged"],"No valid M1 start ACK")
    fail_unless(data["stop_ack"] and data["after_gpio"] and
                "motors_low=1" in data["after_gpio"] and
                "tx_low=1" in data["after_gpio"],"M1 output off unverified")
    fail_unless(data["trace_complete"] and data["motor_trace"],"No valid current trace")
    fail_unless(data.get("search_result")!="UNCLASSIFIED_FAULT",
                "Motor fault without endstop candidate: no homing declared")
    # Only a candidate! Zero position must be independently confirmed.
    # No automatic re-drive or fault-clear.

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
        print("KNX096_ABORT",type(exc).__name__,str(exc),file=sys.stderr)
        return 5
if __name__=="__main__":raise SystemExit(main())
