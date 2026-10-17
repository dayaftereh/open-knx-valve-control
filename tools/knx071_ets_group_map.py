#!/usr/bin/env python3
"""Read-only KNX ETS .knxproj XML group-address inventory and optional TP1 annotation.

Reads only P-*/0.xml from ETS ZIP, never alters source KNX project or KNX network.
Outputs a lossless row per declared GroupAddress with GA, DPT, nested range labels,
links to ETS device ComObjects, and a separate device inventory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def localname(e: ET.Element) -> str:
    return e.tag.rsplit("}", 1)[-1]


def addr_text(value: int) -> str:
    return f"{value >> 11}/{(value >> 8) & 0x7}/{value & 0xFF}"


def device_inventory(root: ET.Element, parents: dict) -> tuple[list[dict], dict]:
    devices = []
    device_by_element = {}
    for el in root.iter():
        if localname(el) != "DeviceInstance":
            continue
        nodes = []
        node = parents.get(el)
        while node is not None:
            nodes.append(node)
            node = parents.get(node)
        area = next((n.get("Address") for n in nodes if localname(n) == "Area"), "?")
        line = next((n.get("Address") for n in nodes if localname(n) == "Line"), "?")
        num = el.get("Address")
        individual = f"{area}.{line}.{num}" if num is not None else ""
        d = {
            "id": el.get("Id", ""),
            "physical_address": individual,
            "name": el.get("Name", "") or "",
            "description": el.get("Description", "") or "",
            "product": el.get("ProductRefId", "") or "",
            "loaded": el.get("ApplicationProgramLoaded", ""),
            "last_download": el.get("LastDownload", ""),
        }
        devices.append(d)
        device_by_element[el] = d
    return devices, device_by_element


def read_ets(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as zin:
        candidates = [n for n in zin.namelist() if re.fullmatch(r"P-[0-9A-Fa-f]+/0\.xml", n)]
        if len(candidates) != 1:
            raise ValueError("Expected one ETS P-*/0.xml; found " + repr(candidates))
        root = ET.fromstring(zin.read(candidates[0]))
    parents = {c: p for p in root.iter() for c in p}
    devices, device_by_el = device_inventory(root, parents)
    links_by_ref: dict[str, list[dict]] = collections.defaultdict(list)
    all_link_tokens = collections.Counter()
    # GroupAddress refs live in <ComObjectInstanceRef Links="GA-14 GA-81">
    for d_el, device in device_by_el.items():
        for ref in d_el.iter():
            if localname(ref) != "ComObjectInstanceRef":
                continue
            text = ref.get("Links", "")
            for token in re.findall(r"\bGA-\d+\b", text):
                all_link_tokens[token] += 1
                links_by_ref[token].append({
                    "device": device["physical_address"],
                    "device_description": device["description"].strip(),
                    "com_object_ref": ref.get("RefId", ""),
                })
    rows = []
    for el in root.iter():
        if localname(el) != "GroupAddress":
            continue
        n = int(el.attrib["Address"])
        ancestors = []
        parent = parents.get(el)
        while parent is not None:
            if localname(parent) == "GroupRange":
                ancestors.append(parent.get("Name", "") or "")
            parent = parents.get(parent)
        ancestors.reverse()
        gid = el.get("Id", "")
        suffix = re.search(r"(GA-\d+)$", gid)
        token = suffix.group(1) if suffix else ""
        bindings = links_by_ref.get(token, [])
        devices_linked = sorted(set(
            f'{r["device"]} {r["device_description"]}'.strip() for r in bindings
        ))
        dpt_raw = el.get("DatapointType", "") or ""
        row = {
            "group_address": addr_text(n),
            "address_raw": n,
            "id": gid,
            "main": (ancestors + ["", "", ""])[0],
            "middle": (ancestors + ["", "", ""])[1],
            "ranges": " > ".join(ancestors),
            "name": el.get("Name", "") or "",
            "description": el.get("Description", "") or "",
            "dpt": dpt_raw.replace("DPST-", "DPT ").replace("-", "."),
            "dpt_id": dpt_raw,
            "link_count": len(bindings),
            "device_count": len(devices_linked),
            "linked_devices": " | ".join(devices_linked),
            "links": bindings,
        }
        rows.append(row)
    rows.sort(key=lambda r: int(r["address_raw"]))
    known_tokens = {re.search(r"(GA-\d+)$", r["id"]).group(1) for r in rows}
    unknown_tokens = sorted(set(all_link_tokens) - known_tokens)
    if unknown_tokens:
        raise ValueError("Unresolved ETS group address link tokens: " + repr(unknown_tokens[:20]))
    addrs = [r["address_raw"] for r in rows]
    if len(addrs) != len(set(addrs)):
        raise ValueError("Duplicate ETS group addresses")
    return {
        "source": str(path),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "project_xml": candidates[0],
        "total_groups": len(rows),
        "total_devices": len(devices),
        "assigned_com_links": sum(all_link_tokens.values()),
        "row_counts_per_main": dict(sorted(collections.Counter(int(r["address_raw"]) >> 11 for r in rows).items())),
        "groups": rows,
        "devices": devices,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--json", required=True, type=Path)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--devices-csv", type=Path)
    args = ap.parse_args()
    result = read_ets(args.project)
    for file in (args.csv, args.json, args.devices_csv):
        if file is not None:
            file.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cols = ["group_address", "address_raw", "main", "middle", "ranges", "name",
            "description", "dpt", "link_count", "device_count", "linked_devices", "id"]
    with args.csv.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=cols, delimiter=";")
        writer.writeheader()
        writer.writerows({k: row[k] for k in cols} for row in result["groups"])
    if args.devices_csv:
        cols2 = ["physical_address", "name", "description", "product", "loaded",
                 "last_download", "id"]
        with args.devices_csv.open("w", newline="", encoding="utf-8-sig") as fp:
            writer = csv.DictWriter(fp, fieldnames=cols2, delimiter=";")
            writer.writeheader()
            writer.writerows({k: d[k] for k in cols2} for d in result["devices"])
    print("ETS_MAP_COMPLETE", "GAs", result["total_groups"],
          "devices", result["total_devices"], "com_links", result["assigned_com_links"])
    print("SOURCE_SHA256", result["source_sha256"])
    for main in sorted(set(r["main"] for r in result["groups"])):
        arr = [r for r in result["groups"] if r["main"] == main]
        print("MAIN_GROUP", repr(main), len(arr), "WITH_COM_LINKS",
              sum(1 for r in arr if r["link_count"] > 0))
    print("UNLINKED_GAS", sum(1 for r in result["groups"] if r["link_count"] == 0))
    for name, file in (("CSV",args.csv),("DEVICES",args.devices_csv),("JSON",args.json)):
        if file:
            print("SAVED", name, str(file), file.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
