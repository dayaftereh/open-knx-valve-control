#include "../../lib/common/knx024_room_dpt_adapter.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace Knx024;
using namespace HeatingZone;

static const uint8_t Temperature23[2] = {0x0C, 0x7E}; // 23.00C
static const uint8_t Temperature19[2] = {0x07, 0x6C}; // 19.00C

static Frame frame(uint16_t ko, Dpt dpt, const uint8_t* payload,
                   uint8_t length, FrameKind kind = FrameKind::GroupValueWrite)
{
    return {ko, dpt, kind, payload, length};
}

static void testDpt9001ExactEncoding()
{
    int16_t centi = 999;
    const uint8_t plus20[2] = {0x07, 0xD0}; // 20C, exp0, mantissa2000
    const uint8_t negative1[2] = {0x87, 0x9C}; // -1.00C, exp0, M=-100
    const uint8_t negative40[2] = {0x94, 0x18}; // -40.00C, exp3, M=-500
    const uint8_t badSentinel[2] = {0x7F, 0xFF};
    const uint8_t overRange[2] = {0x7F, 0xFE};
    assert(decodeTemperature(Temperature23, 2, centi) && centi == 2300);
    assert(decodeTemperature(Temperature19, 2, centi) && centi == 1900);
    assert(decodeTemperature(plus20, 2, centi) && centi == 2000);
    assert(decodeTemperature(negative1, 2, centi) && centi == -100);
    assert(decodeTemperature(negative40, 2, centi) && centi == -4000);
    assert(!decodeTemperature(badSentinel, 2, centi));
    assert(!decodeTemperature(overRange, 2, centi));
    assert(!decodeTemperature(nullptr, 2, centi));
    assert(!decodeTemperature(plus20, 1, centi));
    printf("DPT9.001 signed mantissa/exponent/0x7FFF: PASS\n");
}

static void testExactKOMap()
{
    uint8_t zone = 255;
    InputKind kind = InputKind::RequestedOutput;
    Dpt type = Dpt::Unknown;
    for (uint8_t i = 0; i < 8; ++i)
    {
        for (uint8_t field = 0; field < 4; ++field)
        {
            const uint16_t ko = objectFor(i, static_cast<InputKind>(field));
            assert(ko == static_cast<uint16_t>(36 + i * 4 + field));
            const bool isRx = receiveDescriptor(ko, zone, kind, type);
            assert(isRx == (field < 3));
            if (field < 3)
            {
                assert(zone == i);
                assert(static_cast<uint8_t>(kind) == field);
                assert(type == (field == 2 ?
                    Dpt::Scaling5001 : Dpt::Temperature9001));
            }
        }
    }
    for (uint16_t ko = 1; ko <= 35; ++ko)
        assert(!receiveDescriptor(ko, zone, kind, type));
    for (uint16_t ko = 68; ko <= 120; ++ko)
        assert(!receiveDescriptor(ko, zone, kind, type));
    printf("8 zones KO36..67 receive-only contract + legacy KO17..24: PASS\n");
}

static void testDirectAcrossAllEightZones()
{
    RoomControlRuntime::Pipeline p;
    Adapter adapter;
    adapter.reset(p, 0);
    assert(!adapter.configured());
    const uint8_t raw = 128;
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001, &raw, 1), 0) ==
           Status::IgnoredUnconfigured);
    Settings config{};
    for (uint8_t zone = 0; zone < 8; ++zone)
    {
        config.modes[zone] = Mode::DirectPercent;
        config.motorZone[zone] = static_cast<uint8_t>(zone + 1);
    }
    assert(adapter.configure(p, config, 0));
    for (uint8_t zone = 0; zone < 8; ++zone)
    {
        const uint16_t ko = objectFor(zone, InputKind::DirectDemand);
        assert(adapter.receive(p, frame(ko, Dpt::Scaling5001, &raw, 1), 50) ==
               Status::Accepted);
    }
    adapter.tick(p, 100);
    assert(p.snapshot().targets.eligibleMotorMask == 0xFF);
    assert(p.snapshot().targets.activeZoneMask == 0xFF);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    for (uint8_t i = 0; i < 8; ++i)
    {
        assert(p.snapshot().targets.motors[i].permille == 502);
        ProposedOutput tx{};
        assert(adapter.requestedOutput(p, i, 100, tx));
        assert(tx.objectNumber == objectFor(i, InputKind::RequestedOutput));
        assert(tx.declaredDpt == Dpt::Scaling5001);
        assert(tx.payload == 128);
    }
    ProposedOutput tx{};
    assert(!adapter.requestedOutput(p, 8, 100, tx));
    assert(!adapter.requestedOutput(p, 0, 101, tx)); // must be same tick
    // Input bytes are now stale; no new requested output or motor target.
    adapter.tick(p, 300050);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(!adapter.requestedOutput(p, 0, 300050, tx));
    printf("8 zones direct percent scale, time-to-live and TX intents: PASS\n");
}

