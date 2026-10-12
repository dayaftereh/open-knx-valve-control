#include "../../lib/common/room_control_runtime.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace RoomControlRuntime;
using namespace HeatingZone;

static MotorQueueSim::Guards qualifiedSyntheticGuards()
{
    MotorQueueSim::Guards guards{};
    guards.explicitTestPermit = true;
    guards.boardAsBuiltQualified = true;
    guards.supplyQualified = true;
    guards.outputInterlockQualified = true;
    guards.currentMonitoringQualified = true;
    return guards;
}

static void ensureExclusive(const Pipeline& p)
{
    const Snapshot snap = p.snapshot();
    assert(snap.physicalOutputsConnected == false);
    assert(snap.nativeSimulationAvailable);
    const auto occupancy = p.nativeBackendStatus().abstractOccupiedMask;
    const auto lease = snap.queue.leaseMask;
    assert((occupancy & (occupancy - 1U)) == 0);
    assert((lease & (lease - 1U)) == 0);
    assert((occupancy & static_cast<uint8_t>(~lease)) == 0);
    assert(p.nativeBackendStatus().protocolViolations == 0);
}

static void configuredDirect(Pipeline& p)
{
    auto& settings = p.settings();
    settings.modes[0] = Mode::DirectPercent;
    settings.motorZone[0] = 1;
    settings.motorZone[1] = 1;
    p.tick(0); // the KNX019 topology barrier must precede new inputs
    p.inputs().zones[0].directDpt5001Raw = {128, 50, true};
    assert(p.injectNativePosition(0, 0, 10000, 1));
    assert(p.injectNativePosition(1, 0, 10000, 2));
}

static void testBootAndDefaultFailClosed()
{
    Pipeline p;
    p.reset(0);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    assert(p.snapshot().queue.leaseMask == 0);
    assert(p.snapshot().tickCount == 0);
    assert(!p.armNativeSimulation(0, {}));

    // Unconfigured fields never become valid motor demands.
    for (uint32_t now = 100; now <= 2000; now += 100)
    {
        p.tick(now);
        ensureExclusive(p);
        assert(p.snapshot().lastMockEvent.kind ==
               MotorQueueSim::EventKind::None);
    }
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);

    configuredDirect(p);
    p.tick(500);
    assert(p.snapshot().targets.eligibleMotorMask == 0x03);
    assert(p.snapshot().targets.motors[0].permille == 502);
    // Two software target intents are NOT an automatic motor grant.
    assert(p.snapshot().lastMockEvent.kind ==
           MotorQueueSim::EventKind::None);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
}

static void testDirectAndPIEndToEnd()
{
    Pipeline p;
    p.reset(0);
    auto& cfg = p.settings();
    cfg.modes[0] = Mode::DirectPercent;
    cfg.modes[1] = Mode::RoomTemperature;
    cfg.motorZone[0] = 1;
    cfg.motorZone[1] = 1;
    cfg.motorZone[2] = 2;
    p.tick(0); // global topology/PI startup fence

    auto& ins = p.inputs();
    ins.zones[0].directDpt5001Raw = {128, 50, true};
    ins.zones[1].setpointCentiC = {2300, 50, true};
    ins.zones[1].roomActualCentiC = {1900, 50, true};
    for (uint8_t i = 0; i < 3; ++i)
        assert(p.injectNativePosition(i, 0, 10000, i + 1));

    assert(p.armNativeSimulation(0, qualifiedSyntheticGuards()));
    uint32_t startCount = 0, stopCount = 0;
    uint8_t startMask = 0;
    for (uint32_t now = 50; now <= 65500; now += 50)
    {
        if (now == 60000)
        {
            ins.zones[1].setpointCentiC.receivedAtMs = now;
            ins.zones[1].roomActualCentiC.receivedAtMs = now;
        }
        p.tick(now);
        const auto last = p.snapshot().lastMockEvent;
        if (last.kind == MotorQueueSim::EventKind::Start)
        {
            ++startCount;
            startMask |= static_cast<uint8_t>(1U << last.motor);
        }
        if (last.kind == MotorQueueSim::EventKind::Stop)
            ++stopCount;
        ensureExclusive(p);
    }
    const auto d = p.nativeBackendStatus();
    assert(startCount == 3 && stopCount == 3);
    assert(d.startCount == 3 && d.offAckCount == 3);
    assert(d.completedTravelCount == 3);
    assert(d.abortedTravelCount == 0);
    assert(startMask == 0x07);
    assert(p.nativePosition(0).estimatedPermille == 502);
    assert(p.nativePosition(1).estimatedPermille == 502);
    assert(p.nativePosition(2).estimatedPermille == 30);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Idle);
    assert(p.zoneDiagnostic(1).outputValid);
    printf("KNX023 PI/Zone/Queue/native mock: 3 Start, 3 Off-ACK, "
           "M1/M2/M3=502/502/30 permille\n");
}

