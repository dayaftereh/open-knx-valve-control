#!/usr/bin/env python3
"""KNX024 strict offline proposed-ETS ABI/firmware non-actuation gate.

The KNX008 AppV3 proposal is an immutable DESIGN CONTRACT, not a real
ETS-importable AppV3 product. This tool never accesses USB, GPIO, ETS, KNX
buses or the network. PASS means source consistency, not ETS certification.
"""
from __future__ import annotations

import copy
import difflib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "99d7244"
PROPOSAL = "assets/knx008_zone_ets_proposal.json"
FROZEN = (
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    PROPOSAL,
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


class ContractError(ValueError):
    """Proposed-only ETS objects differ from checked byte-level API."""


def check(condition: bool, what: str) -> None:
    if not condition:
        raise ContractError(what)
    print("PASS:", what)


def frozen_source(path: str) -> None:
    expected = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
    actual = (ROOT / path).read_bytes()
    check(expected.replace(b"\r\n", b"\n") ==
          actual.replace(b"\r\n", b"\n"),
          "Product/PCB/ATtiny/existing model untouched: " + path)


def check_proposal(p: dict) -> None:
    check(p.get("schema") == "openknxvalve.knx008.zone-proposal.v1",
          "Proposal schema locked to KNX008")
    check(p.get("status") == "PROPOSAL_ONLY__NOT_IN_ETS_XML_OR_FIRMWARE",
          "Proposed KOs not misrepresented as actual ETS product")
    base = p["baseline"]
    check(base["existingApplicationVersion"] == 2 and
          base["proposedApplicationVersion"] == 3 and
          base["existingCommunicationObjects"] == 35 and
          base["existingParameters"] == 21 and
          base["preserveKoRange"] == [1, 35] and
          base["preserveParameterRange"] == [1, 21],
          "Existing ETS V2 KO1..35 P1..21 preserve / V3 only proposed")

    pct = p["percentage"]
    check(pct["canonicalDpt"] == "5.001" and
          pct["legacyDptToPreserve"] == "5.004" and
          pct["legacyObjects"] == [17, 24],
          "DPT5.001 != legacy 5.004 KO17..24")

    objects = p["proposedComObjects"]
    check(len(objects) == 65 and
          [o["number"] for o in objects] == list(range(36, 101)),
          "Proposed communication objects exactly KO36..100")
    fields = ("RoomSetpoint", "RoomActual",
              "DirectDemand", "RequestedOutput")
    dpts = ("9.001", "9.001", "5.001", "5.001")
    directions = ("rx", "rx", "rx", "tx")
    lengths = (2, 2, 1, 1)
    for zone in range(1, 9):
        for offset, suffix in enumerate(fields):
            entry = objects[(zone - 1) * 4 + offset]
            expected = {
                "number": 36 + (zone - 1) * 4 + offset,
                "name": f"Zone{zone}{suffix}",
                "zone": zone,
                "dpt": dpts[offset],
                "direction": directions[offset],
                "sizeBytes": lengths[offset]
            }
            check(all(entry.get(k) == v for k, v in expected.items()),
                  f"Zone{zone} {suffix} KO/DPT/size/direction contract")
    check(objects[32]["number"] == 68 and
          objects[-1]["number"] == 100,
          "KOs 68..100 reserved outside KNX024 RX parser")

    parameters = p["proposedParameters"]
    check(len(parameters) == 18 and
          [entry["number"] for entry in parameters] ==
          list(range(22, 40)),
          "P22..P39 parameter range exact")
    check([entry["name"] for entry in parameters[:8]] ==
          [f"Zone{n}Mode" for n in range(1, 9)],
          "P22..29 zone modes align with eight zones")
    check([entry["name"] for entry in parameters[8:16]] ==
          [f"Motor{n}Zone" for n in range(1, 9)],
          "P30..37 motor-zone IDs align with eight motors")
    check(parameters[16]["name"] ==
          "RoomTemperatureInputTimeoutSeconds" and
          parameters[17]["name"] ==
          "DirectDemandInputTimeoutSeconds",
          "P38/P39 freshness timeout contract")
    print("RESULT: exact KNX008 proposed V3 KO36..100/P22..39 ABI PASS")


def check_additive_source(rel: str, required: tuple[str, ...]) -> None:
    old = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{rel}"], cwd=ROOT).decode(
        "utf8").replace("\r\n", "\n").splitlines()
    new = (ROOT / rel).read_text(
        encoding="utf8").replace("\r\n", "\n").splitlines()
    added = []
    for opcode, _, _, lo, hi in difflib.SequenceMatcher(
            None, old, new, autojunk=False).get_opcodes():
        check(opcode in ("equal", "insert"),
              "No pre-existing source removal/replacement in " + rel)
        if opcode == "insert":
            added.extend(new[lo:hi])
    delta = "\n".join(added)
    for token in required:
        check(delta.count(token) == 1,
              f"Expected additive {rel} source: {token}")
    # New firmware additions and portable model must not invoke hardware.
    return delta


