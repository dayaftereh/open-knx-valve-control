#!/usr/bin/env python3
"""KNX015 ETS product-data preservation audit (offline, no ETS import).

Compare original app schema at KNX014 HEAD e2e54c6 with current XML:
KO1..33 retain NUMBER/ID/DPT/FLAGS/TEXT; old 19 parameter layouts fixed.
Only C identifier Name fields are normalized. App version 2, append
parameters P20/P21 at offsets 7/9 and diagnostics KO34/35. Validate
producer normalized header if the user passes --header or canonical default.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]
NS = "{http://knx.org/xml/project/20}"


def elements(xml: bytes, kind: str):
    return list(ET.fromstring(xml).iter(NS + kind))


def demand(test: bool, why: str):
    if not test:
        raise AssertionError(why)


def baseline_file() -> bytes:
    return subprocess.check_output(
        ["git", "show", "e2e54c6:assets/open-knx-valve-control.xml"],
        cwd=ROOT,
    )


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--header", type=Path, default=ROOT/"include/knxprod.hpp")
    cli.add_argument("--knxprod", type=Path, help="optional generated ETS container ZIP for CRC, version and KO count audit")
    args = cli.parse_args()
    old = baseline_file()
    new = (ROOT/"assets/open-knx-valve-control.xml").read_bytes()

    old_kos = elements(old, "ComObject")
    kos = elements(new, "ComObject")
    demand(len(old_kos)==33 and len(kos)==35,"KO count 33 -> 35")
    for i in range(33):
        legacy = dict(old_kos[i].attrib)
        current = dict(kos[i].attrib)
        old_name = legacy.pop("Name")
        new_name = current.pop("Name")
        demand(current == legacy, f"KO {i+1} metadata/number/DPT changed")
        expected = re.sub(r"[^A-Za-z0-9_]+", "_", old_name).strip("_")
        demand(new_name == expected, f"KO {i+1} name mapping changed")

    old_params = elements(old,"Parameter")
    params = elements(new,"Parameter")
    demand(len(old_params)==19 and len(params)==21,"parameter count")
    def structural(e):
        # Ignore XML pretty-print whitespace in tail; retain all attributes,
        # element text and nested memory offsets/bit positions.
        return (e.tag, tuple(sorted(e.attrib.items())),
                (e.text or "").strip(),
                tuple(structural(c) for c in e))
    for i in range(19):
        demand(structural(old_params[i]) == structural(params[i]),
               f"Existing parameter P{i+1} modified")

    old_paramrefs = elements(old,"ParameterRef")
    refs = elements(new,"ParameterRef")
    demand(len(refs)==21,"parameter ref count")
    for i in range(19):
        demand(refs[i].attrib==old_paramrefs[i].attrib,
               f"Old parameter ref {i+1} modified")
    for name, refid, addr, typ, default in [
        ("TemperatureSendIntervalSeconds", "%AID%_P-20", "7",
         "%AID%_PT-TemperatureSendIntervalSeconds", "60"),
        ("TemperatureChangeThresholdCenti", "%AID%_P-21", "9",
         "%AID%_PT-TemperatureChangeThresholdCenti", "50"),
    ]:
        found=[e for e in params if e.get("Name")==name]
        demand(len(found)==1, f"Missing {name}")
        e=found[0]
        demand(e.get("Id")==refid and e.get("ParameterType")==typ and
               e.get("Value")==default,f"{name} metadata")
        memory=e.find(NS+"Memory")
        demand(memory is not None and memory.get("Offset")==addr and
               memory.get("BitOffset")=="0",f"{name} memory overlap")

    ids=[e.get("Number") for e in kos]
    demand(ids==list(map(str,range(1,36))),"KO numbering/order must be 1..35")
    demand(all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",e.get("Name",""))
               for e in kos),"Invalid C identifier in ComObject.Name")
    demand(len({e.get("Name") for e in kos})==35,"non-unique KO names")
    for num, name, dpt, size in [
        (34,"TemperatureBridgeOnline","DPST-1-2","1 Bit"),
        (35,"TemperatureValidMask","DPST-7-1","2 Bytes"),
    ]:
        e=kos[num-1]
        demand(e.get("Name")==name and e.get("DatapointType")==dpt and
               e.get("ObjectSize")==size, f"New KO {num} ABI invalid")
    program=elements(new,"ApplicationProgram")[0]
    demand(program.get("ApplicationVersion")=="2","app version unchanged")

    dynamic=elements(new,"Dynamic")[0]
    dynamic_xml=ET.tostring(dynamic,encoding="unicode")
    for name in ("%AID%_P-20_R-20","%AID%_P-21_R-21",
                 "%AID%_O-34_R-34","%AID%_O-35_R-35"):
        demand(name in dynamic_xml, "New ETS setting/KO not exposed: "+name)
    demand("%AID%_P-19_R-19" in dynamic_xml,"P19 gating missing")

    header=args.header
    demand(header.is_file(),"No generated KNX header: "+str(header))
    source=header.read_text(encoding="utf-8")
    numbers=dict(re.findall(r"^#define[ \t]+(Ko[A-Za-z0-9_]+)[ \t]+(\d+)[ \t]*$",
                            source, flags=re.M))
    demand(len(numbers)==35,"Header does not have 35 unique numeric KOs")
    for i,e in enumerate(kos,1):
        demand(numbers.get("Ko"+e.get("Name"))==str(i),
               f"Header index mismatch at KO{i}")
        demand(("Ko"+e.get("Name")+"Object") in source,
               f"Header accessor missing at KO{i}")
    for name, offset in (
        ("TemperatureSendIntervalSeconds",7),
        ("TemperatureChangeThresholdCenti",9)):
        demand(re.search(r"^#define[ \t]+"+name+r"[ \t]+"+str(offset)+r"[ \t]",
                         source,re.M)!=None,
               "Header parameter offset mismatch: "+name)
    definitions=re.findall(r"^#define[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]+",
                           source,flags=re.M)
    demand(len(definitions)==len(set(definitions)),
           "Header contains duplicate object-like macros")
    print("PASS: KO1..KO33, P1..P19 fully preserved")
    print("PASS: app version 2, 35 numbered KOs, two diagnostic KOs")
    print("PASS: 21 ETS parameters, new P20/P21 offsets 7 and 9")
    print("PASS: producer header 35 KO identifiers/accessors; no duplicate macros")

    if args.knxprod:
        try:
            with ZipFile(args.knxprod) as package:
                demand(package.testzip() is None,
                       "Generated .knxprod ZIP has corrupt contents")
                files=[name for name in package.namelist()
                       if name.endswith(".xml") and "_A-" in name]
                demand(len(files)==1,"Generated package app XML missing/ambiguous")
                inside=package.read(files[0])
                demand(len(elements(inside,"ComObject"))==35,
                       "Packaged product has wrong KO count")
                demand(len(elements(inside,"Parameter"))==21,
                       "Packaged product has wrong ETS parameter count")
                app=elements(inside,"ApplicationProgram")
                demand(len(app)==1 and app[0].get("ApplicationVersion")=="2",
                       "Packaged app version != 2")
                print("PASS: generated .knxprod ZIP CRC, app version 2, KO35/P21")
        except (OSError, BadZipFile) as exc:
            raise AssertionError("Unable to inspect generated .knxprod: "+str(exc))
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ET.ParseError) as exc:
        print("FAIL:",exc,file=sys.stderr)
        raise SystemExit(2)
