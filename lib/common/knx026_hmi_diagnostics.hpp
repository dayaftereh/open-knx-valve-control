#ifndef OPENKNX_KNX026_HMI_DIAGNOSTICS_HPP
#define OPENKNX_KNX026_HMI_DIAGNOSTICS_HPP

#include "knx025_fault_supervisor.hpp"
#include "temperature_protocol.hpp"
#include <stdint.h>

// KNX026: read-only fixed-size presentation state. No GPIO, KNX, actuator,
// encoder interrupt, display driver or fault acknowledgement can be called.
// A software target is NEVER evidence of a physically referenced motor.
namespace Knx026
{
enum class Quality : uint8_t { Unknown, Fresh, Stale, Invalid };
enum class LinkState : uint8_t { Unknown, Online, Offline };
enum class Page : uint8_t { Overview, Water, Zones, Motors, Links, Faults };
constexpr uint8_t PageCount = 6;

struct Reading
{
    int16_t centiC = 0;
    uint32_t ageSeconds = 0;
    uint8_t fault = 0;
    Quality quality = Quality::Unknown;
};
struct TimedRoomReading
{
    Reading value{};
};
struct Zone
{
    HeatingZone::Mode mode = HeatingZone::Mode::Disabled;
    uint8_t motorMask = 0;
    Reading setpoint{};
    Reading actual{};
    bool directFresh = false;
    uint16_t directPermille = 0;
    bool piOutputValid = false;
    uint16_t piOutputPermille = 0;
    uint16_t requestedPermille = 0;
    bool requestedValid = false;
};
struct Motor
{
    uint8_t zoneId = 0;
    uint16_t requestedPermille = 0;
    bool requestedValid = false;
    // On actual hardware this must stay Unknown until separately certified.
    Quality physicalPositionQuality = Quality::Unknown;
    // Synthetic model only: not derived from physical movement.
    bool virtualPositionValid = false;
    uint16_t virtualPositionPermille = 0;
    bool virtualReferenced = false;
};
struct WaterInput
{
    bool observed = false;
    bool online = false;
    // Prepared by source adapter from channelValid() / ageSeconds().
    Reading channels[TemperatureProtocol::Channels] = {};
};
struct Snapshot
{
    uint32_t observedAtMs = 0;
    Reading water[TemperatureProtocol::Channels] = {};
    Zone zones[HeatingZone::ZoneCount] = {};
    Motor motors[HeatingZone::MotorCount] = {};
    Knx025::Diagnostics fault{};
    LinkState roomKnx = LinkState::Unknown;
    LinkState manifoldUart = LinkState::Unknown;
    bool hardwareDriveBlocked = true;
    bool actualPhysicalAllOffProven = false;
    bool actualMotorReferenceProven = false;
};

inline LinkState knownLink(bool monitored, bool online)
{
    return !monitored ? LinkState::Unknown :
           online ? LinkState::Online : LinkState::Offline;
}
inline Reading roomValue(const HeatingZone::TimedValue<int16_t>& src,
                         uint32_t nowMs, uint32_t ttl,
                         bool isSetpoint)
{
    Reading out{};
    if (!src.valid) return out;
    out.centiC = src.value;
    out.ageSeconds = static_cast<uint32_t>(nowMs - src.receivedAtMs) / 1000UL;
    if (!(isSetpoint ? HeatingZone::validRoomSetpoint(src.value) :
                       HeatingZone::validRoomActual(src.value)))
        out.quality = Quality::Invalid;
    else
        out.quality = HeatingZone::fresh(src, nowMs, ttl) ?
            Quality::Fresh : Quality::Stale;
    return out;
}
inline Snapshot capture(const RoomControlRuntime::Pipeline& runtime,
                        const Knx025::Diagnostics& fault,
                        const WaterInput& water, uint32_t nowMs)
{
    Snapshot result{};
    result.observedAtMs = nowMs;
    result.fault = fault;
    result.roomKnx = knownLink(fault.roomTransportMonitored,
                               fault.roomTransportOnline);
    result.manifoldUart = knownLink(water.observed, water.online);
    for (uint8_t i = 0; i < TemperatureProtocol::Channels; ++i)
    {
        // Never display last-known water as fresh when UART is offline.
        if (water.observed)
        {
            result.water[i] = water.channels[i];
            if (!water.online && result.water[i].quality == Quality::Fresh)
                result.water[i].quality = Quality::Stale;
        }
    }

    const auto& cfg = runtime.settings();
    const auto& in = runtime.inputs();
    const auto state = runtime.snapshot();
    const uint32_t roomTtl = static_cast<uint32_t>(cfg.roomTimeoutSeconds) * 1000UL;
    const uint32_t directTtl = static_cast<uint32_t>(cfg.directTimeoutSeconds) * 1000UL;
    for (uint8_t z = 0; z < HeatingZone::ZoneCount; ++z)
    {
        Zone& dst = result.zones[z];
        dst.mode = cfg.modes[z];
        dst.setpoint = roomValue(in.zones[z].setpointCentiC, nowMs, roomTtl, true);
        dst.actual = roomValue(in.zones[z].roomActualCentiC, nowMs, roomTtl, false);
        const auto& direct = in.zones[z].directDpt5001Raw;
        dst.directFresh = HeatingZone::fresh(direct, nowMs, directTtl);
        if (dst.directFresh)
            dst.directPermille = HeatingZone::rawScalingToPermille(direct.value);
        const auto pi = runtime.zoneDiagnostic(z);
        dst.piOutputValid = pi.outputValid &&
            cfg.modes[z] == HeatingZone::Mode::RoomTemperature &&
            fault.phase != Knx025::Phase::FaultLatched;
        if (dst.piOutputValid) dst.piOutputPermille = pi.outputPermille;
    }
    for (uint8_t m = 0; m < HeatingZone::MotorCount; ++m)
    {
        Motor& dst = result.motors[m];
        const uint8_t zoneId = cfg.motorZone[m];
        if (zoneId >= 1 && zoneId <= HeatingZone::ZoneCount)
        {
            dst.zoneId = zoneId;
            result.zones[zoneId - 1].motorMask |= static_cast<uint8_t>(1U << m);
        }
        // Faulted software may retain an old target in RAM: quarantine for UI.
        if (fault.phase != Knx025::Phase::FaultLatched &&
            state.targets.motors[m].eligible &&
            state.targets.motors[m].permille <= HeatingZone::MaxPermille)
        {
            dst.requestedValid = true;
            dst.requestedPermille = state.targets.motors[m].permille;
            if (dst.zoneId)
            {
                Zone& z = result.zones[dst.zoneId - 1];
                z.requestedValid = true;
                z.requestedPermille = dst.requestedPermille;
            }
        }
#if !defined(ARDUINO)
        const auto& virtualEvidence = runtime.nativePosition(m);
        if (virtualEvidence.valid &&
            virtualEvidence.estimatedPermille <= HeatingZone::MaxPermille)
        {
            dst.virtualPositionValid = true;
            dst.virtualPositionPermille = virtualEvidence.estimatedPermille;
            dst.virtualReferenced = virtualEvidence.referenced;
        }
#endif
    }
    // Strictly no model flag can certify physical position or output isolation.
    result.hardwareDriveBlocked = true;
    result.actualPhysicalAllOffProven = false;
    result.actualMotorReferenceProven = false;
    return result;
}

// Read-only navigation. The caller may feed simulated encoder detents/button.
// No action codes for motor motion or fault recovery exist.
struct Menu
{
    Page page = Page::Overview;
    uint8_t index = 0;
    bool detail = false;
    void rotate(int8_t detents)
    {
        const uint8_t max = detail ?
            (page == Page::Water ? TemperatureProtocol::Channels :
             page == Page::Zones ? HeatingZone::ZoneCount :
             page == Page::Motors ? HeatingZone::MotorCount : 1U)
            : PageCount;
        if (max == 0) return;
        int16_t position = static_cast<int16_t>(detail ? index :
                                                 static_cast<uint8_t>(page));
        position += detents;
        while (position < 0) position += max;
        while (position >= max) position -= max;
        if (detail) index = static_cast<uint8_t>(position);
        else page = static_cast<Page>(position);
    }
    void press()
    {
        if (detail) { detail = false; index = 0; }
        else { detail = true; index = 0; }
    }
};
static_assert(HeatingZone::ZoneCount == 8 &&
              HeatingZone::MotorCount == 8 &&
              TemperatureProtocol::Channels == 9,
              "KNX026 fixed-size UI schema requires 8 zones / 8 motors / 9 water probes");
}
#endif
