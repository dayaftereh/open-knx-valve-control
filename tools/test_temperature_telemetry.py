#!/usr/bin/env python3
"""KNX015 C++ policy and real-controller-publisher mock integration tests.

Uses only native C++ with simulated UART/KNX objects; never flashes devices.
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


def main() -> int:
    requested = os.environ.get("CXX", "")
    found = shutil.which(requested) if requested else shutil.which("g++")
    if not found and requested:
        found = requested
    if not found and MSYS_GPP.is_file():
        found = str(MSYS_GPP)
    if not found:
        print("ERROR: C++ compiler unavailable", file=sys.stderr)
        return 2
    cxx = Path(found).resolve()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")
    suites = [
        ("policy",
         ["tests/native/test_temperature_telemetry.cpp"], []),
        ("publisher",
         ["tests/native/test_temperature_publisher_integration.cpp",
          "src/controller/temperature_publisher.cpp",
          "src/controller/temperature_bridge.cpp"],
         ["-I", str(ROOT / "tests/native/mocks"),
          "-I", str(ROOT / "lib/common"),
          "-I", str(ROOT / "src/controller")]),
    ]
    with tempfile.TemporaryDirectory(prefix="openknx-knx015-") as tmp:
        for label, files, options in suites:
            binary = Path(tmp) / (label + (".exe" if os.name == "nt" else ""))
            cmd = [str(cxx), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                   *options, "-o", str(binary),
                   *(str(ROOT / path) for path in files)]
            print("Building KNX015", label, flush=True)
            build = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
            if build.returncode:
                return build.returncode
            print("Running KNX015", label, flush=True)
            run = subprocess.run([str(binary)], cwd=ROOT, env=env, check=False)
            if run.returncode:
                return run.returncode
    print("RESULT: both KNX015 native C++ suites PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
