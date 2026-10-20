#!/usr/bin/env python3
"""Generate KNX095 first bounded INA219 reference-seek firmware from KNX094."""
from pathlib import Path
import shutil

base=Path(__file__).resolve().parents[1]/"knx094_motor_10s"
dest=Path(__file__).resolve().parent
(dest/"src").mkdir(exist_ok=True)
for part in ("main.cpp","motor_gate.hpp"):
    shutil.copyfile(base/"src"/part,dest/"src"/part)

def replace_once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new,1)

p=dest/"src"/"motor_gate.hpp"
s=p.read_text("utf8")
s=replace_once(s,"kMaxPulseMs=10000","kMaxPulseMs=15000")
p.write_text(s,"utf8",newline="\n")

p=dest/"src"/"main.cpp"
s=p.read_text("utf8")
s="// KNX095: first 15s M1 R homing-search trial, stop on current rise or current collapse; no automatic retry.\n"+s
s=replace_once(s,
 "constexpr unsigned kTraceSize=1500; // >=10s / 8ms, retains full raw INA trace",
 "constexpr unsigned kTraceSize=2200; // 15s / 8ms = 1875 samples, preserve entire trace")
s=replace_once(s,"constexpr uint32_t kStallGuardStartMs=400;",
                 "constexpr uint32_t kEndstopGuardStartMs=450;")
s=replace_once(s,"constexpr int kStallCurrentMa=60;",
                 "constexpr int kEndstopHighCurrentMa=45;\nconstexpr int kEndstopLowCurrentMa=5;")
s=replace_once(s,"constexpr uint8_t kStallConsecutive=6;",
                 "constexpr uint8_t kEndstopConsecutive=6;")
s=replace_once(s,"uint8_t stallHighCount=0;",
                 "uint8_t endstopHighCount=0;\nuint8_t endstopLowCount=0;")
s=replace_once(s,"bool stallGuardTripped=false;",
                 """const char* endstopKind="NONE";
uint32_t endstopAtMs=0;
int endstopAtMa=0;
""")
old='''        // KNX094: after inrush settles (>400ms) abort a sustained rise
        // above 60mA for 6 consecutive valid samples (~48ms).
        // Never infer a mechanical endstop without a current rise.
        if(static_cast<uint32_t>(now-motor.started())>=kStallGuardStartMs) {
            if(ina.readOk && !ina.overflow &&
               ina.currentMa>=kStallCurrentMa) {
                if(stallHighCount<kStallConsecutive)++stallHighCount;
            } else stallHighCount=0;
            if(stallHighCount>=kStallConsecutive) {
                stallGuardTripped=true;
                motor.trip();
            }
        }
'''
new='''        // First reference-search candidate, NEVER assert homing success
        // from a mere current threshold alone.
        // Inrush ignored for 450ms. Six good consecutive ~8ms samples
        // above 45mA => LOAD_RISE; near zero <=5mA => CURRENT_CUT
        // (for devices with possible built-in limit switch).
        // Both conditions stop M1 IMMEDIATELY via latched MotorGate fault.
        // Invalid INA, USB dropout, rail faults and 120mA absolute limit
        // are independently stopped by motor.tick().
        if(static_cast<uint32_t>(now-motor.started())>=kEndstopGuardStartMs &&
           motor.active()) {
            if(ina.readOk && !ina.overflow) {
                if(ina.currentMa>=kEndstopHighCurrentMa) {
                    if(endstopHighCount<kEndstopConsecutive)++endstopHighCount;
                } else endstopHighCount=0;
                if(ina.currentMa>=0 && ina.currentMa<=kEndstopLowCurrentMa) {
                    if(endstopLowCount<kEndstopConsecutive)++endstopLowCount;
                } else endstopLowCount=0;
            } else {
                endstopHighCount=0;
                endstopLowCount=0;
            }
            const bool rising=endstopHighCount>=kEndstopConsecutive;
            const bool opening=endstopLowCount>=kEndstopConsecutive;
            if(rising || opening) {
                endstopKind=rising?"LOAD_RISE":"CURRENT_CUT";
                endstopAtMs=static_cast<uint32_t>(now-motor.started());
                endstopAtMa=ina.currentMa;
                motor.trip();
                if(Serial){
                    Serial.print(F("KNX095 ENDSTOP_CANDIDATE kind="));
                    Serial.print(endstopKind);
                    Serial.print(F(" t_ms="));Serial.print(endstopAtMs);
                    Serial.print(F(" current_ma="));Serial.print(endstopAtMa);
                    Serial.print(F(" bus_mv="));Serial.println(ina.busMv);
                }
            }
        }
'''
s=replace_once(s,old,new)
s=replace_once(s,
 '''if(strcmp(cmd,"KNX093")==0) {
        if(Serial){
            Serial.print(F("KNX094 M1_R_ONLY duration_ms=10000 motor_gate="));
            Serial.print(KNX085_HARDWARE_GATE_APPROVED);
            Serial.print(F(" limit_ma=120 stall_ma=60 after_ms=400 consecutive=6 latched="));
            Serial.println(stallGuardTripped?1:0);
        }
        return;
    }''',
 '''if(strcmp(cmd,"KNX095")==0) {
        if(Serial){
            Serial.print(F("KNX095 M1_R_SEARCH duration_ms=15000 motor_gate="));
            Serial.print(KNX085_HARDWARE_GATE_APPROVED);
            Serial.print(F(" limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop="));
            Serial.println(endstopKind);
        }
        return;
    }''')
s=replace_once(s,"if(ch!=1 || dir!='R' || ms!=10000)",
                 "if(ch!=1 || dir!='R' || ms!=15000)")
s=replace_once(s,"KNX094 REFUSED_ONLY_M1_R_10000",
                 "KNX095 REFUSED_ONLY_M1_R_15000")
s=replace_once(s,
 '''        stallHighCount=0;
        stallGuardTripped=false;
        lastLiveReportMs=0;''',
 '''        endstopHighCount=0;
        endstopLowCount=0;
        endstopKind="NONE";
        endstopAtMs=0;
        endstopAtMa=0;
        lastLiveReportMs=0;''')
s=replace_once(s,"KNX094 LIVE t_ms=","KNX095 LIVE t_ms=")
s=s.replace("KNX094:","KNX095:")
p.write_text(s,"utf8",newline="\n")

pio=(base/"platformio.ini").read_text("utf8")
pio=pio.replace("KNX094","KNX095").replace("knx094_m1_reverse_10000",
                                             "knx095_m1_reference_15000")
pio=pio.replace("M1 R 10000ms","M1 R reference 15000ms")
(dest/"platformio.ini").write_text(pio.rstrip()+"\n",encoding="utf8",newline="\n")
print("KNX095 source generated: ONLY M1 R 15000, 8ms INA trace x2200, 45mA load rise or <=5mA cutoff at six samples after t450ms; max120mA")
