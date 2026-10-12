#ifndef OPENKNX_MOTOR_QUEUE_SIMULATOR_HPP
#define OPENKNX_MOTOR_QUEUE_SIMULATOR_HPP

#include "heating_zone_model.hpp"
#include <stdint.h>

// KNX020 is strictly a PORTABLE SIMULATION CONTRACT, NOT a motor driver.
// A "Start" / "Stop" event has no physical side effect. Real H-bridge
// interlocks, independent safe-off and INA219 limits require KNX002-006.
namespace MotorQueueSim
{
constexpr uint8_t MotorCount = HeatingZone::MotorCount;
constexpr uint8_t NoMotor = 0xFF;

enum class State : uint8_t
{
    Disarmed,
    Idle,
    StartPending,
    Running,
    StopPending,
    FaultLatched
};

enum class Direction : uint8_t
{
    None,
    LogicalOpen,
    LogicalClose
};

enum class EventKind : uint8_t
{
    None,
    Start,
    Stop
};

enum class StopReason : uint8_t
{
    None,
    PlannedTravelTime,
    Cancelled,
    TargetInvalid,
    TargetChanged,
    ReferenceLost,
    MotorFault,
    SafetyLost,
    StartAckTimeout
};

enum class FaultReason : uint8_t
{
    None,
    SafetyLost,
    MotorFault,
    StartAckTimeout,
    StopAckTimeout
};

enum class AckKind : uint8_t
{
    None,
    Started,
    AllOff
};

struct Acknowledgement
{
    AckKind kind = AckKind::None;
    uint32_t token = 0;
    // An "AllOff" ACK must originate from an independent output-off proof
    // in future hardware, never inferred from the elapsed drive time.
    bool outputsConfirmedOff = false;
};

struct Guards
{
    // ALL are simulation inputs. Setting them true does NOT certify
    // physical safety, power, shunt, outputs or bus readiness.
    bool explicitTestPermit = false;
    bool boardAsBuiltQualified = false;
    bool supplyQualified = false;
    bool outputInterlockQualified = false;
    bool currentMonitoringQualified = false;
    bool emergencyStop = false;
    uint8_t motorFaultMask = 0;

    bool qualified() const
    {
        return explicitTestPermit && boardAsBuiltQualified &&
               supplyQualified && outputInterlockQualified &&
               currentMonitoringQualified && !emergencyStop;
    }
};

struct PositionEvidence
{
    bool valid = false;
    bool referenced = false;
    uint16_t estimatedPermille = 0;
    // Duration is SIMULATED and must be replaced by measured per-motor
    // calibration from KNX005/006 before any physical drive integration.
    uint32_t fullStrokeTimeMs = 0;
    // Increment only when a distinct trusted position assessment arrives.
    uint32_t revision = 0;
};

struct Config
{
    uint16_t minChangePermille = 20;
    uint32_t minFullStrokeMs = 5000;
    uint32_t maxFullStrokeMs = 180000;
    uint32_t maxSingleTravelMs = 120000;
    uint32_t startAckTimeoutMs = 1000;
    uint32_t stopAckTimeoutMs = 2000;
    uint32_t interMotorDeadtimeMs = 500;
};

inline bool validConfig(const Config& cfg)
{
    return cfg.minChangePermille >= 1 &&
           cfg.minChangePermille <= 100 &&
           cfg.minFullStrokeMs >= 1000 &&
           cfg.maxFullStrokeMs <= 600000 &&
           cfg.minFullStrokeMs <= cfg.maxFullStrokeMs &&
           cfg.maxSingleTravelMs >= 100 &&
           cfg.maxSingleTravelMs <= cfg.maxFullStrokeMs &&
           cfg.startAckTimeoutMs >= 100 &&
           cfg.startAckTimeoutMs <= 10000 &&
           cfg.stopAckTimeoutMs >= 100 &&
           cfg.stopAckTimeoutMs <= 10000 &&
           cfg.interMotorDeadtimeMs >= 100 &&
           cfg.interMotorDeadtimeMs <= 30000;
}

inline bool elapsed(uint32_t now, uint32_t before, uint32_t duration)
{
    return static_cast<uint32_t>(now - before) >= duration;
}

struct Event
{
    EventKind kind = EventKind::None;
    uint8_t motor = NoMotor;  // index 0..7, NOT a physical GPIO pin
    uint32_t token = 0;
    Direction direction = Direction::None;
    uint16_t targetPermille = 0;
    uint32_t plannedTravelMs = 0;
    StopReason stopReason = StopReason::None;
};

struct Status
{
    State state = State::Disarmed;
    FaultReason fault = FaultReason::None;
    uint8_t leasedMotor = NoMotor;
    uint8_t leaseMask = 0; // at most ONE bit, even before Start ACK
    uint8_t nextCandidate = 0;
    uint32_t activeToken = 0;
    uint32_t completedLeaseCount = 0; // Stop ACKs, not measured travel
    bool stopAcknowledgementOverdue = false;
    bool rearmRequired = true;
};

class Queue
{
public:
    explicit Queue(const Config& config = {}) : config_(config) {}

