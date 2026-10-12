#!/usr/bin/env python3
"""Native KNX021 software-only end-to-end simulation: PI -> zones -> queue.

No device, KNX bus, GPIO, simulator-as-production or firmware flashing.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/native/test_knx021_end_to_end.cpp"
MSYS_GPP = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")


def main() -> int:
    selected = os.environ.get("CXX", "")
    compiler = shutil.which(selected) if selected else shutil.which("g++")
    if not compiler and selected:
        compiler = selected
    if not compiler and MSYS_GPP.is_file():
        compiler = str(MSYS_GPP)
    if not compiler:
        print("ERROR: No native C++ compiler; set CXX.", file=sys.stderr)
        return 2
    cxx = Path(compiler).resolve()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="openknx-knx021-") as tmp:
        exe = Path(tmp) / ("knx021.exe" if os.name == "nt" else "knx021")
        cmd = [
            str(cxx), "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-pedantic", "-o", str(exe), str(SOURCE),
        ]
        print("Building KNX021 native end-to-end model...", flush=True)
        result = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
        print("Running KNX021 end-to-end integration...", flush=True)
        result = subprocess.run([str(exe)], cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode

    print("RESULT: KNX021 native end-to-end software simulation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
