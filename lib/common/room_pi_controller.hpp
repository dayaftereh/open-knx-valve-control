#ifndef OPENKNX_ROOM_PI_CONTROLLER_HPP
#define OPENKNX_ROOM_PI_CONTROLLER_HPP

#include "heating_zone_model.hpp"
#include <stdint.h>

// KNX019 ONLY: portable thermal-control REFERENCE MODEL.
// No Arduino, no ETS, no KNX network I/O, no motor driver, and no output
// scheduling. Outputs are *software demand intents*, not safe drive commands.
namespace RoomPi
{
constexpr uint8_t Zones = HeatingZone::ZoneCount;
constexpr double MinDemand = 0.0;
constexpr double MaxDemand = 1000.0;  // permille

struct Tuning
{
    // Illustrative defaults: NOT empirically tuned for a building or valve.
    uint16_t kpPermillePerKelvin = 250;
    uint16_t integralTimeSeconds = 3600;
    uint16_t deadbandCentiC = 10;
    uint16_t slewPermillePerMinute = 30;
    uint16_t sampleSeconds = 60;
};

inline bool operator==(const Tuning& a, const Tuning& b)
{
    return a.kpPermillePerKelvin == b.kpPermillePerKelvin &&
           a.integralTimeSeconds == b.integralTimeSeconds &&
           a.deadbandCentiC == b.deadbandCentiC &&
           a.slewPermillePerMinute == b.slewPermillePerMinute &&
           a.sampleSeconds == b.sampleSeconds;
}

inline bool validTuning(const Tuning& tuning)
{
    return tuning.kpPermillePerKelvin >= 1 &&
           tuning.kpPermillePerKelvin <= 1500 &&
           tuning.integralTimeSeconds >= 300 &&
           tuning.integralTimeSeconds <= 21600 &&
           tuning.deadbandCentiC <= 100 &&
           tuning.slewPermillePerMinute >= 1 &&
           tuning.slewPermillePerMinute <= 300 &&
           tuning.sampleSeconds >= 30 &&
           tuning.sampleSeconds <= 600;
}

enum class Status : uint8_t
{
    Disabled,
    DirectBypass,
    InvalidConfiguration,
    InvalidTuning,
    WaitingForInputs,
    WaitingForFreshInputs,
    Initialized,
    Holding,
    Updated,
    LoopGap
};

struct Diagnostic
{
    Status status = Status::Disabled;
    bool outputValid = false;
    uint16_t outputPermille = 0;
    double integralPermille = 0.0;
    uint32_t outputAtMs = 0;
};

inline double limit(double value, double low, double high)
{
    if (value < low) return low;
    if (value > high) return high;
    return value;
}

inline double magnitude(double value)
{
    return value < 0.0 ? -value : value;
}

inline bool sinceBarrier(uint32_t receivedMs,
                         uint32_t barrierMs, uint32_t nowMs)
{
    // All valid telemetry must already pass HeatingZone::fresh() so
    // elapsed times are small (<3600s) and wrap-safe.
    return static_cast<uint32_t>(nowMs - receivedMs) <=
           static_cast<uint32_t>(nowMs - barrierMs);
}

class ZoneController
{
public:
    void reset(uint32_t nowMs)
    {
        ready_ = false;
        requireNewInputs_ = true;
        barrierMs_ = nowMs;
        lastStepMs_ = nowMs;
        output_ = 0;
        integral_ = 0.0;
    }

