#!/usr/bin/env python3
"""KNX030 passive host-inventory unit tests. All device calls mocked."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import knx030_passive_inventory as knx


RAW = {
    "source_kind": "local_os_metadata_only",
    "usb_and_ports": [
        {
            "instance_id": "USB\\VID_1A86&PID_7523\\SENSITIVE_SERIAL_0001",
            "display_name": "USB-SERIAL CH340 (COM5)",
            "class_name": "Ports",
            "status": "OK",
        }
    ],
    "rp2_volumes": [],
    "local_network_adapters": [
        {"name": "WLAN", "description": "Intel Wireless",
         "status": "Up"},
        {"name": "Ethernet", "description": "Intel Ethernet",
         "status": "Disconnected"},
    ],
}


class FakeWindows:
    def __init__(self, response=None, code=0, output=None):
        self.response = response if response is not None else RAW
        self.code = code
        self.output = output
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        assert len(args) == 7, "Unexpected PowerShell arguments"
        assert args[0] == "powershell.exe"
        assert args[1:6] == [
            "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-File",
        ]
        assert args[6].endswith("knx030_passive_inventory_probe.ps1")
        assert not any(
            item.lower() in ("upload", "erase", "flash", "com5",
                             "picotool", "pymcuprog")
            for item in args)
        return subprocess.CompletedProcess(
            args, self.code,
            stdout=self.output if self.output is not None else
            json.dumps(self.response),
            stderr="mock OS error" if self.code else "")


class PassiveInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knx030-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.one = self.folder / "disconnected.json"

    def test_default_plan_is_subprocess_free(self):
        with patch("knx030_passive_inventory.subprocess.run",
                   side_effect=AssertionError("plan contacted Windows")):
            captured = io.StringIO()
            with redirect_stdout(captured):
                self.assertEqual(knx.main([]), 0)
            p = json.loads(captured.getvalue())
            self.assertTrue(p["no_device_IO"])
            self.assertFalse(p["knx_ip_discovery"])
            self.assertFalse(p["flash_or_motor_authority"])
            self.assertFalse(any(p["hardware_release_gates"].values()))

    def test_capture_redacts_serial_and_preserves_only_os_hints(self):
        win = FakeWindows()
        record = knx.capture(
            str(self.one), "disconnected", runner=win,
            powershell="powershell.exe")
        self.assertEqual(len(win.calls), 1)
        self.assertEqual(len(record["devices"]), 1)
        device = record["devices"][0]
        self.assertEqual(device["vid_pid"], "1A86:7523")
        self.assertEqual(device["com_port"], "COM5")
        self.assertEqual(device["candidate_hint"], "usb_serial_candidate")
        self.assertEqual(len(device["instance_sha256"]), 64)
        self.assertNotIn("instance_id", device)
        self.assertNotIn("SENSITIVE_SERIAL_0001", self.one.read_text())
        self.assertEqual(record["local_network_adapters"][0]["classification"],
                         "local_link_only_not_knx_ip")
        self.assertTrue(all(g is False for g in
                            record["hardware_release_gates"].values()))

    def test_board_like_vendor_is_candidate_not_release(self):
        payload = json.loads(json.dumps(RAW))
        payload["usb_and_ports"] = [{
            "instance_id": "USB\\VID_2E8A&PID_0003\\PRIVATE_ID",
            "display_name": "RP2 Boot",
            "class_name": "USB", "status": "OK"}]
        payload["rp2_volumes"] = [{
            "label": "RPI-RP2", "drive_letter": "E", "file_system": "FAT"}]
        record = knx.normalize(payload, "plugged", "2026-10-13T11:00:00Z")
        self.assertEqual(record["devices"][0]["candidate_hint"],
                         "rp2040_vendor_candidate")
        self.assertEqual(record["rp2_volumes"][0]["classification"],
                         "bootsel_volume_candidate_only")
        self.assertFalse(any(record["hardware_release_gates"].values()))

    def test_diff_new_candidates_no_false_knx_device(self):
        before = knx.normalize(
            {**RAW, "usb_and_ports": [], "rp2_volumes": []}, "unplugged")
        after_raw = json.loads(json.dumps(RAW))
        after_raw["rp2_volumes"] = [{
            "label": "RPI-RP2", "drive_letter": "G", "file_system": "FAT"}]
        after_raw["local_network_adapters"][0]["status"] = "Disconnected"
        after = knx.normalize(after_raw, "plugged")
        result = knx.compare(before, after)
        self.assertEqual(result["new_com_port_names"], ["COM5"])
        self.assertEqual(len(result["new_usb_port_candidates"]), 1)
        self.assertEqual(len(result["new_rp2_volume_candidates"]), 1)
        self.assertEqual(len(result["local_adapter_link_changes"]), 1)
        self.assertFalse(result["knx_ip_gateway_verified"])
        self.assertFalse(result["rp2040_or_attiny_identity_verified"])

    def test_offline_compare_cannot_call_subprocess(self):
        a = knx.normalize(RAW, "a")
        b = knx.normalize(RAW, "b")
        self.one.write_text(json.dumps(a))
        next_file = self.folder / "b.json"
        next_file.write_text(json.dumps(b))
        with patch("knx030_passive_inventory.subprocess.run",
                   side_effect=AssertionError("comparison did OS I/O")):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(knx.main(["compare", "--before",
                                           str(self.one), "--after",
                                           str(next_file)]), 0)
            self.assertEqual(json.loads(out.getvalue())
                             ["new_usb_port_candidates"], [])

    def test_dirty_or_in_repo_destination_refused_before_probe(self):
        self.one.write_text("existing")
        fn = FakeWindows()
        with self.assertRaisesRegex(knx.InventoryError, "overwrite"):
            knx.capture(str(self.one), "disconnected", runner=fn,
                        powershell="powershell.exe")
        with self.assertRaisesRegex(knx.InventoryError, "OUTSIDE"):
            knx.capture(str(knx.ROOT / "oops.json"), "disconnected",
                        runner=fn, powershell="powershell.exe")
        self.assertEqual(fn.calls, [])

    def test_malformed_os_json_and_failed_windows_probe_fail_closed(self):
        for proc in (FakeWindows(output="{not-json"),
                     FakeWindows(code=1)):
            with self.assertRaises(knx.InventoryError):
                knx.capture(str(self.one), "unplugged",
                            runner=proc, powershell="powershell.exe")
            self.assertFalse(self.one.exists())

    def test_bad_source_label_and_duplicate_device_input(self):
        raw = dict(RAW)
        raw["source_kind"] = "network_probe"
        with self.assertRaises(knx.InventoryError):
            knx.normalize(raw, "before")
        with self.assertRaises(knx.InventoryError):
            knx.normalize(RAW, "a b")
        duplicate = json.loads(json.dumps(RAW))
        duplicate["usb_and_ports"].append(duplicate["usb_and_ports"][0])
        snapshot = knx.normalize(duplicate, "dup")
        # Multiple appearances of the same OS instance are de-duplicated.
        self.assertEqual(len(snapshot["devices"]), 1)

    def test_tampered_snapshot_cannot_authorize_motor(self):
        a = knx.normalize(RAW, "before")
        a["hardware_release_gates"]["motor_enable_authorized"] = True
        with self.assertRaisesRegex(knx.InventoryError, "cannot claim"):
            knx.validate(a)
        with self.assertRaises(knx.InventoryError):
            knx.compare(a, a)

    def test_tampered_snapshot_cannot_export_raw_instance_id(self):
        a = knx.normalize(RAW, "before")
        a["devices"][0]["instance_id"] = "RAW_PRIVACY_SECRET"
        with self.assertRaisesRegex(knx.InventoryError, "raw or malformed"):
            knx.validate(a)

    def test_input_without_arrays_is_rejected(self):
        for key in ("usb_and_ports", "rp2_volumes", "local_network_adapters"):
            bad = json.loads(json.dumps(RAW))
            bad.pop(key)
            with self.assertRaises(knx.InventoryError):
                knx.normalize(bad, "before")


if __name__ == "__main__":
    unittest.main(verbosity=2)
