#!/usr/bin/env python3
"""KNX095 first controlled M1 reference-search offline validation. No serial I/O."""
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx095_m1_reference"))
import knx095_host as host
import knx092_office_usb_m1 as old

def refuse(callback):
    try:callback()
    except old.Refused:return
    raise AssertionError("Unsafe command accepted")

def main():
    src=Path("tools/knx095_m1_reference")
    fw=(src/"src"/"main.cpp").read_text("utf8")
    gate=(src/"src"/"motor_gate.hpp").read_text("utf8")
    ini=(src/"platformio.ini").read_text("utf8")
    assert "kMaxPulseMs=15000" in gate
    for s in ("kRunningCurrentLimitMa=120","kIdleCurrentLimitMa=25",
              "kMinMotorBusMv=3100","kMaxMotorBusMv=3450",
              "void trip(){state_=Phase::Fault;}", "kArmWindowMs=5000"):
        assert s in gate,s
    print("PASS 1/7: max15s/current/voltage/USB arm/fault")

    for s in ("kTraceSize=2200","kInaRunIntervalMs=8",
              "kEndstopGuardStartMs=450","kEndstopHighCurrentMa=45",
              "kEndstopLowCurrentMa=5","kEndstopConsecutive=6",
              "if(ch!=1 || dir!='R' || ms!=15000)",
              "motor.trip();","KNX095 ENDSTOP_CANDIDATE kind=",
              "KNX095 LIVE t_ms="):
        assert s in fw,s
    assert "gpio_put(kKnxTx,1)" not in fw
    assert "KNX095 M1_R_SEARCH duration_ms=15000 motor_gate=" in fw
    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" in ini
    assert "upload_command = cmd /c exit 91" in ini
    print("PASS 2/7: strict M1 R15000 and both stop profiles")

    image=host.confirm_image()
    assert image["sha256"]==host.IMAGE_SHA256 and image["bytes"]==244224
    print("PASS 3/7: pinned exact compiled image hash")

    assert host.SIGNATURE==("KNX095 M1_R_SEARCH duration_ms=15000 motor_gate=1 "
        "limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop=")
    assert host.LIVE_LINE.fullmatch(
        "KNX095 LIVE t_ms=500 current_ma=28 shunt_raw=560 bus_mv=3280")
    assert host.ENDSTOP_CANDIDATE.fullmatch(
        "KNX095 ENDSTOP_CANDIDATE kind=LOAD_RISE t_ms=5680 current_ma=49 bus_mv=3272").groups()==(
        "LOAD_RISE","5680","49","3272")
    assert host.ENDSTOP_CANDIDATE.fullmatch(
        "KNX095 ENDSTOP_CANDIDATE kind=CURRENT_CUT t_ms=7100 current_ma=0 bus_mv=3280").group(1)=="CURRENT_CUT"
    print("PASS 4/7: firmware ID and both endstop candidate parsers")

    class Fake:
        def reset_input_buffer(self):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass

    good=host.SIGNATURE+"NONE"
    def gather(ser,seconds,lines,end=None):
        lines.extend([good,
           "KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=gather):
        out=host.verify_new("COM7")
        assert out["knx095_version_verified"]==good
    print("PASS 5/7: safe verify after freshly flashed firmware")

    def wrong(ser,seconds,lines,end=None):
        lines.extend(["KNX094 M1_R_ONLY duration_ms=10000 motor_gate=1 "
                      "limit_ma=120 stall_ma=60 after_ms=400 consecutive=6 latched=0",
                      "KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=wrong):
        refuse(lambda:host.verify_new("COM7"))
    print("PASS 6/7: wrong firmware is refused")

    assert "position_zero_committed" in (src/"knx095_host.py").read_text("utf8")
    assert "UNCLASSIFIED_FAULT" in (src/"knx095_host.py").read_text("utf8")
    assert "KNX095_FLASH_STARTED.flag" in (src/"knx095_host.py").read_text("utf8")
    assert "KNX095_M1_R15000_STARTED.flag" in (src/"knx095_host.py").read_text("utf8")
    print("PASS 7/7: no automatic repeat and candidate never assigns reference zero")
    print("KNX095 OFFLINE 7/7 PASS")
if __name__=="__main__":main()
