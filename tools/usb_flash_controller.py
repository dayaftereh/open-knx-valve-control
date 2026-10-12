#!/usr/bin/env python3
"""KNX027 RP2040 USB preparation and explicitly confirmed picotool upload.

Default and probe/plan/build operations NEVER talk to a target. Real upload
requires --execute, --confirm-safe-bench, exact COM port, exact VID:PID,
and the complete current clean Git SHA. Nothing here authorizes motor use.
"""
from __future__ import annotations

import argparse
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

ROOT = Path(__file__).resolve().parents[1]
COPY_ASSETS = (
    "open-knx-producer.py",
    "knxprod_header_fix.py",
    "open-knx-valve-control.xml",
    "init_updi.py",
    "autodetect_port.py",
)
COM_PATTERN = re.compile(r"COM[1-9][0-9]{0,3}", re.IGNORECASE)
VIDPID_PATTERN = re.compile(r"[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}")
PY_SERIAL_ID = re.compile(r"VID:PID=([0-9a-fA-F]{4}):([0-9a-fA-F]{4})")
WINDOWS_PNP_ID = re.compile(r"VID_([0-9a-fA-F]{4})&PID_([0-9a-fA-F]{4})")


class FlashError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_port(value: str) -> str:
    value = value.upper()
    if COM_PATTERN.fullmatch(value) is None:
        raise FlashError("Windows USB serial port must be COMn (no auto-selection)")
    return value


def normalized_vidpid(value: str) -> str:
    if VIDPID_PATTERN.fullmatch(value) is None:
        raise FlashError("Use exact four-digit VID:PID such as 2E8A:00C0")
    return value.upper()


def hwid_vidpid(hwid: str) -> str | None:
    for pattern in (PY_SERIAL_ID, WINDOWS_PNP_ID):
        match = pattern.search(hwid)
        if match is not None:
            return (match.group(1) + ":" + match.group(2)).upper()
    return None


def choose_port(rows: list[dict[str, Any]], port: str, vidpid: str) -> dict[str, Any]:
    port = normalized_port(port)
    vidpid = normalized_vidpid(vidpid)
    matches = [row for row in rows
               if str(row.get("port", "")).upper() == port]
    if len(matches) != 1:
        raise FlashError(f"{port} not uniquely present in PlatformIO device list")
    row = matches[0]
    actual = hwid_vidpid(str(row.get("hwid", "")))
    if actual is None:
        raise FlashError(f"{port} has no verifiable USB VID:PID; refuse upload")
    if actual != vidpid:
        raise FlashError(f"{port} VID:PID mismatch: expected {vidpid}, got {actual}")
    return row


def run_checked(command: list[str], *, cwd: Path,
                env: dict[str, str] | None = None,
                capture: bool = False,
                runner: Any = subprocess.run) -> subprocess.CompletedProcess[str]:
    result = runner(command, cwd=str(cwd), env=env, text=True,
                    capture_output=capture, check=False)
    if result.returncode != 0:
        raise FlashError(
            f"Command returned {result.returncode}: {command[0]} "
            + " ".join(command[1:]))
    return result


def discover_ports(pio: str, runner: Any = subprocess.run) -> list[dict[str, Any]]:
    result = run_checked([pio, "device", "list", "--json-output"],
                         cwd=ROOT, runner=runner, capture=True)
    try:
        ports = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise FlashError("PlatformIO did not return valid serial-port JSON") from exc
    if not isinstance(ports, list) or not all(isinstance(p, dict) for p in ports):
        raise FlashError("PlatformIO serial-port listing has an unexpected schema")
    return ports


def require_upload_consent(args: argparse.Namespace) -> None:
    # Fail BEFORE invoking any platform/programming process.
    if not args.execute or not args.confirm_safe_bench:
        raise FlashError("Upload BLOCKED: require --execute AND --confirm-safe-bench")
    if not args.port or not args.expect_vidpid or not args.expected_head:
        raise FlashError(
            "Upload BLOCKED: --port, --expect-vidpid and --expected-head required")
    normalized_port(args.port)
    normalized_vidpid(args.expect_vidpid)
    if re.fullmatch(r"[0-9a-fA-F]{40}", args.expected_head) is None:
        raise FlashError("--expected-head must be the full 40-character Git SHA")


def verify_clean_head(expected: str, root: Path = ROOT,
                      runner: Any = subprocess.run) -> str:
    head = run_checked(["git", "rev-parse", "HEAD"], cwd=root,
                       capture=True, runner=runner).stdout.strip()
    dirty = run_checked(["git", "status", "--porcelain"], cwd=root,
                        capture=True, runner=runner).stdout.strip()
    if head.lower() != expected.lower():
        raise FlashError(f"Git HEAD mismatch (current {head}); upload refused")
    if dirty:
        raise FlashError("Git working tree is not clean; commit changes first")
    return head


def tool_path(kind: str) -> str:
    if kind == "pio":
        env = os.environ.get("PIO_EXECUTABLE", "")
        choices = [
            env,
            shutil.which("pio") or "",
            shutil.which("platformio") or "",
            str(Path.home() / ".platformio" / "penv" / "Scripts" / "pio.exe"),
        ]
    else:
        env = os.environ.get("OPENKNXPRODUCER_EXECUTABLE", "")
        choices = [
            env,
            shutil.which("OpenKNXproducer.exe") or "",
            r"C:\ASH\Tools\OpenKNXproducer-3.12.2\OpenKNXproducer.exe",
        ]
    for choice in choices:
        if choice and Path(choice).is_file():
            return str(Path(choice))
    raise FlashError(
        f"{kind} executable missing; configure PATH or "
        + ("PIO_EXECUTABLE" if kind == "pio"
           else "OPENKNXPRODUCER_EXECUTABLE"))


