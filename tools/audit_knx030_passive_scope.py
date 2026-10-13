#!/usr/bin/env python3
"""KNX030 scope audit: freeze existing firmware and forbid device/network I/O."""
from pathlib import Path
import ast
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "846bb93"
FROZEN = (
    "platformio.ini",
    "src/controller/controller.ini",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/temperature/temperature.ini",
    "src/temperature/main.cpp",
    "assets/open-knx-valve-control.xml",
    "assets/init_updi.py",
    "assets/autodetect_port.py",
    "include/knxprod.hpp",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "lib/common/room_control_runtime.hpp",
    "lib/common/knx025_fault_supervisor.hpp",
    "lib/common/knx026_hmi_diagnostics.hpp",
    "tools/usb_flash_controller.py",
    "tools/knx029_prepare_bringup.py",
    "tools/audit_knx027_usb_flash_scope.py",
)


def old(path: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "safe.directory=" + ROOT.resolve().as_posix(),
         "-C", str(ROOT), "show", BASE + ":" + path],
        capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError("Cannot validate frozen source: " + path)
    return proc.stdout.decode("utf-8-sig").replace("\r\n", "\n")


def audit() -> None:
    for file in FROZEN:
        actual = (ROOT / file).read_text(encoding="utf-8-sig").replace(
            "\r\n", "\n")
        assert old(file) == actual, "KNX030 unexpectedly modified: " + file
        print("PASS frozen:", file)

    ps = (ROOT / "tools/knx030_passive_inventory_probe.ps1").read_text(
        encoding="utf-8")
    py = (ROOT / "tools/knx030_passive_inventory.py").read_text(
        encoding="utf-8")
    test = (ROOT / "tools/test_knx030_passive_inventory.py").read_text(
        encoding="utf-8")
    ast.parse(py)
    ast.parse(test)

    for required in ("Get-PnpDevice -PresentOnly",
                     "Get-Volume -ErrorAction Stop",
                     "Get-NetAdapter -ErrorAction Stop",
                     "ConvertTo-Json -Depth 5 -Compress"):
        assert required in ps, "Narrow OS-only probe missing " + required
    for forbidden in (
        r"\bSet-PnpDevice\b", r"\bEnable-PnpDevice\b",
        r"\bDisable-PnpDevice\b", r"\bInvoke-RestMethod\b",
        r"\bInvoke-WebRequest\b", r"\bInvoke-Command\b",
        r"\bTest-NetConnection\b", r"\bTest-Connection\b",
        r"\bNew-Net\b", r"\bSet-Net\b", r"\bConnect\b",
        r"\bStart-Process\b", r"\bSet-Volume\b",
        r"\bSet-Disk\b", r"\bSet-Partition\b",
    ):
        script_lines = "\n".join(
            line for line in ps.splitlines()
            if line.strip() and not line.lstrip().startswith("#"))
        assert not re.search(forbidden, script_lines, flags=re.IGNORECASE), (
            "Dangerous command in KNX030 OS probe: " + forbidden)
    for required in (
        'SCHEMA = "openknx-valvecontrol/knx030-passive-os-inventory-v1"',
        "def collect(", "def capture(", "def read_snapshot(",
        "def compare(", "def plan(", "def require_external_new_file(",
        "hashlib.sha256(raw_id.upper().encode",
        "subprocess-free",
        '"knx_ip_gateway_verified": False',
        '"rp2040_or_attiny_identity_verified": False',
        '"motor_enable_authorized"',
        '"-NoProfile"', '"-NonInteractive"',
        '"-File"', 'probe: Path = PROBE',
    ):
        assert required in py or (required == "subprocess-free" and
                                  "Offline comparison" in py), (
            "Missing KNX030 passive contract: " + required)
    for forbidden in (
        "serial.Serial(", "list_ports.comports(", "socket.socket(",
        "picotool ", "pymcuprog ", "upload --execute", "knx.write(",
        "digitalWrite(", "analogWrite(",
    ):
        active = "\n".join(line for line in py.splitlines()
                           if not line.lstrip().startswith("#"))
        assert forbidden not in active, "Unsafe operation in Python collector"
    assert "test_default_plan_is_subprocess_free" in test
    assert "test_offline_compare_cannot_call_subprocess" in test
    assert "test_tampered_snapshot_cannot_authorize_motor" in test
    print("KNX030 PASS: passive Windows metadata only; firmware and hardware frozen")
    print("NO physical safety release, KNX/IP discovery, port open or flash.")


if __name__ == "__main__":
    audit()
