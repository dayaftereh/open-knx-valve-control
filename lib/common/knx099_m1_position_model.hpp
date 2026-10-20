#ifndef OPENKNX_KNX099_M1_POSITION_MODEL_HPP
#define OPENKNX_KNX099_M1_POSITION_MODEL_HPP

#include <stdint.h>

// KNX099: PORTABLE POSITION/ENDSTOP POLICY, NEVER A MOTOR DRIVER.
//
// Internal "positionPermille" is the relative travel F-end (0) to
// R-end (1000). R/F has NOT been mapped to real valve open/closed,
// nor to ETS DPT 5.001; no physical encoder was measured.
// This class NEVER references Arduino, GPIO, INA/I2C, KNX or Serial.
// Caller must supply independently verified start/off ACKs and valid
// current samples and honor every returned STOP immediately.
// KNX098 measurements are bench-current-endstop CANDIDATES only.
namespace Knx099
{

enum class Direction : uint8_t { None, R, F };
enum class Phase : uint8_t {
    Unreferenced, Idle, StartPending, Running, StopPending, FaultLatched
};
enum class Evidence : uint8_t {
    None, CurrentEndstopCandidate, TimedEstimate
};
enum class Operation : uint8_t {
    None, SeekReference, TimedSegment
};
enum class StopReason : uint8_t {
    None, EndstopCandidate, TimedTarget, InvalidINA, LinkLost,
    BadSupply, OverCurrent, CurrentCut, UnexpectedLoad,
    MaxDuration, StartAckTimeout, StartAckMismatch, StopAckTimeout, Cancelled
};
enum class ActionType : uint8_t { None, StartR, StartF, Stop, Rejected };

struct Action
{
    ActionType type = ActionType::None;
    StopReason reason = StopReason::None;
};

struct Sample
{
    bool valid = false;
    bool overflow = false;
    bool linkUp = false;  // watchdog/transport qualified by the caller
    int32_t busMv = 0;
    int32_t currentMa = 0;
};

struct Calibration
{
    // Freeze from KNX098 M1 COM7 3-cycle repeatability (rounded to ms):
    uint32_t fullRMs = 24388;
    uint32_t fullFMs = 22751;
    uint32_t maxSeekMs = 30000;
    uint32_t samplePeriodMs = 8;
    uint32_t startupIgnoreMs = 450;
    uint32_t startAckTimeoutMs = 500;
    uint32_t stopAckTimeoutMs = 1000;
    uint32_t minTimedMs = 150;
    uint16_t deadbandPermille = 15;
    // Never claim a time-only position too close to a measured endpoint;
    // full endpoints are always current-referenced, not timer-referenced.
    uint16_t endpointMarginPermille = 30;
    uint8_t maxTimedSegmentsWithoutReference = 4;
    int32_t riseCurrentMa = 45;
    uint8_t riseConsecutive = 6;
    int32_t cutCurrentMa = 5;
    int32_t absoluteCurrentMa = 120;
    int32_t idleCurrentMa = 25;
    int32_t busMinMv = 3100;
    int32_t busMaxMv = 3450;
};

inline bool validCalibration(const Calibration& c)
{
    return c.fullRMs >= 12000 && c.fullRMs <= 30000 &&
           c.fullFMs >= 12000 && c.fullFMs <= 30000 &&
           c.maxSeekMs >= c.fullRMs && c.maxSeekMs >= c.fullFMs &&
           c.maxSeekMs <= 30000 &&
           c.samplePeriodMs == 8 &&
           c.startupIgnoreMs >= 100 && c.startupIgnoreMs <= 2000 &&
           c.startAckTimeoutMs >= 100 && c.startAckTimeoutMs <= 2000 &&
           c.stopAckTimeoutMs >= 100 && c.stopAckTimeoutMs <= 5000 &&
           c.minTimedMs >= 100 && c.minTimedMs <= 500 &&
           c.deadbandPermille >= 1 && c.deadbandPermille <= 50 &&
           c.endpointMarginPermille >= c.deadbandPermille &&
           c.endpointMarginPermille <= 100 &&
           c.maxTimedSegmentsWithoutReference >= 1 &&
           c.maxTimedSegmentsWithoutReference <= 10 &&
           c.riseCurrentMa >= 20 && c.riseCurrentMa < c.absoluteCurrentMa &&
           c.riseConsecutive >= 3 && c.riseConsecutive <= 12 &&
           c.cutCurrentMa >= 0 && c.cutCurrentMa < c.riseCurrentMa &&
           c.absoluteCurrentMa <= 120 && c.idleCurrentMa <= 25 &&
           c.busMinMv >= 3000 && c.busMaxMv <= 3500 &&
           c.busMaxMv > c.busMinMv;
}

inline uint32_t elapsed(uint32_t now, uint32_t then)
{
    return static_cast<uint32_t>(now - then);
}

inline bool safeSample(const Sample& s, const Calibration& c, bool idle)
{
    return s.valid && !s.overflow && s.linkUp &&
           s.busMv >= c.busMinMv && s.busMv <= c.busMaxMv &&
           s.currentMa >= -5 &&
           s.currentMa <= (idle ? c.idleCurrentMa : c.absoluteCurrentMa);
}

struct Snapshot
{
    Phase phase = Phase::Unreferenced;
    Evidence evidence = Evidence::None;
    Direction activeDirection = Direction::None;
    Operation operation = Operation::None;
    StopReason lastStop = StopReason::None;
    uint16_t estimatedPositionTowardR = 0;
    uint16_t requestedPositionTowardR = 0;
    uint32_t plannedTravelMs = 0;
    uint8_t timedSegmentsSinceReference = 0;
    uint32_t completedReferences = 0;
    uint32_t completedTimedSegments = 0;
    bool referenceAvailable = false;
};

class Model
{
public:
    explicit Model(const Calibration& c = Calibration{}) : cfg_(c) { reset(); }

