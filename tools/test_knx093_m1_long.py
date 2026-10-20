#!/usr/bin/env python3
"""KNX093 motor-direction/timeout/stall and exact board identity offline tests."""
from __future__ import annotations
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx093_m1_long"))
import knx093_host as host
import knx092_office_usb_m1 as old

def check():
    base=Path(__file__).resolve().parent/"knx093_m1_long"
    header=(base/"src"/"motor_gate.hpp").read_text("utf8")
    fw=(base/"src"/"main.cpp").read_text("utf8")
    ini=(base/"platformio.ini").read_text("utf8")
    assert "kMaxPulseMs=800" in header
    assert "kRunningCurrentLimitMa=120" in header
    assert "kIdleCurrentLimitMa=25" in header
    assert "kMinMotorBusMv=3100" in header
    assert "kMaxMotorBusMv=3450" in header
    assert "void trip(){state_=Phase::Fault;}" in header
    print("PASS 1/6: MotorGate 800ms and fail-closed cutoffs")

    for token in ("kTraceSize=160","kStallGuardStartMs=100","kStallCurrentMa=90",
                  "kStallConsecutive=4","stallGuardTripped=true;",
                  "motor.trip();","if(ch!=1 || dir!='R' || ms!=800)",
                  'F("KNX093 REFUSED_ONLY_M1_R_800")',
                  'F("KNX093 M1_R_ONLY duration_ms=800 motor_gate=")'):
        assert token in fw,token
    assert "gpio_put(kKnxTx,1)" not in fw
    assert "PULSE M1 R 800" in (base/"knx093_host.py").read_text("utf8")
    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" in ini
    assert "upload_command = cmd /c exit 91" in ini
    print("PASS 2/6: exact M1 R-only and stall detect with 160 samples")

    img=host.confirm_image()
    assert img["sha256"]==host.IMAGE_SHA256 and 150000<img["bytes"]<350000
    print("PASS 3/6: verified compiled image hash")

    def port(device,serial,vid=0x2e8a,pid=0x000a):
        return SimpleNamespace(device=device,serial_number=serial,vid=vid,pid=pid)
    with patch.object(old.list_ports,"comports",return_value=[
         port("COM7",old.BOARD_SERIAL),port("COM8","",0x1a86,0x7523)]):
        assert old.board()=="COM7"
    with patch.object(old.list_ports,"comports",return_value=[
         port("COM7","WRONG"),port("COM8","",0x1a86,0x7523)]):
        try:old.board()
        except old.Refused:pass
        else:raise AssertionError("wrong RP2040 serial accepted")
    print("PASS 4/6: unique COM7 serial ID while other host CH340s remain")

    class Fake:
        def reset_input_buffer(self):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    signature=host.SIGNATURE+"0"
    old_gather=old.gather
    def fake_gather(ser,secs,lines,end=None):
        lines.extend([signature,
          "KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"])
        return True
    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=fake_gather):
        result=host.verify_new("COM7")
        assert result["knx093_version_verified"]==signature
    print("PASS 5/6: signed firmware ID and idle parsing")

    with patch.object(old,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(old,"open_usb",return_value=Fake()), \
         patch.object(old,"command",return_value=None), \
         patch.object(old,"gather",side_effect=lambda ser,secs,lines,end=None:
           (lines.extend(["KNX085 MOTOR gate=1 state=IDLE channel=0 direction=- duration_ms=0 peak_ma=0"]) or True)):
        try:host.verify_new("COM7")
        except old.Refused:pass
        else:raise AssertionError("old firmware accepted as KNX093")
    print("PASS 6/6: no M1 pulse if firmware signature missing")
    print("KNX093 OFFLINE 6/6 PASS")
if __name__=="__main__":check()
