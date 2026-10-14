"""KNX042 source and host protocol regression, strictly offline."""
import importlib.util
import json
import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "tools/knx042_motor_led_diag/src/main.cpp").read_text(encoding="utf-8")
CONFIG = (ROOT / "tools/knx042_motor_led_diag/platformio.ini").read_text(encoding="utf-8")


class MotorLedSafetyTests(unittest.TestCase):
    def test_motor_pin_mapping_and_shared_direction(self):
        self.assertIn("kMotorEnable[8] = {10, 11, 12, 13, 14, 15, 16, 17}", SOURCE)
        self.assertIn("constexpr uint8_t kDir1 = 18;", SOURCE)
        self.assertIn("constexpr uint8_t kDir2 = 19;", SOURCE)
        self.assertIn("constexpr uint8_t kStknxTx = 0;", SOURCE)

    def test_bounded_pulse_with_explicit_arm(self):
        self.assertIn("constexpr uint32_t kPulseMs = 400;", SOURCE)
        self.assertIn("constexpr uint32_t kArmMs = 15000;", SOURCE)
        self.assertIn('strcmp(inputLine, "ARM LEDS_ONLY") == 0', SOURCE)
        self.assertIn('memcmp(inputLine, "PULSE ", 6) == 0', SOURCE)
        self.assertIn('strcmp(inputLine, "STOP") == 0', SOURCE)
        self.assertIn("if (!armed || pulseActive ||", SOURCE)
        self.assertIn("now - pulseStartedAt) >=", SOURCE)
        self.assertIn("(holdActive ? kHoldMs : kPulseMs)", SOURCE)
        self.assertIn("constexpr uint32_t kHoldMs = 180000;", SOURCE)
        self.assertIn('strcmp(inputLine, "HOLD M1 F") == 0', SOURCE)
        self.assertIn("digitalWrite(kMotorEnable[0], HIGH);", SOURCE)
        self.assertEqual(SOURCE.count("digitalWrite(kMotorEnable[0], HIGH);"), 1)
        self.assertIn("holdActive = false;", SOURCE)
        self.assertIn('KNX042 HOLD M1 F 180s', SOURCE)
        self.assertIn('armed = false; // single-shot', SOURCE)
        self.assertIn("now - armedAt) >= kArmMs", SOURCE)
        self.assertEqual(SOURCE.count("digitalWrite(kMotorEnable[motorIndex], HIGH)"), 1)
        self.assertIn("void stopMotorOutputs()", SOURCE)
        self.assertIn("for (uint8_t pin : kMotorEnable) digitalWrite(pin, LOW);", SOURCE)

    def test_safe_setup_and_no_automatic_drive(self):
        setup = SOURCE.split("void setup() {", 1)[1].split("void printSnapshot", 1)[0]
        self.assertIn("digitalWrite(kStknxTx, LOW);", setup)
        self.assertIn("pinMode(kStknxTx, OUTPUT);", setup)
        self.assertIn("digitalWrite(pin, LOW);", setup)
        self.assertIn("pinMode(pin, OUTPUT);", setup)
        self.assertNotIn("digitalWrite(kMotorEnable[motorIndex], HIGH)", setup)
        self.assertNotIn("receiveCommand();", setup)

    def test_no_knx_or_motor_product_firmware_and_upload_guard(self):
        self.assertNotIn("TPUart", SOURCE)
        self.assertNotIn("Serial1", SOURCE)
        self.assertNotIn("knx.loop", SOURCE)
        self.assertIn("upload_protocol = custom", CONFIG)
        self.assertIn("upload_command = cmd /c exit 91", CONFIG)
        self.assertIn("KNX042_MOTOR_LED_DIAG=1", CONFIG)

    def test_temperature_uart_preserved(self):
        self.assertIn("Serial2.setTX(kAttinyTx)", SOURCE)
        self.assertIn("Serial2.setRX(kAttinyRx)", SOURCE)
        self.assertIn("Serial2.availableForWrite() <= 0", SOURCE)
        self.assertIn("TemperatureProtocol::decodeSnapshot", SOURCE)
        self.assertIn("KNX040 SNAPSHOT seq=", SOURCE)
        self.assertIn("KNX040 CH T", SOURCE)

    def test_physical_led_gate_required_by_usb_host(self):
        host = (ROOT / "tools/knx042_motor_led_control.py").read_text(encoding="utf-8")
        for text in ("--knx-disconnected", "--motors-unplugged", "--usb-only",
                     "--leds-current-limited", "READY_LINE", "identify_port",
                     "KNX042 AUTO-STOP", "hold_confirmed", "stop_command",
                     "hold is limited to --channel 1 --direction F"):
            self.assertIn(text, host)

    def test_host_port_identity_strict(self):
        spec = importlib.util.spec_from_file_location(
            "knx042_motor_led_control", ROOT / "tools/knx042_motor_led_control.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        good = types.SimpleNamespace(device="COM7", vid=0x2E8A, pid=0x000A,
                                     serial_number="E464401787522D33")
        self.assertIs(module.identify_port([good], "COM7", "E464401787522D33"), good)
        for case in (("COM4", good.serial_number), ("COM7", "different")):
            with self.assertRaises(RuntimeError):
                module.identify_port([good], *case)


if __name__ == "__main__":
    unittest.main()