    void reset()
    {
        // Reboot loses RAM position; no presumed reference survived.
        phase_ = Phase::Unreferenced;
        evidence_ = Evidence::None;
        operation_ = Operation::None;
        direction_ = Direction::None;
        reason_ = StopReason::None;
        position_ = 0;
        desired_ = 0;
        plannedMs_ = 0;
        startedAt_ = 0;
        requestedAt_ = 0;
        stopAt_ = 0;
        lastSampleAt_ = 0;
        haveSample_ = false;
        highCount_ = 0;
        lowCount_ = 0;
        segmentsSinceReference_ = 0;
        completedReferences_ = 0;
        completedSegments_ = 0;
    }

    const Calibration& calibration() const { return cfg_; }
    Phase phase() const { return phase_; }
    Evidence evidence() const { return evidence_; }
    uint16_t positionTowardR() const { return position_; }
    uint32_t plannedMs() const { return plannedMs_; }

    Snapshot snapshot() const
    {
        Snapshot s{};
        s.phase = phase_;
        s.evidence = evidence_;
        s.activeDirection = direction_;
        s.operation = operation_;
        s.lastStop = reason_;
        s.estimatedPositionTowardR = position_;
        s.requestedPositionTowardR = desired_;
        s.plannedTravelMs = plannedMs_;
        s.timedSegmentsSinceReference = segmentsSinceReference_;
        s.completedReferences = completedReferences_;
        s.completedTimedSegments = completedSegments_;
        s.referenceAvailable = evidence_ != Evidence::None;
        return s;
    }

    // For offline replay of an ALREADY MEASURED, already stopped
    // INA current endstop; never an assertion of physical open/closed.
    // A real adapter may only pass TRUE after independently validating
    // a LOAD_RISE trace AND power-off proof.
    bool acceptStoppedCurrentEndpoint(Direction at, bool confirmedSixSamples,
                                      bool independentAllOff, const Sample& idle)
    {
        if (at == Direction::None || !confirmedSixSamples ||
            !independentAllOff || !validCalibration(cfg_) ||
            !safeSample(idle, cfg_, true) ||
            (phase_ != Phase::Idle && phase_ != Phase::Unreferenced))
            return false;
        position_ = (at == Direction::R) ? 1000 : 0;
        desired_ = position_;
        evidence_ = Evidence::CurrentEndstopCandidate;
        phase_ = Phase::Idle;
        direction_ = Direction::None;
        operation_ = Operation::None;
        reason_ = StopReason::EndstopCandidate;
        segmentsSinceReference_ = 0;
        ++completedReferences_;
        return true;
    }

    // Explicit homing sequence; current threshold (not elapsed time)
    // must stop it, and OFF ACK must follow before any anchor is accepted.
    Action requestReference(Direction toward, uint32_t now,
                            const Sample& idle, bool independentAllOff,
                            bool explicitPermit)
    {
        if (toward == Direction::None)
            return {ActionType::Rejected, StopReason::None};
        return begin(Operation::SeekReference,toward,now,idle,
                     independentAllOff,explicitPermit,
                     toward == Direction::R ? 1000 : 0,cfg_.maxSeekMs);
    }

