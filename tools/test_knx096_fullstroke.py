#!/usr/bin/env python3
"""KNX096 offline-only motor F full-travel safety and host contract tests."""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx096_m1_fullstroke"))
import knx096_host as host
import knx092_office_usb_m1 as old

def refuse(task):
    try: task()
    except old.Refused:return
    raise AssertionError("Unsafe state was not refused")

def main():
    fwdir=Path("tools/knx096_m1_fullstroke")
    fw=(fwdir/"src"/"main.cpp").read_text("utf8")
    gate=(fwdir/"src"/"motor_gate.hpp").read_text("utf8")
    ini=(fwdir/"platformio.ini").read_text("utf8")
    assert "kMaxPulseMs=30000" in gate
    for needle in ["kRunningCurrentLimitMa=120","kIdleCurrentLimitMa=25",
                   "kMinMotorBusMv=3100","kMaxMotorBusMv=3450",
                   "kArmWindowMs=5000","state_=Phase::Fault","void trip()"]:
        assert needle in gate,needle
    print("PASS max30s and fail-closed motor-current/supply safeguards")

    for needle in ["kTraceSize=4200","kInaRunIntervalMs=8",
                   "kEndstopGuardStartMs=450","kEndstopHighCurrentMa=45",
                   "kEndstopLowCurrentMa=5","kEndstopConsecutive=6",
                   "if(ch!=1 || dir!='F' || ms!=30000)",
                   "KNX096 ENDSTOP_CANDIDATE kind=",
                   "KNX096 LIVE t_ms=","motor.trip();",
                   "KNX096 M1_F_SEARCH duration_ms=30000"]:
        assert needle in fw,needle
    assert "gpio_put(kKnxTx,1)" not in fw
    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" in ini
    assert "upload_command = cmd /c exit 91" in ini
    print("PASS F-only stop on six rising/cut samples, complete trace")

    i=host.confirm_image()
    assert i["sha256"]==host.IMAGE_SHA256 and i["bytes"]==244224
    print("PASS exact pinned UF2 firmware hash")

    assert host.SIGNATURE==("KNX096 M1_F_SEARCH duration_ms=30000 motor_gate=1 "
              "limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop=")
    assert host.ENDSTOP_CANDIDATE.fullmatch("KNX096 ENDSTOP_CANDIDATE kind=LOAD_RISE t_ms=17200 current_ma=47 bus_mv=3280")
    assert host.ENDSTOP_CANDIDATE.fullmatch("KNX096 ENDSTOP_CANDIDATE kind=CURRENT_CUT t_ms=17200 current_ma=1 bus_mv=3280")
    assert host.LIVE_LINE.fullmatch("KNX096 LIVE t_ms=12000 current_ma=32 shunt_raw=640 bus_mv=3280")
    print("PASS MCU firmware fingerprint and opposite-end candidate parsers")

    class SerialFake:
        def reset_input_buffer(self):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    sig=host.SIGNATURE+"NONE"
    def replies(ser,seconds,lines,end=None):
        lines.extend([sig,"KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=SerialFake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=replies):
        v=host.verify_new("COM7",require_fresh=True)
        assert v["knx096_version_verified"]==sig
    print("PASS verified F firmware ID and fresh homing state")

    sig2=host.SIGNATURE+"LOAD_RISE"
    def old_state(ser,seconds,lines,end=None):
        lines.extend([sig2,"KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=SerialFake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=old_state):
        assert host.verify_new("COM7")["endstop_status"]=="LOAD_RISE"
        refuse(lambda:host.verify_new("COM7",require_fresh=True))
    print("PASS report known endpoint but disallow duplicate motion")

    def wrong(ser,seconds,lines,end=None):
        lines.extend(["KNX095 M1_R_SEARCH duration_ms=15000 motor_gate=1 limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop=NONE",
                      "KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=SerialFake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=wrong):
        refuse(lambda:host.verify_new("COM7",require_fresh=True))
    print("PASS wrong firmware refuses to arm")

    p=fwdir/"knx096_host.py"
    text=p.read_text("utf8")
    assert "PULSE M1 F 30000" in text and "PULSE M1 R" not in text
    assert "140.0" in text and "33.0" in text
    assert "position_zero_committed" in text and "position_fullstroke_committed" in text
    assert "KNX096_FLASH_STARTED.flag" in text
    assert "KNX096B_M1_F30000_STARTED.flag" in text
    assert "KNX096_M1_F30000_20261020_101611.json" in text
    assert 'PULSE_STARTED M1 F duration_ms=30000' in text
    assert 'PULSE_STARTED M1 R duration_ms=30000' not in text
    print("PASS single 30s F attempt, complete receive/readback, no auto reference assignment")
    print("KNX096 OFFLINE 8/8 PASS")
if __name__=="__main__":main()
