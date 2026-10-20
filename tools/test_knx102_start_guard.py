#!/usr/bin/env python3
"""KNX102 fail-closed offline start-guard diagnostics. No COM, USB or flash."""
from __future__ import annotations
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FW100=ROOT/"tools/knx100_position_usb/src/main.cpp"
FW101=ROOT/"tools/knx101_position_diag/src/main.cpp"
HOST101=ROOT/"tools/knx101_position_diag/knx101_host.py"
IMAGE101=ROOT/"tools/knx101_position_diag/.pio/build/knx101_m1_position_diag_5step/firmware.uf2"
EVIDENCE=Path(r"C:\ASH\Workspace\Runtime\KNX100\KNX100_STEP_03_F.json")

class KNX102(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=FW100.read_text("utf8")
        cls.new=FW101.read_text("utf8")
        cls.host=HOST101.read_text("utf8")

    def test_01_prior_start_error_combined(self):
        self.assertIn("FAILED_OUTPUT_OR_START_ACK",self.old)
        self.assertIn("ack.type!=Knx099::ActionType::None || !gpioActive",self.old)

    def test_02_differential_start_diagnostics(self):
        for term in ("gpio_get_out_level(kMotorEnables[0])",
                     "gpioPadInitial=gpio_get(kMotorEnables[0])",
                     "gpioPadSettled=gpio_get(kMotorEnables[0])",
                     "delayMicroseconds(1300)",
                     "pin_latch=","pin_input_initial=","pin_input_settled=",
                     "model_action=","model_phase="):
            self.assertIn(term,self.new)

    def test_03_guards_not_bypassed(self):
        for term in ("ack.type!=Knx099::ActionType::None || !gpioOut || !gpioPadSettled",
                     "motor.trip();","forceAllInactive();",
                     "position.cancel(millis());"):
            self.assertIn(term,self.new)
        self.assertNotIn("gpio_put(kKnxTx,1)",self.new)
        self.assertNotIn('if(strncmp(cmd,"PULSE "',self.new)

    def test_04_pin_not_ready_cannot_flash(self):
        self.assertIn('PIN_SHA="__KNX101_SHA__"',self.host)
        self.assertIn("PIN_BYTES=0",self.host)
        self.assertIn("sha==PIN_SHA and len(data)==PIN_BYTES",self.host)

    @unittest.skipUnless(IMAGE101.exists(),"KNX101 UF2 not built")
    def test_05_separate_diagnostic_image(self):
        data=IMAGE101.read_bytes()
        self.assertEqual(len(data),250880)
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76")
        self.assertEqual(data[:4],bytes.fromhex("5546320a"))

    @unittest.skipUnless(EVIDENCE.exists(),"Original COM7 event report unavailable")
    def test_06_real_start_fault_and_stop(self):
        event=json.loads(EVIDENCE.read_text("utf8"))
        self.assertFalse(event["complete"])
        self.assertFalse(event["started"])
        self.assertIn("FAILED_OUTPUT_OR_START_ACK",event["error"])
        self.assertIn("KNX100 ARMED_5S",event["rx_excerpt"])
        self.assertIn("KNX100 STOPPED_ALL_OFF",event["rx_excerpt"])
        self.assertEqual(event["preflight"]["position"],500)
        self.assertEqual(event["preflight"]["driver"],"IDLE")
        self.assertEqual(event["preflight"]["idle_ma"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
