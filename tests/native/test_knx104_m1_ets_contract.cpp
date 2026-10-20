// KNX104: pure host-side ETS DPT5.001 <-> KNX099 internal M1 position
// contract. No KNX bus, GroupObject, GPIO or actual motor is called.
#include "../../lib/common/knx104_m1_ets_contract.hpp"
#include <cassert>
#include <iostream>
using namespace Knx104;

static Settings ready(Mapping m=Mapping::F_End_Closed) {
    Settings s{};
    s.motorNumber=1;s.zoneNumber=1;
    s.mode=Mode::DirectPercent;
    s.mapping=m;
    s.physicallyVerified=true;
    s.etsV3Commissioned=true;
    s.directTimeoutSeconds=300;
    return s;
}
static Knx099::Snapshot anchorR() {
    Knx099::Snapshot s{};
    s.phase=Knx099::Phase::Idle;
    s.evidence=Knx099::Evidence::CurrentEndstopCandidate;
    s.referenceAvailable=true;
    s.estimatedPositionTowardR=1000;
    return s;
}
static WriteFrame demand(uint8_t* value) {
    WriteFrame f{};
    f.objectNumber=38;
    f.kind=FrameKind::GroupValueWrite;
    f.declaredDpt=Dpt::Scaling5001;
    f.gaBindingValidated=true;
    f.payload=value;
    f.payloadLength=1;
    return f;
}
static void testSafeDefaults() {
    Contract c;
    uint8_t v=128;
    assert(c.receive(demand(&v),0)==ReceiveResult::IgnoredUnconfigured);
    assert(!c.target(0,anchorR(),true,true).valid);
    assert(!c.telemetry(anchorR(),true).positionAvailable);
    Settings s{};
    assert(c.configure(s));
    assert(c.receive(demand(&v),0)==ReceiveResult::DisarmedConfiguration);
    assert(!c.target(0,anchorR(),true,true).valid);
    assert(!c.telemetry(anchorR(),true).positionAvailable);
}
static void testObjectNumbersAndLegacyExclusion() {
    const ProposalObjects first=proposed(1,1);
    assert(first.directDemandRx==38 && first.estimatedPositionTx==68 &&
           first.faultTx==76 && first.referencedTx==84 &&
           first.movingTx==92 && first.deviceBusyTx==100);
    const ProposalObjects last=proposed(8,8);
    assert(last.directDemandRx==66 && last.estimatedPositionTx==75 &&
           last.faultTx==83 && last.referencedTx==91 &&
           last.movingTx==99 && last.deviceBusyTx==100);
    assert(proposed(0,1).directDemandRx==0);
    assert(proposed(1,9).estimatedPositionTx==0);
    for(unsigned z=1;z<=8;z++)
        for(unsigned m=1;m<=8;m++) {
            ProposalObjects objects=proposed(static_cast<uint8_t>(m),
                                            static_cast<uint8_t>(z));
            assert(objects.directDemandRx>=38 && objects.directDemandRx<=66);
            assert(objects.estimatedPositionTx>=68 && objects.estimatedPositionTx<=75);
            assert(objects.faultTx>=76 && objects.faultTx<=83);
            assert(objects.referencedTx>=84 && objects.referencedTx<=91);
            assert(objects.movingTx>=92 && objects.movingTx<=99);
        }
    // No new object aliases any existing AppVersion2 KO 1..35,
    // or the legacy DPT 5.004 KO17..24.
}
static void testConfigurationValidation() {
    Contract c;
    Settings s=ready();
    s.mapping=Mapping::Unconfirmed;
    assert(!c.configure(s)); // impossible to commission unknown mapping
    assert(!c.configured());
    s=ready();s.directTimeoutSeconds=0;assert(!c.configure(s));
    s=ready();s.motorNumber=9;assert(!c.configure(s));
    s=ready();s.zoneNumber=0;assert(!c.configure(s));
    s=ready();s.directTimeoutSeconds=3601;assert(!c.configure(s));
    s=ready();assert(c.configure(s));
    assert(c.configured());
}
static void testDptScalingReceiveAndValues() {
    Contract c;assert(c.configure(ready()));
    Knx099::Snapshot s=anchorR();
    uint8_t input=0;
    assert(c.receive(demand(&input),10)==ReceiveResult::Accepted);
    TargetProposal t=c.target(10,s,true,true);
    assert(t.valid && t.requestedOpenPermille==0 &&
           t.internalTowardRPermille==0 && t.dptScalingByte==0);
    input=128;
    assert(c.receive(demand(&input),20)==ReceiveResult::Accepted);
    t=c.target(20,s,true,true);
    assert(t.valid && t.requestedOpenPermille==502 &&
           t.internalTowardRPermille==502 && t.dptScalingByte==128);
    input=255;
    assert(c.receive(demand(&input),30)==ReceiveResult::Accepted);
    t=c.target(30,s,true,true);
    assert(t.valid && t.requestedOpenPermille==1000 &&
           t.internalTowardRPermille==1000);
}
static void testInverseMapping() {
    Contract c;assert(c.configure(ready(Mapping::R_End_Closed)));
    uint8_t raw=0;
    assert(c.receive(demand(&raw),5)==ReceiveResult::Accepted);
    TargetProposal t=c.target(5,anchorR(),true,true);
    assert(t.valid && t.internalTowardRPermille==1000);
    raw=255;
    assert(c.receive(demand(&raw),10)==ReceiveResult::Accepted);
    t=c.target(10,anchorR(),true,true);
    assert(t.valid && t.internalTowardRPermille==0);
    Knx099::Snapshot s=anchorR();
    auto out=c.telemetry(s,true);
    assert(out.positionAvailable && out.estimatedValveOpenRaw==0);
    s.estimatedPositionTowardR=0;
    out=c.telemetry(s,true);
    assert(out.positionAvailable && out.estimatedValveOpenRaw==255);
}
static void testWrongDptClearsPending() {
    Contract c;assert(c.configure(ready()));
    uint8_t raw=255;
    WriteFrame f=demand(&raw);
    assert(c.receive(f,100)==ReceiveResult::Accepted);
    f.declaredDpt=Dpt::LegacyPercent5004;
    assert(c.receive(f,110)==ReceiveResult::InvalidDpt);
    assert(!c.target(111,anchorR(),true,true).valid);
    f.declaredDpt=Dpt::Unknown;
    assert(c.receive(f,120)==ReceiveResult::InvalidDpt);
    assert(!c.target(121,anchorR(),true,true).valid);
}
static void testWrongGaAndPayloadClearPending() {
    Contract c;assert(c.configure(ready()));
    uint8_t raw=123;
    WriteFrame f=demand(&raw);
    assert(c.receive(f,1)==ReceiveResult::Accepted);
    f.gaBindingValidated=false;
    assert(c.receive(f,2)==ReceiveResult::InvalidGaBinding);
    assert(!c.target(3,anchorR(),true,true).valid);
    f.gaBindingValidated=true;f.payloadLength=2;
    assert(c.receive(f,4)==ReceiveResult::InvalidPayload);
    f.payloadLength=1;f.payload=nullptr;
    assert(c.receive(f,5)==ReceiveResult::InvalidPayload);
    assert(!c.target(6,anchorR(),true,true).valid);
}
static void testUnrelatedOrNonWriteIgnored() {
    Contract c;assert(c.configure(ready()));
    uint8_t raw=5;
    WriteFrame f=demand(&raw);
    f.objectNumber=17;
    assert(c.receive(f,4)==ReceiveResult::IgnoredWrongObject);
    f.objectNumber=38;f.kind=FrameKind::GroupValueRead;
    assert(c.receive(f,6)==ReceiveResult::IgnoredNotWrite);
    f.kind=FrameKind::GroupValueResponse;
    assert(c.receive(f,8)==ReceiveResult::IgnoredNotWrite);
    assert(!c.target(8,anchorR(),true,true).valid);
    // Reconfigure to ROOM mode: direct percent KO is never usable.
    Settings s=ready();s.mode=Mode::RoomTemperature;
    assert(c.configure(s));
    f.kind=FrameKind::GroupValueWrite;
    assert(c.receive(f,10)==ReceiveResult::IgnoredWrongMode);
}
static void testTimeoutAndWraparound() {
    Contract c;assert(c.configure(ready()));
    uint8_t raw=128;
    const uint32_t start=0xfffffff0u;
    assert(c.receive(demand(&raw),start)==ReceiveResult::Accepted);
    assert(c.target(start,anchorR(),true,true).valid);
    assert(c.target(start+299999u,anchorR(),true,true).valid);
    assert(!c.target(start+300000u,anchorR(),true,true).valid);
}
static void testNoMotorPositionOrHardwarePermit() {
    Contract c;assert(c.configure(ready()));
    uint8_t raw=128;
    assert(c.receive(demand(&raw),0)==ReceiveResult::Accepted);
    auto snap=anchorR();
    assert(!c.target(1,snap,false,true).valid);
    assert(!c.target(1,snap,true,false).valid);
    snap.phase=Knx099::Phase::Running;
    assert(!c.target(1,snap,true,true).valid);
    snap.phase=Knx099::Phase::Idle;snap.referenceAvailable=false;
    assert(!c.target(1,snap,true,true).valid);
    snap.referenceAvailable=true;snap.evidence=Knx099::Evidence::None;
    assert(!c.target(1,snap,true,true).valid);
}
static void testPositionTelemetryEvidenceAndStatus() {
    Contract c;assert(c.configure(ready()));
    auto s=anchorR();
    auto t=c.telemetry(s,true);
    assert(t.mappingReady && t.referenced && !t.fault && !t.moving &&
           !t.deviceBusy && t.positionAvailable &&
           t.estimatedValveOpenRaw==255 &&
           t.evidence==Knx099::Evidence::CurrentEndstopCandidate);
    s.estimatedPositionTowardR=500;
    s.evidence=Knx099::Evidence::TimedEstimate;
    t=c.telemetry(s,true);
    assert(t.positionAvailable && t.estimatedValveOpenRaw==128 &&
           t.evidence==Knx099::Evidence::TimedEstimate);
    assert(!c.telemetry(s,false).positionAvailable);
    s.phase=Knx099::Phase::Running;
    t=c.telemetry(s,true);
    assert(t.moving && t.deviceBusy && !t.positionAvailable);
    s.phase=Knx099::Phase::StartPending;
    assert(c.telemetry(s,true).moving);
    s.phase=Knx099::Phase::StopPending;
    assert(c.telemetry(s,true).moving);
    s.phase=Knx099::Phase::FaultLatched;
    t=c.telemetry(s,true);
    assert(t.fault && !t.referenced && !t.positionAvailable);
}
static void testUnmappedStatusStillNoFalsePosition() {
    Contract c;
    Settings s=ready();
    s.etsV3Commissioned=false;
    s.physicallyVerified=false;
    s.mapping=Mapping::Unconfirmed;
    assert(c.configure(s));
    auto status=c.telemetry(anchorR(),true);
    assert(!status.mappingReady && !status.positionAvailable);
    assert(status.referenced); // internal candidate can be diagnostic only
    assert(status.objects.estimatedPositionTx==68);
    uint8_t raw=128;
    assert(c.receive(demand(&raw),0)==ReceiveResult::DisarmedConfiguration);
    assert(!c.target(1,anchorR(),true,true).valid);
}
static void testReconfigureDisarmsPending() {
    Contract c;
    Settings s=ready();
    assert(c.configure(s));
    uint8_t raw=255;
    assert(c.receive(demand(&raw),10)==ReceiveResult::Accepted);
    assert(c.target(10,anchorR(),true,true).valid);
    s.mapping=Mapping::R_End_Closed;
    assert(c.configure(s));
    assert(!c.target(11,anchorR(),true,true).valid);
    assert(c.receive(demand(&raw),12)==ReceiveResult::Accepted);
    assert(c.target(13,anchorR(),true,true).internalTowardRPermille==0);
}
static void testRealKnx099ReferenceCandidate() {
    Knx099::Model position;
    Knx099::Sample idle{true,false,true,3292,0};
    assert(position.acceptStoppedCurrentEndpoint(Knx099::Direction::F,true,true,idle));
    Contract c;assert(c.configure(ready()));
    uint8_t raw=255;
    assert(c.receive(demand(&raw),500)==ReceiveResult::Accepted);
    const auto proposal=c.target(500,position.snapshot(),true,true);
    assert(proposal.valid && proposal.internalTowardRPermille==1000);
    assert(c.telemetry(position.snapshot(),true).estimatedValveOpenRaw==0);
    position.reset();
    assert(!c.telemetry(position.snapshot(),true).positionAvailable);
}
int main() {
    testSafeDefaults();
    testObjectNumbersAndLegacyExclusion();
    testConfigurationValidation();
    testDptScalingReceiveAndValues();
    testInverseMapping();
    testWrongDptClearsPending();
    testWrongGaAndPayloadClearPending();
    testUnrelatedOrNonWriteIgnored();
    testTimeoutAndWraparound();
    testNoMotorPositionOrHardwarePermit();
    testPositionTelemetryEvidenceAndStatus();
    testUnmappedStatusStillNoFalsePosition();
    testReconfigureDisarmsPending();
    testRealKnx099ReferenceCandidate();
    std::cout<<"KNX104 ETS/V3 POSITION SOFTWARE CONTRACT: 14 test groups PASS\n";
    return 0;
}
