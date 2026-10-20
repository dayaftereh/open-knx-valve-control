// KNX100: USB-only M1 position firmware, exactly 5 user-ARM'ed guarded steps.
// KNX097: 3x R/F alternating, MCU controlled 30s limit, INA cutoff, no auto-drive.
// KNX096 USB-only M1 F full-stroke 30s cap; abort on first sustained endstop current signature.
// KNX096: first 15s M1 R homing-search trial, stop on current rise or current collapse; no automatic retry.
// KNX094 M1 R max 10s USB-only monitored hard-end observation.
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
#include "../../../lib/common/knx099_m1_position_model.hpp"

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
constexpr unsigned kTraceSize=4800; // >=30s / 8ms = 3750 samples
constexpr uint32_t kEndstopGuardStartMs=450;
constexpr int kEndstopHighCurrentMa=45;
constexpr int kEndstopLowCurrentMa=5;
constexpr uint8_t kEndstopConsecutive=6;
Knx099::Model position;
uint8_t stepsCompleted=0;
uint8_t stepsIssued=0;
constexpr uint8_t kStepsMaximum=5;
const char* endstopKind="NONE";
uint32_t endstopAtMs=0;
int endstopAtMa=0;
char lastCommandDirection='-';
uint16_t lastCommandTarget=0;
bool commandAccepted=false;
uint32_t lastLiveReportMs=0;

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
        // KNX100: KNX099 state machine receives this measured INA
        // sample in serviceMotor(). No independent duplicated stall counter.

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
// KNX099 stop reason is logged when a 8-ms INA sample causes MCU STOP.
const char* stopName(Knx099::StopReason r) {
    using Knx099::StopReason;
    switch(r) {
        case StopReason::None:return "NONE";
        case StopReason::EndstopCandidate:return "ENDSTOP_CANDIDATE";
        case StopReason::TimedTarget:return "TIMED_TARGET";
        case StopReason::InvalidINA:return "INVALID_INA";
        case StopReason::LinkLost:return "LINK_LOST";
        case StopReason::BadSupply:return "BAD_SUPPLY";
        case StopReason::OverCurrent:return "OVERCURRENT";
        case StopReason::CurrentCut:return "CURRENT_CUT";
        case StopReason::UnexpectedLoad:return "UNEXPECTED_LOAD";
        case StopReason::MaxDuration:return "MAX_DURATION";
        case StopReason::StartAckTimeout:return "START_ACK_TIMEOUT";
        case StopReason::StartAckMismatch:return "START_ACK_MISMATCH";
        case StopReason::StopAckTimeout:return "STOP_ACK_TIMEOUT";
        case StopReason::Cancelled:return "CANCELLED";
    }
    return "UNKNOWN";
}
const char* positionPhaseName(Knx099::Phase p) {
    using Knx099::Phase;
    switch(p) {
        case Phase::Unreferenced:return "UNREFERENCED";
        case Phase::Idle:return "IDLE";
        case Phase::StartPending:return "START_PENDING";
        case Phase::Running:return "RUNNING";
        case Phase::StopPending:return "STOP_PENDING";
        case Phase::FaultLatched:return "FAULT_LATCHED";
    }
    return "UNKNOWN";
}
const char* positionEvidenceName(Knx099::Evidence e) {
    switch(e) {
      case Knx099::Evidence::None:return "NONE";
      case Knx099::Evidence::CurrentEndstopCandidate:return "CURRENT_ENDSTOP_CANDIDATE";
      case Knx099::Evidence::TimedEstimate:return "TIMED_ESTIMATE";
    }
    return "UNKNOWN";
}
bool motorsLow();
void printPosition() {
    if(!Serial)return;
    const auto s=position.snapshot();
    Serial.print(F("KNX100 POSITION phase="));Serial.print(positionPhaseName(s.phase));
    Serial.print(F(" evidence="));Serial.print(positionEvidenceName(s.evidence));
    Serial.print(F(" position_r_permille="));Serial.print(s.estimatedPositionTowardR);
    Serial.print(F(" desired_r_permille="));Serial.print(s.requestedPositionTowardR);
    Serial.print(F(" planned_ms="));Serial.print(s.plannedTravelMs);
    Serial.print(F(" step_issued="));Serial.print(stepsIssued);
    Serial.print(F(" step_completed="));Serial.print(stepsCompleted);
    Serial.print(F(" last_stop="));Serial.print(stopName(s.lastStop));
    Serial.print(F(" driver="));Serial.print(Knx085::phaseName(motor.state()));
    Serial.print(F(" motors_low="));Serial.println(motorsLow()?1:0);
}
void serviceMotor() {
    const bool wasActive=motor.active();
    const uint32_t before=lastInaMs;
    sampleIna();
    if(motor.active() && before!=lastInaMs) {
        const Knx099::Sample a{ina.readOk,ina.overflow,static_cast<bool>(Serial),
                               ina.busMv,ina.currentMa};
        const Knx099::Action action=position.tick(lastInaMs,a);
        if(action.type==Knx099::ActionType::Stop) {
            endstopKind=stopName(action.reason);
            endstopAtMs=static_cast<uint32_t>(lastInaMs-motor.started());
            endstopAtMa=ina.currentMa;
            motor.trip();
            forceAllInactive();
            if(Serial) {
                Serial.print(F("KNX100 STOP_CANDIDATE reason="));Serial.print(endstopKind);
                Serial.print(F(" t_ms="));Serial.print(endstopAtMs);
                Serial.print(F(" current_ma="));Serial.print(endstopAtMa);
                Serial.print(F(" bus_mv="));Serial.println(ina.busMv);
            }
        }
    }
    if(motor.active() && Serial) {
        const uint32_t t=static_cast<uint32_t>(millis()-motor.started());
        if(t>=lastLiveReportMs+200u) {
            lastLiveReportMs=t;
            Serial.print(F("KNX100 LIVE t_ms="));Serial.print(t);
            Serial.print(F(" current_ma="));Serial.print(ina.currentMa);
            Serial.print(F(" shunt_raw="));Serial.print(static_cast<int16_t>(lastRawShunt));
            Serial.print(F(" bus_mv="));Serial.println(ina.busMv);
        }
    }
    motor.tick(millis(),static_cast<bool>(Serial),ina);
    if(wasActive && !motor.active() &&
       position.phase()==Knx099::Phase::Running) {
        // Hardware gate stopped independently of position policy.
        // Invalidate position and require manual fault recovery.
        position.cancel(millis());
        endstopKind="DRIVER_STOPPED_FIRST";
    }
    gpio_put(kKnxTx,0);
    if(!motor.active())forceAllInactive();
    else {
        for(unsigned i=0;i<8;++i)
            if(static_cast<int>(i+1)!=motor.channel())gpio_put(kMotorEnables[i],0);
    }
    if(wasActive && !motor.active() && Serial) {
        Serial.print(F("KNX100 MOTOR_ENDED state="));
        Serial.print(Knx085::phaseName(motor.state()));
        Serial.print(F(" reason="));Serial.println(endstopKind);
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
    if(strcmp(cmd,"KNX100")==0) {
        if(Serial)Serial.println(F("KNX100 POSITION_USB_ONLY steps=5 order=R,500,250,750,F full_r_ms=24388 full_f_ms=22751 limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 motor_gate=1"));
        printPosition();
        return;
    }
    if(strcmp(cmd,"POSSTATUS")==0) { printPosition();return; }
    if(strcmp(cmd,"STOP")==0) {
        forceAllInactive();
        if(position.phase()==Knx099::Phase::Running ||
           position.phase()==Knx099::Phase::StartPending)
            position.cancel(millis());
        motor.stop();
        if(Serial)Serial.println(F("KNX100 STOPPED_ALL_OFF"));
        return;
    }
    if(strcmp(cmd,"INA")==0) { sampleIna(true);printIna();return; }
    if(strcmp(cmd,"MSTATUS")==0) { printMotor();return; }
    if(strcmp(cmd,"TRACE")==0) { printTrace();return; }
    if(strcmp(cmd,"POSACKOFF")==0) {
        if(position.phase()!=Knx099::Phase::StopPending || motor.active()) {
            if(Serial)Serial.println(F("KNX100 POSACKOFF_REFUSED_NOT_STOPPED"));
            return;
        }
        // Separate USB-command acknowledgement of the physically low
        // digital GPIO levels with fresh INA idle measurement.
        // GPIO LOW is *not* independent hardware STO or encoder evidence.
        forceAllInactive();
        sampleIna(true);
        const bool allOff=motorsLow() && gpio_get(kKnxTx)==0 &&
                          !motor.active() && Knx085::powerOkay(ina,true);
        const bool wasPending=position.phase()==Knx099::Phase::StopPending;
        const bool acknowledged=wasPending &&
                                position.acknowledgeAllOff(allOff);
        const bool cleared=acknowledged &&
            (motor.state()==Knx085::Phase::Fault
               ? motor.clearFault(ina) : motor.state()==Knx085::Phase::Idle);
        if(acknowledged && cleared &&
           position.phase()==Knx099::Phase::Idle &&
           stepsCompleted<kStepsMaximum &&
           stepsIssued==stepsCompleted+1) {
            ++stepsCompleted;
            if(Serial)Serial.println(F("KNX100 POSACKOFF_COMPLETE"));
        } else {
            if(Serial)Serial.println(F("KNX100 POSACKOFF_REFUSED_OR_FAULT"));
        }
        printPosition();
        return;
    }
    if(strcmp(cmd,"ARM MOTORS")==0) {
        const bool stateOK=position.phase()==Knx099::Phase::Unreferenced ||
                           position.phase()==Knx099::Phase::Idle;
        if(!stateOK || motor.state()!=Knx085::Phase::Idle) {
            if(Serial)Serial.println(F("KNX100 REFUSED_ARM"));
            return;
        }
        forceAllInactive();sampleIna(true);
        const bool ok=stateOK && !motor.active() &&
                      motor.state()==Knx085::Phase::Idle &&
                      stepsIssued==stepsCompleted &&
                      stepsCompleted<kStepsMaximum &&
                      idleGoodSamples>=5 &&
                      motor.arm(millis(),
                         KNX085_HARDWARE_GATE_APPROVED==1,ina);
        if(Serial)Serial.println(ok?F("KNX100 ARMED_5S"):
                                    F("KNX100 REFUSED_ARM"));
        return;
    }
    bool seek=false,timed=false;
    char direction='-';
    unsigned target=0;
    if(strcmp(cmd,"SEEK R")==0) {seek=true;direction='R';}
    else if(strcmp(cmd,"SEEK F")==0) {seek=true;direction='F';}
    else {
        int consumed=0;
        if(sscanf(cmd,"SET %u%n",&target,&consumed)==1 &&
           consumed>0 && cmd[consumed]==0)
            timed=true;
    }
    if(seek || timed) {
        const bool sequenceOK=
            (stepsCompleted==0 && seek && direction=='R') ||
            (stepsCompleted==1 && timed && target==500) ||
            (stepsCompleted==2 && timed && target==250) ||
            (stepsCompleted==3 && timed && target==750) ||
            (stepsCompleted==4 && seek && direction=='F');
        if(!sequenceOK || stepsIssued!=stepsCompleted ||
           motor.state()!=Knx085::Phase::Armed ||
           !motorsLow() || stepsCompleted>=kStepsMaximum) {
            if(Serial)Serial.println(F("KNX100 REFUSED_SEQUENCE_OR_ARM"));
            return;
        }
        sampleIna(true);
        const uint32_t now=millis();
        const Knx099::Sample reading{ina.readOk,ina.overflow,
                          static_cast<bool>(Serial),ina.busMv,ina.currentMa};
        Knx099::Action action=
            seek ? position.requestReference(direction=='R'
                              ? Knx099::Direction::R
                              : Knx099::Direction::F,
                              now,reading,true,true)
                 : position.requestTarget(static_cast<uint16_t>(target),
                              now,reading,true,true);
        if(action.type!=Knx099::ActionType::StartR &&
           action.type!=Knx099::ActionType::StartF) {
            motor.stop();
            if(Serial)Serial.println(F("KNX100 REFUSED_POSITION_INTERLOCK"));
            return;
        }
        const char d=action.type==Knx099::ActionType::StartR?'R':'F';
        // The hardware MotorGate has an independent length bound.
        const uint32_t requestedMs=position.plannedMs();
        const uint32_t driverMs=seek?30000u:requestedMs+32u;
        const bool started=motor.start(now,1,d,driverMs,
                                      KNX085_HARDWARE_GATE_APPROVED==1,ina);
        if(!started) {
            forceAllInactive();
            position.cancel(now);
            motor.trip();
            if(Serial)Serial.println(F("KNX100 FAILED_DRIVER_START"));
            return;
        }
        maxSeenMa=0;
        traceCount=0;
        lastLiveReportMs=0;
        lastCommandDirection=d;
        lastCommandTarget=timed?static_cast<uint16_t>(target):(d=='R'?1000:0);
        endstopKind="NONE";
        endstopAtMs=0;
        endstopAtMa=0;
        startOutputs();
        const bool gpioActive=gpio_get(kMotorEnables[0])==1;
        const Knx099::Action ack=position.acknowledgeStarted(
                                  motor.started(),d=='R'
                                  ? Knx099::Direction::R
                                  : Knx099::Direction::F);
        if(ack.type!=Knx099::ActionType::None || !gpioActive) {
            forceAllInactive();
            motor.trip();
            position.cancel(millis());
            if(Serial)Serial.println(F("KNX100 FAILED_OUTPUT_OR_START_ACK"));
            return;
        }
        ++stepsIssued;
        if(Serial) {
            Serial.print(F("KNX100 STARTED step="));Serial.print(stepsIssued);
            Serial.print(F(" dir="));Serial.print(d);
            Serial.print(F(" target_r_permille="));Serial.print(lastCommandTarget);
            Serial.print(F(" planned_ms="));Serial.println(requestedMs);
        }
        return;
    }
    if(strcmp(cmd,"STATUS")==0) {printStatus();return;}
    if(strcmp(cmd,"HELP")==0) {
        if(Serial)Serial.println(F("KNX100 COMMANDS KNX100 POSSTATUS STATUS INA MSTATUS TRACE ARM MOTORS SEEK R SET 500 SET 250 SET 750 SEEK F POSACKOFF STOP"));
        return;
    }
    if(Serial)Serial.println(F("KNX100 REFUSED_UNKNOWN_NO_PULSE_CLEARFAULT"));
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
