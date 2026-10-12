#include "../../lib/common/virtual_motor_feedback.hpp"
#include "../../lib/common/room_pi_controller.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace MotorQueueSim;
using namespace HeatingZone;

static Guards nominalGuards()
{
    Guards g{};
    g.explicitTestPermit = true;
    g.boardAsBuiltQualified = true;
    g.supplyQualified = true;
    g.outputInterlockQualified = true;
    g.currentMonitoringQualified = true;
    return g;
}

struct Lab
{
    Queue queue{};
    VirtualMotor::Backend backend{};
    RoomPi::Bank pi{};
    Settings config{};
    Inputs input{};
    RoomPi::Tuning tuning[ZoneCount]{};
    Guards guards = nominalGuards();
    uint32_t startEvents = 0;
    uint32_t stopEvents = 0;
    uint8_t startSeenMask = 0;
    bool allAccepted = true;
    StopReason lastStopReason = StopReason::None;

    Lab()
    {
        queue.reset(0);
        backend.reset();
        for (uint8_t m = 0; m < MotorQueueSim::MotorCount; ++m)
            assert(backend.setEvidence(m, 0, 10000,
                                       static_cast<uint32_t>(m + 1)));
    }

    void tick(uint32_t now)
    {
        pi.update(config, tuning, input, now);
        const Targets targets = HeatingZone::resolve(config, input, now);
        const Acknowledgement reply = backend.poll(now);
        const Event event =
            queue.step(now, targets, backend.positions(), guards, reply);
        allAccepted &= backend.consume(event, now);
        if (event.kind == EventKind::Start)
        {
            ++startEvents;
            startSeenMask |= static_cast<uint8_t>(1U << event.motor);
        }
        if (event.kind == EventKind::Stop)
        {
            ++stopEvents;
            lastStopReason = event.stopReason;
        }
        const auto position = backend.status();
        const auto scheduler = queue.status();
        assert(allAccepted);
        const uint16_t occupied = position.abstractOccupiedMask;
        const uint16_t lease = scheduler.leaseMask;
        assert((occupied & (occupied - 1U)) == 0U);
        assert((lease & (lease - 1U)) == 0U);
        // A virtual output may only be occupied while the owning
        // exclusive scheduler lease remains reserved for that motor.
        assert((occupied & static_cast<uint16_t>(~lease)) == 0U);
        assert(position.protocolViolations == 0U);
    }
};

static void testThreeRealSoftwareComponentsTogether()
{
    Lab lab;
    // Zone 1 has two circuits and is direct Scaling; Zone 2 has one
    // room-PI-controlled circuit. PI runs on the ACTUAL KNX019 class.
    lab.config.modes[0] = Mode::DirectPercent;
    lab.config.modes[1] = Mode::RoomTemperature;
    lab.config.motorZone[0] = 1;
    lab.config.motorZone[1] = 1;
    lab.config.motorZone[2] = 2;
    lab.input.zones[1].setpointCentiC = {2300, 0, true};
    lab.input.zones[1].roomActualCentiC = {1900, 0, true};

    lab.tick(0);
    // Startup topology change invalidates any old direct command.
    lab.input.zones[0].directDpt5001Raw = {128, 50, true};
    assert(lab.queue.arm(0, lab.guards,
                         lab.backend.independentlyAllOff()));
    for (uint32_t now = 50; now <= 65500; now += 50)
    {
        // KNX019 PI computes first changed output at 60s.
        if (now == 60000)
        {
            lab.input.zones[1].setpointCentiC.receivedAtMs = now;
            lab.input.zones[1].roomActualCentiC.receivedAtMs = now;
        }
        lab.tick(now);
    }
    const auto diag = lab.backend.status();
    assert(diag.startCount == 3);
    assert(diag.offAckCount == 3);
    assert(diag.completedTravelCount == 3);
    assert(diag.abortedTravelCount == 0);
    assert(diag.abstractOccupiedMask == 0);
    assert(lab.startSeenMask == 0x07);
    assert(lab.backend.positions()[0].estimatedPermille == 502);
    assert(lab.backend.positions()[1].estimatedPermille == 502);
    assert(lab.backend.positions()[2].estimatedPermille == 30);
    assert(lab.backend.positions()[0].referenced);
    assert(lab.backend.positions()[2].referenced);
    assert(lab.queue.status().state == State::Idle);
    const auto desired = resolve(lab.config, lab.input, 65500);
    assert(desired.eligibleMotorMask == 0x07);
    assert(desired.motors[0].permille ==
           desired.motors[1].permille);
    printf("KNX021 complete integration: %lu virtual starts, "
           "%lu off ACKs, motors M1/M2/M3 = %u/%u/%u promille\n",
           static_cast<unsigned long>(diag.startCount),
           static_cast<unsigned long>(diag.offAckCount),
           lab.backend.positions()[0].estimatedPermille,
           lab.backend.positions()[1].estimatedPermille,
           lab.backend.positions()[2].estimatedPermille);
}

