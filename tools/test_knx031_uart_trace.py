#!/usr/bin/env python3
"""KNX031 native codec cross-check and offline UART-parser regression tests."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import knx031_uart_trace as trace

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "tests/native/knx031_uart_vector_oracle.cpp"
LOCAL_GPP = Path(
    r"C:\_myspace\Tools\winlibs-gcc-16.2.0-ucrt\mingw64\bin\g++.exe"
)


def reference_vectors() -> tuple[bytes, bytes]:
    """Compile the existing project's native C++ codec into a temporary dir."""
    compiler = os.environ.get("CXX") or (
        str(LOCAL_GPP) if LOCAL_GPP.is_file() else shutil.which("g++")
    )
    if not compiler:
        raise RuntimeError("No native host g++ installed: KNX031 codec oracle required")
    compiler = str(Path(compiler).resolve())
    with tempfile.TemporaryDirectory(prefix="knx031-native-oracle-") as tmp:
        output = Path(tmp) / "oracle.exe"
        env = os.environ.copy()
        env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get(
            "PATH", "")
        cmd = [
            compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-pedantic", "-o", str(output), str(ORACLE)
        ]
        build = subprocess.run(
            cmd, cwd=ROOT, env=env, capture_output=True, text=True,
            check=False)
        if build.returncode:
            raise RuntimeError("Native C++ golden oracle build failed:\n" +
                               build.stderr[-2000:])
        run = subprocess.run(
            [str(output)], cwd=tmp, env=env, capture_output=True,
            text=True, check=False)
        if run.returncode:
            raise RuntimeError("Native C++ golden oracle failed:\n" +
                               run.stderr[-2000:])
        vectors = {}
        for line in run.stdout.splitlines():
            kind, sep, hex_str = line.partition(" ")
            if sep != " " or kind in vectors:
                raise RuntimeError("Unexpected C++ golden vector output")
            vectors[kind] = bytes.fromhex(hex_str)
        if set(vectors) != {"REQUEST", "SNAPSHOT"}:
            raise RuntimeError("Missing native vectors")
        return vectors["REQUEST"], vectors["SNAPSHOT"]


def framed(kind: int, seq: int, payload: bytes = b"",
           version: int = 1) -> bytes:
    header = bytes((version, kind, seq, len(payload))) + payload
    crc = trace.crc16_ccitt_false(header)
    return trace.SYNC + header + crc.to_bytes(2, "little")


class UARTTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request, cls.response = reference_vectors()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="knx031-trace-tests-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_default_plan_never_opens_file_or_serial(self):
        with patch("knx031_uart_trace.Path.read_bytes",
                   side_effect=AssertionError("plan read bytes")):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(trace.main([]), 0)
            result = json.loads(output.getvalue())
            self.assertTrue(result["no_serial_or_knx_io"])
            self.assertTrue(result["no_telemetry_liveness_claim"])
            self.assertTrue(result["no_motor_authority"])

    def test_native_golden_request(self):
        self.assertEqual(self.request.hex().upper(),
                         "A55A010137004659")
        self.assertEqual(len(self.request), 8)
        self.assertEqual(trace.crc16_ccitt_false(self.request[2:-2]),
                         int.from_bytes(self.request[-2:], "little"))
        result = trace.inspect(self.request)
        self.assertEqual(result["stats"]["get_snapshot_requests"], 1)
        self.assertEqual(result["stats"]["snapshot_valid"], 0)

    def test_native_golden_snapshot_all_nine_channels(self):
        self.assertEqual(len(self.response), trace.MAX_FRAME_BYTES)
        result = trace.inspect(self.response)
        self.assertEqual(result["stats"]["snapshot_valid"], 1)
        self.assertEqual(result["stats"]["unpaired_response_sequences"], 1)
        entry = result["records"][0]
        self.assertEqual(entry["status"], "snapshot_decoded")
        self.assertEqual(entry["sequence"], 0x37)
        data = entry["snapshot"]
        self.assertEqual(data["uptime_ms"], 0x12345678)
        self.assertEqual(len(data["channels"]), 9)
        self.assertEqual(data["channels"][0]["reported_celsius_if_valid"], 0.0)
        self.assertEqual(data["channels"][0]["role"], "Vorlauf")
        self.assertEqual(data["channels"][1]["reported_celsius_if_valid"], -10.5)
        self.assertEqual(data["channels"][8]["role"], "Ruecklauf M8")
        missing = data["channels"][5]
        self.assertEqual(missing["fault_name"], "NoSensor")
        self.assertIsNone(missing["reported_age_seconds"])
        self.assertIsNone(missing["reported_celsius_if_valid"])
        self.assertFalse(missing["physical_measurement_verified"])
        self.assertEqual(data["channels"][6]["fault_name"], "ReadFailed")

    def test_mixed_stream_noise_request_response(self):
        data = b"\x00\xFF\xA5\xA5\x5A" + self.request[2:] + self.response
        result = trace.inspect(data)
        self.assertEqual(result["stats"]["good_crc_frames"], 2)
        self.assertEqual(result["stats"]["snapshot_valid"], 1)
        self.assertEqual(result["stats"]["get_snapshot_requests"], 1)
        self.assertFalse(result["records"][-1]["status"] == "crc_rejected")
        self.assertTrue(result["records"][-1]["prior_same_sequence_request_seen"])
        self.assertEqual(result["stats"]["unpaired_response_sequences"], 0)
        self.assertEqual(result["truncated_tail_bytes"], 0)

    def test_corruption_crc_and_recovery(self):
        wrong = bytearray(self.response)
        wrong[13] ^= 0x80
        raw = bytes(wrong) + self.response
        result = trace.inspect(raw)
        self.assertEqual(result["stats"]["bad_crc_frames"], 1)
        self.assertEqual(result["stats"]["snapshot_valid"], 1)
        self.assertEqual(result["records"][0]["status"], "crc_rejected")

    def test_reject_header_version_and_payload_excess(self):
        bad_version = framed(0x01, 7, version=2)
        # Unsupported length is rejected at 4-byte header, before CRC.
        bad_length = b"\xA5\x5A\x01\x81\x01\xFF"
        result = trace.inspect(bad_version + bad_length + self.request)
        self.assertEqual(result["stats"]["invalid_header"], 2)
        self.assertEqual(result["stats"]["get_snapshot_requests"], 1)
        self.assertEqual(result["stats"]["good_crc_frames"], 1)

    def test_reject_semantics_even_when_crc_is_correct(self):
        payload = bytearray(self.response[6:-2])
        # A channel falsely reports Valid without HasSample.
        payload[5 + 4] = 0x02
        rejected = framed(trace.SNAPSHOT_RESPONSE, 55, bytes(payload))
        result = trace.inspect(rejected)
        self.assertEqual(result["stats"]["bad_crc_frames"], 0)
        self.assertEqual(result["stats"]["snapshot_payload_rejected"], 1)
        self.assertEqual(result["stats"]["snapshot_valid"], 0)
        # A reserved module status must always be zero.
        payload = bytearray(self.response[6:-2])
        payload[4] = 1
        self.assertEqual(
            trace.inspect(framed(0x81, 20, bytes(payload)))
            ["stats"]["snapshot_payload_rejected"], 1)

    def test_age_fault_and_flag_range_validation(self):
        payload = bytearray(self.response[6:-2])
        payload[5 + 2:5 + 4] = b"\x00\x00"
        payload[5 + 4] = 0x00
        self.assertEqual(
            trace.inspect(framed(0x81, 9, payload))
            ["stats"]["snapshot_payload_rejected"], 1)
        payload[5 + 4] = 0x20
        self.assertEqual(
            trace.inspect(framed(0x81, 9, payload))
            ["stats"]["snapshot_payload_rejected"], 1)
        payload[5 + 4] = 0x01
        payload[5 + 5] = 9
        self.assertEqual(
            trace.inspect(framed(0x81, 9, payload))
            ["stats"]["snapshot_payload_rejected"], 1)

    def test_partial_and_unknown_types(self):
        partial = self.response[:10]
        result = trace.inspect(partial)
        self.assertEqual(result["truncated_tail_bytes"], 10)
        self.assertEqual(result["stats"]["snapshot_valid"], 0)
        sample = framed(0x77, 9)
        bad_request = framed(0x01, 9, b"\x00")
        result = trace.inspect(sample + bad_request)
        self.assertEqual(result["stats"]["unknown_frame_type"], 1)
        self.assertEqual(result["stats"]["malformed_requests"], 1)

    def test_sequence_wrap_is_observation_not_client_ack(self):
        before = framed(0x01, 255)
        next_req = framed(0x01, 0)
        response = framed(0x81, 0, self.response[6:-2])
        result = trace.inspect(before + next_req + response)
        self.assertEqual(result["stats"]["get_snapshot_requests"], 2)
        self.assertTrue(result["records"][-1]["prior_same_sequence_request_seen"])
        self.assertIn("400ms request timeout",
                      result["raw_dump_cannot_verify"])

    def test_file_format_binary_and_text(self):
        binary = self.folder / "capture.bin"
        binary.write_bytes(self.request + self.response)
        text_file = self.folder / "capture.hex"
        text_file.write_text("0xA5 0x5A, 01 01 37 00 46 59\n", encoding="ascii")
        self.assertEqual(trace.read_trace(str(binary), "binary"),
                         self.request + self.response)
        self.assertEqual(trace.read_trace(str(text_file), "hex"),
                         self.request)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(trace.main([
                "inspect", "--input", str(text_file), "--format", "hex"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["stats"]
                         ["get_snapshot_requests"], 1)
        self.assertEqual(hashlib.sha256(self.request).hexdigest(),
                         trace.inspect(self.request)["input_sha256"])

    def test_refuse_invalid_paths_size_or_non_hex(self):
        not_file = self.folder / "missing.bin"
        with self.assertRaises(trace.TraceError):
            trace.read_trace(str(not_file), "binary")
        # Do not allow COM or named-pipe device paths.
        with self.assertRaises(trace.TraceError):
            trace.read_trace(r"\\.\COM5", "binary")
        bad = self.folder / "corrupt.hex"
        bad.write_text("A5 5A HELLO", encoding="ascii")
        with self.assertRaises(trace.TraceError):
            trace.read_trace(str(bad), "hex")
        empty = self.folder / "empty.bin"
        empty.write_bytes(b"")
        with self.assertRaises(trace.TraceError):
            trace.read_trace(str(empty), "binary")
        with self.assertRaises(trace.TraceError):
            trace.inspect(self.request, max_records=0)

    def test_compact_command_output_is_safe_for_remote_agent(self):
        trace_file = self.folder / "native-example.hex"
        trace_file.write_text((self.request + self.response).hex(),
                              encoding="ascii")
        output = io.StringIO()
        with redirect_stdout(output):
            exitcode = trace.main([
                "inspect", "--input", str(trace_file),
                "--format", "hex", "--summary-only"])
        self.assertEqual(exitcode, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["records"], [])
        self.assertTrue(report["records_suppressed"])
        self.assertEqual(report["stats"]["good_crc_frames"], 2)
        self.assertLess(len(output.getvalue()), 2500)

    def test_windows_reserved_aliases_never_checked_as_real_files(self):
        for reserved in ("COM1.bin", "LPT9.txt", "NUL.dat", "CON.hex"):
            with self.assertRaisesRegex(trace.TraceError, "reserved device"):
                trace.local_trace_file(reserved, "hex" if reserved.endswith((".txt", ".hex")) else "binary")

    def test_large_stream_records_are_bounded(self):
        raw = self.request * 1200
        result = trace.inspect(raw, max_records=5)
        self.assertEqual(result["stats"]["get_snapshot_requests"], 1200)
        self.assertTrue(result["records_limited"])
        self.assertEqual(len(result["records"]), 5)
        self.assertFalse(any(result["physical_release_gates"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
