#!/usr/bin/env python3
"""KNX022 source-driven negative/guard tests. No physical I/O.

Tamper simulated in-memory copies ONLY. Never edits the canonical PCB,
schematic, firmware, or real measurement evidence.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_knx022_hw_preflight as hw


def rejection(sources: dict, label: str) -> None:
    try:
        hw.evaluate(sources)
    except hw.PreflightError:
        print("PASS EXPECTED BLOCK:", label)
        return
    raise AssertionError("FAIL TO DETECT HARDWARE DESIGN DRIFT: " + label)


def main() -> int:
    inputs = hw.load_sources()
    baseline = hw.evaluate(inputs)
    assert baseline["static_checks_passed"] >= 35
    assert baseline["hardware_readiness"] == \
           "BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR"
    assert baseline["physical_hardware_checks_performed"] == 0
    assert len(baseline["physical_evidence"]) >= 8
    assert all(v is None for v in baseline["physical_evidence"].values())
    assert baseline["drivers_stby_pad19_nets"] == {
        ref: "3.3V" for ref in ("U34", "U35", "U36", "U37")}
    assert baseline["known_metadata_conflicts"] == {
        "R29": True, "U25": True, "F1": True}
    assert len(baseline["findings"]) == 10
    assert baseline["blocker_count"] == 10
    assert len({f["id"] for f in baseline["findings"]}) == 10
    print("PASS KNX022 current real source inventory has 35+ invariants,"
          " no measurements and explicit BLOCKED verdict")

    def corrupt(action, name: str) -> None:
        test = deepcopy(inputs)
        action(test)
        rejection(test, name)

    corrupt(lambda s: s["parts"]["U34"]["pins"].__setitem__("19", "STBY"),
            "TB6612 STBY net changes from 3.3V")
    corrupt(lambda s: s["parts"]["U35"]["pins"].__setitem__("19", "GND"),
            "TB6612 STBY grounded (hardware design changed)")
    corrupt(lambda s: s["parts"]["R29"]["pins"].__setitem__("1", "5V"),
            "Shunt unexpectedly fed from 5V instead of 3.3V")
    corrupt(lambda s: s["parts"]["R29"]["pins"].__setitem__("2", "3.3V"),
            "Shared motor M_VCC shunt path missing")
    corrupt(lambda s: s["parts"]["D6"]["pins"].__setitem__("2", "5V"),
            "Schottky D6 USB_VCC net drift")
    corrupt(lambda s: s["parts"]["Q1"]["pins"].__setitem__("3", "KNX_VCC"),
            "Q1 source-selection node drift")
    corrupt(lambda s: s["parts"]["JMP1"]["pins"].__setitem__("2", "5V"),
            "JMP1 incorrectly assumed 5V source connector")
    corrupt(lambda s: s["parts"]["U6"]["pins"].__setitem__("1", "5V"),
            "U6 converter input path changed")
    corrupt(lambda s: s["parts"]["U23"]["pins"].__setitem__("8", "GND"),
            "INA219 input sense network changed")
    corrupt(lambda s: s["parts"]["U18"]["pins"].__setitem__("27", "3.3V"),
            "RP2040 motor seven enable net removed")
    corrupt(lambda s: s.__setitem__(
        "config", s["config"].replace("Drive7 = D16", "Drive7 = D17")),
        "RP2040 software motor pin map diverges")
    corrupt(lambda s: s.__setitem__(
        "attiny", s["attiny"].replace(
            "board = ATtiny3216", "board = ATtiny1616")),
        "ATtiny programmer target switches without board review")
    corrupt(lambda s: s["labels"]["R29"].__setitem__(
        "display", "1MOhm (1W)"),
        "Schematic shunt value no longer 200mOhm")
    corrupt(lambda s: s["labels"]["F1"].__setitem__(
        "display", "60 A"),
        "Schematic F1 value no longer 630mA")
    corrupt(lambda s: s.__setitem__(
        "main", s["main"] + "\npinMode(Pin::Drive1, OUTPUT);\n"),
        "RP2040 starts touching motor outputs; preflight needs redesign")

    # Repairing a BOM text field still CANNOT prove a populated chip/fuse.
    fixed = deepcopy(inputs)
    fixed["parts"]["U25"]["meta"]["Manufacturer Part"] = "ATTINY3216-SN"
    possible = hw.evaluate(fixed)
    assert possible["hardware_readiness"] == baseline["hardware_readiness"]
    assert possible["physical_hardware_checks_performed"] == 0
    assert not possible["known_metadata_conflicts"]["U25"]
    assert any(f["id"] == "U25_PART_METADATA" for f in possible["findings"])
    print("PASS correcting supplier metadata DOES NOT grant physical clearance")

    # Deterministic report across two independent parses and evaluations.
    assert hw.serialize(hw.evaluate(hw.load_sources())) == \
           hw.serialize(hw.evaluate(hw.load_sources()))
    print("RESULT: KNX022 15 negative guard tests and metadata/JSON"
          " determinism PASS; operating readiness remains BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
