#!/usr/bin/env python3
"""Build KNX024 DPT9/5 typed-object tests in a temporary native C++ sandbox.

No programmer, serial port, KNX bus, ETS6 or motor hardware is accessed.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MSYS_GPP = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")
CASES = (
    ("tests/native/test_knx024_room_dpt_adapter.cpp", []),
    ("tests/native/test_knx024_firmware_hardlock.cpp", ["-DARDUINO=10800"]),
)


def main() -> int:
    selected = os.environ.get("CXX", "")
    compiler = shutil.which(selected) if selected else shutil.which("g++")
    if selected and not compiler:
        compiler = selected
    if not compiler and MSYS_GPP.exists():
        compiler = str(MSYS_GPP)
    if not compiler:
        print("ERROR: No native g++; configure CXX", file=sys.stderr)
        return 2

    cxx = Path(compiler).resolve()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx024-") as td:
        for i, (rel, definitions) in enumerate(CASES):
            exe = Path(td) / (
                f"knx024_{i}.exe" if os.name == "nt" else f"knx024_{i}")
            cmd = [str(cxx), "-std=c++17", "-Wall", "-Wextra",
                   "-Werror", "-pedantic", *definitions, "-o", str(exe),
                   str(ROOT / rel)]
            print("COMPILE", rel, flush=True)
            build = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
            if build.returncode:
                return build.returncode
            print("EXECUTE", rel, flush=True)
            run = subprocess.run([str(exe)], cwd=ROOT, env=env, check=False)
            if run.returncode:
                return run.returncode
    print("RESULT: KNX024 typed KNX room KO adapter two native suites PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
