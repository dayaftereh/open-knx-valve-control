"""KNX076 source-level safety regression for non-autonomous PIO one-shot."""
from pathlib import Path
import re
import unittest

SOURCE = (Path(__file__).resolve().parents[1] /
          "tools" / "knx076_tx_single_pio" / "src" / "main.cpp")

class TestKnx076PioSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf8")

    def test_35us_high_sideset_sequence(self):
        pins = [int(a) for a in re.findall(r"pio_encode_nop\(\)\s*\|\s*pio_encode_delay\((\d+)\)",self.text)]
        self.assertEqual(pins, [15,15,2])
        self.assertEqual(sum(x+1 for x in pins),35)

    def test_only_one_pio_queue_command(self):
        self.assertEqual(self.text.count("pio_sm_put_blocking("),1)
        self.assertIn("alreadyFired = true",self.text)
        self.assertIn("if (!ready || !armed || alreadyFired",self.text)
        self.assertIn("if (!ready || alreadyFired || gpio_get(kTxPin))",self.text)

    def test_gpio_latched_low_at_boot(self):
        self.assertIn("gpio_put(kTxPin, 0)",self.text)
        self.assertIn("gpio_set_dir(kTxPin, GPIO_OUT)",self.text)
        self.assertLess(self.text.index("gpio_put(kTxPin, 0)"),
                        self.text.index("gpio_set_dir(kTxPin, GPIO_OUT)"))
        self.assertNotIn("gpio_put(kTxPin, 1)",self.text)

    def test_pio_autonomous_low_after_pulse(self):
        self.assertIn("pio_encode_pull(false, true)",self.text)
        self.assertIn("pio_encode_nop() | pio_encode_sideset(1, 0)",self.text)
        self.assertIn("sm_config_set_sideset(&cfg, 1, false, false)",self.text)

    def test_two_stage_explicit_arm(self):
        self.assertIn('cmd == "ARM ONE"',self.text)
        self.assertIn('cmd == "FIRE ONE"',self.text)
        self.assertIn("kArmWindowMs = 4000",self.text)
        self.assertIn("disarm();",self.text)

if __name__ == "__main__":
    unittest.main()
