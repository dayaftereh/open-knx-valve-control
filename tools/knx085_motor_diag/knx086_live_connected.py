#!/usr/bin/env python3
"""KNX086: stage-by-stage RP2040 KNX085 flash + M1 current trace on the
previously proven KNX084 live test rig (KNX 1.3 + CH340 UPDI + M1/M2).
Only this exact board, USB identity, and pinned UF2. No KNX transmission.
Unlike the older isolated script, KNX/UPDI are expected in this profile.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

import serial
from serial.tools import list_ports
import knx085_one_shot as base
import knx085_bench_host as host

BOARD_SERIAL="E464401787522D33"
DATA_DIR=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX086_LIVE_M1")
TX_LIMIT=250
WATCH_SECONDS=2.6
STATUS_084=re.compile(r"KNX084 STATUS tx_low=(\d+) motors_low=(\d+) uart_ready=(\d+) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+)")
STATUS_085=host.STATUS

def require(value,why):
    if not value:raise RuntimeError(why)

def board_ports():
    rows=list(list_ports.comports())
    rp=[x for x in rows if (x.vid,x.pid)==(0x2e8a,0x000a)]
    updi=[x for x in rows if (x.vid,x.pid)==(0x1a86,0x7523)]
    require(len(rp)==1 and (rp[0].serial_number or "").upper()==BOARD_SERIAL,
            "Incorrect or nonunique RP2040 USB identity")
    require(len(updi)==1,
            "The known KNX084 live hardware profile expects exactly one CH340 UPDI")
    return rp[0].device,updi[0].device

def send(dev,text):
    dev.write((text+"\n").encode("ascii"))
    dev.flush()

def collect(dev,seconds,lines,until=None):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            raw=dev.readline()
        except (OSError,serial.SerialException) as e:
            raise RuntimeError("USB communication lost; no retry/second pulse") from e
        if raw:
            line=raw.decode("ascii","replace").strip()
            if line:
                lines.append(line)
                if until and until(line):return True
    return False

def usb_port(port):
    return serial.Serial(port,115200,timeout=.13,write_timeout=.5,
                         rtscts=False,dsrdtr=False)

def preflight_live():
    image=base.check_image()
    port,updi=board_ports()
    lines=[]
    with usb_port(port) as dev:
        dev.reset_input_buffer()
        send(dev,"STATUS")
        send(dev,"RXSTATS")
        send(dev,"TEMPS")
        collect(dev,2.0,lines)
        send(dev,"STATUS")
        send(dev,"RXSTATS")
        collect(dev,1.0,lines)
    statuses=[STATUS_084.match(x) for x in lines if x.startswith("KNX084 STATUS")]
    statuses=[x for x in statuses if x]
    require(len(statuses)>=2,"Expected KNX084 as-flashed baseline, not arbitrary image")
    require(all(s.group(1,2,3)==("1","1","1") for s in statuses),
            "KNX084 TX/motor outputs or temperature UART not idle")
    edge0,edge1=int(statuses[0].group(7)),int(statuses[-1].group(7))
    # A healthy KNX line can legitimately be quiet for several seconds;
    # never interpret missing *recent* edges as a cable-disconnect proof.
    # A >1M cumulative count + matching board fingerprint is historical
    # evidence this exact rig received KNX. User confirms current wiring.
    require(edge0>1000000 and edge1>=edge0,
            "Known KNX084 live hardware fingerprint / RX counter missing")
    temp={}
    for line in lines:
        m=host.TEMP.fullmatch(line.replace("KNX084 CH","KNX085 CH"))
        if m:temp[int(m.group(1))]=m
    require(len(temp)==4 and all(temp[i].group(2)=="1" and temp[i].group(5)=="0" for i in range(4)),
            "4 channels T0..T3 must be fault-free")
    return {"port":port,"updi":updi,"usb_serial":BOARD_SERIAL,
            "firmware":"KNX084","rx_edges_first":edge0,"rx_edges_last":edge1,
            "all_motor_outputs_low":True,"knx_tx_low":True,
            "temperature_c":{f"T{i}":float(temp[i].group(3)) for i in range(4)},
            "uf2":image}

def save(name,data):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    path=DATA_DIR/(name+"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("EVIDENCE_PATH",path)
    return path

def flash_once():
    start=preflight_live()
    save("KNX086_BEFORE_FLASH",start)
    port=start["port"]
    require(base.rom_volume() is None,
            "RP2040 already in ROM boot mode, no second reset/flash")
    # Prior KNX076/081/084 were successfully flashed on this same KNX
    # R17-removed setup. This is NOT claiming absolute proof under brownout.
    touch_error=None
    try:
        base.touch_rom(port)
    except (OSError,serial.SerialException) as exc:
        # KNX050: Windows reported serial-port removal mid-touch *because*
        # the USB reset had already succeeded. Check ROM once; never retry.
        touch_error=str(exc)
    volume=base.wait_rom_disk(seconds=15)
    require((volume/"INFO_UF2.TXT").is_file(),
            "RP2040 ROM UF2 board identity missing")
    target=volume/"KNX086_M1.uf2"
    require(not target.exists(),"UF2 target file already exists")
    try:
        shutil.copyfile(base.IMAGE,target)
    except OSError as exc:
        raise RuntimeError("UF2 write ambiguous; do NOT retry automatically") from exc
    new_port=base.wait_app(seconds=20)
    result={"starting_port":port,"new_port":new_port,
            "image_sha256":start["uf2"]["sha256"],
            "touch_error_during_usb_disappearance":touch_error,
            "uf2_copied_once":True}
    # Informational only: lack of INA readback is a safe motor block.
    save("KNX086_FLASH",result)
    return result

def passive_085():
    port,updi=board_ports()
    lines=[]
    with usb_port(port) as dev:
        dev.reset_input_buffer()
        send(dev,"STATUS")
        send(dev,"TEMPS")
        send(dev,"INA")
        collect(dev,4.2,lines)
        for _ in range(9):
            send(dev,"INA")
            collect(dev,.27,lines)
            try:
                ina=host.check_ina(lines)
                break
            except RuntimeError:
                continue
        else:
            raise RuntimeError("INA219 address/calibration/config/supply or idle gate FAILED; no motor")
    status=host.check_status(lines,gate_required=True,require_temps=True)
    tx_after=[STATUS_085.match(x) for x in lines if x.startswith("KNX085 STATUS")]
    require(all(x and x.group(1)=="1" for x in tx_after),
            "KNX085 unexpected KNX TX pin state")
    return {"port":port,"updi":updi,"serial":BOARD_SERIAL,
            "status":status,"ina":ina,"last_lines":lines[-40:]}

def summarize_r29_ina(lines):
    """200 mOhm/1W user-confirmed R29, shared M_VCC; USB read-only math."""
    m=host.latest(lines,host.INA)
    value={"r29_ohms":0.2,"r29_rated_w":1,
           "r29_source":"user-confirmed physically populated 2026-10-19",
           "measures":"shared M_VCC rail, not M1 exclusively",
           "physical_movement_observed":False}
    if not m:
        value["measurement_valid"]=False
        return value
    ok,bus,ma,overflow,idle=m.groups()
    value["measurement_valid"]=ok=="1" and overflow=="0"
    value["ina_bus_mv"]=int(bus)
    value["motor_ready_idle_gate"]=idle=="1"
    if value["measurement_valid"]:
        current=int(ma)
        value["shared_supply_ma_reported"]=current
        value["shunt_drop_mv_inferred"]=round(current*0.2,3)
        value["r29_dissipated_w_inferred"]=round((current/1000)**2*0.2,5)
        value["m_vcc_idle_over_25ma_gate"]=current>25
        value["motor_output_turned_on"]=False
    return value

def diagnose_085():
    """Read-only raw USB snapshot even if INA219 gate fails."""
    port,updi=board_ports()
    lines=[]
    with usb_port(port) as dev:
        dev.reset_input_buffer()
        for command in ("STATUS","MSTATUS","INA","TEMPS","RXSTATS"):
            send(dev,command)
        collect(dev,4.5,lines)
    require(any(line.startswith("KNX085 STATUS") for line in lines),
            "Board not running KNX085 test firmware")
    require(any(line.startswith("KNX085 INA read_ok=") for line in lines),
            "INA219 readback absent")
    require(any(line.startswith("KNX085 STATUS tx_low=1 motors_low=1")
                for line in lines),
            "TX or motor pins not all OFF")
    result={"port":port,"updi":updi,"mode":"READ_ONLY",
            "motor_activated":False,
            "r29_and_ina":summarize_r29_ina(lines),
            "raw_usb_lines":lines}
    try:
        result["motor_ready"]=bool(host.check_ina(lines) and
                                   host.check_status(lines,gate_required=True))
    except RuntimeError:
        result["motor_ready"]=False
        result["reason"]="INA219 idle voltage/current or temperature gate refused"
    save("KNX086_DIAGNOSTIC",result)
    return {"port":port,"updi":updi,"motor_ready":result["motor_ready"],
            "r29_and_ina":result["r29_and_ina"],
            "selected_lines":[l for l in lines if l.startswith(("KNX085 STATUS",
                "KNX085 INA","KNX085 MOTOR","KNX085 RXSTATS"))]}

def test_m1(duration=150):
    require(50<=duration<=TX_LIMIT,"Short one-shot pulse must be <=250ms")
    diagnostic=passive_085()
    # Only M1 forward is permitted in this initial current experiment.
    port=diagnostic["port"]
    record={"experiment":"M1_FORWARD_SHORT_CURRENT_PROFILE","port":port,
            "requested_ms":duration,"preflight":diagnostic,
            "pulse_ack":False,"stopped_confirmed":False,
            "raw_lines":[],"trace":[],"max_current_nominal_ma":None}
    lines=record["raw_lines"]
    try:
        with usb_port(port) as dev:
            dev.reset_input_buffer()
            try:
                send(dev,"STATUS")
                send(dev,"INA")
                collect(dev,.6,lines)
                host.check_status(lines,gate_required=True,require_temps=False)
                host.check_ina(lines)
                # Reserve one-shot before ARM; repeated launches cannot create
                # an unplanned second physical motor pulse.
                DATA_DIR.mkdir(parents=True,exist_ok=True)
                latch=DATA_DIR/"M1_FIRST_SHORT_PULSE_STARTED.flag"
                require(not latch.exists(),
                        "M1 one-shot already attempted. Review current trace and "
                        "explicitly plan the next run.")
                with os.fdopen(os.open(str(latch),os.O_CREAT|os.O_EXCL|os.O_WRONLY),
                               "w",encoding="utf8") as lockfile:
                    lockfile.write(f"M1 F {duration}ms at "
                                   f"{datetime.now().isoformat()}\n")
                send(dev,"ARM MOTORS")
                ok=collect(dev,1.3,lines,lambda l:l in
                    ("KNX085 ARMED_5S","KNX085 REFUSED_ARM_HARDWARE_OR_POWER_GATE"))
                require(ok and "KNX085 ARMED_5S" in lines,
                        "ARM refused or timed out, NO motor movement")
                send(dev,f"PULSE M1 F {duration}")
                ok=collect(dev,1.3,lines,lambda l:
                    l.startswith("KNX085 PULSE_STARTED") or
                    l.startswith("KNX085 REFUSED_"))
                require(ok and any(l.startswith("KNX085 PULSE_STARTED M1 F")
                                   for l in lines),
                        "M1 pulse refused; no motor start")
                record["pulse_ack"]=True
                ok=collect(dev,2.0,lines,lambda l:
                    l.startswith("KNX085 MOTOR_ENDED state="))
                require(ok,"No firmware motor-end acknowledgement")
                require("KNX085 MOTOR_ENDED state=IDLE" in lines,
                        "M1 terminated in FAULT or unexpected state")
            finally:
                # Redundant USB STOP even if power/INA/model fault is detected.
                try:
                    send(dev,"STOP")
                    send(dev,"STATUS")
                    send(dev,"INA")
                    send(dev,"TRACE")
                    collect(dev,1.5,lines,lambda l:l=="KNX085 TRACE_END")
                except (OSError,serial.SerialException,RuntimeError):
                    lines.append("HOST_STOP_OR_POSTREAD_FAILED")
    finally:
        # Preserve USB evidence even when the motor command returns failure.
        record["trace"]=[{
            "ms":int(m.group(1)),
            "shunt_raw":int(m.group(2)),
            "shunt_uv":int(m.group(3)),
            "bus_mv":int(m.group(4)),
            "valid":m.group(5)=="1",
            "nominal_ma_at_R29_200mohm":round(int(m.group(3))/200,3)}
            for line in lines if (m:=host.TRACE.fullmatch(line))]
        statuses=[STATUS_085.match(l) for l in lines if l.startswith("KNX085 STATUS")]
        statuses=[x for x in statuses if x]
        record["stopped_confirmed"]=bool(statuses and
            statuses[-1].group(2)=="1" and
            statuses[-1].group(9)=="IDLE" and
            any(l=="KNX085 STOPPED_ALL_OFF" for l in lines))
        valid=[a["nominal_ma_at_R29_200mohm"] for a in record["trace"] if a["valid"]]
        if valid: record["max_current_nominal_ma"]=max(valid)
        path=save("KNX086_M1_TRACE",record)
        if record["trace"]:
            csvpath=path.with_suffix(".csv")
            with csvpath.open("w",newline="",encoding="utf8") as file:
                cols=list(record["trace"][0].keys())
                writer=csv.DictWriter(file,fieldnames=cols)
                writer.writeheader();writer.writerows(record["trace"])
            print("CSV_PATH",csvpath)
    require(record["pulse_ack"] and record["stopped_confirmed"] and record["trace"],
            "M1 telemetry or STOP evidence incomplete; inspect saved logs")
    return {"samples":len(record["trace"]),
            "max_current_nominal_ma":record["max_current_nominal_ma"],
            "stopped_confirmed":record["stopped_confirmed"],
            "first_last":record["trace"][:2]+record["trace"][-2:]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["preflight","flash","read_ina","diagnose","m1"])
    p.add_argument("--duration-ms",type=int,default=150)
    a=p.parse_args()
    try:
        if a.action=="preflight":result=preflight_live()
        elif a.action=="flash":result=flash_once()
        elif a.action=="read_ina":result=passive_085()
        elif a.action=="diagnose":result=diagnose_085()
        else:result=test_m1(a.duration_ms)
        print("KNX086",a.action,"PASS",json.dumps(result,ensure_ascii=False))
        return 0
    except Exception as exc:
        print("KNX086",a.action,"STOP:",exc,file=sys.stderr)
        return 5
if __name__=="__main__":
    raise SystemExit(main())
