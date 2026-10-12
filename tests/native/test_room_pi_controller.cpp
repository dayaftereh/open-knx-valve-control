#include "../../lib/common/room_pi_controller.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace HeatingZone;
using namespace RoomPi;

static void injectRoom(Inputs& input, uint8_t z, uint32_t now,
                       int16_t desired, int16_t actual)
{
    input.zones[z].setpointCentiC = {desired, now, true};
    input.zones[z].roomActualCentiC = {actual, now, true};
}

static Tuning profiles[Zones]{};

static void testProfileValidation()
{
    Tuning p{};
    assert(validTuning(p));
    p.kpPermillePerKelvin = 0;
    assert(!validTuning(p));
    p = {};
    p.integralTimeSeconds = 0;
    assert(!validTuning(p));
    p = {};
    p.deadbandCentiC = 101;
    assert(!validTuning(p));
    p = {};
    p.slewPermillePerMinute = 0;
    assert(!validTuning(p));
    p = {};
    p.sampleSeconds = 29;
    assert(!validTuning(p));
    p = {};
    p.sampleSeconds = 600;
    assert(validTuning(p));
}

static void testNoJumpAndSlew()
{
    Settings config{};
    Inputs input{};
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    config.motorZone[1] = 1;
    config.motorZone[2] = 1;
    config.motorZone[3] = 1;
    injectRoom(input, 0, 1000, 2300, 1800);
    Bank bank;
    bank.update(config, profiles, input, 1000);
    assert(bank.diagnostic(0).status == Status::Initialized);
    assert(input.zones[0].regulatorOutputPermille.valid);
    assert(input.zones[0].regulatorOutputPermille.value == 0);
    assert(resolve(config, input, 1000).eligibleMotorMask == 0x0f);

    bank.update(config, profiles, input, 30999);
    assert(bank.diagnostic(0).status == Status::Holding);
    assert(input.zones[0].regulatorOutputPermille.value == 0);
    assert(input.zones[0].regulatorOutputPermille.receivedAtMs == 1000);

    bank.update(config, profiles, input, 61000);
    assert(bank.diagnostic(0).status == Status::Updated);
    assert(input.zones[0].regulatorOutputPermille.value == 30);
    assert(input.zones[0].regulatorOutputPermille.receivedAtMs == 61000);
    auto routed = resolve(config, input, 61000);
    assert(routed.eligibleMotorMask == 0x0f);
    for (uint8_t i = 0; i < 4; ++i)
        assert(routed.motors[i].permille == 30);

    bank.update(config, profiles, input, 121000);
    assert(bank.diagnostic(0).status == Status::Updated);
    assert(input.zones[0].regulatorOutputPermille.value == 60);
    // The accumulated I term must NOT grow behind the slew limit.
    assert(bank.diagnostic(0).integralPermille == 0.0);
}

static void testRoomAndDirectAreMutuallyExclusive()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    config.motorZone[1] = 1;
    config.modes[1] = Mode::DirectPercent;
    config.motorZone[2] = 2;
    input.zones[1].directDpt5001Raw = {255, 20, true};

    injectRoom(input, 0, 20, 2250, 2000);
    bank.update(config, profiles, input, 20);
    // Old direct demand is explicitly discarded on first mode entry.
    assert(!input.zones[1].directDpt5001Raw.valid);
    assert(resolve(config, input, 20).eligibleMotorMask == 0x03);
    input.zones[1].directDpt5001Raw = {128, 21, true};
    bank.update(config, profiles, input, 21);
    assert(resolve(config, input, 21).eligibleMotorMask == 0x07);
    assert(resolve(config, input, 21).motors[2].permille == 502);

    // A new mode must not replay the earlier direct KNX request.
    config.modes[0] = Mode::DirectPercent;
    input.zones[0].directDpt5001Raw = {255, 21, true};
    bank.update(config, profiles, input, 1000);
    assert(!input.zones[0].directDpt5001Raw.valid);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    // Any ETS topology/mode reconfiguration invalidates ALL old input
    // epochs, including the unchanged second zone's direct demand.
    assert(resolve(config, input, 1000).eligibleMotorMask == 0);
    input.zones[0].directDpt5001Raw = {0, 1001, true};
    input.zones[1].directDpt5001Raw = {128, 1001, true};
    bank.update(config, profiles, input, 1001);
    auto targets = resolve(config, input, 1001);
    assert(targets.eligibleMotorMask == 0x07);
    assert(targets.motors[0].permille == 0); // valid genuine 0% demand

    // Changing back to RoomTemperature requires NEW room telegrams.
    config.modes[0] = Mode::RoomTemperature;
    bank.update(config, profiles, input, 2000);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    assert(bank.diagnostic(0).status == Status::WaitingForFreshInputs);
    injectRoom(input, 0, 2001, 2300, 1900);
    bank.update(config, profiles, input, 2001);
    assert(bank.diagnostic(0).status == Status::Initialized);
}

