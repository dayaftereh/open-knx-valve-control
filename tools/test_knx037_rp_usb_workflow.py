#!/usr/bin/env python3
"""KNX037 safety contract tests; all executable paths mocked, no USB I/O."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import unittest

import knx037_rp_usb_workflow as W


def port(device: str, vid: int | None, pid: int | None,
         serial_number: str = "") -> SimpleNamespace:
    return SimpleNamespace(device=device, vid=vid, pid=pid,
                           serial_number=serial_number)


class TestRPWorkflow(unittest.TestCase):
    PORTS = [
        port("COM1", None, None),
        port("COM3", None, None),
        port("COM4", 0x1A86, 0x7523),
        port("COM7", 0x2E8A, 0x000A, "FAKE_SERIAL_RP2040"),
    ]

    def test_default_plan_does_not_touch_ports_or_serial(self):
        with mock.patch.object(W, "ports",
                               side_effect=AssertionError("NO PROBE")):
            self.assertEqual(W.main() if False else W.plan()["operation"],
                             "PLAN_ONLY_NO_SERIAL_OPEN")
        self.assertFalse(W.plan()["automatic_upload_allowed"])
        self.assertTrue(W.plan()["no_ch340_or_updi_access"])

    def test_active_rp2040_identified_by_full_usb_identity(self):
        found = W.find_app_port("COM7", "2E8A:000A", "FAKE_SERIAL_RP2040",
                                self.PORTS)
        self.assertEqual(found.device, "COM7")

    def test_ch340_com4_is_not_a_target(self):
        with self.assertRaises(W.SafeUSBError):
            W.find_app_port("COM4", "1A86:7523", "", self.PORTS)

    def test_stale_com5_must_fail(self):
        with self.assertRaises(W.SafeUSBError):
            W.find_app_port("COM5", "2E8A:000A", "FAKE_SERIAL_RP2040",
                            self.PORTS)

    def test_serial_number_mismatch_must_fail(self):
        with self.assertRaises(W.SafeUSBError):
            W.find_app_port("COM7", "2E8A:000A", "0000000000000000",
                            self.PORTS)

    def test_rp2040_vidpid_mismatch_must_fail(self):
        with self.assertRaises(W.SafeUSBError):
            W.find_app_port("COM7", "2E8A:00C0", "FAKE_SERIAL_RP2040",
                            self.PORTS)

    def test_multiple_pico_cdc_devices_fail_closed(self):
        with self.assertRaises(W.SafeUSBError):
            W.find_app_port("COM7", "2E8A:000A", "FAKE_SERIAL_RP2040",
                            self.PORTS + [port("COM8",0x2E8A,0x000A,"OTHER")])

    def test_usb_flash_cannot_run_without_flags(self):
        options = argparse.Namespace(
            execute=False, confirm_no_knx=True, confirm_no_motors=True,
            confirm_safe_power=True, confirm_updi_cable_disconnected=True)
        with mock.patch.object(W, "ports",
                               side_effect=AssertionError("USB opened")):
            with self.assertRaises(W.SafeUSBError):
                W.flash(options)
        for missing in ("confirm_no_knx", "confirm_no_motors",
                        "confirm_safe_power", "confirm_updi_cable_disconnected"):
            opt = argparse.Namespace(
                execute=True, confirm_no_knx=True, confirm_no_motors=True,
                confirm_safe_power=True, confirm_updi_cable_disconnected=True)
            setattr(opt, missing, False)
            with mock.patch.object(W, "ports",
                                   side_effect=AssertionError("USB touched")):
                with self.assertRaises(W.SafeUSBError):
                    W.flash(opt)

    def test_expected_sha_mandatory(self):
        with self.assertRaises(W.SafeUSBError):
            W.verify_image("does-not-exist.uf2", "abc")

    def test_checksum_blocks_forged_image(self):
        p = (Path(r"C:\ASH\Workspace\Builds\OpenKNXValveControl")
             / "KNX036-desktop-usb-diagnostic-20261014"
             / "rp2040-usb-only-diagnostic.uf2")
        if not p.exists():
            self.skipTest("Desktop UF2 not available in this environment")
        import hashlib
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(W.verify_image(str(p), sha), p)
        with self.assertRaises(W.SafeUSBError):
            W.verify_image(str(p), "f" * 64)

    def test_no_updi_or_motor_commands_in_workflow(self):
        code = Path(W.__file__).read_text(encoding="utf-8")
        self.assertNotIn("pymcuprog ", code)
        self.assertNotIn("Serial1.begin(", code)
        self.assertNotIn("motor_enable(", code)
        self.assertIn('s.rts = False', code)
        self.assertIn('PICOTOOL', code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