    // INTERMEDIATE ONLY. Endpoints always require their current
    // threshold, not merely an unverified duration.
    Action requestTarget(uint16_t targetTowardR, uint32_t now,
                         const Sample& idle, bool independentAllOff,
                         bool explicitPermit)
    {
        if (phase_ != Phase::Idle || evidence_ == Evidence::None ||
            targetTowardR > 1000 ||
            targetTowardR <= cfg_.endpointMarginPermille ||
            targetTowardR >= 1000-cfg_.endpointMarginPermille ||
            segmentsSinceReference_ >= cfg_.maxTimedSegmentsWithoutReference)
            return {ActionType::Rejected, StopReason::None};
        const uint16_t delta = (targetTowardR > position_)
            ? static_cast<uint16_t>(targetTowardR - position_)
            : static_cast<uint16_t>(position_ - targetTowardR);
        if (delta <= cfg_.deadbandPermille)
            return {ActionType::None, StopReason::None};
        const Direction d = (targetTowardR > position_) ? Direction::R : Direction::F;
        const uint32_t full = (d == Direction::R) ? cfg_.fullRMs : cfg_.fullFMs;
        const uint32_t ms = static_cast<uint32_t>(
            (static_cast<uint64_t>(full) * delta + 500u) / 1000u);
        if (ms < cfg_.minTimedMs || ms >= cfg_.maxSeekMs)
            return {ActionType::Rejected, StopReason::None};
        return begin(Operation::TimedSegment,d,now,idle,
                     independentAllOff,explicitPermit,targetTowardR,ms);
    }

    // Only a real motor-start ACK can start counting timed motion.
    // An ACK with the wrong direction immediately EMITS STOP; a caller
    // must never ignore this Action and continue running in the wrong
    // direction. A successful ACK returns None and switches to Running.
    Action acknowledgeStarted(uint32_t now, Direction actuallyRunning)
    {
        if (phase_ != Phase::StartPending || direction_ == Direction::None)
            return {ActionType::Rejected, StopReason::None};
        if (direction_ != actuallyRunning)
            return issueStop(now,StopReason::StartAckMismatch);
        if (elapsed(now,requestedAt_) > cfg_.startAckTimeoutMs)
            return issueStop(now,StopReason::StartAckTimeout);
        startedAt_ = now;
        highCount_ = 0;
        lowCount_ = 0;
        haveSample_ = false;
        phase_ = Phase::Running;
        return {};
    }

    // Called with validated I2C sample at approximately 8ms cadence.
    // STOP is an ORDER; the caller must still prove outputs physically off.
    Action tick(uint32_t now, const Sample& sample)
    {
        if (phase_ == Phase::StartPending &&
            elapsed(now,requestedAt_) > cfg_.startAckTimeoutMs)
            return issueStop(now,StopReason::StartAckTimeout);
        if (phase_ == Phase::StopPending &&
            elapsed(now,stopAt_) > cfg_.stopAckTimeoutMs)
        {
            // Unknown hardware state: fault permanently, never declare success.
            invalidate(StopReason::StopAckTimeout);
            return {ActionType::Stop,StopReason::StopAckTimeout};
        }
        if (phase_ != Phase::Running)
            return {};

        const uint32_t t = elapsed(now,startedAt_);
        if (!sample.linkUp)
            return issueStop(now,StopReason::LinkLost);
        if (!sample.valid || sample.overflow || sample.currentMa < -5)
            return issueStop(now,StopReason::InvalidINA);
        if (sample.busMv < cfg_.busMinMv || sample.busMv > cfg_.busMaxMv)
            return issueStop(now,StopReason::BadSupply);
        if (sample.currentMa > cfg_.absoluteCurrentMa)
            return issueStop(now,StopReason::OverCurrent);
        // A gap is never allowed to count as consecutive readings.
        // Also reject a delayed FIRST sample; otherwise a timed segment
        // could falsely complete without any current monitoring.
        if ((!haveSample_ && t > 2u*cfg_.samplePeriodMs) ||
            (haveSample_ && elapsed(now,lastSampleAt_) > 2u*cfg_.samplePeriodMs))
            return issueStop(now,StopReason::InvalidINA);
        haveSample_ = true;
        lastSampleAt_ = now;

        if (t >= cfg_.startupIgnoreMs)
        {
            highCount_ = sample.currentMa >= cfg_.riseCurrentMa
                ? static_cast<uint8_t>(highCount_+1u) : 0;
            lowCount_ = sample.currentMa >= 0 &&
                        sample.currentMa <= cfg_.cutCurrentMa
                ? static_cast<uint8_t>(lowCount_+1u) : 0;
            if (highCount_ >= cfg_.riseConsecutive)
                return issueStop(now, operation_ == Operation::SeekReference
                           ? StopReason::EndstopCandidate
                           : StopReason::UnexpectedLoad);
            if (lowCount_ >= cfg_.riseConsecutive)
                return issueStop(now, StopReason::CurrentCut);
        }

        if (t >= cfg_.maxSeekMs)
            return issueStop(now,StopReason::MaxDuration);
        if (operation_ == Operation::TimedSegment && t >= plannedMs_)
            return issueStop(now,StopReason::TimedTarget);
        return {};
    }

