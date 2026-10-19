#!/usr/bin/env python3
"""KNX085 one-shot M1 diagnostic deployment + 150 ms current recording.

DEFAULT: plan only (no serial port opened, no bootloader, no movement).
EXECUTE: requires physical KNX/UPDI isolation and independently checked
guards before touching the RP2040 USB firmware. Intended for user to run,
not for an unattended agent. Never use on a live KNX TP connection.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from serial.tools import list_ports
import serial

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
BUNDLE=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX085-M1-20261019")
IMAGE=BUNDLE/"knx085_bench_unlocked.uf2"
# Exactly this separately reviewed and compiled candidate; never accept an
# arbitrary UF2 path from the command line.
IMAGE_SHA256="86cbf6942fd12eba07402c52842ba7543cabd2c2a557a329607c954388a54750"
SERIAL="E464401787522D33"
APP_VIDPID=(0x2e8a,0x000a)
ROM_VIDPID=(0x2e8a,0x0003)
UPDI_VIDPID=(0x1a86,0x7523)
RX_STATS=re.compile(r"KNX084 RXSTATS edges=(\d+) ")
FW_STATUS=re.compile(r"KNX084 STATUS tx_low=(\d+) motors_low=(\d+) uart_ready=(\d+) snapshots=(\d+)")
TEMP=re.compile(r"KNX084 CH T([0-3]) valid=([01]) temp_c=(NA|-?\d+(?:\.\d+)?) flags=(\d+) fault=(\d+)")

class Refused(RuntimeError):
    pass

def demand(ok:bool,message:str)->None:
    if not ok:
        raise Refused(message)

def serial_rows():
    return list(list_ports.comports())

def check_image()->dict:
    demand(IMAGE.is_file(),"Precompiled KNX085 M1 UF2 missing at "+str(IMAGE))
    raw=IMAGE.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    demand(digest==IMAGE_SHA256,"UF2 SHA-256 mismatch: refusing different/modified firmware")
    demand(len(raw)%512==0 and 1024<=len(raw)<=1024*1024,
           "UF2 size/block alignment invalid")
    demand(raw.startswith(bytes.fromhex("5546320A")),"UF2 magic invalid")
    return {"path":str(IMAGE),"sha256":digest,"bytes":len(raw)}

def check_operator(args)->None:
    required=(
        args.knx_physically_disconnected,
        args.updi_physically_disconnected,
        args.usb_only_power,
        args.physical_power_cut_available,
    )
    demand(all(required),
           "NEVER flash on connected KNX/UPDI. Physically disconnect KNX TP "
           "and CN1/UPDI, use USB-only supply, and have an accessible "
           "physical power cutoff. All four confirmations are required.")
    demand(50<=args.duration_ms<=250,"Only 50..250 ms M1 one-shot pulse is allowed")

def check_usb_ports()->str:
    rows=serial_rows()
    updi=[p.device for p in rows if (p.vid,p.pid)==UPDI_VIDPID]
    demand(not updi,"CH340/UPDI still attached ("+", ".join(updi)+"). Disconnect CN1.")
    app=[p for p in rows if (p.vid,p.pid)==APP_VIDPID]
    demand(len(app)==1,"Expected exactly one RP2040 application USB device")
    demand((app[0].serial_number or "").upper()==SERIAL,
           "Wrong RP2040 USB serial. No firmware upload.")
    return app[0].device

def capture_idle(port:str,seconds:float=3.2)->dict:
    # Observation only: never send STOP/MOTOR/KNX telegram to KNX084.
    lines=[]
    with serial.Serial(port,115200,timeout=.18,write_timeout=.5,
                       rtscts=False,dsrdtr=False) as s:
        s.reset_input_buffer()
        s.write(b"STATUS\nRXSTATS\nTEMPS\n")
        mid=time.monotonic()+seconds/2
        end=time.monotonic()+seconds
        second=False
        while time.monotonic()<end:
            if not second and time.monotonic()>=mid:
                s.write(b"STATUS\nRXSTATS\nTEMPS\n")
                second=True
            line=s.readline().decode("ascii","replace").strip()
            if line: lines.append(line)
    status=[FW_STATUS.search(x) for x in lines if x.startswith("KNX084 STATUS")]
    status=[x for x in status if x]
    demand(len(status)>=1,"Board is not running expected KNX084 baseline")
    demand(all(s.group(1,2,3)==("1","1","1") for s in status),
           "KNX TX/motor GPIO/ATtiny UART baseline not all healthy")
    rx=[int(m.group(1)) for x in lines if (m:=RX_STATS.match(x))]
    demand(len(rx)>=2,"Cannot verify quiet/disconnected KNX RX baseline")
    demand(rx[-1]==rx[0],
           f"KNX RX edges changed ({rx[0]} to {rx[-1]}): bus activity detected. "
           "Do not restart the RP2040 while connected to KNX.")
    by_channel={}
    for x in lines:
        match=TEMP.match(x)
        if match: by_channel[int(match.group(1))]=match
    demand(len(by_channel)==4 and all(by_channel[n].group(2)=="1" and
        by_channel[n].group(5)=="0" for n in range(4)),
        "Four valid ATtiny sensor temperatures required before flashing")
    return {"port":port,"firmware":"KNX084","tx_low":True,"motors_low":True,
            "rx_edges_first":rx[0],"rx_edges_last":rx[-1],
            "temperatures_c":{f"T{n}":float(by_channel[n].group(3)) for n in range(4)}}

def rom_volume()->Path|None:
    valid=[]
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        info=Path(f"{letter}:\\INFO_UF2.TXT")
        try:
            if info.is_file():
                body=info.read_text(encoding="ascii",errors="replace")
                if "Board-ID: RPI-RP2" in body:
                    valid.append(info.parent)
        except OSError:
            continue
    demand(len(valid)<=1,"Multiple RPI-RP2 ROM disks found; abort")
    return valid[0] if valid else None

def touch_rom(port:str)->None:
    # Arduino-Pico 1200-baud CDC control transfer, same routine as KNX037.
    # MUST NOT be called while KNX TP is connected. Never open CH340.
    s=serial.Serial()
    s.port=port
    s.baudrate=1200
    s.timeout=.25
    s.write_timeout=.25
    s.rts=False
    s.dtr=True
    try:
        s.open()
        time.sleep(.15)
        s.dtr=False
    finally:
        if s.is_open:s.close()

def wait_rom_disk(seconds:float=15)->Path:
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        drive=rom_volume()
        if drive is not None:
            # Presence of the expected RP2040 ROM USB VID/PID is additional
            # evidence; Windows WinUSB driver is NOT needed for UF2 drive.
            return drive
        time.sleep(.2)
    raise Refused("BOOTSEL entered but no verified RPI-RP2 UF2 disk appeared")

def wait_app(seconds:float=20)->str:
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        matches=[p for p in serial_rows() if (p.vid,p.pid)==APP_VIDPID and
                 (p.serial_number or "").upper()==SERIAL]
        if len(matches)==1:return matches[0].device
        demand(len(matches)==0,"Multiple matching RP2040 USB applications")
        time.sleep(.25)
    raise Refused("UF2 submitted but expected RP2040 application COM port did not return")

def flash_exact_uf2(port:str)->str:
    demand(rom_volume() is None,
           "Board already in RP2040 ROM mode; refuse duplicate boot/upload")
    touch_rom(port)
    drive=wait_rom_disk()
    path=drive/"KNX085_M1.uf2"
    # ONE copy only. A disappearing mass-storage drive during this step is
    # normal for a successful UF2 load, but we DO NOT retry a failed copy.
    try:
        shutil.copyfile(IMAGE,path)
    except OSError as exc:
        raise Refused("UF2 copy ambiguous/failed, do NOT retry automatically: "+str(exc)) from exc
    return wait_app()

def evaluate_knx085(port:str,lines:list[str])->None:
    # Read-only sanity, not a motor start.
    from knx085_bench_host import check_status,check_ina
    with serial.Serial(port,115200,timeout=.18,write_timeout=.5,
                       rtscts=False,dsrdtr=False) as s:
        s.reset_input_buffer()
        s.write(b"STATUS\nINA\nTEMPS\nMSTATUS\n")
        deadline=time.monotonic()+5.5
        while time.monotonic()<deadline:
            line=s.readline().decode("ascii","replace").strip()
            if line:lines.append(line)
        summary=check_status(lines,gate_required=True,require_temps=True)
        # Sample five healthy INA219 readings before permitting ARM.
        for _ in range(10):
            s.write(b"INA\n")
            t=time.monotonic()+.25
            while time.monotonic()<t:
                line=s.readline().decode("ascii","replace").strip()
                if line:lines.append(line)
            try:
                current=check_ina(lines)
                print("KNX085 INA idle validated:",json.dumps(current))
                break
            except RuntimeError:continue
        else:raise Refused("No stable INA219 idle/current measurement; refusing motor start")
        demand(summary["gate"]==1,"Wrong/locked firmware")

def confirm_not_previously_executed()->Path:
    BUNDLE.mkdir(parents=True,exist_ok=True)
    flag=BUNDLE/"M1_ONESHOT_RUN_STARTED.flag"
    demand(not flag.exists(),
           "M1 one-shot already initiated on this computer. Review its log "
           "before any repeat; no automatic second run.")
    return flag

def execute(args)->dict:
    # THESE CHECKS AND USB MONITOR ARE ALL BEFORE FLASH/RESET.
    check_operator(args)
    image=check_image()
    marker=confirm_not_previously_executed()
    port=check_usb_ports()
    baseline=capture_idle(port)
    print("PREFLIGHT PASS:",json.dumps(baseline,ensure_ascii=False))
    log_dir=BUNDLE/"logs"
    log_dir.mkdir(parents=True,exist_ok=True)
    run={"started_local":datetime.now().isoformat(timespec="seconds"),
         "board_serial":SERIAL,"original_port":port,"firmware":image,
         "preflight":baseline,"pulse_requested_ms":args.duration_ms,
         "direction":args.direction,"physical_isolation_operator_confirmed":True,
         "pulse_and_off_verified":False,
         "physical_movement_observed":None}
    report=log_dir/("KNX085_M1_ONESHOT_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
    run["report_path"]=str(report)
    try:
        port=flash_exact_uf2(port)
        run["flashed_port"]=port
        print("UF2 flash submitted, re-enumerated",port)
        lines=[]
        evaluate_knx085(port,lines)
        run["knx085_idle_lines"]=lines[-25:]
        # Durable one-shot flag is created BEFORE the first M1 pulse.
        fd=os.open(str(marker),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        with os.fdopen(fd,"w",encoding="utf-8") as file:
            file.write(f"Started {datetime.now().isoformat()} M1 {args.direction} "
                       f"{args.duration_ms}ms; operator review before repeat.\n")
        host=HERE/"knx085_bench_host.py"
        cmd=[sys.executable,str(host),"pulse","--port",port,
             "--expected-serial",SERIAL,"--direction",args.direction,
             "--duration-ms",str(args.duration_ms),
             "--knx-physically-unplugged","--updi-unplugged",
             "--usb-only-supply","--physical-usb-off-ready",
             "--output",str(log_dir)]
        proc=subprocess.run(cmd,cwd=str(REPO),capture_output=True,
                            text=True,errors="replace",timeout=35,check=False)
        run["motor_host_exit"]=proc.returncode
        run["motor_host_stdout"]=proc.stdout[-10000:]
        run["motor_host_stderr"]=proc.stderr[-3000:]
        # Host script only exits 0 after receiving MOTOR_ENDED IDLE, verified
        # all-off STATUS, and a non-empty INA shunt voltage time series.
        run["pulse_and_off_verified"]=proc.returncode==0
        demand(proc.returncode==0,
               "M1 host refused or failed; do not repeat without inspecting logs")
        print(proc.stdout)
        return run
    finally:
        report.write_text(json.dumps(run,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print("ONESHOT_REPORT",report)

def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("plan","execute"),nargs="?",default="plan")
    p.add_argument("--duration-ms",type=int,default=150)
    p.add_argument("--direction",choices=("F","R"),default="F")
    p.add_argument("--knx-physically-disconnected",action="store_true")
    p.add_argument("--updi-physically-disconnected",action="store_true")
    p.add_argument("--usb-only-power",action="store_true")
    p.add_argument("--physical-power-cut-available",action="store_true")
    return p.parse_args(argv)

def main(argv=None):
    args=parse_args(argv)
    if args.action=="plan":
        print(json.dumps({
            "action":"PLAN ONLY - no hardware operations",
            "serial":SERIAL,"image":str(IMAGE),"expected_sha256":IMAGE_SHA256,
            "pulse":"M1, one direction, 50..250ms max, 150ms default",
            "dry_run_commands":"KNX084 USB STATUS/RXSTATS/TEMPS only",
            "preconditions":["KNX physically disconnected",
                             "UPDI/CN1 disconnected and CH340 absent",
                             "USB-only regulated power and power cutoff available",
                             "no new KNX GPIO1 RX edges during observation",
                             "original KNX084 passive outputs LOW and T0..T3 valid",
                             "known SHA256 image and exact USB identity"],
            "result":"CSV/JSON INA219 shunt trace, no full homing-to-stop"
        },indent=2,ensure_ascii=False))
        return 0
    try:
        data=execute(args)
        print("KNX085 M1 RESULT:",json.dumps({
            "pulse_and_off_verified":data["pulse_and_off_verified"],
            "report":data.get("report_path"),
            "host_exit":data.get("motor_host_exit")
        },ensure_ascii=False))
        return 0
    except Exception as exc:
        print("KNX085 ONE_SHOT REFUSED/FAILED:",str(exc),file=sys.stderr)
        return 5

if __name__=="__main__":
    raise SystemExit(main())
