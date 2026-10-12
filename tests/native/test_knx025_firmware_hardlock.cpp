#ifndef ARDUINO
#define ARDUINO 10800
#endif
#include "../../lib/common/knx025_fault_supervisor.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main()
{
    RoomControlRuntime::Pipeline p;
    Knx024::Adapter adapter;
    Knx025::Supervisor supervisor;
    supervisor.boot(p, adapter, 0);
    HeatingZone::Settings config{};
    config.modes[0] = HeatingZone::Mode::DirectPercent;
    config.motorZone[0] = 1;
    assert(supervisor.configure(p, adapter, config, 0));

    const uint8_t direct = 255;
    Knx024::Frame frame{38, Knx024::Dpt::Scaling5001,
                        Knx024::FrameKind::GroupValueWrite,
                        &direct, 1};
    assert(supervisor.receive(p, adapter, frame, 50) ==
           Knx024::Status::Accepted);

    MotorQueueSim::Guards fake{};
    fake.explicitTestPermit = true;
    fake.boardAsBuiltQualified = true;
    fake.supplyQualified = true;
    fake.outputInterlockQualified = true;
    fake.currentMonitoringQualified = true;

    // All tests deliberately build the ARDUINO path, so a spurious
    // physically-unchecked "qualified" permit must never start motion.
    for (uint32_t now = 100; now <= 2000; now += 100)
    {
        supervisor.softwareTick(p, adapter, {}, now);
        assert(!p.armNativeSimulation(now, fake));
        assert(!p.injectNativePosition(0, 200, 15000, 1));
        assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
        assert(p.snapshot().queue.leaseMask == 0);
        assert(p.snapshot().lastMockEvent.kind ==
               MotorQueueSim::EventKind::None);
        assert(!p.snapshot().nativeSimulationAvailable);
        assert(!p.snapshot().physicalOutputsConnected);
        assert(!supervisor.diagnostics().physicalOutputsVerifiedOff);
    }
    assert(supervisor.diagnostics().phase ==
           Knx025::Phase::HealthySoftwareInputs);
    Knx025::Signals emergency{};
    emergency.manualEmergencyStop = true;
    supervisor.softwareTick(p, adapter, emergency, 2100);
    assert(supervisor.diagnostics().phase == Knx025::Phase::FaultLatched);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(!supervisor.acknowledgeAndRequireFresh(
        p, adapter, 2200, false));
    // A software acknowledgement still cannot grant hardware control:
    supervisor.softwareTick(p, adapter, {}, 2200);
    assert(supervisor.acknowledgeAndRequireFresh(
        p, adapter, 2300, true));
    assert(!adapter.configured());
    assert(!p.armNativeSimulation(2400, fake));
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    puts("KNX025 ARDUINO fault supervisor compile + motor hardlock: PASS");
    return 0;
}
