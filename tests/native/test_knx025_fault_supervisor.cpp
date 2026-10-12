#include "../../lib/common/knx025_fault_supervisor.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace Knx025;
using namespace HeatingZone;

static MotorQueueSim::Guards nativeAllTrue()
{
    MotorQueueSim::Guards g{};
    g.explicitTestPermit = true;
    g.boardAsBuiltQualified = true;
    g.supplyQualified = true;
    g.outputInterlockQualified = true;
    g.currentMonitoringQualified = true;
    return g; // SIMULATOR ONLY: not real electrical evidence
}

static Knx024::Frame directFrame(const uint8_t* raw, uint8_t len = 1,
                                 Knx024::Dpt type = Knx024::Dpt::Scaling5001)
{
    return {38, type, Knx024::FrameKind::GroupValueWrite, raw, len};
}

static Knx024::Frame roomFrame(uint16_t ko, const uint8_t* v, uint8_t len = 2)
{
    return {ko, Knx024::Dpt::Temperature9001,
            Knx024::FrameKind::GroupValueWrite, v, len};
}

struct Rig
{
    RoomControlRuntime::Pipeline pipeline;
    Knx024::Adapter adapter;
    Supervisor supervisor;

    explicit Rig(uint32_t bootTime = 0)
    {
        supervisor.boot(pipeline, adapter, bootTime);
    }

    void configureDirect(uint32_t now = 0, uint16_t timeout = 30)
    {
        Settings cfg{};
        cfg.modes[0] = Mode::DirectPercent;
        cfg.motorZone[0] = 1;
        cfg.directTimeoutSeconds = timeout;
        assert(supervisor.configure(pipeline, adapter, cfg, now));
    }

    void configureTemperature(uint32_t now = 0, uint16_t timeout = 30)
    {
        Settings cfg{};
        cfg.modes[0] = Mode::RoomTemperature;
        cfg.motorZone[0] = 1;
        cfg.roomTimeoutSeconds = timeout;
        assert(supervisor.configure(pipeline, adapter, cfg, now));
    }

    void sendDirect(uint32_t when, uint8_t raw = 128)
    {
        assert(supervisor.receive(
            pipeline, adapter, directFrame(&raw), when) ==
            Knx024::Status::Accepted);
    }

    void tick(uint32_t when, Signals signals = {})
    {
        supervisor.softwareTick(pipeline, adapter, signals, when);
        const auto diag = supervisor.diagnostics();
        assert(diag.physicalOutputsVerifiedOff == false);
        assert(pipeline.snapshot().physicalOutputsConnected == false);
    }
};

static void bootWithoutConfigurationIsNotFault()
{
    Rig r;
    for (uint32_t t = 50; t <= 1500; t += 50)
        r.tick(t);
    auto d = r.supervisor.diagnostics();
    assert(d.phase == Phase::Unconfigured);
    assert(d.firstFault == Fault::None);
    assert(d.faultEpochCount == 0);
    assert(d.freshZoneMask == 0 && d.requiredZoneMask == 0);
    assert(r.pipeline.snapshot().queue.state ==
           MotorQueueSim::State::Disarmed);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 1600, true));
    puts("KNX025 boot without V3 configuration does not alarm: PASS");
}

static void activeDirectSourceStaleRequiresFreshRecovery()
{
    Rig r;
    r.configureDirect();
    for (uint32_t t = 100; t <= 1000; t += 100)
        r.tick(t);
    assert(r.supervisor.diagnostics().phase ==
           Phase::WaitingForFreshInputs);
    assert(r.supervisor.diagnostics().faultEpochCount == 0);
    r.sendDirect(1050, 128);
    r.tick(1100);
    assert(r.supervisor.diagnostics().phase ==
           Phase::HealthySoftwareInputs);
    assert(r.supervisor.diagnostics().everReadyZoneMask == 1);
    assert(r.pipeline.snapshot().targets.motors[0].permille == 502);

    // 30s timeout. All steps remain below the 2s software deadline.
    for (uint32_t t = 1600; t <= 31600; t += 500)
        r.tick(t);
    const auto d = r.supervisor.diagnostics();
    assert(d.phase == Phase::FaultLatched);
    assert(d.firstFault == Fault::DirectDemandExpired);
    assert(d.firstFaultZone == 1);
    assert(d.faultEpochCount == 1);
    assert(d.freshZoneMask == 0);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);

    const uint8_t raw = 255;
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, directFrame(&raw), 31700) ==
        Knx024::Status::IgnoredUnconfigured);
    r.tick(31800);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::DirectDemandExpired); // first fault stays sticky
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 31900, true));
    assert(r.supervisor.diagnostics().phase == Phase::Unconfigured);
    assert(r.pipeline.snapshot().queue.state ==
           MotorQueueSim::State::Disarmed);
    assert(!r.adapter.configured());
    r.tick(32000);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    r.configureDirect(32050);
    r.tick(32100);
    assert(r.supervisor.diagnostics().phase ==
           Phase::WaitingForFreshInputs);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    r.sendDirect(32150, 255);
    r.tick(32200);
    assert(r.supervisor.diagnostics().phase ==
           Phase::HealthySoftwareInputs);
    assert(r.pipeline.snapshot().targets.motors[0].permille == 1000);
    assert(r.pipeline.snapshot().queue.state ==
           MotorQueueSim::State::Disarmed);
    puts("KNX025 stale DPT5.001 sticky fault, no automatic resurrection: PASS");
}

