#!/usr/bin/env python3
"""One-shot deterministic fork of KNX084 into an isolated KNX085 diagnosis image.

Input is always the committed KNX084 firmware; destination is only KNX085.
Run from repository root with platformio Python. Do not upload or touch COM.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/"tools/knx084_passive_rx_temp/src/main.cpp").read_text(encoding="utf8")
target=Path(__file__).parent/"src/main.cpp"

def one(old,new):
    global source
    count=source.count(old)
    if count!=1:
        raise RuntimeError(f"expected exactly one anchor, found {count}: {old[:100]!r}")
    source=source.replace(old,new,1)

one("#include <Arduino.h>", """#include <Arduino.h>
#include <Wire.h>
#include "motor_gate.hpp"
""")
source=source.replace("KNX084", "KNX085")
source=source.replace("KNX085_RECEIVE_TEMP_ONLY", "KNX085_MOTOR_DIAG")
one('#endif\n\nnamespace {', '''#endif
#ifndef KNX085_HARDWARE_GATE_APPROVED
#error "KNX085 requires an explicit hardware-output gate value"
#endif
#if KNX085_HARDWARE_GATE_APPROVED != 0 && KNX085_HARDWARE_GATE_APPROVED != 1
#error "Hardware gate must be exactly 0 or 1"
#endif

namespace {''')

one("uint8_t inputLength=0;\n", """uint8_t inputLength=0;

// V1.2 U23 INA219: SDA=GPIO4 / SCL=GPIO5; 0x40 is a candidate
// until physical A0/A1 and I2C readback are confirmed. R29 is NOT
// considered characterized by the nominal schematic value alone.
constexpr uint8_t kInaSda=4, kInaScl=5, kInaCandidate=0x40;
constexpr uint32_t kInaIdleIntervalMs=200, kInaRunIntervalMs=8;
Knx085::MotorGate motor;
Knx085::InaSample ina{};
uint32_t lastInaMs=0;
bool inaInitialized=false;
int maxSeenMa=0;

