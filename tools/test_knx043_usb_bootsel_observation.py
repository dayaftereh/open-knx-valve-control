"""Offline checks for KNX043 BOOTSEL PicoScope / USB observations.

Never opens devices or changes electronics. Tests that ROM PID 0003 is not
mistaken for application CDC PID 000A and hardware bus gates stay pending.
"""
import json
from datetime import datetime
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parent.parent
OBSERVATION = PROJECT / "docs" / "KNX043_PICOSCOPE_BOOTSEL_20261015.json"
GATES = PROJECT / "docs" / "KNX043_HOME_KNX_GATE.json"
WATCHER = PROJECT / "tools" / "knx043_usb_bootsel_watch.py"


class KNX043BootselObservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(OBSERVATION.read_text(encoding="utf-8"))
        cls.gates = json.loads(GATES.read_text(encoding="utf-8"))
        cls.watcher = WATCHER.read_text(encoding="utf-8")

    def test_initial_application_and_later_rom_have_distinct_ids(self):
        e = self.report["usb_events"]
        self.assertEqual(e[0]["vidpid"], "2E8A:000A")
        self.assertEqual(e[-1]["vidpid"], "2E8A:0003")
        self.assertEqual(e[-1]["state"], "RP2 Boot ROM interface COM6")
        self.assertFalse(self.report["rom_volume"]["RPI_RP2_detected"])

    def test_trigger_finished_between_usb_detach_and_rom_enumeration(self):
        e = self.report["usb_events"]
        to_dt = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        capture = self.report["scope_transition"]
        self.assertLess(to_dt(e[1]["time_utc"]), to_dt(capture["captured_utc"]))
        self.assertLess(to_dt(capture["captured_utc"]), to_dt(e[2]["time_utc"]))
        self.assertGreater(capture["maximum_tip_v"], 0.25)
        self.assertLess(capture["maximum_tip_v"], 0.5)
        self.assertEqual(capture["samples_above_0p5_v"], 0)

    def test_rom_usb_steady_level_not_stored_as_full_safety_release(self):
        r = self.report["rom_steady_scope"]
        self.assertEqual(r["sample_count"], 400000)
        self.assertLess(r["max_uncorrected_tip_v"], 0.2)
        self.assertEqual(r["samples_above_0p5v"], 0)
        self.assertFalse(self.report["safety"]["rom_boot_tx_fail_low_all_conditions_verified"])

    def test_usb_watcher_categorizes_rom_different_from_application(self):
        s = self.watcher
        self.assertIn("if p.pid == 0x000A", s)
        self.assertIn("elif p.pid == 0x0003", s)
        self.assertIn('"rp2040_rom_boot_ports"', s)
        self.assertIn('"rp2040_cdc_ports"', s)
        self.assertNotIn("write_bytes(", s)
        self.assertNotIn("Copy-Item", s)

    def test_all_electrical_knx_gate_observations_remain_open(self):
        g = self.gates["observations"]
        self.assertEqual(len(g), 17)
        self.assertTrue(all(value is None for value in g.values()))
        self.assertFalse(self.report["safety"]["knx_tp_connection_authorized"])
        self.assertFalse(self.report["safety"]["any_firmware_written"])


if __name__ == "__main__":
    unittest.main()
