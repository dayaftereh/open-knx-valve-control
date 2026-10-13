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


def strip_known_knx028_pin_changes(config: str) -> str:
    """Compare legacy KNX027 upload scope after undoing reviewed KNX028 pins.

    This does NOT broadly ignore controller.ini edits: the exact platform
    commit, framework, and compiler release must match this new contract.
    """
    original_platform = "platform = https://github.com/maxgerhardt/platform-raspberrypi"
    pinned_platform = (
        "; KNX028: Home-verified maxgerhardt PlatformIO revision (raspberrypi 1.20.0).\n"
        "platform = https://github.com/maxgerhardt/platform-raspberrypi.git#"
        "5d4561a05e3b212660ac6fdd3fbfb328d1988aa1"
    )
    framework = (
        "framework-arduinopico @ https://github.com/earlephilhower/"
        "arduino-pico/releases/download/5.5.0/rp2040-5.5.0.zip"
    )
    original_packages = "platform_packages = " + framework
    pinned_packages = (
        "; KNX028: reproducible toolchain. GCC 16.1.0 broke Arduino-Pico 5.5.0\n"
        "; with __getreent not declared (framework malloc-lock.cpp). GCC 14.3.0\n"
        "; matches the previously verified successful LLO Desktop controller build.\n"
        "platform_packages =\n"
        "    " + framework + "\n"
        "    toolchain-rp2040-earlephilhower @ "
        "https://github.com/earlephilhower/pico-quick-toolchain/releases/"
        "download/4.1.0/x86_64-w64-mingw32.arm-none-eabi-1aec55e.250530.zip"
    )
    if "KNX028:" in config:
        check(config.count(pinned_platform) == 1,
              "KNX028 explicit platform revision only")
        check(config.count(pinned_packages) == 1,
              "KNX028 explicit GCC 14.3.0 compiler pin only")
        config = config.replace(pinned_platform, original_platform, 1)
        config = config.replace(pinned_packages, original_packages, 1)
    return config


def main() -> int:
    for path in FROZEN:
        check(previous(path) == current(path), "unchanged firmware/ETS/PCB: " + path)

    old = previous("src/controller/controller.ini").splitlines(keepends=True)
    new = strip_known_knx028_pin_changes(
        current("src/controller/controller.ini")).splitlines(keepends=True)
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
