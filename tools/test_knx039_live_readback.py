#!/usr/bin/env python3
"""KNX039 live-updi evidence integrity tests; no serial, flash or target access."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"docs/KNX039_UPDI_READBACK_EVIDENCE.json"

class ReadbackEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=json.loads(REPORT.read_text(encoding="utf-8-sig"))

    def test_identity_grounded_by_live_signature(self):
        self.assertEqual(self.e["schema"],"openknx-valvecontrol/knx039-live-readback-evidence-v1")
        self.assertEqual(self.e["device"]["measured_signature"],"1E9521")
        self.assertEqual(self.e["device"]["confirmed_model"],"ATtiny3216")
        self.assertEqual(self.e["device"]["usb_vidpid"],"1A86:7523")

    def test_target_com_not_the_rp2040(self):
        self.assertEqual(self.e["device"]["com"],"COM4")
        self.assertNotEqual(self.e["device"]["com"],"COM7")
        self.assertTrue(self.e["programmer"]["physical_port_connection_validated_by_successful_response"])

    def test_all_five_calls_no_nvm_writes(self):
        calls=self.e["calls"]
        self.assertEqual([(c["operation"],c["memory"]) for c in calls],
             [("ping",None),("read","flash"),("read","eeprom"),
              ("read","fuses"),("read","user_row")])
        self.assertTrue(all(c["status"]=="PASS" and c["nvm_write"] is False for c in calls))

    def test_never_claim_measured_3v3_5v_safety(self):
        self.assertFalse(self.e["programmer"]["RTS_line_voltage_measured"])
        self.assertFalse(self.e["programmer"]["power_voltage_compatibility_measured"])
        self.assertTrue(all(v is False for v in self.e["source_hazards_open"].values()))

    def test_no_erase_or_flash_action(self):
        self.assertTrue(all(v is False for v in self.e["actions_not_performed"].values()))
        self.assertFalse(self.e["new_temperature_build"]["uploaded_to_target"])
        self.assertEqual(self.e["result"],"UPDI_SIGNATURE_AND_MEMORY_READBACK_PASS_NO_NVM_WRITE")

    def test_memory_image_shapes(self):
        p=self.e["readback"]
        self.assertEqual(p["flash"]["bytes"],32768)
        self.assertEqual(p["eeprom"]["bytes"],256)
        self.assertEqual(p["fuses"]["bytes"],9)
        self.assertEqual(p["user_row"]["bytes"],32)
        self.assertTrue(p["all_hex_checksums_valid"])
        self.assertTrue(p["eeprom"]["all_ff"])
        self.assertTrue(p["user_row"]["all_ff"])

    def test_build_diff_not_claimed_identical(self):
        p=self.e["new_temperature_build"]
        self.assertEqual(p["flash_defined_bytes"],8655)
        self.assertEqual(p["different_defined_bytes"],8450)
        self.assertEqual(p["first_different_address"],"0x2")
        self.assertFalse(p["firmware_matches_existing_flash"])

    def test_backup_sha256_when_desktop_file_is_available(self):
        folder=Path(self.e["readback"]["directory"])
        if not folder.is_dir():
            self.skipTest("Private backup files are intentionally not in Git/Home")
        manifest=json.loads((folder/"readback_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["target_signature"],"1E9521")
        self.assertTrue(manifest["no_write_actions_performed"])
        for name in ("flash","eeprom","fuses","user_row"):
            value=self.e["readback"][name]
            raw=(folder/value["file"]).read_bytes()
            actual=hashlib.sha256(raw).hexdigest()
            self.assertEqual(actual,manifest["files"][name]["file_sha256"])
            if value.get("sha256"):self.assertEqual(actual,value["sha256"])
            self.assertEqual(manifest["files"][name]["memory_defined_bytes"],value["bytes"])

if __name__=="__main__":
    unittest.main(verbosity=2)
