#!/usr/bin/env python3
"""KNX040 independent RP2040 USB/ATtiny temperature UART diagnostics guard.

Static/source tests. --check-build validates local compiled UF2 if available;
does not enumerate or open COM, touch devices, run a PIO upload, or send KNX.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
INI=ROOT/"tools/knx040_uart_diag/platformio.ini"
SRC=ROOT/"tools/knx040_uart_diag/src/main.cpp"
UF2=ROOT/"tools/knx040_uart_diag/.pio/build/knx040_uart/firmware.uf2"

class KNX040Tests(unittest.TestCase):
    require_build=False

    @classmethod
    def setUpClass(cls):
        cls.src=SRC.read_text(encoding="utf-8")
        cls.ini=INI.read_text(encoding="utf-8")

    def test_diagnostic_project_is_separate(self):
        self.assertIn("[env:knx040_uart]",self.ini)
        self.assertIn("default_envs = knx040_uart",self.ini)
        self.assertIn("board = rpipico",self.ini)
        self.assertNotIn("lib_deps",self.ini)
        active = "\n".join(line for line in self.ini.splitlines()
                           if not line.lstrip().startswith(";"))
        for unsafe in ("TPUart","knxprod","src/controller","motor","OpenKNXproducer"):
            self.assertNotIn(unsafe,active)

    def test_no_default_upload(self):
        self.assertRegex(self.ini,r"(?m)^upload_protocol\s*=\s*custom$")
        self.assertRegex(self.ini,r"(?m)^upload_command\s*=\s*cmd /c exit 91$")
        self.assertNotIn("upload_port",self.ini)

    def test_strict_board_and_variant(self):
        self.assertIn("#ifndef ARDUINO_ARCH_RP2040",self.src)
        self.assertIn("#ifndef KNX040_TEMPERATURE_UART_DIAG",self.src)
        self.assertIn("-DKNX040_TEMPERATURE_UART_DIAG=1",self.ini)

    def test_transceiver_safe_low_before_uart_setup(self):
        low=self.src.find("digitalWrite(kStknxTx, LOW);")
        output=self.src.find("pinMode(kStknxTx, OUTPUT);")
        usb=self.src.find("Serial.begin(115200);")
        self.assertTrue(0<=low<output<usb)
        self.assertIn("constexpr uint8_t kStknxTx = 0;",self.src)
        self.assertNotIn("digitalWrite(kStknxTx, HIGH)",self.src)

    def test_temperature_uart1_pins_exact(self):
        self.assertIn("constexpr uint8_t kAttinyTx = 8;",self.src)
        self.assertIn("constexpr uint8_t kAttinyRx = 9;",self.src)
        self.assertIn("Serial2.setTX(kAttinyTx)",self.src)
        self.assertIn("Serial2.setRX(kAttinyRx)",self.src)
        self.assertIn("Serial2.begin(kBaud)",self.src)
        self.assertIn("constexpr uint32_t kBaud = 115200;",self.src)
        self.assertNotIn("Serial1.",self.src)

    def test_no_ordinary_knx_or_motor_initialization(self):
        for forbidden in ("setupKnx(", "knx.start(", "knx.loop(",
                          "TPUart::", "motor", "Motor", "STBY", "PWM",
                          "setOpenClose(", "analogWrite(", "SPI.begin(",
                          "Wire.begin(", "pymcuprog", "rp2040.reboot"):
            # Comments may explain forbidden calls, so test active code.
            active="\n".join(line for line in self.src.splitlines()
                           if not line.lstrip().startswith("//"))
            self.assertNotIn(forbidden,active)
        active="\n".join(line for line in self.src.splitlines()
                         if not line.lstrip().startswith("//"))
        self.assertEqual(active.count("digitalWrite("),1)
        self.assertEqual(active.count("pinMode("),1)

    def test_shared_knx014_protocol_and_crc(self):
        self.assertIn('#include "../../../lib/common/temperature_protocol.hpp"',self.src)
        self.assertIn("TemperatureProtocol::encodeRequest(",self.src)
        self.assertIn("TemperatureProtocol::Parser parser;",self.src)
        self.assertIn("TemperatureProtocol::decodeSnapshot(",self.src)
        self.assertIn("frame.sequence != outstandingSequence",self.src)
        self.assertIn("frame.type != TemperatureProtocol::SnapshotResponse",self.src)

    def test_pico_available_for_write_is_boolean_not_fifo_count(self):
        self.assertIn("Serial2.availableForWrite() <= 0", self.src)
        self.assertNotIn("Serial2.availableForWrite() < count", self.src)

    def test_reports_all_nine_real_fault_channels(self):
        self.assertIn("TemperatureProtocol::Channels",self.src)
        self.assertIn('F("KNX040 CH T")',self.src)
        self.assertIn('F("KNX040 SNAPSHOT seq=")',self.src)
        self.assertIn('F(" no_sensor=")',self.src)
        self.assertIn('F("KNX040 TIMEOUT seq=")',self.src)
        self.assertIn("ch.fault == 1",self.src)
        self.assertIn("ch.ageSeconds == 0xFFFF",self.src)

    def test_builded_uf2_if_requested(self):
        if not self.require_build:
            self.skipTest("Build is optional for Home regression")
        self.assertTrue(UF2.is_file(),"Compile isolated RP2040 diag first")
        data=UF2.read_bytes()
        self.assertEqual(data[:4],bytes.fromhex("5546320A"))
        self.assertGreater(len(data),1024)
        self.assertLess(len(data),1024*1024)
        self.assertEqual(len(data)%512,0)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check-build",action="store_true")
    a=p.parse_args()
    KNX040Tests.require_build=a.check_build
    result=unittest.TextTestRunner(verbosity=2).run(
       unittest.defaultTestLoader.loadTestsFromTestCase(KNX040Tests))
    return 0 if result.wasSuccessful() else 2

if __name__=="__main__":
    raise SystemExit(main())
