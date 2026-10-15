"""KNX043 offline RUN-reset evidence contract.

No USB, PicoScope, KNX, firmware, or motor operations. This deliberately rejects
claims of KNX bus clearance from a non-triggered PicoScope observation.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent


class Knx043ResetEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.observed = json.loads((ROOT / "docs/KNX043_PICOSCOPE_RUN_RESET_20261015.json").read_text(encoding="utf-8"))
        cls.gates = json.loads((ROOT / "docs/KNX043_HOME_KNX_GATE.json").read_text(encoding="utf-8"))
        cls.waveforms = json.loads((ROOT / "docs/KNX043_PICOSCOPE_MEASUREMENTS_20261015.json").read_text(encoding="utf-8"))
        cls.script = (ROOT / "tools/knx043_picoscope_reset_trigger.ps1").read_text(encoding="utf-8")

    def test_scope_was_hardware_armed_without_autotrigger(self):
        s = self.observed["scope"]
        self.assertEqual(s["hardware_trigger"], "positive edge over 0.35 V at probe tip")
        self.assertEqual(s["state"], "STOP_REQUESTED_NO_TRIGGER")
        self.assertTrue(s["no_auto_trigger"])
        self.assertFalse(s["raw_waveform_for_run_transition_saved"])
        self.assertEqual(s["recording_sample_interval_ns_if_triggered"], 1984)

    def test_usb_port_events_were_inside_trigger_window(self):
        s = self.observed["scope"]
        events = self.observed["reset_usb_evidence"]["port_events_UTC"]
        self.assertEqual([e["com_port_visible"] for e in events], [True, False, True])
        t = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        self.assertLess(t(s["armed_at_utc"]), t(events[1]["utc"]))
        self.assertLess(t(events[1]["utc"]), t(events[2]["utc"]))
        self.assertLess(t(events[2]["utc"]), t(s["stopped_at_utc"]))

    def test_nontrigger_not_mislabeled_as_captured_waveform(self):
        ev = self.observed["safety_conclusion"]
        self.assertTrue(ev["USB_port_reenumeration_during_scope_arm"])
        self.assertTrue(ev["no_scope_rising_trigger_above_0p35V_during_arm"])
        self.assertFalse(ev["absolute_voltage_waveform_during_reset_captured"])
        self.assertFalse(ev["KNX_bus_connection_authorized"])
        self.assertFalse(ev["rom_bootsel_low_verified"])
        self.assertFalse(ev["brownout_low_verified"])

    def test_postreset_usb_passive_samples(self):
        r = self.observed["after_run_steady_CH_A"]
        self.assertEqual(r["sample_count"], 400000)
        self.assertEqual(r["number_samples_over_0p5_volts"], 0)
        self.assertLess(r["maximum_tip_volts"], 0.15)
        self.assertFalse(self.observed["safety_conclusion"]["KNX_bus_power_tested"])
        self.assertEqual(self.observed["after_run_firmware"]["actual_response"],
                         "KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0")

    def test_17_combined_electrical_gates_still_unverified(self):
        values = self.gates["observations"]
        self.assertEqual(len(values), 17)
        self.assertTrue(all(value is None for value in values.values()))
        v = self.gates["desktop_usb_scope_RUN_reset_observation"]
        self.assertTrue(v["no_raw_reset_waveform_saved"])
        self.assertFalse(v["connection_to_KNX_TP_bus_authorized"])
        self.assertFalse(self.waveforms["physical_knx_tp_bus_test_authorized"])

    def test_picoscope_script_is_passive_and_has_bounded_wait(self):
        s = self.script
        self.assertIn("ps3000aSetSimpleTrigger", s)
        self.assertIn("[ValidateRange(10,3600)][int]$MaxWaitSeconds=1800", s)
        self.assertIn('Mode -eq "Arm"', s)
        self.assertIn('reset_initiated_by_agent=$false', s)
        self.assertNotIn("ps3000aSetSigGen", s)
        self.assertNotIn("ps3000aSetSigGenBuiltIn", s)
        self.assertNotIn("picotool load", s)
        self.assertNotIn("Copy-Item", s)


if __name__ == "__main__":
    unittest.main()
