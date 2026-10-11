#!/usr/bin/env python3
"""Build RP2040 controller in a new isolated temporary source tree.

The PlatformIO pre-script runs OpenKNXproducer and otherwise overwrites
the tracked include/knxprod.hpp. This tool never builds inside the canonical
repository. --keep preserves the temporary build directory for inspection.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIO_FALLBACK = Path(r"C:\Users\LLO\.platformio\penv\Scripts\pio.exe")
PRODUCER_FALLBACK = Path(r"C:\ASH\Tools\OpenKNXproducer-3.12.2\OpenKNXproducer.exe")
ASSET_FILES = (
    "open-knx-producer.py",
    "open-knx-valve-control.xml",
    "init_updi.py",
    "autodetect_port.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="keep the isolated build including generated UF2")
    args = parser.parse_args()

    pio = shutil.which("pio") or shutil.which("platformio")
    if not pio and PIO_FALLBACK.exists():
        pio = str(PIO_FALLBACK)
    producer = shutil.which("OpenKNXproducer.exe")
    if not producer and PRODUCER_FALLBACK.exists():
        producer = str(PRODUCER_FALLBACK)
    if not pio or not producer:
        print("ERROR: PlatformIO or OpenKNXproducer unavailable", file=sys.stderr)
        return 2

    canonical_header = ROOT / "include" / "knxprod.hpp"
    canonical_before = sha256(canonical_header)
    temp = Path(tempfile.mkdtemp(prefix="openknx-controller-isolated-"))
    print("Isolated build:", temp, flush=True)
    code = 1
    try:
        shutil.copy2(ROOT / "platformio.ini", temp / "platformio.ini")
        for part in ("src", "lib", "include"):
            shutil.copytree(ROOT / part, temp / part)
        (temp / "assets").mkdir()
        for filename in ASSET_FILES:
            shutil.copy2(ROOT / "assets" / filename, temp / "assets" / filename)

        env = os.environ.copy()
        env["PATH"] = str(Path(producer).parent) + os.pathsep + env.get("PATH", "")
        result = subprocess.run([str(pio), "run", "-e", "controller"],
                                cwd=str(temp), env=env, check=False)
        code = result.returncode
        print("Controller build exit:", code, flush=True)
        built = temp / ".pio/build/controller/firmware.uf2"
        print("UF2 generated:", built.is_file(), flush=True)
        if code == 0 and not built.is_file():
            code = 4
    except OSError as e:
        print("ERROR:", e, file=sys.stderr)
        code = 5
    finally:
        canonical_after = sha256(canonical_header)
        print("Canonical knxprod.hpp unchanged:",
              canonical_before == canonical_after, flush=True)
        if canonical_before != canonical_after:
            code = 6
        if args.keep or code != 0:
            print("Saved isolated workspace:", temp, flush=True)
        else:
            # PlatformIO git dependencies can contain Windows read-only .git
            # pack files. Restore write permissions for our OWN temporary
            # files before retrying deletion; do not touch the source tree.
            def clear_readonly(func, filename, error_info):
                os.chmod(filename, stat.S_IWRITE | stat.S_IREAD)
                func(filename)

            try:
                shutil.rmtree(temp, onerror=clear_readonly)
            except OSError as exc:
                # A successful build must not be reported as failed simply
                # because Windows holds an isolated build-cache file open.
                print("WARNING: build PASS, temporary cleanup incomplete:",
                      exc, flush=True)
                print("Remaining workspace:", temp, flush=True)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
