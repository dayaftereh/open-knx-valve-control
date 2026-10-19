#!/usr/bin/env python3
"""KNX086 offline contract tests; no COM open, no Bootloader, no motor."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx085_motor_diag"))
import knx086_live_connected as mod

def port(device,vid,pid,serial=""):
    return SimpleNamespace(device=device,vid=vid,pid=pid,serial_number=serial)
GOOD=[port("COM8",0x2e8a,0x000a,mod.BOARD_SERIAL),
      port("COM5",0x1a86,0x7523)]
def reject(f):
    try:f()
    except RuntimeError:return
    raise AssertionError("unsafe input incorrectly accepted")
def test_live_usb_profile():
    with patch.object(mod.list_ports,"comports",return_value=GOOD):
        assert mod.board_ports()==("COM8","COM5")
    with patch.object(mod.list_ports,"comports",return_value=[GOOD[0]]):
        reject(mod.board_ports)
    with patch.object(mod.list_ports,"comports",return_value=[
            port("COM8",0x2e8a,0x000a,"wrong"),GOOD[1]]):
        reject(mod.board_ports)

def test_firmware_identity():
    f=mod.base.check_image()
    assert f["bytes"]==242688
    assert f["sha256"]==mod.base.IMAGE_SHA256

def test_flash_single_copy():
    with TemporaryDirectory() as td:
        drive=Path(td)
        (drive/"INFO_UF2.TXT").write_text("Board-ID: RPI-RP2",encoding="utf8")
        summary={"port":"COM8","updi":"COM5","uf2":{"sha256":mod.base.IMAGE_SHA256}}
        with patch.object(mod,"preflight_live",return_value=summary), \
             patch.object(mod,"save",return_value=Path(td)/"fake.json"), \
             patch.object(mod.base,"rom_volume",return_value=None), \
             patch.object(mod.base,"touch_rom") as touch, \
             patch.object(mod.base,"wait_rom_disk",return_value=drive), \
             patch.object(mod.shutil,"copyfile") as copied, \
             patch.object(mod.base,"wait_app",return_value="COM8"):
            result=mod.flash_once()
            assert result["new_port"]=="COM8"
            assert result["uf2_copied_once"]
            touch.assert_called_once_with("COM8")
            copied.assert_called_once()
            assert copied.call_args.args[0]==mod.base.IMAGE
        with patch.object(mod,"preflight_live",return_value=summary), \
             patch.object(mod,"save",return_value=Path(td)/"fake.json"), \
             patch.object(mod.base,"rom_volume",return_value=drive), \
             patch.object(mod.base,"touch_rom",side_effect=AssertionError("reset attempted")):
            reject(mod.flash_once)

def test_ina_gate_blocks_motor():
    with patch.object(mod,"passive_085",side_effect=RuntimeError("INA unsafe")), \
         patch.object(mod,"usb_port",side_effect=AssertionError("USB ARM attempted")):
        reject(lambda:mod.test_m1(150))
    reject(lambda:mod.test_m1(251))

def test_tx_and_updi_preflight_contract():
    # Ensures R17-remediated test profile is recognized without pretending
    # KNX and UPDI need unplugging: the exact KNX084 live baseline is required.
    class MockSerial:
        def __init__(self,corrupt=False):
            self.writes=[]
            self.lines=[]
            self.bad=corrupt
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def reset_input_buffer(self):self.lines=[]
        def write(self,b):
            self.writes.append(b)
            if b==b"STATUS\n":
                tx="0" if self.bad else "1"
                edges="2151000" if len(self.writes)<5 else "2151300"
                self.lines.append(f"KNX084 STATUS tx_low={tx} motors_low=1 uart_ready=1 snapshots=500 timeout=0 rejected=0 rx_edges={edges} NO_KNX_TX_NO_MOTOR_ACTUATION")
            if b==b"TEMPS\n":
                self.lines.extend([f"KNX084 CH T{i} valid=1 temp_c=14.50 flags=3 fault=0 fault_name=None age_s=1" for i in range(4)])
            if b==b"RXSTATS\n":
                self.lines.append("KNX084 RXSTATS edges=2151300 rises=1 falls=1 lost=0 buffered=0 last_us=100 current_level=0")
        def flush(self):pass
        def readline(self):
            return (self.lines.pop(0)+"\n").encode("ascii") if self.lines else b""
    # Use a manually advancing fake clock so collection finishes quickly.
    ticks=[0]
    def now():
        ticks[0]+=.2
        return ticks[0]
    for corrupt in (False,True):
        ticks[0]=0
        mock=MockSerial(corrupt)
        with patch.object(mod,"board_ports",return_value=("COM8","COM5")), \
             patch.object(mod.base,"check_image",return_value={"sha256":"known"}), \
             patch.object(mod,"usb_port",return_value=mock), \
             patch.object(mod.time,"monotonic",side_effect=now):
            if corrupt:
                reject(mod.preflight_live)
            else:
                v=mod.preflight_live()
                assert v["all_motor_outputs_low"] and v["knx_tx_low"]
                assert len(v["temperature_c"])==4
                assert v["rx_edges_last"]>=v["rx_edges_first"]

def main():
    tests=(test_live_usb_profile,test_firmware_identity,test_flash_single_copy,
           test_ina_gate_blocks_motor,test_tx_and_updi_preflight_contract)
    for fn in tests:
        fn()
        print("PASS",fn.__name__)
    print(f"KNX086 LIVE PROFILE OFFLINE {len(tests)}/{len(tests)} PASS")
if __name__=="__main__":
    main()
