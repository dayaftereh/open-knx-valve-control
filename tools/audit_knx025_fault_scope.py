#!/usr/bin/env python3
"""KNX025 read-only production-scope and recovery audit.

PASS here is solely a static software invariant, NOT KNX, ETS, independent
motor AllOff, brownout watchdog or actual powered board acceptance.
"""
from __future__ import annotations

import difflib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = "044eac5"
FROZEN = (
    "assets/open-knx-valve-control.xml",
    "assets/knx008_zone_ets_proposal.json",
    "include/knxprod.hpp",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "src/temperature/temperature.ini",
    "lib/common/room_control_runtime.hpp",
    "lib/common/knx024_room_dpt_adapter.hpp",
    "lib/common/heating_zone_model.hpp",
    "lib/common/room_pi_controller.hpp",
    "lib/common/motor_queue_simulator.hpp",
    "lib/common/virtual_motor_feedback.hpp",
)


class ScopeError(ValueError):
    pass


def check(ok: bool, message: str) -> None:
    if not ok:
        raise ScopeError(message)
    print("PASS:", message)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig").replace(
        "\r\n", "\n")


def initial(rel: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASE}:{rel}"], cwd=ROOT).decode(
            "utf-8-sig").replace("\r\n", "\n")


def main() -> int:
    for path in FROZEN:
        check(read(path) == initial(path),
              "KNX025 preserves product V2 / V3 proposal / motors / ATtiny: "
              + path)

    old = initial("src/controller/main.cpp").splitlines(keepends=True)
    new = read("src/controller/main.cpp").splitlines(keepends=True)
    additions = []
    for kind, _, _, lo, hi in difflib.SequenceMatcher(
            None, old, new, autojunk=False).get_opcodes():
        check(kind in ("equal", "insert"),
              "KNX025 only adds code to controller main, not replacing"
              " existing functions")
        if kind == "insert":
            additions += new[lo:hi]
    newCode = "".join(additions)
    for required in (
        '#include "knx025_fault_supervisor.hpp"',
        "Knx025::Supervisor roomFaultSupervisor;",
        "roomFaultSupervisor.reset(lastRoomSoftwareTickMs);",
        "softwareSignals.manifoldTelemetryObserved =",
        "temperatureBridge.hasSnapshot();",
        "softwareSignals.manifoldTelemetryOnline =",
        "temperatureBridge.online(softwareNow);",
        "roomFaultSupervisor.observeFirmware(",
    ):
        check(newCode.count(required) == 1,
              "Real firmware KNX025 passive-only diagnostic: " + required)

    header = read("lib/common/knx025_fault_supervisor.hpp")
    for required in (
        "enum class Fault",
        "InvalidRoomTelegram",
        "RoomSourceExpired",
        "DirectDemandExpired",
        "RoomTransportLost",
        "SoftwareLoopStalled",
        "SoftwareConfigurationChanged",
        "MotorQueueFault",
        "MockBackendProtocolFault",
        "OperatorEmergencyStop",
        "Phase::FaultLatched",
        "void observeFirmware(",
        "void softwareTick(",
        "acknowledgeAndRequireFresh(",
        "void quarantine(",
        "pipeline.cancelNativeSimulation();",
        "pipeline.inputs() = {};",
        "q.leaseMask != 0U",
        "nativeMockOccupancy(pipeline) == 0U",
        "RoomPi::sameSettings(cfg, expectedSettings_)",
        "d_.physicalOutputsVerifiedOff = false;",
        "manifoldTelemetryWarning",
        "return false;",
        "#if defined(ARDUINO)",
        "pipeline.nativeBackendStatus()",
    ):
        check(required in header,
              "KNX025 expected fail-closed source contract: " + required)

    motorApi = re.compile(
        r"\b(?:pinMode|digitalWrite|analogWrite|gpio_put|gpio_init|"
        r"pwm_set_gpio_level|pwm_set_wrap|motorEnable|startMotor|"
        r"watchdog_enable|watchdog_reboot|"
        r"knx\s*\.\s*getGroupObject|GroupObject\s*::\s*value)\s*\(")
    check(not motorApi.search(newCode + "\n" + header),
          "No motor GPIO, KNX group-object, or REAL HW watchdog calls added")
    check("Knx024::Adapter" not in newCode,
          "Real AppVersion2 firmware not bound to proposed V3 KO RX")
    check("knx.configured()" not in newCode,
          "KNX commissioned flag NOT misused as room transport heartbeat")
    check("roomControlRuntime.tick(softwareNow);" in read(
        "src/controller/main.cpp"),
        "Existing KNX023 DISARMED controller RAM computation unchanged")

    tests = read("tests/native/test_knx025_fault_supervisor.cpp")
    for required in (
        "activeDirectSourceStaleRequiresFreshRecovery",
        "roomPIInvalidAndStaleInput",
        "physicalProbeTelemetryIsIndependentOfRoomInput",
        "transportLossBlocksRecoverUntilOnline",
        "softwareLoopWatchdogAndUint32Wrap",
        "virtualMotorLeaseStopAckMustCompleteBeforeRecovery",
        "nativeQueueFaultAndOperatorStop",
        "passiveFirmwareIsNotANewKNXBus",
    ):
        check(required in tests,
              "KNX025 native negative-safety scenario: " + required)
    check("MotorQueueSim::State::Disarmed" in read(
        "tests/native/test_knx025_firmware_hardlock.cpp"),
        "ARDUINO compiled-branch hardlock regression present")

    roadmap = read("docs/ROADMAP.md")
    check("| **KNX025** " in roadmap, "Roadmap documents KNX025")
    for task in ("KNX009", "KNX016"):
        check(re.search(
            rf"(?m)^\| \*\*{task}\*\*[^|]*\| "
            r"\*\*deferred, 2026-10-12\*\* \|", roadmap) is not None,
            task + " ETS/KNX live test remains deferred")
    check(re.search(
        r"(?m)^\| \*\*KNX004\*\*[^|]*\| planned \|", roadmap) is not None,
        "Real KNX004 motor hardware interlock remains planned")
    print("RESULT: KNX025 strict proposed room fault supervisor"
          " and production NO-MOTOR-I/O audit PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScopeError, OSError, subprocess.CalledProcessError) as error:
        print("FAIL KNX025 static source audit:", error, file=sys.stderr)
        raise SystemExit(2)
