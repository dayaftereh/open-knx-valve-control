#ifndef OPENKNX_KNX024_ROOM_DPT_ADAPTER_HPP
#define OPENKNX_KNX024_ROOM_DPT_ADAPTER_HPP

#include "room_control_runtime.hpp"
#include <stdint.h>

// KNX024: SOFTWARE-ONLY reference adapter for PROPOSED AppVersion3 KOs.
//
// The existing ETS AppVersion2 has ONLY KO1..35. No live GroupObject or
// KNX interface is wired to this class. Object numbers are trusted local
// descriptors for an eventual ETS product, NOT group-address wire numbers.
// The bus itself does NOT advertise a DPT: expected DPT must be bound in
// ETS/GA configuration. Never take raw legacy DPT5.004 KO17..24 as 5.001.
//
// On Arduino this class can compute in-memory software targets, but the
// KNX023 runtime compile fence prevents any motor arming and all GPIO I/O.
namespace Knx024
{
constexpr uint16_t FirstRoomObject = 36;
constexpr uint16_t LastRoomObject = 67;
constexpr uint8_t ObjectsPerZone = 4;

enum class Dpt : uint8_t
{
    Unknown,
    Temperature9001,
    Scaling5001,
    LegacyPercent5004
};

enum class FrameKind : uint8_t
{
    GroupValueWrite,
    GroupValueResponse,
    GroupValueRead
};

enum class Status : uint8_t
{
    Accepted,
    IgnoredUnconfigured,
    IgnoredNonWrite,
    IgnoredNotReceiveObject,
    IgnoredWrongMode,
    InvalidatedTypeMismatch,
    InvalidatedMalformedPayload,
    InvalidatedTemperature,
    DisarmedConfigurationChanged
};

// bytes are the APPLICATION payload only (no cEMI/APDU headers).
// A future hardware/KNX adapter must validate telegram context and GA/DPT
// binding before presenting this trusted descriptor.
struct Frame
{
    uint16_t objectNumber = 0;
    Dpt declaredDpt = Dpt::Unknown;
    FrameKind kind = FrameKind::GroupValueWrite;
    const uint8_t* payload = nullptr;
    uint8_t payloadLength = 0;
};

struct ProposedOutput
{
    uint16_t objectNumber = 0;
    Dpt declaredDpt = Dpt::Scaling5001;
    uint8_t payload = 0;
};

struct Counters
{
    uint32_t accepted = 0;
    uint32_t rejected = 0;
    uint32_t ignored = 0;
    uint32_t configurationFences = 0;
};

enum class InputKind : uint8_t
{
    Setpoint,
    RoomActual,
    DirectDemand,
    RequestedOutput
};

inline uint16_t objectFor(uint8_t zeroBasedZone, InputKind kind)
{
    return static_cast<uint16_t>(
        FirstRoomObject + static_cast<uint16_t>(zeroBasedZone) *
        ObjectsPerZone + static_cast<uint8_t>(kind));
}

inline bool receiveDescriptor(uint16_t ko, uint8_t& zone,
                              InputKind& kind, Dpt& expectedDpt)
{
    if (ko < FirstRoomObject || ko > LastRoomObject)
        return false;
    const uint16_t index = ko - FirstRoomObject;
    const uint8_t offset = static_cast<uint8_t>(index % ObjectsPerZone);
    if (offset == 3)
        return false; // requested-output KO is TX ONLY
    zone = static_cast<uint8_t>(index / ObjectsPerZone);
    kind = static_cast<InputKind>(offset);
    expectedDpt = offset == 2 ? Dpt::Scaling5001 : Dpt::Temperature9001;
    return zone < HeatingZone::ZoneCount;
}

// KNX DPT9.001: 2-byte big-endian S EEEE MMMMMMMMMMM,
// value in 0.01 deg C = signed M * (2 ^ E).
// 0x7FFF is the KNX-specification invalid sentinel for ALL DPT9.xxx.
// Reject values beyond int16 centi-degree, then apply domain-specific
// setpoint/room-air limits; DO NOT silently clamp bad sensor telegrams.
inline bool decodeTemperature(const uint8_t* bytes, uint8_t length,
                              int16_t& centiC)
{
    if (!bytes || length != 2)
        return false;
    const uint16_t raw = static_cast<uint16_t>(
        (static_cast<uint16_t>(bytes[0]) << 8) | bytes[1]);
    if (raw == 0x7FFF)
        return false;
    const int32_t mantissa = (raw & 0x8000U) ?
        static_cast<int32_t>(raw & 0x07FFU) - 2048L :
        static_cast<int32_t>(raw & 0x07FFU);
    const uint8_t exponent = static_cast<uint8_t>((raw >> 11) & 0x0FU);
    const int32_t scaled = mantissa * static_cast<int32_t>(1UL << exponent);
    if (scaled < -32768L || scaled > 32767L)
        return false;
    centiC = static_cast<int16_t>(scaled);
    return true;
}

class Adapter
{
public:
    void reset(RoomControlRuntime::Pipeline& pipeline, uint32_t nowMs)
    {
        configured_ = false;
        haveTick_ = false;
        stats_ = {};
        pipeline.reset(nowMs);
    }