bool readInaReg(uint8_t reg,uint16_t& value) {
    Wire.beginTransmission(kInaCandidate);
    Wire.write(reg);
    if(Wire.endTransmission(false)!=0)return false;
    if(Wire.requestFrom(kInaCandidate,static_cast<uint8_t>(2))!=2)return false;
    const int high=Wire.read(),low=Wire.read();
    if(high<0 || low<0)return false;
    value=(static_cast<uint16_t>(high)<<8)|static_cast<uint16_t>(low);
    return true;
}
void sampleIna(bool force=false) {
    if(!inaInitialized)return;
    const uint32_t now=millis();
    const uint32_t interval=motor.active()?kInaRunIntervalMs:kInaIdleIntervalMs;
    if(!force && lastInaMs &&
       static_cast<uint32_t>(now-lastInaMs)<interval)return;
    lastInaMs=now;
    uint16_t shunt=0,bus=0;
    Knx085::InaSample next{};
    next.readOk=readInaReg(0x01,shunt) && readInaReg(0x02,bus);
    if(next.readOk){
        // INA219 raw shunt LSB = 10 uV. ONLY with verified R29=200 mOhm,
        // 1 raw count = 0.05 mA; displayed mA is provisional until then.
        next.currentMa=(static_cast<int32_t>(static_cast<int16_t>(shunt))*10)/200;
        next.busMv=static_cast<int>((bus>>3)*4);
        next.overflow=(bus&1u)!=0u;
    }
    ina=next;
    if(motor.active() && ina.currentMa>maxSeenMa)maxSeenMa=ina.currentMa;
}
void printIna() {
    if(!Serial)return;
    Serial.print(F("KNX085 INA read_ok="));Serial.print(ina.readOk?1:0);
    Serial.print(F(" bus_mv="));Serial.print(ina.busMv);
    Serial.print(F(" current_ma_assuming_R29_200mohm="));Serial.print(ina.currentMa);
    Serial.print(F(" overflow="));Serial.print(ina.overflow?1:0);
    Serial.print(F(" idle_ok="));Serial.print(Knx085::powerOkay(ina,true)?1:0);
    Serial.println(F(" SHUNT_AND_SUPPLY_AS_BUILT_NOT_YET_MEASURED"));
}
void printMotor() {
    if(!Serial)return;
    Serial.print(F("KNX085 MOTOR gate="));Serial.print(KNX085_HARDWARE_GATE_APPROVED);
    Serial.print(F(" state="));Serial.print(Knx085::phaseName(motor.state()));
    Serial.print(F(" channel="));Serial.print(motor.channel());
    Serial.print(F(" direction="));Serial.print(motor.direction());
    Serial.print(F(" duration_ms="));Serial.print(motor.pulseDuration());
    Serial.print(F(" peak_ma="));Serial.println(maxSeenMa);
}
""")

# ForceAllInactive is retained and used on every STOP, fault and idle iteration.
one("bool motorsLow() {", """void serviceMotor() {
    const bool wasActive=motor.active();
    sampleIna();
    motor.tick(millis(),static_cast<bool>(Serial),ina);
    gpio_put(kKnxTx,0); // NO physical KNX transmission in any KNX085 mode.
    if(!motor.active())forceAllInactive();
    else {
        // Only the selected H-bridge may be enabled, ever.
        for(unsigned i=0;i<8;++i)
            if(static_cast<int>(i+1)!=motor.channel())gpio_put(kMotorEnables[i],0);
    }
    if(wasActive && !motor.active() && Serial){
        Serial.print(F("KNX085 MOTOR_ENDED state="));
        Serial.println(Knx085::phaseName(motor.state()));
        printIna();
    }
}
void startOutputs() {
    // The state machine already checked exclusive M1/M2, 50..250ms,
    // INA power window and the compile-time hardware gate.
    forceAllInactive();
#if KNX085_HARDWARE_GATE_APPROVED == 1
    gpio_put(kMotorDirection[0],motor.direction()=='F'?1:0);
    gpio_put(kMotorDirection[1],motor.direction()=='R'?1:0);
    delayMicroseconds(500);  // shared direction settles before enable
    gpio_put(kMotorEnables[motor.channel()-1],1);
#endif
}
bool motorsLow() {""")

one('Serial.print(F(" rx_edges="));Serial.print(rxTotal);\n    Serial.println(F(" NO_KNX_TX_NO_MOTOR_ACTUATION"));',
    '''Serial.print(F(" rx_edges="));Serial.print(rxTotal);
    Serial.print(F(" motor_gate="));Serial.print(KNX085_HARDWARE_GATE_APPROVED);
    Serial.print(F(" motor_state="));Serial.print(Knx085::phaseName(motor.state()));
    Serial.println(F(" NO_AUTOMATIC_MOTOR_OR_KNX_TX"));''')

one('void readOnlyCommand(const char *cmd) {\n', """void usbCommand(const char *cmd) {
    if(strcmp(cmd,"STOP")==0) {
        forceAllInactive();
        motor.stop();
        if(Serial)Serial.println(F("KNX085 STOPPED_ALL_OFF"));
        return;
    }
    if(strcmp(cmd,"INA")==0) {
        sampleIna(true);
        printIna();
        return;
    }
    if(strcmp(cmd,"MSTATUS")==0) {
        printMotor();
        return;
    }
    if(strcmp(cmd,"CLEARFAULT")==0) {
        forceAllInactive();
        sampleIna(true);
        const bool ok=motor.clearFault(ina);
        if(Serial)Serial.println(ok?F("KNX085 FAULT_CLEARED"):F("KNX085 REFUSED_CLEARFAULT"));
        return;
    }
    if(strcmp(cmd,"ARM MOTORS")==0) {
        forceAllInactive();
        sampleIna(true);
        const bool ok=motor.arm(millis(),KNX085_HARDWARE_GATE_APPROVED==1,ina);
        if(Serial)Serial.println(ok?F("KNX085 ARMED_5S"):F("KNX085 REFUSED_ARM_HARDWARE_OR_POWER_GATE"));
        return;
    }
    if(strncmp(cmd,"PULSE ",6)==0) {
        unsigned ch=0,ms=0;
        char dir=0;
        int consumed=0;
        if(sscanf(cmd,"PULSE M%u %c %u%n",&ch,&dir,&ms,&consumed)!=3 ||
           consumed<=0 || cmd[consumed]!=0) {
            if(Serial)Serial.println(F("KNX085 REFUSED_PULSE_SYNTAX"));
            return;
        }
        sampleIna(true);
        const bool ok=motor.start(millis(),static_cast<int>(ch),dir,ms,
                                  KNX085_HARDWARE_GATE_APPROVED==1,ina);
        if(!ok) {
            forceAllInactive();
            if(Serial)Serial.println(F("KNX085 REFUSED_PULSE_INTERLOCK"));
            return;
        }
        maxSeenMa=0;
        startOutputs();
        if(Serial) {
            Serial.print(F("KNX085 PULSE_STARTED M"));Serial.print(ch);
            Serial.print(' ');Serial.print(dir);
            Serial.print(F(" duration_ms="));Serial.println(ms);
        }
        return;
    }
""")

one('KNX085 COMMANDS STATUS TEMPS RXSTATS RXDUMP HELP',
    'KNX085 COMMANDS STATUS TEMPS RXSTATS RXDUMP INA MSTATUS STOP CLEARFAULT ARM MOTORS PULSE M1|M2 F|R 50..250 HELP')
one('readOnlyCommand(inputLine);','usbCommand(inputLine);')
one('void setup() {\n', 'void setup() {\n')  # Validate single setup anchor.
one('attachInterrupt(digitalPinToInterrupt(kKnxRx),isrKnxRx,CHANGE);\n',
    '''attachInterrupt(digitalPinToInterrupt(kKnxRx),isrKnxRx,CHANGE);
    Wire.setSDA(kInaSda);
    Wire.setSCL(kInaScl);
    Wire.begin();
    Wire.setClock(100000);
    Wire.setTimeout(15);
    inaInitialized=true;
    sampleIna(true);
''')
one('''void loop() {
    pollTemperature();
    pollUsb();
    drainRxToUsb();
    // Reassert both safety states periodically; command handlers can never enable them.
    static uint32_t lastOffMs=0;
    const uint32_t now=millis();
    if(static_cast<uint32_t>(now-lastOffMs)>100){
        forceAllInactive();
        lastOffMs=now;
    }
    if(static_cast<uint32_t>(now-lastStatusMs)>=kStatusIntervalMs){
        lastStatusMs=now;
        if(Serial){
            Serial.println(F("KNX085 PASSIVE_KNX_RX_AND_ATtiny_TEMPERATURES"));
            printStatus();
            printRxStats();
        }
    }
}
''','''void loop() {
    // Never run slow RXDUMP / temperature printing while an output is active.
    // KNX RX capture continues via ISR; ATtiny data resumes after <=250ms.
    serviceMotor();
    pollUsb();  // STOP is parsed also while a short pulse is active.
    serviceMotor();
    if(motor.active())return;
    pollTemperature();
    drainRxToUsb();
    const uint32_t now=millis();
    if(static_cast<uint32_t>(now-lastStatusMs)>=kStatusIntervalMs){
        lastStatusMs=now;
        if(Serial){
            Serial.println(F("KNX085 PASSIVE_RX_T0_T3_AND_GATED_MOTOR_DIAG"));
            printStatus();
            printRxStats();
        }
    }
}
''')
target.write_text(source,encoding="utf8",newline="\n")
monitor=Path(__file__).parent/"knx085_live_monitor.py"
text=monitor.read_text(encoding="utf8").replace("KNX084","KNX085")
monitor.write_text(text,encoding="utf8",newline="\n")
print(f"KNX085 GENERATED source_bytes={len(source.encode())}; monitor_bytes={len(text.encode())}")