static void roomPIInvalidAndStaleInput()
{
    static const uint8_t setpoint23[] = {0x0C, 0x7E};
    static const uint8_t room19[] = {0x07, 0x6C};
    static const uint8_t invalidDpt[] = {0x7F, 0xFF};
    Rig r;
    r.configureTemperature();
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, roomFrame(36, setpoint23), 50) ==
        Knx024::Status::Accepted);
    r.tick(100);
    assert(r.supervisor.diagnostics().phase ==
           Phase::WaitingForFreshInputs);
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, roomFrame(37, room19), 150) ==
        Knx024::Status::Accepted);
    r.tick(200);
    assert(r.supervisor.diagnostics().phase == Phase::HealthySoftwareInputs);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 1);
    // Receiving KNX's invalid 0x7FFF revokes formerly ready ROOM source.
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, roomFrame(37, invalidDpt), 250) ==
        Knx024::Status::InvalidatedTemperature);
    assert(r.supervisor.diagnostics().phase == Phase::FaultLatched);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::InvalidRoomTelegram);
    assert(r.supervisor.diagnostics().firstFaultZone == 1);
    r.tick(300);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 400, true));
    r.configureTemperature(450);
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, roomFrame(36, setpoint23), 500) ==
        Knx024::Status::Accepted);
    assert(r.supervisor.receive(
        r.pipeline, r.adapter, roomFrame(37, room19), 500) ==
        Knx024::Status::Accepted);
    r.tick(550);
    assert(r.supervisor.diagnostics().phase == Phase::HealthySoftwareInputs);
    for (uint32_t now = 1050; now <= 31050; now += 500)
        r.tick(now);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::RoomSourceExpired);
    assert(r.supervisor.diagnostics().firstFaultZone == 1);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    puts("KNX025 room setpoint/actual loss invalidates PI and latches: PASS");
}

static void physicalProbeTelemetryIsIndependentOfRoomInput()
{
    Rig r;
    r.configureDirect();
    r.sendDirect(50);
    Signals sig{};
    sig.manifoldTelemetryObserved = true;
    sig.manifoldTelemetryOnline = false; // ATtiny water sensor link lost
    r.tick(100, sig);
    auto diag = r.supervisor.diagnostics();
    assert(diag.phase == Phase::HealthySoftwareInputs);
    assert(diag.manifoldTelemetryWarning);
    assert(diag.firstFault == Fault::None);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 1);
    sig.manifoldTelemetryOnline = true;
    r.tick(150, sig);
    assert(!r.supervisor.diagnostics().manifoldTelemetryWarning);
    assert(r.supervisor.diagnostics().phase == Phase::HealthySoftwareInputs);
    puts("KNX025 manifold T0..T8 telemetry warning independent: PASS");
}

static void transportLossBlocksRecoverUntilOnline()
{
    // Known-offline must stop BEFORE a first-ever control tick, not only
    // after a previously observed healthy network connection.
    {
        Rig initiallyOffline;
        initiallyOffline.configureDirect();
        assert(initiallyOffline.pipeline.injectNativePosition(
            0, 0, 10000, 1));
        assert(initiallyOffline.pipeline.armNativeSimulation(
            0, nativeAllTrue()));
        initiallyOffline.sendDirect(50);
        Signals offline{};
        offline.roomTransportMonitored = true;
        offline.roomTransportOnline = false;
        initiallyOffline.tick(500, offline);
        assert(initiallyOffline.supervisor.diagnostics().firstFault ==
               Fault::RoomTransportLost);
        assert(initiallyOffline.pipeline.nativeBackendStatus().startCount == 0);
        assert(initiallyOffline.pipeline.snapshot().queue.leaseMask == 0);
    }

    Rig r;
    r.configureDirect();
    r.sendDirect(50);
    Signals link{};
    link.roomTransportMonitored = true;
    link.roomTransportOnline = true;
    r.tick(100, link);
    assert(r.supervisor.diagnostics().phase == Phase::HealthySoftwareInputs);
    link.roomTransportOnline = false;
    r.tick(150, link);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::RoomTransportLost);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 160, true));
    link.roomTransportOnline = true;
    r.tick(200, link);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::RoomTransportLost);
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 250, true));
    assert(!r.adapter.configured());
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    puts("KNX025 simulated room KNX transport drop/recovery gate: PASS");
}