    // This is a PROPOSED P22..39 configuration input from a TRUSTED
    // software test, NOT reading ETS program memory / live bus data.
    // Changing ANY zone mode/assignment or timeout drops ALL prior RX
    // records. Reinitialization never auto-arms the KNX023 motor queue.
    bool configure(RoomControlRuntime::Pipeline& pipeline,
                   const HeatingZone::Settings& settings, uint32_t nowMs)
    {
        const bool valid =
            HeatingZone::validate(settings) == HeatingZone::ConfigError::None;
        pipeline.settings() = valid ? settings : HeatingZone::Settings{};
        pipeline.inputs() = {};
        haveTick_ = false;
        configured_ = valid;
        lastSettings_ = pipeline.settings();
        ++stats_.configurationFences;
        pipeline.tick(nowMs); // establish PI and zone epoch, synthetic only
        lastTickMs_ = nowMs;
        return valid;
    }

    // No direct bus access. The caller MUST use only the immutable proposed
    // KO descriptors and expected DPTs defined in the KNX008 JSON contract.
    Status receive(RoomControlRuntime::Pipeline& pipeline,
                   const Frame& frame, uint32_t nowMs)
    {
        if (configurationDrift(pipeline))
        {
            invalidateConfiguration(pipeline, nowMs);
            return Status::DisarmedConfigurationChanged;
        }
        if (!configured_)
            return ignored(Status::IgnoredUnconfigured);
        if (frame.kind != FrameKind::GroupValueWrite)
            return ignored(Status::IgnoredNonWrite);

        uint8_t zone = 0;
        InputKind kind = InputKind::Setpoint;
        Dpt expected = Dpt::Unknown;
        if (!receiveDescriptor(frame.objectNumber, zone, kind, expected))
            return ignored(Status::IgnoredNotReceiveObject);

        const HeatingZone::Mode mode = pipeline.settings().modes[zone];
        if ((kind == InputKind::DirectDemand &&
             mode != HeatingZone::Mode::DirectPercent) ||
            (kind != InputKind::DirectDemand &&
             mode != HeatingZone::Mode::RoomTemperature))
            return ignored(Status::IgnoredWrongMode);

        if (frame.declaredDpt != expected)
        {
            clearValue(pipeline, zone, kind);
            return rejected(Status::InvalidatedTypeMismatch);
        }

        if (!frame.payload ||
            frame.payloadLength != (kind == InputKind::DirectDemand ? 1 : 2))
        {
            clearValue(pipeline, zone, kind);
            return rejected(Status::InvalidatedMalformedPayload);
        }

        HeatingZone::ZoneInput& input = pipeline.inputs().zones[zone];
        if (kind == InputKind::DirectDemand)
        {
            input.directDpt5001Raw = {frame.payload[0], nowMs, true};
        }
        else
        {
            int16_t centiC = 0;
            if (!decodeTemperature(frame.payload, frame.payloadLength, centiC) ||
                (kind == InputKind::Setpoint &&
                 !HeatingZone::validRoomSetpoint(centiC)) ||
                (kind == InputKind::RoomActual &&
                 !HeatingZone::validRoomActual(centiC)))
            {
                clearValue(pipeline, zone, kind);
                return rejected(Status::InvalidatedTemperature);
            }
            if (kind == InputKind::Setpoint)
                input.setpointCentiC = {centiC, nowMs, true};
            else
                input.roomActualCentiC = {centiC, nowMs, true};
        }
        haveTick_ = false;
        ++stats_.accepted;
        return Status::Accepted;
    }

    // Safe RAM-only handoff for the existing 100ms firmware software loop.
    // A client mutating Pipeline.settings() without configure() triggers
    // an immediate global input fence. No cached old mode/zone is reused.
    void tick(RoomControlRuntime::Pipeline& pipeline, uint32_t nowMs)
    {
        if (configurationDrift(pipeline))
        {
            invalidateConfiguration(pipeline, nowMs);
            return;
        }
        pipeline.tick(nowMs);
        lastTickMs_ = nowMs;
        haveTick_ = true;
    }

