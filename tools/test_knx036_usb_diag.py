#!/usr/bin/env python3
"""KNX036 desktop first-contact static contract and optional local UF2 check.

No COM, OS PnP, USB, programmer, network, KNX or MCU access.
Checks that isolated diag build cannot accidentally link the production TPUart
controller and that its PlatformIO upload target is deliberately disabled.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/knx036_usb_diag/src/main.cpp"
INI = ROOT / "tools/knx036_usb_diag/platformio.ini"
UF2 = ROOT / "tools/knx036_usb_diag/.pio/build/knx036_usb/firmware.uf2"
MARKER = "KNX036 USB-ONLY RP2040 ALIVE"


def active_source() -> str:
    return "\n".join(
        line for line in SOURCE.read_text(encoding="utf-8-sig").splitlines()
        if not line.lstrip().startswith("//")
    )


class IsolatedUsbDiagnostics(unittest.TestCase):
    def test_is_separate_application(self):
        pio = INI.read_text(encoding="utf-8-sig")
        self.assertIn("[platformio]", pio)
        self.assertIn("[env:knx036_usb]", pio)
        self.assertIn("board = rpipico", pio)
        self.assertIn("framework = arduino", pio)
        self.assertIn("default_envs = knx036_usb", pio)
        self.assertIn("KNX036_USB_DIAGNOSTIC=1", pio)
        for forbidden in ("open-knx-producer.py", "src/controller",
                          "include/knxprod.hpp", "lib_deps"):
            self.assertNotIn(forbidden, pio)

    def test_upload_always_blocked(self):
        pio = INI.read_text(encoding="utf-8-sig")
        self.assertRegex(pio, r"(?m)^upload_protocol\s*=\s*custom\s*$")
        self.assertRegex(pio, r"(?m)^upload_command\s*=\s*cmd /c exit 91\s*$")
        self.assertNotIn("picotool load", pio)
        self.assertNotIn("1200", pio)

    def test_knx_tx_forced_low_before_usb_setup(self):
        src = active_source()
        low = src.find("digitalWrite(kKnxTxGpio, LOW);")
        drive = src.find("pinMode(kKnxTxGpio, OUTPUT);")
        start = src.find("Serial.begin(115200);")
        self.assertTrue(0 <= low < drive < start)
        self.assertIn("constexpr uint8_t kKnxTxGpio = 0;", src)
        self.assertNotIn("digitalWrite(kKnxTxGpio, HIGH)", src)

    def test_usb_only_marker(self):
        src = active_source()
        self.assertIn(MARKER, src)
        self.assertRegex(src, r"if\s*\(Serial\)")
        self.assertIn("Serial.print", src)
        self.assertIn("Serial.println", src)

    def test_no_motor_or_attiny_uart_or_knx_stack(self):
        src = active_source()
        for forbidden in (
            "Serial1", "Serial2", "TPUart", "setupKnx(", "knx.start(",
            "knx.loop(", "Wire.begin(", "SPI.begin(", "pymcuprog",
            "picotool", "flash_range_erase", "reset_usb_boot",
            "upload", "setTX(", "setRX("
        ):
            self.assertNotIn(forbidden, src)
        # The only GPIO write is to the STKNX TX pin and is always LOW.
        self.assertEqual(src.count("digitalWrite("), 1)
        self.assertEqual(src.count("pinMode("), 1)
        self.assertEqual(len(re.findall(r"\b(?:analogWrite|digitalWrite)\(", src)), 1)
        self.assertIn("no gpio8/9", SOURCE.read_text(encoding="utf-8").lower())

    def test_strict_target_guards(self):
        src = active_source()
        self.assertIn("#ifndef ARDUINO_ARCH_RP2040", src)
        self.assertIn("#ifndef KNX036_USB_DIAGNOSTIC", src)
        self.assertIn("#error", src)

    def test_unpowered_testing_limit_documented(self):
        guide = (ROOT / "docs/KNX036_DESKTOP_USB_FIRST_CONTACT.md").read_text(
            encoding="utf-8-sig")
        for required in (
            "ohne KNX-Bus", "F1", "D1", "R17",
            "4,75 V", "COM1", "COM3", "CN1", "UPDI", "JMP1",
            "BOOTSEL", "STKNX", "kein", "strombegrenzte",
        ):
            self.assertIn(required.lower(), guide.lower())

    def test_optional_built_uf2(self):
        if not getattr(self, "require_build", False):
            self.skipTest("UF2 validation is opt-in")
        self.assertTrue(UF2.is_file())
        data = UF2.read_bytes()
        self.assertGreater(len(data), 1024)
        self.assertLess(len(data), 1024 * 1024)
        # UF2 512-byte blocks, little-endian fixed magic.
        self.assertEqual(len(data) % 512, 0)
        self.assertEqual(data[:4], bytes.fromhex("5546320A"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check-build", action="store_true")
    args = p.parse_args()
    IsolatedUsbDiagnostics.require_build = args.check_build
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IsolatedUsbDiagnostics)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 2


if __name__ == "__main__":
    raise SystemExit(main())
