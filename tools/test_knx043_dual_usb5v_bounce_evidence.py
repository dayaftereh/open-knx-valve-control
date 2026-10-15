"""Offline evidence checks: KNX_TX vs user-provided USB 5V PicoScope capture.

The original raw data are archived separately with SHA-256. These checks
deliberately do not mark actual KNX electrical safety gates as passed.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "docs" / "KNX043_PICOSCOPE_DUAL_USB5V_RESULT_20261015.json"
GATE = ROOT / "docs" / "KNX043_HOME_KNX_GATE.json"


class DualCHBootselSupplyBounce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = json.loads(RECORD.read_text(encoding="utf-8"))
        cls.gates = json.loads(GATE.read_text(encoding="utf-8"))

    def test_scope_true_physical_ratios_and_simultaneous_samples(self):
        s = self.ev["scope"]
        self.assertEqual(s["A_probe_ratio"], 10)
        self.assertEqual(s["B_probe_ratio"], 1)
        self.assertEqual(s["B_input_range_plus_minus_v"], 10)
        self.assertEqual(s["samples_per_channel"], 500000)
        self.assertEqual(s["sampling_interval_us"], 7.984)

    def test_hardware_B_fell_rose_fell(self):
        p = self.ev["power_rising_falling_observed"]
        events = p["hysteresis_low_under_2V_and_high_over_3V_events"]
        self.assertEqual([i["event"] for i in events], [
            "USB5V_HIGH", "USB5V_LOW", "USB5V_HIGH", "USB5V_LOW"
        ])
        self.assertEqual(events[0]["at_sample"], 0)
        self.assertTrue(p["initial_HIGH_at_sample_0_is_not_a_power_on_edge"])
        self.assertEqual(events[1]["relative_to_trigger_ms"], -8.383)
        self.assertEqual(events[2]["relative_to_trigger_ms"], 0)
        self.assertEqual(events[3]["relative_to_trigger_ms"], 11.233)

    def test_knx_tx_spikes_are_unpowered_state_not_connected_high(self):
        t = self.ev["KNX_TX_vs_power"]
        categories = t["category_statistics"]
        self.assertEqual(t["A_count_above_0p5V"], 5596)
        self.assertEqual(categories["B_below_0p2V"]["TX_samples_over_0p5V"], 5536)
        self.assertEqual(categories["B_above_3V"]["TX_samples_over_0p5V"], 0)
        self.assertGreater(t["A_peak_max_v"], 0.5)
        self.assertLess(t["A_peak_sample_and_supply"]["B_supply_v_at_same_sample"], 0.2)

    def test_rom_usb_appeared_after_analog_capture(self):
        e = self.ev["USB_log"]
        self.assertEqual(e["ROM_USB_vidpid"], "2E8A:0003")
        self.assertEqual(e["ROM_boot_COM_port"], "COM6")
        self.assertEqual(len(e["observations_utc"]), 3)
        self.assertEqual(e["observations_utc"][1]["rp2040_rom_boot_ports"], [])
        self.assertTrue(e["observations_utc"][2]["rp2040_rom_boot_ports"])

    def test_post_replug_quiet_scope_and_no_bus_release(self):
        s = self.ev["steady_after_replug"]
        self.assertEqual(s["samples_per_channel"], 500000)
        self.assertLess(s["A_tx_peak_v"], 0.2)
        self.assertEqual(s["A_tx_samples_over0p5"], 0)
        self.assertGreater(s["B_voltage_mean_uncorrected_v"], 4.0)
        self.assertFalse(self.ev["physical_safety"]["KNX_TP_bus_connection_authorized"])
        self.assertFalse(self.gates["desktop_usb_scope_dual_USB5V_20261015"]["KNX_TP_bus_connection_authorized"])

    def test_combined_electrical_gates_unverified(self):
        g = self.gates["observations"]
        self.assertEqual(len(g), 17)
        self.assertTrue(all(v is None for v in g.values()))


if __name__ == "__main__":
    unittest.main()
