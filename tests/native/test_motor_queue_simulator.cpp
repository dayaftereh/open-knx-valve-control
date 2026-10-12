#include "../../lib/common/motor_queue_simulator.hpp"
#include "../../lib/common/room_pi_controller.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace MotorQueueSim;

static Guards qualified()
{
    Guards g{};
    g.explicitTestPermit = true;
    g.boardAsBuiltQualified = true;
    g.supplyQualified = true;
    g.outputInterlockQualified = true;
    g.currentMonitoringQualified = true;
    return g; // MOCK EVIDENCE ONLY, no hardware verified.
}

static HeatingZone::Targets targets(uint8_t mask = 0xFF,
                                     uint16_t permille = 500)
{
    HeatingZone::Targets t{};
    t.configurationValid = true;
    t.eligibleMotorMask = mask;
    for (uint8_t i = 0; i < MotorCount; ++i)
    {
        t.motors[i].eligible = (mask & (1U << i)) != 0;
        t.motors[i].zoneId = static_cast<uint8_t>((i % 4U) + 1U);
        t.motors[i].permille = permille;
    }
    return t;
}

static void initialize(PositionEvidence (&position)[MotorCount],
                       uint32_t fullStrokeTimeMs = 10000)
{
    for (uint8_t i = 0; i < MotorCount; ++i)
    {
        position[i].valid = true;
        position[i].referenced = true;
        position[i].estimatedPermille = 0;
        position[i].fullStrokeTimeMs = fullStrokeTimeMs;
        position[i].revision = static_cast<uint32_t>(i + 1);
    }
}

static void assertSingleLease(const Queue& q)
{
    const auto s = q.status();
    const uint16_t mask = s.leaseMask;
    assert((mask & (mask - 1U)) == 0U);
    if (s.state == State::Disarmed ||
        s.state == State::Idle ||
        s.state == State::FaultLatched)
    {
        assert(mask == 0);
        assert(s.leasedMotor == NoMotor);
    }
    else
    {
        assert(mask != 0);
        assert(s.leasedMotor < MotorCount);
        assert(mask == static_cast<uint16_t>(1U << s.leasedMotor));
    }
}

static void testDefaultDisarmAndQualification()
{
    Queue q;
    PositionEvidence positions[MotorCount]{};
    initialize(positions);
    const auto all = targets();
    auto g = qualified();
    assert(q.status().state == State::Disarmed);
    assert(q.step(600, all, positions, g).kind == EventKind::None);

    g.boardAsBuiltQualified = false;
    assert(!q.arm(0, g, true));
    g = qualified();
    assert(!q.arm(0, g, false));
    assert(q.arm(0, g, true));
    assert(!q.arm(1, g, true)); // already armed
    assert(q.step(499, all, positions, g).kind == EventKind::None);
    auto start = q.step(500, all, positions, g);
    assert(start.kind == EventKind::Start);
    assert(start.motor == 0);
    assert(start.direction == Direction::LogicalOpen);
    assert(start.targetPermille == 500);
    assert(start.plannedTravelMs == 5000);
    assert(start.token != 0);
    assert(q.status().state == State::StartPending);
    assertSingleLease(q);
    assert(q.step(999, all, positions, g).kind == EventKind::None);

    // Incorrect START token is ignored.
    Acknowledgement bad{AckKind::Started, start.token + 1, false};
    assert(q.step(1000, all, positions, g, bad).kind == EventKind::None);
    Acknowledgement startAck{AckKind::Started, start.token, false};
    assert(q.step(1001, all, positions, g, startAck).kind == EventKind::None);
    assert(q.status().state == State::Running);
    assert(q.step(6000, all, positions, g).kind == EventKind::None);
    auto stop = q.step(6001, all, positions, g);
    assert(stop.kind == EventKind::Stop && stop.motor == 0);
    assert(stop.stopReason == StopReason::PlannedTravelTime);
    assert(stop.token != start.token);
    assertSingleLease(q);

    // The STOP event must be idempotently retried with its original token.
    const auto repeated = q.step(6100, all, positions, g);
    assert(repeated.kind == EventKind::Stop &&
           repeated.token == stop.token);

    // Old Start ACK, unrelated Stop ACK, or Stop ACK without independent
    // all-off confirmation must not release the exclusive lease.
    assert(q.step(6200, all, positions, g, startAck).kind == EventKind::Stop);
    assert(q.step(6201, all, positions, g,
                  {AckKind::AllOff, stop.token + 1, true}).kind ==
           EventKind::Stop);
    assert(q.step(6202, all, positions, g,
                  {AckKind::AllOff, stop.token, false}).kind ==
           EventKind::Stop);
    assert(q.status().leasedMotor == 0);
    assert(q.step(6203, all, positions, g,
                  {AckKind::AllOff, stop.token, true}).kind ==
           EventKind::None);
    assert(q.status().state == State::Idle);
    assert(q.status().completedLeaseCount == 1);
    assertSingleLease(q);

    // The previous position cannot be replayed without a new estimate
    // revision. Round-robin should take motor 1 next (not motor 0).
    assert(q.step(6702, all, positions, g).kind == EventKind::None);
    start = q.step(6703, all, positions, g);
    assert(start.kind == EventKind::Start && start.motor == 1);
}