    void reset(uint32_t now)
    {
        // After reboot, hardware state cannot be inferred from RAM.
        // The simulator remains DISARMED until external ALL-OFF evidence.
        state_ = State::Disarmed;
        leasedMotor_ = NoMotor;
        fault_ = FaultReason::None;
        faultLatched_ = false;
        rearmRequired_ = true;
        stopOverdue_ = false;
        currentToken_ = 0;
        // Do not recycle tokens across software resets of the same
        // instance; late ACKs must never confirm a new lease.
        currentDirection_ = Direction::None;
        currentTarget_ = 0;
        currentZone_ = 0;
        currentTravelMs_ = 0;
        lastStopMs_ = now;
        startIssuedMs_ = now;
        startedMs_ = now;
        stopIssuedMs_ = now;
        lastStopReason_ = StopReason::None;
        nextCandidate_ = 0;
        completed_ = 0;
        haveStop_ = false;
        for (uint8_t i = 0; i < MotorCount; ++i)
        {
            awaitingRevision_[i] = false;
            dispatchedRevision_[i] = 0;
        }
    }

    bool arm(uint32_t now, const Guards& guards, bool independentlyAllOff)
    {
        if (state_ != State::Disarmed || faultLatched_ ||
            !validConfig(config_) || !guards.qualified() ||
            !independentlyAllOff)
            return false;
        state_ = State::Idle;
        rearmRequired_ = false;
        lastStopMs_ = now;
        haveStop_ = true; // initial cooldown also applies after boot
        return true;
    }

    // Fault clearing alone never arms or issues a Start.
    bool clearFault(const Guards& guards, bool independentlyAllOff)
    {
        if (state_ != State::FaultLatched || !guards.qualified() ||
            !independentlyAllOff)
            return false;
        state_ = State::Disarmed;
        faultLatched_ = false;
        fault_ = FaultReason::None;
        stopOverdue_ = false;
        rearmRequired_ = true;
        return true;
    }

    // Operator cancellation acts on the next tick; never releases the
    // leased motor before receiving its own matching stop acknowledgement.
    void cancelAll()
    {
        rearmRequired_ = true;
        if (state_ == State::Idle)
            state_ = State::Disarmed;
    }

    Status status() const
    {
        Status out{};
        out.state = state_;
        out.fault = fault_;
        out.leasedMotor = leasedMotor_;
        out.leaseMask = leasedMotor_ == NoMotor ?
            0 : static_cast<uint8_t>(1U << leasedMotor_);
        out.nextCandidate = nextCandidate_;
        out.activeToken = currentToken_;
        out.completedLeaseCount = completed_;
        out.stopAcknowledgementOverdue = stopOverdue_;
        out.rearmRequired = rearmRequired_;
        return out;
    }

