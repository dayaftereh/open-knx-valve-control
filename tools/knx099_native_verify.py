#!/usr/bin/env python3
"""KNX099 offline C++ model verification against real KNX097 INA traces.

Windows LLO Desktop Visual Studio 2022 MSVC, never COM/USB/KNX/GPIO.
Outputs binaries and execution logs only in external Runtime/KNX099.
"""
from __future__ import annotations

import argparse,json,os,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MSVC=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat")
OUT=Path(r"C:\ASH\Workspace\Runtime\KNX099")
TRACE=Path(r"C:\ASH\Workspace\Runtime\KNX097")
CAL=ROOT/"config"/"knx098_m1_bench_calibration.json"
HEADER=ROOT/"lib"/"common"/"knx099_m1_position_model.hpp"

def verified_cpp_defaults():
    p=json.loads(CAL.read_text("utf8"))
    s=HEADER.read_text("utf8")
    expected={
       "fullRMs":round(p["directional_stroke_ms"]["R"]),
       "fullFMs":round(p["directional_stroke_ms"]["F"]),
       "maxSeekMs":p["guards"]["max_stroke_ms"],
       "samplePeriodMs":p["guards"]["ina_period_ms"],
       "startupIgnoreMs":p["guards"]["ina_startup_ignore_ms"],
       "riseCurrentMa":p["guards"]["ina_threshold_ma"],
       "riseConsecutive":p["guards"]["ina_consecutive_samples"],
       "cutCurrentMa":p["guards"]["current_cut_ma"],
       "absoluteCurrentMa":p["guards"]["absolute_current_limit_ma"],
       "idleCurrentMa":p["guards"]["idle_current_limit_ma"],
       "busMinMv":p["guards"]["motor_bus_min_mv"],
       "busMaxMv":p["guards"]["motor_bus_max_mv"]}
    for name,actual in expected.items():
        m=re.search(r"\b"+re.escape(name)+r"\s*=\s*(\d+)\s*;",s)
        if not m or int(m.group(1))!=actual:
            raise RuntimeError(f"KNX099 default {name} differs from KNX098 freeze: {m and m.group(1)} versus {actual}")
    forbidden=("digitalWrite(","gpio_put(","knx.groupObject(","Serial.","Wire.")
    executable_lines="\n".join(line for line in s.splitlines()
                               if not line.lstrip().startswith("//"))
    for text in forbidden:
        if text in executable_lines:
            raise RuntimeError(f"Actuator/transport primitive forbidden from portable model: {text}")
    print("CALIBRATION_CONTRACT_PASS",json.dumps(expected),flush=True)
    return expected

def build_and_run(source,exe,params):
    if not MSVC.is_file():
        raise RuntimeError(f"Windows MSVC vcvars64.bat unavailable: {MSVC}")
    OUT.mkdir(parents=True,exist_ok=True)
    src=ROOT/"tests"/"native"/source
    target=OUT/exe
    obj=OUT/(src.stem+".obj")
    cmd=f'call "{MSVC}" >nul && cl.exe /nologo /std:c++17 /EHsc /W4 /WX /Od /Fo:"{obj}" /Fe:"{target}" "{src}"'
    p=subprocess.run(cmd,shell=True,cwd=ROOT,
                     capture_output=True,text=True,errors="replace",timeout=100)
    if p.returncode:
        raise RuntimeError(f"KNX099 MSVC compiler error {p.returncode} {p.stdout[-1400:]} {p.stderr[-1400:]}")
    print("MSVC_BUILD_PASS",source,flush=True)
    q=subprocess.run([str(target),*params],cwd=ROOT,
                     capture_output=True,text=True,errors="replace",timeout=30)
    if q.returncode:
        raise RuntimeError(f"KNX099 native run error {q.returncode} {q.stdout[-1500:]} {q.stderr[-1500:]}")
    print(q.stdout.strip(),flush=True)
    return q.stdout

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-replay",action="store_true",
                        help="Validate C++ policy only; skips archived six CSV files")
    args=parser.parse_args()
    verified_cpp_defaults()
    native=build_and_run("test_knx099_position_model.cpp",
                         "knx099_position_native.exe",[])
    if not args.no_replay:
        if not TRACE.is_dir():
            raise RuntimeError("Original KNX097 traces unavailable for replay")
        replay=build_and_run("test_knx099_trace_replay.cpp",
                            "knx099_replay.exe",[str(TRACE)])
        assert "REAL 6/6" in replay
    print("KNX099_SOFTWARE_NO_HARDWARE_ACTION_PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("KNX099_OFFLINE_FAILED",repr(exc),file=sys.stderr)
        raise SystemExit(3)
