#!/usr/bin/env python3
"""KNX027 offline USB/upload safety tests. ALL hardware/tool calls mocked."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import usb_flash_controller as flash


FAKE_PORTS = [
    {"port": "COM3", "description": "Intel AMT", "hwid": "PCI\\VEN_8086"},
    {"port": "COM5", "description": "USB CDC",
     "hwid": "USB VID:PID=2E8A:00C0 SER=F1 LOCATION=1-1"},
    {"port": "COM6", "description": "USB CDC",
     "hwid": "USB\\VID_2E8A&PID_00C0\\ABCDE"},
]


class USBFlashTests(unittest.TestCase):
    def test_port_parser_and_exact_selection(self):
        self.assertEqual(flash.hwid_vidpid(FAKE_PORTS[1]["hwid"]),
                         "2E8A:00C0")
        self.assertEqual(flash.hwid_vidpid(FAKE_PORTS[2]["hwid"]),
                         "2E8A:00C0")
        self.assertEqual(flash.choose_port(FAKE_PORTS, "com5", "2e8a:00c0")["port"],
                         "COM5")
        self.assertIsNone(flash.hwid_vidpid(FAKE_PORTS[0]["hwid"]))
        for port, id_string in (
            ("COM3", "2E8A:00C0"),
            ("COM5", "ABCD:1234"),
            ("COM1", "2E8A:00C0"),
            ("COM5", "2E8A:XYZ0"),
            ("\\x5c\\x5c.\\COM5", "2E8A:00C0"),
        ):
            with self.subTest(port=port, id_string=id_string):
                with self.assertRaises(flash.FlashError):
                    flash.choose_port(FAKE_PORTS, port, id_string)
        with self.assertRaises(flash.FlashError):
            flash.choose_port(FAKE_PORTS + [FAKE_PORTS[1]], "COM5", "2E8A:00C0")

    def test_upload_requires_all_flags_before_subprocess(self):
        attempts = [
            ["upload"],
            ["upload", "--port", "COM5"],
            ["upload", "--port", "COM5", "--expect-vidpid", "2E8A:00C0"],
            ["upload", "--port", "COM5", "--execute", "--confirm-safe-bench"],
            ["upload", "--port", "COM5", "--expect-vidpid", "2E8A:00C0",
             "--execute", "--confirm-safe-bench"],
            ["upload", "--port", "COM5", "--expect-vidpid", "2E8A:00C0",
             "--execute", "--confirm-safe-bench", "--expected-head", "a" * 7],
        ]
        with mock.patch.object(flash, "tool_path", side_effect=AssertionError(
                "probe/build must never happen before consent")):
            for args in attempts:
                with self.subTest(args=args), mock.patch("sys.stderr"):
                    self.assertEqual(flash.main(args), 2)

    def test_plan_never_inspects_usb_or_builds(self):
        with mock.patch.object(flash, "tool_path",
                               side_effect=AssertionError("no side effects")):
            self.assertEqual(flash.main(
                ["plan", "--port", "com5", "--expect-vidpid", "2E8A:00C0"]), 0)

    def test_mismatch_blocks_before_build(self):
        args = [
            "upload", "--port", "COM3", "--expect-vidpid", "2E8A:00C0",
            "--expected-head", "a" * 40, "--execute", "--confirm-safe-bench",
        ]
        with (mock.patch.object(flash, "verify_clean_head",
                                return_value="a" * 40),
              mock.patch.object(flash, "tool_path", side_effect=lambda x: x),
              mock.patch.object(flash, "discover_ports", return_value=FAKE_PORTS),
              mock.patch.object(flash, "build_isolated",
                                side_effect=AssertionError("must never build")),
              mock.patch("sys.stderr")):
            self.assertEqual(flash.main(args), 2)

    def test_probe_read_only_port_inventory(self):
        commands = []

        def fake(command, **kwargs):
            commands.append(command)
            return subprocess.CompletedProcess(command, 0,
                                               stdout=__import__("json").dumps(FAKE_PORTS),
                                               stderr="")

        self.assertEqual(flash.discover_ports("pio", runner=fake), FAKE_PORTS)
        self.assertEqual(commands, [["pio", "device", "list", "--json-output"]])
        with mock.patch.object(flash, "tool_path", return_value="pio"), \
             mock.patch.object(flash, "discover_ports", return_value=FAKE_PORTS):
            self.assertEqual(flash.main(["probe"]), 0)

    def test_git_shield(self):
        def ok(command, **kwargs):
            return subprocess.CompletedProcess(
                command, 0,
                stdout=("a" * 40 + "\n") if "rev-parse" in command else "")
        self.assertEqual(flash.verify_clean_head("a" * 40, runner=ok), "a" * 40)
        with self.assertRaises(flash.FlashError):
            flash.verify_clean_head("b" * 40, runner=ok)
        def dirty(command, **kwargs):
            return subprocess.CompletedProcess(
                command, 0,
                stdout=("a" * 40 + "\n") if "rev-parse" in command else
                       " M src/controller/main.cpp\n")
        with self.assertRaises(flash.FlashError):
            flash.verify_clean_head("a" * 40, runner=dirty)

    def test_isolated_copy_and_firmware_artifacts(self):
        with tempfile.TemporaryDirectory() as outer:
            base = Path(outer)
            canonical = base / "canonical"
            scratch = base / "isolated"
            scratch.mkdir()
            for folder in ("src/controller", "lib/common", "include", "assets"):
                (canonical / folder).mkdir(parents=True)
            (canonical / "platformio.ini").write_text("[platformio]\n")
            (canonical / "src/controller/controller.ini").write_text(
                "[env:controller]\nupload_protocol = picotool\n")
            (canonical / "lib/common/dummy.hpp").write_text("unchanged\n")
            (canonical / "include/knxprod.hpp").write_text("original-header\n")
            for name in flash.COPY_ASSETS:
                (canonical / "assets" / name).write_text("asset\n")
            calls = []
            def fake_build(command, **kwargs):
                calls.append(command)
                isolated = Path(kwargs["cwd"])
                (isolated / "include" / "knxprod.hpp").write_text("generated\n")
                target = isolated / ".pio/build/controller"
                target.mkdir(parents=True)
                (target / "firmware.elf").write_bytes(b"elf\n")
                (target / "firmware.uf2").write_bytes(b"uf2\n")
                return subprocess.CompletedProcess(command, 0)
            elf, uf2 = flash.build_isolated("pio", "producer", scratch,
                                            root=canonical, runner=fake_build)
            self.assertTrue(elf.is_file())
            self.assertEqual(uf2.read_bytes(), b"uf2\n")
            self.assertEqual(
                (canonical / "include/knxprod.hpp").read_text(),
                "original-header\n")
            self.assertEqual(calls[0][:4], ["pio", "run", "-e", "controller"])
            recovery = base / "recovery.uf2"
            self.assertEqual(flash.save_uf2(uf2, str(recovery)), recovery)
            self.assertEqual(recovery.read_bytes(), b"uf2\n")
            with self.assertRaises(FileExistsError):
                flash.save_uf2(uf2, str(recovery))

    def test_mocked_happy_path_upload_runs_once(self):
        observed = []
        def fake_build(pio, producer, dst):
            target = Path(dst) / ".pio/build/controller"
            target.mkdir(parents=True)
            elf, uf2 = target / "firmware.elf", target / "firmware.uf2"
            elf.write_bytes(b"fake-elf")
            uf2.write_bytes(b"fake-uf2")
            return elf, uf2
        def fake_run(command, **kwargs):
            observed.append(command)
            return subprocess.CompletedProcess(command, 0)
        cmd = [
            "upload", "--port", "COM5", "--expect-vidpid", "2E8A:00C0",
            "--expected-head", "a" * 40, "--execute", "--confirm-safe-bench",
        ]
        with (mock.patch.object(flash, "verify_clean_head", return_value="a"*40),
              mock.patch.object(flash, "tool_path", side_effect=lambda kind: kind),
              mock.patch.object(flash, "discover_ports", return_value=FAKE_PORTS),
              mock.patch.object(flash, "build_isolated", side_effect=fake_build),
              mock.patch.object(flash, "run_checked", side_effect=fake_run)):
            self.assertEqual(flash.main(cmd), 0)
        self.assertEqual(observed, [[
            "pio", "run", "-e", "controller", "-t", "upload",
            "--upload-port", "COM5",
        ]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
