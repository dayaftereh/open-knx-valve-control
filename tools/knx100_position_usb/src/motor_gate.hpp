#pragma once
// KNX085 - hardware-independent fail-closed MOTOR permission/state model.
// Do NOT infer hardware safety from a successful software test. TB6612 STBY is hardwired HIGH.
#include <stdint.h>

namespace Knx085 {
constexpr uint32_t kArmWindowMs=5000;
constexpr uint32_t kMinPulseMs=50;
constexpr uint32_t kMaxPulseMs=30000;
constexpr int kMinMotorBusMv=3100;
constexpr int kMaxMotorBusMv=3450;
constexpr int kIdleCurrentLimitMa=25;
constexpr int kRunningCurrentLimitMa=120;

struct InaSample {
    bool readOk=false;
    bool overflow=false;
    int busMv=0;
    int currentMa=0;
};

inline bool powerOkay(const InaSample& sample,bool atRest) {
    if(!sample.readOk || sample.overflow ||
       sample.busMv<kMinMotorBusMv || sample.busMv>kMaxMotorBusMv)
        return false;
    return sample.currentMa>=-5 &&
           sample.currentMa<=(atRest?kIdleCurrentLimitMa:kRunningCurrentLimitMa);
}

enum class Phase:uint8_t {Idle,Armed,Active,Fault};
inline const char* phaseName(Phase p) {
    switch(p) {
      case Phase::Idle:return "IDLE";
      case Phase::Armed:return "ARMED";
      case Phase::Active:return "ACTIVE";
      case Phase::Fault:return "FAULT";
    }
    return "UNKNOWN";
}

class MotorGate {
public:
    Phase state()const{return state_;}
    bool active()const{return state_==Phase::Active;}
    int channel()const{return channel_;}
    char direction()const{return direction_;}
    uint32_t started()const{return started_;}
    uint32_t pulseDuration()const{return duration_;}
    void stop(){state_=Phase::Idle;channel_=0;direction_='-';duration_=0;}
    // KNX093 short-test stall guard: fail CLOSED without allowing another pulse.
    void trip(){state_=Phase::Fault;}
    // Explicit clearing is allowed only in motor-OFF state with verified idle power.
    bool clearFault(const InaSample& s) {
        if(state_!=Phase::Fault || !powerOkay(s,true))return false;
        stop();return true;
    }
    bool arm(uint32_t now,bool hardwareReleased,const InaSample& s) {
        if(state_!=Phase::Idle || !hardwareReleased || !powerOkay(s,true))
            return false;
        state_=Phase::Armed;
        armed_=now;
        return true;
    }
    bool start(uint32_t now,int channel,char direction,uint32_t pulseMs,
               bool hardwareReleased,const InaSample& s) {
        if(state_!=Phase::Armed || !hardwareReleased ||
           static_cast<uint32_t>(now-armed_)>kArmWindowMs ||
           (channel!=1 && channel!=2) ||
           (direction!='F' && direction!='R') ||
           pulseMs<kMinPulseMs || pulseMs>kMaxPulseMs || !powerOkay(s,true))
            return false;
        channel_=channel;
        direction_=direction;
        started_=now;
        duration_=pulseMs;
        state_=Phase::Active;
        return true;
    }
    // Call before other application work and after USB parsing. Real HW samples must
    // be refreshed periodically while active; the physical gate is not a hardware STO.
    void tick(uint32_t now,bool usbConnected,const InaSample& s) {
        if(state_==Phase::Armed &&
           (!usbConnected || static_cast<uint32_t>(now-armed_)>kArmWindowMs))
            stop();
        if(state_!=Phase::Active)return;
        if(!usbConnected || !powerOkay(s,false)) {
            state_=Phase::Fault;
            return;
        }
        if(static_cast<uint32_t>(now-started_)>=duration_)stop();
    }
private:
    Phase state_=Phase::Idle;
    int channel_=0;
    char direction_='-';
    uint32_t armed_=0;
    uint32_t started_=0;
    uint32_t duration_=0;
};
} // namespace Knx085
