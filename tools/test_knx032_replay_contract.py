#!/usr/bin/env python3
"""KNX032 contract tests; always software-only, no USB, KNX or GPIO."""
from __future__ import annotations
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import knx031_uart_trace as trace
import test_knx032_uart_to_knx as replay
from test_knx031_uart_trace import reference_vectors


class ReplayContractTests(unittest.TestCase):
    def test_plan_no_subprocess_or_file_interaction(self):
        with patch("test_knx032_uart_to_knx.subprocess.run",
                   side_effect=AssertionError("Offline plan ran native tool")):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(replay.main(["plan"]), 0)
            doc = json.loads(out.getvalue())
            self.assertTrue(doc["source_firmware_mutated"] is False)
            self.assertEqual(doc["max_real_device_access"], 0)
            self.assertFalse(doc["motor_enable_authorized"])

    def test_empty_or_wrong_sequence_rejected(self):
        header = bytes([1, 1, 2, 0])
        crc = trace.crc16_ccitt_false(header).to_bytes(2, "little")
        get = trace.SYNC + header + crc
        with self.assertRaises(replay.OfflineTestError):
            replay.preflight(get)
        _, snapshot = reference_vectors()
        with self.assertRaises(replay.OfflineTestError):
            replay.preflight(get + snapshot)

    def test_semantic_invalid_flag_rejected_even_with_good_crc(self):
        req, packet = reference_vectors()
        resp = bytearray(packet)
        resp[6 + 5 + 4] = 0x02
        resp[-2:] = trace.crc16_ccitt_false(bytes(resp[2:-2])).to_bytes(
            2, "little")
        with self.assertRaises(replay.OfflineTestError):
            replay.preflight(req + bytes(resp))

    def test_crc_mutation_rejected_before_native_test(self):
        req, packet = reference_vectors()
        broken = bytearray(packet)
        broken[-10] ^= 0x01
        with self.assertRaises(replay.OfflineTestError):
            replay.preflight(req + bytes(broken))

    def test_native_good_path_and_adversarial_variants(self):
        value = replay.exercise()
        self.assertEqual(value["status"], "PASS")
        self.assertEqual(value["sample_snapshot_channels"], 9)
        self.assertEqual(value["sample_crc_good_frames"], 2)
        self.assertEqual(value["negative_trace_cases"], 4)
        self.assertTrue(value["physical_release_gates_all_blocked"])
        self.assertTrue(value["no_real_serial_or_knx_bus"])
        self.assertEqual(len(value["native_stdout"]), 3)

    def test_explicit_saved_hex_replay_from_real_cpp_oracle(self):
        req, reply = reference_vectors()
        with tempfile.TemporaryDirectory(prefix="knx032-contract-") as d:
            path = Path(d) / "mock.hex"
            path.write_text(
                "00 FF " + (req + reply).hex(" ").upper(), encoding="ascii")
            obj = replay.exercise(supplied=str(path), file_format="hex")
        self.assertEqual(obj["status"], "PASS")
        self.assertEqual(obj["negative_trace_cases"], 0)
        self.assertIn("explicit saved file", obj["source_kind"])

    def test_missing_cxx_fails_without_automatic_fallback(self):
        with patch.dict(os.environ, {"CXX": r"Z:\nonexistent\g++.exe"}):
            with self.assertRaises(replay.OfflineTestError):
                replay.compiler()

    def test_wrong_saved_filename_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="knx032-contract-") as d:
            path = Path(d) / "COM1.txt"
            path.write_text("A5 5A", encoding="ascii")
            with self.assertRaises(trace.TraceError):
                replay.exercise(supplied=str(path), file_format="hex")


if __name__ == "__main__":
    unittest.main(verbosity=2)
