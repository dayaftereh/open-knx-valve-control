// KNX099 – portable position controller proof, native-only; NO H-bridge.
#include "../../lib/common/knx099_m1_position_model.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Knx099;

static Sample good(int32_t ma=25) { return Sample{true,false,true,3290,ma}; }
static Sample idle() { return good(0); }
static bool is(Action a,ActionType t,StopReason r=StopReason::None) {
    return a.type==t && a.reason==r;
}

static void referenceAtF(Model& m,uint32_t=0) {
    assert(m.acceptStoppedCurrentEndpoint(Direction::F,true,true,idle()));
    assert(m.snapshot().phase==Phase::Idle);
    assert(m.snapshot().evidence==Evidence::CurrentEndstopCandidate);
    assert(m.snapshot().estimatedPositionTowardR==0);
}

static void testBootAndMapping() {
    Model m;
    assert(m.phase()==Phase::Unreferenced);
    assert(!m.snapshot().referenceAvailable);
    assert(is(m.requestTarget(500,0,idle(),true,true),ActionType::Rejected));
    assert(!m.acceptStoppedCurrentEndpoint(Direction::None,true,true,idle()));
    assert(!m.acceptStoppedCurrentEndpoint(Direction::F,false,true,idle()));
    assert(!m.acceptStoppedCurrentEndpoint(Direction::F,true,false,idle()));
    assert(!m.acceptStoppedCurrentEndpoint(Direction::F,true,true,good(35)));
    referenceAtF(m);
    assert(is(m.requestTarget(1000,0,idle(),true,true),ActionType::Rejected));
    assert(is(m.requestTarget(0,0,idle(),true,true),ActionType::Rejected));
    assert(is(m.requestTarget(1001,0,idle(),true,true),ActionType::Rejected));
    assert(is(m.requestTarget(20,0,idle(),true,true),ActionType::Rejected));
    assert(is(m.requestTarget(980,0,idle(),true,true),ActionType::Rejected));
    m.reset();
    assert(m.phase()==Phase::Unreferenced);
    assert(!m.snapshot().referenceAvailable);
}

static void testHomingAndElectricalOffAck() {
    Model m;
    assert(is(m.requestReference(Direction::R,1000,idle(),true,false),
              ActionType::Rejected));
    assert(is(m.requestReference(Direction::R,1000,good(26),true,true),
              ActionType::Rejected));
    assert(is(m.requestReference(Direction::R,1000,idle(),false,true),
              ActionType::Rejected));
    assert(is(m.requestReference(Direction::R,1000,idle(),true,true),
              ActionType::StartR));
    assert(m.phase()==Phase::StartPending);
    assert(is(m.acknowledgeStarted(1008,Direction::R),ActionType::None));
    uint32_t t=1016;
    for(;t<1500;t+=8)assert(is(m.tick(t,good(30)),ActionType::None));
    // Sporadic early peaks >45mA should not stop the motor.
    for(int j=0;j<18;j++,t+=8)
    {
        Action a=m.tick(t,good(j%5==2?49:30));
        assert(is(a,ActionType::None));
    }
    // Reset the isolated high sample before a deliberately sustained rise.
    assert(is(m.tick(t,good(30)),ActionType::None));
    t+=8;
    for(int j=0;j<5;j++,t+=8)
        assert(is(m.tick(t,good(46)),ActionType::None));
    Action stop=m.tick(t,good(46));
    assert(is(stop,ActionType::Stop,StopReason::EndstopCandidate));
    assert(m.phase()==Phase::StopPending);
    assert(!m.acknowledgeAllOff(false));
    assert(m.phase()==Phase::StopPending);
    assert(m.acknowledgeAllOff(true));
    assert(m.phase()==Phase::Idle);
    assert(m.snapshot().evidence==Evidence::CurrentEndstopCandidate);
    assert(m.positionTowardR()==1000);
    assert(m.snapshot().completedReferences==1);
    assert(!m.acknowledgeAllOff(true));
}