static void testFaultLatchAndRecovery()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    config.roomTimeoutSeconds = 30;
    // Use sample 30s to avoid exceeding the room source freshness policy.
    Tuning tuning[Zones]{};
    tuning[0].sampleSeconds = 30;
    injectRoom(input, 0, 0, 2200, 1900);
    bank.update(config, tuning, input, 0);
    bank.update(config, tuning, input, 29000);
    assert(bank.diagnostic(0).status == Status::Holding);
    bank.update(config, tuning, input, 30000);
    assert(bank.diagnostic(0).status == Status::WaitingForInputs);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    assert(resolve(config, input, 30000).eligibleMotorMask == 0);

    // A resumed room sensor alone must not revive the old setpoint.
    input.zones[0].roomActualCentiC = {1910, 31000, true};
    bank.update(config, tuning, input, 31000);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    input.zones[0].setpointCentiC = {2200, 31001, true};
    bank.update(config, tuning, input, 31001);
    assert(bank.diagnostic(0).status == Status::Initialized);
    assert(resolve(config, input, 31001).eligibleMotorMask == 1);

    // An implausible actual room temperature invalidates immediately.
    injectRoom(input, 0, 32000, 2200, 9999);
    bank.update(config, tuning, input, 32000);
    assert(bank.diagnostic(0).status == Status::WaitingForInputs);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    injectRoom(input, 0, 33000, 2200, 2000);
    bank.update(config, tuning, input, 33000);
    assert(bank.diagnostic(0).status == Status::Initialized);

    // Asynchronous KNX telegrams may recover in either order. Latch the
    // first fault barrier, not a moving barrier that invalidates a setpoint
    // merely because it arrived before the next room-actual telegram.
    input.zones[0].roomActualCentiC.valid = false;
    bank.update(config, tuning, input, 34000);
    assert(bank.diagnostic(0).status == Status::WaitingForInputs);
    input.zones[0].setpointCentiC = {2200, 34100, true};
    bank.update(config, tuning, input, 34100);
    assert(bank.diagnostic(0).status == Status::WaitingForInputs);
    input.zones[0].roomActualCentiC = {2010, 34200, true};
    bank.update(config, tuning, input, 34200);
    assert(bank.diagnostic(0).status == Status::Initialized);
}

static void testGapAndTuningChanges()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    injectRoom(input, 0, 0, 2200, 1900);
    bank.update(config, profiles, input, 0);
    bank.update(config, profiles, input, 181000); // >3 x 60s
    assert(bank.diagnostic(0).status == Status::LoopGap);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    bank.update(config, profiles, input, 181001);
    assert(bank.diagnostic(0).status == Status::WaitingForFreshInputs);

    injectRoom(input, 0, 181002, 2200, 1900);
    bank.update(config, profiles, input, 181002);
    assert(bank.diagnostic(0).status == Status::Initialized);

    Tuning tune[Zones]{};
    tune[0].kpPermillePerKelvin = 400;
    bank.update(config, tune, input, 181003);
    assert(bank.diagnostic(0).status == Status::WaitingForFreshInputs);
    injectRoom(input, 0, 181004, 2200, 1900);
    bank.update(config, tune, input, 181004);
    assert(bank.diagnostic(0).status == Status::Initialized);
    tune[0].integralTimeSeconds = 0;
    bank.update(config, tune, input, 181005);
    assert(bank.diagnostic(0).status == Status::InvalidTuning);
    assert(resolve(config, input, 181005).eligibleMotorMask == 0);

    tune[0].integralTimeSeconds = 3600;
    bank.update(config, tune, input, 181006);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    injectRoom(input, 0, 181007, 2200, 1900);
    bank.update(config, tune, input, 181007);
    assert(bank.diagnostic(0).status == Status::Initialized);

    // Any invalid KNX008 motor/zone assignment suppresses *all* channels.
    config.motorZone[7] = 9;
    bank.update(config, tune, input, 181008);
    assert(bank.diagnostic(0).status == Status::InvalidConfiguration);
    assert(!input.zones[0].regulatorOutputPermille.valid);
}