static void malformedAndConfigurationDriftStayLatched()
{
    Rig r;
    r.configureDirect();
    r.sendDirect(50);
    r.tick(100);
    const uint8_t value = 128;
    assert(r.supervisor.receive(r.pipeline, r.adapter,
        directFrame(&value, 1, Knx024::Dpt::LegacyPercent5004), 150) ==
        Knx024::Status::InvalidatedTypeMismatch);
    r.tick(200);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::InvalidRoomTelegram);
    const uint8_t oldValue = 255;
    assert(r.supervisor.receive(r.pipeline, r.adapter,
        directFrame(&oldValue), 220) ==
        Knx024::Status::IgnoredUnconfigured);
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 250, true));
    r.configureDirect(300);
    r.sendDirect(350);
    r.tick(400);
    r.pipeline.settings().directTimeoutSeconds = 31;
    r.tick(450);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::SoftwareConfigurationChanged);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    puts("KNX025 wrong DPT5.004 + out-of-band config drift: PASS");
}

static void softwareLoopWatchdogAndUint32Wrap()
{
    Rig r(0xFFFFFF00UL);
    r.configureDirect(0xFFFFFF00UL);
    r.sendDirect(0xFFFFFF50UL, 255);
    r.tick(0xFFFFFF80UL);
    r.tick(0x00000050UL); // across 32-bit rollover
    assert(r.supervisor.diagnostics().phase == Phase::HealthySoftwareInputs);
    r.tick(0x00000A50UL); // gap 2560ms > max permissible 2000
    assert(r.supervisor.diagnostics().phase == Phase::FaultLatched);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::SoftwareLoopStalled);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    puts("KNX025 software scheduling monitor rollover and overrun: PASS");
}

static void virtualMotorLeaseStopAckMustCompleteBeforeRecovery()
{
    Rig r;
    r.configureDirect();
    assert(r.pipeline.injectNativePosition(0, 0, 10000, 11));
    assert(r.pipeline.armNativeSimulation(0, nativeAllTrue()));
    r.sendDirect(50);
    for (uint32_t now = 100; now <= 650; now += 50)
        r.tick(now);
    assert(r.pipeline.nativeBackendStatus().startCount == 1);
    assert(r.pipeline.snapshot().queue.leaseMask == 1);

    const uint8_t badValue = 200;
    VirtualMotor::Options options{};
    options.dropStopAck = true;
    r.pipeline.setNativeBackendOptions(options);
    assert(r.supervisor.receive(
        r.pipeline, r.adapter,
        directFrame(&badValue, 2), 700) ==
        Knx024::Status::InvalidatedMalformedPayload);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::InvalidRoomTelegram);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 700, true));

    // Active native queue must request STOP and RETAIN one motor lease.
    for (uint32_t now = 750; now <= 3450; now += 50)
        r.tick(now);
    assert(r.pipeline.nativeBackendStatus().startCount == 1);
    assert(r.pipeline.snapshot().queue.leaseMask == 1);
    assert(r.pipeline.snapshot().queue.stopAcknowledgementOverdue);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::InvalidRoomTelegram); // first cause retained
    assert(r.supervisor.diagnostics().simulatedQueueFault ==
           MotorQueueSim::FaultReason::StopAckTimeout);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 3500, true));

    options.dropStopAck = false;
    r.pipeline.setNativeBackendOptions(options);
    for (uint32_t now = 3500; now <= 3750; now += 50)
        r.tick(now);
    assert(r.pipeline.snapshot().queue.leaseMask == 0);
    assert(r.pipeline.nativeBackendStatus().abstractOccupiedMask == 0);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 3800, false));
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 3850, true));
    assert(r.pipeline.snapshot().queue.state ==
           MotorQueueSim::State::Disarmed);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    assert(!r.pipeline.nativePosition(0).referenced);
    assert(r.supervisor.diagnostics().faultEpochCount == 1);
    assert(r.supervisor.diagnostics().recoveryCount == 1);
    puts("KNX025 STOP-ACK token lease preserved, manual recovery only: PASS");
}

