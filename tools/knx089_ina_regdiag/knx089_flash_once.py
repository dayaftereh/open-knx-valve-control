#!/usr/bin/env python3
"""One-time guarded KNX085 -> KNX089 *motor-locked* ADC-register diagnostic flash.

Known OpenKNXValveControl V1.2 on LLO Home COM8, USB serial fixed.
This is a local script, not general upload; verifies exact SHA256 and
single RPI-RP2 UF2 volume. NO ARM/PULSE, NO UPDI write, NO KNX TX.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
from datetime import datetime
import serial
from serial.tools import list_ports

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"knx085_motor_diag"))
import knx085_one_shot as usb

IMAGE=HERE/".pio"/"build"/"knx089_ina_locked"/"firmware.uf2"
SHA="4715c992fc1ba61d90720a3b463ac172cd6499660a3d13ed3678793db916baef"
PORT="COM8"
SERIAL="E464401787522D33"
OUT=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX089_R29_0MV")
STATUS=re.compile(r"KNX085 STATUS tx_low=(\d) motors_low=(\d) uart_ready=(\d) snapshots=(\d+) timeout=(\d+) rejected=(\d+) rx_edges=(\d+) motor_gate=(\d) motor_state=(\w+)(?: .*)?")
def demand(ok,msg):
    if not ok:raise RuntimeError(msg)
def check_usb():
    boards=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2e8a,0x000a)]
    demand(len(boards)==1 and boards[0].device.upper()==PORT and
           (boards[0].serial_number or "").upper()==SERIAL,
           "USB VID/PID/serial not exact matching KNX085 RP2040 COM8")
    return boards[0].device
def validate_image():
    raw=IMAGE.read_bytes()
    demand(hashlib.sha256(raw).hexdigest()==SHA and len(raw)==243200,
           "Read-only motor-lock UF2 candidate checksum/size mismatch")
    demand(raw[:4]==bytes.fromhex("5546320A"),"Invalid UF2 magic")
    return len(raw)
def query_status(port,expected_gate):
    statuses=[]
    with serial.Serial(port,115200,timeout=.15,write_timeout=.5,
                       rtscts=False,dsrdtr=False) as dev:
        dev.reset_input_buffer()
        for j in range(3):
            dev.write(b"STATUS\n")
            end=time.monotonic()+1.0
            while time.monotonic()<end:
                ln=dev.readline().decode("ascii","replace").strip()
                m=STATUS.fullmatch(ln)
                if m:statuses.append(m)
    demand(len(statuses)>=2,"No 2 reliable KNX085 STATUS replies")
    demand(all(m.group(1,2,3,8,9)==("1","1","1",str(expected_gate),"IDLE")
               for m in statuses),
           "KNX_TX, motor pins, UART or firmware gate unexpected")
    return {"gate":expected_gate,"rx_edges_before":int(statuses[0].group(7)),
            "rx_edges_after":int(statuses[-1].group(7))}
def execute():
    validate_image()
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/"KNX089_ONE_FLASH_STARTED.flag"
    demand(not marker.exists(),"KNX089 ROM flash already attempted; no double reset")
    port=check_usb()
    before=query_status(port,1)
    demand(usb.rom_volume() is None,
           "Already in RP2040 ROM mode; do not initiate another reset")
    marker.write_text("KNX089 one-shot diagnostic flash "
                      +datetime.now().isoformat()+"\n",encoding="utf8")
    data={"time":datetime.now().isoformat(),"before":before,"image_sha256":SHA,
          "bytes":243200,"motor_commands_sent":False,"motor_moved":False}
    try:
        try:
            usb.touch_rom(port)
        except (serial.SerialException,OSError) as exc:
            data["cdc_1200_port_disappearance"]=str(exc)
        volume=usb.wait_rom_disk(seconds=15)
        board_id=(volume/"INFO_UF2.TXT").read_text(encoding="ascii",errors="replace")
        demand("Board-ID: RPI-RP2" in board_id,
               "Unexpected BOOTSEL disk identity")
        target=volume/"KNX089_INA_REGS.uf2"
        demand(not target.exists(),"UF2 target already exists")
        try:shutil.copyfile(IMAGE,target)
        except OSError as exc:
            raise RuntimeError("Ambiguous UF2 copy, no automatic retry") from exc
        data["uf2_copied_once"]=True
        post=usb.wait_app(seconds=20)
        demand(post.upper()==PORT,"USB port changed after flash")
        data["after"]=query_status(post,0)
        data["verified"]=True
        print("KNX089 LOCKED REGDIAG FLASH SUCCESS; USB",post,
              "motor_gate=0, tx_low=1, motors_low=1")
        return 0
    finally:
        report=OUT/("KNX089_FLASH_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
        report.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        print("FLASH_EVIDENCE",report)
if __name__=="__main__":
    try:raise SystemExit(execute())
    except Exception as exc:
        print("KNX089_FLASH_REFUSED_OR_FAILED",exc,file=sys.stderr)
        raise SystemExit(5)