static void testDirectionalSegments() {
    Model m;referenceAtF(m);
    assert(is(m.requestTarget(500,10,idle(),true,true),ActionType::StartR));
    assert(m.plannedMs()==12194); // full R 24.388s / 2
    assert(is(m.acknowledgeStarted(18,Direction::R),ActionType::None));
    // Start high current is allowed through first 450ms if under120mA.
    for(uint32_t t=26;t<18u+m.plannedMs();t+=8) {
        int current=t<468?95:25;
        Action a=m.tick(t,good(current));
        assert(is(a,ActionType::None));
    }
    uint32_t due=18u+m.plannedMs();
    assert(is(m.tick(due,good(24)),ActionType::Stop,StopReason::TimedTarget));
    assert(!m.acknowledgeAllOff(false));
    assert(m.acknowledgeAllOff(true));
    assert(m.snapshot().estimatedPositionTowardR==500);
    assert(m.snapshot().evidence==Evidence::TimedEstimate);
    assert(m.snapshot().timedSegmentsSinceReference==1);
    assert(is(m.requestTarget(502,due+50,idle(),true,true),ActionType::None));
    assert(m.positionTowardR()==500); // deadband MUST NOT change reported position
    assert(is(m.requestTarget(250,due+50,idle(),true,true),ActionType::StartF));
    assert(m.plannedMs()==5688); // 250/1000 * 22.751s rounded
    assert(is(m.acknowledgeStarted(due+55,Direction::F),ActionType::None));
    uint32_t next=due+55+m.plannedMs();
    for(uint32_t k=due+63;k<next;k+=8)
        assert(is(m.tick(k,good(20)),ActionType::None));
    assert(is(m.tick(next,good(20)),ActionType::Stop,StopReason::TimedTarget));
    assert(m.acknowledgeAllOff(true));
    assert(m.positionTowardR()==250);
    assert(m.snapshot().completedTimedSegments==2);
    assert(m.snapshot().timedSegmentsSinceReference==2);
}

static void testCumulativeLimitAndReset() {
    Model m;referenceAtF(m);
    const uint16_t targets[]={100,200,300,400};
    uint32_t now=100;
    for(uint16_t target:targets)
    {
        Action a=m.requestTarget(target,now,idle(),true,true);
        assert(is(a,ActionType::StartR));
        assert(is(m.acknowledgeStarted(now+8,Direction::R),ActionType::None));
        const uint32_t start=now+8;
        now+=8+m.plannedMs();
        for(uint32_t k=start+8;k<now;k+=8)
            assert(is(m.tick(k,good(27)),ActionType::None));
        assert(is(m.tick(now,good(27)),ActionType::Stop,StopReason::TimedTarget));
        assert(m.acknowledgeAllOff(true));
        now+=100;
    }
    assert(m.snapshot().timedSegmentsSinceReference==4);
    assert(is(m.requestTarget(500,now,idle(),true,true),ActionType::Rejected));
    assert(m.acceptStoppedCurrentEndpoint(Direction::F,true,true,idle()));
    assert(m.snapshot().timedSegmentsSinceReference==0);
    assert(m.positionTowardR()==0);
}

static void testUnexpectedStallNeverBecomesPosition() {
    Model m;referenceAtF(m);
    assert(is(m.requestTarget(500,0,idle(),true,true),ActionType::StartR));
    assert(is(m.acknowledgeStarted(8,Direction::R),ActionType::None));
    uint32_t t=16;
    for(;t<464;t+=8)assert(is(m.tick(t,good(25)),ActionType::None));
    for(int i=0;i<5;i++,t+=8)assert(is(m.tick(t,good(46)),ActionType::None));
    assert(is(m.tick(t,good(46)),ActionType::Stop,StopReason::UnexpectedLoad));
    assert(m.acknowledgeAllOff(true));
    assert(m.phase()==Phase::FaultLatched);
    assert(m.evidence()==Evidence::None);
    assert(!m.snapshot().referenceAvailable);
    assert(is(m.requestTarget(250,t+10,idle(),true,true),ActionType::Rejected));
}

static void testInterruptionAndAckTimeouts() {
    Model a;referenceAtF(a);
    assert(is(a.requestTarget(200,0,idle(),true,true),ActionType::StartR));
    assert(is(a.tick(501,idle()),ActionType::Stop,StopReason::StartAckTimeout));
    assert(a.acknowledgeAllOff(true));
    assert(a.phase()==Phase::FaultLatched);

    Model b;referenceAtF(b);
    assert(is(b.requestTarget(200,20,idle(),true,true),ActionType::StartR));
    assert(is(b.acknowledgeStarted(28,Direction::R),ActionType::None));
    assert(is(b.cancel(100),ActionType::Stop,StopReason::Cancelled));
    assert(is(b.tick(1101,idle()),ActionType::Stop,StopReason::StopAckTimeout));
    assert(b.phase()==Phase::FaultLatched);
    assert(!b.snapshot().referenceAvailable);
}

static void testBadSensorPowerLinkAndOvercurrent() {
    for(int kind=0;kind<6;kind++) {
        Model m;referenceAtF(m);
        assert(is(m.requestTarget(600,100,idle(),true,true),ActionType::StartR));
        assert(is(m.acknowledgeStarted(108,Direction::R),ActionType::None));
        Sample s=good(29);
        StopReason expect=StopReason::InvalidINA;
        switch(kind) {
            case 0:s.valid=false;break;
            case 1:s.overflow=true;break;
            case 2:s.linkUp=false;expect=StopReason::LinkLost;break;
            case 3:s.busMv=3099;expect=StopReason::BadSupply;break;
            case 4:s.busMv=3451;expect=StopReason::BadSupply;break;
            case 5:s.currentMa=121;expect=StopReason::OverCurrent;break;
        }
        assert(is(m.tick(116,s),ActionType::Stop,expect));
        assert(m.acknowledgeAllOff(true));
        assert(m.phase()==Phase::FaultLatched);
        assert(!m.snapshot().referenceAvailable);
    }
}