    Diagnostic step(HeatingZone::Mode mode, const Tuning& tuning,
                    uint16_t roomTimeoutSeconds,
                    const HeatingZone::ZoneInput& zone,
                    uint32_t nowMs)
    {
        if (!initialized_ || mode != lastMode_ ||
            !(tuning == lastTuning_))
        {
            reset(nowMs);
            initialized_ = true;
            lastMode_ = mode;
            lastTuning_ = tuning;
        }

        if (!HeatingZone::isValidMode(mode) ||
            !HeatingZone::validTimeout(roomTimeoutSeconds))
        {
            reset(nowMs);
            return status(Status::InvalidConfiguration);
        }
        if (mode != HeatingZone::Mode::RoomTemperature)
        {
            reset(nowMs);
            return status(mode == HeatingZone::Mode::DirectPercent ?
                          Status::DirectBypass : Status::Disabled);
        }
        if (!validTuning(tuning))
        {
            reset(nowMs);
            return status(Status::InvalidTuning);
        }

        const uint32_t timeoutMs =
            static_cast<uint32_t>(roomTimeoutSeconds) * 1000UL;
        if (!HeatingZone::fresh(zone.setpointCentiC, nowMs, timeoutMs) ||
            !HeatingZone::fresh(zone.roomActualCentiC, nowMs, timeoutMs) ||
            !HeatingZone::validRoomSetpoint(zone.setpointCentiC.value) ||
            !HeatingZone::validRoomActual(zone.roomActualCentiC.value))
        {
            // Latch the FIRST fault timestamp. Do not advance this
            // recovery barrier on every loop iteration, or a fresh room
            // setpoint arriving before the room actual could be wrongly
            // invalidated when the second telemetry source recovers.
            if (ready_ || !requireNewInputs_)
                reset(nowMs);
            return status(Status::WaitingForInputs);
        }

        if (requireNewInputs_)
        {
            if (!sinceBarrier(zone.setpointCentiC.receivedAtMs,
                              barrierMs_, nowMs) ||
                !sinceBarrier(zone.roomActualCentiC.receivedAtMs,
                              barrierMs_, nowMs))
                return status(Status::WaitingForFreshInputs);

            requireNewInputs_ = false;
        }

        if (!ready_)
        {
            ready_ = true;
            lastStepMs_ = nowMs;
            // Bumpless from a neutral demand; never jump to an unbounded
            // position after reboot or regain of room sensors.
            output_ = 0;
            integral_ = 0.0;
            return status(Status::Initialized);
        }

        const uint32_t dtMs = static_cast<uint32_t>(nowMs - lastStepMs_);
        const uint32_t sampleMs =
            static_cast<uint32_t>(tuning.sampleSeconds) * 1000UL;
        if (dtMs < sampleMs)
            return status(Status::Holding);
        if (dtMs > 3UL * sampleMs)
        {
            // A suspended control task is not a safe way to integrate many
            // minutes of heat demand. Require NEW room telegrams afterwards.
            reset(nowMs);
            return status(Status::LoopGap);
        }

        int32_t errorCenti = static_cast<int32_t>(
            zone.setpointCentiC.value) - zone.roomActualCentiC.value;
        if (errorCenti >= -static_cast<int32_t>(tuning.deadbandCentiC) &&
            errorCenti <= static_cast<int32_t>(tuning.deadbandCentiC))
            errorCenti = 0;
        const double p = static_cast<double>(
            tuning.kpPermillePerKelvin) *
            static_cast<double>(errorCenti) / 100.0;

        const double stepLimit = static_cast<double>(
            tuning.slewPermillePerMinute) *
            static_cast<double>(dtMs) / 60000.0;
        const double current = static_cast<double>(output_);
        const double lo = limit(current - stepLimit, MinDemand, MaxDemand);
        const double hi = limit(current + stepLimit, MinDemand, MaxDemand);

        const double preIntegral = p + integral_;
        const double preTarget = limit(preIntegral, MinDemand, MaxDemand);

        // Conditional integration anti-windup: freeze when the command is
        // saturated OR when its requested direction is slew-limited.
        // Integrate when the error points *back* toward admissible output.
        const bool windupHigh = p > 0.0 &&
            (preIntegral >= MaxDemand || preTarget > hi);
        const bool windupLow = p < 0.0 &&
            (preIntegral <= MinDemand || preTarget < lo);
        if (!windupHigh && !windupLow)
        {
            // I_dot = (Kp/Ti)*error in permille/second.
            const double increment = p * static_cast<double>(dtMs) /
                (static_cast<double>(tuning.integralTimeSeconds) * 1000.0);
            integral_ = limit(integral_ + increment, MinDemand, MaxDemand);
        }

        const double target = limit(p + integral_, MinDemand, MaxDemand);
        const double bounded = limit(target, lo, hi);
        output_ = static_cast<uint16_t>(bounded + 0.5);
        lastStepMs_ = nowMs;
        return status(Status::Updated);
    }

    void invalidate(uint32_t nowMs)
    {
        reset(nowMs);
    }

