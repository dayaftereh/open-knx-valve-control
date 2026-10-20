#!/usr/bin/env python3
"""Generate bounded KNX096 F full-stroke firmware from checked KNX095."""
from pathlib import Path
import shutil
base=Path(__file__).resolve().parents[1]/"knx095_m1_reference"
dest=Path(__file__).resolve().parent
(dest/"src").mkdir(parents=True,exist_ok=True)
for f in ("main.cpp","motor_gate.hpp"):
    shutil.copyfile(base/"src"/f,dest/"src"/f)
def sub1(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)

gate=dest/"src"/"motor_gate.hpp"
s=gate.read_text("utf8")
s=sub1(s,"kMaxPulseMs=15000","kMaxPulseMs=30000")
gate.write_text(s,"utf8",newline="\n")

main=dest/"src"/"main.cpp"
s=main.read_text("utf8")
s="// KNX096 USB-only M1 F full-stroke 30s cap; abort on first sustained endstop current signature.\n"+s
s=sub1(s,"constexpr unsigned kTraceSize=2200; // 15s / 8ms = 1875 samples, preserve entire trace",
          "constexpr unsigned kTraceSize=4200; // >=30s / 8ms = 3750 samples")
s=sub1(s,"KNX095 ENDSTOP_CANDIDATE","KNX096 ENDSTOP_CANDIDATE")
s=sub1(s,"if(strcmp(cmd,\"KNX095\")==0)","if(strcmp(cmd,\"KNX096\")==0)")
s=sub1(s,"KNX095 M1_R_SEARCH duration_ms=15000","KNX096 M1_F_SEARCH duration_ms=30000")
s=sub1(s,"if(ch!=1 || dir!='R' || ms!=15000)","if(ch!=1 || dir!='F' || ms!=30000)")
s=sub1(s,"KNX095 REFUSED_ONLY_M1_R_15000","KNX096 REFUSED_ONLY_M1_F_30000")
s=sub1(s,"KNX095 LIVE t_ms=","KNX096 LIVE t_ms=")
s=s.replace("KNX095:","KNX096:")
s=s.replace("// Exact M1 R 800 only. No F, no M2, no second duration.",
            "// Exact M1 F 30000 only (opposite end). No R/M2/other durations.")
# Legacy HELP was hard-coded 50..250, correct displayed help without enabling other commands
s=s.replace("KNX085 COMMANDS STATUS TEMPS RXSTATS RXDUMP INA MSTATUS TRACE STOP CLEARFAULT ARM MOTORS PULSE M1|M2 F|R 50..250 HELP",
            "KNX096 COMMANDS STATUS INA MSTATUS TRACE STOP CLEARFAULT ARM MOTORS PULSE M1 F 30000 HELP")
main.write_text(s,"utf8",newline="\n")

ini=(base/"platformio.ini").read_text("utf8")
ini=ini.replace("KNX095","KNX096").replace("knx095_m1_reference_15000","knx096_m1_fullstroke_30000")
ini=ini.replace("M1 R reference 15000ms","M1 F full-stroke max30000ms")
(dest/"platformio.ini").write_text(ini.rstrip()+"\n","utf8",newline="\n")
print("KNX096 F-only build source prepared: deadline30s, 4200 x 8ms raw trace slots, rise45mA x6 after450ms and cut0..5mA x6, 120mA absolute cap")
