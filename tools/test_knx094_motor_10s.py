#!/usr/bin/env python3
"""KNX094 offline-only contract tests; cannot open COM or move motor."""
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx094_motor_10s"))
import knx094_host as h
import knx092_office_usb_m1 as old

def main():
    base=Path(__file__).resolve().parent/"knx094_motor_10s"
    fw=(base/"src"/"main.cpp").read_text("utf8")
    gate=(base/"src"/"motor_gate.hpp").read_text("utf8")
    ini=(base/"platformio.ini").read_text("utf8")
    assert "kMaxPulseMs=10000" in gate and "kRunningCurrentLimitMa=120" in gate
    assert "kIdleCurrentLimitMa=25" in gate
    assert "kMinMotorBusMv=3100" in gate and "kMaxMotorBusMv=3450" in gate
    assert "state_=Phase::Fault;" in gate and "void trip()" in gate
    print("PASS timeout, current, supply, fault gates")
    for term in ["kTraceSize=1500","kInaRunIntervalMs=8","kStallGuardStartMs=400",
                 "kStallCurrentMa=60","kStallConsecutive=6",
                 "if(ch!=1 || dir!='R' || ms!=10000)",
                 "stallGuardTripped=true;","motor.trip();",
                 'Serial.print(F("KNX094 LIVE t_ms="))']:
        assert term in fw,term
    assert "gpio_put(kKnxTx,1)" not in fw
    assert '-DKNX085_HARDWARE_GATE_APPROVED=1' in ini
    print("PASS R-only 10s firmware guard, stall logic and streamed samples")
    image=h.confirm_image()
    assert image["sha256"]==h.IMAGE_SHA256 and image["bytes"]==243712
    print("PASS immutable exact image hash/size")
    assert h.SIGNATURE=="KNX094 M1_R_ONLY duration_ms=10000 motor_gate=1 limit_ma=120 stall_ma=60 after_ms=400 consecutive=6 latched="
    assert h.LIVE_LINE.fullmatch("KNX094 LIVE t_ms=600 current_ma=38 shunt_raw=760 bus_mv=3280").groups()==("600","38","760","3280")
    print("PASS firmware fingerprint/live-current parser")
    class Fake:
        def reset_input_buffer(self):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    good=h.SIGNATURE+"0"
    def gather(ser,seconds,lines,end=None):
        lines.extend([good,"KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=gather):
        assert h.verify_new("COM7")["knx094_version_verified"]==good
    print("PASS safe USB-only bench version accepted")
    def bad(ser,seconds,lines,end=None):
        lines.extend(["KNX093 M1_R_ONLY duration_ms=800 motor_gate=1 limit_ma=120 stall_ma=90 after_ms=100 consecutive=4 latched=0",
                      "KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=bad):
        try:h.verify_new("COM7")
        except old.Refused:pass
        else:raise AssertionError("Wrong firmware accepted")
    print("PASS outdated 800ms firmware refused")
    print("KNX094 OFFLINE 6/6 PASS")
if __name__=="__main__":main()