static void testRoundRobinAllEightAndRevision()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p);
    const auto all = targets();
    auto g = qualified();
    q.reset(0);
    assert(q.arm(0, g, true));
    uint32_t now = 500;
    uint32_t completed = 0;
    for (uint8_t expected = 0; expected < MotorCount; ++expected)
    {
        auto start = q.step(now, all, p, g);
        assert(start.kind == EventKind::Start);
        assert(start.motor == expected);
        assertSingleLease(q);
        assert(q.step(now + 1, all, p, g,
                      {AckKind::Started, start.token, false}).kind ==
               EventKind::None);
        assert(q.status().state == State::Running);
        const auto stop = q.step(now + 1 + start.plannedTravelMs,
                                 all, p, g);
        assert(stop.kind == EventKind::Stop);
        assert(stop.motor == expected);
        assertSingleLease(q);
        now += 2 + start.plannedTravelMs;
        assert(q.step(now, all, p, g,
                      {AckKind::AllOff, stop.token, true}).kind ==
               EventKind::None);
        ++completed;
        assert(q.status().completedLeaseCount == completed);
        assertSingleLease(q);
        p[expected].estimatedPermille = 500;
        ++p[expected].revision;
        now += 500;
    }
    assert(q.status().state == State::Idle);
    // Confirmed targets have reached their desired position.
    assert(q.step(now, all, p, g).kind == EventKind::None);
    assertSingleLease(q);
}

static void testExpiredInputStopsAndRequiresRearm()
{
    Queue q;
    HeatingZone::Settings cfg{};
    HeatingZone::Inputs input{};
    cfg.modes[0] = HeatingZone::Mode::DirectPercent;
    cfg.modes[1] = HeatingZone::Mode::DirectPercent;
    cfg.motorZone[0] = 1;
    cfg.motorZone[1] = 2;
    cfg.directTimeoutSeconds = 30;
    input.zones[0].directDpt5001Raw = {255, 0, true};
    input.zones[1].directDpt5001Raw = {255, 0, true};
    PositionEvidence p[MotorCount]{};
    initialize(p, 120000);
    const auto g = qualified();
    q.reset(0);
    assert(q.arm(0, g, true));
    const auto first = q.step(500, HeatingZone::resolve(cfg,input,500), p,g);
    assert(first.kind == EventKind::Start && first.motor == 0);
    assert(q.step(501, HeatingZone::resolve(cfg,input,501), p,g,
                  {AckKind::Started, first.token, false}).kind ==
           EventKind::None);
    // Force age timeout to invalidate both live KNX008 intents.
    const auto invalid = HeatingZone::resolve(cfg,input,30000);
    assert(invalid.eligibleMotorMask == 0);
    const auto stop = q.step(30000,invalid,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::TargetInvalid);
    assert(q.status().rearmRequired);
    assert(q.step(30001,invalid,p,g,
                  {AckKind::AllOff, stop.token, true}).kind ==
           EventKind::None);
    assert(q.status().state == State::Disarmed);
    assert(q.step(30500,invalid,p,g).kind == EventKind::None);
    assertSingleLease(q);

    // Fresh input must arrive AND the simulated operator must explicitly
    // re-arm from independently off-proven state.
    input.zones[0].directDpt5001Raw = {128, 30501, true};
    assert(q.step(30501, HeatingZone::resolve(cfg,input,30501), p,g).kind ==
           EventKind::None);
    assert(q.arm(30501,g,true));
    // Old position needs revision update after stop; otherwise not
    // automatically replayed. The second motor has a fresh intent? No.
    const auto fresh = HeatingZone::resolve(cfg,input,31001);
    assert(q.step(31001,fresh,p,g).kind == EventKind::None);
    ++p[0].revision;
    const auto second = q.step(31002,fresh,p,g);
    assert(second.kind == EventKind::Start && second.motor == 0);
}

