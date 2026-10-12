#ifndef OPENKNX_HEATING_ZONE_MODEL_HPP
#define OPENKNX_HEATING_ZONE_MODEL_HPP

#include <stdint.h>

// KNX008 is deliberately hardware independent. No Arduino, KNX, GPIO,
// INA219 or actuator driver dependencies. The returned values are merely
// software TARGET INTENTS: executing movement requires KNX004/005/006.
namespace HeatingZone
{
constexpr uint8_t ZoneCount = 8;
constexpr uint8_t MotorCount = 8;
constexpr uint16_t MaxPermille = 1000;

enum class Mode : uint8_t
{
    Disabled = 0,
    RoomTemperature = 1,
    DirectPercent = 2
};

enum class ConfigError : uint8_t
{
    None = 0,
    InvalidMode,
    InvalidAssignment,
    InvalidRoomTimeout,
    InvalidDirectTimeout
};

// Every physical motor has exactly ONE zone ID (0 = unassigned).
// Disabled zones and unassigned motors can never request motion.
struct Settings
{
    Mode modes[ZoneCount] = {};
    uint8_t motorZone[MotorCount] = {};
    uint16_t roomTimeoutSeconds = 900;   // proposed ETS P38
    uint16_t directTimeoutSeconds = 300; // proposed ETS P39
};

template <class T>
struct TimedValue
{
    T value = {};
    uint32_t receivedAtMs = 0;
    bool valid = false;
};

// Each zone gets its OWN external room temperature and command KOs.
// T0/T1..T8 pipe/water temperatures are explicitly not inputs here.
struct ZoneInput
{
    TimedValue<int16_t> setpointCentiC;
    TimedValue<int16_t> roomActualCentiC;
    TimedValue<uint16_t> regulatorOutputPermille; // FUTURE KNX010 PI output
    TimedValue<uint8_t> directDpt5001Raw;         // 0..255 => 0..100%
};

struct Inputs
{
    ZoneInput zones[ZoneCount] = {};
};

struct MotorTarget
{
    bool eligible = false;   // valid software intent, NOT physical permission
    uint8_t zoneId = 0;      // 1..8
    uint16_t permille = 0;   // 0..1000 (0.1 percent increments)
};

struct Targets
{
    bool configurationValid = false;
    ConfigError error = ConfigError::None;
    uint8_t errorIndex = 0;  // 1-based zone/motor for config errors
    uint8_t eligibleMotorMask = 0;
    uint8_t activeZoneMask = 0;
    MotorTarget motors[MotorCount] = {};
};

inline bool isValidMode(Mode mode)
{
    return static_cast<uint8_t>(mode) <=
           static_cast<uint8_t>(Mode::DirectPercent);
}

inline bool validTimeout(uint16_t seconds)
{
    return seconds >= 30 && seconds <= 3600;
}

inline ConfigError validate(const Settings& settings,
                            uint8_t* firstIndex = nullptr)
{
    if (firstIndex)
        *firstIndex = 0;
    if (!validTimeout(settings.roomTimeoutSeconds))
        return ConfigError::InvalidRoomTimeout;
    if (!validTimeout(settings.directTimeoutSeconds))
        return ConfigError::InvalidDirectTimeout;

    for (uint8_t i = 0; i < ZoneCount; ++i)
    {
        if (!isValidMode(settings.modes[i]))
        {
            if (firstIndex)
                *firstIndex = static_cast<uint8_t>(i + 1);
            return ConfigError::InvalidMode;
        }
    }
    for (uint8_t motor = 0; motor < MotorCount; ++motor)
    {
        if (settings.motorZone[motor] > ZoneCount)
        {
            if (firstIndex)
                *firstIndex = static_cast<uint8_t>(motor + 1);
            return ConfigError::InvalidAssignment;
        }
    }
    return ConfigError::None;
}

// DPT 5.001 scaling uses RAW 0..255 for logical 0..100 percent.
// In contrast, legacy DPT 5.004 is an unsigned 0..255 percent counter
// and MUST NOT be reinterpreted as DPT 5.001 bytes.
inline uint16_t rawScalingToPermille(uint8_t raw)
{
    return static_cast<uint16_t>(
        (static_cast<uint32_t>(raw) * MaxPermille + 127U) / 255U);
}

inline uint8_t permilleToRawScaling(uint16_t permille)
{
    if (permille > MaxPermille)
        permille = MaxPermille;
    return static_cast<uint8_t>(
        (static_cast<uint32_t>(permille) * 255U + 500U) / MaxPermille);
}

template <class T>
inline bool fresh(const TimedValue<T>& v, uint32_t nowMs,
                  uint32_t timeoutMs)
{
    return v.valid &&
           static_cast<uint32_t>(nowMs - v.receivedAtMs) < timeoutMs;
}

inline bool validRoomSetpoint(int16_t centiC)
{
    // Proposed conservative room limits. Final ETS values/commissioning
    // constraints require KNX009/010 review, NOT inferred from pipe probes.
    return centiC >= 500 && centiC <= 3500;
}

inline bool validRoomActual(int16_t centiC)
{
    return centiC >= -4000 && centiC <= 8000;
}

inline Targets resolve(const Settings& settings, const Inputs& input,
                       uint32_t nowMs)
{
    Targets result{};
    result.error = validate(settings, &result.errorIndex);
    if (result.error != ConfigError::None)
        return result; // FAIL CLOSED globally on corrupt ETS parameters
    result.configurationValid = true;

    bool ready[ZoneCount] = {};
    uint16_t targetPermille[ZoneCount] = {};

    const uint32_t roomTtlMs =
        static_cast<uint32_t>(settings.roomTimeoutSeconds) * 1000UL;
    const uint32_t directTtlMs =
        static_cast<uint32_t>(settings.directTimeoutSeconds) * 1000UL;

    for (uint8_t z = 0; z < ZoneCount; ++z)
    {
        const ZoneInput& zone = input.zones[z];
        switch (settings.modes[z])
        {
        case Mode::Disabled:
            break;
        case Mode::RoomTemperature:
            // This does not pretend to be a thermal controller: KNX010
            // must compute a regulator result, with anti-windup and fault
            // behavior, and refresh the output time independently.
            if (fresh(zone.setpointCentiC, nowMs, roomTtlMs) &&
                fresh(zone.roomActualCentiC, nowMs, roomTtlMs) &&
                fresh(zone.regulatorOutputPermille, nowMs, roomTtlMs) &&
                validRoomSetpoint(zone.setpointCentiC.value) &&
                validRoomActual(zone.roomActualCentiC.value) &&
                zone.regulatorOutputPermille.value <= MaxPermille)
            {
                ready[z] = true;
                targetPermille[z] = zone.regulatorOutputPermille.value;
            }
            break;
        case Mode::DirectPercent:
            if (fresh(zone.directDpt5001Raw, nowMs, directTtlMs))
            {
                ready[z] = true;
                targetPermille[z] =
                    rawScalingToPermille(zone.directDpt5001Raw.value);
            }
            break;
        }
        if (ready[z])
            result.activeZoneMask |= static_cast<uint8_t>(1U << z);
    }

    for (uint8_t m = 0; m < MotorCount; ++m)
    {
        const uint8_t zoneId = settings.motorZone[m];
        if (zoneId == 0 || !ready[zoneId - 1])
            continue;
        MotorTarget& target = result.motors[m];
        target.eligible = true;
        target.zoneId = zoneId;
        target.permille = targetPermille[zoneId - 1];
        result.eligibleMotorMask |= static_cast<uint8_t>(1U << m);
    }
    return result;
}

static_assert(ZoneCount == 8 && MotorCount == 8,
              "KNX008 physical vs logical mapping changed");
} // namespace HeatingZone

#endif // OPENKNX_HEATING_ZONE_MODEL_HPP
