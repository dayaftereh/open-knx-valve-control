#!/usr/bin/env python3
"""KNX020 native C++ motor queue safety-contract and stress simulations.

No KNX interface, RP2040, motor, USB or GPIO hardware is accessed.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "tests/native/test_motor_queue_simulator.cpp",
    "tests/native/test_motor_queue_stress.cpp",
)
MSYS_GPP = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")


def main() -> int:
    selected = os.environ.get("CXX", "")
    found = shutil.which(selected) if selected else shutil.which("g++")
    if not found and selected:
        found = selected
    if not found and MSYS_GPP.is_file():
        found = str(MSYS_GPP)
    if not found:
        print("ERROR: no native C++ compiler; set CXX", file=sys.stderr)
        return 2
    cxx = Path(found).resolve()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="openknx-knx020-") as temp:
        for num, relpath in enumerate(SOURCES):
            binary = Path(temp) / (
                f"knx020_{num}.exe" if os.name == "nt" else f"knx020_{num}")
            cmd = [
                str(cxx), "-std=c++17", "-Wall", "-Wextra",
                "-Werror", "-pedantic", "-o", str(binary),
                str(ROOT / relpath),
            ]
            print("Building", relpath, flush=True)
            build = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
            if build.returncode:
                return build.returncode
            print("Running", relpath, flush=True)
            run = subprocess.run([str(binary)], cwd=ROOT, env=env, check=False)
            if run.returncode:
                return run.returncode
    print("RESULT: BOTH KNX020 native C++ suites PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
