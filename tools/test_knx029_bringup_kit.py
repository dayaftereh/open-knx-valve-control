#!/usr/bin/env python3
"""KNX029 offline candidate-bundle and first-contact interlock tests.

Runs only fake PlatformIO/Git commands in temporary directories. No USB,
COM enumeration, UPDI, KNX bus, target flash, or motor access.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import knx029_prepare_bringup as kit


HEAD = "a" * 40
OTHER_HEAD = "b" * 40


class FakeRunner:
    def __init__(self, *, head: str = HEAD, dirty: bool = False,
                 fail_target: str = "", missing_hex: bool = False,
                 change_head_midbuild: bool = False) -> None:
        self.head = head
        self.dirty = dirty
        self.fail_target = fail_target
        self.missing_hex = missing_hex
        self.change_head_midbuild = change_head_midbuild
        self.calls: list[list[str]] = []
        self.snapshots = 0
        self.attiny_config_safe = False

    def __call__(self, command, **kwargs):
        cmd = [str(x) for x in command]
        self.calls.append(cmd)
        if cmd[0] == "git":
            if "rev-parse" in cmd:
                self.snapshots += 1
                ref = OTHER_HEAD if (self.change_head_midbuild and
                                     self.snapshots > 1) else self.head
                return subprocess.CompletedProcess(cmd, 0, stdout=ref + "\n")
            if "status" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=(" M README.md\n" if self.dirty else ""))
            raise AssertionError("Unsupported fake Git command: " + str(cmd))
        assert "-t" not in cmd, "No PlatformIO upload target permitted"
        assert "upload" not in cmd and "erase" not in cmd
        assert "device" not in cmd and "monitor" not in cmd
        assert cmd[-2:] in (["-e", "controller"], ["-e", "temperature"])
        tmp = Path(kwargs["cwd"])
        target = cmd[-1]
        if target == "temperature":
            conf = (tmp / "src" / "temperature" / "temperature.ini").read_text()
            self.attiny_config_safe = all(
                value not in conf for value in
                ("upload_protocol", "init_updi.py", "autodetect_port.py",
                 "upload_command", "monitor_rts"))
        if target == self.fail_target:
            return subprocess.CompletedProcess(cmd, 5)
        place = tmp / ".pio" / "build" / target
        place.mkdir(parents=True, exist_ok=True)
        (place / "firmware.elf").write_bytes(("ELF:" + target).encode())
        if target == "controller":
            (place / "firmware.uf2").write_bytes(b"UF2-CONTROLLER-MOCK")
        if target == "temperature" and not self.missing_hex:
            (place / "firmware.hex").write_bytes(b":00000001FF\n")
        return subprocess.CompletedProcess(cmd, 0)


class KNX029OfflineKitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knx029-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.pio = self.dir / "fake-pio.exe"
        self.producer = self.dir / "fake-producer.exe"
        self.pio.write_bytes(b"fake")
        self.producer.write_bytes(b"fake")
        self.out = self.dir / "candidate-1"

    def build(self, runner: FakeRunner, target: Path | None = None,
              head: str = HEAD):
        return kit.build_bundle(
            head, str(target or self.out), root=kit.ROOT,
            runner=runner, pio=str(self.pio), producer=str(self.producer))

    def test_plan_does_not_execute_commands_or_contact_devices(self):
        with patch("knx029_prepare_bringup.subprocess.run",
                   side_effect=AssertionError("No process allowed")):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(kit.main([]), 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["schema"], kit.SCHEMA)
            self.assertFalse(any(payload["release_gates"].values()))
            self.assertEqual(payload["classification"],
                             "NOT_FLASHED_HARDWARE_UNVERIFIED")
            self.assertTrue(any("MOTORS" in v for v in payload["sequence"]))

    def test_bad_sha_rejected_before_git_or_build(self):
        runner = FakeRunner()
        with self.assertRaises(kit.KitError):
            self.build(runner, head="1234")
        self.assertEqual(runner.calls, [])
        self.assertFalse(self.out.exists())

    def test_dirty_git_or_wrong_head_refuses_any_pio(self):
        for runner in (FakeRunner(dirty=True), FakeRunner(head=OTHER_HEAD)):
            with self.assertRaises(kit.KitError):
                self.build(runner)
            self.assertFalse(any("-e" in c for c in runner.calls))
        self.assertFalse(self.out.exists())

    def test_existing_or_in_repo_output_is_rejected(self):
        self.out.mkdir()
        runner = FakeRunner()
        with self.assertRaises(kit.KitError):
            self.build(runner)
        self.assertFalse(any("-e" in c for c in runner.calls))
        with self.assertRaises(kit.KitError):
            kit.output_path(str(kit.ROOT / "forbidden-kit"), kit.ROOT)

    def test_valid_build_only_two_targets_no_updi_actions(self):
        runner = FakeRunner()
        actual = self.build(runner)
        self.assertEqual(actual, self.out)
        self.assertTrue(runner.attiny_config_safe)
        build_steps = [c[-1] for c in runner.calls if "-e" in c]
        self.assertEqual(build_steps, ["controller", "temperature"])
        self.assertEqual(runner.snapshots, 2)
        manifest = json.loads((actual / "bringup-manifest.json").read_text())
        self.assertEqual(manifest["source_git_head"], HEAD)
        self.assertFalse(any(manifest["release_gates"].values()))
        self.assertEqual(set(manifest["firmware_artifacts"]), set(kit.ARTIFACTS))
        sums = (actual / "SHA256SUMS.txt").read_text()
        self.assertEqual(len(sums.splitlines()), 5)
        for name, record in manifest["firmware_artifacts"].items():
            artifact = actual / name
            self.assertEqual(record["sha256"], kit.sha256_file(artifact))
            self.assertEqual(record["size_bytes"], artifact.stat().st_size)
            self.assertIn(name, sums)
        self.assertFalse((kit.ROOT / "candidate-1").exists())

    def test_missing_hex_fails_without_published_bundle(self):
        runner = FakeRunner(missing_hex=True)
        with self.assertRaises(kit.KitError):
            self.build(runner)
        self.assertFalse(self.out.exists())

    def test_failed_build_fails_without_published_bundle(self):
        runner = FakeRunner(fail_target="temperature")
        with self.assertRaises(kit.usb.FlashError):
            self.build(runner)
        self.assertFalse(self.out.exists())

    def test_source_changes_during_build_fail_closed(self):
        runner = FakeRunner(change_head_midbuild=True)
        with self.assertRaises(kit.KitError):
            self.build(runner)
        self.assertEqual(runner.snapshots, 2)
        self.assertFalse(self.out.exists())

    def test_verify_checks_manifest_sizes_and_hashes_readonly(self):
        self.build(FakeRunner())
        with patch("knx029_prepare_bringup.subprocess.run",
                   side_effect=AssertionError("Verification must be offline")):
            result = kit.verify_bundle(str(self.out))
            self.assertEqual(result["artifacts_verified"], 4)
            self.assertEqual(result["checksum_records"], 5)
            self.assertTrue(result["release_gates_all_blocked"])
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(kit.main(
                    ["verify", "--kit", str(self.out)]), 0)
            self.assertFalse(json.loads(stdout.getvalue())["hardware_contact"])

    def test_verify_detects_mutated_uf2_or_checksum(self):
        self.build(FakeRunner())
        uf2 = self.out / "controller-rp2040.uf2"
        uf2.write_bytes(uf2.read_bytes() + b"TAMPER")
        with self.assertRaisesRegex(kit.KitError, "SHA256"):
            kit.verify_bundle(str(self.out))

    def test_verify_cannot_promote_any_real_hardware_gate(self):
        self.build(FakeRunner())
        manifest = self.out / "bringup-manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["release_gates"]["motor_enable_authorized"] = True
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(kit.KitError, "hardware release"):
            kit.verify_bundle(str(self.out))

    def test_verify_rejects_missing_files(self):
        self.build(FakeRunner())
        (self.out / "temperature-attiny3216.hex").unlink()
        with self.assertRaisesRegex(kit.KitError, "file list"):
            kit.verify_bundle(str(self.out))

    def test_updi_config_drift_refuses_any_programming(self):
        isolated = self.dir / "single"
        (isolated / "src" / "temperature").mkdir(parents=True)
        base = (kit.ROOT / "src" / "temperature" / "temperature.ini").read_text()
        (isolated / "src" / "temperature" / "temperature.ini").write_text(
            base + "\ncustom_unknown_directive = dangerous\n")
        with self.assertRaises(kit.KitError):
            kit.strip_updi_actions_in_temporary_config(isolated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