    // Encode PROPOSED TX KO39,43,...67 for offline-test comparison ONLY.
    // This method NEVER calls GroupObject.value(), Serial or any bus API.
    // The output is valid only at the exact last software tick timestamp
    // and only for still-fresh, explicitly configured zone inputs.
    bool requestedOutput(const RoomControlRuntime::Pipeline& pipeline,
                         uint8_t zeroBasedZone, uint32_t nowMs,
                         ProposedOutput& out) const
    {
        if (!configured_ || !haveTick_ || lastTickMs_ != nowMs ||
            configurationDrift(pipeline) ||
            zeroBasedZone >= HeatingZone::ZoneCount)
            return false;

        const HeatingZone::Targets& targets = pipeline.snapshot().targets;
        if (!targets.configurationValid ||
            !(targets.activeZoneMask &
              static_cast<uint8_t>(1U << zeroBasedZone)))
            return false;

        const HeatingZone::Settings& cfg = pipeline.settings();
        const HeatingZone::ZoneInput& in = pipeline.inputs().zones[zeroBasedZone];
        uint16_t permille = 0;
        if (cfg.modes[zeroBasedZone] == HeatingZone::Mode::DirectPercent)
        {
            if (!HeatingZone::fresh(
                    in.directDpt5001Raw, nowMs,
                    static_cast<uint32_t>(cfg.directTimeoutSeconds) * 1000UL))
                return false;
            permille = HeatingZone::rawScalingToPermille(
                in.directDpt5001Raw.value);
        }
        else if (cfg.modes[zeroBasedZone] ==
                 HeatingZone::Mode::RoomTemperature)
        {
            const uint32_t timeout =
                static_cast<uint32_t>(cfg.roomTimeoutSeconds) * 1000UL;
            if (!HeatingZone::fresh(in.setpointCentiC, nowMs, timeout) ||
                !HeatingZone::fresh(in.roomActualCentiC, nowMs, timeout) ||
                !HeatingZone::fresh(
                    in.regulatorOutputPermille, nowMs, timeout) ||
                !HeatingZone::validRoomSetpoint(in.setpointCentiC.value) ||
                !HeatingZone::validRoomActual(in.roomActualCentiC.value) ||
                in.regulatorOutputPermille.value > HeatingZone::MaxPermille)
                return false;
            permille = in.regulatorOutputPermille.value;
        }
        else
            return false;

        out = {objectFor(zeroBasedZone, InputKind::RequestedOutput),
               Dpt::Scaling5001,
               HeatingZone::permilleToRawScaling(permille)};
        return true;
    }

    bool configured() const
    {
        return configured_;
    }

    const Counters& counters() const
    {
        return stats_;
    }

private:
    static void clearValue(RoomControlRuntime::Pipeline& pipeline,
                           uint8_t zone, InputKind kind)
    {
        HeatingZone::ZoneInput& in = pipeline.inputs().zones[zone];
        if (kind == InputKind::Setpoint)
            in.setpointCentiC = {};
        else if (kind == InputKind::RoomActual)
            in.roomActualCentiC = {};
        else if (kind == InputKind::DirectDemand)
            in.directDpt5001Raw = {};
    }

    bool configurationDrift(const RoomControlRuntime::Pipeline& pipeline) const
    {
        return configured_ &&
               !RoomPi::sameSettings(pipeline.settings(), lastSettings_);
    }

    void invalidateConfiguration(RoomControlRuntime::Pipeline& pipeline,
                                 uint32_t nowMs)
    {
        pipeline.settings() = {};
        pipeline.inputs() = {};
        configured_ = false;
        haveTick_ = false;
        ++stats_.configurationFences;
        pipeline.tick(nowMs); // native queue issues synthetic stop if running
    }

    Status ignored(Status s)
    {
        ++stats_.ignored;
        return s;
    }

    Status rejected(Status s)
    {
        haveTick_ = false;
        ++stats_.rejected;
        return s;
    }

    bool configured_ = false;
    bool haveTick_ = false;
    HeatingZone::Settings lastSettings_ = {};
    uint32_t lastTickMs_ = 0;
    Counters stats_ = {};
};

static_assert(LastRoomObject ==
                  FirstRoomObject +
                  ObjectsPerZone * HeatingZone::ZoneCount - 1,
              "Proposed KNX008 room objects must end at KO67");
} // namespace Knx024

#endif // OPENKNX_KNX024_ROOM_DPT_ADAPTER_HPP
