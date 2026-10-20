#!/usr/bin/env python3
"""KNX104 offline native C++ / ETS proposal checks on LLO Desktop.

No Serial, GPIO, GroupObject, KNX bus, motor, flash or Git I/O.
Build artifacts stay outside repository under Runtime/KNX104.
"""
from __future__ import annotations
import subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MSVC=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat")
BUILD=Path(r"C:\ASH\Workspace\Runtime\KNX104")
SOURCE=ROOT/"tests/native/test_knx104_m1_ets_contract.cpp"

def run(command,timeout=35):
    p=subprocess.run(command,cwd=ROOT,capture_output=True,
                     text=True,errors="replace",timeout=timeout,
                     shell=isinstance(command,str))
    if p.returncode:
        raise RuntimeError(f"Exit {p.returncode}: {str(command)[:150]}: {p.stdout[-1300:]} {p.stderr[-1300:]}")
    print(p.stdout.strip())
    if p.stderr.strip(): print(p.stderr[-800:].strip())

def main():
    if not MSVC.is_file() or not SOURCE.is_file():
        raise RuntimeError("MSVC or KNX104 native test source absent")
    BUILD.mkdir(parents=True,exist_ok=True)
    exe=BUILD/"knx104_native.exe"
    obj=BUILD/"knx104_native.obj"
    command=(f'call "{MSVC}" >nul && cl.exe /nologo /std:c++17 '
             f'/EHsc /W4 /WX /Od /Fo:"{obj}" /Fe:"{exe}" "{SOURCE}"')
    run(command,timeout=100)
    run([str(exe)])
    run([sys.executable,"tools/knx104_ets_preview.py"])
    run([sys.executable,"tools/test_knx104_ets_preview.py"])
    print("KNX104_OFFLINE_ETS_POSITION_CONTRACT_PASS")

if __name__=="__main__":
    try: main()
    except Exception as e:
        print("KNX104_OFFLINE_VERIFY_FAILED",repr(e),file=sys.stderr)
        raise SystemExit(3)
