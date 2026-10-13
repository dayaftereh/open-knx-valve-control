#!/usr/bin/env python3
"""KNX033: verify evidence/source consistency of V1.2 as-built photo preflight.

This is NOT photographic OCR, electrical continuity, an ERC/DRC or a release.
It does not open hardware/COM/KNX, flash, supply power or enable any motor.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from audit_design import components
from audit_knx022_hw_preflight import schematic_labels

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/KNX033_AS_BUILT_PREFLIGHT.json"
SCHEMA = "openknx-valvecontrol/knx033-visual-as-built-preflight-v1"
BASE = "7d8f835"
STATUS = "BLOCKED_NO_POWER_NO_FLASH_NO_MOTOR"
PHOTO_HASHES = {
    "20261013_160055.jpg":
        "d1d43ebca2575577a443a118c7578d40129f9b239abf974b2431568b032cbdb0",
    "20261013_160046.jpg":
        "21eeb078657f3835bfff5b7f9d13454e07c54c7d4498e2c0f4d6019847081c16",
    "20261013_160042.jpg":
        "420375056e798662df1b34f1335b48489f11c784210af7c802e63249599522c1",
}
EXPECTED = {
    "D1": {"1": "D1_1", "2": "5V"},
    "F1": {"1": "5V_", "2": "5V"},
    "D6": {"1": "5V_", "2": "USB_VCC"},
    "Q1": {"1": "USB_VCC", "2": "5V_", "3": "R9_2"},
    "JMP1": {"1": "KNX_VCC", "2": "R9_2"},
    "JMP2": {"1": "KNX_RX'", "2": "KNX_RX", "3": "KNX_TX'"},
    "JMP3": {"1": "KNX_RX'", "2": "KNX_TX", "3": "KNX_TX'"},
    "U6": {"1": "D1_1", "2": "GND", "3": "3.3V"},
    "R29": {"1": "3.3V", "2": "M_VCC"},
    "U25": {"1": "3.3V", "16": "UPDI", "20": "GND"},
}
LINKS = {
    "JMP1": ["1", "2"],
    "JMP2_upper_if_matching_PCB_orientation": ["1", "2"],
    "JMP3_upper_if_matching_PCB_orientation": ["2", "3"],
    "D1_bypass": ["1", "2"],
}
MEASUREMENTS = {
    "JMP1_pad1_2_ohms", "JMP2_pad1_2_ohms",
    "JMP2_pad2_3_ohms", "JMP3_pad2_3_ohms",
    "JMP3_pad1_2_ohms", "D1_pad1_2_ohms",
    "D1_bridge_to_adjacent_D5_R7_short_test",
    "F1_pad1_2_ohms", "U6_physical_location_and_part",
    "U6_input_to_ground_observation",
    "three_point_three_V_to_GND_observation",
    "five_V_to_GND_observation",
    "U25_full_marking_and_read_only_signature",
    "R29_as_built_part_and_milliohm_measurement",
    "reverse_side_photo_received",
}
RELEASE = {
    "correct_fuse_protective_rating_verified",
    "power_source_selection_Q1_JMP1_verified",
    "D1_bypass_short_and_reverse_current_safety_verified",
    "U6_regulator_physically_verified",
    "rails_and_updi_voltage_topology_verified",
    "KNX_to_USB_backfeed_absent_verified",
    "MCU_and_flash_variant_confirmed",
    "any_power_on_authorized",
    "any_USB_UPDI_KNX_contact_authorized",
    "motor_enable_authorized",
}
FROZEN = (
    "schematic/pcb_knx-valve-control_v1.2.json",
    "schematic/sch_knx-valve-control_v1.2.json",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/controller.ini",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "lib/common/temperature_protocol.hpp",
    "assets/open-knx-valve-control.xml",
    "tools/usb_flash_controller.py",
    "tools/knx029_prepare_bringup.py",
    "tools/knx030_passive_inventory.py",
    "tools/knx031_uart_trace.py",
    "tools/test_knx032_uart_to_knx.py",
)


class ReviewError(RuntimeError):
    pass


def ensure(condition: bool, text: str) -> None:
    if not condition:
        raise ReviewError(text)


def audit_document(doc: dict[str, Any],
                   pcb: dict[str, Any],
                   labels: dict[str, Any]) -> None:
    """Fail closed: a photo cannot establish physical power-on GO."""
    ensure(doc.get("schema") == SCHEMA and
           doc.get("source_git_head") == BASE and
           doc.get("revision") == "V1.2", "Wrong V1.2 source or schema")
    ensure(doc.get("status") == STATUS, "Wrong photo-gate status")
    ensure("not" in doc.get("image_archive", "").lower() and
           "ChatGPT" in doc.get("image_archive", ""),
           "Photos were NOT archived to LLO Home; never pretend otherwise")
    images = doc.get("photos", [])
    ensure(isinstance(images, list) and len(images) == 3,
           "Exactly three current user photos are referenced")
    ensure({p.get("filename"): p.get("sha256") for p in images
            if isinstance(p, dict)} == PHOTO_HASHES,
           "As-built photo hashes differ from originals observed in this chat")
    ensure(all(isinstance(p.get("size_bytes"), int) and
               p["size_bytes"] > 500000 for p in images),
           "Photo source record sizes incomplete")
    wanted = doc.get("net_contracts")
    ensure(wanted == EXPECTED, "Expected pad-net audit contract changed")
    for name, pins in EXPECTED.items():
        actual = pcb.get(name, {}).get("pins", {})
        for pin, net in pins.items():
            ensure(actual.get(pin) == net,
                   f"PCB as-designed mismatch: {name} pin {pin} vs {net}")
    ensure(labels.get("F1", {}).get("display") == "630mA 275V",
           "Schematic expected F1 630mA changed")
    ensure(labels.get("U25", {}).get("display") == "ATTINY3216",
           "Schematic U25 ATtiny3216 intent changed")
    ensure(pcb.get("U25", {}).get("meta", {}).get("Manufacturer Part") ==
           "ATTINY1616-SN", "PCB U25 metadata discrepancy changed")
    ensure(pcb.get("F1", {}).get("meta", {}).get("Manufacturer Part") ==
           "S1032-F-60.0A", "PCB F1 metadata discrepancy changed")
    ensure(pcb.get("D1", {}).get("meta", {}).get("Manufacturer Part") ==
           "1N5819HW-7-F", "Original diode metadata changed")
    ensure(doc.get("nominal_expected_links") == LINKS,
           "Jumper electrical pad assignments must not be guessed")
    observed = doc.get("observations", {})
    fuse = observed.get("F1", {})
    ensure(fuse.get("schematic_nominal_mA") == 630 and
           fuse.get("photo_apparent_nominal_mA") == 2500 and
           fuse.get("schematic_nominal_mA") !=
           fuse.get("photo_apparent_nominal_mA") and
           "T 2.5A" in fuse.get("photo_marking", ""),
           "F1 630mA / photographed 2.5A discrepancy MUST remain open")
    ensure(observed.get("U6", {}).get("installed_location") is None,
           "U6 installation cannot be inferred from single board side")
    ensure(observed.get("R29", {}).get("actual_ohms") is None,
           "No actual R29 ohm measurement exists")
    ensure(observed.get("U25", {}).get("hardware_mcu_signature") is None,
           "No genuine UPDI device signature read exists")
    ensure(observed.get("D1_wire", {}).get("continuity_verified") is False,
           "D1 continuity is not tested")
    reports = doc.get("reported_modifications", {})
    for key in ("JMP1", "JMP2", "JMP3", "D1"):
        ensure(isinstance(reports.get(key), dict) and
               reports[key].get("electrical_verified") is False,
               "Photo/user assertion must not become electrical verification")
    ensure("removed" in reports["D1"].get("user_report", "") and
           "bidirectionally" in reports["D1"].get("effect", ""),
           "D1 removed one-way isolation cannot be silently reinstated")
    checks = doc.get("unpowered_checks")
    ensure(isinstance(checks, dict) and set(checks) == MEASUREMENTS and
           all(v is None for v in checks.values()),
           "No real ohmmeter reading or backside evidence yet")
    release = doc.get("pre_energization_release")
    ensure(isinstance(release, dict) and set(release) == RELEASE and
           all(v is False for v in release.values()),
           "Photo report cannot authorize power/USB/KNX/UPDI/motor")


def frozen_git_read(path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-c", "safe.directory=" + ROOT.resolve().as_posix(),
         "-C", str(ROOT), "show", f"{BASE}:{path}"],
        capture_output=True, check=False)
    ensure(proc.returncode == 0, "Git source unavailable: " + path)
    return proc.stdout.replace(b"\r\n", b"\n")


def main() -> int:
    try:
        source = json.loads(REPORT.read_text(encoding="utf-8"))
        pcb = components(json.loads(
            (ROOT / "schematic/pcb_knx-valve-control_v1.2.json")
            .read_text(encoding="utf-8-sig"))["shape"])
        sch = schematic_labels(json.loads(
            (ROOT / "schematic/sch_knx-valve-control_v1.2.json")
            .read_text(encoding="utf-8-sig")))
        audit_document(source, pcb, sch)
        print("PASS KNX033 as-built photo/source gate; F1 mismatch flagged")
        for f in FROZEN:
            now = (ROOT / f).read_bytes().replace(b"\r\n", b"\n")
            ensure(now == frozen_git_read(f), "Unexpected source edit: " + f)
        print("PASS KNX033: production firmware, ETS, PCB, USB tools FROZEN")
        print("STATUS:", STATUS)
        print("ALL real electrical data ABSENT; photo observations are not a power-on GO")
        return 0
    except (OSError, ReviewError, ValueError) as error:
        print("FAIL KNX033:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