static void reconfigurationCannotDropAnActiveMotorLease()
{
    Rig r;
    r.configureDirect();
    assert(r.pipeline.injectNativePosition(0, 0, 10000, 1));
    assert(r.pipeline.armNativeSimulation(0, nativeAllTrue()));
    r.sendDirect(50);
    for (uint32_t now = 100; now <= 650; now += 50)
        r.tick(now);
    assert(r.pipeline.snapshot().queue.leaseMask == 1);

    Settings different = r.pipeline.settings();
    different.motorZone[1] = 1;
    assert(!r.supervisor.configure(r.pipeline, r.adapter, different, 700));
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::SoftwareConfigurationChanged);
    assert(r.pipeline.snapshot().queue.leaseMask == 1);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 700, true));
    for (uint32_t now = 750; now <= 1000; now += 50)
        r.tick(now);
    assert(r.pipeline.snapshot().queue.leaseMask == 0);
    assert(r.pipeline.nativeBackendStatus().abstractOccupiedMask == 0);
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 1050, true));
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    assert(r.pipeline.snapshot().queue.state ==
           MotorQueueSim::State::Disarmed);
    puts("KNX025 mid-lease ETS topology change cannot drop ACK/lease: PASS");
}

static void nativeQueueFaultAndOperatorStop()
{
    Rig r;
    r.configureDirect();
    assert(r.pipeline.injectNativePosition(0, 0, 10000, 1));
    assert(r.pipeline.armNativeSimulation(0, nativeAllTrue()));
    VirtualMotor::Options options{};
    options.dropStartAck = true;
    r.pipeline.setNativeBackendOptions(options);
    r.sendDirect(50);
    for (uint32_t now = 100; now <= 2000; now += 50)
        r.tick(now);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::MotorQueueFault);
    assert(r.pipeline.nativeBackendStatus().startCount == 1);
    assert(r.pipeline.snapshot().queue.leaseMask == 0);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 2050, false));
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 2100, true));
    r.configureDirect(2150);
    r.sendDirect(2200);
    Signals emergency{};
    emergency.manualEmergencyStop = true;
    r.tick(2250, emergency);
    assert(r.supervisor.diagnostics().firstFault ==
           Fault::OperatorEmergencyStop);
    assert(r.pipeline.snapshot().targets.eligibleMotorMask == 0);
    assert(!r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 2300, true));
    r.tick(2350); // emergency cleared, only operator can recover
    assert(r.supervisor.acknowledgeAndRequireFresh(
        r.pipeline, r.adapter, 2400, true));
    puts("KNX025 native start-ACK fault and manual E-stop: PASS");
}

static void passiveFirmwareIsNotANewKNXBus()
{
    RoomControlRuntime::Pipeline p;
    Supervisor monitor;
    p.reset(0);
    monitor.reset(0);
    Signals s{};
    monitor.observeFirmware(p, s, 100);
    assert(monitor.diagnostics().phase == Phase::Unconfigured);
    assert(monitor.diagnostics().firstFault == Fault::None);
    assert(!monitor.diagnostics().physicalOutputsVerifiedOff);
    s.manifoldTelemetryObserved = true;
    s.manifoldTelemetryOnline = false;
    monitor.observeFirmware(p, s, 200);
    assert(monitor.diagnostics().manifoldTelemetryWarning);
    assert(monitor.diagnostics().phase == Phase::Unconfigured);
    monitor.observeFirmware(p, s, 2300);
    assert(monitor.diagnostics().firstFault ==
           Fault::SoftwareLoopStalled);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    puts("KNX025 passive production diagnostics only, no V3 bus binding: PASS");
}

int main()
{
    bootWithoutConfigurationIsNotFault();
    activeDirectSourceStaleRequiresFreshRecovery();
    roomPIInvalidAndStaleInput();
    physicalProbeTelemetryIsIndependentOfRoomInput();
    transportLossBlocksRecoverUntilOnline();
    malformedAndConfigurationDriftStayLatched();
    softwareLoopWatchdogAndUint32Wrap();
    virtualMotorLeaseStopAckMustCompleteBeforeRecovery();
    reconfigurationCannotDropAnActiveMotorLease();
    nativeQueueFaultAndOperatorStop();
    passiveFirmwareIsNotANewKNXBus();
    puts("RESULT: KNX025 native fault/recovery/diagnostic scenarios PASS");
    return 0;
}
