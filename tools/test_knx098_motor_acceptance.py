#!/usr/bin/env python3
"""KNX098 offline acceptance regression. No board access, no motor commands."""
from __future__ import annotations
import csv,json,shutil,tempfile,unittest
from pathlib import Path
import knx098_motor_acceptance as acc

LIVE_DATA=acc.DEFAULT_DATA
PROFILE=acc.DEFAULT_PROFILE

class KNX098AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=json.loads(PROFILE.read_text("utf8"))

    def test_01_profile_is_bench_only(self):
        p=self.baseline
        self.assertEqual(p["status"],"bench_accepted_current_endstop_candidates")
        self.assertTrue(p["acceptance"]["full_stroke_current_detection"])
        self.assertTrue(p["acceptance"]["six_full_strokes_repeated"])
        self.assertFalse(p["acceptance"]["intermediate_positions_measured"])
        self.assertFalse(p["acceptance"]["absolute_mechanical_endstops_verified"])
        self.assertFalse(p["acceptance"]["open_closed_mapping_defined"])
        self.assertFalse(p["acceptance"]["knx_ets_product_firmware_released"])

    def test_02_immutable_six_evidence_fingerprints(self):
        rec=self.baseline["source_trials"]
        self.assertEqual([x["direction"] for x in rec],list("RFRFRF"))
        self.assertEqual(sum(x["sample_count"] for x in rec),17678)
        self.assertEqual(len({x["csv_sha256"] for x in rec}),6)
        self.assertEqual(len({x["json_sha256"] for x in rec}),6)
        for x in rec:
            self.assertEqual(len(x["csv_sha256"]),64)
            self.assertEqual(len(x["json_sha256"]),64)
            self.assertTrue(x["gpio_low"] and x["full_trace_8ms"])
            self.assertTrue(x["first_sustained_rise_at_cutoff"])

    def test_03_direction_timing_and_limits(self):
        p=self.baseline
        self.assertAlmostEqual(p["directional_stroke_ms"]["R"],24388.333,places=3)
        self.assertEqual(p["directional_stroke_ms"]["F"],22751)
        self.assertEqual(p["repeatability"]["R"]["spread_ms"],216)
        self.assertEqual(p["repeatability"]["F"]["spread_ms"],144)
        self.assertLess(p["repeatability"]["R"]["cv_percent"],1)
        self.assertLess(p["repeatability"]["F"]["cv_percent"],1)
        self.assertEqual(p["guards"]["ina_threshold_ma"],45)
        self.assertEqual(p["guards"]["ina_consecutive_samples"],6)
        self.assertEqual(p["guards"]["absolute_current_limit_ma"],120)
        self.assertEqual(p["guards"]["max_stroke_ms"],30000)
        self.assertEqual(p["guards"]["ina_period_ms"],8)

    def test_04_one_noise_peak_is_not_an_endstop(self):
        series=[(450+8*i,45 if i in (5,11,17) else 30)
                for i in range(60)]
        self.assertIsNone(acc.first_streak(series,lambda ma:ma>=45))

    def test_05_threshold_needs_six_in_order(self):
        seq=[(450+8*i,45 if i>=7 else 24) for i in range(13)]
        self.assertEqual(acc.first_streak(seq,lambda ma:ma>=45),546)
        self.assertIsNone(acc.first_streak(seq[:-1],lambda ma:ma>=45))

    def test_06_early_inrush_is_ignored(self):
        seq=[(7+8*i,90) for i in range(50)]
        self.assertIsNone(acc.first_streak(seq,lambda ma:ma>=45))
        seq.extend((450+8*i,49) for i in range(6))
        self.assertEqual(acc.first_streak(seq,lambda ma:ma>=45),490)

    def test_07_statistical_spread_is_directional(self):
        r=acc.compute_stats([24423,24479,24263])
        f=acc.compute_stats([22767,22815,22671])
        self.assertEqual(r["spread_ms"],216)
        self.assertEqual(f["spread_ms"],144)
        self.assertAlmostEqual(r["mean_ms"],24388.333,places=3)
        self.assertEqual(f["mean_ms"],22751)
        self.assertLess(r["cv_percent"],.4)
        self.assertLess(f["cv_percent"],.3)

    @unittest.skipUnless(LIVE_DATA.exists(),"Original private KNX097 runtime traces are not mounted")
    def test_08_verify_all_raw_samples_against_frozen_profile(self):
        self.assertEqual(acc.evaluate(LIVE_DATA),self.baseline)

    def _single_leg_fixture(self,folder):
        for ext in (".json",".csv"):
            shutil.copyfile(LIVE_DATA/("KNX097_LEG_01_R"+ext),
                            folder/("KNX097_LEG_01_R"+ext))

    @unittest.skipUnless(LIVE_DATA.exists(),"Original private runtime traces not mounted")
    def test_09_missing_evidence_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            shutil.copyfile(LIVE_DATA/"KNX097_LEG_01_R.json",
                            d/"KNX097_LEG_01_R.json")
            with self.assertRaises(acc.Rejected):
                acc.inspect_leg(d,1,"R")

    @unittest.skipUnless(LIVE_DATA.exists(),"Original private runtime traces not mounted")
    def test_10_single_trace_timing_gap_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);self._single_leg_fixture(d)
            p=d/"KNX097_LEG_01_R.csv"
            with p.open("r",encoding="utf8",newline="") as file:
                values=list(csv.DictReader(file))
            values[1500]["ms"]=str(int(values[1500]["ms"])+1)
            with p.open("w",encoding="utf8",newline="") as file:
                writer=csv.DictWriter(file,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values)
            with self.assertRaisesRegex(acc.Rejected,"missing/duplicate/shifted"):
                acc.inspect_leg(d,1,"R")

    @unittest.skipUnless(LIVE_DATA.exists(),"Original private runtime traces not mounted")
    def test_11_premature_sustained_current_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);self._single_leg_fixture(d)
            p=d/"KNX097_LEG_01_R.csv"
            with p.open("r",encoding="utf8",newline="") as file:
                values=list(csv.DictReader(file))
            # Introduce a counterfeit six-sample earlier hard-stop; adjust
            # shunt and displayed derived current consistently.
            for item in values[1000:1006]:
                item["shunt_raw"]="980"
                item["shunt_uV"]="9800"
                item["ma"]="49.0"
            with p.open("w",encoding="utf8",newline="") as file:
                writer=csv.DictWriter(file,fieldnames=list(values[0]))
                writer.writeheader();writer.writerows(values)
            with self.assertRaisesRegex(acc.Rejected,"guard replay contradicts"):
                acc.inspect_leg(d,1,"R")

    @unittest.skipUnless(LIVE_DATA.exists(),"Original private runtime traces not mounted")
    def test_12_non_loadrise_end_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);self._single_leg_fixture(d)
            p=d/"KNX097_LEG_01_R.json"
            doc=json.loads(p.read_text("utf8"))
            doc["candidate"]["type"]="CURRENT_CUT"
            p.write_text(json.dumps(doc),encoding="utf8")
            with self.assertRaisesRegex(acc.Rejected,"direction/endstop/elapsed"):
                acc.inspect_leg(d,1,"R")

if __name__=="__main__":
    unittest.main(verbosity=2)
