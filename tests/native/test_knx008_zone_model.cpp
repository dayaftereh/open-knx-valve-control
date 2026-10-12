#include "../../lib/common/heating_zone_model.hpp"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace HeatingZone;

static void scalingContract()
{
    assert(rawScalingToPermille(0) == 0);
    assert(rawScalingToPermille(128) == 502);
    assert(rawScalingToPermille(255) == 1000);
    assert(rawScalingToPermille(50) == 196);
    // Raw 50 in legacy DPT5.004 means 50%, NOT 19.6% DPT5.001.
    assert(rawScalingToPermille(50) != 500);
    assert(permilleToRawScaling(0) == 0);
    assert(permilleToRawScaling(500) == 128);
    assert(permilleToRawScaling(1000) == 255);
    assert(permilleToRawScaling(9999) == 255);
    for (unsigned int raw = 0; raw <= 255U; ++raw)
        assert(permilleToRawScaling(rawScalingToPermille(
            static_cast<uint8_t>(raw))) == raw);
}

static void groupSizesOneToFour()
{
    for (uint8_t size = 1; size <= 4; ++size)
    {
        Settings config{};
        Inputs inputs{};
        config.modes[0] = Mode::DirectPercent;
        for (uint8_t motor = 0; motor < size; ++motor)
            config.motorZone[motor] = 1;
        inputs.zones[0].directDpt5001Raw = {128, 1000, true};

        auto result = resolve(config, inputs, 1000);
        assert(result.configurationValid && result.error == ConfigError::None);
        assert(result.eligibleMotorMask == ((1U << size) - 1U));
        assert(result.activeZoneMask == 0x01);
        for (uint8_t motor = 0; motor < 8; ++motor)
        {
            assert(result.motors[motor].eligible == (motor < size));
            if (motor < size)
            {
                assert(result.motors[motor].zoneId == 1);
                assert(result.motors[motor].permille == 502);
            }
        }
    }
}

static void eightMotorsThreeZonesAndRealZero()
{
    Settings config{};
    Inputs inputs{};
    config.modes[0] = Mode::DirectPercent;
    config.modes[1] = Mode::DirectPercent;
    config.modes[2] = Mode::DirectPercent;
    for (uint8_t i = 0; i < 8; ++i)
        config.motorZone[i] = i < 4 ? 1 : (i < 7 ? 2 : 3);
    inputs.zones[0].directDpt5001Raw = {128, 7777, true};
    inputs.zones[1].directDpt5001Raw = {255, 7777, true};
    inputs.zones[2].directDpt5001Raw = {0, 7777, true};

    const auto output = resolve(config, inputs, 7800);
    assert(output.configurationValid);
    assert(output.eligibleMotorMask == 0xff);
    assert(output.activeZoneMask == 0x07);
    for (uint8_t i = 0; i < 8; ++i)
    {
        assert(output.motors[i].eligible);
        const uint16_t expect = i < 4 ? 502 : (i < 7 ? 1000 : 0);
        assert(output.motors[i].permille == expect);
        assert(output.motors[i].zoneId == config.motorZone[i]);
    }
}

static void temperatureIsNotDirectDemand()
{
    Settings config{};
    Inputs inputs{};
    config.modes[0] = Mode::RoomTemperature;
    config.modes[1] = Mode::DirectPercent;
    config.motorZone[0] = 1;
    config.motorZone[1] = 1;
    config.motorZone[2] = 2;

    auto &room = inputs.zones[0];
    room.setpointCentiC = {2100, 50000, true};
    room.roomActualCentiC = {1920, 50000, true};
    // PI output comes from future KNX010 algorithm. This test injects it.
    room.regulatorOutputPermille = {275, 50000, true};
    room.directDpt5001Raw = {255, 50000, true}; // ignored in temp mode

    auto &direct = inputs.zones[1];
    direct.directDpt5001Raw = {51, 50000, true};
    direct.regulatorOutputPermille = {1000, 50000, true}; // ignored direct

    auto result = resolve(config, inputs, 50010);
    assert(result.configurationValid);
    assert(result.eligibleMotorMask == 7);
    assert(result.motors[0].permille == 275);
    assert(result.motors[1].permille == 275);
    assert(result.motors[2].permille == 200);

    // Both actual and setpoint must be fresh for an internal regulator.
    room.roomActualCentiC.valid = false;
    result = resolve(config, inputs, 50020);
    assert(result.eligibleMotorMask == 0x04);
    // Also do not derive room-air temperature from local T0..T8 water probes.
    room.roomActualCentiC = {-4001, 50020, true};
    assert(resolve(config, inputs, 50021).eligibleMotorMask == 0x04);
    room.roomActualCentiC = {-1000, 50020, true};
    room.regulatorOutputPermille.value = 1001;
    assert(resolve(config, inputs, 50021).eligibleMotorMask == 0x04);
    room.regulatorOutputPermille.value = 0; // genuine 0% permitted
    result = resolve(config, inputs, 50021);
    assert(result.motors[0].eligible && result.motors[0].permille == 0);
}

