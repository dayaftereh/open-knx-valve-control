#ifndef OPENKNX_VIRTUAL_MOTOR_FEEDBACK_HPP
#define OPENKNX_VIRTUAL_MOTOR_FEEDBACK_HPP

#include "motor_queue_simulator.hpp"
#include <stdint.h>

// KNX021: synthetic event consumer. NOT a H-bridge driver.
// "On" means an abstract occupied slot in this software model only.
// The PositionEvidence records are intentionally invalidated after an
// interrupted movement: elapsed time alone does not prove real position.
namespace VirtualMotor
{
using MotorQueueSim::Acknowledgement;
using MotorQueueSim::AckKind;
using MotorQueueSim::Event;
using MotorQueueSim::EventKind;
using MotorQueueSim::MotorCount;
using MotorQueueSim::NoMotor;
using MotorQueueSim::PositionEvidence;
using MotorQueueSim::StopReason;

struct Options
{
    uint32_t startAckDelayMs = 50;
    uint32_t stopAckDelayMs = 50;
    bool dropStartAck = false;
    bool dropStopAck = false;
    bool stuckOnStop = false;
};

struct Diagnostics
{
    uint8_t abstractOccupiedMask = 0;
    uint8_t activeMotor = NoMotor;
    uint32_t startCount = 0;
    uint32_t stopCount = 0;
    uint32_t offAckCount = 0;
    uint32_t completedTravelCount = 0;
    uint32_t abortedTravelCount = 0;
    uint32_t protocolViolations = 0;
};

inline bool due(uint32_t now, uint32_t at, uint32_t waitMs)
{
    return static_cast<uint32_t>(now - at) >= waitMs;
}

class Backend
{
public:
    explicit Backend(const Options& options = {}) : options_(options) {}

    void reset()
    {
        // Resetting THIS simulator proves nothing about real power outputs.
        occupiedMask_ = 0;
        activeMotor_ = NoMotor;
        startPending_ = false;
        stopPending_ = false;
        startConfirmed_ = false;
        diag_ = {};
        for (uint8_t i = 0; i < MotorCount; ++i)
            evidence_[i] = {};
    }

    bool setEvidence(uint8_t motor, uint16_t estimatedPermille,
                     uint32_t fullStrokeMs, uint32_t revision)
    {
        if (motor >= MotorCount || occupiedMask_ != 0 ||
            startPending_ || stopPending_ ||
            estimatedPermille > HeatingZone::MaxPermille ||
            fullStrokeMs == 0)
            return false;
        evidence_[motor] = {true, true, estimatedPermille,
                            fullStrokeMs, revision};
        return true;
    }

    void setOptions(const Options& options)
    {
        options_ = options;
    }

    const PositionEvidence (&positions() const)[MotorCount]
    {
        return evidence_;
    }

    Diagnostics status() const
    {
        Diagnostics value = diag_;
        value.abstractOccupiedMask = occupiedMask_;
        value.activeMotor = activeMotor_;
        return value;
    }

    // Require the entire abstract output slot OFF, and no outstanding
    // STOP event, before separately permitting a new scheduler arm.
    bool independentlyAllOff() const
    {
        return occupiedMask_ == 0 && !stopPending_;
    }

    // May return ONE virtual acknowledgement for the prior tick's event.
    Acknowledgement poll(uint32_t now)
    {
        if (stopPending_)
        {
            if (!options_.dropStopAck && occupiedMask_ == 0 &&
                due(now, stoppedAtMs_, options_.stopAckDelayMs))
            {
                // Position has a new revision only after synthetic OFF ACK.
                if (activeMotor_ < MotorCount)
                {
                    PositionEvidence& measured = evidence_[activeMotor_];
                    ++measured.revision;
                    if (plannedCompletion_)
                    {
                        measured.estimatedPermille = targetPermille_;
                        measured.valid = true;
                        measured.referenced = true;
                        ++diag_.completedTravelCount;
                    }
                    else
                    {
                        // Simulated emergency/interruption may have moved
                        // partway, so neither a final position nor a
                        // previously trusted reference may be assumed.
                        measured.valid = false;
                        measured.referenced = false;
                        ++diag_.abortedTravelCount;
                    }
                }
                const Acknowledgement ack{
                    AckKind::AllOff, stopToken_, true};
                stopPending_ = false;
                startPending_ = false;
                startConfirmed_ = false;
                activeMotor_ = NoMotor;
                ++diag_.offAckCount;
                return ack;
            }
            return {};
        }

        if (startPending_ && !options_.dropStartAck &&
            due(now, startAtMs_, options_.startAckDelayMs))
        {
            startPending_ = false;
            startConfirmed_ = true;
            startedAckAtMs_ = now;
            return {AckKind::Started, startToken_, false};
        }
        return {};
    }

