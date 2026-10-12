#ifndef OPENKNX_KNX025_FAULT_SUPERVISOR_HPP
#define OPENKNX_KNX025_FAULT_SUPERVISOR_HPP

#include "knx024_room_dpt_adapter.hpp"
#include <stdint.h>

// KNX025: software-only fault observations and safe recovery contract.
//
// The only possible native "actuator" is KNX021 VirtualMotor, never a pin.
// ARDUINO firmware still has KNX023's permanent compile-time motor hardlock.
// In particular, a native AllOff ACK, operatorAck=true, or status.ok == true
// does NOT constitute electrically verified isolation. No network, I/O,
// watchdog peripheral, KNX GroupObject or physical motor is used here.
namespace Knx025
{
constexpr uint32_t MaxSoftwareTickGapMs = 2000U;

enum class Phase : uint8_t
{
    Unconfigured,
    WaitingForFreshInputs,
    HealthySoftwareInputs,
    FaultLatched
};

enum class Fault : uint8_t
{
    None,
    InvalidConfiguration,
    InvalidRoomTelegram,
    RoomSourceExpired,
    DirectDemandExpired,
    RoomTransportLost,
    SoftwareLoopStalled,
    SoftwareConfigurationChanged,
    MotorQueueFault,
    MockBackendProtocolFault,
    OperatorEmergencyStop
};

struct Signals
{
    // A trusted room-transport indicator would come from a FUTURE verified
    // KNX/IP + ETS input gateway, never from the existence of T0..T8 values
    // or from 'knx.configured()' alone.
    bool roomTransportMonitored = false;
    bool roomTransportOnline = false;

    // Manifold 1-Wire T0..T8 is TELEMETRY, NOT external room-air actual.
    // A loss may warn the user but never becomes a room temperature value.
    bool manifoldTelemetryObserved = false;
    bool manifoldTelemetryOnline = false;
    bool manualEmergencyStop = false;
};

struct Diagnostics
{
    Phase phase = Phase::Unconfigured;
    Fault firstFault = Fault::None;
    uint8_t firstFaultZone = 0; // 1-based; zero denotes global failure
    uint32_t firstFaultAtMs = 0;
    uint32_t lastSoftwareTickMs = 0;
    uint32_t softwareTickCount = 0;
    uint32_t faultEpochCount = 0;
    uint32_t recoveryCount = 0;
    uint32_t deniedRecoveryCount = 0;
    uint32_t ignoredDuringFaultCount = 0;
    uint8_t requiredZoneMask = 0;
    uint8_t freshZoneMask = 0;
    uint8_t everReadyZoneMask = 0;
    bool manifoldTelemetryWarning = false;
    bool roomTransportOnline = false;
    bool roomTransportMonitored = false;
    MotorQueueSim::State simulatedQueueState = MotorQueueSim::State::Disarmed;
    MotorQueueSim::FaultReason simulatedQueueFault =
        MotorQueueSim::FaultReason::None;
    uint8_t simulatedMotorLeaseMask = 0;
    bool physicalOutputsVerifiedOff = false; // always FALSE in KNX025
};

class Supervisor
{
public:
    // Only reset the fault latch and diagnostics at actual process startup.
    // This method does NOT and cannot prove that a power-stage is off.
    void reset(uint32_t nowMs)
    {
        d_ = {};
        d_.lastSoftwareTickMs = nowMs;
        haveTick_ = true;
        configured_ = false;
        expectedSettings_ = {};
        lastSignals_ = {};
        d_.phase = Phase::Unconfigured;
    }

    // Called during actual RP2040 software setup (no live ETS KOs). The
    // adapter and mock queue are rebooted DISARMED, with zero input history.
    void boot(RoomControlRuntime::Pipeline& pipeline,
              Knx024::Adapter& adapter, uint32_t nowMs)
    {
        adapter.reset(pipeline, nowMs);
        reset(nowMs);
        updateQueueDiagnostics(pipeline);
    }

    // Explicitly configured proposed ETS P22..P39 inputs. No EEPROM/KNX
    // write. Reassignments never inherit an old PI/demand/data epoch.
    bool configure(RoomControlRuntime::Pipeline& pipeline,
                   Knx024::Adapter& adapter,
                   const HeatingZone::Settings& config, uint32_t nowMs)
    {
        if (d_.phase == Phase::FaultLatched)
            return false;
        if (pipeline.snapshot().queue.leaseMask != 0U ||
            nativeMockOccupancy(pipeline) != 0U)
        {
            latch(Fault::SoftwareConfigurationChanged, 0, nowMs);
            quarantine(pipeline);
            return false;
        }
        if (HeatingZone::validate(config) !=
            HeatingZone::ConfigError::None)
        {
            latch(Fault::InvalidConfiguration, 0, nowMs);
            quarantine(pipeline);
            return false;
        }
        if (!adapter.configure(pipeline, config, nowMs))
        {
            latch(Fault::InvalidConfiguration, 0, nowMs);
            quarantine(pipeline);
            return false;
        }
        configured_ = true;
        expectedSettings_ = config;
        d_.everReadyZoneMask = 0;
        d_.freshZoneMask = 0;
        d_.requiredZoneMask = assignedZoneMask(config);
        d_.phase = Phase::WaitingForFreshInputs;
        updateQueueDiagnostics(pipeline);
        return true;
    }

