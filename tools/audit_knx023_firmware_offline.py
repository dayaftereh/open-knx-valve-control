#!/usr/bin/env python3
"""KNX023 read-only software/firmware-ABI and no-motor-IO gate.

Compares live files to the immutable KNX022 closing baseline; DOES NOT
access serial ports, USB programmer, GPIO, network bus or devices.
Exitcode 0 means only that the restricted software change was audited.
"""
from __future__ import annotations

import difflib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = "3b47fa7"
UNCHANGED = (
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    "assets/knx008_zone_ets_proposal.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "schematic/sch_knx-valve-control_v1.2.json",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "lib/common/heating_zone_model.hpp",
    "lib/common/room_pi_controller.hpp",
    "lib/common/motor_queue_simulator.hpp",
    "lib/common/virtual_motor_feedback.hpp",
)


def check(condition: bool, name: str) -> None:
    if not condition:
        raise ValueError(name)
    print("PASS:", name)


def baseline(relpath: str) -> str:
    raw = subprocess.check_output(["git", "show", f"{BASE}:{relpath}"],
                                  cwd=ROOT)
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def current(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8-sig").replace(
        "\r\n", "\n")


def main() -> int:
    for path in UNCHANGED:
        check(current(path) == baseline(path),
              "No edits to production XML/PCB/ATtiny/existing models: " + path)

    main_old = baseline("src/controller/main.cpp")
    main_new = current("src/controller/main.cpp")
    old_lines = main_old.splitlines(keepends=True)
    new_lines = main_new.splitlines(keepends=True)
    changes = difflib.SequenceMatcher(
        None, old_lines, new_lines, autojunk=False).get_opcodes()
    new_only = []
    for kind, _, _, begin, end in changes:
        check(kind in ("equal", "insert"),
              "Controller main.cpp modified by insertion only (" + kind + ")")
        if kind == "insert":
            new_only.extend(new_lines[begin:end])
    inserted = "".join(new_only)

    for expected in (
        '#include "room_control_runtime.hpp"',
        "RoomControlRuntime::Pipeline roomControlRuntime;",
        "lastRoomSoftwareTickMs = millis();",
        "roomControlRuntime.reset(lastRoomSoftwareTickMs);",
        "roomControlRuntime.tick(softwareNow);",
        "static_cast<uint32_t>(softwareNow - lastRoomSoftwareTickMs) >= 100UL",
    ):
        check(inserted.count(expected) == 1,
              "Controller actual RAM-only integration hook: " + expected)

    # This audit does not accept new physical output/control I/O in
    # added source. Existing, previously approved KNX temperature
    # publishing and UART functions are outside of this new scope.
    disallowed_io = re.compile(
        r"\b(?:pinMode|digitalWrite|analogWrite|gpio_put|gpio_init|"
        r"pwm_set_|motorEnable|startMotor|knx\.getGroupObject|"
        r"GroupObject)\s*\(")
    check(not disallowed_io.search(inserted),
          "No added motor GPIO/PWM/KNX KO actuation in main.cpp")

    header = current("lib/common/room_control_runtime.hpp")
    for required in (
        '#include "room_pi_controller.hpp"',
        '#include "heating_zone_model.hpp"',
        '#include "motor_queue_simulator.hpp"',
        '#include "virtual_motor_feedback.hpp"',
        '#if !defined(ARDUINO)',
        '#if defined(ARDUINO)',
        'return false;',
        'MotorQueueSim::Queue queue_',
        'void tick(uint32_t nowMs)',
        'physicalOutputsConnected = false;',
    ):
        check(required in header,
              "Embedded portable runtime contract: " + required)
    check(not disallowed_io.search(header),
          "No physical I/O calls in runtime implementation")
    check(header.count('return false;') >= 2,
          "Arduino arming and position injection both hard deny")
    check(header.index('#if !defined(ARDUINO)') <
          header.index('#include "virtual_motor_feedback.hpp"'),
          "Virtual native feedback excluded in Arduino build")
    check("virtual_motor_feedback.hpp" not in main_new,
          "Real controller source does not include virtual motor backend")

    roadmap = current("docs/ROADMAP.md")
    check("| **KNX023** " in roadmap,
          "KNX023 separate ASH slice documented")
    for ident in ("KNX009", "KNX016"):
        check(re.search(
            rf"(?m)^\| \*\*{ident}\*\*[^|]*\| "
            r"\*\*deferred, 2026-10-12\*\* \|", roadmap) is not None,
            "Real ETS/KNX " + ident + " remains deferred")
    check(re.search(
        r"(?m)^\| \*\*KNX004\*\*[^|]*\| planned \|", roadmap) is not None,
          "Real KNX004 motor safety stays planned")
    check("BLOCKED" in current("docs/KNX018_LAPTOP_UPDI_TESTBENCH.md") or
          "nicht" in current("docs/KNX018_LAPTOP_UPDI_TESTBENCH.md").lower(),
          "Laptop hardware-readiness not claimed as complete")
    print("RESULT: KNX023 strict non-actuating source/firmware scope PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as err:
        print("FAIL:", err, file=sys.stderr)
        raise SystemExit(2)
