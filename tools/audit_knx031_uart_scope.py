#!/usr/bin/env python3
"""KNX031 scope audit: existing ETS/firmware/PCB/flash tooling frozen."""
from pathlib import Path
import ast
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "688e7ce"
FROZEN = (
    "lib/common/temperature_protocol.hpp",
    "lib/common/temperature_client_core.hpp",
    "lib/common/temperature_telemetry_policy.hpp",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "src/controller/controller.ini",
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "tools/usb_flash_controller.py",
    "tools/knx029_prepare_bringup.py",
    "tools/knx030_passive_inventory.py",
)


def check(test: bool, message: str) -> None:
    assert test, message
    print("PASS", message)


def base_file(name: str) -> bytes:
    result = subprocess.run([
        "git", "-c", "safe.directory=" + ROOT.resolve().as_posix(),
        "-C", str(ROOT), "show", BASE + ":" + name],
        check=False, capture_output=True)
    if result.returncode:
        raise RuntimeError("Cannot inspect historical source " + name)
    return result.stdout.replace(b"\r\n", b"\n")


def main() -> None:
    for name in FROZEN:
        current = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        check(current == base_file(name), "immutable source: " + name)
    python_file = ROOT / "tools/knx031_uart_trace.py"
    py = python_file.read_text(encoding="utf-8-sig")
    ast_tree = ast.parse(py)
    allowed_imports = {
        "__future__", "argparse", "binascii", "hashlib", "json",
        "pathlib", "re", "struct", "sys", "typing"
    }
    imported: set[str] = set()
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    check(imported <= allowed_imports, "Python strictly standard-library, no serial/network/process imports")
    check("read_bytes()" in py and "Path(" in py,
          "source reads existing local byte file")
    for forbidden in ("socket.socket(", "serial.Serial(", "subprocess.run(",
                      "os.system(", ".write_bytes(", ".write_text(",
                      "picotool ", "pymcuprog ", "knx.write(", "digitalWrite("):
        # Comments/docstrings may describe forbidden operations, but the
        # tool implementation MUST NOT be able to execute them.
        active = "\n".join(x for x in py.splitlines() if
                           not x.lstrip().startswith("#"))
        check(forbidden not in active, "no active device/file-write action " + forbidden)
    for wanted in (
        "def crc16_ccitt_false(", "def decode_snapshot(", "class Scanner:",
        "def read_trace(", "def plan(", "def inspect(",
        '"physical_measurement_verified": False',
        '"no_device_or_knx_access": True',
        '"motor_enable_authorized": False',
        '"no_telemetry_liveness_claim": True',
        "PAYLOAD_BYTES = 59", "MAX_FRAME_BYTES = 67",
        "trace must be",
    ):
        if wanted == "trace must be":
            continue
        check(wanted in py, "KNX014 diagnosis contract " + wanted)
    cpp = (ROOT / "tests/native/knx031_uart_vector_oracle.cpp").read_text(
        encoding="utf-8-sig")
    check('#include "../../lib/common/temperature_protocol.hpp"' in cpp,
          "C++ test vectors from production protocol")
    for forbidden in ("Arduino.h", "Serial.begin", "knx.", "digitalWrite",
                      "pymcuprog", "picotool"):
        check(forbidden not in cpp, "C++ oracle has no hardware path: " + forbidden)
    tests = (ROOT / "tools/test_knx031_uart_trace.py").read_text(
        encoding="utf-8-sig")
    for required in ("reference_vectors()", "test_native_golden_request",
                     "test_native_golden_snapshot_all_nine_channels",
                     "test_corruption_crc_and_recovery",
                     "test_reject_semantics_even_when_crc_is_correct",
                     "test_default_plan_never_opens_file_or_serial"):
        check(required in tests, "native/error/IO tests exist " + required)
    print("KNX031 PASS: offline UART-only inspector; all prior firmware/product/hardware frozen.")
    print("Physical RP2040, ATtiny, KNX, ETS, motor and power gates remain open.")


if __name__ == "__main__":
    main()
