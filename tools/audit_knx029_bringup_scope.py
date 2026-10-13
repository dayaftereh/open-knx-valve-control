#!/usr/bin/env python3
"""KNX029 repo scope check: software-only bundle, frozen firmware and electrical layout."""
from pathlib import Path
import ast
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "a35d6be"
FROZEN = (
    "platformio.ini",
    "src/controller/controller.ini",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
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
    "tools/audit_knx027_usb_flash_scope.py",
)


def git_base(path: str) -> str:
    result = subprocess.run(
        ["git", "-c", "safe.directory=" + ROOT.resolve().as_posix(),
         "-C", str(ROOT), "show", f"{BASE}:{path}"],
        capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Could not verify unchanged {path}")
    return result.stdout.decode("utf-8-sig").replace("\r\n", "\n")


def run() -> None:
    for path in FROZEN:
        actual = (ROOT / path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        assert git_base(path) == actual, f"KNX029 changed frozen firmware/hardware: {path}"
        print("PASS immutable original source:", path)

    script = (ROOT / "tools/knx029_prepare_bringup.py").read_text(encoding="utf-8")
    tests = (ROOT / "tools/test_knx029_bringup_kit.py").read_text(encoding="utf-8")
    ast.parse(script)
    ast.parse(tests)
    for term in (
        'def require_clean_commit(', 'def output_path(',
        'def strip_updi_actions_in_temporary_config(',
        'def readiness(', 'def build_bundle(', 'def verify_bundle(',
        'usb.build_isolated(', 'usb.run_checked([pio, "run", "-e", "temperature"]',
        '"source_dirty": False', '"motor_enable_authorized": False',
        '"UPDI_3V3_levels_CN1_verified": False',
        '"attiny_signature_readonly_verified": False',
        '"rp2040_software_boot_and_com_verified": False',
        'SHA256SUMS.txt', 'ARTIFACTS', 'require_clean_commit(expected, root, runner)',
        'preserved_dir = temp / ".knx029-captured-rp2040"',
        'saved = preserved_dir / name',
        'source = preserved.get(name, temp / relative)',
    ):
        assert term in script, f"Missing hardlock: {term}"
    # Only compiler commands are permitted; all programmer-specific entries
    # must be stripped from a TEMPORARY copy of the ATtiny config.
    for forbidden in (
        'os.system(', 'shell=True', 'Serial(', 'knx.write(',
        'digitalWrite(', 'pymcuprog write', 'pymcuprog erase',
        '"upload", "--execute"', '"-t", "upload"',
    ):
        assert forbidden not in script, f"Unexpected device operation: {forbidden}"
    assert "test_plan_does_not_execute_commands_or_contact_devices" in tests
    assert "test_updi_config_drift_refuses_any_programming" in tests
    assert "test_verify_detects_mutated_uf2_or_checksum" in tests
    print("KNX029 read-only/offline firmware bundle source-scope PASS")
    print("Physical hardware blockers remain UNSOLVED.")


if __name__ == "__main__":
    run()