static void testPIExternalRoomsAndDptGuards()
{
    RoomControlRuntime::Pipeline p;
    Adapter adapter;
    adapter.reset(p, 0);
    Settings cfg{};
    cfg.modes[0] = Mode::RoomTemperature;
    cfg.motorZone[0] = 1;
    cfg.motorZone[1] = 1;
    assert(adapter.configure(p, cfg, 0));
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2), 50) == Status::Accepted);
    assert(adapter.receive(p, frame(37, Dpt::Temperature9001,
                                    Temperature19, 2), 50) == Status::Accepted);
    adapter.tick(p, 50);
    assert(p.inputs().zones[0].setpointCentiC.value == 2300);
    assert(p.inputs().zones[0].roomActualCentiC.value == 1900);
    assert(p.snapshot().targets.eligibleMotorMask == 3);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    assert(!p.snapshot().physicalOutputsConnected);
    ProposedOutput requested{};
    assert(adapter.requestedOutput(p, 0, 50, requested));
    assert(requested.objectNumber == 39);
    // Before the first minute PI limiter may still be at zero.
    adapter.tick(p, 60050);
    assert(p.snapshot().targets.eligibleMotorMask == 3);
    assert(p.snapshot().targets.motors[0].permille == 30);
    assert(p.snapshot().targets.motors[1].permille == 30);
    assert(adapter.requestedOutput(p, 0, 60050, requested));
    assert(requested.payload ==
           HeatingZone::permilleToRawScaling(30));

    // Reject illegal attempt to feed historical 5.004 motor KO as 5.001.
    const uint8_t raw = 128;
    assert(adapter.receive(p, frame(17, Dpt::LegacyPercent5004,
                                    &raw, 1), 60100) ==
           Status::IgnoredNotReceiveObject);
    assert(adapter.receive(p, frame(39, Dpt::Scaling5001,
                                    &raw, 1), 60100) ==
           Status::IgnoredNotReceiveObject);
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2,
                                    FrameKind::GroupValueRead), 60100) ==
           Status::IgnoredNonWrite);
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    &raw, 1), 60100) ==
           Status::IgnoredWrongMode);
    assert(adapter.receive(p, frame(36, Dpt::Scaling5001,
                                    &raw, 1), 60100) ==
           Status::InvalidatedTypeMismatch);
    adapter.tick(p, 60100);
    assert(!p.inputs().zones[0].setpointCentiC.valid);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(!adapter.requestedOutput(p, 0, 60100, requested));

    // KNX 0x7FFF invalid data must revoke formerly valid room reading.
    const uint8_t invalid[2] = {0x7F, 0xFF};
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2), 60150) == Status::Accepted);
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    invalid, 2), 60200) ==
           Status::InvalidatedTemperature);
    assert(!p.inputs().zones[0].setpointCentiC.valid);
    adapter.tick(p, 60200);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    printf("DPT9.001/room PI, source isolation, invalidation and output: PASS\n");
}

