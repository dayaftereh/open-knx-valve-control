// Pretend to compile for a real Arduino/Pico target. This pure header must
// NEVER include the native mock backend or expose an actuator-event path.
#ifndef ARDUINO
#define ARDUINO 10800
#endif
#include "../../lib/common/room_control_runtime.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static MotorQueueSim::Guards syntheticAllTrue()
{
    MotorQueueSim::Guards g{};
    g.explicitTestPermit = true;
    g.boardAsBuiltQualified = true;
    g.supplyQualified = true;
    g.outputInterlockQualified = true;
    g.currentMonitoringQualified = true;
    return g;
}

int main()
{
    RoomControlRuntime::Pipeline p;
    p.reset(0);
    auto s = p.snapshot();
    assert(!s.nativeSimulationAvailable);
    assert(!s.physicalOutputsConnected);
    assert(s.queue.state == MotorQueueSim::State::Disarmed);
    assert(!p.injectNativePosition(0, 200, 10000, 1));
    assert(!p.armNativeSimulation(0, syntheticAllTrue()));

    p.settings().modes[0] = HeatingZone::Mode::DirectPercent;
    p.settings().motorZone[0] = 1;
    p.tick(0); // initial topology fence
    p.inputs().zones[0].directDpt5001Raw = {255, 50, true};
    for (uint32_t now = 50; now < 100000; now += 50)
    {
        p.tick(now);
        s = p.snapshot();
        assert(s.queue.state == MotorQueueSim::State::Disarmed);
        assert(s.queue.leaseMask == 0);
        assert(s.lastMockEvent.kind == MotorQueueSim::EventKind::None);
        assert(!s.nativeSimulationAvailable);
        assert(!s.physicalOutputsConnected);
        assert(!p.armNativeSimulation(now, syntheticAllTrue()));
    }
    puts("KNX023 firmware ARDUINO build hardlock: cannot arm, "
         "cannot inject position, no motor events: PASS");
    return 0;
}