static void testSensorGapAndCurrentCut() {
    Model a;referenceAtF(a);
    assert(is(a.requestTarget(550,1,idle(),true,true),ActionType::StartR));
    assert(is(a.acknowledgeStarted(9,Direction::R),ActionType::None));
    assert(is(a.tick(17,good(24)),ActionType::None));
    assert(is(a.tick(42,good(24)),ActionType::Stop,StopReason::InvalidINA));

    Model b;
    assert(is(b.requestReference(Direction::R,0,idle(),true,true),ActionType::StartR));
    assert(is(b.acknowledgeStarted(8,Direction::R),ActionType::None));
    uint32_t t=16;
    for(;t<464;t+=8)assert(is(b.tick(t,good(20)),ActionType::None));
    for(int j=0;j<5;j++,t+=8)assert(is(b.tick(t,good(0)),ActionType::None));
    assert(is(b.tick(t,good(0)),ActionType::Stop,StopReason::CurrentCut));
    assert(b.acknowledgeAllOff(true));
    assert(b.phase()==Phase::FaultLatched);
}

static void testHomingTimeoutAndWrap() {
    Model a;
    assert(is(a.requestReference(Direction::F,0,idle(),true,true),ActionType::StartF));
    assert(is(a.acknowledgeStarted(8,Direction::F),ActionType::None));
    for(uint32_t t=16;t<30008;t+=8)
        assert(is(a.tick(t,good(20)),ActionType::None));
    assert(is(a.tick(30008,good(20)),ActionType::Stop,StopReason::MaxDuration));
    assert(a.acknowledgeAllOff(true));
    assert(a.phase()==Phase::FaultLatched);

    Model b;referenceAtF(b);
    const uint32_t begin=0xfffffff0u;
    assert(is(b.requestTarget(100,begin,idle(),true,true),ActionType::StartR));
    assert(is(b.acknowledgeStarted(0xfffffff8u,Direction::R),ActionType::None));
    assert(b.plannedMs()==2439);
    const uint32_t end=static_cast<uint32_t>(0xfffffff8u+b.plannedMs());
    for(uint32_t t=0u;t<end;t+=8u)
        assert(is(b.tick(t,good(30)),ActionType::None));
    assert(is(b.tick(end,good(30)),ActionType::Stop,StopReason::TimedTarget));
    assert(b.acknowledgeAllOff(true));
    assert(b.positionTowardR()==100);
}

static void testWrongDirectionAckAndMissingFirstSample() {
    Model wrong;referenceAtF(wrong);
    assert(is(wrong.requestTarget(500,100,idle(),true,true),ActionType::StartR));
    assert(is(wrong.acknowledgeStarted(108,Direction::F),
              ActionType::Stop,StopReason::StartAckMismatch));
    assert(wrong.phase()==Phase::StopPending);
    assert(wrong.acknowledgeAllOff(true));
    assert(wrong.phase()==Phase::FaultLatched);
    assert(!wrong.snapshot().referenceAvailable);

    Model missing;referenceAtF(missing);
    assert(is(missing.requestTarget(500,100,idle(),true,true),ActionType::StartR));
    assert(is(missing.acknowledgeStarted(108,Direction::R),ActionType::None));
    assert(is(missing.tick(133,good(25)),ActionType::Stop,StopReason::InvalidINA));
    assert(missing.acknowledgeAllOff(true));
    assert(missing.phase()==Phase::FaultLatched);
}

static void testNoPhysicalMappingOrGPIO() {
    Model m;
    Calibration bad{};bad.riseCurrentMa=140;
    Model n(bad);
    assert(is(n.requestReference(Direction::R,0,idle(),true,true),ActionType::Rejected));
    assert(m.snapshot().phase==Phase::Unreferenced);
    // The core is *defined only* in F endpoint 0/R endpoint 1000 space.
    // No valve-percent, KNX DPT or actual motor pin is exposed.
}

int main() {
    testBootAndMapping();
    testHomingAndElectricalOffAck();
    testDirectionalSegments();
    testCumulativeLimitAndReset();
    testUnexpectedStallNeverBecomesPosition();
    testInterruptionAndAckTimeouts();
    testBadSensorPowerLinkAndOvercurrent();
    testSensorGapAndCurrentCut();
    testHomingTimeoutAndWrap();
    testWrongDirectionAckAndMissingFirstSample();
    testNoPhysicalMappingOrGPIO();
    std::cout<<"KNX099 NATIVE POSITION CORE: 11 scenario groups PASS\n";
}