static void testWrongLengthDomainAndReconfiguration()
{
    RoomControlRuntime::Pipeline p;
    Adapter adapter;
    adapter.reset(p, 0);
    Settings cfg{};
    cfg.modes[0] = Mode::DirectPercent;
    cfg.motorZone[0] = 1;
    assert(adapter.configure(p, cfg, 0));
    const uint8_t rawFull = 255;
    const uint8_t rawZero = 0;
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    &rawFull, 1), 50) == Status::Accepted);
    adapter.tick(p, 50);
    assert(p.snapshot().targets.motors[0].permille == 1000);
    ProposedOutput out{};
    assert(adapter.requestedOutput(p, 0, 50, out) && out.payload == 255);
    assert(adapter.receive(p, frame(38, Dpt::LegacyPercent5004,
                                    &rawFull, 1), 100) ==
           Status::InvalidatedTypeMismatch);
    adapter.tick(p, 100);
    assert(!adapter.requestedOutput(p, 0, 100, out));
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    &rawZero, 2), 150) ==
           Status::InvalidatedMalformedPayload);
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    nullptr, 1), 150) ==
           Status::InvalidatedMalformedPayload);
    adapter.tick(p, 150);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    &rawZero, 1), 200) == Status::Accepted);
    adapter.tick(p, 200);
    assert(p.snapshot().targets.motors[0].permille == 0);
    assert(adapter.requestedOutput(p, 0, 200, out) && out.payload == 0);

    // Even changing only motor topology invalidates any prior input.
    cfg.motorZone[1] = 1;
    assert(adapter.configure(p, cfg, 250));
    adapter.tick(p, 300);
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(adapter.receive(p, frame(38, Dpt::Scaling5001,
                                    &rawFull, 1), 350) == Status::Accepted);
    adapter.tick(p, 350);
    assert(p.snapshot().targets.eligibleMotorMask == 3);

    // Someone mutates the runtime setting without the adapter's
    // configure guard: fail closed, clear software inputs and disarm.
    p.settings().modes[0] = Mode::RoomTemperature;
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2), 400) ==
           Status::DisarmedConfigurationChanged);
    assert(!adapter.configured());
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(p.snapshot().queue.state == MotorQueueSim::State::Disarmed);
    assert(adapter.counters().configurationFences >= 3);

    assert(!adapter.configure(p, Settings{Mode(0xFF)}, 450));
    assert(!adapter.configured());
    printf("Malformed DPT5.001, reassignment and config drift failclosed: PASS\n");
}

static void testRoomDomainsAndWrapTime()
{
    RoomControlRuntime::Pipeline p;
    Adapter adapter;
    adapter.reset(p, 0xFFFFFF00U);
    Settings cfg{};
    cfg.modes[0] = Mode::RoomTemperature;
    cfg.motorZone[0] = 1;
    assert(adapter.configure(p, cfg, 0xFFFFFF00U));
    const uint8_t tooColdSetpoint[2] = {0x87, 0x9C}; // -1.00C
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    tooColdSetpoint, 2), 0xFFFFFF30U) ==
           Status::InvalidatedTemperature);
    assert(!p.inputs().zones[0].setpointCentiC.valid);
    // A second validly encoded but out-of-range ROOM actual (100.00C)
    // is rejected even though it fits the signed 16-bit centi-C format.
    const uint8_t tooHotRoom[2] = {0x1C, 0xE2};
    assert(adapter.receive(p, frame(37, Dpt::Temperature9001,
                                    tooHotRoom, 2), 0xFFFFFF40U) ==
           Status::InvalidatedTemperature);
    // Positive plausible data sent before a 32-bit millis wrap.
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2), 0xFFFFFF50U) ==
           Status::Accepted);
    assert(adapter.receive(p, frame(37, Dpt::Temperature9001,
                                    Temperature19, 2), 0xFFFFFF50U) ==
           Status::Accepted);
    // GroupValueResponse is not a GroupValueWrite: it cannot override
    // an already-fresh input with a new different room actual.
    assert(adapter.receive(p, frame(37, Dpt::Temperature9001,
                                    tooHotRoom, 2,
                                    FrameKind::GroupValueResponse),
                           0x00000010U) == Status::IgnoredNonWrite);
    assert(p.inputs().zones[0].roomActualCentiC.value == 1900);
    adapter.tick(p, 0x00000050U);
    assert(p.snapshot().targets.eligibleMotorMask == 1);
    assert(!p.snapshot().physicalOutputsConnected);
    adapter.tick(p, 900100U); // >900s after wrap from input receipt
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    ProposedOutput wrapOutput{};
    assert(!adapter.requestedOutput(p, 0, 900100U, wrapOutput));
    adapter.reset(p, 900200U);
    assert(!adapter.configured());
    assert(p.snapshot().targets.eligibleMotorMask == 0);
    assert(adapter.receive(p, frame(36, Dpt::Temperature9001,
                                    Temperature23, 2), 900250U) ==
           Status::IgnoredUnconfigured);
    printf("DPT9 bounds, response rejection, wrap freshness and reboot: PASS\n");
}

int main()
{
    testDpt9001ExactEncoding();
    testExactKOMap();
    testDirectAcrossAllEightZones();
    testPIExternalRoomsAndDptGuards();
    testWrongLengthDomainAndReconfiguration();
    testRoomDomainsAndWrapTime();
    puts("KNX024 proposed ETS RX/TX typed adapter native: PASS");
    return 0;
}
