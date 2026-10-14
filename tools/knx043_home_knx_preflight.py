#!/usr/bin/env python3
"""KNX043: read-only workstation and safety-gate inventory on LLO Home.

Never opens serial ports, never sends or receives KNX telegrams, never flashes
hardware and never authorizes energizing a board or connecting the KNX bus.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

SCHEMA = "knx043-home-knx-bench/v1"
REQUIRED_PHYSICAL_GATES = (
    "board_visual_no_short_or_heat_damage",
    "u9_pin24_knx_tx_pullup_r17_removed_without_pad_bridge",
    "u11_actual_68ohm_and_thermal_damage_checked",
    "f1_rating_current_limit_reviewed",
    "d1_bypass_usb_knx_backfeed_reviewed",
    "jmp1_power_source_position_measured",
    "jmp2_knx_rx_to_rp_gpio1_continuity_verified",
    "jmp3_knx_tx_to_rp_gpio0_continuity_verified",
    "knx_tx_low_no_bus_at_reset_boot_and_firmware_running",
    "knx_tx_low_no_bus_at_brownout_or_usb_replug",
    "u9_u11_postincident_electrical_inspection_approved",
    "board_usb_only_3v3_and_5v_within_safe_limits",
    "no_actual_motor_connected",
    "dedicated_isolated_knx_tp_supply_and_interface_identified",
    "knx_usb_or_ip_interface_ready_on_home",
    "rx_only_firmware_for_stknx_loaded_after_boot_gate",
    "user_explicit_release_for_separate_knx_connection_test",
)
# The firmware input is intentionally the OLD working KNX042 and the new
# LED-only preview, not a claim of available STKNX-safe bus firmware.
KNOWN_IMAGES = {
    "knx042_led_sequence_built_not_flashed": (
        "knx042-all-motor-led-sequence-5rounds.uf2",
        "959cde9090d8ddc1258971fed548aa01c823254105ae1ac3f292fb01790c2875",
    ),
    "knx042_rollback": (
        "rollback-knx042-m1-180s.uf2",
        "7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d",
    ),
}
HOME_BUILD = Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl")
HOME_TOOL = Path(r"C:\_myspace\Tools\OpenKNXproducer-3.12.2\tools\Windows\OpenKNXproducer-x64.exe")
HOME_PYTHON = Path(r"C:\Users\ll\.platformio\penv\Scripts\python.exe")
HOME_PIO = Path(r"C:\Users\ll\.platformio\penv\Scripts\pio.exe")
HOME_ETS = Path(r"C:\Program Files (x86)\ETS6\ETS6.exe")


def load_gate(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != SCHEMA:
        raise ValueError("Invalid KNX043 gate JSON/schema")
    observations = obj.get("observations")
    if not isinstance(observations, dict):
        raise ValueError("Gate observations must be an object")
    missing = sorted(set(REQUIRED_PHYSICAL_GATES) - set(observations))
    if missing:
        raise ValueError("Missing required physical gates: " + ", ".join(missing))
    # Invalid values must not be silently treated as affirmative.
    bad = [k for k in REQUIRED_PHYSICAL_GATES
           if observations[k] is not None and type(observations[k]) is not bool]
    if bad:
        raise ValueError("Gates must be null or boolean, not text/numbers: " + ", ".join(bad))
    return obj


def classify_gate(gate: dict[str, Any]) -> dict[str, Any]:
    observed = gate["observations"]
    awaiting = [k for k in REQUIRED_PHYSICAL_GATES if observed[k] is not True]
    return {
        "status": "BLOCKED_AWAIT_HARDWARE_EVIDENCE" if awaiting else "CHECKLIST_COMPLETE_NEEDS_INDEPENDENT_SAFETY_REVIEW",
        "unverified_items": awaiting,
        "physical_items_confirmed": len(REQUIRED_PHYSICAL_GATES) - len(awaiting),
        "physical_items_total": len(REQUIRED_PHYSICAL_GATES),
        "knx_power_or_bus_connection_authorized": False,
        "warning": "Never self-authorize KNX power/connection. Only a qualified manual electrical review can release hardware testing.",
    }


def file_integrity(path: Path, sha_expected: str) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "hash_match": False}
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "present": True, "size": path.stat().st_size,
            "sha256": sha, "hash_match": sha == sha_expected}


def inventory(gate: dict[str, Any], root: Path, home_build: Path = HOME_BUILD) -> dict[str, Any]:
    seqdir = home_build / "KNX042-ALL-MOTOR-LED-SEQUENCE-20261014"
    images = {label: file_integrity(seqdir / filename, digest)
              for label, (filename, digest) in KNOWN_IMAGES.items()}
    kit = home_build / "KNX029-b016a16-v1"
    def known_file(path: Path) -> dict[str, Any]:
        return {"path": str(path), "present": path.is_file()}
    tools = {
        "python": known_file(HOME_PYTHON),
        "platformio": known_file(HOME_PIO),
        "openknxproducer": known_file(HOME_TOOL),
        "ets6": known_file(HOME_ETS),
        "old_knx029_controller_uf2": known_file(kit / "controller-rp2040.uf2"),
        "old_knx029_attiny_hex": known_file(kit / "temperature-attiny3216.hex"),
        "pcb_v1_2": known_file(root / "schematic" / "pcb_knx-valve-control_v1.2.json"),
    }
    # This is *intentionally* not an automated port detection or network scan.
    # A physically absent board must not trigger USB/open/flash or KNX/IP traffic.
    return {
        "operation": "KNX043_READ_ONLY_PREPARATION",
        "workstation": "LLO Home",
        "device_connection_attempted": False,
        "knx_frame_sent": False,
        "firmware_flash_attempted": False,
        "physical_board_expected": "not yet connected (user has it)",
        "software_tools": tools,
        "known_firmware_backups": images,
        "notes": [
            "Normal TPUart UART-8E1 TX idle HIGH is incompatible with STKNX active-HIGH KNX_TX; DO NOT flash production KNX image onto connected bus.",
            "R17 pullup, U11 previous overheating, D1 bypass, F1 protection and source selection remain physical gates.",
            "RP2040 KNX_RX is GPIO1, STKNX U9 pin23 through JMP2; passive pulse inspection is not ETS programming.",
            "No KNX/USB/IP interface or ETS license state is inferred from ETS6.exe presence.",
        ],
        "hardware_gate": classify_gate(gate),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=Path(__file__).resolve().parent.parent / "docs" / "KNX043_HOME_KNX_GATE.json")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, help="Write JSON inventory at supplied path, no device operations")
    args = parser.parse_args(argv)
    try:
        gate = load_gate(args.gate)
        result = inventory(gate, args.project)
        out = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
        print(out, end="")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("KNX043 READ-ONLY PREFLIGHT ERROR: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
