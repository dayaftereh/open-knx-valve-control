#!/usr/bin/env python3
"""KNX035 static fail-closed STKNX TX safety audit; no device I/O."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

from audit_design import components
from audit_knx022_hw_preflight import schematic_labels

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/KNX035_STKNX_TX_HAZARD.json"
BASE = "374dbc4f837169057b2000b0f19a3b91f240784e"
FROZEN = [
    "schematic/pcb_knx-valve-control_v1.2.json",
    "schematic/sch_knx-valve-control_v1.2.json",
    "src/controller/main.cpp",
    "src/controller/config.hpp",
    "lib/common/temperature_protocol.hpp",
    "assets/open-knx-valve-control.xml",
    "tools/usb_flash_controller.py",
    "docs/KNX034_USB_ONLY_PREPOWER_GATE.md",
]
class UnsafeEvidence(ValueError):
    pass

def guard(truth: bool, detail: str) -> None:
    if not truth:
        raise UnsafeEvidence(detail)

def audit(report: dict, pcb: dict, sch: dict,
          controller: str, uart: str, tpuart: str) -> None:
    guard(report.get("schema") ==
          "openknx-valvecontrol/knx035-stknx-tx-hazard-v1",
          "wrong KNX035 schema")
    guard(report.get("source_git_baseline") == BASE and
          report.get("status") == "ELECTRICAL_TX_IDLE_HAZARD_OPEN",
          "wrong baseline or physically unverified hazard closed")
    guard(pcb["R17"]["pins"] == {"1": "KNX_TX", "2": "3.3V"} and
          sch["R17"]["display"].startswith("10k"),
          "R17 no longer 10k up to 3.3V in source")
    guard(pcb["U9"]["pins"]["24"] == "KNX_TX" and
          pcb["U9"]["pins"]["3"] == "R68" and
          pcb["U9"]["pins"]["11"] == "KNX_A",
          "U9 STKNX TX / R68 mismatch")
    guard(pcb["U11"]["pins"] == {"1": "R68", "2": "KNX_A"} and
          sch["U11"]["display"].startswith("68") and
          pcb["U11"]["meta"]["Manufacturer Part"] ==
          "HoJLR2512-3W-3.5mR-1%",
          "U11 real-68R versus incorrect PCB MPN discrepancy changed")
    guard(pcb["JMP3"]["pins"]["2"] == "KNX_TX" and
          pcb["JMP3"]["pins"]["3"] == "KNX_TX'" and
          pcb["U18"]["pins"]["2"] == "KNX_TX'",
          "JMP3 RP2040 path changed")
    guard("TPUart::Interface::ArduinoSerial(Serial1)" in controller,
          "old TPUart backend no longer present; re-evaluate")
    guard("SERIAL_8E1" in uart and
          "19200, 38400" in tpuart,
          "conventional UART startup no longer present")
    e = report["evidence"]
    guard(e["TX_idle_low"] is True and
          e["TX_active_high_pulse_us"] == 35 and
          e["TX_low_following_us"] == 69 and
          e["TX_internal_pull_down_typical_uA"] == 6,
          "STKNX datasheet idle polarity / timings falsified")
    guard(e["R17_nominal_ohms"] == 10000 and
          e["R17_pins"] == pcb["R17"]["pins"] and
          e["U11_schematic_ohms"] == 68 and
          e["U11_actual_mpn_confirmed"] is False and
          e["STKNX_TX_high_actually_measured"] is False and
          e["U9_damage_excluded"] is False and
          e["actual_blink_program_pin_setup_verified"] is False,
          "unmeasured physical facts fabricated")
    guard(e["U11_photo_actual"] ==
          "user_reports_68_ohm_installed_not_ohmmeter_verified",
          "user 68ohm statement misreported as resistance test")
    guard(report["v12_current"]["R17_removed_confirmed"] is False and
          report["v12_current"]["KNX_bus_safe_to_connect"] is False,
          "unsafe claim that R17 removal or bus qualification happened")
    v13 = report["v13_ECO_proposals"]
    guard(v13["remove_R17_3V3_pullup"] is True and
          v13["add_new_external_pull_down_to_GND_ohms_range"] == [4700,10000] and
          v13["existing_R17_footprint_can_be_reused_unchanged"] is False and
          v13["hardware_TX_enable_fail_low_review_required"] is True and
          v13["replace_direct_TPUart_UART_driver_with_STKNX_pulse_phy_required"] is True,
          "KNX_TX ECO lost or tied to wrong net")
    releases = report.get("release",{})
    guard(releases and all(value is False for value in releases.values()),
          "unpowered user report cannot authorize KNX bus or motor operation")

def frozen() -> None:
    for p in FROZEN:
        git = subprocess.run(
            ["git","-c","safe.directory="+ROOT.resolve().as_posix(),
             "-C",str(ROOT),"show",BASE+":"+p],
            capture_output=True,check=False)
        guard(git.returncode==0 and
              git.stdout.replace(b"\r\n",b"\n") ==
              (ROOT / p).read_bytes().replace(b"\r\n",b"\n"),
              "production source touched during static TX review: "+p)

def main() -> int:
    try:
        report = json.loads(DATA.read_text(encoding="utf-8"))
        sch = schematic_labels(json.loads((ROOT /
           "schematic/sch_knx-valve-control_v1.2.json").read_text(encoding="utf-8-sig")))
        pcb = components(json.loads((ROOT /
           "schematic/pcb_knx-valve-control_v1.2.json").read_text(encoding="utf-8-sig"))["shape"])
        controller = (ROOT / "src/controller/main.cpp").read_text(encoding="utf-8-sig")
        uart = (ROOT / ".pio/libdeps/controller/TPUart/src/TPUart/Interface/ArduinoSerial.h").read_text(encoding="utf-8-sig")
        tpuart = (ROOT / ".pio/libdeps/controller/TPUart/src/TPUart/DataLinkLayer.cpp").read_text(encoding="utf-8-sig")
        audit(report,pcb,sch,controller,uart,tpuart)
        frozen()
        print("KNX035 PASS: R17 pullup violates STKNX idle-LOW contract; U11 actual 68R user-reported.")
        print("KNX035 PASS: direct TP-UART Serial1 remains incompatible pending new STKNX PHY.")
        print("KNX035 STATUS: TX HIGH NOT MEASURED; U9/U11 may be damaged; no power/bus/motor authorized.")
        return 0
    except (UnsafeEvidence,KeyError,OSError,ValueError) as exc:
        print("KNX035 BLOCKED:",str(exc),file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
