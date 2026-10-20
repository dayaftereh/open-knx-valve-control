#ifndef OPENKNX_KNX104_M1_ETS_CONTRACT_HPP
#define OPENKNX_KNX104_M1_ETS_CONTRACT_HPP

// KNX104: PORTABLE, ETS-V3 PROPOSAL ONLY. No GroupObject/KNX, Serial,
// Arduino, motor GPIO, INA219, or host callbacks. None of these signals
// cause motion. The installed product XML is still AppVersion2 (KO1..35).
//
// Canonical domain: DPT 5.001 raw 0..255, internal 0..1000 permille.
// LEGACY DPT 5.004 KO17..24 MUST NEVER BE REINTERPRETED AS 5.001.
// Actual F/R->valve open/closed is UNVERIFIED on the present M1 bench;
// defaults never release an open-degree setpoint or position feedback.

#include "heating_zone_model.hpp"
#include "knx099_m1_position_model.hpp"
#include <stdint.h>

namespace Knx104 {

enum class Mapping : uint8_t {
    Unconfirmed = 0,
    F_End_Closed = 1, // R=1000 is physically OPEN (requires commissioning)
    R_End_Closed = 2  // F=0 is physically OPEN (requires commissioning)
};
enum class Mode : uint8_t { Disabled = 0, RoomTemperature = 1, DirectPercent = 2 };
enum class Dpt : uint8_t {
    Unknown, Scaling5001, LegacyPercent5004, Switch1001, Boolean1002, Alarm1005
};
enum class FrameKind : uint8_t { GroupValueWrite, GroupValueRead, GroupValueResponse };

enum class ReceiveResult : uint8_t {
    Accepted, IgnoredUnconfigured, IgnoredNotWrite, IgnoredWrongObject,
    IgnoredWrongMode, InvalidGaBinding, InvalidDpt, InvalidPayload,
    DisarmedConfiguration
};

struct ProposalObjects {
    uint16_t directDemandRx=0;      // Z1 38, Z8 66; DPT 5.001
    uint16_t estimatedPositionTx=0; // M1 68..M8 75; DPT 5.001
    uint16_t faultTx=0;             // M1 76..M8 83; DPT 1.005
    uint16_t referencedTx=0;        // M1 84..M8 91; DPT 1.002
    uint16_t movingTx=0;            // M1 92..M8 99; DPT 1.001
    uint16_t deviceBusyTx=100;     // DPT 1.002
};
inline ProposalObjects proposed(uint8_t motorNumber,uint8_t zoneNumber) {
    if(motorNumber<1 || motorNumber>8 || zoneNumber<1 || zoneNumber>8)
        return {};
    const uint8_t motorIdx=static_cast<uint8_t>(motorNumber-1);
    const uint8_t zoneIdx=static_cast<uint8_t>(zoneNumber-1);
    ProposalObjects result{};
    result.directDemandRx=static_cast<uint16_t>(38u+4u*zoneIdx);
    result.estimatedPositionTx=static_cast<uint16_t>(68u+motorIdx);
    result.faultTx=static_cast<uint16_t>(76u+motorIdx);
    result.referencedTx=static_cast<uint16_t>(84u+motorIdx);
    result.movingTx=static_cast<uint16_t>(92u+motorIdx);
    return result;
}

struct Settings {
    uint8_t motorNumber=1;
    uint8_t zoneNumber=1;
    Mode mode=Mode::Disabled;
    Mapping mapping=Mapping::Unconfirmed;
    bool physicallyVerified=false;
    bool etsV3Commissioned=false;
    // Existing KNX008 proposal default direct demand TTL=300 s.
    uint16_t directTimeoutSeconds=300;
};

inline bool validSettings(const Settings& s) {
    return s.motorNumber>=1 && s.motorNumber<=8 &&
        s.zoneNumber>=1 && s.zoneNumber<=8 &&
        (s.mode==Mode::Disabled || s.mode==Mode::RoomTemperature ||
         s.mode==Mode::DirectPercent) &&
        (s.mapping==Mapping::Unconfirmed || s.mapping==Mapping::F_End_Closed ||
         s.mapping==Mapping::R_End_Closed) &&
        s.directTimeoutSeconds>=10 && s.directTimeoutSeconds<=3600 &&
        (!s.physicallyVerified || s.mapping!=Mapping::Unconfirmed);
}
inline bool valveSemanticsUnlocked(const Settings& s) {
    return validSettings(s) && s.etsV3Commissioned && s.physicallyVerified &&
           s.mapping!=Mapping::Unconfirmed;
}

struct WriteFrame {
    uint16_t objectNumber=0;
    Dpt declaredDpt=Dpt::Unknown;
    FrameKind kind=FrameKind::GroupValueWrite;
    // Trusted by caller only after GA association was confirmed in ETS;
    // KNX APDU itself has NO DPT type field.
    bool gaBindingValidated=false;
    const uint8_t* payload=nullptr;
    uint8_t payloadLength=0;
};

struct TargetProposal {
    bool valid=false;
    uint16_t internalTowardRPermille=0;
    uint16_t requestedOpenPermille=0;
    uint8_t dptScalingByte=0;
    // Informational only; NEVER call Knx099::Model.requestTarget automatically.
    bool physicallyCommissioned=false;
};

struct TelemetryProposal {
    ProposalObjects objects={};
    bool mappingReady=false;
    bool fault=false;
    bool referenced=false;
    bool moving=false;
    bool deviceBusy=false;
    bool positionAvailable=false;
    uint8_t estimatedValveOpenRaw=0;
    uint16_t estimatedInternalTowardRPermille=0;
    Knx099::Evidence evidence=Knx099::Evidence::None;
    // No "measured position" field: model has no independent encoder.
};

class Contract {
public:
    Contract() { reset(); }

