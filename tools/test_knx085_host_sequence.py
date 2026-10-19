#!/usr/bin/env python3
"""Simulated USB end-to-end KNX085 M1 host pulse and INA CSV test. NO HARDWARE."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx085_motor_diag"))
import knx085_bench_host as host

SERIAL=host.SERIAL
class FakeSerial:
    def __init__(self,end_state="IDLE"):
        self.lines=[]
        self.commands=[]
        self.end_state=end_state
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def reset_input_buffer(self):self.lines.clear()
    def flush(self):pass
    def write(self,b):
        for command in b.decode("ascii").splitlines():
            self.commands.append(command)
            if command=="STATUS":
                self.lines.append("KNX085 STATUS tx_low=1 motors_low=1 uart_ready=1 snapshots=10 timeout=0 rejected=0 rx_edges=100 motor_gate=1 motor_state=IDLE NO_AUTOMATIC_MOTOR_OR_KNX_TX")
            elif command=="INA":
                self.lines.extend([
                    "KNX085 INA addr=0x40 config=0x399f config_ok=1 good_idle_samples=6",
                    "KNX085 INA read_ok=1 bus_mv=3280 current_ma_assuming_R29_200mohm=0 overflow=0 idle_ok=1 SHUNT_AND_SUPPLY_AS_BUILT_NOT_YET_MEASURED"])
            elif command=="TEMPS":
                self.lines += [f"KNX085 CH T{i} valid=1 temp_c=14.50 flags=3 fault=0 fault_name=None age_s=0" for i in range(4)]
            elif command=="ARM MOTORS":
                self.lines.append("KNX085 ARMED_5S")
            elif command.startswith("PULSE M1 "):
                self.lines.extend([f"KNX085 PULSE_STARTED M1 F duration_ms=150",
                    "KNX085 MOTOR_ENDED state="+self.end_state])
            elif command=="TRACE":
                self.lines.extend(["KNX085 TRACE_BEGIN count=2",
                    "KNX085 TRACE t_ms=10 shunt_raw=300 shunt_uv=3000 bus_mv=3290 valid=1",
                    "KNX085 TRACE t_ms=20 shunt_raw=360 shunt_uv=3600 bus_mv=3280 valid=1",
                    "KNX085 TRACE_END"])
            elif command=="STOP":
                self.lines.append("KNX085 STOPPED_ALL_OFF")
            else:raise AssertionError("unexpected USB command "+command)
        return len(b)
    def readline(self):
        if self.lines:return (self.lines.pop(0)+"\n").encode("ascii")
        return b""

def clock():
    n=[0.0]
    def now():
        n[0]+=.15
        return n[0]
    return now

def run_once(end_state:str):
    with TemporaryDirectory() as tmp:
        fake=FakeSerial(end_state=end_state)
        rp=SimpleNamespace(device="COM8",vid=0x2e8a,pid=0x000a,serial_number=SERIAL)
        argv=["knx085_bench_host","pulse","--port","COM8",
              "--expected-serial",SERIAL,"--duration-ms","150",
              "--direction","F","--knx-physically-unplugged",
              "--updi-unplugged","--usb-only-supply",
              "--physical-usb-off-ready","--output",tmp]
        with patch.object(sys,"argv",argv), \
             patch.object(host.list_ports,"comports",return_value=[rp]), \
             patch.object(host.serial,"Serial",return_value=fake), \
             patch.object(host.time,"monotonic",side_effect=clock()):
            if end_state=="IDLE":
                assert host.main()==0
            else:
                try:host.main()
                except RuntimeError as exc:
                    assert "fault" in str(exc).lower()
                else:raise AssertionError("fault response accepted")
        files=list(Path(tmp).glob("*"))
        raws=list(Path(tmp).glob("*_USBRAW.json"))
        assert len(raws)==1
        payload=json.loads(raws[0].read_text(encoding="utf8"))
        assert payload["trace_complete"]
        assert "PULSE M1 F 150" in fake.commands
        assert "STOP" in fake.commands
        if end_state=="IDLE":
            reports=[p for p in files if p.suffix==".json" and "_USBRAW" not in p.name]
            assert len(reports)==1
            data=json.loads(reports[0].read_text(encoding="utf8"))
            assert data["max_nominal_mA"]==18.0
            assert len(data["trace"])==2
            csvs=list(Path(tmp).glob("*.csv"))
            assert len(csvs)==1
            assert csvs[0].read_text(encoding="utf8").count("\n")==3
        print("PASS simulated M1 USB "+end_state+" evidence and STOP")
if __name__=="__main__":
    run_once("IDLE")
    run_once("FAULT")
    print("KNX085 HOST simulated USB pulse and fault regression 2/2 PASS")
