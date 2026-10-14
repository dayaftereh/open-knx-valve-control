"""KNX041 regression: Arduino-Pico SerialUART write readiness is boolean."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TemperatureBridgeWriteReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "src/controller/temperature_bridge.cpp").read_text(encoding="utf-8")

    def test_boolean_write_ready_guard(self):
        self.assertRegex(self.source, r"if\s*\(uart_->availableForWrite\(\)\s*<=\s*0\)")
        self.assertNotRegex(self.source, r"availableForWrite\(\)\s*<\s*8")

    def test_guard_precedes_request_state_advance(self):
        ready = self.source.index("if (uart_->availableForWrite() <= 0)")
        prepare = self.source.index("client_.prepareRequest(")
        self.assertLess(ready, prepare)
        self.assertRegex(self.source[ready:prepare], r"return\s*;")

    def test_only_intended_production_source_delta(self):
        import subprocess
        base = subprocess.run(["git", "show", "32d72ce:src/controller/temperature_bridge.cpp"],
                              cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        original = ("    // Request packet is only 8 bytes; do not mark it pending unless the\n"
                    "    // hardware TX FIFO has capacity for the whole frame.\n"
                    "    if (uart_->availableForWrite() < 8)")
        replacement = ("    // Arduino-Pico SerialUART::availableForWrite() returns a boolean\n"
                       "    // readiness indication (0/1), not the free TX FIFO byte count.\n"
                       "    // A count-based threshold of 8 suppresses every request.\n"
                       "    if (uart_->availableForWrite() <= 0)")
        self.assertEqual(base.count(original), 1)
        self.assertEqual(self.source, base.replace(original, replacement))

    def test_request_still_sent_through_uart(self):
        self.assertRegex(self.source, r"if\s*\(count\)\s*uart_->write\(request, count\)")


if __name__ == "__main__":
    unittest.main()