static void testSaturationAndAntiWindup()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    Tuning tune[Zones]{};
    tune[0].kpPermillePerKelvin = 1500;
    tune[0].integralTimeSeconds = 300;
    tune[0].slewPermillePerMinute = 300;
    injectRoom(input, 0, 0, 3500, -2000);
    bank.update(config, tune, input, 0);
    for (uint32_t i = 1; i <= 14; ++i)
    {
        const uint32_t t = i * 60000UL;
        injectRoom(input, 0, t, 3500, -2000);
        bank.update(config, tune, input, t);
        const auto& diag = bank.diagnostic(0);
        assert(diag.outputPermille <= 1000);
        // Saturation / slew limit cannot silently build hidden heat debt.
        assert(diag.integralPermille < 0.00001);
    }
    assert(input.zones[0].regulatorOutputPermille.value == 1000);

    // Strong overshoot must make the valve target decrease, not wind up.
    for (uint32_t i = 15; i <= 20; ++i)
    {
        const uint32_t t = i * 60000UL;
        injectRoom(input, 0, t, 3500, 4500);
        bank.update(config, tune, input, t);
    }
    assert(input.zones[0].regulatorOutputPermille.value == 0);
}

static void testAssignmentReconfigurationFence()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    config.motorZone[1] = 1;
    injectRoom(input, 0, 0, 2300, 1950);
    bank.update(config, profiles, input, 0);
    bank.update(config, profiles, input, 60000);
    assert(resolve(config, input, 60000).eligibleMotorMask == 0x03);
    assert(input.zones[0].regulatorOutputPermille.value == 30);

    // Moving another motor into an active zone must NOT reuse a previously
    // computed output without new room telegrams and a neutral PI restart.
    config.motorZone[2] = 1;
    bank.update(config, profiles, input, 60001);
    assert(!input.zones[0].regulatorOutputPermille.valid);
    assert(resolve(config, input, 60001).eligibleMotorMask == 0);
    assert(bank.diagnostic(0).status == Status::WaitingForFreshInputs);

    injectRoom(input, 0, 60002, 2300, 1950);
    bank.update(config, profiles, input, 60002);
    assert(resolve(config, input, 60002).eligibleMotorMask == 0x07);
    assert(resolve(config, input, 60002).motors[2].permille == 0);

    // Changing the freshness policy is a new configuration epoch too.
    config.roomTimeoutSeconds = 300;
    bank.update(config, profiles, input, 60003);
    assert(resolve(config, input, 60003).eligibleMotorMask == 0);
    injectRoom(input, 0, 60004, 2300, 1950);
    bank.update(config, profiles, input, 60004);
    assert(bank.diagnostic(0).status == Status::Initialized);
}

static void testIndependentEightZonesAndFailureIsolation()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    for (uint8_t z = 0; z < Zones; ++z)
    {
        config.modes[z] = Mode::RoomTemperature;
        config.motorZone[z] = static_cast<uint8_t>(z + 1);
        injectRoom(input, z, 0,
                   static_cast<int16_t>(2000 + 10 * z), 1800);
    }
    bank.update(config, profiles, input, 0);
    assert(resolve(config, input, 0).eligibleMotorMask == 0xff);

    // One invalid room actual affects that zone only, not 7 other rooms.
    input.zones[4].roomActualCentiC.valid = false;
    bank.update(config, profiles, input, 1000);
    assert(bank.diagnostic(4).status == Status::WaitingForInputs);
    assert(resolve(config, input, 1000).eligibleMotorMask == 0xef);
    assert(!input.zones[4].regulatorOutputPermille.valid);

    // Recovery requires both fresh signals for zone 5; other zones persist.
    input.zones[4].roomActualCentiC = {1800, 1001, true};
    bank.update(config, profiles, input, 1001);
    assert(resolve(config, input, 1001).eligibleMotorMask == 0xef);
    input.zones[4].setpointCentiC = {2040, 1002, true};
    bank.update(config, profiles, input, 1002);
    assert(resolve(config, input, 1002).eligibleMotorMask == 0xff);
}

static void testDeadbandPreventsNoiseHunting()
{
    Settings config{};
    Inputs input{};
    Bank bank;
    Tuning tune[Zones]{};
    tune[0].deadbandCentiC = 25;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;

    // Room sensor jitter within +/-0.2 K must not generate PI movement.
    for (uint32_t minute = 0; minute < 15; ++minute)
    {
        const uint32_t t = minute * 60000UL;
        const int16_t room = static_cast<int16_t>(
            2100 + (minute % 2U ? 18 : -18));
        injectRoom(input, 0, t, 2100, room);
        bank.update(config, tune, input, t);
        assert(resolve(config, input, t).eligibleMotorMask == 1);
        assert(input.zones[0].regulatorOutputPermille.value == 0);
        assert(bank.diagnostic(0).integralPermille == 0.0);
    }
}

