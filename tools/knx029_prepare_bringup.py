#!/usr/bin/env python3
"""KNX029: create an OFFLINE, explicitly unflashable first-contact firmware kit.

No USB, COM, UPDI, GPIO, ETS, KNX, or motor operations. Builds the RP2040
and ATtiny3216 *configured* targets in a temporary copy, never the source
repository. Real ATtiny signature and RP2040 flash capacity are NOT known.

Default invocation is 'plan' and starts no subprocess at all. 'build' requires
a clean, exact 40-hex Git commit and a NEW directory outside the repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import usb_flash_controller as usb

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "openknx-valvecontrol/knx029-offline-bringup-v1"
HEX40 = re.compile(r"[a-f0-9]{40}", re.IGNORECASE)
ARTIFACTS = {
    "controller-rp2040.uf2": ".pio/build/controller/firmware.uf2",
    "controller-rp2040.elf": ".pio/build/controller/firmware.elf",
    "temperature-attiny3216.hex": ".pio/build/temperature/firmware.hex",
    "temperature-attiny3216.elf": ".pio/build/temperature/firmware.elf",
}
ATINY_CONFIG_START = "[env:temperature]"
ATINY_UPLOAD_SECTION_START = "monitor_rts = 0"


class KitError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    hash_object = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            hash_object.update(part)
    return hash_object.hexdigest()


def safe_git(root: Path, args: list[str],
             runner: Any = subprocess.run) -> str:
    # The Home agent runs as SYSTEM while the repo is owned by user ll.
    # Trust ONLY this repo for this single invocation, never git --global.
    run = runner(
        ["git", "-c", "safe.directory=" + root.resolve().as_posix(),
         "-C", str(root.resolve()), *args],
        cwd=str(root), text=True, capture_output=True, check=False)
    if run.returncode != 0:
        raise KitError("Git query failed; repository unavailable or untrusted")
    return run.stdout.strip()


def require_clean_commit(expected: str, root: Path = ROOT,
                         runner: Any = subprocess.run) -> str:
    if HEX40.fullmatch(expected) is None:
        raise KitError("--expected-head must contain exactly 40 hexadecimal characters")
    head = safe_git(root, ["rev-parse", "HEAD"], runner)
    if head.lower() != expected.lower():
        raise KitError("Refusing build: Git HEAD changed or does not match --expected-head")
    if safe_git(root, ["status", "--porcelain=v1", "--untracked-files=all"], runner):
        raise KitError("Refusing build: Git worktree dirty; commit first")
    return head


def output_path(name: str, root: Path = ROOT) -> Path:
    if not name.strip():
        raise KitError("Empty --output-dir is not allowed")
    dst = Path(name).resolve()
    source = root.resolve()
    if dst == source or source in dst.parents:
        raise KitError("Output directory MUST be outside the Git repository")
    if dst.exists():
        raise KitError("Output directory already exists; no overwrite allowed")
    return dst


def strip_updi_actions_in_temporary_config(isolated: Path) -> None:
    """Remove all UPDI/port discovery extras ONLY from the isolated copy.

    The ATtiny board, clock, dependencies, build_src_filter and firmware
    content stay identical. An upstream config change fails closed rather than
    accidentally invoking a port selector or programmer during a build.
    """
    ini = isolated / "src" / "temperature" / "temperature.ini"
    raw = ini.read_text(encoding="utf-8")
    if raw.count(ATINY_CONFIG_START) != 1 or raw.count(
            ATINY_UPLOAD_SECTION_START) != 1:
        raise KitError("Unexpected ATtiny config; refusing to strip UPDI actions")
    prefix, suffix = raw.split(ATINY_UPLOAD_SECTION_START, 1)
    suffix = suffix.partition("\n")[2]  # skip the remainder of monitor_rts line
    for required in (
        "board = ATtiny3216",
        "board_build.f_cpu = 20000000L",
        "build_src_filter",
        "milesburton/DallasTemperature",
        "https://github.com/SpenceKonde/OneWire",
    ):
        if required not in prefix:
            raise KitError("ATtiny config no longer matches expected build: " + required)
    for required in (
        "upload_protocol = custom",
        "pre:./assets/init_updi.py",
        "pre:./assets/autodetect_port.py",
        "upload_command = pymcuprog",
    ):
        if required not in suffix:
            raise KitError("Unknown upload section; refusing partial UPDI stripping")
    # Fail-closed if unexpected non-empty entries follow the known contract.
    after = [line.strip() for line in suffix.splitlines()
             if line.strip() and not line.strip().startswith((";", "#"))]
    allowed = (
        "upload_protocol = custom", "extra_scripts =",
        "pre:./assets/init_updi.py", "pre:./assets/autodetect_port.py",
        "upload_flags =", "--filename", "$SOURCE",
        "upload_command = pymcuprog",
    )
    if any(not any(line.startswith(known) for known in allowed)
           for line in after):
        raise KitError("ATtiny config includes an unknown upload directive")
    ini.write_text(prefix.rstrip() +
        "\n; KNX029 isolated BUILD-ONLY target: UPDI/COM/upload settings removed\n",
        encoding="utf-8")
    stripped = ini.read_text(encoding="utf-8")
    if any(token in stripped for token in
           ("upload_protocol", "upload_command", "init_updi.py",
            "autodetect_port.py", "monitor_rts")):
        raise KitError("Isolated ATtiny config still contains programmer settings")


def readiness() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "classification": "NOT_FLASHED_HARDWARE_UNVERIFIED",
        "board": "OpenKNXValveControl V1.2 (as-designed; as-built unknown)",
        "configured_targets": {
            "rp2040": {
                "board": "rpipico",
                "usb_upload": "picotool (KNX027, no real trial yet)",
                "flash_capacity": "unverified physical chip; config assumes 16 MiB",
                "power_safe": False,
            },
            "attiny": {
                "configured_mcu": "ATtiny3216",
                "as_built_mcu": "UNKNOWN: PCB metadata might be ATtiny1616",
                "device_signature_verified": False,
                "updi_voltage_and_CN1_pin1_safe": False,
            },
        },
        "release_gates": {
            "physical_assembly_verified": False,
            "USB_KNX_power_backfeed_safe": False,
            "UPDI_3V3_levels_CN1_verified": False,
            "rp2040_software_boot_and_com_verified": False,
            "attiny_signature_readonly_verified": False,
            "KNX_IP_testbus_verified": False,
            "KNX_ETS6_test_project_verified": False,
            "motor_enable_authorized": False,
        },
        "sequence": [
            "OFFLINE: inspect BOM and visual board photos (U25,R29,F1,U6,Q1,JMP1,STBY)",
            "UNPOWERED: verify CN1 pin1/5V and 3V3 UPDI level isolation",
            "BENCH: current-limited, motor-disconnected supply and USB/KNX backfeed test",
            "RP2040: passive USB enumeration; BOOTSEL/CDC identity with known flash capacity",
            "ATtiny: inspect physical package and read ONLY silicon signature after UPDI level checks",
            "FLASH: separate manual approval for RP2040 then target-matched ATtiny, verify/reboot",
            "KNX: isolated KNX/IP test bus, then ETS6 test project, no productive telegrams",
            "TELEMETRY: T0 first, T1..T8 then DPT9.001 mapping/CRC/age offline handling",
            "MOTORS: remain FORBIDDEN until KNX002-006 independently qualify physical interlock",
        ],
    }


def build_bundle(expected_head: str, target_dir: str,
                 *, root: Path = ROOT, runner: Any = subprocess.run,
                 pio: str | None = None, producer: str | None = None) -> Path:
    expected = require_clean_commit(expected_head, root, runner)
    dst = output_path(target_dir, root)
    pio = pio or usb.tool_path("pio")
    producer = producer or usb.tool_path("producer")
    if not Path(pio).is_file() or not Path(producer).is_file():
        raise KitError("Pinned compiler tools missing; no bundle generated")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Everything is created in temporary directories outside tracked source.
    with tempfile.TemporaryDirectory(prefix="knx029-build-") as builder_dir:
        temp = Path(builder_dir)
        # Reuses KNX027: only 'pio run -e controller', protects canonical header.
        elf, uf2 = usb.build_isolated(
            pio, producer, temp, root=root, runner=runner)
        if not elf.is_file() or not uf2.is_file():
            raise KitError("RP2040 build incomplete")
        # PlatformIO may clean a different environment's .pio/build outputs
        # when switching toolchains (RP2040 -> ATtiny). Capture the finished
        # controller binaries outside .pio BEFORE starting the second build.
        preserved_dir = temp / ".knx029-captured-rp2040"
        preserved_dir.mkdir()
        preserved: dict[str, Path] = {}
        for name, origin in (("controller-rp2040.uf2", uf2),
                             ("controller-rp2040.elf", elf)):
            if not origin.is_file() or origin.stat().st_size == 0:
                raise KitError("Empty RP2040 artifact: " + name)
            saved = preserved_dir / name
            shutil.copyfile(origin, saved)
            if sha256_file(saved) != sha256_file(origin):
                raise KitError("Failed to safeguard controller artifact: " + name)
            preserved[name] = saved
        strip_updi_actions_in_temporary_config(temp)
        env = os.environ.copy()
        env["PATH"] = str(Path(producer).parent) + os.pathsep + env.get("PATH", "")
        # Explicit BUILD, never 'upload'; temp config lacks ALL programmer hooks.
        usb.run_checked([pio, "run", "-e", "temperature"], cwd=temp,
                        env=env, runner=runner)
        for name, relative in ARTIFACTS.items():
            source = preserved.get(name, temp / relative)
            if not source.is_file() or source.stat().st_size == 0:
                raise KitError("Expected firmware build artifact missing: " + name)
        # Detect concurrent source/branch mutation before publishing artifacts.
        require_clean_commit(expected, root, runner)
        with tempfile.TemporaryDirectory(
                prefix=".knx029-staging-", dir=dst.parent) as staging_dir:
            staging = Path(staging_dir) / "kit"
            staging.mkdir()
            records: dict[str, dict[str, Any]] = {}
            for name, relative in ARTIFACTS.items():
                inp = preserved.get(name, temp / relative)
                out = staging / name
                shutil.copyfile(inp, out)
                hashed = sha256_file(out)
                if hashed != sha256_file(inp):
                    raise KitError("Artifact copy hash mismatch: " + name)
                records[name] = {"sha256": hashed, "size_bytes": out.stat().st_size}
            manifest = {
                **readiness(),
                "built_utc": datetime.now(timezone.utc).isoformat(),
                "source_git_head": expected,
                "source_dirty": False,
                "rp2040_toolchain": "GCC14.3.0 / Arduino-Pico5.5.0 / KNX028 pins",
                "attiny_target": "ATtiny3216 configured, chip identity NOT verified",
                "build_environment": "isolated temp copies, no upload or COM discovery",
                "firmware_artifacts": records,
            }
            manifest_path = staging / "bringup-manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            entries = {name: sha256_file(staging / name) for name in records}
            entries[manifest_path.name] = sha256_file(manifest_path)
            (staging / "SHA256SUMS.txt").write_text(
                "".join(f"{hashval}  {name}\n" for name, hashval
                        in sorted(entries.items())),
                encoding="utf-8")
            if dst.exists():
                raise KitError("Output directory appeared during build; no overwrite")
            # On the same volume this moves a complete staged kit atomically.
            staging.rename(dst)
        return dst


def verify_bundle(folder: str) -> dict[str, Any]:
    """Verify artifact sizes and SHA256SUMS without touching a device."""
    kit = Path(folder).resolve()
    if not kit.is_dir():
        raise KitError("Kit directory missing")
    expected = set(ARTIFACTS) | {"bringup-manifest.json", "SHA256SUMS.txt"}
    items = {entry.name: entry for entry in kit.iterdir()}
    if set(items) != expected:
        raise KitError("Kit file list is incomplete or has unexpected entries")
    if any(not p.is_file() or p.is_symlink() for p in items.values()):
        raise KitError("Kit must contain only regular files, no symlinks")
    try:
        manifest = json.loads(items["bringup-manifest.json"].read_text(
            encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise KitError("Malformed manifest JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise KitError("Wrong or missing KNX029 schema")
    if (manifest.get("classification") != "NOT_FLASHED_HARDWARE_UNVERIFIED"
            or manifest.get("source_dirty") is not False
            or not isinstance(manifest.get("source_git_head"), str)
            or HEX40.fullmatch(manifest["source_git_head"]) is None):
        raise KitError("Kit does not identify a clean, unflashed source commit")
    gates = manifest.get("release_gates")
    if not isinstance(gates, dict) or set(gates) != set(readiness()["release_gates"]):
        raise KitError("Unexpected or missing physical interlock gates")
    if any(value is not False for value in gates.values()):
        raise KitError("Kit incorrectly asserts a real hardware release")
    records = manifest.get("firmware_artifacts")
    if not isinstance(records, dict) or set(records) != set(ARTIFACTS):
        raise KitError("Firmware artifact list mismatch")
    lines = items["SHA256SUMS.txt"].read_text(encoding="ascii").splitlines()
    if len(lines) != len(expected) - 1:
        raise KitError("Checksum entries missing or duplicated")
    hashes: dict[str, str] = {}
    for line in lines:
        digest, sep, name = line.partition("  ")
        if (sep != "  " or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or name not in expected - {"SHA256SUMS.txt"}
                or name in hashes):
            raise KitError("Invalid SHA256SUMS entry")
        hashes[name] = digest
    if set(hashes) != expected - {"SHA256SUMS.txt"}:
        raise KitError("Checksum list does not exactly match kit")
    for name, digest in hashes.items():
        if sha256_file(items[name]) != digest:
            raise KitError("Kit artifact SHA256 mismatch: " + name)
    for name, record in records.items():
        if (not isinstance(record, dict)
                or record.get("sha256") != hashes[name]
                or record.get("size_bytes") != items[name].stat().st_size
                or record["size_bytes"] <= 0):
            raise KitError("Manifest size/hash mismatch: " + name)
    return {
        "kit": str(kit),
        "source_git_head": manifest["source_git_head"],
        "artifacts_verified": len(records),
        "checksum_records": len(hashes),
        "release_gates_all_blocked": True,
        "hardware_contact": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action")
    sub.add_parser("plan", help="print readiness gates; no commands executed")
    b = sub.add_parser("build", help="build and package RP2040 + configured ATtiny, NO UPLOAD")
    b.add_argument("--output-dir", required=True, help="new directory OUTSIDE Git root")
    b.add_argument("--expected-head", required=True, help="exact clean 40-hex Git commit")
    v = sub.add_parser("verify", help="verify an existing offline kit, NO DEVICES")
    v.add_argument("--kit", required=True, help="existing KNX029 output directory")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action in (None, "plan"):
            print(json.dumps(readiness(), indent=2, sort_keys=True))
        elif args.action == "build":
            kit = build_bundle(args.expected_head, args.output_dir)
            print("KNX029 OFFLINE KIT:", kit)
            print("NO USB/UPDI/KNX operation, NO flash, NO physical motor release")
        elif args.action == "verify":
            print(json.dumps(verify_bundle(args.kit), indent=2, sort_keys=True))
        else:
            raise KitError("Invalid action")
        return 0
    except (KitError, usb.FlashError, OSError) as exc:
        print("BLOCKED/FAILED KNX029:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
