#!/usr/bin/env python3
"""KNX025 portable software fault supervisor and Arduino hard-lock tests.

Native binaries in a throw-away dir. No USB, KNX bus, GPIO or actual motors.
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
    ("tests/native/test_knx025_fault_supervisor.cpp", []),
    ("tests/native/test_knx025_firmware_hardlock.cpp", ["-DARDUINO=10800"]),
)


def main() -> int:
    selected = os.environ.get("CXX", "")
    cxx = shutil.which(selected) if selected else shutil.which("g++")
    if selected and not cxx:
        cxx = selected
    if not cxx and MSYS_GPP.exists():
        cxx = str(MSYS_GPP)
    if not cxx:
        print("FAIL no g++ compiler: configure CXX", file=sys.stderr)
        return 2
    compiler = Path(cxx).resolve()
    env = os.environ.copy()
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx025-") as tmp:
        for num, (source, flags) in enumerate(TESTS):
            exe = Path(tmp) / (
                f"knx025_{num}.exe" if os.name == "nt" else f"knx025_{num}")
            build = [
                str(compiler), "-std=c++17", "-Wall", "-Wextra",
                "-Werror", "-pedantic", *flags, "-o", str(exe),
                str(ROOT / source)]
            print("BUILD", source, flush=True)
            code = subprocess.run(build, cwd=ROOT, env=env,
                                  check=False).returncode
            if code:
                return code
            print("RUN", source, flush=True)
            code = subprocess.run([str(exe)], cwd=ROOT, env=env,
                                  check=False).returncode
            if code:
                return code
    print("RESULT: KNX025 two native C++ suites PASS "
          "(fault supervisor + compiled Arduino hardlock)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
