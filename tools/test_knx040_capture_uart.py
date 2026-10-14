#!/usr/bin/env python3
"""KNX040 offline contract + hardware-trace integrity tests; never open COM."""
from __future__ import annotations
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import knx040_capture_uart as U

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"docs/KNX040_LIVE_TEMPERATURE_UART_EVIDENCE.json"

class Tests(unittest.TestCase):
    def device(self,p="COM7",vid=U.VID,pid=U.PID,serial="TEST_RP2040"):
        return SimpleNamespace(device=p,vid=vid,pid=pid,serial_number=serial)

    def test_strict_usb_identity(self):
        self.assertEqual(U.assert_port([self.device()],"COM7","TEST_RP2040").device,"COM7")

    def test_ch340_is_never_rp2040_cdc(self):
        with self.assertRaises(U.ReadOnlyProbeError):
            U.assert_port([self.device("COM4",0x1A86,0x7523)],"COM4","TEST_RP2040")

    def test_stale_port_refused(self):
        with self.assertRaises(U.ReadOnlyProbeError):
            U.assert_port([self.device()],"COM5","TEST_RP2040")

    def test_wrong_serial_refused(self):
        with self.assertRaises(U.ReadOnlyProbeError):
            U.assert_port([self.device()],"COM7","WRONG")

    def test_multiple_candidate_usb_devices_refused(self):
        with self.assertRaises(U.ReadOnlyProbeError):
            U.assert_port([self.device(),self.device("COM8")],"COM7","TEST_RP2040")

    def test_nosensor_channel_parse_never_fabricates_zero_celsius(self):
        sample=("KNX040 USB-CONTROL UART1-only uart_configured=1 accepted=2 timeout=0\n"+
            "KNX040 SNAPSHOT seq=2 up_ms=45000 valid=0 no_sensor=9 faults=9 accepted=2 timeout=0 rejected=0\n"+
            "".join(f"KNX040 CH T{i} flags=16 fault=1 age_s=65535 centiC=0\n" for i in range(9)))
        e=U.parse_capture(sample.encode("ascii"))
        self.assertEqual(e["snapshot_count"],1)
        self.assertTrue(e["all_observed_nine_channels_NoSensor"])
        self.assertEqual(len(e["last_observed_channels"]),9)
        self.assertTrue(all(x["temperature_C"] is None for x in e["last_observed_channels"]))

    def test_valid_negative_temperature_parse(self):
        source="KNX040 CH T1 flags=3 fault=0 age_s=3 centiC=-1050\n"
        result=U.parse_capture(source.encode("ascii"))
        self.assertEqual(result["last_observed_channels"][0]["temperature_C"],-10.5)

    def test_timeout_not_claimed_to_be_nosensor(self):
        e=U.parse_capture(b"KNX040 TIMEOUT seq=1 count=1\n")
        self.assertTrue(e["any_timeouts"])
        self.assertFalse(e["all_observed_nine_channels_NoSensor"])

    def test_documented_live_results_consistent(self):
        e=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(e["firmware"]["at_tiny"]["postflash_mismatch_defined_bytes"],0)
        self.assertTrue(e["firmware"]["at_tiny"]["fuses_unchanged"])
        self.assertTrue(e["firmware"]["at_tiny"]["eeprom_unchanged"])
        self.assertEqual(e["live_test"]["valid_crc_decoded_snapshots"],8)
        self.assertEqual(e["live_test"]["all_snapshots_nosensor_channels"],9)
        self.assertEqual(e["live_test"]["rejected_responses"],0)
        self.assertEqual(e["live_test"]["timed_out_requests"],0)
        self.assertFalse(e["production_controller_fix_pending"]["already_applied_to_production_source"])

    def test_actual_desktop_trace_if_local(self):
        e=json.loads(EVIDENCE.read_text(encoding="utf-8"))
        raw=Path(e["live_test"]["raw_trace_path"])
        if not raw.exists():
            self.skipTest("Desktop-only physical USB trace is not copied into Git/Home")
        parsed=U.parse_capture(raw.read_bytes())
        self.assertEqual(parsed["snapshot_count"],e["live_test"]["valid_crc_decoded_snapshots"])
        self.assertTrue(parsed["all_observed_nine_channels_NoSensor"])
        self.assertFalse(parsed["any_timeouts"])
        self.assertEqual(parsed["number_of_channel_lines"],72)

    def test_capture_source_never_has_nvm_write_or_knx(self):
        src=Path(U.__file__).read_text(encoding="utf-8")
        active="\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotIn("pymcuprog",active)
        self.assertNotIn("Serial1",active)
        self.assertNotIn("picotool.exe",active)
        self.assertNotIn("knx.write",active)
        self.assertNotIn("s.write(",active)

if __name__=="__main__":
    unittest.main(verbosity=2)