def main() -> int:
    for path in FROZEN:
        frozen_source(path)

    check_proposal(json.loads((ROOT / PROPOSAL).read_text(encoding="utf8")))

    additions = check_additive_source(
        "src/controller/main.cpp",
        ('#include "knx024_room_dpt_adapter.hpp"',
         "static_assert(Knx024::FirstRoomObject == 36"))
    additions += check_additive_source(
        "lib/common/room_control_runtime.hpp",
        ("const HeatingZone::Settings& settings() const",
         "const HeatingZone::Inputs& inputs() const"))

    header = (ROOT / "lib/common/knx024_room_dpt_adapter.hpp").read_text(
        encoding="utf8")
    required = (
        "constexpr uint16_t FirstRoomObject = 36",
        "constexpr uint16_t LastRoomObject = 67",
        "constexpr uint8_t ObjectsPerZone = 4",
        "GroupValueWrite",
        "frame.declaredDpt != expected",
        "raw == 0x7FFF",
        "HeatingZone::validRoomSetpoint",
        "HeatingZone::validRoomActual",
        "HeatingZone::rawScalingToPermille",
        "HeatingZone::permilleToRawScaling",
        "bool configurationDrift(",
        "Status::InvalidatedMalformedPayload",
        "Status::InvalidatedTemperature",
        "Status::IgnoredNotReceiveObject",
        "bool requestedOutput(",
    )
    for token in required:
        check(token in header, "Portable room adapter API: " + token)

    disallowed = re.compile(
        r"\b(?:pinMode|digitalWrite|analogWrite|gpio_put|gpio_init|"
        r"pwm_set_wrap|pwm_set_gpio_level|motorEnable|startMotor|"
        r"GroupObject\s*::\s*value|knx\s*\.\s*getGroupObject)\s*\(")
    check(not disallowed.search(additions + "\n" + header),
          "KNX024 additions contain no real motor, KNX or GPIO I/O")
    main = (ROOT / "src/controller/main.cpp").read_text(encoding="utf8")
    check("knx024_room_dpt_adapter.hpp" in main and
          "knxRoomInputs.receive" not in main and
          "knxRoomInputs.configure" not in main,
          "Actual firmware only compiles proposed parser; no live V3 KO binding")
    check("#if defined(ARDUINO)" in
          (ROOT / "lib/common/room_control_runtime.hpp").read_text(
              encoding="utf8"),
          "KNX023 ARDUINO motor hardlock remains present")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf8")
    check("| **KNX024** " in roadmap, "KNX024 ASH roadmap recorded")
    for stage in ("KNX009", "KNX016"):
        check(re.search(
            rf"(?m)^\| \*\*{stage}\*\*[^|]*\| "
            r"\*\*deferred, 2026-10-12\*\* \|", roadmap) is not None,
            f"{stage} real ETS6 import remains deferred")
    check(re.search(
        r"(?m)^\| \*\*KNX004\*\*[^|]*\| planned \|", roadmap) is not None,
          "Real motor safety KNX004 remains planned")

    print("RESULT: KNX024 source/ETS proposal ABI and no-actuation PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ContractError, KeyError, TypeError,
            subprocess.CalledProcessError) as exc:
        print("FAIL KNX024 contract:", exc, file=sys.stderr)
        raise SystemExit(2)
