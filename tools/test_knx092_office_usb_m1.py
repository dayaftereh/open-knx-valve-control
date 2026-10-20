#!/usr/bin/env python3
"""KNX092 offline USB-only M1 tool contract; NO hardware or serial access."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, call
import subprocess
import hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import knx092_office_usb_m1 as mod

def refuse(fn):
    try:fn()
    except mod.Refused:return
    raise AssertionError("Fail-closed gate accepted unsafe input")
def port(name,vid,pid,serial):
    return SimpleNamespace(device=name,vid=vid,pid=pid,serial_number=serial)
def main():
    d=mod.image_check()
    assert d["sha256"]==mod.SHA256 and d["bytes"]==242688
    print("PASS pinned image checksum")
    good=port("COM7",0x2e8a,0x000a,mod.BOARD_SERIAL)
    others=[port("COM8",0x1a86,0x7523,""),port("COM9",0x1a86,0x7523,"")]
    with patch.object(mod.list_ports,"comports",return_value=[good]+others):
        assert mod.board()=="COM7"
    with patch.object(mod.list_ports,"comports",return_value=[port("COM7",0x2e8a,0x000a,"OTHER")]+others):
        refuse(mod.board)
    with patch.object(mod.list_ports,"comports",return_value=[port("COM8",0x2e8a,0x000a,mod.BOARD_SERIAL)]+others):
        refuse(mod.board)
    print("PASS COM7 serial and unrelated CH340 isolation")
    p=Path("tools/knx085_motor_diag/src/main.cpp")
    g=Path("tools/knx085_motor_diag/src/motor_gate.hpp")
    src=p.read_text(encoding="utf8")
    gates=g.read_text(encoding="utf8")
    for s in ("kMotorEnables[8]={10,11,12,13,14,15,16,17}",
              "kMotorDirection[2]={18,19}",
              "gpio_put(kKnxTx,0)",
              "KNX085_HARDWARE_GATE_APPROVED == 1",
              "TRACE_BEGIN","PULSE_STARTED"):
        assert s in src,s
    assert "gpio_put(kKnxTx,1)" not in src
    for s in ("kMinPulseMs=50","kMaxPulseMs=250",
              "kIdleCurrentLimitMa=25","kRunningCurrentLimitMa=120"):
        assert s in gates
    print("PASS firmware motor pulse watchdog and INA current guards")
    with patch.object(mod,"board",return_value="COM7"), \
         patch.object(mod,"read_baseline",return_value={"motor_gate":1}), \
         patch.object(mod,"open_usb",side_effect=AssertionError("Unexpected motor USB open")):
        refuse(lambda:mod.pulse(500))
    print("PASS no pulse outside exact 150ms")
    with patch.object(mod.list_ports,"comports",return_value=[
        port("COM6",0x2e8a,0x0003,"BOOT-ROM")]), \
        patch.object(mod.subprocess,"run",side_effect=[
            subprocess.CompletedProcess([],0,stdout=
                "Device Information\\n type: RP2040\\n flash id: 0x"+
                mod.BOARD_SERIAL),
            subprocess.CompletedProcess([],0,stdout=
                "Loading 100%\\nVerifying 100%\\n  OK\\n"+
                "The device was rebooted to start the application.")]) as proc:
        result=mod.load_via_picotool()
        assert result["flash_id"]==mod.BOARD_SERIAL
        assert result["uf2_programmed_once"] and proc.call_count==2
    with patch.object(mod.list_ports,"comports",return_value=[
        port("COM6",0x2e8a,0x0003,"BOOT-ROM")]), \
        patch.object(mod.subprocess,"run",side_effect=[
            subprocess.CompletedProcess([],0,stdout=
                "Device Information\\n type: RP2040\\n flash id: 0x0000000011111111")]) as proc:
        refuse(mod.load_via_picotool)
        assert proc.call_count==1
    print("PASS picotool ROM USB flash-id identity and no wrong-board write")
    print("KNX092 OFFLINE 5/5 PASS")
if __name__=="__main__":main()
