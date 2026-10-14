"""Offline tests for KNX043 Home KNX safety gate; no hardware access."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knx043_home_knx_preflight as pf


class Knx043HomePreflightTests(unittest.TestCase):
    def gate(self, value=None):
        return {
            "schema": pf.SCHEMA,
            "observations": {name: value for name in pf.REQUIRED_PHYSICAL_GATES},
        }

    def test_missing_and_null_gate_is_blocked(self):
        entry = self.gate()
        result = pf.classify_gate(entry)
        self.assertEqual(result["status"], "BLOCKED_AWAIT_HARDWARE_EVIDENCE")
        self.assertEqual(result["physical_items_confirmed"], 0)
        self.assertEqual(len(result["unverified_items"]), len(pf.REQUIRED_PHYSICAL_GATES))
        self.assertFalse(result["knx_power_or_bus_connection_authorized"])

    def test_all_true_never_grants_automatic_bus_authorization(self):
        gate = self.gate(True)
        result = pf.classify_gate(gate)
        self.assertEqual(result["status"], "CHECKLIST_COMPLETE_NEEDS_INDEPENDENT_SAFETY_REVIEW")
        self.assertEqual(result["unverified_items"], [])
        self.assertFalse(result["knx_power_or_bus_connection_authorized"])

    def test_one_false_still_blocks(self):
        gate = self.gate(True)
        gate["observations"]["u11_actual_68ohm_and_thermal_damage_checked"] = False
        result = pf.classify_gate(gate)
        self.assertEqual(result["status"], "BLOCKED_AWAIT_HARDWARE_EVIDENCE")
        self.assertEqual(result["unverified_items"], ["u11_actual_68ohm_and_thermal_damage_checked"])

    def test_invalid_null_bool_types_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate.json"
            entry = self.gate()
            entry["observations"]["u11_actual_68ohm_and_thermal_damage_checked"] = "yes"
            path.write_text(json.dumps(entry), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Gates must be null or boolean"):
                pf.load_gate(path)

    def test_missing_required_gate_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"gate.json"
            entry=self.gate()
            del entry["observations"]["no_actual_motor_connected"]
            path.write_text(json.dumps(entry),encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required physical gates"):
                pf.load_gate(path)

    def test_hashes_are_verified_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"image.uf2"
            p.write_bytes(b"KNX043-FAKE-DO-NOT-FLASH")
            digest=pf.hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertTrue(pf.file_integrity(p,digest)["hash_match"])
            self.assertFalse(pf.file_integrity(p,"0"*64)["hash_match"])
            self.assertFalse(pf.file_integrity(Path(tmp)/"missing.uf2",digest)["present"])

    def test_inventory_has_no_host_device_or_bus_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate=self.gate()
            result=pf.inventory(gate,Path(tmp),Path(tmp)/"builds")
            self.assertFalse(result["device_connection_attempted"])
            self.assertFalse(result["knx_frame_sent"])
            self.assertFalse(result["firmware_flash_attempted"])
            self.assertFalse(result["hardware_gate"]["knx_power_or_bus_connection_authorized"])
            self.assertIn("KNX043",result["operation"])

    def test_real_template_is_initially_blocked(self):
        p=Path(__file__).resolve().parent.parent/"docs"/"KNX043_HOME_KNX_GATE.json"
        gate=pf.load_gate(p)
        result=pf.classify_gate(gate)
        self.assertEqual(result["status"],"BLOCKED_AWAIT_HARDWARE_EVIDENCE")
        self.assertFalse(result["knx_power_or_bus_connection_authorized"])


if __name__=="__main__":
    unittest.main()
