#!/usr/bin/env python3
"""KNX038 offline UPDI preflight/consent tests: no COM4 RTS or UPDI traffic."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import knx038_updi_readiness as W

def device(name="COM4",vid=0x1A86,pid=0x7523):
    return SimpleNamespace(device=name,vid=vid,pid=pid)

def gate(**overrides):
    value=dict(execute=True,port="COM4",
               confirm_cn1_orientation=True,
               confirm_target_vdd=True,
               confirm_updi_level=True,
               confirm_cn1_power=True,
               confirm_no_knx_motors=True)
    value.update(overrides)
    return argparse.Namespace(**value)

class Tests(unittest.TestCase):
    def test_expected_com_matches_known_pnp(self):
        self.assertEqual(W.verify_com([device()]).device,"COM4")

    def test_wrong_port_rejected(self):
        with self.assertRaises(W.GateError):
            W.verify_com([device()],"COM5")

    def test_wrong_chip_id_rejected(self):
        with self.assertRaises(W.GateError):
            W.verify_com([device(vid=0x2E8A,pid=0x000A)])

    def test_duplicate_ch340_rejected(self):
        with self.assertRaises(W.GateError):
            W.verify_com([device(),device("COM8")])

    def test_plan_requires_no_serial_or_pymcuprog(self):
        with patch.object(W,"ports",side_effect=AssertionError("USB I/O not allowed")):
            self.assertEqual(W.EXPECTED_SIGNATURE,"1E9521")

    def test_default_signature_gate_is_off(self):
        with self.assertRaises(W.GateError):
            W.ready(gate(execute=False))

    def test_each_independent_physical_gate_required(self):
        fields=["confirm_cn1_orientation","confirm_target_vdd",
                "confirm_updi_level","confirm_cn1_power",
                "confirm_no_knx_motors"]
        for key in fields:
            with self.subTest(key=key):
                with self.assertRaises(W.GateError):
                    W.ready(gate(**{key:False}))

    def test_zero_com4_access_before_voltage_verification(self):
        with patch.object(W,"ports",
                          side_effect=AssertionError("COM4 must not be touched")):
            with self.assertRaises(W.GateError):
                W.ping(gate(confirm_updi_level=False))

    def test_wrong_port_abort_before_touch(self):
        with patch.object(W,"ports",
                          side_effect=AssertionError("not allowed")):
            with self.assertRaises(W.GateError):
                W.ping(gate(port="COM7"))

    def test_expected_hex_and_manifest_if_here(self):
        if not W.MANIFEST.exists():
            self.skipTest("External build artifact is only on Desktop")
        x=W.verify_build()
        self.assertEqual(x["target"],"ATtiny3216")
        self.assertEqual(len(x["sha256"]),64)

    def test_pymcuprog_reverse_signature_accepted(self):
        self.assertTrue(W.expected_signature_response(
            "Pinging device...\nPing response: 21951E\n"))

    def test_wrong_attiny1616_signature_rejected(self):
        self.assertFalse(W.expected_signature_response(
            "Pinging device...\nPing response: 21941E\n"))

    def test_no_unknown_signature_mistaken_for_success(self):
        self.assertFalse(W.expected_signature_response(
            "Programmer opened, Device detection timed out"))

    def test_no_flash_command_or_erase_in_source(self):
        src=Path(W.__file__).read_text(encoding="utf-8")
        self.assertIn('"ping"',src)
        self.assertNotIn('"write"',src)
        self.assertNotIn('"erase"',src)
        self.assertNotIn('"--erase"',src)
        self.assertIn('"--confirm-updi-level"',src)

if __name__=="__main__":
    unittest.main(verbosity=2)
