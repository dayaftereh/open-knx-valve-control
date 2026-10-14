#!/usr/bin/env python3
"""KNX035 static TX hazard negative assertions. Does not touch real hardware."""
from __future__ import annotations
from copy import deepcopy
import json
import unittest

from audit_design import components
from audit_knx022_hw_preflight import schematic_labels
import audit_knx035_stknx_tx as check

class TXIdleHazardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(check.DATA.read_text(encoding="utf-8"))
        cls.pcb = components(json.loads((check.ROOT /
            "schematic/pcb_knx-valve-control_v1.2.json").read_text(
            encoding="utf-8-sig"))["shape"])
        cls.sch = schematic_labels(json.loads((check.ROOT /
            "schematic/sch_knx-valve-control_v1.2.json").read_text(
            encoding="utf-8-sig")))
        cls.controller = (check.ROOT / "src/controller/main.cpp").read_text(
            encoding="utf-8-sig")
        cls.uart = (check.ROOT /
            ".pio/libdeps/controller/TPUart/src/TPUart/Interface/ArduinoSerial.h"
            ).read_text(encoding="utf-8-sig")
        cls.dll = (check.ROOT /
            ".pio/libdeps/controller/TPUart/src/TPUart/DataLinkLayer.cpp"
            ).read_text(encoding="utf-8-sig")

    def deny(self, change):
        data = deepcopy(self.report)
        change(data)
        with self.assertRaises(check.UnsafeEvidence):
            check.audit(data,self.pcb,self.sch,self.controller,self.uart,self.dll)

    def test_source_truth(self):
        check.audit(self.report,self.pcb,self.sch,
                    self.controller,self.uart,self.dll)
        self.assertEqual(self.pcb["R17"]["pins"]["2"],"3.3V")

    def test_cannot_claim_tx_low_measurement(self):
        self.deny(lambda x: x["evidence"].update(STKNX_TX_high_actually_measured=True))

    def test_cannot_claim_u9_intact(self):
        self.deny(lambda x: x["evidence"].update(U9_damage_excluded=True))

    def test_cannot_claim_blink_binary_inspected(self):
        self.deny(lambda x: x["evidence"].update(actual_blink_program_pin_setup_verified=True))

    def test_cannot_claim_installed_u11_is_3_5_milliohm(self):
        self.deny(lambda x: x["evidence"].update(U11_photo_actual="3.5mR"))

    def test_cannot_claim_R17_already_removed(self):
        self.deny(lambda x: x["v12_current"].update(R17_removed_confirmed=True))

    def test_pull_down_cannot_use_existing_3v3_footprint(self):
        self.deny(lambda x: x["v13_ECO_proposals"].update(
            existing_R17_footprint_can_be_reused_unchanged=True))

    def test_pulldown_must_target_gnd(self):
        self.deny(lambda x: x["v13_ECO_proposals"].update(
            add_new_external_pull_down_to_GND_ohms_range=[4700,10000,20000]))

    def test_uart_not_equivalent_to_stknx_phy(self):
        self.deny(lambda x: x["v13_ECO_proposals"].update(
            replace_direct_TPUart_UART_driver_with_STKNX_pulse_phy_required=False))

    def test_cannot_authorize_bus_power(self):
        self.deny(lambda x: x["release"].update(any_KNX_bus_retest_authorized=True))

    def test_cannot_authorize_motor(self):
        self.deny(lambda x: x["release"].update(any_motor_action_authorized=True))

    def test_stknx_idle_is_low(self):
        self.deny(lambda x: x["evidence"].update(TX_idle_low=False))

if __name__ == "__main__":
    unittest.main(verbosity=2)