    Diagnostic current() const
    {
        return status(ready_ ? Status::Holding : Status::WaitingForInputs);
    }

private:
    Diagnostic status(Status state) const
    {
        Diagnostic result{};
        result.status = state;
        result.outputValid = ready_;
        result.outputPermille = ready_ ? output_ : 0;
        result.outputAtMs = lastStepMs_;
        result.integralPermille = integral_;
        return result;
    }

    bool initialized_ = false;
    bool ready_ = false;
    bool requireNewInputs_ = true;
    HeatingZone::Mode lastMode_ = HeatingZone::Mode::Disabled;
    Tuning lastTuning_{};
    uint32_t barrierMs_ = 0;
    uint32_t lastStepMs_ = 0;
    uint16_t output_ = 0;
    double integral_ = 0.0;
};

inline bool sameSettings(const HeatingZone::Settings& a,
                         const HeatingZone::Settings& b)
{
    if (a.roomTimeoutSeconds != b.roomTimeoutSeconds ||
        a.directTimeoutSeconds != b.directTimeoutSeconds)
        return false;
    for (uint8_t i = 0; i < Zones; ++i)
        if (a.modes[i] != b.modes[i] ||
            a.motorZone[i] != b.motorZone[i])
            return false;
    return true;
}

class Bank
{
public:
    void reset(uint32_t nowMs)
    {
        for (uint8_t z = 0; z < Zones; ++z)
        {
            zones_[z] = ZoneController{};
            zones_[z].reset(nowMs);
            diagnostics_[z] = {};
        }
        settingsSeen_ = false;
    }

    // Caller supplies independent room signals, never manifold/pipe temps.
    // The bank overwrites ONLY regulatorOutputPermille, leaving the KNX008
    // setpoint, actual and direct input records untouched except that old
    // DIRECT demands are invalidated on mode entry/reconfiguration.
    void update(const HeatingZone::Settings& settings,
                const Tuning (&tuning)[Zones],
                HeatingZone::Inputs& inputs, uint32_t nowMs)
    {
        const bool configValid =
            HeatingZone::validate(settings) == HeatingZone::ConfigError::None;
        const bool reconfigured =
            !settingsSeen_ || !sameSettings(settings, lastSettings_);
        if (reconfigured)
        {
            // Invalidate every prior demand epoch, not merely a zone mode:
            // a motor-to-zone reassignment must not inherit an old command.
            // This conservative global fence requires new room/direct
            // telegrams after ANY ETS topology/timeout configuration change.
            for (uint8_t z = 0; z < Zones; ++z)
            {
                zones_[z].invalidate(nowMs);
                inputs.zones[z].directDpt5001Raw.valid = false;
            }
            lastSettings_ = settings;
            settingsSeen_ = true;
        }
        for (uint8_t z = 0; z < Zones; ++z)
        {
            const HeatingZone::Mode mode = settings.modes[z];
            if (!configValid)
            {
                zones_[z].invalidate(nowMs);
                diagnostics_[z] = {};
                diagnostics_[z].status = Status::InvalidConfiguration;
                inputs.zones[z].regulatorOutputPermille = {};
                continue;
            }
            diagnostics_[z] = zones_[z].step(
                mode, tuning[z], settings.roomTimeoutSeconds,
                inputs.zones[z], nowMs);
            const Diagnostic& diag = diagnostics_[z];
            HeatingZone::TimedValue<uint16_t>& out =
                inputs.zones[z].regulatorOutputPermille;
            if (diag.outputValid)
            {
                out.value = diag.outputPermille;
                out.receivedAtMs = diag.outputAtMs;
                out.valid = true;
            }
            else
            {
                out = {};
            }
        }
    }

    const Diagnostic& diagnostic(uint8_t zoneIndex) const
    {
        return diagnostics_[zoneIndex]; // caller must check 0..7
    }

private:
    ZoneController zones_[Zones] = {};
    Diagnostic diagnostics_[Zones] = {};
    bool settingsSeen_ = false;
    HeatingZone::Settings lastSettings_{};
};

static_assert(Zones == 8, "Room controller must match 8-zone KNX008 model");
} // namespace RoomPi

#endif // OPENKNX_ROOM_PI_CONTROLLER_HPP
