#!/usr/bin/env python3
"""KNX019 native RoomPI plus KNX008 zone-router simulated thermal plant tests.

Only native portable C++ source is compiled and executed. No ETS/KNX bus,
serial hardware or actuator is opened, flashed, or commanded.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "native" / "test_room_pi_controller.cpp"
MSYS_GPP = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")


def main() -> int:
    selected = os.environ.get("CXX", "")
    binary = shutil.which(selected) if selected else shutil.which("g++")
    if not binary and selected:
        binary = selected
    if not binary and MSYS_GPP.is_file():
        binary = str(MSYS_GPP)
    if not binary:
        print("ERROR: no native C++ compiler; set CXX", file=sys.stderr)
        return 2

    compiler = Path(binary).resolve()
    env = dict(os.environ)
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="openknx-knx019-") as tmp:
        path = Path(tmp) / ("roompi.exe" if os.name == "nt" else "roompi")
        args = [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-o", str(path), str(SOURCE)]
        print("Building KNX019 native RoomPI simulation", flush=True)
        result = subprocess.run(args, cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
        print("Running KNX019 native RoomPI simulation", flush=True)
        result = subprocess.run([str(path)], cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
    print("RESULT: KNX019 RoomPI integration/simulation tests PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
