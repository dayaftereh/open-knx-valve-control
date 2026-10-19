#!/usr/bin/env python3
"""KNX085 one-shot offline safety tests. No serial, flash or motor actions."""
from __future__ import annotations
import argparse
from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch,Mock

sys.path.insert(0,str(Path(__file__).resolve().parent/"knx085_motor_diag"))
import knx085_one_shot as target

def expect_refusal(call):
    try:call()
    except target.Refused:return
    raise AssertionError("Fail-closed test accepted unsafe state")

def args(**kw):
    values={"knx_physically_disconnected":False,
            "updi_physically_disconnected":False,
            "usb_only_power":False,
            "physical_power_cut_available":False,
            "duration_ms":150,"direction":"F"}
    values.update(kw)
    return argparse.Namespace(**values)

VALID=args(knx_physically_disconnected=True,
           updi_physically_disconnected=True,
           usb_only_power=True,
           physical_power_cut_available=True)

def port(device,vid,pid,serial):
    return SimpleNamespace(device=device,vid=vid,pid=pid,serial_number=serial)

class FakeSerial:
    def __init__(self,rows):
        self.rows=list(rows)
        self.writes=[]
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def reset_input_buffer(self):pass
    def write(self,data):self.writes.append(data);return len(data)
    def readline(self):
        return ((self.rows.pop(0)+"\n").encode("ascii") if self.rows else b"")

def clock():
    tick=[0]
    def step():
        tick[0]+=.16
        return tick[0]
    return step

def baseline_lines(final_edges=24):
    base="KNX084 STATUS tx_low=1 motors_low=1 uart_ready=1 snapshots=10 timeout=0 rejected=0 rx_edges=24 NO_KNX_TX_NO_MOTOR_ACTUATION"
    def rx(edges):
        return f"KNX084 RXSTATS edges={edges} rises=12 falls=12 lost=0 buffered=0 last_us=123 current_level=0"
    sensors=[f"KNX084 CH T{n} valid=1 temp_c=14.25 flags=3 fault=0 fault_name=None age_s=1"
             for n in range(4)]
    return [base,rx(24),*sensors,base,rx(final_edges),*sensors]

def test_plan_no_usb():
    with patch.object(target,"serial_rows",side_effect=AssertionError("USB accessed")), \
         patch.object(target.serial,"Serial",side_effect=AssertionError("COM opened")), \
         patch.object(target,"touch_rom",side_effect=AssertionError("BOOT toggled")):
        assert target.main(["plan"])==0

def test_operator_preconditions():
    expect_refusal(lambda:target.check_operator(args()))
    expect_refusal(lambda:target.check_operator(args(knx_physically_disconnected=True)))
    expect_refusal(lambda:target.check_operator(args(
       knx_physically_disconnected=True,updi_physically_disconnected=True,
       usb_only_power=True,physical_power_cut_available=True,duration_ms=999)))
    target.check_operator(VALID)

def test_exact_uf2():
    img=target.check_image()
    assert img["bytes"]==242688 and img["sha256"]==target.IMAGE_SHA256
    with TemporaryDirectory() as td:
        other=Path(td)/"unknown.uf2"
        other.write_bytes(b"x"*1024)
        with patch.object(target,"IMAGE",other):
            expect_refusal(target.check_image)

def test_port_selection():
    good=port("COM8",0x2e8a,0x000a,target.SERIAL)
    with patch.object(target,"serial_rows",return_value=[good,
         port("COM5",0x1a86,0x7523,"")]):
        expect_refusal(target.check_usb_ports)
    with patch.object(target,"serial_rows",return_value=[port("COM8",0x2e8a,0x000a,"NOT-BOARD")]):
        expect_refusal(target.check_usb_ports)
    with patch.object(target,"serial_rows",return_value=[good]):
        assert target.check_usb_ports()=="COM8"

def test_knx_idle():
    fake=FakeSerial(baseline_lines())
    with patch.object(target.serial,"Serial",return_value=fake), \
         patch.object(target.time,"monotonic",side_effect=clock()):
        v=target.capture_idle("COM8")
    assert v["rx_edges_last"]==24 and v["motors_low"] and len(v["temperatures_c"])==4
    fake=FakeSerial(baseline_lines(48))
    with patch.object(target.serial,"Serial",return_value=fake), \
         patch.object(target.time,"monotonic",side_effect=clock()):
        expect_refusal(lambda:target.capture_idle("COM8"))

def test_copy_exactly_once():
    with patch.object(target,"rom_volume",return_value=None), \
         patch.object(target,"touch_rom") as boot, \
         patch.object(target,"wait_rom_disk",return_value=Path("D:\\")), \
         patch.object(target.shutil,"copyfile") as copy, \
         patch.object(target,"wait_app",return_value="COM9"):
        assert target.flash_exact_uf2("COM8")=="COM9"
        boot.assert_called_once_with("COM8")
        copy.assert_called_once()
    with patch.object(target,"rom_volume",return_value=Path("D:\\")), \
         patch.object(target,"touch_rom",side_effect=AssertionError("BOOT touched")):
        expect_refusal(lambda:target.flash_exact_uf2("COM8"))

def test_complete_simulated_one_shot():
    with TemporaryDirectory() as td:
        dir=Path(td)
        with patch.object(target,"BUNDLE",dir), \
             patch.object(target,"check_image",return_value={"sha256":"mock"}), \
             patch.object(target,"check_usb_ports",return_value="COM8"), \
             patch.object(target,"capture_idle",return_value={"motors_low":True,"tx_low":True}), \
             patch.object(target,"flash_exact_uf2",return_value="COM9") as flashed, \
             patch.object(target,"evaluate_knx085") as evaluated, \
             patch.object(target.subprocess,"run",return_value=subprocess.CompletedProcess([],0,
                                             stdout="EVIDENCE MOCK",stderr="")) as host:
            v=target.execute(VALID)
            assert v["pulse_and_off_verified"] is True
            assert v["physical_movement_observed"] is None
            assert (dir/"M1_ONESHOT_RUN_STARTED.flag").is_file()
            reports=list((dir/"logs").glob("KNX085_M1_ONESHOT_*.json"))
            assert len(reports)==1
            record=json.loads(reports[0].read_text(encoding="utf-8"))
            assert record["pulse_and_off_verified"]
            flashed.assert_called_once_with("COM8")
            evaluated.assert_called_once()
            assert "--duration-ms" in host.call_args.args[0]
            expect_refusal(lambda:target.execute(VALID))
            assert host.call_count==1

def test_fail_fast_before_usb():
    with patch.object(target,"check_usb_ports",side_effect=AssertionError("USB accessed")), \
         patch.object(target,"touch_rom",side_effect=AssertionError("ROM reset")):
        assert target.main(["execute"])==5

def main():
    tasks=(test_plan_no_usb,test_operator_preconditions,test_exact_uf2,
           test_port_selection,test_knx_idle,test_copy_exactly_once,
           test_complete_simulated_one_shot,test_fail_fast_before_usb)
    for task in tasks:
        task()
        print("PASS",task.__name__)
    print(f"KNX085 ONE_SHOT OFFLINE {len(tasks)}/{len(tasks)} PASS")
if __name__=="__main__":
    main()
