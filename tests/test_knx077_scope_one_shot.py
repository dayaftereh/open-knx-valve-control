#!/usr/bin/env python3
"""Pure offline KNX077 PicoScope processing and single-FIRE guard tests."""
from __future__ import annotations
import array
import importlib.util
from pathlib import Path
import tempfile
import unittest

PROJECT=Path(__file__).resolve().parents[1]
SOURCE=PROJECT/"tools"/"knx076_tx_single_pio"/"knx077_scope_one_shot.py"
spec=importlib.util.spec_from_file_location("knx077_scope_one_shot",str(SOURCE))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ADC=32512


def counts(voltage,fullscale):
    return round(voltage*ADC/fullscale)


class TestKNX077(unittest.TestCase):
    def test_idle_gate_good(self):
        a=array.array("h",[counts(31.1,50)]*30000)
        b=array.array("h",[counts(0.086,5)]*30000)
        x,y=module.verify_idle_samples(a,b,ADC)
        self.assertAlmostEqual(x,31.1,delta=0.002)
        self.assertAlmostEqual(y,0.086,delta=0.002)

    def test_idle_gate_rejects_bad_bus_or_stuck_tx(self):
        with self.assertRaisesRegex(RuntimeError,"KNX"):
            module.verify_idle_samples(
                array.array("h",[counts(8,50)]*30000),
                array.array("h",[counts(0.08,5)]*30000),ADC)
        with self.assertRaisesRegex(RuntimeError,"TX"):
            module.verify_idle_samples(
                array.array("h",[counts(31,50)]*30000),
                array.array("h",[counts(3.3,5)]*30000),ADC)

    def test_single_scope_pulse_and_correlated_bus_dip(self):
        n=3500
        a=array.array("h",[counts(31,50)]*n)
        b=array.array("h",[counts(.08,5)]*n)
        for j in range(1500,1535):
            a[j]=counts(24,50)
            b[j]=counts(3.3,5)
        with tempfile.TemporaryDirectory() as tmp:
            pa=Path(tmp)/"a.bin"
            pb=Path(tmp)/"b.bin"
            pa.write_bytes(a.tobytes())
            pb.write_bytes(b.tobytes())
            result=module.analyze(pa,pb,ADC,1,[],0,True,(31,.08))
            self.assertEqual(result["pulses_above_1_35V"],1)
            self.assertEqual(result["events"][0]["width_us"],35)
            self.assertAlmostEqual(result["events"][0]["A_KNXPLUS_max_dropV"],7,delta=.005)
            self.assertTrue(result["one_shot_scope_success"])

    def test_two_pulses_do_not_pass(self):
        n=3500
        a=array.array("h",[counts(31,50)]*n)
        b=array.array("h",[counts(.08,5)]*n)
        for offset in (800,2000):
            for j in range(offset,offset+35):
                a[j]=counts(24,50)
                b[j]=counts(3.3,5)
        with tempfile.TemporaryDirectory() as tmp:
            pa=Path(tmp)/"a.bin"
            pb=Path(tmp)/"b.bin"
            pa.write_bytes(a.tobytes())
            pb.write_bytes(b.tobytes())
            result=module.analyze(pa,pb,ADC,1,[],0,True,(31,.08))
            self.assertEqual(result["pulses_above_1_35V"],2)
            self.assertFalse(result["one_shot_scope_success"])

    def test_source_contains_one_fire_command(self):
        txt=SOURCE.read_text(encoding="utf-8")
        self.assertEqual(txt.count('usb_send("FIRE ONE")'),1)
        self.assertIn("fire_one_sent=True",txt)
        self.assertIn("stage=3",txt)
        self.assertIn("--confirm-lab-setup",txt)
        self.assertIn("--execute",txt)


if __name__=="__main__":
    unittest.main()
