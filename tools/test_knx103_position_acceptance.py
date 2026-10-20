#!/usr/bin/env python3
"""KNX103 USB-position acceptance negative tests, no COM/USB/motor access."""
from __future__ import annotations
import csv,json,shutil,tempfile,unittest
from pathlib import Path
import knx103_position_acceptance as a

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=json.loads(a.FROZEN.read_text("utf8"))

    def test_01_original_profile_reproducible(self):
        self.assertEqual(a.evaluate(a.DATA),self.ref)

    def test_02_five_ordered_moves(self):
        rows=self.ref["trials"]
        self.assertEqual([(x["direction"],x["target_internal_r_permille"]) for x in rows],
                         [("R",1000),("F",500),("F",250),("R",750),("F",0)])
        self.assertEqual([x["cutoff_ms"] for x in rows],[12951,11383,5694,12199,16599])

    def test_03_total_trace_integrity(self):
        self.assertEqual(self.ref["complete_8ms_ina_samples"],7354)
        self.assertTrue(all(x["all_8ms_samples_complete"] for x in self.ref["trials"]))
        self.assertTrue(all(x["stop_and_idle_acknowledged"] for x in self.ref["trials"]))
        self.assertEqual(len({x["source_trace_csv_sha256"] for x in self.ref["trials"]}),5)
        self.assertEqual(len({x["source_result_json_sha256"] for x in self.ref["trials"]}),5)

    def test_04_directional_timer_precision_and_limits(self):
        self.assertEqual(self.ref["timed_cutoff_jitter_ms"],[7,6,5])
        self.assertTrue(all(x["raw_current_peak_ma"]<=120 for x in self.ref["trials"]))
        self.assertTrue(all(3100<=x["bus_mv_min"]<=x["bus_mv_max"]<=3450
                            for x in self.ref["trials"]))
        self.assertEqual(self.ref["F_reference_from_internal_750"]["difference_actual_minus_expected_ms"],-464)

    def test_05_position_labels_are_not_mechanical_truth(self):
        self.assertFalse(self.ref["mechanical_valve_open_close_mapped"])
        self.assertFalse(self.ref["absolute_mid_position_encoder_verified"])
        self.assertIn("no_KNX_ETS",self.ref["release_status"])

    def _copy(self,folder,i=1):
        d,t,ms,n,kind,evidence,planned=a.STEPS[i-1]
        stem=f"KNX101_STEP_{i:02d}_{d}"
        for ext in (".json",".csv"):
            shutil.copyfile(a.DATA/(stem+ext),folder/(stem+ext))
        return folder/(stem+".json"),folder/(stem+".csv")

    def test_06_bad_sample_count_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            lines=cp.read_text("utf8").splitlines()
            cp.write_text("\n".join(lines[:-1])+"\n",encoding="utf8")
            with self.assertRaises(a.Invalid):a.inspect(td,1)

    def test_07_gap_in_sample_timing_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            with cp.open(newline="",encoding="utf8") as f:
                rows=list(csv.DictReader(f))
            rows[1000]["ms"]=str(int(rows[1000]["ms"])+1)
            with cp.open("w",encoding="utf8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]))
                writer.writeheader();writer.writerows(rows)
            with self.assertRaisesRegex(a.Invalid,"lost INA sample"):a.inspect(td,1)

    def test_08_early_sustained_current_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            with cp.open(newline="",encoding="utf8") as f:rows=list(csv.DictReader(f))
            for r in rows[200:206]:
                r["shunt_raw"]="1000"
                r["shunt_uV"]="10000"
                r["ma"]="50.0"
            with cp.open("w",newline="",encoding="utf8") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            with self.assertRaisesRegex(a.Invalid,"not first continuous current rise"):
                a.inspect(td,1)

    def test_09_bad_bus_voltage_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            with cp.open(newline="",encoding="utf8") as f:rows=list(csv.DictReader(f))
            rows[200]["bus_mv"]="2800"
            with cp.open("w",newline="",encoding="utf8") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            with self.assertRaisesRegex(a.Invalid,"supply/current"):a.inspect(td,1)

    def test_10_wrong_gpio_ack_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            doc=json.loads(jp.read_text("utf8"))
            doc["rx_excerpt"]=[x.replace("START_DIAG_OK","START_DIAG_FAILED")
                               for x in doc["rx_excerpt"]]
            jp.write_text(json.dumps(doc),encoding="utf8")
            with self.assertRaisesRegex(a.Invalid,"no correct GPIO"):
                a.inspect(td,1)

    def test_11_wrong_position_or_cutoff_refused(self):
        with tempfile.TemporaryDirectory() as td:
            jp,cp=self._copy(Path(td))
            doc=json.loads(jp.read_text("utf8"))
            doc["postflight"]["position"]=500
            jp.write_text(json.dumps(doc),encoding="utf8")
            with self.assertRaisesRegex(a.Invalid,"position evidence"):
                a.inspect(td,1)

    def test_12_recovery_when_no_KNX_bus_requires_no_COM(self):
        s=Path(a.__file__).read_text("utf8")
        self.assertNotIn("import serial",s)
        self.assertNotIn('command(ser,',s)
        self.assertNotIn('gpio_put(',s)

if __name__=="__main__":
    unittest.main(verbosity=2)
