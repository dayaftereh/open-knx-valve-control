#!/usr/bin/env python3
"""Audit *proposed-only* KNX008 ETS ABI against actual unchanged KNX015 XML.

No product file is generated or imported; an invalid contract fails loudly.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "assets" / "knx008_zone_ets_proposal.json"
XML_FILE = "assets/open-knx-valve-control.xml"
HEADER_FILE = "include/knxprod.hpp"
BASELINE = "c171d17"
KNX_NS = "{http://knx.org/xml/project/20}"
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def unchanged(path: str) -> bytes:
    source = (ROOT / path).read_bytes()
    baseline = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
    # Git checkout on Windows may map canonical LF -> CRLF.
    require(source.replace(b"\r\n", b"\n") == baseline.replace(b"\r\n", b"\n"),
            f"{path} changed; KNX008 is PROPOSAL-ONLY")
    return source


def main() -> int:
    doc = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    require(doc.get("status") == "PROPOSAL_ONLY__NOT_IN_ETS_XML_OR_FIRMWARE",
            "Do not mark KNX008 as deployed")
    require(doc.get("schema") == "openknxvalve.knx008.zone-proposal.v1",
            "Unexpected proposal schema")
    require(doc.get("baseline", {}).get("verifiedGitHead") == BASELINE,
            "Wrong KNX008 baseline")
    xml = unchanged(XML_FILE)
    unchanged(HEADER_FILE)
    app = ET.fromstring(xml)
    apps = list(app.iter(KNX_NS + "ApplicationProgram"))
    kos = list(app.iter(KNX_NS + "ComObject"))
    params = list(app.iter(KNX_NS + "Parameter"))
    types = list(app.iter(KNX_NS + "ParameterType"))
    require(len(apps) == 1 and apps[0].get("ApplicationVersion") == "2",
            "Existing APP version changed without ETS gate")
    require(len(kos) == 35 and len(params) == 21, "Existing product ABI changed")
    require([int(e.get("Number")) for e in kos] == list(range(1, 36)),
            "Existing KO ordering changed")
    base = doc["baseline"]
    require(base["existingApplicationVersion"] == 2 and
            base["proposedApplicationVersion"] == 3 and
            base["existingCommunicationObjects"] == 35 and
            base["existingParameters"] == 21, "Incorrect product migration metadata")
    limits = doc["limits"]
    require(limits["motorCount"] == limits["zoneCount"] == 8 and
            limits["physicalMotorConcurrency"] == 1, "Zone/motor count or safety token")
    dpt_old = {int(e.get("Number")): e.get("DatapointType") for e in kos}
    require(all(dpt_old[i] == "DPST-5-4" for i in range(17, 25)),
            "Legacy Stell-Wert DPT5.004 changed")

    objects = doc["proposedComObjects"]
    require(len(objects) == 65, "Expected 65 appended zone/channel/status objects")
    require([o["number"] for o in objects] == list(range(36, 101)),
            "Proposal KO IDs must be a unique contiguous 36..100")
    names = [o["name"] for o in objects]
    old_names = [o.get("Name") for o in kos]
    require(len(set(names)) == 65 and
            not set(names).intersection(old_names) and
            all(IDENTIFIER.fullmatch(n) for n in names),
            "Proposal C identifiers collide or are invalid")

    lookup = {o["number"]: o for o in objects}
    for z in range(1, 9):
        n = 36 + 4 * (z - 1)
        expected = [
            (f"Zone{z}RoomSetpoint", "9.001", "rx"),
            (f"Zone{z}RoomActual", "9.001", "rx"),
            (f"Zone{z}DirectDemand", "5.001", "rx"),
            (f"Zone{z}RequestedOutput", "5.001", "tx"),
        ]
        for delta, (name, dpt, direction) in enumerate(expected):
            ko = lookup[n + delta]
            require(ko["name"] == name and ko["dpt"] == dpt and
                    ko["direction"] == direction and ko["zone"] == z,
                    f"Invalid zone {z} KO contract {n+delta}")
    for motor in range(1, 9):
        for n, suffix, dpt in [
            (68, "EstimatedPosition", "5.001"),
            (76, "Fault", "1.005"),
            (84, "Referenced", "1.002"),
            (92, "Moving", "1.001"),
        ]:
            ko = lookup[n + motor - 1]
            require(ko["name"] == f"Motor{motor}{suffix}" and
                    ko["dpt"] == dpt and ko["direction"] == "tx" and
                    ko["motor"] == motor, "Motor KO contract mismatch")
    require(lookup[100]["name"] == "DeviceMotionBusy" and
            lookup[100]["dpt"] == "1.002" and
            lookup[100]["direction"] == "tx",
            "Shared motor scheduler busy object is wrong")

    # Existing memory allocations are expressed as bit addresses; reject
    # collisions, including bits packed into byte4 and byte5.
    type_bits = {}
    for t in types:
        children = list(t)
        require(len(children) == 1, f"Unexpected ETS type layout: {t.get('Id')}")
        attr_size = children[0].get("SizeInBit")
        # KNX TypeFloat IEEE754 Single has implicit 32-bit storage.
        if attr_size is None and children[0].tag.endswith("TypeFloat"):
            attr_size = "32"
        require(attr_size is not None, "Unrecognized ETS parameter type size")
        type_bits[t.get("Id")] = int(attr_size)
    occupied: set[int] = set()
    for p in params:
        memory = p.find(KNX_NS + "Memory")
        require(memory is not None, "Baseline ETS parameter lacks memory")
        start = int(memory.get("Offset")) * 8 + int(memory.get("BitOffset"))
        count = type_bits[p.get("ParameterType")]
        for bit in range(start, start + count):
            require(bit not in occupied,
                    f"Current ETS parameters overlap at bit {bit}")
            occupied.add(bit)

    planned = doc["proposedParameters"]
    require(len(planned) == 18 and
            [p["number"] for p in planned] == list(range(22, 40)),
            "Proposal param IDs must be P22..P39")
    for p in planned:
        require(IDENTIFIER.fullmatch(p["name"]), "Invalid proposed parameter name")
        bits = p["sizeBits"]
        require(bits in (8, 16), "Unexpected proposed storage size")
        start = p["memoryByteOffset"] * 8
        for bit in range(start, start + bits):
            require(bit not in occupied,
                    f"Proposed parameter overlaps old/new bit {bit}")
            occupied.add(bit)
        if p["type"] == "unsignedInt":
            require(p["min"] <= p["default"] <= p["max"], "Bad ETS numeric default")
        if p["type"] == "enum":
            require(p["default"] in [v["value"] for v in p["allowed"]],
                    "Invalid enum default")
    require([p["name"] for p in planned[:8]] ==
            [f"Zone{z}Mode" for z in range(1, 9)],
            "Zone mode parameters mismatched")
    require(all(p["default"] == 0 for p in planned[:16]),
            "Zone/motor assignments must default to OFF/UNASSIGNED")
    require([p["name"] for p in planned[8:16]] ==
            [f"Motor{m}Zone" for m in range(1, 9)],
            "Channel zone assignments mismatched")
    require(planned[16]["name"] == "RoomTemperatureInputTimeoutSeconds" and
            planned[17]["name"] == "DirectDemandInputTimeoutSeconds" and
            planned[16]["default"] == 900 and planned[17]["default"] == 300,
            "Input freshness defaults inconsistent")
    require(max(occupied) <= (30 * 8 + 7), "ETS memory usage beyond proposed extent")
    # Verify after existing 11 occupied bytes, new allocations run 11..30.
    require(planned[0]["memoryByteOffset"] == 11 and
            planned[-1]["memoryByteOffset"] == 29,
            "Proposed ETS parameter byte offsets not as reviewed")

    require(doc["percentage"]["canonicalDpt"] == "5.001" and
            doc["percentage"]["legacyDptToPreserve"] == "5.004",
            "DPT 5.004 vs 5.001 migration decision lost")
    print("PASS: existing XML KO1..35 and P1..21 unchanged since KNX017")
    print("PASS: proposed KO36..100 C-safe unique names, DPT and directions")
    print("PASS: proposed P22..39 ETS settings, defaults and bit allocations")
    print("PASS: hardware limits 8 motors, 8 zones, one movement at a time")
    print("PASS: proposed-only AppVersion3, no KNX009/016 product mutation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, ET.ParseError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        raise SystemExit(2)