    Event step(uint32_t now,
               const HeatingZone::Targets& targets,
               const PositionEvidence (&positions)[MotorCount],
               const Guards& guards,
               const Acknowledgement& ack = {})
    {
        if (state_ == State::FaultLatched ||
            state_ == State::Disarmed)
            return {};

        const bool globalSafe =
            validConfig(config_) && guards.qualified();
        if (state_ == State::Idle)
        {
            if (!globalSafe)
            {
                fault_ = FaultReason::SafetyLost;
                faultLatched_ = true;
                rearmRequired_ = true;
                state_ = State::FaultLatched;
                return {};
            }
            if (!targets.configurationValid)
            {
                rearmRequired_ = true;
                state_ = State::Disarmed;
                return {};
            }
            if (haveStop_ && !elapsed(now, lastStopMs_,
                                      config_.interMotorDeadtimeMs))
                return {};
            return selectAndStart(now, targets, positions, guards);
        }

        if (state_ == State::StopPending)
        {
            // A missing global qualification cannot turn a STOP ack into
            // an automatic new grant: it latches a fault first.
            if (!globalSafe && !faultLatched_)
                latchFault(FaultReason::SafetyLost);

            // Match tokens, AND require independently proven all-off.
            if (ack.kind == AckKind::AllOff &&
                ack.token == currentToken_ &&
                ack.outputsConfirmedOff)
            {
                const uint8_t justStopped = leasedMotor_;
                leasedMotor_ = NoMotor;
                currentDirection_ = Direction::None;
                currentToken_ = 0;
                ++completed_;
                nextCandidate_ = static_cast<uint8_t>(
                    (justStopped + 1U) % MotorCount);
                lastStopMs_ = now;
                haveStop_ = true;
                if (faultLatched_)
                    state_ = State::FaultLatched;
                else if (rearmRequired_)
                    state_ = State::Disarmed;
                else
                    state_ = State::Idle;
                return {}; // NEVER start another on an ACK step
            }
            if (!stopOverdue_ &&
                elapsed(now, stopIssuedMs_, config_.stopAckTimeoutMs))
            {
                stopOverdue_ = true;
                latchFault(FaultReason::StopAckTimeout);
            }
            // STOP is idempotently repeated, with the SAME token. The
            // lease remains held even if STOP confirmation never arrives.
            return stopEvent(lastStopReason_);
        }

        // StartPending/Running always hold the same exclusive lease.
        if (!globalSafe)
            return requestStop(now, StopReason::SafetyLost,
                               FaultReason::SafetyLost, true);

        if ((guards.motorFaultMask & (1U << leasedMotor_)) != 0)
            return requestStop(now, StopReason::MotorFault,
                               FaultReason::MotorFault, true);

        if (!targets.configurationValid ||
            !isCurrentIntentValid(targets))
            return requestStop(now, StopReason::TargetInvalid,
                               FaultReason::None, true);

        const HeatingZone::MotorTarget& target =
            targets.motors[leasedMotor_];
        if (target.zoneId != currentZone_ ||
            target.permille != currentTarget_)
            return requestStop(now, StopReason::TargetChanged,
                               FaultReason::None, true);

        const PositionEvidence& position = positions[leasedMotor_];
        if (!position.valid || !position.referenced ||
            position.estimatedPermille > HeatingZone::MaxPermille ||
            position.fullStrokeTimeMs < config_.minFullStrokeMs ||
            position.fullStrokeTimeMs > config_.maxFullStrokeMs ||
            position.revision != dispatchedRevision_[leasedMotor_])
            return requestStop(now, StopReason::ReferenceLost,
                               FaultReason::None, true);

        if (rearmRequired_)
            return requestStop(now, StopReason::Cancelled,
                               FaultReason::None, false);

        if (state_ == State::StartPending)
        {
            if (ack.kind == AckKind::Started &&
                ack.token == currentToken_)
            {
                state_ = State::Running;
                startedMs_ = now;
                return {};
            }
            if (elapsed(now, startIssuedMs_,
                        config_.startAckTimeoutMs))
                return requestStop(now, StopReason::StartAckTimeout,
                                   FaultReason::StartAckTimeout, true);
            return {};
        }

        // No acknowledgement or elapsed time grants a new motor. A
        // measured stop acknowledgement is always required afterward.
        if (elapsed(now, startedMs_, currentTravelMs_))
            return requestStop(now, StopReason::PlannedTravelTime,
                               FaultReason::None, false);
        return {};
    }

private:
    static uint16_t absDelta(uint16_t a, uint16_t b)
    {
        return a >= b ? static_cast<uint16_t>(a - b) :
                        static_cast<uint16_t>(b - a);
    }

    bool isCurrentIntentValid(const HeatingZone::Targets& targets) const
    {
        if (leasedMotor_ == NoMotor ||
            leasedMotor_ >= MotorCount)
            return false;
        const uint8_t bit = static_cast<uint8_t>(1U << leasedMotor_);
        return (targets.eligibleMotorMask & bit) != 0 &&
            targets.motors[leasedMotor_].eligible &&
            targets.motors[leasedMotor_].zoneId >= 1 &&
            targets.motors[leasedMotor_].zoneId <= HeatingZone::ZoneCount &&
            targets.motors[leasedMotor_].permille <= HeatingZone::MaxPermille;
    }

    uint32_t newToken()
    {
        ++nextToken_;
        if (nextToken_ == 0)
            ++nextToken_;
        return nextToken_;
    }

