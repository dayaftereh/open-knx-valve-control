"""Offline safety contract for read-only KNX043 PicoScope USB 5V vs TX capture."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "knx043_picoscope_dual_usb5v_capture.ps1"


class TestDualUSB5VPicoScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_A_KNX_TX_and_B_usb_5v_are_both_enabled(self):
        s = self.text
        self.assertIn("ps3000aSetChannel($handle,0,1,1,5", s)
        self.assertIn("ps3000aSetChannel($handle,1,1,1,$bSdkRange", s)
        self.assertIn("elseif($BInputRangeVolts -eq 10){$bSdkRange=9}", s)
        self.assertIn("ps3000aSetDataBuffer($handle,0,$pinA.AddrOfPinnedObject()", s)
        self.assertIn("ps3000aSetDataBuffer($handle,1,$pinB.AddrOfPinnedObject()", s)

    def test_B_is_positive_edge_trigger_with_10x_scale(self):
        s = self.text
        self.assertIn("$TriggerTipVolts=2.5", s)
        self.assertIn("$TriggerTipVolts/$bTipFullscale*$maxAdc", s)
        self.assertIn("ps3000aSetSimpleTrigger($handle,1,1,$thresholdAdc,2,0,0)", s)
        self.assertIn("auto-trigger", s)
        self.assertIn("probe_ratio_B=$ProbeRatioB", s)

    def test_arm_requires_human_probes_confirmation(self):
        self.assertIn("[switch]$PhysicalProbesVerified", self.text)
        self.assertIn("if($Mode -eq \"Arm\" -and -not $PhysicalProbesVerified)", self.text)

    def test_raw_ADC_archives_and_bounce_hysteresis(self):
        for key in ("chA_KNX_TX_i16le.bin", "chB_USB_5V_i16le.bin",
                    "Get-FileHash", "high_edges_above_3V", "low_edges_below_2V",
                    "relative_to_trigger_ms"):
            self.assertIn(key, self.text)

    def test_no_board_control_or_firmware_writes(self):
        s = self.text
        self.assertNotIn("ps3000aSetSigGen", s)
        self.assertNotIn("picotool load", s)
        self.assertNotIn("Copy-Item", s)
        self.assertNotIn("SerialPort]::Open", s)
        self.assertIn("no_firmware_or_KNX_bus_or_motor_commands_by_agent=$true", s)

    def test_pico_driver_stops_and_releases_both_pins(self):
        self.assertIn("$pinA.Free()", self.text)
        self.assertIn("$pinB.Free()", self.text)
        self.assertIn("ps3000aStop($handle)", self.text)
        self.assertIn("ps3000aCloseUnit($handle)", self.text)


if __name__ == "__main__":
    unittest.main()