static void testInterruptedMotionLosesPositionCertainty()
{
    Lab lab;
    lab.config.modes[0] = Mode::DirectPercent;
    lab.config.motorZone[0] = 1;
    lab.config.motorZone[1] = 1;
    lab.tick(0); // establish topology/barrier
    lab.input.zones[0].directDpt5001Raw = {255, 50, true};
    assert(lab.queue.arm(0,lab.guards,
                         lab.backend.independentlyAllOff()));
    for (uint32_t now = 50; now <= 700; now += 50)
        lab.tick(now);
    assert(lab.backend.status().abstractOccupiedMask == 1);
    assert(lab.queue.status().state == State::Running);
    // A mock KNX-signal fault cancels the old target. The interrupted
    // position is unknown, even if the previous estimate was valid.
    lab.input.zones[0].directDpt5001Raw.valid = false;
    lab.tick(750);
    assert(lab.queue.status().state == State::StopPending);
    assert(lab.lastStopReason == StopReason::TargetInvalid);
    assert(!lab.backend.independentlyAllOff());
    lab.tick(800);
    assert(lab.backend.independentlyAllOff());
    assert(lab.queue.status().state == State::Disarmed);
    assert(!lab.backend.positions()[0].valid);
    assert(!lab.backend.positions()[0].referenced);
    assert(lab.backend.status().abortedTravelCount == 1);

    // Even with renewed KNX demand and manual re-arm, M1 MUST NOT move
    // without independent new position reference.
    lab.input.zones[0].directDpt5001Raw = {255, 850, true};
    assert(lab.queue.arm(850,lab.guards,
                         lab.backend.independentlyAllOff()));
    for (uint32_t now = 900; now <= 1500; now += 50)
        lab.tick(now);
    assert((lab.startSeenMask & 0x01) == 1); // initial M1 only
    assert(lab.backend.status().startCount == 2);
    // The other referenced circuit M2 may move, M1 remains blocked.
    assert(lab.queue.status().leasedMotor == 1);
    lab.queue.cancelAll();
    lab.tick(1550);
    lab.tick(1600);
    assert(lab.queue.status().state == State::Disarmed);
    assert(!lab.backend.positions()[1].valid);
    // Only a test operator can inject simulated new reference evidence.
    assert(lab.backend.setEvidence(0, 100, 10000, 100));
    assert(lab.backend.setEvidence(1, 0, 10000, 101));
    assert(lab.queue.arm(1600,lab.guards,
                         lab.backend.independentlyAllOff()));
    for (uint32_t now = 1650; now <= 3000; now += 50)
        lab.tick(now);
    assert(lab.backend.status().startCount >= 3);
}

static void testMissingStopAckBlocksOtherChannels()
{
    Lab lab;
    VirtualMotor::Options opts{};
    lab.backend.setOptions(opts);
    lab.config.modes[0] = Mode::DirectPercent;
    lab.config.motorZone[0] = 1;
    lab.config.motorZone[1] = 1;
    lab.tick(0);
    lab.input.zones[0].directDpt5001Raw = {255, 50, true};
    assert(lab.queue.arm(0,lab.guards,
                         lab.backend.independentlyAllOff()));
    for (uint32_t now = 50; now <= 700; now += 50)
        lab.tick(now);
    assert(lab.backend.status().startCount == 1);
    assert(lab.backend.status().abstractOccupiedMask == 1);

    opts.dropStopAck = true;
    lab.backend.setOptions(opts);
    lab.input.zones[0].directDpt5001Raw.valid = false;
    lab.tick(750);
    assert(lab.queue.status().state == State::StopPending);
    assert(lab.queue.status().leaseMask == 1);
    // An output may be off, but without independent AllOff ACK the
    // exclusive lease is NOT released. 4s > 2s stop ACK timeout.
    for (uint32_t now = 800; now <= 4000; now += 50)
        lab.tick(now);
    assert(lab.queue.status().state == State::StopPending);
    assert(lab.queue.status().stopAcknowledgementOverdue);
    assert(lab.queue.status().fault == FaultReason::StopAckTimeout);
    assert(lab.queue.status().leaseMask == 1);
    assert(lab.backend.status().startCount == 1);
    assert(!lab.backend.independentlyAllOff());

    // Once ACKs recover, the overdue lease may be released only after
    // a matching AllOff ACK; re-arm remains manual due latched fault.
    opts.dropStopAck = false;
    lab.backend.setOptions(opts);
    lab.tick(4050);
    assert(lab.queue.status().state == State::FaultLatched);
    assert(lab.queue.status().leaseMask == 0);
    assert(lab.backend.status().abortedTravelCount == 1);
    assert(lab.queue.clearFault(lab.guards,
                                lab.backend.independentlyAllOff()));
    assert(lab.queue.status().state == State::Disarmed);
}

