#!/usr/bin/env python3
"""KNX033 negative tests: no photo can create power/KNX/motor release."""
from copy import deepcopy
import json
import unittest

import audit_knx033_asbuilt as review
from audit_design import components
from audit_knx022_hw_preflight import schematic_labels


class PhotoGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(review.REPORT.read_text(encoding="utf-8"))
        pcb = json.loads((review.ROOT /
                          "schematic/pcb_knx-valve-control_v1.2.json")
                         .read_text(encoding="utf-8-sig"))
        sch = json.loads((review.ROOT /
                          "schematic/sch_knx-valve-control_v1.2.json")
                         .read_text(encoding="utf-8-sig"))
        cls.pcb = components(pcb["shape"])
        cls.labels = schematic_labels(sch)

    def check_reject(self, mutate):
        doc = deepcopy(self.data)
        mutate(doc)
        with self.assertRaises(review.ReviewError):
            review.audit_document(doc, self.pcb, self.labels)

    def test_baseline_remains_blocked(self):
        review.audit_document(self.data, self.pcb, self.labels)
        self.assertEqual(self.data["status"], review.STATUS)
        self.assertFalse(any(self.data["pre_energization_release"].values()))
        self.assertTrue(all(v is None for v in
                            self.data["unpowered_checks"].values()))

    def test_original_image_hash_cannot_change_silently(self):
        self.check_reject(lambda d: d["photos"][0].update({"sha256": "0"*64}))

    def test_fuse_2_5A_cannot_be_marked_630mA(self):
        self.check_reject(lambda d: d["observations"]["F1"].update(
            {"photo_apparent_nominal_mA": 630}))

    def test_fuse_schematic_630mA_cannot_be_edited_in_report(self):
        self.check_reject(lambda d: d["observations"]["F1"].update(
            {"schematic_nominal_mA": 2500}))

    def test_photo_cannot_claim_U6_installed_on_reverse(self):
        self.check_reject(lambda d: d["observations"]["U6"].update(
            {"installed_location": "underside verified"}))

    def test_photo_cannot_claim_attiny_signature(self):
        self.check_reject(lambda d: d["observations"]["U25"].update(
            {"hardware_mcu_signature": "ATtiny3216"}))

    def test_photo_cannot_claim_shunt_200_milliohms(self):
        self.check_reject(lambda d: d["observations"]["R29"].update(
            {"actual_ohms": 0.2}))

    def test_synthetic_continuity_measurement_is_forbidden(self):
        self.check_reject(lambda d: d["unpowered_checks"].update(
            {"D1_pad1_2_ohms": 0.0}))

    def test_jumper_user_statement_is_not_ohmmeter_result(self):
        self.check_reject(lambda d: d["reported_modifications"]["JMP1"].update(
            {"electrical_verified": True}))

    def test_diode_reverse_blocking_cannot_be_implied(self):
        self.check_reject(lambda d: d["reported_modifications"]["D1"].update(
            {"effect": "original diode protects all supplies"}))

    def test_invalid_jumper_net_contract_refused(self):
        self.check_reject(lambda d: d["net_contracts"]["JMP3"].update(
            {"3": "KNX_RX'"}))

    def test_false_physical_release_gate_rejected(self):
        self.check_reject(lambda d: d["pre_energization_release"].update(
            {"any_power_on_authorized": True}))

    def test_false_motor_release_gate_rejected(self):
        self.check_reject(lambda d: d["pre_energization_release"].update(
            {"motor_enable_authorized": True}))

    def test_mcu_type_still_has_metadata_discrepancy(self):
        self.assertEqual(self.labels["U25"]["display"], "ATTINY3216")
        self.assertEqual(self.pcb["U25"]["meta"]["Manufacturer Part"],
                         "ATTINY1616-SN")

    def test_actual_source_net_contract(self):
        self.assertEqual(self.pcb["D1"]["pins"]["1"], "D1_1")
        self.assertEqual(self.pcb["D1"]["pins"]["2"], "5V")
        self.assertEqual(self.pcb["JMP1"]["pins"]["1"], "KNX_VCC")
        self.assertEqual(self.pcb["JMP1"]["pins"]["2"], "R9_2")
        self.assertEqual(self.pcb["JMP2"]["pins"]["1"], "KNX_RX'")
        self.assertEqual(self.pcb["JMP3"]["pins"]["3"], "KNX_TX'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
