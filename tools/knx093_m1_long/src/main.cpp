// KNX093: one M1 reverse pulse 800ms, current-limited and stall-guarded; USB-only office bench.
// KNX085 - passive KNX TP RX + ATtiny3216 temperature UART diagnostic.
// KNX bus is LIVE on cellar line 1.3. DO NOT drive GPIO0 HIGH.
// M1..M8 idle LOW; only gated KNX085 bench pulses can activate M1/M2.
// No KNX TP TX; motor outputs require physical release, INA gate and USB ARM.
// NOTE: firmware cannot guarantee GPIO0 and motor levels during BOOTSEL/reset.
// The board's U11/D1/F1/CN1 and multi-source supply gates remain unresolved.
#include <Arduino.h>
#include <Wire.h>
#include "motor_gate.hpp"

#include "hardware/gpio.h"
#include "../../../lib/common/temperature_protocol.hpp"
#include <stdio.h>
#include <string.h>
#ifndef ARDUINO_ARCH_RP2040
#error "KNX085 requires an RP2040 board"
#endif
#ifndef KNX085_MOTOR_DIAG
#error "KNX085 must be built only as isolated gated diagnostic"
#endif
#ifndef KNX085_HARDWARE_GATE_APPROVED
#error "KNX085 requires an explicit hardware-output gate value"
#endif
#if KNX085_HARDWARE_GATE_APPROVED != 0 && KNX085_HARDWARE_GATE_APPROVED != 1
#error "Hardware gate must be exactly 0 or 1"
#endif

