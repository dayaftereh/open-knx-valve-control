#!/usr/bin/env python3
"""KNX032: native-only UART payload replay through actual controller C++ modules.

NO Arduino firmware modifications. NO connected hardware, COM/USB/UPDI/KNX
access, ETS6 or motor command. Default command is 'test' using C++ KNX031
golden frames generated from the *current source*. Optionally --trace accepts
one saved, explicitly provided, locally stored KNX014 byte stream. The host
re-encodes a correctly CRC-checked recorded SNAPSHOT payload with the fresh
simulated RP2040 request sequence; it is NOT a literal on-wire replay.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import knx031_uart_trace as trace

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GPP = Path(
    r"C:\_myspace\Tools\winlibs-gcc-16.2.0-ucrt\mingw64\bin\g++.exe"
)
ORACLE = ROOT / "tests/native/knx031_uart_vector_oracle.cpp"
NATIVE = ROOT / "tests/native/test_knx032_uart_to_knx.cpp"
SOURCES = (
    ROOT / "src/controller/temperature_bridge.cpp",
    ROOT / "src/controller/temperature_publisher.cpp",
)


class OfflineTestError(RuntimeError):
    pass


def plan() -> dict[str, Any]:
    return {
        "gate": "OFFLINE_ONLY_NOT_HARDWARE_TESTED",
        "operation": "compile current KNX014 C++ codec and actual RP2040 bridge/publisher into native WinLibs test process",
        "source": "saved local KNX014 two-frame bytes or generated native C++ golden vector",
        "expected_ko": "KO25..33 DPT9.001, KO34 DPT1.002, KO35 DPT7.001",
        "max_real_device_access": 0,
        "serial_or_updi_opened": False,
        "knx_or_ets_bus_traffic": False,
        "motor_enable_authorized": False,
        "source_firmware_mutated": False,
        "recorded_response_sequence_reframed_for_simulated_request": True,
        "physical_gate_status": "BLOCKED",
    }


def compiler() -> str:
    configured = os.environ.get("CXX", "")
    if configured:
        chosen = shutil.which(configured)
        if not chosen and Path(configured).is_file():
            chosen = configured
        if not chosen:
            raise OfflineTestError("CXX was specified but is unavailable")
    elif DEFAULT_GPP.is_file():
        chosen = str(DEFAULT_GPP)
    else:
        chosen = shutil.which("g++")
    if not chosen or not Path(chosen).is_file():
        raise OfflineTestError("Native g++ missing; do not fall back to device builds")
    return str(Path(chosen).resolve())


def checked_run(args: list[str], directory: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    output = subprocess.run(
        args, cwd=directory, env=env, capture_output=True, text=True,
        check=False, timeout=90)
    if output.returncode != 0:
        raise OfflineTestError(
            "Native code compile / test failed:\n" + (
                output.stdout + "\n" + output.stderr)[-2400:])
    return output


def read_vectors(stdout: str) -> tuple[bytes, bytes]:
    vectors: dict[str, bytes] = {}
    for line in stdout.splitlines():
        kind, sep, content = line.partition(" ")
        if sep != " " or kind in vectors or kind not in ("REQUEST", "SNAPSHOT"):
            raise OfflineTestError("Unexpected native C++ KNX031 oracle output")
        try:
            vectors[kind] = bytes.fromhex(content)
        except ValueError as exc:
            raise OfflineTestError("Malformed native oracle HEX bytes") from exc
    if set(vectors) != {"REQUEST", "SNAPSHOT"}:
        raise OfflineTestError("Incomplete C++ KNX014 oracle output")
    request, response = vectors["REQUEST"], vectors["SNAPSHOT"]
    if (request.hex().upper() != "A55A010137004659" or
            len(response) != trace.MAX_FRAME_BYTES or
            not response.startswith(b"\xA5\x5A\x01\x81\x37\x3B")):
        raise OfflineTestError("Native KNX014 reference protocol drift")
    return request, response


def preflight(saved_bytes: bytes) -> dict[str, Any]:
    report = trace.inspect(saved_bytes, 5)
    stats = report["stats"]
    valid_pair = (
        stats["good_crc_frames"] == 2 and
        stats["get_snapshot_requests"] == 1 and
        stats["snapshot_valid"] == 1 and
        stats["bad_crc_frames"] == 0 and
        stats["invalid_header"] == 0 and
        stats["snapshot_payload_rejected"] == 0 and
        stats["unpaired_response_sequences"] == 0 and
        stats["unknown_frame_type"] == 0 and
        stats["malformed_requests"] == 0 and
        report["truncated_tail_bytes"] == 0 and
        len(report["records"]) == 2 and
        report["records"][0]["status"] == "request_observed" and
        report["records"][1]["status"] == "snapshot_decoded" and
        report["records"][0]["sequence"] ==
        report["records"][1]["sequence"]
    )
    if not valid_pair:
        raise OfflineTestError(
            "Input must contain one valid GET followed by one CRC and flag-valid SNAPSHOT"
        )
    return report


def expect_rejection(executable: Path, path: Path, data: bytes,
                     env: dict[str, str]) -> None:
    path.write_bytes(data)
    response = subprocess.run(
        [str(executable), str(path)], cwd=str(ROOT), env=env,
        capture_output=True, text=True, check=False, timeout=20)
    if response.returncode == 0:
        raise OfflineTestError(
            "Fail-closed regression: native mock accepted a tampered trace")


def exercise(*, supplied: str | None = None,
             file_format: str = "binary") -> dict[str, Any]:
    cxx = compiler()
    env = os.environ.copy()
    env["PATH"] = str(Path(cxx).parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="knx032-native-host-") as d:
        temp = Path(d)
        oracle = temp / "knx031-oracle.exe"
        harness = temp / "knx032-replay.exe"
        common = [cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                  "-pedantic"]
        checked_run(common + ["-o", str(oracle), str(ORACLE)], ROOT, env)
        oracle_output = checked_run([str(oracle)], ROOT, env)
        request, response = read_vectors(oracle_output.stdout)

        checked_run(
            common + [
                "-I", str(ROOT / "tests/native/mocks"),
                "-I", str(ROOT / "lib/common"),
                "-I", str(ROOT / "src/controller"),
                "-o", str(harness), str(NATIVE),
                *(str(p) for p in SOURCES)
            ], ROOT, env)

        if supplied:
            raw = trace.read_trace(supplied, file_format)
            origin = "explicit saved file (no live serial access)"
        else:
            raw = b"\x00\xFF" + request + response
            origin = "C++ source-derived synthetic golden pair"
        report = preflight(raw)
        good = temp / "good-captured-bytes.bin"
        good.write_bytes(raw)
        accepted = checked_run([str(harness), str(good)], ROOT, env)

        if not supplied:
            # CRC corruption: a real CRC error cannot be treated as telemetry.
            flip = bytearray(raw)
            flip[-20] ^= 0x80
            expect_rejection(harness, temp / "bad-crc.bin", bytes(flip), env)
            # Correct CRC but wrong response sequence cannot pair with GET.
            flip = bytearray(raw)
            response_start = raw.find(b"\xA5\x5A\x01\x81")
            if response_start < 0:
                raise OfflineTestError("No SNAPSHOT start in native golden")
            flip[response_start + 4] ^= 0x01
            crc = trace.crc16_ccitt_false(
                bytes(flip[response_start + 2:-2]))
            flip[-2:] = crc.to_bytes(2, "little")
            expect_rejection(harness, temp / "wrong-seq.bin", bytes(flip), env)
            # Semantic flag fault despite valid CRC.
            flip = bytearray(raw)
            flip[response_start + 6 + 5 + 4] = 0x02
            crc = trace.crc16_ccitt_false(
                bytes(flip[response_start + 2:-2]))
            flip[-2:] = crc.to_bytes(2, "little")
            expect_rejection(harness, temp / "bad-quality.bin", bytes(flip), env)
            expect_rejection(harness, temp / "truncated.bin", raw[:-9], env)

        return {
            "status": "PASS",
            "source_kind": origin,
            "sample_bytes": len(raw),
            "sample_crc_good_frames": report["stats"]["good_crc_frames"],
            "sample_snapshot_channels": len(
                report["records"][1]["snapshot"]["channels"]),
            "source_native_protocol": "production temperature_protocol.hpp",
            "runtime_test": "real TemperatureBridge and TemperaturePublisher plus in-memory KNXMock",
            "native_stdout": accepted.stdout.strip().splitlines(),
            "negative_trace_cases": (4 if not supplied else 0),
            "no_real_serial_or_knx_bus": True,
            "source_firmware_mutated": False,
            "physical_release_gates_all_blocked": True,
        }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan", "test"), nargs="?", default="plan")
    p.add_argument("--trace", help="explicitly saved local UART frame stream only")
    p.add_argument("--format", choices=("binary", "hex"), default="binary")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "plan":
            payload = plan()
        else:
            payload = exercise(supplied=args.trace, file_format=args.format)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OfflineTestError, trace.TraceError, OSError,
            subprocess.TimeoutExpired) as exc:
        print("KNX032 OFFLINE TEST BLOCKED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
