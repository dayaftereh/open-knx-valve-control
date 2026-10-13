#!/usr/bin/env python3
"""KNX034 documentation-source safety audit. Never authorizes any power or bus I/O."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from audit_design import components

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/KNX034_USB_ONLY_PREFLIGHT.json"
BASE = "e8033c7"
PHOTO_SHA = "932bfac8982d03ebee0e23087a8da03d7480d40fc89b5677eec800fb3d392e82"
STATUS = "BLOCKED_PENDING_UNPOWERED_MEASUREMENTS_AND_F1_REVIEW"
EXPECTED_NETS = {
    "JMP1": {"1": "KNX_VCC", "2": "R9_2"},
    "Q1": {"1": "USB_VCC", "2": "5V_", "3": "R9_2"},
    "R9": {"1": "GND", "2": "R9_2"},
    "D6": {"1": "5V_", "2": "USB_VCC"},
    "F1": {"1": "5V_", "2": "5V"},
    "D1": {"1": "D1_1", "2": "5V"},
    "U6": {"1": "D1_1", "2": "GND", "3": "3.3V"},
}
FROZEN = (
    "docs/KNX033_AS_BUILT_PREFLIGHT.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "schematic/sch_knx-valve-control_v1.2.json",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "assets/open-knx-valve-control.xml",
    "tools/audit_knx033_asbuilt.py",
    "tools/test_knx033_asbuilt_gate.py",
    "tools/usb_flash_controller.py",
    "tools/knx029_prepare_bringup.py",
    "tools/knx031_uart_trace.py",
)


class ReviewBlocked(ValueError):
    pass


def guard(ok: bool, reason: str) -> None:
    if not ok:
        raise ReviewBlocked(reason)


def validate(report: dict[str, Any], pcb: dict[str, Any]) -> None:
    guard(report.get("schema") ==
          "openknx-valvecontrol/knx034-usb-only-power-gate-v1",
          "Wrong schema")
    guard(report.get("source_head") == BASE and
          report.get("revision") == "V1.2",
          "Wrong baseline/revision")
    guard(report.get("status") == STATUS,
          "Visual evidence cannot grant power authorization")
    guard(report.get("evidence") == "photographic_and_designed_netlist_only",
          "Evidence incorrectly upgraded to electrical measurements")
    photo = report.get("new_photo", {})
    guard(photo.get("filename") == "20261013_164325.jpg" and
          photo.get("sha256") == PHOTO_SHA and
          photo.get("image_archived_on_home") is False and
          photo.get("side") == "reverse",
          "Reverse-side photo identity or storage incorrectly claimed")
    seen = photo.get("observations", {})
    guard(seen.get("U6_black_regulator_housing_visible") is True and
          seen.get("U6_label_near_component_visible") is True and
          seen.get("U6_exact_manufacturer_marking_readable") is False and
          seen.get("electrical_test_performed") is False,
          "Visual U6 observation cannot claim exact module or electrical tests")
    current = report.get("current_jmp1", {})
    proposed = report.get("proposed_jmp1", {})
    guard(current.get("source") == "prior_user_report" and
          current.get("reported_closed") is True and
          current.get("measured_resistance_ohms") is None,
          "Prior reported installed jumper has no measured state")
    guard(proposed.get("state") == "PROPOSED_NOT_APPLIED" and
          proposed.get("target_open") is True and
          proposed.get("physical_change_performed") is False and
          proposed.get("measured_resistance_ohms") is None,
          "JMP1 proposal cannot be recorded as a physical operation")
    guard(proposed.get("expected_severed_net_pair") ==
          ["KNX_VCC", "R9_2"] and
          proposed.get("galvanic_isolation_proven") is False and
          proposed.get("KNX_USB_backfeed_absence_proven") is False,
          "JMP1 alone cannot claim galvanic isolation / backfeed absence")

    guard(report.get("expected_pad_nets") == EXPECTED_NETS,
          "PCB pad-net contract changed")
    for component, connections in EXPECTED_NETS.items():
        observed = pcb.get(component, {}).get("pins", {})
        for pad, expected in connections.items():
            guard(observed.get(pad) == expected,
                  f"PCB net changed: {component}.{pad} != {expected}")

    f1 = report.get("f1", {})
    guard(f1.get("nominal_schematic_mA") == 630 and
          f1.get("observed_photo_mA") == 2500 and
          f1.get("actual_part_characteristics_verified") is False and
          f1.get("protective_coordination_verified") is False,
          "F1 nominal/current discrepancy remains unresolved")
    d1 = report.get("d1", {})
    guard(d1.get("installed") == "wire_bypass_user_report" and
          d1.get("original_diode_directional_isolation_removed") is True and
          d1.get("electrical_continuity_verified") is False and
          d1.get("adjacent_shorts_excluded") is False,
          "D1 wire cannot be treated as a protected/verified diode")
    u6 = report.get("u6", {})
    guard(u6.get("housing_seen_on_reverse_photo") is True and
          u6.get("exact_part_marking_verified") is False and
          u6.get("minimum_VIN_V") == 4.75 and
          u6.get("actual_VIN_V") is None and
          u6.get("actual_output_V") is None,
          "Visual U6 housing is not a real voltage measurement")
    requirements = report.get("requirements", {})
    guard(requirements and all(x is True for x in requirements.values()),
          "Hardware preconditions cannot be relaxed in photo evidence")
    measurements = report.get("unpowered_measured")
    guard(isinstance(measurements, dict) and len(measurements) >= 10 and
          all(value is None for value in measurements.values()),
          "There are no new real DMM measurements yet")
    releases = report.get("releases")
    guard(isinstance(releases, dict) and len(releases) == 7 and
          all(value is False for value in releases.values()),
          "Photo/jumper proposal must never allow power/flash/bus/motor")


def main() -> int:
    try:
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        data = json.loads((ROOT / "schematic/pcb_knx-valve-control_v1.2.json")
                          .read_text(encoding="utf-8-sig"))
        validate(doc, components(data["shape"]))
        print("PASS KNX034: jumper USB-only proposal, power blocked, nets checked")
        safe_dir = ROOT.resolve().as_posix()
        for path in FROZEN:
            v = subprocess.run(["git", "-c", f"safe.directory={safe_dir}",
                                "-C", str(ROOT), "show", f"{BASE}:{path}"],
                               capture_output=True, check=False)
            guard(v.returncode == 0 and
                  v.stdout.replace(b"\r\n", b"\n") ==
                  (ROOT / path).read_bytes().replace(b"\r\n", b"\n"),
                  "Prior firmware/PCB/ETS/KNX033 source changed: " + path)
        print("PASS KNX034: previous source/FW/PCB/ETS/KNX033 evidence frozen")
        print("STATUS:", STATUS)
        return 0
    except (OSError, ValueError, ReviewBlocked) as exc:
        print("FAIL KNX034:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
