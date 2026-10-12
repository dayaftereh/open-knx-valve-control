#!/usr/bin/env python3
"""KNX026 read-only source-scope audit; not physical hardware approval."""
from pathlib import Path
import difflib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "52833af"
FROZEN = (
    "assets/open-knx-valve-control.xml",
    "assets/knx008_zone_ets_proposal.json",
    "include/knxprod.hpp",
    "schematic/sch_knx-valve-control_v1.2.json",
    "schematic/pcb_knx-valve-control_v1.2.json",
    "src/controller/config.hpp",
    "src/controller/temperature_bridge.cpp",
    "src/controller/temperature_bridge.hpp",
    "src/controller/temperature_publisher.cpp",
    "src/temperature/main.cpp",
    "lib/common/knx025_fault_supervisor.hpp",
    "lib/common/room_control_runtime.hpp",
    "lib/common/knx024_room_dpt_adapter.hpp",
    "lib/common/motor_queue_simulator.hpp",
)
def old(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT).decode("utf-8-sig").replace("\r\n", "\n")
def current(path):
    return (ROOT / path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
def must(test, description):
    assert test, description
    print("PASS", description)
def main():
    for item in FROZEN:
        must(old(item) == current(item), "frozen KNX/ETS/PCB/ATtiny/safety: " + item)
    before = old("src/controller/main.cpp").splitlines(keepends=True)
    after = current("src/controller/main.cpp").splitlines(keepends=True)
    edits = difflib.SequenceMatcher(None, before, after, autojunk=False)
    added = []
    for op, _, _, low, high in edits.get_opcodes():
        must(op in ("insert", "equal"), "RP2040 original source insert-only")
        if op == "insert": added.extend(after[low:high])
    source = "".join(added)
    for required in ('#include "knx026_hmi_diagnostics.hpp"',
                     "Knx026::Snapshot hmiSnapshot;",
                     "Knx026::WaterInput hmiWater{};",
                     "temperatureBridge.channelValid(i, softwareNow)",
                     "hmiSnapshot = Knx026::capture("):
        must(source.count(required) == 1, "single passive HMI call: " + required)
    forbidden = ("digitalWrite(", "pinMode(", "analogWrite(", "GroupObject",
                 "armNativeSimulation(", "acknowledgeAndRequireFresh(",
                 "knx.write(", "Wire.begin(", "EEPROM", "Serial2.write(")
    for value in forbidden:
        must(value not in source, "no new hardware or recovery action " + value)
    header = current("lib/common/knx026_hmi_diagnostics.hpp")
    for value in ("hardwareDriveBlocked = true",
                  "actualPhysicalAllOffProven = false",
                  "actualMotorReferenceProven = false",
                  "Knx025::Diagnostics fault{};",
                  "#if !defined(ARDUINO)",
                  "virtualPositionValid"):
        must(value in header, "diagnostic model contract " + value)
    print("KNX026 scope audit PASS; software-only, no electrical safety approval")
if __name__ == "__main__":
    main()
