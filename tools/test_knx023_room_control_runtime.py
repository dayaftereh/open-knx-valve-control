#!/usr/bin/env python3
"""KNX023 native runtime and Arduino-preprocessor hard-lock tests.

No I/O to GPIO, RP2040, USB, serial, KNX bus or motors.
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

TESTS = (
    ("tests/native/test_knx023_room_control_runtime.cpp", []),
    ("tests/native/test_knx023_firmware_hardlock.cpp",
     ["-DARDUINO=10800"]),
)


def main() -> int:
    requested = os.environ.get("CXX", "")
    compiler = shutil.which(requested) if requested else shutil.which("g++")
    if requested and not compiler:
        compiler = requested
    if not compiler and MSYS_GPP.is_file():
        compiler = str(MSYS_GPP)
    if not compiler:
        print("FAIL: No native C++ compiler. Set CXX.", file=sys.stderr)
        return 2

    resolved = Path(compiler).resolve()
    env = os.environ.copy()
    env["PATH"] = str(resolved.parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx023-") as td:
        for index, (source, defines) in enumerate(TESTS):
            binary = Path(td) / (
                f"knx023_{index}.exe" if os.name == "nt" else f"knx023_{index}")
            cmd = [
                str(resolved), "-std=c++17", "-Wall", "-Wextra",
                "-Werror", "-pedantic", *defines,
                "-o", str(binary), str(ROOT / source),
            ]
            print("BUILD KNX023", source, flush=True)
            result = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
            if result.returncode:
                return result.returncode
            print("RUN KNX023", source, flush=True)
            result = subprocess.run(
                [str(binary)], cwd=ROOT, env=env, check=False)
            if result.returncode:
                return result.returncode
    print("RESULT: 2 KNX023 native suites PASS, Arduino hardlock PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
