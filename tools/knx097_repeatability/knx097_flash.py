#!/usr/bin/env python3
"""KNX097 guarded flash and read-only firmware-state validator for office COM7."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import hashlib,json,re,sys,time,subprocess,shutil
import serial
from serial.tools import list_ports
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import knx092_office_usb_m1 as old

OUT=Path(r"C:\ASH\Workspace\Runtime\KNX097")
IMAGE=HERE/".pio"/"build"/"knx097_m1_repeat_30000"/"firmware.uf2"
SHA="d54632979a63dd6895f898f8923b6e9c94b72b93c6f874b9469dfe8dd792a2eb"
VERSION=re.compile(r"KNX097 M1_ALTERNATE duration_ms=30000 motor_gate=1 limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 next_dir=([RF]) legs_done=(\d) last_kind=(NONE|LOAD_RISE|TOO_SHORT_LOAD_RISE|CURRENT_CUT) last_dir=([RF-])")
STAMP=datetime.now().strftime("%Y%m%d_%H%M%S")
class Stop(RuntimeError):pass

def require(ok,msg):
    if not ok:raise Stop(msg)

def safe_file(label,data):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/f"KNX097_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n","utf8")
    print("EVIDENCE",p,flush=True)
    return p

def pin():
    require(IMAGE.is_file(),"PINNED KNX097 UF2 is missing")
    b=IMAGE.read_bytes()
    got=hashlib.sha256(b).hexdigest()
    require(got==SHA and len(b)==244736 and b[:4]==bytes.fromhex("5546320a"),
            "KNX097 UF2 SHA/size/header mismatch; refuse flash")
    return {"file":str(IMAGE),"size":len(b),"sha256":got}

def parse_version(lines):
    vs=[m for line in lines if (m:=VERSION.fullmatch(line))]
    require(vs,"No exact KNX097 firmware version/limits/sequence signature")
    m=vs[-1]
    return {"next_dir":m.group(1),"legs_done":int(m.group(2)),
            "last_kind":m.group(3),"last_dir":m.group(4)}

def verify(require_start=False):
    port=old.board() # Unique COM7 and exact RP2040 serial, ignores PC's CH340
    idle=old.read_baseline(port,gate=1)
    lines=[]
    with serial.Serial(port,115200,timeout=.14,write_timeout=.5) as ser:
        ser.reset_input_buffer()
        for _ in range(3):
            ser.write(b"KNX097\nMSTATUS\n")
            ser.flush()
            end=time.monotonic()+.55
            while time.monotonic()<end:
                line=ser.readline().decode("ascii","replace").strip()
                if line:lines.append(line)
    v=parse_version(lines)
    require(v["legs_done"]<=6,"Invalid leg counter")
    if require_start:
        require(v=={"next_dir":"R","legs_done":0,"last_kind":"NONE","last_dir":"-"},
                "KNX097 does not start at F-side with zero legs")
    require(idle.get("motor_idle") is True and idle.get("nominal_ma_max",999)<=3
            and idle.get("nominal_ma_min",-999)>=-5,"INA/motor not idle")
    result={"board":"COM7","serial":old.BOARD_SERIAL,"version":v,
            "config":idle["ina219_config"],"valid_idle_reads":idle["ina_samples"],
            "bus_mv":[idle["bus_mv_min"],idle["bus_mv_max"]],
            "nominal_ma":[idle["nominal_ma_min"],idle["nominal_ma_max"]]}
    print("VERIFIED",json.dumps(result),flush=True)
    return result

def flash_once():
    image=pin()
    port=old.board()
    # Starting firmware KNX096 documented a LOAD_RISE at F
    # and must be idle before any ROM reset.
    sys.path.insert(0,str(HERE.parent/"knx096_m1_fullstroke"))
    import knx096_host as prev
    prior=prev.verify_new(port)
    require(prior.get("endstop_status")=="LOAD_RISE" and prior["motor_idle"],
            "Not the documented F-side endstop before new firmware")
    OUT.mkdir(parents=True,exist_ok=True)
    flag=OUT/"KNX097_FLASH_STARTED.flag"
    require(not flag.exists(),"KNX097 flashing previously attempted; no retry")
    require(old.rom_volume() is None,"Unexpected BOOTSEL device before flash")
    report={"image":image,"initial_port":port,"prior_endstop":"F_LOAD_RISE",
            "completed":False,"motor_actions":0}
    flag.write_text("Attempted once: KNX097 ROM flash\n",encoding="utf8")
    try:
        old.enter_rom(port)
        volume=None
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            volume=old.rom_volume()
            if volume:break
            time.sleep(.15)
        if volume:
            dst=volume/"KNX097_R_F_3CYCLES.uf2"
            require(not dst.exists(),"Unexpected ROM target exists")
            shutil.copyfile(IMAGE,dst)
            report["method"]="RPI-RP2 UF2 mounted drive"
        else:
            exe=old.PICOTOOL
            require(exe.is_file(),"No boot volume/picotool")
            boots=[p for p in list_ports.comports() if (p.vid,p.pid)==(0x2e8a,0x0003)]
            require(len(boots)==1,"Not exactly one ROM RP2040")
            info=subprocess.run([str(exe),"info","-a"],capture_output=True,text=True,
                                errors="replace",timeout=18)
            match=re.search(r"flash id:\s*0x([0-9A-Fa-f]+)",info.stdout)
            require(info.returncode==0 and match and
                    match.group(1).upper()==old.BOARD_SERIAL and
                    re.search(r"type:\s+RP2040",info.stdout),
                    "RP2040 ROM flash identity mismatch")
            proc=subprocess.run([str(exe),"load","-v","-x",str(IMAGE)],
                                capture_output=True,text=True,errors="replace",
                                timeout=48)
            require(proc.returncode==0 and "OK" in proc.stdout and
                    "rebooted to start the application" in proc.stdout,
                    "picotool load/verify/reboot ambiguous - no automatic retry")
            report["method"]="picotool verified load -v -x"
            report["flash_id"]=match.group(1).upper()
        limit=time.monotonic()+25
        while time.monotonic()<limit:
            try:
                port=old.board()
                break
            except old.Refused:
                time.sleep(.2)
        else:raise Stop("No same RP2040 COM7 after flash")
        report["postflight"]=verify(require_start=True)
        report["completed"]=True
    except Exception as e:
        report["error"]=repr(e)
        raise
    finally:
        safe_file("FLASH",report)
    print("KNX097 FLASH PASS no motor movement",flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=["pin","verify","flash"])
    args=ap.parse_args()
    try:
        if args.stage=="pin":print(json.dumps(pin()))
        elif args.stage=="verify":verify()
        else:flash_once()
    except Exception as e:
        print("KNX097_REFUSED",repr(e),file=sys.stderr)
        raise SystemExit(5)
