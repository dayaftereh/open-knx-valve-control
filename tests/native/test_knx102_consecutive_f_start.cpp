// KNX102: exact KNX100 R reference -> F500 -> F250 model ACK replay.
// Pure C++ simulation: no GPIO, USB, flash or motion.
#include "../../lib/common/knx099_m1_position_model.hpp"
#include <cassert>
#include <iostream>
using namespace Knx099;
static Sample idle() { return Sample{true,false,true,3288,0}; }
static Sample running() { return Sample{true,false,true,3280,18}; }
static void finishTimed(Model& m,uint32_t start,Direction d,uint16_t target,unsigned planned)
{
    const Action begin=m.requestTarget(target,start,idle(),true,true);
    assert(begin.type==(d==Direction::F?ActionType::StartF:ActionType::StartR));
    assert(m.phase()==Phase::StartPending);
    assert(m.plannedMs()==planned);
    // This is exactly the ACK at motor.started() used in KNX100.
    const Action ack=m.acknowledgeStarted(start,d);
    assert(ack.type==ActionType::None);
    assert(m.phase()==Phase::Running);
    for(uint32_t t=start+8;t<start+planned;t+=8)
        assert(m.tick(t,running()).type==ActionType::None);
    const Action stop=m.tick(start+planned,running());
    assert(stop.type==ActionType::Stop);
    assert(stop.reason==StopReason::TimedTarget);
    assert(m.phase()==Phase::StopPending);
    assert(!m.acknowledgeAllOff(false));
    assert(m.acknowledgeAllOff(true));
    assert(m.phase()==Phase::Idle);
    assert(m.positionTowardR()==target);
    assert(m.evidence()==Evidence::TimedEstimate);
}
int main()
{
    Model m;
    assert(m.acceptStoppedCurrentEndpoint(Direction::R,true,true,idle()));
    assert(m.positionTowardR()==1000);
    finishTimed(m,1000,Direction::F,500,11376);
    finishTimed(m,20000,Direction::F,250,5688);
    assert(m.snapshot().completedTimedSegments==2);
    assert(m.snapshot().timedSegmentsSinceReference==2);
    std::cout<<"KNX102 position ACK exact R-end -> F500 -> F250: PASS\n";
    return 0;
}