    // Handles purely synthetic KNX024 KO descriptors. Invalid ACTIVE
    // telegrams latch and invalidate the entire software control epoch.
    // Unknown KO, group-read, non-active mode are ignored by KNX024.
    Knx024::Status receive(RoomControlRuntime::Pipeline& pipeline,
                          Knx024::Adapter& adapter,
                          const Knx024::Frame& frame, uint32_t nowMs)
    {
        if (d_.phase == Phase::FaultLatched)
        {
            ++d_.ignoredDuringFaultCount;
            return Knx024::Status::IgnoredUnconfigured;
        }
        const Knx024::Status result = adapter.receive(pipeline, frame, nowMs);
        switch (result)
        {
            case Knx024::Status::InvalidatedTypeMismatch:
            case Knx024::Status::InvalidatedMalformedPayload:
            case Knx024::Status::InvalidatedTemperature:
            {
                uint8_t zone = 0;
                Knx024::InputKind kind = Knx024::InputKind::Setpoint;
                Knx024::Dpt expected = Knx024::Dpt::Unknown;
                if (!Knx024::receiveDescriptor(
                    frame.objectNumber, zone, kind, expected))
                    zone = 0xFF;
                latch(Fault::InvalidRoomTelegram,
                      zone == 0xFF ? 0 : static_cast<uint8_t>(zone + 1),
                      nowMs);
                quarantine(pipeline);
                break;
            }
            case Knx024::Status::DisarmedConfigurationChanged:
                latch(Fault::SoftwareConfigurationChanged, 0, nowMs);
                quarantine(pipeline);
                break;
            default:
                break;
        }
        return result;
    }

    // IMPORTANT: This is the active pre-tick gate used exclusively by
    // native lab simulations until a real KNX V3 gateway is verified.
    // Detect faults BEFORE KNX023 runs the synthetic motor scheduler.
    // Even after latching it continues native ticks ONLY so the existing
    // ACK-token STOP handshake can complete; lease is never forgotten.
    void softwareTick(RoomControlRuntime::Pipeline& pipeline,
                      Knx024::Adapter& adapter,
                      const Signals& signals, uint32_t nowMs)
    {
        preflight(pipeline, adapter.configured(), signals, nowMs);
        if (d_.phase == Phase::FaultLatched)
            quarantine(pipeline);

        adapter.tick(pipeline, nowMs);

        if (d_.phase != Phase::FaultLatched &&
            !adapter.configured() && configured_)
            latch(Fault::SoftwareConfigurationChanged, 0, nowMs);

        inspectQueue(pipeline, nowMs);
        if (d_.phase == Phase::FaultLatched)
            quarantine(pipeline);
        recordTick(pipeline, nowMs);
    }

    // Production RP2040 uses ONLY this passive diagnostic sampler: current
    // AppV2 lacks the proposed KNX024 receive KOs. This path never
    // configures, arms, or modifies the pipeline. A real motor controller
    // MUST instead use a pre-tick safety gate plus independent HW interlock.
    void observeFirmware(const RoomControlRuntime::Pipeline& pipeline,
                         const Signals& signals, uint32_t nowMs)
    {
        if (haveTick_ && static_cast<uint32_t>(
                nowMs - d_.lastSoftwareTickMs) > MaxSoftwareTickGapMs)
            latch(Fault::SoftwareLoopStalled, 0, nowMs);
        lastSignals_ = signals;
        updateTelemetryWarning(signals);
        if (signals.manualEmergencyStop)
            latch(Fault::OperatorEmergencyStop, 0, nowMs);
        inspectQueue(pipeline, nowMs);
        recordTick(pipeline, nowMs);
    }

