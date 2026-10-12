#!/usr/bin/env python3
"""KNX027 scope audit: USB tooling only, no device/ETS/physical motor changes."""
from __future__ import annotations

import ast
import difflib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "8ce8de2"
FROZEN = (
    "platformio.ini",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "assets/open-knx-valve-control.xml",
    "assets/knx008_zone_ets_proposal.json",
    "include/knxprod.hpp",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "lib/common/room_control_runtime.hpp",
    "lib/common/knx025_fault_supervisor.hpp",
    "lib/common/knx026_hmi_diagnostics.hpp",
    "tools/build_controller_isolated.py",
)


def previous(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT
    ).decode("utf-8-sig").replace("\r\n", "\n")


def current(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def check(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError("KNX027 FAIL: " + label)
    print("PASS:", label)


def main() -> int:
    for path in FROZEN:
        check(previous(path) == current(path), "unchanged firmware/ETS/PCB: " + path)

    old = previous("src/controller/controller.ini").splitlines(keepends=True)
    new = current("src/controller/controller.ini").splitlines(keepends=True)
    inserted = []
    for op, _, _, lo, hi in difflib.SequenceMatcher(
            None, old, new, autojunk=False).get_opcodes():
        check(op in ("insert", "equal"),
              "controller.ini only adds explicit picotool protocol")
        if op == "insert":
            inserted += new[lo:hi]
    addition = "".join(inserted)
    check(addition.count("upload_protocol = picotool") == 1,
          "exactly one explicit controller picotool protocol")
    check("upload_command" not in addition and "upload_flags" not in addition,
          "no unsafe custom PlatformIO upload command")

    tool = current("tools/usb_flash_controller.py")
    test = current("tools/test_usb_flash_controller.py")
    ast.parse(tool)
    ast.parse(test)
    for symbol in (
        'def choose_port(', 'def hwid_vidpid(', 'def require_upload_consent(',
        'def verify_clean_head(', 'def copy_isolated_source(',
        'def build_isolated(', 'def save_uf2(', 'def discover_ports(',
        '--confirm-safe-bench', '--execute', '--port',
        '--expect-vidpid', '--expected-head',
        '"upload",', '"plan",', '"probe",',
        '"--upload-port"', 'normalized_port(args.port)',
        'verify_clean_head(args.expected_head)',
    ):
        check(symbol in tool, "guarded USB host path " + symbol)
    for forbidden in (
        'digitalWrite(', 'knx.write(', 'Serial2.write(',
        'acknowledgeAndRequireFresh(', 'armNativeSimulation(',
    ):
        check(forbidden not in tool,
              "no KNX motor/firmware runtime side effect: " + forbidden)

    doc = current("docs/KNX027_USB_FLASH_AUTOMATION.md")
    check("KEIN" in doc or "kein physischer" in doc.lower(),
          "real hardware operation explicitly deferred")
    check("BOOTSEL" in doc and "KNX018" in doc,
          "manual recovery and laptop bench documented")
    print("RESULT: KNX027 USB scope and frozen firmware product PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
