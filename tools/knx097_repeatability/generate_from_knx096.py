#!/usr/bin/env python3
"""Generate KNX097 3x R/F repeatability-bench MCU firmware from KNX096."""
from pathlib import Path
import shutil
base=Path(__file__).resolve().parents[1]/"knx096_m1_fullstroke"
dest=Path(__file__).resolve().parent
(dest/"src").mkdir(parents=True,exist_ok=True)
for file in ("main.cpp","motor_gate.hpp"):
    shutil.copyfile(base/"src"/file,dest/"src"/file)
def once(src,a,b):
    assert src.count(a)==1,(a,src.count(a))
    return src.replace(a,b,1)
p=dest/"src"/"main.cpp"
s=p.read_text("utf8")
s="// KNX097: 3x R/F alternating, MCU controlled 30s limit, INA cutoff, no auto-drive.\n"+s
s=once(s,
'constexpr unsigned kTraceSize=4200; // >=30s / 8ms = 3750 samples',
'constexpr unsigned kTraceSize=4800; // >=30s / 8ms = 3750 samples')
s=once(s,
'const char* endstopKind="NONE";',
'''const char* endstopKind="NONE";
const char* lastLegKind="NONE";
char expectedDirection='R'; // Board is at previous F-side load-rise candidate
char lastLegDirection='-';
uint8_t legsCompleted=0;
constexpr uint8_t kLegsMaximum=6;
constexpr uint32_t kShortestPlausibleLegMs=12000;
''')
s=once(s,'motor.trip();\n                if(Serial){',
'''motor.trip();
                // Advance only on a plausible load-rise with sufficient travel.
                // Abnormal short runs, CURRENT_CUT and >30s do not authorize
                // another leg. The host also checks every trace before ARM.
                lastLegDirection=motor.direction();
                if(rising && endstopAtMs>=kShortestPlausibleLegMs &&
                   legsCompleted<kLegsMaximum) {
                    ++legsCompleted;
                    expectedDirection=(expectedDirection=='R')?'F':'R';
                    lastLegKind="LOAD_RISE";
                } else {
                    lastLegKind=rising?"TOO_SHORT_LOAD_RISE":"CURRENT_CUT";
                }
                if(Serial){''')
s=once(s,'KNX096 ENDSTOP_CANDIDATE kind=',
       'KNX097 ENDSTOP_CANDIDATE kind=')
s=once(s,'KNX096 LIVE t_ms=','KNX097 LIVE t_ms=')
old='''if(strcmp(cmd,"KNX096")==0) {
        if(Serial){
            Serial.print(F("KNX096 M1_F_SEARCH duration_ms=30000 motor_gate="));
            Serial.print(KNX085_HARDWARE_GATE_APPROVED);
            Serial.print(F(" limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop="));
            Serial.println(endstopKind);
        }
        return;
    }'''
new='''if(strcmp(cmd,"KNX097")==0) {
        if(Serial){
            Serial.print(F("KNX097 M1_ALTERNATE duration_ms=30000 motor_gate="));
            Serial.print(KNX085_HARDWARE_GATE_APPROVED);
            Serial.print(F(" limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 next_dir="));
            Serial.print(expectedDirection);
            Serial.print(F(" legs_done="));Serial.print(legsCompleted);
            Serial.print(F(" last_kind="));Serial.print(lastLegKind);
            Serial.print(F(" last_dir="));Serial.println(lastLegDirection);
        }
        return;
    }'''
s=once(s,old,new)
s=once(s,
'// Exact M1 F 30000 only (opposite end). No R/M2/other durations.',
'// Only 6 alternating M1 legs R F R F R F. Each requires explicit ARM.')
s=once(s,
'''if(ch!=1 || dir!='F' || ms!=30000) {
            forceAllInactive();
            if(Serial)Serial.println(F("KNX096 REFUSED_ONLY_M1_F_30000"));''',
'''if(ch!=1 || (dir!='F' && dir!='R') || ms!=30000 ||
           dir!=expectedDirection || legsCompleted>=kLegsMaximum ||
           (legsCompleted!=0 && strcmp(lastLegKind,"LOAD_RISE")!=0)) {
            forceAllInactive();
            if(Serial)Serial.println(F("KNX097 REFUSED_LEG_ORDER_OR_LIMIT"));''')
s=s.replace('KNX096 COMMANDS STATUS INA MSTATUS TRACE STOP CLEARFAULT ARM MOTORS PULSE M1 F 30000 HELP',
            'KNX097 COMMANDS STATUS INA MSTATUS TRACE STOP ARM MOTORS PULSE M1 R|F 30000 KNX097')
assert not any("KNX096" in line for line in s.splitlines() if not line.strip().startswith("//"))
p.write_text(s,encoding="utf8",newline="\n")
ini=(base/"platformio.ini").read_text("utf8")
ini=ini.replace("KNX096","KNX097").replace("knx096_m1_fullstroke_30000","knx097_m1_repeat_30000")
ini=ini.replace("M1 F full-stroke max30000ms","M1 3x R/F alternating max30000ms per leg")
(dest/"platformio.ini").write_text(ini.rstrip()+"\n","utf8",newline="\n")
print("KNX097 generated: R/F exactly 6 stages, min12s each, 30s MCU timeout, 120mA cap, INA8ms, >=45mA x6 => stop, 4800 sample trace")
