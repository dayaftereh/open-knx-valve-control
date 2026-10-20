#!/usr/bin/env python3
"""Derive KNX094 USB-only 10s M1 reverse diagnostic from accepted KNX093."""
from pathlib import Path
import shutil

base=Path(__file__).resolve().parents[1]/"knx093_m1_long"
dest=Path(__file__).resolve().parent
(dest/"src").mkdir(exist_ok=True)
for name in ("main.cpp","motor_gate.hpp"):
    shutil.copyfile(base/"src"/name,dest/"src"/name)

p=dest/"src"/"motor_gate.hpp"
s=p.read_text(encoding="utf8")
assert s.count("kMaxPulseMs=800")==1
s=s.replace("kMaxPulseMs=800","kMaxPulseMs=10000")
p.write_text(s,encoding="utf8",newline="\n")

p=dest/"src"/"main.cpp"
s=p.read_text(encoding="utf8")
s="// KNX094 M1 R max 10s USB-only monitored hard-end observation.\n"+s
replace={
"constexpr unsigned kTraceSize=160; // 800ms / 8ms = ~100 readings":
 "constexpr unsigned kTraceSize=1500; // >=10s / 8ms, retains full raw INA trace",
"constexpr uint32_t kStallGuardStartMs=100;":
 "constexpr uint32_t kStallGuardStartMs=400;",
"constexpr int kStallCurrentMa=90;":
 "constexpr int kStallCurrentMa=60;",
"constexpr uint8_t kStallConsecutive=4;":
 "constexpr uint8_t kStallConsecutive=6;",
"uint8_t stallHighCount=0;":
 "uint8_t stallHighCount=0;\nuint32_t lastLiveReportMs=0;",
"KNX093 M1_R_ONLY duration_ms=800":
 "KNX094 M1_R_ONLY duration_ms=10000",
" limit_ma=120 stall_ma=90 after_ms=100 consecutive=4 latched=":
 " limit_ma=120 stall_ma=60 after_ms=400 consecutive=6 latched=",
"if(ch!=1 || dir!='R' || ms!=800)":
 "if(ch!=1 || dir!='R' || ms!=10000)",
"KNX093 REFUSED_ONLY_M1_R_800":
 "KNX094 REFUSED_ONLY_M1_R_10000",
"        stallHighCount=0;\n        stallGuardTripped=false;":
 "        stallHighCount=0;\n        stallGuardTripped=false;\n        lastLiveReportMs=0;",
}
for old,new in replace.items():
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new,1)
start=s.index("        // A blocked gearbox can draw <120mA")
end=s.index("        if(static_cast<uint32_t>(now-motor.started())>=kStallGuardStartMs)",start)
s=s[:start]+("""        // KNX094: after inrush settles (>400ms) abort a sustained rise
        // above 60mA for 6 consecutive valid samples (~48ms).
        // Never infer a mechanical endstop without a current rise.
""")+s[end:]
needle='''    const bool wasActive=motor.active();
    sampleIna();
    motor.tick(millis(),static_cast<bool>(Serial),ina);
'''
assert s.count(needle)==1
s=s.replace(needle,'''    const bool wasActive=motor.active();
    sampleIna();
    // Low-bandwidth live telemetry (~5 Hz), never motor control by host
    // timing. Firmware continues sampling at 8ms and trips locally.
    if(motor.active() && Serial) {
        const uint32_t t=static_cast<uint32_t>(millis()-motor.started());
        if(t>=lastLiveReportMs+200u) {
            lastLiveReportMs=t;
            Serial.print(F("KNX094 LIVE t_ms="));Serial.print(t);
            Serial.print(F(" current_ma="));Serial.print(ina.currentMa);
            Serial.print(F(" shunt_raw="));Serial.print(static_cast<int16_t>(lastRawShunt));
            Serial.print(F(" bus_mv="));Serial.println(ina.busMv);
        }
    }
    motor.tick(millis(),static_cast<bool>(Serial),ina);
''',1)
assert '#include <Wire.h>' in s
p.write_text(s,encoding="utf8",newline="\n")
ini=(base/"platformio.ini").read_text(encoding="utf8")
ini=ini.replace("KNX093 ONLY M1 R 800ms","KNX094 ONLY M1 R 10000ms")
ini=ini.replace("KNX093", "KNX094").replace("knx093_m1_reverse_800","knx094_m1_reverse_10000")
(dest/"platformio.ini").write_text(ini.rstrip()+"\n",encoding="utf8",newline="\n")
print("KNX094 generate PASS 10s max, INA 8ms, full trace, live telemetry, 60mA x6 stall after 400ms")
