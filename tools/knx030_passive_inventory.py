#!/usr/bin/env python3
"""KNX030: passive, local-only Windows PnP evidence for KNX018 first contact.

Actions:
  plan             Print the conservative inspection contract; no subprocess.
  capture --output NEW.json --label disconnected
                   Read OS PnP/volume/local-network metadata; never touch a
                   COM port, KNX/IP gateway, USB volume contents, or MCU.
  compare --before A.json --after B.json
                   Offline comparison; no OS/API/process calls of any kind.

All candidates remain unverified; nothing may authorize flashing or motors.
Hardware serial/instance identifiers are SHA256-hashed, not written raw.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tools" / "knx030_passive_inventory_probe.ps1"
SCHEMA = "openknx-valvecontrol/knx030-passive-os-inventory-v1"
VIDPID = re.compile(r"VID_([0-9a-fA-F]{4})&PID_([0-9a-fA-F]{4})")
COM = re.compile(r"\bCOM[0-9]{1,4}\b", re.IGNORECASE)
LABEL = re.compile(r"[A-Za-z0-9_-]{1,40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
GATES = (
    "board_electrically_verified",
    "physical_mcu_identity_verified",
    "usb_flash_authorized",
    "updi_flash_authorized",
    "knx_gateway_verified",
    "knx_telegram_authorized",
    "motor_enable_authorized",
)


class InventoryError(RuntimeError):
    pass


def text(value: Any, limit: int = 120) -> str:
    """Bound output size and suppress untrusted control characters."""
    return "".join(ch if ch.isprintable() else " " for ch in
                   str(value or ""))[:limit].strip()


def ensure_array(raw: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = raw.get(field)
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise InventoryError(f"Windows probe did not supply an array for {field}")
    return value


def normalize(raw: dict[str, Any], label: str,
              observed_utc: str | None = None) -> dict[str, Any]:
    if raw.get("source_kind") != "local_os_metadata_only":
        raise InventoryError("Unrecognized source: refusing untrusted device evidence")
    if LABEL.fullmatch(label) is None:
        raise InventoryError("Invalid label: only A-Z a-z 0-9 underscore and dash")
    devices: dict[str, dict[str, Any]] = {}
    for item in ensure_array(raw, "usb_and_ports"):
        raw_id = str(item.get("instance_id", "")).strip()
        if not raw_id:
            raise InventoryError("PnP instance has no ID; evidence incomplete")
        token = hashlib.sha256(raw_id.upper().encode("utf-8")).hexdigest()
        match = VIDPID.search(raw_id.upper())
        vendor_product = (match.group(1).upper() + ":" + match.group(2).upper()
                          if match else None)
        description = text(item.get("display_name"))
        com = COM.search(description)
        # These are OS hints, NOT physical board identity or wiring evidence.
        hint = ("rp2040_vendor_candidate" if vendor_product and
                vendor_product.startswith("2E8A:") else
                "usb_serial_candidate" if (com or (vendor_product and
                vendor_product.startswith(("1A86:", "0403:", "03EB:")))) else
                "other_present_usb_or_port")
        devices[token] = {
            "instance_sha256": token,
            "vid_pid": vendor_product,
            "com_port": com.group(0).upper() if com else None,
            "friendly_name": description,
            "pnp_class": text(item.get("class_name"), 50),
            "os_status": text(item.get("status"), 45),
            "candidate_hint": hint,
        }
    volumes = {}
    for item in ensure_array(raw, "rp2_volumes"):
        name = text(item.get("label"), 40)
        if name != "RPI-RP2":
            raise InventoryError("Unexpected volume label from narrow probe")
        drive = text(item.get("drive_letter"), 3).upper()
        if drive and not re.fullmatch(r"[A-Z]", drive):
            raise InventoryError("Malformed local drive letter")
        identity = f"RPI-RP2:{drive}"
        volumes[identity] = {
            "label": "RPI-RP2",
            "drive_letter": drive or None,
            "file_system": text(item.get("file_system"), 40),
            "classification": "bootsel_volume_candidate_only",
        }
    adapters = {}
    for item in ensure_array(raw, "local_network_adapters"):
        name = text(item.get("name"), 90)
        if not name:
            raise InventoryError("Local network adapter missing name")
        adapters[name] = {
            "name": name,
            "description": text(item.get("description"), 120),
            "os_link_status": text(item.get("status"), 30),
            "classification": "local_link_only_not_knx_ip",
        }
    return {
        "schema": SCHEMA,
        "source_kind": "local_os_metadata_only",
        "label": label,
        "observed_utc": observed_utc or datetime.now(timezone.utc).isoformat(),
        "devices": sorted(devices.values(), key=lambda x: x["instance_sha256"]),
        "rp2_volumes": sorted(volumes.values(), key=lambda x: (x["drive_letter"] or "")),
        "local_network_adapters": sorted(adapters.values(), key=lambda x: x["name"]),
        "hardware_release_gates": {key: False for key in GATES},
        "interpretation": (
            "Only Windows OS metadata. Candidate hints do not confirm OpenKNX "
            "hardware, KNX/IP endpoints, a safe power path or flash permission."),
    }


def validate(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise InventoryError("Not a KNX030 inventory snapshot")
    if snapshot.get("source_kind") != "local_os_metadata_only":
        raise InventoryError("Inventory is not sourced from passive local OS metadata")
    gates = snapshot.get("hardware_release_gates")
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        raise InventoryError("Unrecognized physical release gates")
    if any(value is not False for value in gates.values()):
        raise InventoryError("Inventory cannot claim hardware authorization")
    if LABEL.fullmatch(str(snapshot.get("label", ""))) is None:
        raise InventoryError("Snapshot has invalid label")
    for name in ("devices", "rp2_volumes", "local_network_adapters"):
        if not isinstance(snapshot.get(name), list):
            raise InventoryError("Missing collection " + name)
    ids: set[str] = set()
    for d in snapshot["devices"]:
        if (not isinstance(d, dict) or
                not isinstance(d.get("instance_sha256"), str) or
                HEX64.fullmatch(d["instance_sha256"]) is None or
                "instance_id" in d or "serial_number" in d):
            raise InventoryError("Device list contains raw or malformed instance ID")
        if d["instance_sha256"] in ids:
            raise InventoryError("Duplicate instance evidence")
        ids.add(d["instance_sha256"])
    return snapshot


def require_external_new_file(path_str: str, root: Path = ROOT) -> Path:
    if not path_str.strip():
        raise InventoryError("Output filename must be specified")
    target = Path(path_str).resolve()
    repo = root.resolve()
    if target == repo or repo in target.parents:
        raise InventoryError("Snapshot must be OUTSIDE the Git source tree")
    if target.exists():
        raise InventoryError("Refusing to overwrite an existing snapshot")
    if target.suffix.lower() != ".json":
        raise InventoryError("Snapshot filename must end in .json")
    return target


def collect(*, runner: Any = subprocess.run, powershell: str | None = None,
            probe: Path = PROBE) -> dict[str, Any]:
    powershell = powershell or shutil.which("powershell.exe")
    if not powershell or not probe.is_file():
        raise InventoryError("Missing Windows PowerShell or fixed passive probe")
    args = [powershell, "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-File", str(probe)]
    proc = runner(args, cwd=str(ROOT), text=True, capture_output=True,
                  encoding="utf-8", errors="strict", check=False, timeout=40)
    if proc.returncode != 0:
        raise InventoryError("Local OS enumeration failed: no snapshot captured")
    try:
        response = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise InventoryError("Invalid JSON from passive Windows probe") from exc
    if not isinstance(response, dict):
        raise InventoryError("Malformed Windows PnP evidence")
    return response


def capture(destination: str, label: str, *, root: Path = ROOT,
            runner: Any = subprocess.run,
            powershell: str | None = None, probe: Path = PROBE) -> dict[str, Any]:
    target = require_external_new_file(destination, root)
    collected = collect(runner=runner, powershell=powershell, probe=probe)
    result = validate(normalize(collected, label))
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create: if another process created the path, NEVER overwrite.
    try:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise InventoryError("Output appeared meanwhile; no overwrite") from exc
    return result


def read_snapshot(path: str) -> dict[str, Any]:
    try:
        with Path(path).open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, ValueError) as exc:
        raise InventoryError("Cannot load a valid inventory snapshot") from exc
    return validate(payload)


def _devices_by_hash(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["instance_sha256"]: d for d in snapshot["devices"]}


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    validate(before)
    validate(after)
    prior = _devices_by_hash(before)
    latest = _devices_by_hash(after)
    new = [latest[k] for k in sorted(latest.keys() - prior.keys())]
    removed = [prior[k] for k in sorted(prior.keys() - latest.keys())]
    changed = [
        {"previous": prior[k], "current": latest[k]}
        for k in sorted(latest.keys() & prior.keys())
        if latest[k] != prior[k]
    ]
    prior_vol = {f"{v['label']}:{v.get('drive_letter')}": v
                 for v in before["rp2_volumes"]}
    later_vol = {f"{v['label']}:{v.get('drive_letter')}": v
                 for v in after["rp2_volumes"]}
    earlier_net = {v["name"]: v for v in before["local_network_adapters"]}
    later_net = {v["name"]: v for v in after["local_network_adapters"]}
    changed_link = [
        {"name": name, "previous": earlier_net[name].get("os_link_status"),
         "current": later_net[name].get("os_link_status")}
        for name in sorted(earlier_net.keys() & later_net.keys())
        if earlier_net[name].get("os_link_status") !=
           later_net[name].get("os_link_status")
    ]
    return {
        "schema": "openknx-valvecontrol/knx030-passive-diff-v1",
        "before_label": before["label"],
        "after_label": after["label"],
        "new_usb_port_candidates": new,
        "removed_usb_port_candidates": removed,
        "changed_usb_port_metadata": changed,
        "new_rp2_volume_candidates": [later_vol[k] for k in
                                      sorted(later_vol.keys() - prior_vol.keys())],
        "removed_rp2_volume_candidates": [prior_vol[k] for k in
                                          sorted(prior_vol.keys() - later_vol.keys())],
        "local_adapter_link_changes": changed_link,
        "new_com_port_names": sorted(set(d["com_port"] for d in new
                                         if d.get("com_port"))),
        "knx_ip_gateway_verified": False,
        "rp2040_or_attiny_identity_verified": False,
        "hardware_release_gates": {key: False for key in GATES},
        "note": ("Device appearance is only a candidate; no COM/KNX packets "
                 "or MCU signature read. Never use this diff to authorize flash/motors."),
    }


def plan() -> dict[str, Any]:
    return {
        "purpose": "LLO Home local-only read-only inventory before/after board attachment",
        "commands": ["plan", "capture", "compare"],
        "operations": [
            "Get-PnpDevice -PresentOnly (USB/Ports only)",
            "Get-Volume filtered to RPI-RP2 label (no volume file access)",
            "Get-NetAdapter (local link metadata, not KNX/IP scan)",
            "hash and redact raw Windows PnP instance IDs",
            "compare local snapshot JSON files without system/device access",
        ],
        "no_device_IO": True,
        "knx_ip_discovery": False,
        "flash_or_motor_authority": False,
        "hardware_release_gates": {key: False for key in GATES},
    }


def cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("plan", help="No OS call; explain restrictions")
    c = sub.add_parser("capture", help="Passive Windows device metadata snapshot")
    c.add_argument("--output", required=True, help="NEW .json outside repository")
    c.add_argument("--label", required=True, help="e.g. disconnected or connected")
    d = sub.add_parser("compare", help="Offline snapshot comparison (no subprocess)")
    d.add_argument("--before", required=True)
    d.add_argument("--after", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = cli().parse_args(argv)
    try:
        if args.action in ("plan", None):
            output = plan()
        elif args.action == "capture":
            snapshot = capture(args.output, args.label)
            output = {
                "saved_to": str(Path(args.output).resolve()),
                "label": snapshot["label"],
                "usb_port_candidates": len(snapshot["devices"]),
                "rpi_rp2_volumes": len(snapshot["rp2_volumes"]),
                "network_adapter_records": len(snapshot["local_network_adapters"]),
                "raw_device_ids_saved": False,
                "hardware_release_gates_all_blocked": True,
            }
        elif args.action == "compare":
            output = compare(read_snapshot(args.before), read_snapshot(args.after))
        else:
            raise InventoryError("Unsupported command")
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except InventoryError as exc:
        print("KNX030 BLOCKED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
