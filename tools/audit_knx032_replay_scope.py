#!/usr/bin/env python3
"""KNX032: narrow frozen-source + native-only replay scope audit."""
from pathlib import Path
import ast
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "e0efd61"
FROZEN = (
    "platformio.ini",
    "src/controller/controller.ini",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_bridge.hpp",
    "src/controller/temperature_publisher.cpp",
    "src/controller/temperature_publisher.hpp",
    "src/temperature/temperature.ini",
    "src/temperature/main.cpp",
    "lib/common/temperature_protocol.hpp",
    "lib/common/temperature_client_core.hpp",
    "lib/common/temperature_telemetry_policy.hpp",
    "include/knxprod.hpp",
    "assets/open-knx-valve-control.xml",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "tests/native/mocks/Arduino.h",
    "tests/native/mocks/knx.h",
    "tools/usb_flash_controller.py",
    "tools/knx029_prepare_bringup.py",
    "tools/knx030_passive_inventory.py",
    "tools/knx031_uart_trace.py",
    "tests/native/knx031_uart_vector_oracle.cpp",
)


def check(value: bool, message: str) -> None:
    assert value, message
    print("PASS:", message)


def get_prior(filename: str) -> bytes:
    p = subprocess.run(
        ["git", "-c", "safe.directory=" + ROOT.resolve().as_posix(),
         "-C", str(ROOT), "show", f"{BASE}:{filename}"],
        capture_output=True, check=False)
    if p.returncode:
        raise RuntimeError("Missing immutable baseline file: " + filename)
    return p.stdout.replace(b"\r\n", b"\n")


def run() -> None:
    for filename in FROZEN:
        actual = (ROOT / filename).read_bytes().replace(b"\r\n", b"\n")
        check(actual == get_prior(filename), "frozen: " + filename)
    cpp = (ROOT / "tests/native/test_knx032_uart_to_knx.cpp").read_text(
        encoding="utf-8-sig")
    for token in (
        '"../../src/controller/temperature_bridge.hpp"',
        '"../../src/controller/temperature_publisher.hpp"',
        "<temperature_protocol.hpp>", "<knx.h>",
        "TemperatureBridge bridge;", "TemperaturePublisher publisher;",
        "P::Parser parser;", "P::decodeSnapshot(frame, decoded)",
        "P::encodeFrame(", "uart.inject(", "getGroupObject",
    ):
        if token == "getGroupObject":
            # Production publisher is linked, not textually included.
            check("checkDpt(" in cpp, "native mock checks actual KO DPT")
        else:
            check(token in cpp, "production C++ integration " + token)
    for token in ("Serial.begin(", "SerialUSB", "digitalWrite(",
                  "pinMode(", "analogWrite(", "knx.loop(",
                  "knx.write(", "picotool", "pymcuprog", "OpenSerial"):
        check(token not in cpp, "native mock does not touch hardware " + token)

    runner = (ROOT / "tools/test_knx032_uart_to_knx.py").read_text(
        encoding="utf-8-sig")
    ast.parse(runner)
    check("knx031_uart_trace as trace" in runner,
          "source-bounded offline saved file validator")
    check('"-std=c++17"' in runner and '"-Werror"' in runner,
          "native host C++17 compilation with warnings as errors")
    check('"-I", str(ROOT / "tests/native/mocks")' in runner,
          "production C++ links only to in-memory serial/KNX mocks")
    check('"physical_release_gates_all_blocked": True' in runner,
          "no physical GO claimed by test tool")
    for forbid in ("socket.socket(", "serial.Serial(", "digitalWrite(",
                   "os.system(", "pymcuprog write", "picotool load",
                   "knx.write("):
        check(forbid not in runner, "no device/bus action " + forbid)

    contract = (ROOT / "tools/test_knx032_replay_contract.py").read_text(
        encoding="utf-8-sig")
    ast.parse(contract)
    for item in (
        "test_native_good_path_and_adversarial_variants",
        "test_explicit_saved_hex_replay_from_real_cpp_oracle",
        "test_semantic_invalid_flag_rejected_even_with_good_crc",
        "test_plan_no_subprocess_or_file_interaction",
        "test_wrong_saved_filename_fails_closed",
    ):
        check(item in contract, "independent replay contract test " + item)
    print("KNX032 Scope PASS: product/firmware/ETS/motor/PCB/upload untouched.")
    print("KNX002-006/018 hardware and KNX009/016 ETS tests remain blocked/deferred.")


if __name__ == "__main__":
    run()
