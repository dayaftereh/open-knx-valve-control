#!/usr/bin/env python3
"""KNX019: verify offline RoomPI integration cannot mutate installed KNX ABI.

Compares selected implementation files against immutable KNX008 gate4 HEAD,
and ensures KNX009/016 remain deferred pending KNX018 standalone testbench.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "025c84e"
UNCHANGED = [
    "assets/open-knx-valve-control.xml",
    "include/knxprod.hpp",
    "assets/knx008_zone_ets_proposal.json",
    "lib/common/heating_zone_model.hpp",
    "src/controller/main.cpp",
    "src/temperature/main.cpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_publisher.cpp",
]


def check(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)
    print("PASS:", label)


def base(rel: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{rel}"], cwd=ROOT)


def main() -> int:
    for rel in UNCHANGED:
        now = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        old = base(rel).replace(b"\r\n", b"\n")
        check(now == old, "unchanged KNX/ETS/firmware baseline: " + rel)

    code = (ROOT / "lib/common/room_pi_controller.hpp").read_text(
        encoding="utf8")
    check('#include "heating_zone_model.hpp"' in code,
          "ROOM PI consumes the KNX008 zone model")
    check("class Bank" in code and "class ZoneController" in code,
          "eight-zone regulator bank + stateful PI algorithm present")
    check("HeatingZone::Mode::RoomTemperature" in code and
          "Status::DirectBypass" in code,
          "room-regulator and direct-position modes remain distinct")
    check("sinceBarrier(" in code and "lastSettings_" in code and
          "directDpt5001Raw.valid = false" in code,
          "reconfiguration and source-recovery freshness fence present")
    include_lines = re.findall(
        r"(?m)^#include[ \t]+([<\"][^>\"]+[>\"])", code)
    check(set(include_lines) <= {
        '"heating_zone_model.hpp"', "<stdint.h>"
    }, "portable C++ core with no hardware/KNX stack dependencies")

    forbidden_ops = [
        "digitalWrite(", "analogWrite(", "pinMode(",
        "knx.getGroupObject(", "Serial1.", "Serial2.", "Wire.",
        "setPWM(", "motorEnable(",
    ]
    check(not any(op in code for op in forbidden_ops),
          "no actual GPIO/motor/KNX/serial calls in PI core")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf8")
    for slice_id in ("KNX009", "KNX016"):
        check(re.search(rf"(?m)^\| \*\*{slice_id}\*\*[^|]*\| "
                        r"\*\*deferred, 2026-10-12\*\* \|",
                        roadmap) is not None,
              slice_id + " ETS/live KNX still deferred")
    check("| **KNX018** " in roadmap,
          "independent hardware testbench KNX018 remains planned")
    check("| **KNX010** " in roadmap,
          "full room/KNX/motor integration KNX010 remains a separate slice")
    print("RESULT: KNX019 strictly offline and compatible with existing ETS v2")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(2)
