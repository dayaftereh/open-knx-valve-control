#!/usr/bin/env python3
"""KNX021 gate: offline chain only, immutable production ETS/PCB/firmware.

Use a fixed verified Git baseline. Verifies that production sources are not
silently modified and that the simulated feedback model has no hardware API.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "8dc7577"
IMMUTABLE = (
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    "assets/knx008_zone_ets_proposal.json",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "lib/common/heating_zone_model.hpp",
    "lib/common/room_pi_controller.hpp",
    "lib/common/motor_queue_simulator.hpp",
)


def check(works: bool, why: str) -> None:
    if not works:
        raise ValueError(why)
    print("PASS:", why)


def frozen(rel: str) -> None:
    previous = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{rel}"], cwd=ROOT)
    actual = (ROOT / rel).read_bytes()
    check(actual.replace(b"\r\n", b"\n") ==
          previous.replace(b"\r\n", b"\n"),
          "Unchanged established software/product source: " + rel)


def main() -> int:
    for filename in IMMUTABLE:
        frozen(filename)

    new = ROOT / "lib/common/virtual_motor_feedback.hpp"
    code = new.read_text(encoding="utf-8")
    includes = set(re.findall(
        r'(?m)^[ \t]*#include[ \t]+([<"][^>"]+[>"])', code))
    check(includes == {'"motor_queue_simulator.hpp"', '<stdint.h>'},
          "Virtual backend imports only portable simulator model")
    dangerous = (
        "digitalWrite(", "analogWrite(", "pinMode(",
        "gpio_put(", "gpio_set_dir(", "pwm_set_",
        "Serial1.", "Serial2.", "Wire.", "knx.",
        "getGroupObject(", "motorEnable(",
    )
    check(not any(name in code for name in dangerous),
          "No KNX, UART, GPIO, PWM or real actuator APIs")
    for token in (
        "independentlyAllOff()", "plannedCompletion_", "stopPending_",
        "AckKind::AllOff", "evidence_[", "referenced = false",
        "options_.stuckOnStop", "options_.dropStopAck",
        "EventKind::Start", "EventKind::Stop",
    ):
        check(token in code, "Virtual backend invariant: " + token)

    integrated = (ROOT / "tests/native/test_knx021_end_to_end.cpp").read_text(
        encoding="utf8")
    for required in (
        "RoomPi::Bank", "HeatingZone::resolve",
        "Queue queue", "VirtualMotor::Backend",
        "testThreeRealSoftwareComponentsTogether",
        "testInterruptedMotionLosesPositionCertainty",
        "testMissingStopAckBlocksOtherChannels",
        "testStopThatDoesNotTurnOffNeverGrantsAnotherMotor",
        "testCrossingMillisWrap",
    ):
        check(required in integrated, "E2E source exercises " + required)

    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf8")
    for ident in ("KNX009", "KNX016"):
        check(re.search(
            rf"(?m)^\| \*\*{ident}\*\*[^|]*\| "
            r"\*\*deferred, 2026-10-12\*\* \|", roadmap) is not None,
            f"{ident} still deferred for independent ETS/KNX bench")
    check(re.search(
        r"(?m)^\| \*\*KNX004\*\*[^|]*\| planned \|", roadmap) is not None,
          "Physical motor safety KNX004 remains planned")
    check("| **KNX018** " in roadmap and "| **KNX021** " in roadmap,
          "Future separate KNX bench and current E2E software slice recorded")

    print("RESULT: KNX021 pure simulation and production immutability PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(2)