static void testStopThatDoesNotTurnOffNeverGrantsAnotherMotor()
{
    Lab lab;
    lab.config.modes[0] = Mode::DirectPercent;
    lab.config.motorZone[0] = 1;
    lab.config.motorZone[1] = 1;
    lab.tick(0);
    lab.input.zones[0].directDpt5001Raw = {255, 50, true};
    assert(lab.queue.arm(0,lab.guards,true));
    for (uint32_t now = 50; now <= 700; now += 50)
        lab.tick(now);
    assert(lab.backend.status().abstractOccupiedMask == 1);
    VirtualMotor::Options options{};
    options.stuckOnStop = true;
    lab.backend.setOptions(options);
    lab.input.zones[0].directDpt5001Raw.valid = false;
    for (uint32_t now = 750; now <= 4000; now += 50)
        lab.tick(now);
    assert(lab.backend.status().abstractOccupiedMask == 1);
    assert(lab.queue.status().stopAcknowledgementOverdue);
    assert(lab.queue.status().leaseMask == 1);
    assert(lab.backend.status().startCount == 1);
    assert(!lab.backend.independentlyAllOff());
    assert(!lab.queue.clearFault(lab.guards,true));

    // Later mock recovery of stop execution is still subject to the
    // matched STOP token and off-ack delay.
    options.stuckOnStop = false;
    lab.backend.setOptions(options);
    lab.tick(4050);
    assert(lab.queue.status().leaseMask == 1);
    lab.tick(4100);
    assert(lab.queue.status().state == State::FaultLatched);
    assert(lab.queue.status().leaseMask == 0);
    assert(lab.backend.status().abstractOccupiedMask == 0);
}

static void testCrossingMillisWrap()
{
    const uint32_t boot = 0xFFFFFF00UL;
    Queue queue;
    VirtualMotor::Backend backend;
    auto guards = nominalGuards();
    HeatingZone::Settings config{};
    HeatingZone::Inputs input{};
    config.modes[0] = Mode::DirectPercent;
    config.motorZone[0] = 1;
    input.zones[0].directDpt5001Raw = {128, boot, true};
    queue.reset(boot);
    backend.reset();
    assert(backend.setEvidence(0,0,10000,1));
    assert(queue.arm(boot,guards,backend.independentlyAllOff()));
    for (uint32_t delta=0;delta<=7000;delta+=50)
    {
        const uint32_t now=boot+delta;
        const auto ack=backend.poll(now);
        const auto t=resolve(config,input,now);
        const auto e=queue.step(now,t,backend.positions(),guards,ack);
        assert(backend.consume(e,now));
        assert((backend.status().abstractOccupiedMask &
                (backend.status().abstractOccupiedMask - 1U)) == 0U);
    }
    assert(backend.status().completedTravelCount==1);
    assert(backend.positions()[0].estimatedPermille==502);
    assert(queue.status().state==State::Idle);
}

int main()
{
    testThreeRealSoftwareComponentsTogether();
    testInterruptedMotionLosesPositionCertainty();
    testMissingStopAckBlocksOtherChannels();
    testStopThatDoesNotTurnOffNeverGrantsAnotherMotor();
    testCrossingMillisWrap();
    puts("KNX021 integrated PI/zone/exclusive-queue/virtual-backend: PASS");
    return 0;
}
