#!/usr/bin/env python3
"""KNX022 V1.2 hardware preflight: reproducible STATIC source evidence.

No serial port, KNX bus, USB interface, GPIO, programmer or other hardware is
accessed. A successful run means the evidence and known blockers were
consistently classified, NOT that the actual assembled board is safe.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_design import components

ROOT = Path(__file__).resolve().parents[1]
PCB_REL = "schematic/pcb_knx-valve-control_v1.2.json"
SCHEMATIC_REL = "schematic/sch_knx-valve-control_v1.2.json"
CONFIG_REL = "src/controller/config.hpp"
CONTROLLER_REL = "src/controller/main.cpp"
ATTINY_INI_REL = "src/temperature/temperature.ini"
FILES = (PCB_REL, SCHEMATIC_REL, CONFIG_REL, CONTROLLER_REL,
         ATTINY_INI_REL)


class PreflightError(ValueError):
    """Static evidence no longer matches the reviewed V1.2 baseline."""


def require(ok: bool, description: str) -> None:
    if not ok:
        raise PreflightError(description)


def schematic_labels(schematic: dict) -> dict[str, dict]:
    sheets = schematic.get("schematics", [])
    require(len(sheets) == 1, "Expected one main-board schematic sheet")
    shapes = sheets[0]["dataStr"]["shape"]
    result: dict[str, dict] = {}
    for shape in shapes:
        if not shape.startswith("LIB~"):
            continue
        labels = re.findall(r"~comment~([^~]+)~1~start", shape)
        if len(labels) < 2:
            continue
        # The second label is the designator (R29, U25, F1, etc.).
        ref = labels[1]
        if not re.fullmatch(r"[A-Za-z]+\d+", ref):
            continue
        result[ref] = {"display": labels[0], "reference": ref}
    return result


def load_sources(root: Path = ROOT) -> dict:
    pcb = json.loads((root / PCB_REL).read_text(encoding="utf-8-sig"))
    sch = json.loads((root / SCHEMATIC_REL).read_text(encoding="utf-8-sig"))
    return {
        "parts": components(pcb["shape"]),
        "labels": schematic_labels(sch),
        "config": (root / CONFIG_REL).read_text(encoding="utf8"),
        "main": (root / CONTROLLER_REL).read_text(encoding="utf8"),
        "attiny": (root / ATTINY_INI_REL).read_text(encoding="utf8"),
        "counts": {
            "pcb_lib_records": sum(s.startswith("LIB~") for s in pcb["shape"]),
            "schematic_lib_records": sum(
                s.startswith("LIB~") for s in
                sch["schematics"][0]["dataStr"]["shape"]),
            "pcb_track_records": sum(
                s.startswith("TRACK~") for s in pcb["shape"]),
            "pcb_via_records": sum(
                s.startswith("VIA~") for s in pcb["shape"]),
        },
    }


def pins(parts: dict, ref: str, expected: dict[str, str]) -> None:
    p = parts.get(ref)
    require(p is not None, f"Missing PCB reference {ref}")
    actual = p["pins"]
    for pad, net in expected.items():
        require(actual.get(pad) == net,
                f"{ref}.{pad}: expected net {net!r}, actual {actual.get(pad)!r}")


def require_firmware_pin(config: str, name: str, gpio: int) -> None:
    require(
        re.search(
            rf"(?m)\b{name}\s*=\s*D{gpio}\s*;", config) is not None,
        f"Firmware Pin::{name} no longer assigned to D{gpio}; "
        "stop and review as-built board pinout"
    )


def evaluate(sources: dict, root: Path = ROOT) -> dict:
    pcb = sources["parts"]
    labels = sources["labels"]
    controller = sources["config"]
    main = sources["main"]
    attiny_ini = sources["attiny"]
    check_names: list[str] = []

    def verified(ok: bool, reason: str) -> None:
        require(ok, reason)
        check_names.append(reason)

    driver_map = {
        "U34": ("M1", "M2"),
        "U36": ("M3", "M4"),
        "U37": ("M5", "M6"),
        "U35": ("M7", "M8"),
    }
    stby_map = {}
    for driver, motors in driver_map.items():
        actual = pcb.get(driver, {}).get("pins", {})
        verified(len(actual) == 24, driver + " has 24 TB6612 footprint pads")
        verified(actual.get("19") == "3.3V",
                 driver + " STBY pin 19 tied to logic 3.3V; NOT GPIO controlled")
        verified(all(f"{m}_EN" in actual.values() for m in motors),
                 driver + " has both distinct PWM enables")
        verified(all(f"{m}{sign}" in actual.values()
                     for m in motors for sign in ("+", "-")),
                 driver + " has both motor output pairs")
        verified({"IN_1", "IN_2"}.issubset(actual.values()),
                 driver + " uses shared direction nets")
        verified("M_VCC" in actual.values(),
                 driver + " VM supplied from common shunt rail")
        stby_map[driver] = actual["19"]

    rp = pcb.get("U18", {}).get("pins", {})
    verified(all(f"M{m}_EN" in rp.values() for m in range(1, 9)),
             "RP2040 exposes all eight M1_EN..M8_EN nets")
    verified({"IN_1", "IN_2"}.issubset(rp.values()),
             "RP2040 exposes only common IN_1/IN_2 direction")
    for m in range(1, 9):
        require_firmware_pin(controller, f"Drive{m}", 9 + m)
    for name, gpio in (("In1", 18), ("In2", 19)):
        require_firmware_pin(controller, name, gpio)
    check_names.append("RP2040 config.hpp D10..D17 and D18/D19 align with PCB nets")
    verified(
        re.search(r"\b(?:pinMode|digitalWrite|analogWrite|pwm_set_|motorEnable)\s*\(",
                  main) is None and
        re.search(r"Pin::(?:Drive[1-8]|In1|In2)\b", main) is None,
        "Current RP2040 main loop does not configure/drive motor pins")

    pins(pcb, "R29", {"1": "3.3V", "2": "M_VCC"})
    pins(pcb, "R33", {"1": "3.3V", "2": "U23_8"})
    pins(pcb, "R34", {"1": "M_VCC", "2": "U23_7"})
    pins(pcb, "U23", {"3": "SDA", "4": "SCL",
                      "7": "U23_7", "8": "U23_8",
                      "5": "3.3V", "6": "GND"})
    verified(True, "Shared R29/INA219 high-side measurement path matches V1.2")

    pins(pcb, "JMP1", {"1": "KNX_VCC", "2": "R9_2"})
    pins(pcb, "Q1", {"1": "USB_VCC", "2": "5V_",
                     "3": "R9_2"})
    pins(pcb, "D6", {"1": "5V_", "2": "USB_VCC"})
    pins(pcb, "F1", {"1": "5V_", "2": "5V"})
    pins(pcb, "D1", {"1": "D1_1", "2": "5V"})
    pins(pcb, "U6", {"1": "D1_1", "2": "GND", "3": "3.3V"})
    pins(pcb, "L1", {"1": "DCDC_LX", "2": "KNX_VCC"})
    verified(True, "USB/KNX selection and two Schottkys before 3.3V U6 recorded")

    verified(len(pcb.get("U25", {}).get("pins", {})) == 20 and
             {f"T{i}" for i in range(9)}.issubset(
                 set(pcb["U25"]["pins"].values())),
             "ATtiny U25 20-pad PCB component provides nine T0..T8 inputs")

    for ref in ("R29", "U25", "F1"):
        require(ref in labels, "Missing schematic nominal annotation " + ref)
        require(ref in pcb, "Missing PCB footprint metadata " + ref)
    verified(labels["R29"]["display"].startswith("200m"),
             "R29 schematic nominal value reads 200mOhm")
    verified(labels["U25"]["display"].upper() == "ATTINY3216",
             "U25 schematic symbol reads ATTINY3216")
    verified("630mA" in labels["F1"]["display"],
             "F1 schematic nominal current reads 630mA")
    verified(re.search(r"(?m)^\s*board\s*=\s*ATtiny3216\s*$",
                       attiny_ini) is not None,
             "PlatformIO ATtiny board target is ATtiny3216")

    # Detect stale supplier metadata but never let a corrected BOM field
    # stand in for proof of what was physically soldered.
    metadata = {ref: pcb[ref]["meta"].get("Manufacturer Part", "")
                for ref in ("R29", "U25", "F1")}
    conflicts = {
        "R29": metadata["R29"].strip().upper() == "SCR1206F1M1",
        "U25": metadata["U25"].strip().upper() == "ATTINY1616-SN",
        "F1": metadata["F1"].strip().upper() == "S1032-F-60.0A",
    }

    # A read-only repository inventory is NOT a manufacturer's DRC result.
    pcb_dir = root / "schematic"
    drc_files = sorted(p.name for p in pcb_dir.iterdir()
                       if p.is_file() and (
                           "drc" in p.name.lower() or
                           "erc" in p.name.lower() or
                           "bom" in p.name.lower()))
    physical_evidence = {
        "populated_r29_measured_mohm": None,
        "populated_u25_marking": None,
        "populated_f1_marking": None,
        "jmp1_open_or_closed": None,
        "power_source_and_backfeed_measurement": None,
        "u6_pin1_minimum_voltage_under_load": None,
        "reset_and_brownout_motor_output_measurement": None,
        "one_motor_current_curve_and_reference": None,
        "manufacturer_erc_drc_and_pcb_bom": None,
    }

    finding_specs = [
        ("R29_PART_METADATA", "P0",
         "Schematic R29 = 200mOhm / 1W; PCB manufacturer part = "
         + metadata["R29"] + "."
         + (" Conflicting source metadata." if conflicts["R29"]
            else " Supplier field differs from known unverified baseline."),
         "Measure/identify installed R29, confirm assembly BOM and calibrate INA219."),
        ("U25_PART_METADATA", "P0",
         "Schematic+firmware ATtiny3216; PCB supplier part = " + metadata["U25"]
         + (" (mismatch)." if conflicts["U25"] else " (unverified installed device)."),
         "Read real IC marking and UPDI signature before flashing."),
        ("F1_PART_METADATA", "P0",
         "Schematic F1 = " + labels["F1"]["display"] + "; PCB part = "
         + metadata["F1"] + ".",
         "Confirm actual fuse marking, current/time characteristic and voltage rating."),
        ("TB6612_STBY_TIED_HIGH", "P0",
         "U34/U36/U37/U35 pin19 STBY all directly on 3.3V. There is NO"
         " independent RP2040-controlled global TB6612 standby shutdown.",
         "Define/test independent hardware all-off and safe boot/brownout logic"
         " before any motor operation; revise PCB if required."),
        ("U6_TWO_DIODE_HEADROOM", "P0",
         "PCB USB_VCC -> D6 -> F1 -> D1 -> U6 VIN -> 3.3V."
         " U6 min VIN 4.75V; margin with two Schottkys is unmeasured.",
         "Measure U6 VIN/3.3V under no-motor KNX-only and USB-only load."),
        ("KNX_USB_SOURCE_BACKFEED", "P0",
         "JMP1 links KNX_VCC to R9_2, Q1 selects source on USB_VCC/5V_."
         " JMP1 is NOT an external 5-V input. Source isolation and backfeed"
         " have no actual measurement.",
         "Qualify source ORing/backfeed, isolation and a protected supply entry"
         " design before applying any external 5V."),
        ("STKNX_POWER_BUDGET", "P0",
         "STKNX bus-side draw and buck load budget have not been measured"
         " with RP2040, LCD, ATtiny and one 3.3V HmIP-VDMOT.",
         "Record KNX extraction/load and worst-case 3.3V supply behavior."),
        ("MOTOR_OUTPUT_BOOT_UNKNOWN", "P0",
         "Controller main.cpp has no motor-specific GPIO initialization or"
         " verified boot/brownout all-off sequence.",
         "Specify independent output default-low and watchdog/stop mechanism;"
         " qualify on safe bench before connecting an actuator."),
        ("SHARED_INA219_AND_DIRECTION", "P1",
         "Exactly one R29/INA219 motor-current channel and shared IN_1/IN_2"
         " for all four dual drivers; no per-motor independent measurement.",
         "Single-motor arbitration and motor-specific reference/current"
         " tests remain mandatory (KNX004/005/006)."),
        ("EASYEDA_MANUFACTURING_GATE", "P0",
         "Only design JSON/PDF exports found; native EasyEDA electrical ERC,"
         " PCB DRC, approved assembly BOM and physical PCB-to-design proof absent."
         " Additional similarly named files: " + repr(drc_files) + ".",
         "Export valid board revision BOM, manufacturing/netlist evidence and"
         " actual native ERC/DRC; reconcile with the populated PCB."),
    ]
    findings = [
        {"id":code, "priority":priority, "status":"BLOCKED_UNTIL_EVIDENCE",
         "source_observation":observation, "required_action":action}
        for code,priority,observation,action in finding_specs
    ]

    hashes = {
        rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
        for rel in FILES
    }
    return {
        "schema": "openknxvalve.knx022.static-readiness.v1",
        "design_revision": "V1.2",
        "basis": "Repository sources only; populated board not inspected",
        "verified_baseline_git": "4d12890",
        "hardware_readiness": "BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR",
        "static_evidence_parsing": "PASS",
        "physical_hardware_checks_performed": 0,
        "static_checks_passed": len(check_names),
        "static_checks": check_names,
        "pcb_inventory": sources["counts"],
        "drivers_stby_pad19_nets": stby_map,
        "supplier_part_metadata": metadata,
        "known_metadata_conflicts": conflicts,
        "physical_evidence": physical_evidence,
        "blocker_count": len(findings),
        "findings": findings,
        "input_sha256": hashes,
        "limits": [
            "Not EasyEDA native ERC, PCB DRC, copper-connectivity proof or BOM approval.",
            "Not proof of physical IC type, shunt value, fuse rating, voltage or motor behavior.",
            "Simulator KNX020/021 lease/AllOff ACK is NOT an electrical shutdown.",
            "Motor output supply remains 3.3V; never apply external 5V to M_VCC.",
        ],
    }


def serialize(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False,
                      sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", type=Path, default=None)
    parser.add_argument("--check-report", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = evaluate(load_sources())
        actual = serialize(result)
        if args.write_report:
            args.write_report.write_text(
                actual, encoding="utf8", newline="\n")
            print("WROTE", args.write_report)
        if args.check_report:
            expected = args.check_report.read_text(encoding="utf8")
            require(actual == expected,
                    "Versioned hardware-readiness report is stale: regenerate")
            print("PASS Report reproducible:", args.check_report)
        print("PASS", result["static_checks_passed"],
              "PCB + schematic + firmware static invariants")
        print("BLOCKED:", result["hardware_readiness"])
        print("BLOCKER REGISTER:", result["blocker_count"],
              "tracked findings with hardware actions")
        for finding in result["findings"]:
            print(f"  {finding['priority']} {finding['id']}")
        return 0   # Source-audit pass, NOT a physical operating clearance.
    except (PreflightError, OSError, KeyError, ValueError) as exc:
        print("FAIL static evidence audit:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