    void reset() {
        settings_={};
        configured_=false;
        haveDemand_=false;
        lastDemand_=0;
        lastRxMs_=0;
    }

    // Reconfiguration discards ALL received commands, even if only mapping
    // or ETS mode changed. Caller must revalidate GA bindings separately.
    bool configure(const Settings& settings) {
        haveDemand_=false;
        lastDemand_=0;
        lastRxMs_=0;
        configured_=validSettings(settings);
        settings_=configured_?settings:Settings{};
        return configured_;
    }
    const Settings& settings() const { return settings_; }
    bool configured() const { return configured_; }

    ReceiveResult receive(const WriteFrame& frame,uint32_t nowMs) {
        if(!configured_)return ReceiveResult::IgnoredUnconfigured;
        if(frame.kind!=FrameKind::GroupValueWrite)
            return ReceiveResult::IgnoredNotWrite;
        if(frame.objectNumber!=proposed(settings_.motorNumber,settings_.zoneNumber).directDemandRx)
            return ReceiveResult::IgnoredWrongObject;
        if(!valveSemanticsUnlocked(settings_)) {
            haveDemand_=false;
            return ReceiveResult::DisarmedConfiguration;
        }
        if(settings_.mode!=Mode::DirectPercent)
            return ReceiveResult::IgnoredWrongMode;
        if(!frame.gaBindingValidated) {
            haveDemand_=false;
            return ReceiveResult::InvalidGaBinding;
        }
        if(frame.declaredDpt!=Dpt::Scaling5001) {
            haveDemand_=false;
            return ReceiveResult::InvalidDpt;
        }
        if(!frame.payload || frame.payloadLength!=1) {
            haveDemand_=false;
            return ReceiveResult::InvalidPayload;
        }
        lastDemand_=frame.payload[0];
        lastRxMs_=nowMs;
        haveDemand_=true;
        return ReceiveResult::Accepted;
    }

    // Pure display/dispatcher PROPOSAL, never a physical movement order.
    // The motor adapter must independently enforce hardware off + valid
    // INA sample + user permit + reference + all timeout/current guards.
    TargetProposal target(uint32_t nowMs,const Knx099::Snapshot& motor,
                          bool allOutputsOffVerified,bool linkAlive) const {
        TargetProposal t{};
        if(!configured_ || !haveDemand_ || !linkAlive ||
           !allOutputsOffVerified || !valveSemanticsUnlocked(settings_) ||
           settings_.mode!=Mode::DirectPercent ||
           static_cast<uint32_t>(nowMs-lastRxMs_)>=
               static_cast<uint32_t>(settings_.directTimeoutSeconds)*1000u ||
           motor.phase!=Knx099::Phase::Idle ||
           !motor.referenceAvailable || motor.evidence==Knx099::Evidence::None)
            return t;

        const uint16_t opening=HeatingZone::rawScalingToPermille(lastDemand_);
        t.valid=true;
        t.dptScalingByte=lastDemand_;
        t.requestedOpenPermille=opening;
        t.internalTowardRPermille=settings_.mapping==Mapping::F_End_Closed
                                   ? opening : static_cast<uint16_t>(1000u-opening);
        t.physicallyCommissioned=true;
        return t;
    }

    TelemetryProposal telemetry(const Knx099::Snapshot& motor,
                                bool allOutputsOffVerified) const {
        TelemetryProposal r{};
        if(!configured_)return r;
        r.objects=proposed(settings_.motorNumber,settings_.zoneNumber);
        r.mappingReady=valveSemanticsUnlocked(settings_);
        r.fault=motor.phase==Knx099::Phase::FaultLatched;
        r.moving=motor.phase==Knx099::Phase::StartPending ||
                 motor.phase==Knx099::Phase::Running ||
                 motor.phase==Knx099::Phase::StopPending;
        r.deviceBusy=r.moving; // only one physical motor may move at once
        r.referenced=motor.referenceAvailable &&
                     motor.evidence!=Knx099::Evidence::None &&
                     !r.fault;
        r.evidence=motor.evidence;

        // No false 5.001 "valve opening" feedback while motor moves,
        // after a fault, without proof of OFF or without physical mapping.
        if(!r.mappingReady || !r.referenced ||
           motor.phase!=Knx099::Phase::Idle || !allOutputsOffVerified ||
           motor.estimatedPositionTowardR>1000)
            return r;
        const uint16_t opening=settings_.mapping==Mapping::F_End_Closed
              ? motor.estimatedPositionTowardR
              : static_cast<uint16_t>(1000u-motor.estimatedPositionTowardR);
        r.estimatedInternalTowardRPermille=motor.estimatedPositionTowardR;
        r.estimatedValveOpenRaw=HeatingZone::permilleToRawScaling(opening);
        r.positionAvailable=true; // still ONLY estimated, never encoder-measured
        return r;
    }

private:
    Settings settings_{};
    bool configured_=false;
    bool haveDemand_=false;
    uint8_t lastDemand_=0;
    uint32_t lastRxMs_=0;
};

} // namespace Knx104

#endif // OPENKNX_KNX104_M1_ETS_CONTRACT_HPP
