#!/usr/bin/env python3
"""Build/run native C++ tests for the actual KNX013 sampler core and channels.

Requires g++ (CXX override supported). Uses the genuine sampler_core.hpp and
temperature.cpp/temperatures.cpp with small OneWire/Dallas test doubles.
No hardware, motor power, serial port or KNX is accessed.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASH_MSYS_GXX = Path(
    r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe"
)


def run_suite(compiler: Path, env: dict[str, str], output: Path,
              sources: list[Path], extra_args: list[str]) -> int:
    args = [
        str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror",
        *extra_args, "-o", str(output),
        *(str(source) for source in sources),
    ]
    print(f"Building {output.stem}...", flush=True)
    build = subprocess.run(args, cwd=ROOT, env=env, check=False)
    if build.returncode != 0:
        print(f"FAIL: C++ compilation exited {build.returncode}")
        return build.returncode
    print(f"Running {output.stem}...", flush=True)
    test = subprocess.run([str(output)], cwd=ROOT, env=env, check=False)
    if test.returncode != 0:
        print(f"FAIL: test exited {test.returncode}")
        return test.returncode
    return 0


def main() -> int:
    requested = os.environ.get("CXX", "").strip()
    selected = shutil.which(requested) if requested else shutil.which("g++")
    if not selected and requested:
        selected = requested
    if not selected and ASH_MSYS_GXX.is_file():
        selected = str(ASH_MSYS_GXX)
    if not selected:
        print("ERROR: g++ not found. Set CXX to a native C++ compiler.",
              file=sys.stderr)
        return 2

    compiler = Path(selected).resolve()
    env = os.environ.copy()
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx013-") as directory:
        temp = Path(directory)
        suffix = ".exe" if os.name == "nt" else ""

        result = run_suite(
            compiler, env, temp / ("sampler_core" + suffix),
            [ROOT / "tests/native/test_sampler_core.cpp"], [],
        )
        if result != 0:
            return result

        test_dir = ROOT / "tests/native"
        result = run_suite(
            compiler, env, temp / ("temperature_integration" + suffix),
            [
                test_dir / "test_temperature_integration.cpp",
                ROOT / "src/temperature/temperature.cpp",
                ROOT / "src/temperature/temperatures.cpp",
            ],
            [
                "-I", str(test_dir / "mocks"),
                "-I", str(ROOT / "src/temperature"),
            ],
        )
        if result != 0:
            return result

    print("RESULT: all KNX013 native C++ tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
