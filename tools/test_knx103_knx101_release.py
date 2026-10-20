#!/usr/bin/env python3
"""KNX103 pre-release tests for KNX101. STRICTLY OFFLINE: no serial calls."""
from __future__ import annotations
import sys,unittest,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"tools"/"knx101_position_diag"
sys.path.insert(0,str(D))
import knx101_host as h

class KNX103Release(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fw=(D/"src"/"main.cpp").read_text(encoding="utf8")
        cls.host=(D/"knx101_host.py").read_text(encoding="utf8")

    def test_01_binary_identity_pinned(self):
        image=h.fingerprint()
        self.assertEqual(image["size"],250880)
        self.assertEqual(image["sha256"],
                         "9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76")
        self.assertEqual(h.BOARD_SERIAL,"E464401787522D33")

    def test_02_wrong_hash_or_size_refused(self):
        with patch.object(h,"PIN_SHA","0"*64):
            with self.assertRaises(h.Refused):h.fingerprint()
        with patch.object(h,"PIN_BYTES",250881):
            with self.assertRaises(h.Refused):h.fingerprint()

    def test_03_bad_magic_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/"changed.uf2"
            data=bytearray(h.IMAGE.read_bytes())
            data[0]^=0x01
            dest.write_bytes(data)
            with patch.object(h,"IMAGE",dest),patch.object(h,"PIN_SHA",hashlib.sha256(data).hexdigest()):
                with self.assertRaises(h.Refused):h.fingerprint()

    def test_04_exact_five_operations(self):
        expected=[("SEEK R","R",1000,"ENDSTOP_CANDIDATE"),
                  ("SET 500","F",500,"TIMED_TARGET"),
                  ("SET 250","F",250,"TIMED_TARGET"),
                  ("SET 750","R",750,"TIMED_TARGET"),
                  ("SEEK F","F",0,"ENDSTOP_CANDIDATE")]
        self.assertEqual([(r["command"],r["direction"],r["target"],r["stop"])
                          for r in h.STEPS],expected)
        self.assertEqual([r["step"] for r in h.STEPS],list(range(1,6)))

    def test_05_gpio_diagnostic_values_recorded(self):
        for text in ("gpio_get_out_level(kMotorEnables[0])",
                     "gpioPadInitial=gpio_get(kMotorEnables[0])",
                     "gpioPadSettled=gpio_get(kMotorEnables[0])",
                     "delayMicroseconds(1300)",
                     "model_action=","model_phase=",
                     "KNX101 START_DIAG_FAILED","KNX101 START_DIAG_OK"):
            self.assertIn(text,self.fw)

    def test_06_guard_never_bypassed(self):
        self.assertIn("ack.type!=Knx099::ActionType::None || !gpioOut || !gpioPadSettled",self.fw)
        self.assertIn("motor.trip();",self.fw)
        self.assertIn("position.cancel(millis());",self.fw)
        self.assertIn("forceAllInactive();",self.fw)
        self.assertIn("gpio_put(kKnxTx,0);",self.fw)
        self.assertNotIn("gpio_put(kKnxTx,1)",self.fw)
        self.assertNotIn('if(strncmp(cmd,"PULSE "',self.fw)

    def test_07_one_shot_firmware_guard(self):
        for text in ("kStepsMaximum=5","stepsIssued!=stepsCompleted",
                     "stepsCompleted>=kStepsMaximum",
                     "motor.state()!=Knx085::Phase::Armed",
                     "motor.state()!=Knx085::Phase::Idle",
                     "KNX101 REFUSED_SEQUENCE_OR_ARM"):
            self.assertIn(text,self.fw)

    def test_08_previous_fault_is_prerequisite_for_flash(self):
        for text in ('prev.verify()','prior_state["phase"]=="FAULT_LATCHED"',
                     'prior_state["issued"]==2','prior_state["completed"]==2',
                     'prior_state["gpio_low"]','prior_state["idle_ma"]==0',
                     'match.group(1).upper()==BOARD_SERIAL',
                     '"load","-v","-x"','not flag.exists()'):
            self.assertIn(text,self.host)

    def test_09_unknown_or_out_of_sequence_motion_denied_without_serial(self):
        with patch.object(h,"board",side_effect=AssertionError("BOARD must not be accessed")):
            with self.assertRaises(h.Refused):h.pulse_step(0)
            with self.assertRaises(h.Refused):h.pulse_step(6)
            with tempfile.TemporaryDirectory() as temp:
                with patch.object(h,"OUT",Path(temp)):
                    with self.assertRaises(h.Refused):h.pulse_step(2)

    def test_10_host_emergency_stop_and_incomplete_report(self):
        self.assertIn('command(ser,"STOP")',self.host)
        self.assertIn('report["error"]=repr(exc)',self.host)
        self.assertIn('store(basename,report)',self.host)
        self.assertIn('flag.write_text(',self.host)

    def test_11_expected_timing_window_no_override(self):
        self.assertEqual(h.STEPS[0]["range_ms"],[6000,30000])
        self.assertEqual(h.STEPS[2]["expected_ms"],5688)
        self.assertEqual(h.STEPS[4]["range_ms"],[12000,30000])
        self.assertIn("need(ma<115 and 3100<=bus<=3450",self.host)
        self.assertIn("abs(vals[-1][",self.host)

    def test_12_firmware_reference_limits(self):
        for text in ("rise_ma=45 after_ms=450 consecutive=6",
                     "motor_gate=1","motor.trip();",
                     "Knx099::Model position;",
                     "position.acknowledgeAllOff(allOff)",
                     "Knx085::powerOkay(ina,true)"):
            self.assertIn(text,self.fw)

if __name__=="__main__":
    unittest.main(verbosity=2)