    // A USB "STOPPED" response is not enough unless caller independently
    // confirms ALL relevant driver GPIOs inactive; this model never checks
    // any physical pins itself.
    bool acknowledgeAllOff(bool independentAllOff)
    {
        if (phase_ != Phase::StopPending || !independentAllOff)
            return false;
        const bool anchor = reason_ == StopReason::EndstopCandidate &&
                            operation_ == Operation::SeekReference;
        const bool timed = reason_ == StopReason::TimedTarget &&
                           operation_ == Operation::TimedSegment;
        if (anchor)
        {
            position_ = direction_ == Direction::R ? 1000 : 0;
            evidence_ = Evidence::CurrentEndstopCandidate;
            segmentsSinceReference_ = 0;
            ++completedReferences_;
        }
        else if (timed)
        {
            position_ = desired_;
            evidence_ = Evidence::TimedEstimate;
            ++segmentsSinceReference_;
            ++completedSegments_;
        }
        else
        {
            invalidate(reason_);  // ambiguous position is never retained
            return true;
        }
        phase_ = Phase::Idle;
        direction_ = Direction::None;
        operation_ = Operation::None;
        return true;
    }

    Action cancel(uint32_t now)
    {
        if (phase_ != Phase::Running && phase_ != Phase::StartPending)
            return {ActionType::None,StopReason::None};
        return issueStop(now,StopReason::Cancelled);
    }

private:
    Action begin(Operation op, Direction d, uint32_t now,
                 const Sample& idle, bool allOff, bool permit,
                 uint16_t target, uint32_t millisToRun)
    {
        if (!validCalibration(cfg_) || !permit || !allOff ||
            !safeSample(idle,cfg_,true) ||
            (phase_ != Phase::Idle && phase_ != Phase::Unreferenced) ||
            d == Direction::None)
            return {ActionType::Rejected,StopReason::None};
        phase_ = Phase::StartPending;
        operation_ = op;
        direction_ = d;
        requestedAt_ = now;
        desired_ = target;
        plannedMs_ = millisToRun;
        reason_ = StopReason::None;
        return {d == Direction::R ? ActionType::StartR : ActionType::StartF,
                StopReason::None};
    }

    Action issueStop(uint32_t now, StopReason why)
    {
        reason_ = why;
        phase_ = Phase::StopPending;
        stopAt_ = now;
        return {ActionType::Stop,why};
    }

    void invalidate(StopReason reason)
    {
        reason_ = reason;
        evidence_ = Evidence::None;
        phase_ = Phase::FaultLatched;
        position_ = 0;
        desired_ = 0;
        direction_ = Direction::None;
        operation_ = Operation::None;
    }

    Calibration cfg_;
    Phase phase_ = Phase::Unreferenced;
    Evidence evidence_ = Evidence::None;
    Operation operation_ = Operation::None;
    Direction direction_ = Direction::None;
    StopReason reason_ = StopReason::None;
    uint16_t position_ = 0;
    uint16_t desired_ = 0;
    uint32_t plannedMs_ = 0;
    uint32_t startedAt_ = 0;
    uint32_t requestedAt_ = 0;
    uint32_t stopAt_ = 0;
    uint32_t lastSampleAt_ = 0;
    bool haveSample_ = false;
    uint8_t highCount_ = 0;
    uint8_t lowCount_ = 0;
    uint8_t segmentsSinceReference_ = 0;
    uint32_t completedReferences_ = 0;
    uint32_t completedSegments_ = 0;
};

} // namespace Knx099

#endif // OPENKNX_KNX099_M1_POSITION_MODEL_HPP