static void disabledUnassignedAndStaleness()
{
    Settings cfg{};
    Inputs inputs{};
    cfg.modes[0] = Mode::DirectPercent;
    cfg.modes[1] = Mode::Disabled;
    cfg.motorZone[0] = 1;
    cfg.motorZone[1] = 0; // unassigned
    cfg.motorZone[2] = 2; // disabled
    cfg.directTimeoutSeconds = 30;
    inputs.zones[0].directDpt5001Raw = {255, 1000, true};
    inputs.zones[1].directDpt5001Raw = {255, 1000, true};

    assert(resolve(cfg, inputs, 1000).eligibleMotorMask == 0x01);
    assert(resolve(cfg, inputs, 30999).eligibleMotorMask == 0x01);
    assert(resolve(cfg, inputs, 31000).eligibleMotorMask == 0);
    inputs.zones[0].directDpt5001Raw = {0, 31000, true};
    auto r = resolve(cfg, inputs, 31000);
    assert(r.eligibleMotorMask == 0x01 && r.motors[0].permille == 0);

    cfg.modes[0] = Mode::RoomTemperature;
    assert(resolve(cfg, inputs, 31001).eligibleMotorMask == 0); // mode switch no mixing
    cfg.modes[0] = Mode::DirectPercent;
    cfg.motorZone[0] = 2;
    assert(resolve(cfg, inputs, 31001).eligibleMotorMask == 0); // zone2 disabled
    cfg.motorZone[0] = 3; // zone3 lacks any new demand
    assert(resolve(cfg, inputs, 31001).eligibleMotorMask == 0);
}

static void corruptConfigurationFailsClosed()
{
    Settings cfg{};
    Inputs input{};
    cfg.modes[0] = Mode::DirectPercent;
    cfg.motorZone[0] = 1;
    input.zones[0].directDpt5001Raw = {255, 0, true};
    assert(resolve(cfg, input, 0).eligibleMotorMask == 1);

    cfg.motorZone[7] = 9; // one invalid channel invalidates all intents
    auto r = resolve(cfg, input, 0);
    assert(!r.configurationValid);
    assert(r.error == ConfigError::InvalidAssignment);
    assert(r.errorIndex == 8);
    assert(r.eligibleMotorMask == 0);

    cfg.motorZone[7] = 0;
    cfg.modes[4] = static_cast<Mode>(255);
    r = resolve(cfg, input, 0);
    assert(!r.configurationValid && r.error == ConfigError::InvalidMode);
    assert(r.errorIndex == 5 && r.eligibleMotorMask == 0);

    cfg.modes[4] = Mode::Disabled;
    cfg.roomTimeoutSeconds = 0;
    assert(resolve(cfg, input, 0).error == ConfigError::InvalidRoomTimeout);
    cfg.roomTimeoutSeconds = 900;
    cfg.directTimeoutSeconds = 3601;
    assert(resolve(cfg, input, 0).error == ConfigError::InvalidDirectTimeout);
}

static void millisWraparoundFreshness()
{
    Settings cfg{};
    Inputs input{};
    cfg.modes[0] = Mode::DirectPercent;
    cfg.motorZone[0] = 1;
    cfg.directTimeoutSeconds = 30;
    const uint32_t start = 0xFFFFFF00U;
    input.zones[0].directDpt5001Raw = {128, start, true};
    assert(resolve(cfg, input, start + 20U).eligibleMotorMask == 1);
    assert(resolve(cfg, input, start + 29999U).eligibleMotorMask == 1);
    assert(resolve(cfg, input, start + 30000U).eligibleMotorMask == 0);
}

int main()
{
    scalingContract();
    groupSizesOneToFour();
    eightMotorsThreeZonesAndRealZero();
    temperatureIsNotDirectDemand();
    disabledUnassignedAndStaleness();
    corruptConfigurationFailsClosed();
    millisWraparoundFreshness();
    puts("KNX008 native 8-motor/8-zone design router: PASS");
    return 0;
}
