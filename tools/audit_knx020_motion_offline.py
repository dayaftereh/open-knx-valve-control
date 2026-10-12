#!/usr/bin/env python3
"""KNX020 guard: only offline, isolated simulator code and docs may change.

The live ETS product, PCB, two production firmware trees and previous KNX008
/ KNX019 models must match the verified pre-slice Git baseline.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "386d305"
UNCHANGED = (
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    "assets/knx008_zone_ets_proposal.json",
    "lib/common/heating_zone_model.hpp",
    "lib/common/room_pi_controller.hpp",
    "src/controller/main.cpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "src/controller/config.hpp",
    "schematic/pcb_knx-valve-control_v1.2.json",
)


def ensure(condition: bool, what: str) -> None:
    if not condition:
        raise ValueError(what)
    print("PASS:", what)


def old_file(rel: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{rel}"], cwd=ROOT)


def main() -> int:
    for rel in UNCHANGED:
        existing = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        old = old_file(rel).replace(b"\r\n", b"\n")
        ensure(existing == old, "No production source/ETS/PCB change: " + rel)

    core = (ROOT / "lib/common/motor_queue_simulator.hpp").read_text(
        encoding="utf8")
    ensure('#include "heating_zone_model.hpp"' in core,
           "Uses KNX008 software-only validated target intents")
    includes = set(re.findall(r'(?m)^#include\s+([<"][^>"]+[>"])', core))
    ensure(includes <= {'"heating_zone_model.hpp"', "<stdint.h>"},
           "Portable simulator only, with no KNX/Arduino/driver imports")
    prohibited = (
        "digitalWrite(", "pinMode(", "analogWrite(",
        "getGroupObject(", "Serial1.", "Serial2.", "Wire.",
        "motorEnable(", "startMotor(", "stopMotor(", "setPWM(",
    )
    ensure(not any(item in core for item in prohibited),
           "Motor simulator has NO physical output or KNX API calls")
    for requirement in (
        "State::StartPending", "State::StopPending", "State::FaultLatched",
        "EventKind::Start", "EventKind::Stop", "AckKind::AllOff",
        "outputInterlockQualified", "currentMonitoringQualified",
        "awaitingRevision_", "nextCandidate_", "stopOverdue_",
        "return stopEvent(lastStopReason_);",
    ):
        ensure(requirement in core, "Scheduler gate: " + requirement)
    ensure("MotorCount = HeatingZone::MotorCount" in core,
           "Exactly eight physical channels tied to KNX008")
    ensure("NoMotor = 0xFF" in core,
           "No implicit active motor on startup")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf8")
    for name in ("KNX009", "KNX016"):
        ensure(re.search(
            rf"(?m)^\| \*\*{name}\*\*[^|]*\| "
            r"\*\*deferred, 2026-10-12\*\* \|", roadmap) is not None,
            f"{name} real ETS/bus tests still deferred")
    ensure(re.search(
        r"(?m)^\| \*\*KNX004\*\*[^|]*\| planned \|", roadmap) is not None,
        "Production KNX004 hardware-safety slice NOT falsely closed")
    ensure("| **KNX018** " in roadmap,
           "Independent KNX testbench dependency retained")
    ensure("| **KNX020** " in roadmap,
           "Separate simulation-only ASH slice recorded")
    print("RESULT: KNX020 offline-only source contract PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(2)
