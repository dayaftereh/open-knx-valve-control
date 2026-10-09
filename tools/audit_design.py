#!/usr/bin/env python3
"""Read-only checks for OpenKNX Valve Control V1.2.

Parses EasyEDA PCB JSON and KNX product XML using Python's standard library.
This is NOT electrical ERC, physical DRC, connectivity closure, or ETS import testing.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / "schematic" / "sch_knx-valve-control_v1.2.json"
PCB = ROOT / "schematic" / "pcb_knx-valve-control_v1.2.json"
ETS = ROOT / "assets" / "open-knx-valve-control.xml"

failures = 0


def report(ok: bool, description: str) -> None:
    global failures
    print(f"{'PASS' if ok else 'FAIL'}  {description}")
    if not ok:
        failures += 1


def warn(description: str) -> None:
    print(f"WARN  {description}")


def short_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def components(shapes: list[str]) -> dict[str, dict]:
    found = {}
    for record in shapes:
        if not record.startswith("LIB~"):
            continue
        chunks = record.split("#@$")
        ref = None
        for chunk in chunks:
            if chunk.startswith("TEXT~P~"):
                pieces = chunk.split("~")
                if len(pieces) > 10:
                    ref = pieces[10]
                    break
        if not ref:
            continue
        attrs = chunks[0].split("~")
        values = attrs[3].split("`") if len(attrs) > 3 else []
        info = dict(zip(values[::2], values[1::2]))
        pins = {}
        for chunk in chunks:
            if chunk.startswith("PAD~"):
                tokens = chunk.split("~")
                if len(tokens) > 8:
                    pins[tokens[8]] = tokens[7]
        found[ref] = {"pins": pins, "meta": info}
    return found


def main() -> int:
    pcb = json.loads(PCB.read_text(encoding="utf-8-sig"))
    schematic = json.loads(SCHEMATIC.read_text(encoding="utf-8-sig"))
    xml = ET.parse(ETS).getroot()
    shapes = pcb["shape"]
    parts = components(shapes)
    counts = Counter(shape.split("~", 1)[0] for shape in shapes)
    layers = {shape.split("~")[2] for shape in shapes if shape.startswith("TRACK~")}
    copper = layers.intersection({"1", "2", "21", "22"})
    report(len(schematic["schematics"]) == 1, "Main schematic JSON: one sheet")
    report(len(copper) == 4, "PCB layout uses top, bottom, and two inner copper layers")
    print(f"INFO  Layout data: {len(parts)} distinct displayed footprint names; {counts['TRACK']} tracks; {counts['VIA']} vias")
    drivers = {"U34": ("M1", "M2"), "U36": ("M3", "M4"),
               "U37": ("M5", "M6"), "U35": ("M7", "M8")}
    for ref, motors in drivers.items():
        pins = parts.get(ref, {}).get("pins", {})
        targets = {motor + sign for motor in motors for sign in ["+", "-"]}
        targets.update({motor + "_EN" for motor in motors})
        report(len(pins) == 24 and targets.issubset(set(pins.values()))
               and pins.get("19") == "3.3V",
               f"{ref}: two motor outputs, two PWM enables, STBY pin 19 high")
    rp = parts.get("U18", {}).get("pins", {})
    report(all(f"M{i}_EN" in rp.values() for i in range(1, 9))
           and "IN_1" in rp.values() and "IN_2" in rp.values(),
           "RP2040: all eight PWM enables and common direction lines")
    shunt = parts.get("R29", {}).get("pins", {})
    report(set(shunt.values()) == {"3.3V", "M_VCC"},
           "R29: shunt connects common 3.3V rail to M_VCC")
    ina = parts.get("U23", {}).get("pins", {})
    report(len(ina) == 8 and ina.get("3") == "SDA" and ina.get("4") == "SCL",
           "INA219: eight pads, I2C SDA/SCL")
    therm = parts.get("U25", {}).get("pins", {})
    report(len(therm) == 20 and all(f"T{i}" in therm.values() for i in range(9)),
           "ATtiny temperature section: nine local inputs T0-T8")
    hmi = parts.get("U29", {}).get("pins", {})
    report(len(hmi) == 16 and hmi.get("15") == "SDA" and hmi.get("14") == "SCL",
           "LCD PCF8574: shared I2C bus")
    objects = [e for e in xml.iter() if short_tag(e) == "ComObject"]
    params = [e for e in xml.iter() if short_tag(e) == "Parameter"]
    channels = [e for e in xml.iter() if short_tag(e) == "Channel"]
    report(len(objects) == 33 and len(params) == 19,
           "Existing ETS XML: 33 static communication objects, 19 parameters")
    report(len(channels) == 1, "Existing ETS XML: only one dynamic ETS channel")
    positions = [e for e in objects if e.get("Name", "").startswith(("Stell-Wert", "Stell_Wert"))]
    report(len(positions) == 8, "Existing ETS XML: eight position communication objects")
    if positions and {e.get("DatapointType") for e in positions} == {"DPST-5-4"}:
        warn("Stellwert currently DPST-5-4 (DPT 5.004), not DPT 5.001 scaling; define KNX conversion deliberately")
    else:
        warn("Stellwert DPTs differ from previously audited 5.004; inspect KNX application compatibility")
    warn("Shunt R29 metadata and U25 microcontroller metadata differ from schematic labels; inspect as-built parts")
    warn("Presence of PCB tracks and vias does not prove routing closure, physical DRC or power integrity")
    header = (ROOT / "include" / "knxprod.hpp").read_text(encoding="utf-8-sig")
    ko_names = [line.split()[1] for line in header.splitlines()
                if line.startswith("#define Ko") and len(line.split()) >= 2]
    invalid = [name for name in ko_names if not name.isidentifier()]
    if invalid:
        warn(f"Generated Ko-family header contains {len(invalid)} invalid C identifier spellings (e.g. {invalid[0]}); regenerate after renaming XML object identifiers")
    warn("OpenKNXproducer packaging and ETS6 import validation are separate gates")
    print(f"RESULT: {failures} invariant failures (manual hardware gates remain)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