    // A purely software diagnostic ACK. It does not establish or clear
    // electrical motor safety. Never reset active mock motor state or a
    // held STOP-token: no ACK => lease stays occupied and recovery denied.
    // Recovery REQUIRES fresh config AND new telegrams; never auto rearm.
    bool acknowledgeAndRequireFresh(RoomControlRuntime::Pipeline& pipeline,
                                   Knx024::Adapter& adapter,
                                   uint32_t nowMs,
                                   bool operatorAcknowledgement)
    {
        const MotorQueueSim::Status q = pipeline.snapshot().queue;
        const bool safeQueueState =
            q.state == MotorQueueSim::State::Disarmed ||
            q.state == MotorQueueSim::State::FaultLatched ||
            q.state == MotorQueueSim::State::Idle;
        const bool safeMock =
            nativeMockOccupancy(pipeline) == 0U &&
            nativeMockProtocolViolations(pipeline) == 0U;
        const bool transportRecovered =
            !lastSignals_.roomTransportMonitored ||
            lastSignals_.roomTransportOnline;
        if (d_.phase != Phase::FaultLatched ||
            !operatorAcknowledgement || lastSignals_.manualEmergencyStop ||
            !safeQueueState || q.leaseMask != 0U ||
            !safeMock || !transportRecovered)
        {
            ++d_.deniedRecoveryCount;
            return false;
        }

        const uint32_t faults = d_.faultEpochCount;
        const uint32_t recoveries = d_.recoveryCount + 1U;
        const uint32_t denied = d_.deniedRecoveryCount;
        const uint32_t ignored = d_.ignoredDuringFaultCount;
        boot(pipeline, adapter, nowMs); // only after synthetic AllOff + no lease
        d_.faultEpochCount = faults;
        d_.recoveryCount = recoveries;
        d_.deniedRecoveryCount = denied;
        d_.ignoredDuringFaultCount = ignored;
        // This ONLY resets RAM; it DOES NOT prove real electrical safety.
        return true;
    }

    Diagnostics diagnostics() const
    {
        return d_;
    }

private:
    static uint8_t nativeMockOccupancy(
        const RoomControlRuntime::Pipeline& pipeline)
    {
#if defined(ARDUINO)
        (void)pipeline;
        return 0; // ARDUINO motor backend is compiled OUT, not HW proof
#else
        return pipeline.nativeBackendStatus().abstractOccupiedMask;
#endif
    }

    static uint32_t nativeMockProtocolViolations(
        const RoomControlRuntime::Pipeline& pipeline)
    {
#if defined(ARDUINO)
        (void)pipeline;
        return 0;
#else
        return pipeline.nativeBackendStatus().protocolViolations;
#endif
    }

    static uint8_t assignedZoneMask(
        const HeatingZone::Settings& config)
    {
        uint8_t result = 0;
        for (uint8_t m = 0; m < HeatingZone::MotorCount; ++m)
        {
            const uint8_t id = config.motorZone[m];
            if (id >= 1 && id <= HeatingZone::ZoneCount &&
                config.modes[id - 1] != HeatingZone::Mode::Disabled)
                result |= static_cast<uint8_t>(1U << (id - 1U));
        }
        return result;
    }

    static bool zoneReady(const HeatingZone::Settings& cfg,
                          const HeatingZone::ZoneInput& in,
                          uint8_t zone, uint32_t nowMs)
    {
        switch (cfg.modes[zone])
        {
            case HeatingZone::Mode::DirectPercent:
                return HeatingZone::fresh(
                    in.directDpt5001Raw, nowMs,
                    static_cast<uint32_t>(cfg.directTimeoutSeconds) * 1000UL);
            case HeatingZone::Mode::RoomTemperature:
            {
                const uint32_t ttl =
                    static_cast<uint32_t>(cfg.roomTimeoutSeconds) * 1000UL;
                return HeatingZone::fresh(in.setpointCentiC, nowMs, ttl) &&
                       HeatingZone::fresh(in.roomActualCentiC, nowMs, ttl) &&
                       HeatingZone::validRoomSetpoint(
                           in.setpointCentiC.value) &&
                       HeatingZone::validRoomActual(
                           in.roomActualCentiC.value);
            }
            default:
                return false;
        }
    }

