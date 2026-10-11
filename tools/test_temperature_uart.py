#!/usr/bin/env python3
"""KNX014 native C++ protocol and production UART adapter test runner.

This runs with an in-memory fake UART and 9 simulated Dallas/OneWire probes,
never opening a serial port, flashing a chip or sending a KNX telegram.
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
    wanted = os.environ.get("CXX", "")
    cxx_path = shutil.which(wanted) if wanted else shutil.which("g++")
    if not cxx_path and wanted:
        cxx_path = wanted
    if not cxx_path and MSYS_GPP.is_file():
        cxx_path = str(MSYS_GPP)
    if not cxx_path:
        print("ERROR: set CXX or install native g++", file=sys.stderr)
        return 2
    compiler = Path(cxx_path).resolve()
    env = os.environ.copy()
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    common = ["-I", str(ROOT / "lib/common"),
              "-I", str(ROOT / "tests/native/mocks"),
              "-I", str(ROOT / "src/temperature")]
    suites = [
        ("protocol", ["tests/native/test_temperature_protocol.cpp"], []),
        ("client", ["tests/native/test_temperature_client.cpp"], []),
        ("attiny_link", [
            "tests/native/test_temperature_link_integration.cpp",
            "src/temperature/temperature_link.cpp",
            "src/temperature/temperature.cpp",
            "src/temperature/temperatures.cpp"
        ], common),
        ("rp_bridge", [
            "tests/native/test_controller_uart_integration.cpp",
            "src/controller/temperature_bridge.cpp"
        ], common)
    ]
    with tempfile.TemporaryDirectory(prefix="openknx-knx014-") as tmp:
        for label, files, includes in suites:
            output = Path(tmp) / (label + (".exe" if os.name == "nt" else ""))
            args = [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    *includes, "-o", str(output),
                    *(str(ROOT / filename) for filename in files)]
            print("Building native KNX014 suite:", label, flush=True)
            r = subprocess.run(args, cwd=ROOT, env=env, check=False)
            if r.returncode != 0:
                return r.returncode
            print("Running native KNX014 suite:", label, flush=True)
            r = subprocess.run([str(output)], cwd=ROOT, env=env, check=False)
            if r.returncode != 0:
                return r.returncode
    print("RESULT: all four KNX014 native C++ test suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