static void testChangedTargetAndSafetyFault()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p, 100000);
    auto wanted = targets(0x03,800);
    auto g = qualified();
    q.reset(0);
    assert(q.arm(0,g,true));
    const auto first = q.step(500,wanted,p,g);
    assert(first.kind == EventKind::Start && first.motor == 0);
    assert(q.step(501,wanted,p,g,
                  {AckKind::Started,first.token,false}).kind ==
           EventKind::None);
    wanted.motors[0].permille = 100;
    auto stop = q.step(700,wanted,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::TargetChanged);
    assert(q.status().leasedMotor == 0);
    assert(q.step(701,wanted,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::Disarmed);
    assert(!q.status().stopAcknowledgementOverdue);
    assert(q.arm(701,g,true));
    assert(q.step(1201,wanted,p,g).kind == EventKind::Start);
    // Motor 1 becomes the next fair candidate because motor0 has not
    // received fresh position revision since its aborted run.
    assert(q.status().leasedMotor == 1);
    g.supplyQualified = false;
    stop = q.step(1202,wanted,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::SafetyLost);
    assert(q.status().fault == FaultReason::SafetyLost);
    assert(q.step(1203,wanted,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::FaultLatched);
    assert(!q.arm(1300,g,true));
    g = qualified();
    assert(!q.arm(1300,g,true)); // fault clearing is distinct
    assert(!q.clearFault(g,false));
    assert(q.clearFault(g,true));
    assert(q.status().state == State::Disarmed);
    assert(q.arm(1300,g,true));
}

static void testStartAckAndStopAckTimeouts()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p);
    const auto all=targets(0x03,500);
    const auto g=qualified();
    q.reset(0);
    assert(q.arm(0,g,true));
    const auto start=q.step(500,all,p,g);
    assert(start.kind == EventKind::Start);
    assert(q.step(1499,all,p,g).kind == EventKind::None);
    auto stop=q.step(1500,all,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::StartAckTimeout);
    assert(q.status().fault == FaultReason::StartAckTimeout);
    // STOP continuously re-issued, even long after its ACK deadline.
    assert(q.step(3499,all,p,g).kind == EventKind::Stop);
    const auto repeated=q.step(3500,all,p,g);
    assert(repeated.kind == EventKind::Stop &&
           repeated.token == stop.token);
    assert(q.status().stopAcknowledgementOverdue);
    // A timed-out STOP still holds the single exclusive lease.
    assert(q.status().leasedMotor == 0);
    assertSingleLease(q);
    assert(!q.clearFault(g,true)); // cannot bypass missing stop ACK
    assert(q.step(5000,all,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::FaultLatched);
    assert(q.clearFault(g,true));
    assert(q.arm(5000,g,true));
}

static void testOperatorCancelAndInvalidCalibration()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p);
    auto all=targets(0x03,1000);
    auto g=qualified();
    q.reset(0);
    assert(q.arm(0,g,true));
    p[0].referenced=false;
    p[1].fullStrokeTimeMs=500000; // invalid calibration
    assert(q.step(500,all,p,g).kind == EventKind::None);
    p[0].referenced=true;
    p[0].fullStrokeTimeMs=180000;
    // full 180s move > permitted 120s; must NOT truncate it.
    assert(q.step(501,all,p,g).kind == EventKind::None);
    p[0].fullStrokeTimeMs=100000;
    const auto start=q.step(502,all,p,g);
    assert(start.kind == EventKind::Start && start.motor == 0);
    assert(q.step(503,all,p,g,{AckKind::Started,start.token,false}).kind ==
           EventKind::None);
    q.cancelAll();
    auto stop=q.step(504,all,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::Cancelled);
    assert(q.step(505,all,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::Disarmed);
    assert(q.step(900,all,p,g).kind == EventKind::None);
}