static void testMillisRollover()
{
    const uint32_t start = 0xFFFFFE00U;
    Settings config{};
    Inputs input{};
    Bank bank;
    config.modes[0] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    injectRoom(input, 0, start, 2300, 2000);
    bank.update(config, profiles, input, start);
    assert(bank.diagnostic(0).status == Status::Initialized);
    const uint32_t next = start + 60000U; // wraps uint32
    bank.update(config, profiles, input, next);
    assert(bank.diagnostic(0).status == Status::Updated);
    assert(input.zones[0].regulatorOutputPermille.value == 30);
    assert(resolve(config, input, next).eligibleMotorMask == 1);
}

static void testToyPlantNoMotorActions()
{
    // This model is synthetic, not calibration against a real heating loop.
    // Two rooms share a limited heating flow; moving one demand mildly
    // reduces the available heat of the other. Sensor updates every minute.
    Settings config{};
    Inputs input{};
    Bank bank;
    Tuning tune[Zones]{};
    config.modes[0] = Mode::RoomTemperature;
    config.modes[1] = Mode::RoomTemperature;
    config.motorZone[0] = 1;
    config.motorZone[1] = 1;
    config.motorZone[2] = 2;
    tune[0].kpPermillePerKelvin = 200;
    tune[1].kpPermillePerKelvin = 200;
    tune[0].integralTimeSeconds = 7200;
    tune[1].integralTimeSeconds = 7200;
    tune[0].slewPermillePerMinute = 20;
    tune[1].slewPermillePerMinute = 20;

    double t0 = 18.0, t1 = 18.5;
    double max0 = t0, max1 = t1;
    double largestStep = 0.0;
    uint16_t prev0 = 0, prev1 = 0;
    for (uint32_t minute = 0; minute < 48UL * 60UL; ++minute)
    {
        const uint32_t now = minute * 60000UL;
        injectRoom(input, 0, now, 2150,
                   static_cast<int16_t>(t0 * 100.0 + 0.5));
        injectRoom(input, 1, now, 2000,
                   static_cast<int16_t>(t1 * 100.0 + 0.5));
        bank.update(config, tune, input, now);
        const auto routed = resolve(config, input, now);
        assert(routed.configurationValid);
        assert(routed.eligibleMotorMask == 0x07);
        const uint16_t motor0 = routed.motors[0].permille;
        const uint16_t motor1 = routed.motors[1].permille;
        const uint16_t motor2 = routed.motors[2].permille;
        assert(motor0 == motor1); // 2 heating circuits share room 1
        assert(motor0 <= 1000 && motor2 <= 1000);
        const uint16_t a = motor0 > prev0 ? motor0 - prev0 : prev0 - motor0;
        const uint16_t b = motor2 > prev1 ? motor2 - prev1 : prev1 - motor2;
        assert(a <= 20 && b <= 20);
        if (a > largestStep) largestStep = a;
        if (b > largestStep) largestStep = b;
        prev0 = motor0;
        prev1 = motor2;
        // Fictitious hydronic plant, 4 h room time constant, ambient 17 C:
        // other valve demand induces -15% shared-flow interaction.
        const double u0 = static_cast<double>(motor0) / 1000.0;
        const double u1 = static_cast<double>(motor2) / 1000.0;
        const double f0 = 1.0 - 0.15 * u1;
        const double f1 = 1.0 - 0.15 * u0;
        t0 += (17.0 + 7.2 * u0 * f0 - t0) / 240.0;
        t1 += (17.0 + 7.2 * u1 * f1 - t1) / 240.0;
        if (t0 > max0) max0 = t0;
        if (t1 > max1) max1 = t1;
        assert(t0 > 10.0 && t0 < 30.0);
        assert(t1 > 10.0 && t1 < 30.0);
    }
    printf("KNX019 toy-plant 48h: zone1=%.2f C zone2=%.2f C; "
           "peak1=%.2f peak2=%.2f; max demand step=%.0f permille/min\n",
           t0, t1, max0, max1, largestStep);
    // This is only a bounded toy-plant regression; it is not proof of
    // convergence, tuning, safety, or hydraulic stability in an actual home.
}

int main()
{
    testProfileValidation();
    testNoJumpAndSlew();
    testRoomAndDirectAreMutuallyExclusive();
    testFaultLatchAndRecovery();
    testGapAndTuningChanges();
    testSaturationAndAntiWindup();
    testAssignmentReconfigurationFence();
    testIndependentEightZonesAndFailureIsolation();
    testDeadbandPreventsNoiseHunting();
    testMillisRollover();
    testToyPlantNoMotorActions();
    puts("KNX019 RoomPI/KNX008 router native simulations: PASS");
    return 0;
}