def copy_isolated_source(root: Path, dst: Path) -> None:
    shutil.copy2(root / "platformio.ini", dst / "platformio.ini")
    for folder in ("src", "lib", "include"):
        shutil.copytree(root / folder, dst / folder)
    asset_folder = dst / "assets"
    asset_folder.mkdir()
    for name in COPY_ASSETS:
        shutil.copy2(root / "assets" / name, asset_folder / name)
    config = (dst / "src" / "controller" / "controller.ini").read_text(
        encoding="utf-8")
    if re.search(r"(?m)^\s*upload_protocol\s*=\s*picotool\s*$", config) is None:
        raise FlashError("Explicit picotool protocol is missing in controller.ini")


def build_isolated(pio: str, producer: str, dst: Path, root: Path = ROOT,
                   runner: Any = subprocess.run) -> tuple[Path, Path]:
    original = root / "include" / "knxprod.hpp"
    before = sha256(original)
    try:
        copy_isolated_source(root, dst)
        env = os.environ.copy()
        env["PATH"] = str(Path(producer).parent) + os.pathsep + env.get("PATH", "")
        run_checked([pio, "run", "-e", "controller"], cwd=dst,
                    env=env, runner=runner)
        elf = dst / ".pio" / "build" / "controller" / "firmware.elf"
        uf2 = dst / ".pio" / "build" / "controller" / "firmware.uf2"
        if not elf.is_file() or not uf2.is_file() or uf2.stat().st_size == 0:
            raise FlashError("Isolated build missing firmware.elf or nonempty UF2")
    finally:
        if sha256(original) != before:
            raise FlashError("Repository include/knxprod.hpp changed during build")
    return elf, uf2


def save_uf2(uf2: Path, destination: str) -> Path:
    path = Path(destination).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create: never overwrite a previously identified recovery UF2.
    with path.open("xb") as target, uf2.open("rb") as source:
        shutil.copyfileobj(source, target)
    return path


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("probe", help="List serial ports only; NEVER reset/flash")
    for action in ("plan", "build", "upload"):
        sub = subs.add_parser(action)
        if action != "build":
            sub.add_argument("--port", required=(action == "plan"),
                             help="Explicit Windows COMn port")
            sub.add_argument("--expect-vidpid",
                             help="Exact USB VID:PID from probe")
        if action in ("build", "upload"):
            sub.add_argument("--output-uf2",
                             help="Optional non-existing path for recovery UF2")
        if action == "upload":
            sub.add_argument("--execute", action="store_true",
                             help="Allow the single selected picotool upload")
            sub.add_argument("--confirm-safe-bench", action="store_true",
                             help="Affirm isolated electrically checked KNX018 bench")
            sub.add_argument("--expected-head",
                             help="Full 40-char committed Git SHA")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = cli_parser().parse_args(argv)
    try:
        if args.action == "upload":
            require_upload_consent(args)
            verify_clean_head(args.expected_head)
        # Without --execute we do not even enumerate/trigger target USB.
        if args.action == "plan":
            port = normalized_port(args.port)
            if args.expect_vidpid:
                normalized_vidpid(args.expect_vidpid)
            print("PLAN ONLY: no USB reset, no flash, no code build")
            print("Future: isolated PlatformIO controller build (source only)")
            print(f"Future: pio run -e controller -t upload --upload-port {port}")
            print("Actual port/hardware/USB driver NOT verified by this plan.")
            return 0
        pio = tool_path("pio")
        if args.action == "probe":
            ports = discover_ports(pio)
            for item in ports:
                print(f'{item.get("port","?")}: {item.get("description","")} '
                      f'| USB VID:PID={hwid_vidpid(str(item.get("hwid",""))) or "UNKNOWN"}'
                      f' | HWID={item.get("hwid","")}')
            if not ports:
                print("No serial ports visible.")
            print("Probe is read-only: COM and VID:PID are NOT board identity proof.")
            return 0
        producer = tool_path("producer")
        if args.action == "upload":
            selected = choose_port(discover_ports(pio), args.port,
                                   args.expect_vidpid)
            print("Matched USB port:", selected.get("port"),
                  hwid_vidpid(str(selected.get("hwid", ""))), flush=True)
            print("Git HEAD:", args.expected_head, flush=True)

        with tempfile.TemporaryDirectory(prefix="openknx-rp2040-usb-") as temp:
            workspace = Path(temp)
            elf, uf2 = build_isolated(pio, producer, workspace)
            print("Isolated controller build: PASS", flush=True)
            print("Firmware UF2 sha256:", sha256(uf2), flush=True)
            if args.output_uf2:
                dest = save_uf2(uf2, args.output_uf2)
                print("Recovery UF2:", dest, flush=True)
            if args.action == "upload":
                # A lengthy build must not hide concurrent source/HEAD edits.
                verify_clean_head(args.expected_head)
                # Recheck just before flashing: never swap to some other COM port.
                choose_port(discover_ports(pio), args.port, args.expect_vidpid)
                env = os.environ.copy()
                env["PATH"] = str(Path(producer).parent) + os.pathsep + env.get("PATH", "")
                run_checked(
                    [pio, "run", "-e", "controller", "-t", "upload",
                     "--upload-port", normalized_port(args.port)],
                    cwd=workspace, env=env)
                print("PlatformIO upload returned success; verify target reboot "
                      "and USB/firmware runtime separately.")
            else:
                print("Build-only: no USB reset and no upload.")
        return 0
    except (FlashError, OSError, subprocess.SubprocessError) as exc:
        print("BLOCKED/FAILED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
