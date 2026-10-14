#!/usr/bin/env python3
"""KNX038 controlled first ATtiny3216/CH340 UPDI signature PREP.

Default is read-only filesystem/metadata. 'ping' sends UPDI via COM4 ONLY
after operator-confirmed physical 3.3-V/5-V level, pinout and power gates.
No ERASE, WRITE, FUSE, flash or HV activation path is implemented here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
BUILD = Path(r"C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX038-ATtiny3216-offline-20261014")
MANIFEST = BUILD / "manifest.json"
EXPECTED_HEX = BUILD / "attiny3216-temperature.hex"
EXPECTED_SIGNATURE = "1E9521"
PYMCUPROG = Path(sys.executable).parent / "pymcuprog.exe"
EXPECTED_USB = "1A86:7523"
EXPECTED_COM = "COM4"

class GateError(RuntimeError):
    pass

def require(test: bool, reason: str) -> None:
    if not test:
        raise GateError(reason)

def ports():
    from serial.tools import list_ports
    return list(list_ports.comports())

def verify_com(available, name=EXPECTED_COM):
    matches = [p for p in available
               if p.vid == 0x1A86 and p.pid == 0x7523]
    require(len(matches) == 1, "Exactly one CH340 VID1A86 PID7523 required")
    require(matches[0].device.upper() == name.upper(),
            "CH340 COM port changed; choose actual port explicitly")
    return matches[0]

def expected_signature_response(output: str) -> bool:
    match = re.search(r"(?im)^\s*Ping response:\s*([0-9a-f]{6})\s*$", output)
    if not match:
        return False
    code = match.group(1).upper()
    return code in {EXPECTED_SIGNATURE, "21951E"}


def verify_build() -> dict:
    require(MANIFEST.is_file() and EXPECTED_HEX.is_file(),
            "Expected isolated, previously compiled ATtiny HEX not available")
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(d.get("schema") == "openknx-valvecontrol/knx038-attiny-offline-v1",
            "Unexpected manifest schema")
    require(d.get("status") == "BUILD_ONLY_NO_DEVICE_SIGNATURE_NO_FLASH",
            "Unrecognized build status")
    require(d.get("board") == "ATtiny3216" and
            d.get("pio_environment") == "temperature",
            "Firmware target is not verified ATtiny3216")
    observed = hashlib.sha256(EXPECTED_HEX.read_bytes()).hexdigest()
    require(d.get("images",{}).get(EXPECTED_HEX.name,{}).get("sha256") == observed,
            "ATtiny HEX checksum changed")
    require(d.get("flash_authorized") is False and
            d.get("fuses_or_erase_authorized") is False,
            "Unsafe manifest authorizations")
    return {"hex":str(EXPECTED_HEX),"sha256":observed,
            "bytes":EXPECTED_HEX.stat().st_size,"target":"ATtiny3216",
            "expected_signature":EXPECTED_SIGNATURE}

def ready(args:argparse.Namespace) -> None:
    # Explicit flags alone do not replace real instrument measurements.
    gates={
        "execute":args.execute,
        "cn1_pin1_correctly_keyed":args.confirm_cn1_orientation,
        "target_VDD_measured_and_compatible":args.confirm_target_vdd,
        "programmer_UPDI_pin3_measured_at_target_safe_level":args.confirm_updi_level,
        "programmer_VCC_pin1_backfeed_isolated_or_qualified":args.confirm_cn1_power,
        "no_KNX_and_motors_connected":args.confirm_no_knx_motors,
    }
    missing=[k for k,v in gates.items() if not v]
    require(not missing,"BLOCKED: first real UPDI signature requires "+
            ", ".join(missing))

def ping(args:argparse.Namespace):
    ready(args)
    require(args.port.upper() == EXPECTED_COM,
            "Only explicitly identified COM4 is permitted")
    verify_com(ports(),args.port)
    verify_build()
    require(PYMCUPROG.is_file(),"pymcuprog.exe not installed")
    # pyserial Serial() in pymcuprog.serialupdi.physical starts default
    # RTS=True/DTR=True. This is an expected *logical* level, not a
    # measured electrical level; suitable only after external verification.
    command=[str(PYMCUPROG),"-d","attiny3216","-t","uart",
             "-u",args.port,"ping"]
    run=subprocess.run(command,cwd=BASE,capture_output=True,text=True,
                       encoding="utf-8",errors="replace",timeout=20,
                       check=False)
    combined=(run.stdout+"\n"+run.stderr)
    require(run.returncode == 0,
            "UPDI read-only ping failed: "+combined[-450:])
    # pymcuprog _action_ping builds reversed printable byte order, e.g.
    # 1E 95 21 is presented as 'Ping response: 21951E'.
    signature_seen = expected_signature_response(combined)
    require(signature_seen,
            "UPDI ping returned wrong/unknown chip signature: "+combined[-300:])
    return {"port":args.port,"command":"pymcuprog -d attiny3216 -t uart -u COM4 ping",
            "tool_success":True,"signature_verified_ATtiny3216":True,
            "device_output":combined[-900:],
            "writes_performed":False,"erasures_performed":False,
            "fuses_changed":False}

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",nargs="?",choices=("plan","probe","verify-build","ping"),
                   default="plan")
    p.add_argument("--port",default="COM4")
    for flag in ("--execute","--confirm-cn1-orientation",
                 "--confirm-target-vdd","--confirm-updi-level",
                 "--confirm-cn1-power","--confirm-no-knx-motors"):
        p.add_argument(flag,action="store_true")
    return p

def main():
    a=parser().parse_args()
    try:
        if a.action=="plan":
            print(json.dumps({
                "mode":"PLAN_ONLY_NO_COM_OPEN",
                "next":"CH340 UPDI read-only signature AFTER voltage measurement",
                "usb":EXPECTED_USB,"port":EXPECTED_COM,
                "intended_logical_UPDI_RTS":True,
                "pymcuprog_uses_default_pyserial_RTS_true":True,
                "UPDI_electrical_voltage_measured":False,
                "ATtiny_flash_or_erase_allowed":False},indent=2))
            return 0
        if a.action=="probe":
            p=verify_com(ports(),a.port)
            print(json.dumps({"COM":p.device,"VID":f"{p.vid:04X}",
                              "PID":f"{p.pid:04X}",
                              "no_port_open":True,"RTS_toggled":False}))
            return 0
        if a.action=="verify-build":
            print(json.dumps(verify_build(),indent=2))
            return 0
        print(json.dumps(ping(a),indent=2))
        return 0
    except (GateError,OSError,ValueError,subprocess.TimeoutExpired) as e:
        print("KNX038 BLOCKED:",str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