namespace {
constexpr uint8_t kKnxTx=0;       // STKNX U9 pin24, active HIGH, idle LOW
constexpr uint8_t kKnxRx=1;       // STKNX U9 pin23, input only
constexpr uint8_t kAttinyTx=8;    // RP GPIO8 UART1 TX -> ATtiny PA2 RX
constexpr uint8_t kAttinyRx=9;    // RP GPIO9 UART1 RX <- ATtiny PA1 TX
constexpr uint8_t kMotorEnables[8]={10,11,12,13,14,15,16,17};
constexpr uint8_t kMotorDirection[2]={18,19};
constexpr uint32_t kUartBaud=115200;
constexpr uint32_t kFirstPollMs=3500;
constexpr uint32_t kPollIntervalMs=2100;
constexpr uint32_t kReplyTimeoutMs=1300;
constexpr uint32_t kStatusIntervalMs=5000;
constexpr unsigned kRxRingCapacity=4096;
static_assert((kRxRingCapacity&(kRxRingCapacity-1))==0,"RX ring must be power-of-two");
struct RxEdge {uint32_t timeUs;uint8_t level;};
static_assert(sizeof(RxEdge)==8,"RX edge layout changed");
volatile RxEdge rxBuffer[kRxRingCapacity]={};
volatile unsigned rxWrite=0;
volatile unsigned rxRead=0;
volatile uint32_t rxLost=0;
volatile uint32_t rxTotal=0;
volatile uint32_t rxRises=0;
volatile uint32_t rxFalls=0;
volatile uint32_t rxLastUs=0;
bool rxDump=false;

TemperatureProtocol::Parser tempParser;
TemperatureProtocol::Snapshot latestSnapshot{};
bool hasSnapshot=false;
bool uartReady=false;
bool requestOutstanding=false;
uint32_t requestAtMs=0;
uint32_t lastPollMs=0;
uint32_t lastUartByteMs=0;
uint32_t lastStatusMs=0;
uint32_t tempAccepted=0;
uint32_t tempRejected=0;
uint32_t tempTimeout=0;
uint32_t tempRxBytes=0;
uint8_t nextSeq=0;
uint8_t pendingSeq=0;
char inputLine[32]={};
uint8_t inputLength=0;

// V1.2 U23 INA219: SDA=GPIO4 / SCL=GPIO5; 0x40 verified live
// INA I2C address 0x40 was confirmed by real USB telemetry.
// R29 assembly confirmed by user 2026-10-19: 0.200 ohm / 1W.
// M_VCC/INA219 confirmed normal after actual 10-ohm R33/R34 replacements (2026-10-20).
constexpr uint8_t kInaSda=4, kInaScl=5, kInaCandidate=0x40;
constexpr uint32_t kInaIdleIntervalMs=200, kInaRunIntervalMs=8;
Knx085::MotorGate motor;
Knx085::InaSample ina{};
uint32_t lastInaMs=0;
bool inaInitialized=false;
int maxSeenMa=0;
uint16_t lastRawShunt=0, inaConfig=0;
bool inaConfigOk=false;
uint8_t idleGoodSamples=0;
struct TraceRow {
    uint32_t elapsedMs;
    int16_t rawShunt;
    uint16_t busMv;
    uint8_t status;
};
constexpr unsigned kTraceSize=160; // 800ms / 8ms = ~100 readings
constexpr uint32_t kStallGuardStartMs=100;
constexpr int kStallCurrentMa=90;
constexpr uint8_t kStallConsecutive=4;
uint8_t stallHighCount=0;
bool stallGuardTripped=false;

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
    next.readOk=inaConfigOk &&
        readInaReg(0x01,shunt) && readInaReg(0x02,bus);
    if(next.readOk){
        // INA219 raw shunt LSB = 10 uV; user confirms R29=200 mOhm / 1 W.
        // 1 raw count = 0.05 mA; high OFF-state reading still unresolved.
        // 1 shunt_raw = 10 uV, 0.2 ohm means 0.05 mA each.
        // Integer mA used ONLY for software cutoff. TRACE retains raw resolution.
        lastRawShunt=shunt;
        next.currentMa=(static_cast<int32_t>(static_cast<int16_t>(shunt))*10)/200;
        next.busMv=static_cast<int>((bus>>3)*4);
        next.overflow=(bus&1u)!=0u;
    }
    ina=next;
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
        // A blocked gearbox can draw <120mA even without a hard overcurrent.
        // After the first 100ms (inrush grace), sustained >=90mA for >=4
        // successive valid ~8ms INA measurements latches a motor FAULT.
        // Latching fault is allowed while active; serviceMotor turns all
        // drive outputs LOW in the same loop.
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
    }
}
void printIna() {
    if(!Serial)return;
    Serial.print(F("KNX085 INA addr=0x40 config=0x"));Serial.print(inaConfig,HEX);
    Serial.print(F(" config_ok="));Serial.print(inaConfigOk?1:0);
    Serial.print(F(" good_idle_samples="));Serial.println(idleGoodSamples);
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

void outputLow(uint8_t pin) {
    // Explicitly preload LOW before enabling SIO output driver.
    gpio_init(pin);
    gpio_put(pin,0);
    gpio_set_dir(pin,GPIO_OUT);
    gpio_pull_down(pin);
}
void forceAllInactive() {
    // This code path NEVER writes a HIGH value to any KNX or motor output.
    gpio_put(kKnxTx,0);
    for(uint8_t pin:kMotorEnables)gpio_put(pin,0);
    for(uint8_t pin:kMotorDirection)gpio_put(pin,0);
}
void serviceMotor() {
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
bool motorsLow() {
    for(uint8_t pin:kMotorEnables)if(gpio_get(pin))return false;
    for(uint8_t pin:kMotorDirection)if(gpio_get(pin))return false;
    return true;
}
void isrKnxRx() {
    const uint8_t level=digitalRead(kKnxRx)?1:0;
    const uint32_t t=micros();
    ++rxTotal;
    if(level)++rxRises;else ++rxFalls;
    rxLastUs=t;
    const unsigned next=(rxWrite+1u)&(kRxRingCapacity-1u);
    if(next==rxRead) {
        ++rxLost;
        return;
    }
    rxBuffer[rxWrite].timeUs=t;
    rxBuffer[rxWrite].level=level;
    rxWrite=next;
}
void printRxStats() {
    uint32_t e,r,f,l,t;
    unsigned buffered;
    noInterrupts();
    e=rxTotal;r=rxRises;f=rxFalls;l=rxLost;t=rxLastUs;
    buffered=(rxWrite-rxRead)&(kRxRingCapacity-1u);
    interrupts();
    if(!Serial)return;
    Serial.print(F("KNX085 RXSTATS edges="));Serial.print(e);
    Serial.print(F(" rises="));Serial.print(r);
    Serial.print(F(" falls="));Serial.print(f);
    Serial.print(F(" lost="));Serial.print(l);
    Serial.print(F(" buffered="));Serial.print(buffered);
    Serial.print(F(" last_us="));Serial.print(t);
    Serial.print(F(" current_level="));Serial.println(digitalRead(kKnxRx)?1:0);
}
void printStatus() {
    if(!Serial)return;
    Serial.print(F("KNX085 STATUS tx_low="));
    Serial.print(gpio_get(kKnxTx)==0?1:0);
    Serial.print(F(" motors_low="));Serial.print(motorsLow()?1:0);
    Serial.print(F(" uart_ready="));Serial.print(uartReady?1:0);
    Serial.print(F(" snapshots="));Serial.print(tempAccepted);
    Serial.print(F(" timeout="));Serial.print(tempTimeout);
    Serial.print(F(" rejected="));Serial.print(tempRejected);
    Serial.print(F(" rx_edges="));Serial.print(rxTotal);
    Serial.print(F(" motor_gate="));Serial.print(KNX085_HARDWARE_GATE_APPROVED);
    Serial.print(F(" motor_state="));Serial.print(Knx085::phaseName(motor.state()));
    Serial.println(F(" NO_AUTOMATIC_MOTOR_OR_KNX_TX"));
}
const char *faultName(uint8_t fault) {
    switch(fault) {
      case 0:return "None";
      case 1:return "NoSensor";
      case 2:return "ParasitePower";
      case 3:return "ReadFailed";
      case 4:return "PowerOn85";
      case 5:return "OutsideRange";
      case 6:return "SampleStale";
      case 7:return "NoSample";
      case 8:return "Recovering";
      default:return "InvalidFault";
    }
}
bool channelFresh(const TemperatureProtocol::Channel& ch) {
    return (ch.flags&0x03)==0x03 &&
           (ch.flags&0x18)==0 &&
           ch.fault==0 && ch.ageSeconds!=0xFFFF && ch.ageSeconds<=30;
}
void printTemps() {
    if(!Serial)return;
    if(!hasSnapshot) {
        Serial.println(F("KNX085 TEMPS NO_SNAPSHOT_YET"));
        return;
    }
    unsigned valid=0,missing=0,faults=0;
    for(uint8_t n=0;n<TemperatureProtocol::Channels;++n){
        const auto &c=latestSnapshot.channels[n];
        if(channelFresh(c))++valid;
        if(c.fault==1 && !(c.flags&0x02))++missing;
        if(c.fault)++faults;
    }
    Serial.print(F("KNX085 SNAPSHOT seq="));Serial.print(pendingSeq);
    Serial.print(F(" attiny_up_ms="));Serial.print(latestSnapshot.uptimeMs);
    Serial.print(F(" valid_all9="));Serial.print(valid);
    Serial.print(F(" no_sensor_all9="));Serial.print(missing);
    Serial.print(F(" faults_all9="));Serial.print(faults);
    Serial.print(F(" accepted="));Serial.print(tempAccepted);
    Serial.print(F(" timeout="));Serial.print(tempTimeout);
    Serial.print(F(" rejected="));Serial.println(tempRejected);
    // Deliberately report T0-T3 only. Never interpret an invalid raw 0 as 0 deg C.
    for(uint8_t n=0;n<4;++n){
        const auto& c=latestSnapshot.channels[n];
        Serial.print(F("KNX085 CH T"));Serial.print(n);
        Serial.print(F(" valid="));Serial.print(channelFresh(c)?1:0);
        Serial.print(F(" temp_c="));
        if(channelFresh(c))Serial.print(c.centiC/100.0f,2);
        else Serial.print(F("NA"));
        Serial.print(F(" flags="));Serial.print(c.flags);
        Serial.print(F(" fault="));Serial.print(c.fault);
        Serial.print(F(" fault_name="));Serial.print(faultName(c.fault));
        Serial.print(F(" age_s="));Serial.println(c.ageSeconds);
    }
}
void usbCommand(const char *cmd) {
    if(strcmp(cmd,"KNX093")==0) {
        if(Serial){
            Serial.print(F("KNX093 M1_R_ONLY duration_ms=800 motor_gate="));
            Serial.print(KNX085_HARDWARE_GATE_APPROVED);
            Serial.print(F(" limit_ma=120 stall_ma=90 after_ms=100 consecutive=4 latched="));
            Serial.println(stallGuardTripped?1:0);
        }
        return;
    }
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
    if(strcmp(cmd,"TRACE")==0){
        printTrace();
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
        const bool ok=motor.arm(millis(),KNX085_HARDWARE_GATE_APPROVED==1
                                    && inaConfigOk && idleGoodSamples>=5,ina);
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
        // Exact M1 R 800 only. No F, no M2, no second duration.
        if(ch!=1 || dir!='R' || ms!=800) {
            forceAllInactive();
            if(Serial)Serial.println(F("KNX093 REFUSED_ONLY_M1_R_800"));
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
        traceCount=0;
        stallHighCount=0;
        stallGuardTripped=false;
        startOutputs();
        if(Serial) {
            Serial.print(F("KNX085 PULSE_STARTED M"));Serial.print(ch);
            Serial.print(' ');Serial.print(dir);
            Serial.print(F(" duration_ms="));Serial.println(ms);
        }
        return;
    }
    if(strcmp(cmd,"STATUS")==0) printStatus();
    else if(strcmp(cmd,"TEMPS")==0) printTemps();
    else if(strcmp(cmd,"RXSTATS")==0) printRxStats();
    else if(strcmp(cmd,"RXDUMP")==0) {
        rxDump=true; // USB dump of already-captured input edges only
        if(Serial)Serial.println(F("KNX085 RXDUMP_START PASSIVE_ONLY"));
    }
    else if(strcmp(cmd,"HELP")==0){
        if(Serial)Serial.println(F("KNX085 COMMANDS STATUS TEMPS RXSTATS RXDUMP INA MSTATUS TRACE STOP CLEARFAULT ARM MOTORS PULSE M1|M2 F|R 50..250 HELP"));
    }
    else if(Serial)Serial.println(F("KNX085 REFUSED_UNRECOGNIZED_OR_ACTUATING_COMMAND"));
}
void pollUsb() {
    for(unsigned n=0;n<32 && Serial.available()>0;++n){
        int c=Serial.read();
        if(c<0)break;
        if(c=='\r')continue;
        if(c=='\n'){
            inputLine[inputLength]=0;
            usbCommand(inputLine);
            inputLength=0;
        } else if(c>=32 && c<=126 && inputLength<sizeof(inputLine)-1){
            inputLine[inputLength++]=static_cast<char>(c);
        } else {
            inputLength=0;
            if(Serial)Serial.println(F("KNX085 REFUSED_BAD_COMMAND_INPUT"));
        }
    }
}
void drainRxToUsb() {
    if(!rxDump || !Serial)return;
    for(unsigned n=0;n<48;++n){
        RxEdge e{};bool have=false;
        noInterrupts();
        if(rxRead!=rxWrite){
            e.timeUs=rxBuffer[rxRead].timeUs;
            e.level=rxBuffer[rxRead].level;
            rxRead=(rxRead+1u)&(kRxRingCapacity-1u);
            have=true;
        }
        interrupts();
        if(!have) {
            rxDump=false;
            Serial.println(F("KNX085 RXDUMP_END"));
            return;
        }
        Serial.print(F("KNX085 RXEDGE t_us="));Serial.print(e.timeUs);
        Serial.print(F(" level="));Serial.println(e.level);
    }
}
void pollTemperature() {
    if(!uartReady)return;
    const uint32_t now=millis();
    if(tempParser.inProgress() &&
       static_cast<uint32_t>(now-lastUartByteMs)>TemperatureProtocol::MaxInterByteGapMs)
        tempParser.reset();

    for(uint8_t n=0;n<64 && Serial2.available()>0;++n){
        const int next=Serial2.read();
        if(next<0)break;
        ++tempRxBytes;
        lastUartByteMs=millis();
        TemperatureProtocol::Frame frame{};
        if(!tempParser.feed(static_cast<uint8_t>(next),frame))continue;
        if(!requestOutstanding ||
           frame.type!=TemperatureProtocol::SnapshotResponse ||
           frame.sequence!=pendingSeq) {
            ++tempRejected;
            continue;
        }
        TemperatureProtocol::Snapshot snapshot{};
        if(!TemperatureProtocol::decodeSnapshot(frame,snapshot)){
            ++tempRejected;
            continue;
        }
        latestSnapshot=snapshot;
        requestOutstanding=false;
        hasSnapshot=true;
        ++tempAccepted;
        printTemps();
    }

    if(requestOutstanding &&
       static_cast<uint32_t>(now-requestAtMs)>kReplyTimeoutMs){
        requestOutstanding=false;
        ++tempTimeout;
        if(Serial) {
            Serial.print(F("KNX085 TEMP_TIMEOUT seq="));
            Serial.print(pendingSeq);
            Serial.print(F(" total="));Serial.println(tempTimeout);
        }
    }
    if(now<kFirstPollMs || requestOutstanding ||
       (lastPollMs && static_cast<uint32_t>(now-lastPollMs)<kPollIntervalMs))
        return;

    uint8_t request[TemperatureProtocol::FrameOverhead]={};
    const uint8_t sequence=++nextSeq;
    const size_t length=TemperatureProtocol::encodeRequest(sequence,request,sizeof(request));
    // Arduino-Pico 5.5.0 SerialUART::availableForWrite() is Boolean (0/1), not bytes.
    if(length!=8 || Serial2.availableForWrite()<=0)return;
    if(Serial2.write(request,length)!=length)return;
    lastPollMs=millis();
    requestAtMs=lastPollMs;
    pendingSeq=sequence;
    requestOutstanding=true;
}
} // namespace

void setup() {
    // First actions under firmware control: never expose a HIGH on KNX TX or motors.
    outputLow(kKnxTx);
    for(uint8_t pin:kMotorEnables)outputLow(pin);
    for(uint8_t pin:kMotorDirection)outputLow(pin);
    forceAllInactive();
    pinMode(kKnxRx,INPUT); // U9 actively drives KNX RX, do NOT pull HIGH.
    Serial.begin(115200); // USB only; no KNX transmit facility.
    const bool txConfigured=Serial2.setTX(kAttinyTx);
    const bool rxConfigured=Serial2.setRX(kAttinyRx);
    uartReady=txConfigured && rxConfigured;
    if(uartReady)Serial2.begin(kUartBaud);
    lastUartByteMs=millis();
    attachInterrupt(digitalPinToInterrupt(kKnxRx),isrKnxRx,CHANGE);
    Wire.setSDA(kInaSda);
    Wire.setSCL(kInaScl);
    Wire.begin();
    Wire.setClock(100000);
    Wire.setTimeout(15);
    inaInitialized=true;
    inaConfigOk=readInaReg(0x00,inaConfig)
        && inaConfig!=0 && inaConfig!=0xffff
        && (inaConfig&0x07)!=0;
    sampleIna(true);
    lastStatusMs=millis()-kStatusIntervalMs;
}

void loop() {
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
