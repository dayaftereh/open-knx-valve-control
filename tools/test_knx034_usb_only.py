#!/usr/bin/env python3
"""KNX034 fail-closed documentation-gate tests, no physical hardware."""
from copy import deepcopy
import json
import unittest

from audit_design import components
import audit_knx034_usb_only as gate


class USBOnlyPrepowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(gate.REPORT.read_text(encoding="utf-8"))
        source = json.loads(
            (gate.ROOT / "schematic/pcb_knx-valve-control_v1.2.json")
            .read_text(encoding="utf-8-sig"))
        cls.pcb = components(source["shape"])

    def deny(self, fn):
        changed = deepcopy(self.report)
        fn(changed)
        with self.assertRaises(gate.ReviewBlocked):
            gate.validate(changed, self.pcb)

    def test_original_read_only_proposal(self):
        gate.validate(self.report, self.pcb)
        self.assertEqual(self.report["proposed_jmp1"]["state"],
                         "PROPOSED_NOT_APPLIED")
        self.assertFalse(any(self.report["releases"].values()))
        self.assertTrue(all(v is None for v in
                            self.report["unpowered_measured"].values()))

    def test_dont_treat_user_proposal_as_solder_operation(self):
        self.deny(lambda x: x["proposed_jmp1"].update(
            physical_change_performed=True))

    def test_dont_claim_isolation_from_jumper(self):
        self.deny(lambda x: x["proposed_jmp1"].update(
            galvanic_isolation_proven=True))

    def test_dont_claim_no_backfeed(self):
        self.deny(lambda x: x["proposed_jmp1"].update(
            KNX_USB_backfeed_absence_proven=True))

    def test_dont_invent_measured_open_jumper(self):
        self.deny(lambda x: x["proposed_jmp1"].update(
            measured_resistance_ohms=1e7))

    def test_dont_hide_fuse_numerical_mismatch(self):
        self.deny(lambda x: x["f1"].update(
            observed_photo_mA=630))

    def test_fuse_coordinated_cannot_be_claimed(self):
        self.deny(lambda x: x["f1"].update(
            protective_coordination_verified=True))

    def test_cannot_claim_d1_reverse_diode_exists(self):
        self.deny(lambda x: x["d1"].update(
            original_diode_directional_isolation_removed=False))

    def test_u6_visible_not_equal_validated_vin(self):
        self.deny(lambda x: x["u6"].update(
            actual_VIN_V=5.0))

    def test_u6_part_marking_still_unreadable(self):
        self.deny(lambda x: x["u6"].update(
            exact_part_marking_verified=True))

    def test_no_dmm_measurements(self):
        self.deny(lambda x: x["unpowered_measured"].update(
            JMP1_pad1_2_after_ohms=3000000))

    def test_no_new_power_authorization(self):
        self.deny(lambda x: x["releases"].update(
            usb_only_power_authorized=True))

    def test_no_implicit_knx_authorization(self):
        self.deny(lambda x: x["releases"].update(
            knx_bus_connection_authorized=True))

    def test_no_motor_permission(self):
        self.deny(lambda x: x["releases"].update(
            motor_enable_authorized=True))

    def test_no_image_archive_fabrication(self):
        self.deny(lambda x: x["new_photo"].update(
            image_archived_on_home=True))

    def test_original_photo_integrity(self):
        self.deny(lambda x: x["new_photo"].update(
            sha256="0"*64))


if __name__ == "__main__":
    unittest.main(verbosity=2)
