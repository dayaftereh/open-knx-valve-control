#!/usr/bin/env python3
"""KNX026 portable display/model tests, including ARDUINO compile hardlock."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
FALLBACK = Path(r"C:\ASH\Tools\CFD\OpenFOAM\v2206\msys64\usr\bin\g++.exe")
def main():
    picked = os.environ.get("CXX", "")
    cxx = shutil.which(picked) if picked else shutil.which("g++")
    if picked and not cxx: cxx = picked
    if not cxx and FALLBACK.is_file(): cxx = str(FALLBACK)
    if not cxx:
        print("FAIL no C++17 compiler")
        return 2
    env = os.environ.copy()
    env["PATH"] = str(Path(cxx).resolve().parent) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="openknx-knx026-") as tmp:
        for i, src in enumerate(("test_knx026_hmi_diagnostics.cpp",
                                 "test_knx026_arduino_hardlock.cpp")):
            exe = str(Path(tmp) / f"knx026_{i}.exe")
            cmd = [str(cxx), "-std=c++17", "-Wall", "-Wextra",
                   "-Werror", "-pedantic", "-o", exe,
                   str(ROOT / "tests" / "native" / src)]
            print("BUILD", src, flush=True)
            rc = subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode
            if rc: return rc
            print("RUN", src, flush=True)
            rc = subprocess.run([exe], cwd=tmp, env=env, check=False).returncode
            if rc: return rc
    print("KNX026 2/2 native suites PASS")
    return 0
if __name__ == "__main__":
    sys.exit(main())
