#!/usr/bin/env python3
"""Generate isolated KNX100 USB-only 5-step hardware/position firmware.

Maintains tested KNX097 exact MotorGate, GPIO, INA219, USB and raw TRACE code.
Replaces hardcoded six full-stroke loop with KNX099 position state machine:
R reference -> internal 50% -> 25% -> 75% -> F reference.
Every step separately requires USB ARM and explicit command; MCU allows
a maximum of five commands and refuses everything else.
"""
from pathlib import Path
import shutil
source=Path(__file__).resolve().parents[1]/"knx097_repeatability"
dest=Path(__file__).resolve().parent
(dest/"src").mkdir(exist_ok=True,parents=True)
shutil.copyfile(source/"src"/"motor_gate.hpp",dest/"src"/"motor_gate.hpp")
s=(source/"src"/"main.cpp").read_text("utf8")
def one(x,old,new):
    assert x.count(old)==1,(old[:80],x.count(old))
    return x.replace(old,new,1)
s=one(s,'#include "motor_gate.hpp"',
      '#include "motor_gate.hpp"\n#include "../../../lib/common/knx099_m1_position_model.hpp"')
s="// KNX100: USB-only M1 position firmware, exactly 5 user-ARM'ed guarded steps.\n"+s
start=s.index('uint8_t endstopHighCount=0;')
end=s.index('TraceRow currentTrace[kTraceSize]',start)
s=s[:start]+'''Knx099::Model position;
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

'''+s[end:]
# Hardware sampling stays intact, but KNX099 owns all threshold decisions.
start=s.index('        // First reference-search candidate, NEVER assert homing success')
end=s.index('\n    }\n}\nvoid printIna()',start)
s=s[:start]+'''        // KNX100: KNX099 state machine receives this measured INA
        // sample in serviceMotor(). No independent duplicated stall counter.
'''+s[end:]
start=s.index('void serviceMotor() {')
end=s.index('void startOutputs() {',start)
s=s[:start]+'''// KNX099 stop reason is logged when a 8-ms INA sample causes MCU STOP.
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
'''+s[end:]
# Need motorsLow forward declaration (original function defined after serviceMotor)
s=one(s,'void printPosition() {','bool motorsLow();\nvoid printPosition() {')
# Rewrite full USB command function before passive USB reader, preserve STOP etc and
# deliberately reject old PULSE/CLEARFAULT: no unplanned M2/motor movements.
start=s.index('void usbCommand(const char *cmd) {')
end=s.index('void pollUsb() {',start)
s=s[:start]+'''void usbCommand(const char *cmd) {
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
'''+s[end:]
# Original KNX097 strings outside runtime remain in outdated comments only.
ini=(source/"platformio.ini").read_text("utf8")
ini=ini.replace("knx097_m1_repeat_30000","knx100_m1_position_5step").replace("KNX097 ONLY M1 3x R/F alternating max30000ms per leg","KNX100 M1 USB-only scripted 5-step position bench")
(dest/"src"/"main.cpp").write_text(s,encoding="utf8",newline="\n")
(dest/"platformio.ini").write_text(ini.rstrip()+"\n",encoding="utf8",newline="\n")
assert "KNX100 STARTED step=" in s and "KNX100 POSACKOFF_COMPLETE" in s
assert "if(strncmp(cmd,\"PULSE \"" not in s
assert "endstopHighCount" not in s
assert "kStepsMaximum=5" in s
assert "Knx099::Model position;" in s
print("GENERATED KNX100 five-step M1 USB and INA controlled positioning, no KNX TX, no autorun")
