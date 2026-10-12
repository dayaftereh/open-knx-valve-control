#ifndef OPENKNX_ROOM_CONTROL_RUNTIME_HPP
#define OPENKNX_ROOM_CONTROL_RUNTIME_HPP

#include "room_pi_controller.hpp"
#include "heating_zone_model.hpp"
#include "motor_queue_simulator.hpp"
#if !defined(ARDUINO)
#include "virtual_motor_feedback.hpp"
#endif
#include <stdint.h>

// KNX023 – SOFTWARE-ONLY coordinator, never an actuator backend.
//
// On an actual Arduino/RP2040 firmware build, a hard compile-time fence
// removes the virtual motor backend and DISABLES all arm/evidence entry
// points. No possible firmware tick can produce a Start/Stop event, and
// this file knows no pin, bus, relay, PWM, motor-enable or KNX API.
//
// The native host path can intentionally drive a *virtual* feedback model
// to test PI -> KNX008 Targets -> KNX020 exclusive lease/ACK behavior.
// Native mock guard booleans MUST NEVER stand for measured electrical safety.
namespace RoomControlRuntime
{

struct Snapshot
{
    HeatingZone::Targets targets = {};
    MotorQueueSim::Status queue = {};
    MotorQueueSim::Event lastMockEvent = {};
    bool mockBackendProtocolError = false;
    uint32_t tickCount = 0;
    bool physicalOutputsConnected = false;
#if defined(ARDUINO)
    bool nativeSimulationAvailable = false;
#else
    bool nativeSimulationAvailable = true;
#endif
};

class Pipeline
{
public:
    Pipeline() = default;

    void reset(uint32_t nowMs)
    {
        // System reset ALWAYS discards old commands and starts DISARMED.
        // The program has no physical output line to toggle; a real
        // watchdog and independent All-off proof remain KNX004 work.
        settings_ = {};
        inputs_ = {};
        for (uint8_t z = 0; z < HeatingZone::ZoneCount; ++z)
            tuning_[z] = {};
        pi_.reset(nowMs);
        queue_.reset(nowMs);
#if !defined(ARDUINO)
        backend_.reset();
        guards_ = {};
#endif
        targets_ = {};
        lastEvent_ = {};
        mockProtocolError_ = false;
        ticks_ = 0;
    }

    HeatingZone::Settings& settings()
    {
        return settings_;
    }

    const HeatingZone::Settings& settings() const
    {
        return settings_;
    }

    HeatingZone::Inputs& inputs()
    {
        return inputs_;
    }

    const HeatingZone::Inputs& inputs() const
    {
        return inputs_;
    }

    RoomPi::Tuning& tuning(uint8_t index)
    {
        // Caller must check index < HeatingZone::ZoneCount.
        return tuning_[index];
    }

    const RoomPi::Diagnostic& zoneDiagnostic(uint8_t index) const
    {
        // Caller must check index < HeatingZone::ZoneCount.
        return pi_.diagnostic(index);
    }

    // A complete tick always works from the CURRENT, validity-checked
    // KNX008 inputs. It does not consume KNX objects in this slice:
    // legacy DPT5.004 motor values must NOT be treated as DPT5.001.
    void tick(uint32_t nowMs)
    {
        pi_.update(settings_, tuning_, inputs_, nowMs);
        targets_ = HeatingZone::resolve(settings_, inputs_, nowMs);

#if !defined(ARDUINO)
        // Only a desktop/native test binary can instantiate and use
        // synthetic motor events. No external GPIO/KNX sink is linked.
        const MotorQueueSim::Acknowledgement ack = backend_.poll(nowMs);
        lastEvent_ = queue_.step(nowMs, targets_, backend_.positions(),
                                  guards_, ack);
        if (!backend_.consume(lastEvent_, nowMs))
        {
            mockProtocolError_ = true;
            guards_ = {};
            queue_.cancelAll();
        }
#else
        // Firmware actively computes software-only PI/Targets. The queue
        // remains DISARMED forever and cannot be armed in this build.
        // No mock backend or synthetic acknowledgement is instantiated.
        lastEvent_ = {};
#endif
        ++ticks_;
    }

    // No production arm interface exists. With ARDUINO set this method
    // always fails even if a caller fabricates five "qualified" flags.
    bool armNativeSimulation(uint32_t nowMs,
                             const MotorQueueSim::Guards& mockGuards)
    {
#if defined(ARDUINO)
        (void)nowMs;
        (void)mockGuards;
        return false;
#else
        if (mockProtocolError_ || !mockGuards.qualified())
            return false;
        if (!backend_.independentlyAllOff())
            return false;
        if (!queue_.arm(nowMs, mockGuards,
                        backend_.independentlyAllOff()))
            return false;
        guards_ = mockGuards;
        return true;
#endif
    }

    bool injectNativePosition(uint8_t motor, uint16_t positionPermille,
                              uint32_t virtualFullStrokeMs,
                              uint32_t evidenceRevision)
    {
#if defined(ARDUINO)
        (void)motor;
        (void)positionPermille;
        (void)virtualFullStrokeMs;
        (void)evidenceRevision;
        return false;
#else
        return backend_.setEvidence(motor, positionPermille,
                                    virtualFullStrokeMs, evidenceRevision);
#endif
    }

    void cancelNativeSimulation()
    {
#if !defined(ARDUINO)
        queue_.cancelAll();
#endif
    }

#if !defined(ARDUINO)
    // Native-only stress/test access. Compiled OUT of actual controller.
    void setNativeBackendOptions(const VirtualMotor::Options& options)
    {
        backend_.setOptions(options);
    }

    VirtualMotor::Diagnostics nativeBackendStatus() const
    {
        return backend_.status();
    }

    const MotorQueueSim::PositionEvidence&
    nativePosition(uint8_t motor) const
    {
        return backend_.positions()[motor]; // native caller checks 0..7
    }

    bool clearNativeFault(const MotorQueueSim::Guards& newMockGuards)
    {
        if (mockProtocolError_ || !newMockGuards.qualified())
            return false;
        if (!queue_.clearFault(newMockGuards,
                               backend_.independentlyAllOff()))
            return false;
        guards_ = newMockGuards;
        return true;
    }
#endif

    Snapshot snapshot() const
    {
        Snapshot state{};
        state.targets = targets_;
        state.queue = queue_.status();
        state.lastMockEvent = lastEvent_;
        state.mockBackendProtocolError = mockProtocolError_;
        state.tickCount = ticks_;
        // Do not turn simulator flags into an actual hardware proof.
        state.physicalOutputsConnected = false;
        return state;
    }

private:
    HeatingZone::Settings settings_ = {};
    HeatingZone::Inputs inputs_ = {};
    RoomPi::Tuning tuning_[HeatingZone::ZoneCount] = {};
    RoomPi::Bank pi_ = {};
    MotorQueueSim::Queue queue_{};
#if !defined(ARDUINO)
    VirtualMotor::Backend backend_{};
    MotorQueueSim::Guards guards_ = {};
#endif
    HeatingZone::Targets targets_ = {};
    MotorQueueSim::Event lastEvent_ = {};
    bool mockProtocolError_ = false;
    uint32_t ticks_ = 0;
};

static_assert(HeatingZone::MotorCount == 8 &&
                  HeatingZone::ZoneCount == 8,
              "KNX023 requires exactly eight KNX008 zones and motors");

} // namespace RoomControlRuntime

#endif // OPENKNX_ROOM_CONTROL_RUNTIME_HPP
