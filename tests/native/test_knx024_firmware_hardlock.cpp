#ifndef ARDUINO
#define ARDUINO 10800
#endif
#include "../../lib/common/knx024_room_dpt_adapter.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

// Entire KNX024 adapter can compile under real firmware preprocessing.
// No actual KNX GroupObject exists yet: this is a typed simulated frame.
int main()
{
    RoomControlRuntime::Pipeline pipeline;
    Knx024::Adapter adapter;
    adapter.reset(pipeline, 0);

    HeatingZone::Settings cfg{};
    cfg.modes[0] = HeatingZone::Mode::DirectPercent;
    cfg.motorZone[0] = 1;
    assert(adapter.configure(pipeline, cfg, 0));
    const uint8_t raw = 255;
    const Knx024::Frame proposed{
        38, Knx024::Dpt::Scaling5001,
        Knx024::FrameKind::GroupValueWrite,
        &raw, 1};
    assert(adapter.receive(pipeline, proposed, 50) ==
           Knx024::Status::Accepted);
    adapter.tick(pipeline, 100);
    assert(pipeline.snapshot().targets.eligibleMotorMask == 1);
    assert(pipeline.snapshot().targets.motors[0].permille == 1000);
    Knx024::ProposedOutput out{};
    assert(adapter.requestedOutput(pipeline, 0, 100, out));
    assert(out.objectNumber == 39 && out.payload == 255);

    MotorQueueSim::Guards fake{};
    fake.explicitTestPermit = true;
    fake.boardAsBuiltQualified = true;
    fake.supplyQualified = true;
    fake.outputInterlockQualified = true;
    fake.currentMonitoringQualified = true;
    assert(!pipeline.armNativeSimulation(100, fake));
    assert(!pipeline.injectNativePosition(0, 100, 10000, 1));
    for (uint32_t now = 200; now < 1500; now += 100)
    {
        adapter.tick(pipeline, now);
        assert(pipeline.snapshot().queue.state ==
               MotorQueueSim::State::Disarmed);
        assert(pipeline.snapshot().queue.leaseMask == 0);
        assert(pipeline.snapshot().lastMockEvent.kind ==
               MotorQueueSim::EventKind::None);
        assert(!pipeline.snapshot().physicalOutputsConnected);
    }
    puts("KNX024 Arduino DPT adapter: RAM-only, motor hardlock PASS");
    return 0;
}