static void testWraparoundAndTokens()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p);
    const auto all=targets(0x01,500);
    const auto g=qualified();
    const uint32_t t0=0xFFFFFF00UL;
    q.reset(t0);
    assert(q.arm(t0,g,true));
    const uint32_t startAt=t0+500U;
    const auto start=q.step(startAt,all,p,g);
    assert(start.kind == EventKind::Start);
    assert(q.step(startAt+1,all,p,g,
                  {AckKind::Started,start.token,false}).kind ==
           EventKind::None);
    auto stop=q.step(startAt+5001,all,p,g);
    assert(stop.kind == EventKind::Stop &&
           stop.stopReason == StopReason::PlannedTravelTime);
    assert(q.step(startAt+5002,all,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::Idle);
    const uint32_t oldToken=stop.token;
    q.reset(8000); // no token reuse after RESET in same process
    assert(q.arm(8000,g,true));
    ++p[0].revision;
    const auto newStart=q.step(8500,all,p,g);
    assert(newStart.kind == EventKind::Start);
    assert(newStart.token > oldToken);
    // An old START ACK must not activate the new lease.
    assert(q.step(8501,all,p,g,
                  {AckKind::Started,start.token,false}).kind ==
           EventKind::None);
    assert(q.status().state == State::StartPending);
}

static void testBackendFaultMaskStops()
{
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p);
    auto all=targets(0x03,300);
    auto g=qualified();
    q.reset(0);
    assert(q.arm(0,g,true));
    g.motorFaultMask=0x01;
    auto first=q.step(500,all,p,g);
    assert(first.kind == EventKind::Start && first.motor == 1);
    assert(q.step(501,all,p,g,
                  {AckKind::Started,first.token,false}).kind ==
           EventKind::None);
    g.motorFaultMask=0x02;
    auto stop=q.step(502,all,p,g);
    assert(stop.kind == EventKind::Stop);
    assert(stop.stopReason == StopReason::MotorFault);
    assert(q.status().fault == FaultReason::MotorFault);
    assert(q.step(503,all,p,g,
                  {AckKind::AllOff,stop.token,true}).kind == EventKind::None);
    assert(q.status().state == State::FaultLatched);
}

static void testRealKNX008IntentIntegration()
{
    // This is an actual KNX008 router object, not a hardcoded toy queue.
    HeatingZone::Settings settings{};
    HeatingZone::Inputs in{};
    settings.modes[0] = HeatingZone::Mode::DirectPercent;
    settings.motorZone[0] = 1;
    settings.motorZone[1] = 1;
    settings.motorZone[2] = 1;
    in.zones[0].directDpt5001Raw={128,0,true};
    const auto t=HeatingZone::resolve(settings,in,500);
    assert(t.eligibleMotorMask==0x07);
    assert(t.motors[0].permille==502);
    Queue q;
    PositionEvidence p[MotorCount]{};
    initialize(p,50000);
    auto g=qualified();
    q.reset(0);
    assert(q.arm(0,g,true));
    const auto event=q.step(500,t,p,g);
    assert(event.kind==EventKind::Start && event.motor==0);
    assert(event.direction==Direction::LogicalOpen);
    assert(event.targetPermille==502);
    // A stale KNX008 input removes every live intent -> required Stop.
    const auto stale=HeatingZone::resolve(settings,in,301000);
    assert(stale.eligibleMotorMask==0);
    const auto stop=q.step(301000,stale,p,g);
    assert(stop.kind==EventKind::Stop &&
           stop.stopReason==StopReason::TargetInvalid);
    assertSingleLease(q);
}

int main()
{
    testDefaultDisarmAndQualification();
    testRoundRobinAllEightAndRevision();
    testExpiredInputStopsAndRequiresRearm();
    testChangedTargetAndSafetyFault();
    testStartAckAndStopAckTimeouts();
    testOperatorCancelAndInvalidCalibration();
    testWraparoundAndTokens();
    testBackendFaultMaskStops();
    testRealKNX008IntentIntegration();
    puts("KNX020 native exclusive motor-queue simulator tests: PASS");
    return 0;
}