static void testStopAckLossAndRearm()
{
    Pipeline p;
    p.reset(0);
    configuredDirect(p);
    assert(p.armNativeSimulation(0, qualifiedSyntheticGuards()));
    for (uint32_t now = 50; now <= 700; now += 50)
        p.tick(now);
    assert(p.nativeBackendStatus().startCount == 1);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Running);

    VirtualMotor::Options fault{};
    fault.dropStopAck = true;
    p.setNativeBackendOptions(fault);
    p.inputs().zones[0].directDpt5001Raw.valid = false;
    for (uint32_t now = 750; now <= 4500; now += 50)
    {
        p.tick(now);
        ensureExclusive(p);
    }
    assert(p.snapshot().queue.state == MotorQueueSim::State::StopPending);
    assert(p.snapshot().queue.stopAcknowledgementOverdue);
    assert(p.snapshot().queue.fault == MotorQueueSim::FaultReason::StopAckTimeout);
    assert(p.nativeBackendStatus().startCount == 1);
    assert(!p.armNativeSimulation(4500, qualifiedSyntheticGuards()));
    fault.dropStopAck = false;
    p.setNativeBackendOptions(fault);
    p.tick(4550);
    assert(p.snapshot().queue.state == MotorQueueSim::State::FaultLatched);
    assert(!p.nativePosition(0).referenced);
    assert(p.clearNativeFault(qualifiedSyntheticGuards()));
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    assert(p.armNativeSimulation(4550, qualifiedSyntheticGuards()));
    // Even after re-arm, stale KNX input forbids further motion.
    for (uint32_t now = 4600; now <= 5250; now += 50)
        p.tick(now);
    assert(p.nativeBackendStatus().startCount == 1);
}

static void testResetDiscardsAllState()
{
    Pipeline p;
    p.reset(0);
    configuredDirect(p);
    assert(p.armNativeSimulation(0, qualifiedSyntheticGuards()));
    p.tick(500);
    assert(p.snapshot().lastMockEvent.kind ==
           MotorQueueSim::EventKind::Start);
    assert(p.nativeBackendStatus().abstractOccupiedMask == 1);
    p.reset(600); // synthetic CPU reboot – DOES NOT prove physical All-off
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(p.snapshot().tickCount == 0);
    assert(p.nativeBackendStatus().abstractOccupiedMask == 0);
    // Restarted process deliberately has no remembered position evidence.
    assert(!p.nativePosition(0).referenced);
    p.tick(700);
    ensureExclusive(p);
    assert(p.snapshot().lastMockEvent.kind ==
           MotorQueueSim::EventKind::None);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
}

static void testTargetsCannotOverrideSafety()
{
    Pipeline p;
    p.reset(0);
    configuredDirect(p);
    auto g = qualifiedSyntheticGuards();
    g.supplyQualified = false;
    assert(!p.armNativeSimulation(0, g));
    p.tick(500);
    assert(p.snapshot().targets.eligibleMotorMask == 0x03);
    assert(p.snapshot().lastMockEvent.kind ==
           MotorQueueSim::EventKind::None);
    assert(p.snapshot().queue.leaseMask == 0);
    assert(!p.snapshot().physicalOutputsConnected);
}

int main()
{
    testBootAndDefaultFailClosed();
    testDirectAndPIEndToEnd();
    testStopAckLossAndRearm();
    testResetDiscardsAllState();
    testTargetsCannotOverrideSafety();
    puts("KNX023 runtime native mock integration: PASS");
    return 0;
}
