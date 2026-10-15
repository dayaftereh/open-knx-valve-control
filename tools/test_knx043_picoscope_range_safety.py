"""KNX043 PicoScope 3205D passive x1/x10 and voltage-range safety checks.

Only inspects local recorder source and measured JSON; no scope or board access.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parent.parent
RECORD = PROJECT / "tools" / "knx043_picoscope_usb_tx_capture.ps1"
EVIDENCE = PROJECT / "docs" / "KNX043_PICOSCOPE_MEASUREMENTS_20261015.json"
GATES = PROJECT / "docs" / "KNX043_HOME_KNX_GATE.json"


class Knx043PicoScopeRangeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = RECORD.read_text(encoding="utf-8")
        cls.ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.gate = json.loads(GATES.read_text(encoding="utf-8"))

    def test_probe_ratio_scales_tip_voltage(self):
        src = self.src
        self.assertIn("[ValidateSet(1,10)][int]$ProbeRatio=1", src)
        self.assertIn("$TipScale=[double]($InputRangeVolts*$ProbeRatio)", src)
        self.assertIn("probe_ratio=$ProbeRatio", src)
        self.assertIn("$value*$TipScale/$maxAdc", src)
        self.assertIn("tip_range_volts_peak=$TipScale", src)

    def test_sdk_range_enumerations(self):
        self.assertIn("if($InputRangeVolts -eq 0.5){$sdkRange=5}", self.src)
        self.assertIn("elseif($InputRangeVolts -eq 5){$sdkRange=8}", self.src)
        self.assertIn("else{throw", self.src)
        self.assertIn("ps3000aSetChannel($handle,0,1,1,$sdkRange", self.src)

    def test_recorder_never_controls_knx_motor_or_board_firmware(self):
        self.assertIn("ps3000aOpenUnit", self.src)
        self.assertIn("ps3000aGetValues", self.src)
        self.assertNotIn("ps3000aSetSigGen", self.src)
        self.assertNotIn("SerialPort", self.src)
        self.assertNotIn("picotool", self.src)
        self.assertNotIn("FLASH", self.src)
        self.assertNotIn("PULSE 1", self.src)

    def test_mismatched_uncalibrated_ranges_cannot_grant_bus(self):
        ten = self.ev["channel_a_10x_steady_usb_measurement"]
        coarse = ten["coarse_range_5V"]
        fine = ten["refined_range_0_5V"]
        self.assertEqual(coarse["samples"], 400000)
        self.assertEqual(fine["samples"], 400000)
        self.assertGreater(coarse["mean_tip_volts"], fine["mean_tip_volts"] * 5)
        self.assertLess(fine["maximum_tip_volts"], 0.5)
        self.assertTrue(ten["instrument_zero_baseline_measured_with_tip_to_GND"])
        self.assertFalse(ten["zero_baseline_independently_verified_by_agent"])
        self.assertFalse(ten["automatically_authorizes_KNX_TP_bus"])
        self.assertFalse(self.ev["physical_knx_tp_bus_test_authorized"])

    def test_all_physical_electrical_gates_still_null(self):
        self.assertTrue(self.gate["observations"])
        self.assertTrue(all(v is None for v in self.gate["observations"].values()))
        self.assertFalse(self.gate["desktop_usb_scope_10x_observation"]["zero_baseline_verified"])
        self.assertTrue(self.gate["desktop_usb_scope_10x_observation"]["user_reported_GND_tip_zero_capture_performed"])
        self.assertFalse(self.gate["desktop_usb_scope_10x_observation"]["knx_power_authorized"])

    def test_calibrated_reference_is_not_confused_with_verified_electrical_gate(self):
        gnd = self.ev["channel_a_10x_GND_reference"]
        rel = self.ev["channel_a_10x_GND_relative_to_earlier_KNX_TX"]
        self.assertEqual(gnd["sample_count"], 400000)
        self.assertFalse(gnd["physical_contact_independently_verified"])
        self.assertEqual(gnd["probe_ratio"], 10)
        self.assertEqual(gnd["scope_input_range_plus_minus_v"], 0.5)
        self.assertLess(rel["TX_minus_GND_mean_tip_millivolts"], rel["approx_adc_code_step_millivolts"])
        self.assertFalse(rel["physical_KNX_connection_authorized"])

    def test_capture_has_explicit_probe_point_metadata(self):
        self.assertIn('ValidateSet("KNX_TX","GND","UNSPECIFIED")', self.src)
        self.assertIn('$ProbePoint', self.src)
        self.assertNotIn('actual_probe_position="KNX_TX according to user', self.src)


    def test_tx_repeat_after_ground_is_near_reference_but_not_bus_clearance(self):
        tx = self.ev["channel_a_10x_TX_return_after_GND"]
        zero = self.ev["channel_a_10x_GND_reference"]
        self.assertEqual(tx["sample_count"], 400000)
        self.assertEqual(zero["sample_count"], 400000)
        self.assertEqual(tx["probe_ratio"], 10)
        self.assertEqual(tx["scope_input_range_plus_minus_v"], 0.5)
        self.assertLess(tx["uncorrected_max_tip_voltage_v"], 0.5)
        self.assertEqual(tx["samples_above_0p5_tip_v"], 0)
        self.assertLess(abs(tx["TX_minus_GND_sequential_mean_mV"]),
                        tx["approx_ADC_code_step_mV"])
        self.assertFalse(tx["controlled_reset_BOOTSEL_brownout_measured"])
        self.assertFalse(tx["KNX_TP_connection_authorized"])
        self.assertFalse(tx["physical_probe_tip_and_ground_independently_verified"])

    def test_scope_ground_return_does_not_pass_an_electrical_gate(self):
        measurement = self.gate["desktop_usb_scope_10x_after_ground_return"]
        self.assertFalse(measurement["bus_connection_authorized"])
        self.assertFalse(measurement["reset_bootsel_brownout_qualification"])
        self.assertTrue(all(v is None for v in self.gate["observations"].values()))


if __name__ == "__main__":
    unittest.main()