    void preflight(const RoomControlRuntime::Pipeline& pipeline,
                   bool adapterConfigured, const Signals& sig,
                   uint32_t nowMs)
    {
        if (haveTick_ && static_cast<uint32_t>(
                nowMs - d_.lastSoftwareTickMs) > MaxSoftwareTickGapMs)
            latch(Fault::SoftwareLoopStalled, 0, nowMs);

        updateTelemetryWarning(sig);
        lastSignals_ = sig;
        if (sig.manualEmergencyStop)
            latch(Fault::OperatorEmergencyStop, 0, nowMs);

        if (d_.phase == Phase::FaultLatched)
            return;
        if (configured_ && !adapterConfigured)
        {
            latch(Fault::SoftwareConfigurationChanged, 0, nowMs);
            return;
        }
        if (!configured_)
            return;

        // A KNOWN-OFFLINE source must never be able to start a new
        // synthetic trip, including on the VERY FIRST configured tick.
        // UNKNOWN is different: production AppV2 has no verified bus
        // health signal and must not invent one.
        if (sig.roomTransportMonitored && !sig.roomTransportOnline)
        {
            latch(Fault::RoomTransportLost, 0, nowMs);
            return;
        }

        const HeatingZone::Settings& cfg = pipeline.settings();
        if (HeatingZone::validate(cfg) != HeatingZone::ConfigError::None ||
            !RoomPi::sameSettings(cfg, expectedSettings_) ||
            assignedZoneMask(cfg) != d_.requiredZoneMask)
        {
            latch(Fault::SoftwareConfigurationChanged, 0, nowMs);
            return;
        }

        uint8_t currentReady = 0;
        for (uint8_t z = 0; z < HeatingZone::ZoneCount; ++z)
        {
            const uint8_t bit = static_cast<uint8_t>(1U << z);
            if ((d_.requiredZoneMask & bit) == 0)
                continue;
            if (zoneReady(cfg, pipeline.inputs().zones[z], z, nowMs))
                currentReady |= bit;
            else if ((d_.everReadyZoneMask & bit) != 0)
            {
                latch(cfg.modes[z] == HeatingZone::Mode::DirectPercent ?
                      Fault::DirectDemandExpired : Fault::RoomSourceExpired,
                      static_cast<uint8_t>(z + 1), nowMs);
                return;
            }
        }
        d_.freshZoneMask = currentReady;
        d_.everReadyZoneMask |= currentReady;
        d_.phase = d_.requiredZoneMask != 0 &&
                   currentReady == d_.requiredZoneMask ?
                   Phase::HealthySoftwareInputs : Phase::WaitingForFreshInputs;
    }

    void updateTelemetryWarning(const Signals& sig)
    {
        // Report only an explicitly observed offline condition, not the
        // normal boot before first ATtiny snapshot.
        d_.manifoldTelemetryWarning =
            sig.manifoldTelemetryObserved && !sig.manifoldTelemetryOnline;
        d_.roomTransportMonitored = sig.roomTransportMonitored;
        d_.roomTransportOnline =
            sig.roomTransportMonitored && sig.roomTransportOnline;
    }

    void quarantine(RoomControlRuntime::Pipeline& pipeline)
    {
        pipeline.inputs() = {};
        pipeline.cancelNativeSimulation();
        d_.freshZoneMask = 0;
        // DO NOT reset the native queue while a leased motor waits for
        // the matching AllOff ACK. STOP retransmissions still occur.
    }

    void inspectQueue(const RoomControlRuntime::Pipeline& pipeline,
                      uint32_t nowMs)
    {
        const RoomControlRuntime::Snapshot state = pipeline.snapshot();
        if (d_.phase != Phase::FaultLatched)
        {
            if (state.mockBackendProtocolError)
                latch(Fault::MockBackendProtocolFault, 0, nowMs);
            else if (state.queue.state == MotorQueueSim::State::FaultLatched ||
                     state.queue.stopAcknowledgementOverdue)
                latch(Fault::MotorQueueFault, 0, nowMs);
        }
        updateQueueDiagnostics(pipeline);
    }

    void updateQueueDiagnostics(const RoomControlRuntime::Pipeline& pipeline)
    {
        const RoomControlRuntime::Snapshot snap = pipeline.snapshot();
        d_.simulatedQueueState = snap.queue.state;
        d_.simulatedQueueFault = snap.queue.fault;
        d_.simulatedMotorLeaseMask = snap.queue.leaseMask;
        d_.physicalOutputsVerifiedOff = false;
    }

    void recordTick(const RoomControlRuntime::Pipeline& pipeline,
                    uint32_t nowMs)
    {
        ++d_.softwareTickCount;
        d_.lastSoftwareTickMs = nowMs;
        haveTick_ = true;
        updateQueueDiagnostics(pipeline);
    }

    void latch(Fault reason, uint8_t zone, uint32_t nowMs)
    {
        if (d_.phase == Phase::FaultLatched)
            return; // first fault cause MUST remain stable
        d_.phase = Phase::FaultLatched;
        d_.firstFault = reason;
        d_.firstFaultZone = zone;
        d_.firstFaultAtMs = nowMs;
        d_.freshZoneMask = 0;
        ++d_.faultEpochCount;
    }

    Diagnostics d_ = {};
    Signals lastSignals_ = {};
    bool configured_ = false;
    HeatingZone::Settings expectedSettings_ = {};
    bool haveTick_ = false;
};

} // namespace Knx025
#endif // OPENKNX_KNX025_FAULT_SUPERVISOR_HPP
