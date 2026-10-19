"""Enhance a freshly generated KNX085 firmware with buffered INA219 waveform evidence.
Used by generate_from_knx084.py; no hardware access.
"""
def enhance(src: str) -> str:
    # Preserve KNX084 technical baseline while updating motor-mode commentary.
    src=src.replace("// M1..M8 TB6612 enables and common direction outputs are ALWAYS LOW.",
                    "// M1..M8 idle LOW; only gated KNX085 bench pulses can activate M1/M2.")
    src=src.replace("// No KNX TX PIO, TPUart, Serial1, ACK generation, motor PWM or drive commands.",
                    "// No KNX TP TX; motor outputs require physical release, INA gate and USB ARM.")
    src=src.replace("#error \"KNX085 must be built in the isolated receive/temp-only environment\"",
                    "#error \"KNX085 must be built only as isolated gated diagnostic\"")
    def replace(old: str, new: str):
        nonlocal src
        n=src.count(old)
        if n!=1:
            raise ValueError(f"KNX085 trace anchor expected once, got {n}: {old[:60]!r}")
        src=src.replace(old,new,1)
    replace("int maxSeenMa=0;\n", """int maxSeenMa=0;
uint16_t lastRawShunt=0, inaConfig=0;
bool inaConfigOk=false;
uint8_t idleGoodSamples=0;
struct TraceRow {
    uint32_t elapsedMs;
    int16_t rawShunt;
    uint16_t busMv;
    uint8_t status;
};
constexpr unsigned kTraceSize=96;
TraceRow currentTrace[kTraceSize]{};
unsigned traceCount=0;

void printTrace() {
    if(!Serial)return;
    if(motor.active()){
        Serial.println(F("KNX085 REFUSED_TRACE_WHILE_RUNNING"));
        return;
    }
    Serial.print(F("KNX085 TRACE_BEGIN count="));Serial.println(traceCount);
    for(unsigned n=0;n<traceCount;++n){
        const TraceRow &t=currentTrace[n];
        Serial.print(F("KNX085 TRACE t_ms="));Serial.print(t.elapsedMs);
        Serial.print(F(" shunt_raw="));Serial.print(t.rawShunt);
        Serial.print(F(" shunt_uv="));Serial.print(t.rawShunt*10);
        Serial.print(F(" bus_mv="));Serial.print(t.busMv);
        Serial.print(F(" valid="));Serial.println(t.status);
    }
    Serial.println(F("KNX085 TRACE_END"));
}
""")
    replace("next.readOk=readInaReg(0x01,shunt) && readInaReg(0x02,bus);",
      """next.readOk=inaConfigOk &&
        readInaReg(0x01,shunt) && readInaReg(0x02,bus);""")
    replace("next.currentMa=(static_cast<int32_t>(static_cast<int16_t>(shunt))*10)/200;",
      """// 1 shunt_raw = 10 uV, 0.2 ohm means 0.05 mA each.
        // Integer mA used ONLY for software cutoff. TRACE retains raw resolution.
        lastRawShunt=shunt;
        next.currentMa=(static_cast<int32_t>(static_cast<int16_t>(shunt))*10)/200;""")
    replace("ina=next;\n    if(motor.active() && ina.currentMa>maxSeenMa)maxSeenMa=ina.currentMa;",
      """ina=next;
    if(!motor.active() && Knx085::powerOkay(ina,true) && idleGoodSamples<250)
        ++idleGoodSamples;
    else if(!Knx085::powerOkay(ina,motor.active()?false:true))
        idleGoodSamples=0;
    if(motor.active()) {
        if(ina.currentMa>maxSeenMa)maxSeenMa=ina.currentMa;
        if(traceCount<kTraceSize){
            currentTrace[traceCount++]=TraceRow{
                static_cast<uint32_t>(now-motor.started()),
                static_cast<int16_t>(lastRawShunt),
                static_cast<uint16_t>(ina.busMv),
                static_cast<uint8_t>(ina.readOk && !ina.overflow)};
        }
    }""")
    replace('Serial.print(F("KNX085 INA read_ok="));Serial.print(ina.readOk?1:0);',
      '''Serial.print(F("KNX085 INA addr=0x40 config=0x"));Serial.print(inaConfig,HEX);
    Serial.print(F(" config_ok="));Serial.print(inaConfigOk?1:0);
    Serial.print(F(" good_idle_samples="));Serial.println(idleGoodSamples);
    Serial.print(F("KNX085 INA read_ok="));Serial.print(ina.readOk?1:0);''')
    replace('const bool ok=motor.arm(millis(),KNX085_HARDWARE_GATE_APPROVED==1,ina);',
      '''const bool ok=motor.arm(millis(),KNX085_HARDWARE_GATE_APPROVED==1
                                    && inaConfigOk && idleGoodSamples>=5,ina);''')
    replace('''    if(strcmp(cmd,"MSTATUS")==0) {
        printMotor();
        return;
    }''','''    if(strcmp(cmd,"MSTATUS")==0) {
        printMotor();
        return;
    }
    if(strcmp(cmd,"TRACE")==0){
        printTrace();
        return;
    }''')
    replace("maxSeenMa=0;\n        startOutputs();", "maxSeenMa=0;\n        traceCount=0;\n        startOutputs();")
    replace('RXDUMP INA MSTATUS STOP CLEARFAULT', 'RXDUMP INA MSTATUS TRACE STOP CLEARFAULT')
    replace('''    Wire.setTimeout(15);
    inaInitialized=true;
    sampleIna(true);''','''    Wire.setTimeout(15);
    inaInitialized=true;
    inaConfigOk=readInaReg(0x00,inaConfig)
        && inaConfig!=0 && inaConfig!=0xffff
        && (inaConfig&0x07)!=0;
    sampleIna(true);''')
    return src
