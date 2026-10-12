#!/usr/bin/env python3
"""KNX008 native C++ zone routing and DPT5.001 scaling tests.

Compiles only the portable header. No KNX bus, ETS or physical motor access.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "native" / "test_knx008_zone_model.cpp"
MSYS_GPP = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")


def main() -> int:
    requested = os.environ.get("CXX", "")
    compiler = shutil.which(requested) if requested else shutil.which("g++")
    if not compiler and requested:
        compiler = requested
    if not compiler and MSYS_GPP.is_file():
        compiler = str(MSYS_GPP)
    if not compiler:
        print("ERROR: g++ not found. Set CXX or install it.", file=sys.stderr)
        return 2

    cxx = Path(compiler).resolve()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx008-") as temp:
        executable = Path(temp) / (
            "zone_tests.exe" if os.name == "nt" else "zone_tests")
        args = [str(cxx), "-std=c++17", "-Wall", "-Wextra",
                "-Werror", "-pedantic", "-o", str(executable), str(SOURCE)]
        print("Building native KNX008 zones tests...", flush=True)
        compile_result = subprocess.run(
            args, cwd=ROOT, env=env, check=False)
        if compile_result.returncode:
            return compile_result.returncode
        print("Running KNX008 zones tests...", flush=True)
        result = subprocess.run([str(executable)], cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
    print("RESULT: KNX008 portable zone router tests PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
