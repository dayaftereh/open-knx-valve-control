#include "../../lib/common/motor_queue_simulator.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

// KNX020 simulated-only stress harness. No actual output driver is linked.
// An abstract "occupied" bit persists from Start until matching AllOff ACK.
using namespace MotorQueueSim;

static uint32_t randomNext(uint32_t& seed)
{
    seed ^= seed << 13;
    seed ^= seed >> 17;
    seed ^= seed << 5;
    return seed;
}

static Guards qualified()
{
    Guards g{};
    g.explicitTestPermit = true;
    g.boardAsBuiltQualified = true;
    g.supplyQualified = true;
    g.outputInterlockQualified = true;
    g.currentMonitoringQualified = true;
    return g;
}

int main()
{
    Queue queue;
    PositionEvidence position[MotorCount]{};
    for (uint8_t i = 0; i < MotorCount; ++i)
    {
        position[i].valid = true;
        position[i].referenced = true;
        position[i].estimatedPermille = 0;
        position[i].fullStrokeTimeMs = 8000;
        position[i].revision = i + 1;
    }

    HeatingZone::Targets input{};
    input.configurationValid = true;
    uint32_t seed = 0x31415926UL;
    uint32_t pendingStart = 0;
    uint32_t pendingStop = 0;
    uint8_t currentMockMotor = NoMotor;
    uint8_t occupied = 0;
    uint32_t startCount = 0;
    uint32_t confirmedStopCount = 0;
    uint16_t targetWhenStarted = 200;
    auto g = qualified();
    queue.reset(0);

    for (uint32_t step = 0; step < 20000; ++step)
    {
        const uint32_t now = step * 100UL;
        const uint32_t randValue = randomNext(seed);
        g.supplyQualified = (step % 191U) != 30U;

        if (step % 79U == 0)
        {
            const uint16_t t = static_cast<uint16_t>(
                100U + randValue % 800U);
            input.eligibleMotorMask =
                (step % 5U == 0) ? 0x55U : 0xFFU;
            for (uint8_t i = 0; i < MotorCount; ++i)
            {
                input.motors[i].eligible =
                    (input.eligibleMotorMask & (1U << i)) != 0;
                input.motors[i].zoneId = static_cast<uint8_t>(
                    i % HeatingZone::ZoneCount + 1);
                input.motors[i].permille = t;
            }
        }
        if (step % 127U == 0)
            input.configurationValid = false;
        if (step % 127U == 1)
            input.configurationValid = true;
        if (step % 331U == 0)
            queue.cancelAll();

        if (queue.status().state == State::FaultLatched &&
            g.qualified() && occupied == 0)
            (void)queue.clearFault(g, true);
        if (queue.status().state == State::Disarmed &&
            g.qualified() && occupied == 0)
            (void)queue.arm(now, g, true);

        Acknowledgement ack{};
        if (pendingStop != 0)
        {
            ack = {AckKind::AllOff, pendingStop, true};
            occupied = 0; // mock-only, verified off feedback
            if (currentMockMotor != NoMotor)
                ++position[currentMockMotor].revision;
            currentMockMotor = NoMotor;
            pendingStop = 0;
            ++confirmedStopCount;
        }
        else if (pendingStart != 0)
        {
            ack = {AckKind::Started, pendingStart, false};
            pendingStart = 0;
        }

        const auto event = queue.step(now, input, position, g, ack);
        const auto status = queue.status();
        const uint8_t lease = status.leaseMask;
        assert((lease & (lease - 1U)) == 0);
        if (event.kind == EventKind::Start)
        {
            // A second motor grant while any earlier abstract motor still
            // occupies its lease would be a test failure.
            assert(occupied == 0);
            assert(event.motor < MotorCount);
            occupied = static_cast<uint8_t>(1U << event.motor);
            currentMockMotor = event.motor;
            targetWhenStarted = event.targetPermille;
            pendingStart = event.token;
            ++startCount;
        }
        if (event.kind == EventKind::Stop)
        {
            assert(event.motor < MotorCount);
            assert(lease == (1U << event.motor));
            pendingStop = event.token;
            currentMockMotor = event.motor;
            // Does NOT change occupied until next matching AllOff ack.
        }
        (void)targetWhenStarted;
        assert((occupied & (occupied - 1U)) == 0);
    }

    printf("KNX020 stress: 20000 ticks, %lu starts, %lu stop ACKs, "
           "maximum concurrent mock motors = 1\n",
           static_cast<unsigned long>(startCount),
           static_cast<unsigned long>(confirmedStopCount));
    assert(startCount >= 20);
    assert(confirmedStopCount >= 15);
    puts("KNX020 deterministic stress simulation: PASS");
    return 0;
}