    Event selectAndStart(uint32_t now,
                         const HeatingZone::Targets& targets,
                         const PositionEvidence (&positions)[MotorCount],
                         const Guards& guards)
    {
        for (uint8_t stepIndex = 0; stepIndex < MotorCount; ++stepIndex)
        {
            const uint8_t i = static_cast<uint8_t>(
                (nextCandidate_ + stepIndex) % MotorCount);
            if ((guards.motorFaultMask & (1U << i)) != 0)
                continue;
            const HeatingZone::MotorTarget& wanted = targets.motors[i];
            if ((targets.eligibleMotorMask & (1U << i)) == 0 ||
                !wanted.eligible || wanted.zoneId == 0 ||
                wanted.zoneId > HeatingZone::ZoneCount ||
                wanted.permille > HeatingZone::MaxPermille)
                continue;
            const PositionEvidence& position = positions[i];
            if (!position.valid || !position.referenced ||
                position.estimatedPermille > HeatingZone::MaxPermille ||
                position.fullStrokeTimeMs < config_.minFullStrokeMs ||
                position.fullStrokeTimeMs > config_.maxFullStrokeMs)
                continue;
            if (awaitingRevision_[i])
            {
                if (position.revision == dispatchedRevision_[i])
                    continue;
                awaitingRevision_[i] = false;
            }

            const uint16_t diff =
                absDelta(wanted.permille, position.estimatedPermille);
            if (diff < config_.minChangePermille)
                continue;
            // ceil(duration*diff/1000), using 64-bit intermediate so no
            // overflow; reject overlong action rather than silently clip.
            const uint64_t scaled =
                static_cast<uint64_t>(position.fullStrokeTimeMs) * diff;
            const uint32_t plannedMs = static_cast<uint32_t>(
                (scaled + 999ULL) / 1000ULL);
            if (plannedMs == 0 || plannedMs > config_.maxSingleTravelMs)
                continue;

            leasedMotor_ = i;   // reserve exclusive lease FIRST
            currentToken_ = newToken();
            currentDirection_ =
                wanted.permille > position.estimatedPermille ?
                Direction::LogicalOpen : Direction::LogicalClose;
            currentTarget_ = wanted.permille;
            currentZone_ = wanted.zoneId;
            currentTravelMs_ = plannedMs;
            startIssuedMs_ = now;
            dispatchedRevision_[i] = position.revision;
            awaitingRevision_[i] = true;
            state_ = State::StartPending;
            Event event{};
            event.kind = EventKind::Start;
            event.motor = i;
            event.token = currentToken_;
            event.direction = currentDirection_;
            event.targetPermille = currentTarget_;
            event.plannedTravelMs = plannedMs;
            return event;
        }
        return {};
    }

    void latchFault(FaultReason fault)
    {
        if (!faultLatched_)
        {
            fault_ = fault;
            faultLatched_ = true;
        }
        rearmRequired_ = true;
    }

    Event requestStop(uint32_t now, StopReason reason,
                      FaultReason fault, bool requireRearm)
    {
        if (fault != FaultReason::None)
            latchFault(fault);
        if (requireRearm)
            rearmRequired_ = true;
        state_ = State::StopPending;
        stopIssuedMs_ = now;
        currentToken_ = newToken(); // New stop token. Old START ACK invalid.
        lastStopReason_ = reason;
        stopOverdue_ = false;
        return stopEvent(reason);
    }

    Event stopEvent(StopReason reason) const
    {
        Event event{};
        event.kind = EventKind::Stop;
        event.motor = leasedMotor_;
        event.token = currentToken_;
        event.direction = Direction::None;
        event.stopReason = reason;
        return event;
    }

    Config config_{};
    State state_ = State::Disarmed;
    FaultReason fault_ = FaultReason::None;
    bool faultLatched_ = false;
    bool rearmRequired_ = true;
    bool stopOverdue_ = false;
    bool haveStop_ = false;
    uint8_t leasedMotor_ = NoMotor;
    uint8_t nextCandidate_ = 0;
    uint8_t currentZone_ = 0;
    Direction currentDirection_ = Direction::None;
    uint16_t currentTarget_ = 0;
    uint32_t currentTravelMs_ = 0;
    uint32_t currentToken_ = 0;
    uint32_t nextToken_ = 0;
    uint32_t startIssuedMs_ = 0;
    uint32_t startedMs_ = 0;
    uint32_t stopIssuedMs_ = 0;
    uint32_t lastStopMs_ = 0;
    uint32_t completed_ = 0;
    StopReason lastStopReason_ = StopReason::None;
    bool awaitingRevision_[MotorCount] = {};
    uint32_t dispatchedRevision_[MotorCount] = {};
};

static_assert(MotorCount == 8, "KNX020 must match eight physical motor channels");
} // namespace MotorQueueSim

#endif // OPENKNX_MOTOR_QUEUE_SIMULATOR_HPP