    // Accept ONLY the abstract event contract from MotorQueueSim.
    // There are no GPIO, KNX or hardware APIs in this class.
    bool consume(const Event& event, uint32_t now)
    {
        if (event.kind == EventKind::None)
            return true;

        if (event.kind == EventKind::Start)
        {
            if (occupiedMask_ != 0 || stopPending_ ||
                activeMotor_ != NoMotor ||
                event.motor >= MotorCount || event.token == 0 ||
                event.direction == MotorQueueSim::Direction::None ||
                event.targetPermille > HeatingZone::MaxPermille ||
                event.plannedTravelMs == 0 ||
                !evidence_[event.motor].valid ||
                !evidence_[event.motor].referenced)
            {
                ++diag_.protocolViolations;
                return false;
            }

            activeMotor_ = event.motor;
            occupiedMask_ =
                static_cast<uint8_t>(1U << activeMotor_);
            startToken_ = event.token;
            startAtMs_ = now;
            startPending_ = true;
            startConfirmed_ = false;
            targetPermille_ = event.targetPermille;
            plannedTravelMs_ = event.plannedTravelMs;
            ++diag_.startCount;
            return true;
        }

        if (event.kind == EventKind::Stop)
        {
            if (event.motor >= MotorCount || event.token == 0 ||
                event.motor != activeMotor_)
            {
                ++diag_.protocolViolations;
                return false;
            }

            // Repeated STOP with the same token is idempotent.
            if (stopPending_)
            {
                if (event.token != stopToken_)
                {
                    ++diag_.protocolViolations;
                    return false;
                }
                if (occupiedMask_ != 0 && !options_.stuckOnStop)
                {
                    occupiedMask_ = 0;
                    stoppedAtMs_ = now;
                }
                return true;
            }

            stopPending_ = true;
            stopToken_ = event.token;
            stoppedAtMs_ = now;
            plannedCompletion_ =
                event.stopReason == StopReason::PlannedTravelTime &&
                startConfirmed_ &&
                due(now, startedAckAtMs_, plannedTravelMs_);
            // The abstract slot is marked OFF only when our simulated
            // backend permits it; stuckOnStop leaves the mask occupied.
            if (!options_.stuckOnStop)
                occupiedMask_ = 0;
            startPending_ = false;
            ++diag_.stopCount;
            return true;
        }

        ++diag_.protocolViolations;
        return false;
    }

private:
    Options options_{};
    PositionEvidence evidence_[MotorCount] = {};
    Diagnostics diag_{};
    uint8_t occupiedMask_ = 0;
    uint8_t activeMotor_ = NoMotor;
    bool startPending_ = false;
    bool startConfirmed_ = false;
    bool stopPending_ = false;
    bool plannedCompletion_ = false;
    uint32_t startToken_ = 0;
    uint32_t stopToken_ = 0;
    uint32_t startAtMs_ = 0;
    uint32_t startedAckAtMs_ = 0;
    uint32_t stoppedAtMs_ = 0;
    uint32_t plannedTravelMs_ = 0;
    uint16_t targetPermille_ = 0;
};
static_assert(MotorCount == 8, "VirtualMotor must match eight KNX008 motors");
} // namespace VirtualMotor

#endif // OPENKNX_VIRTUAL_MOTOR_FEEDBACK_HPP
