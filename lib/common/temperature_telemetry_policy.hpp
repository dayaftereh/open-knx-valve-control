#ifndef OPENKNX_TEMPERATURE_TELEMETRY_POLICY_HPP
#define OPENKNX_TEMPERATURE_TELEMETRY_POLICY_HPP

#include <stdint.h>

// Hardware-independent KNX015 telemetry schedule. It does not encode KNX,
// access the bus, or move a motor. It only proposes one telegram per call.
// Call commit() ONLY after GroupObject.value() accepted the conversion.
namespace TemperatureTelemetry
{
constexpr uint8_t Channels = 9;
constexpr uint16_t SensorMask = 0x01FFU;
constexpr uint32_t MinBusGapMs = 250U;
constexpr uint32_t MinPerSensorMs = 5000U;
constexpr uint32_t MinPeriodSeconds = 10U;
constexpr uint32_t MaxPeriodSeconds = 3600U;
constexpr uint16_t MaxDeltaCenti = 1000U;

enum class Kind : uint8_t
{
    None = 0,
    LinkOnline,
    ValidMask,
    Temperature
};

struct Settings
{
    bool enabled = false;
    uint32_t periodicSeconds = 60U;    // cyclic even when unchanged
    uint16_t changeDeltaCenti = 50U;  // immediate update if >= 0.50 C
};

struct Inputs
{
    bool online = false;
    uint16_t validMask = 0;
    int16_t centiC[Channels] = {};
};

struct Proposal
{
    Kind kind = Kind::None;
    uint8_t channel = 0;
    int16_t centiC = 0;
    uint16_t mask = 0;
    bool online = false;
};

inline bool elapsed(uint32_t now, uint32_t before, uint32_t ms)
{
    return static_cast<uint32_t>(now - before) >= ms;
}

inline Settings bounded(Settings settings)
{
    if (settings.periodicSeconds < MinPeriodSeconds)
        settings.periodicSeconds = MinPeriodSeconds;
    if (settings.periodicSeconds > MaxPeriodSeconds)
        settings.periodicSeconds = MaxPeriodSeconds;
    if (settings.changeDeltaCenti > MaxDeltaCenti)
        settings.changeDeltaCenti = MaxDeltaCenti;
    return settings;
}

inline int32_t absoluteDelta(int16_t a, int16_t b)
{
    const int32_t diff = static_cast<int32_t>(a) - static_cast<int32_t>(b);
    return diff < 0 ? -diff : diff;
}

class Scheduler
{
public:
    void begin(uint32_t now)
    {
        hasBusSend_ = false;
        lastBusSend_ = now;
        linkSent_ = false;
        maskSent_ = false;
        lastLink_ = false;
        lastMask_ = 0;
        observedMask_ = 0;
        nextChannel_ = 0;
        for (uint8_t i = 0; i < Channels; ++i)
        {
            hasTemperature_[i] = false;
            lastTemperature_[i] = 0;
            lastTemperatureAt_[i] = now;
        }
    }

    Proposal select(uint32_t now, Settings settings, const Inputs& input)
    {
        if (!settings.enabled)
            return {};
        settings = bounded(settings);

        // An offline UART bridge MUST report zero valid channels.
        uint16_t mask = input.online ? (input.validMask & SensorMask) : 0;
        // Don't publish impossible sensor values even if an upstream bug
        // accidentally marked them Valid.
        for (uint8_t i = 0; i < Channels; ++i)
            if (input.centiC[i] < -5500 || input.centiC[i] > 12500)
                mask &= static_cast<uint16_t>(~(1U << i));

        // A reattached/previously invalid sensor must be published anew:
        // the old KO may still show an obsolete physical reading.
        const uint16_t rising = static_cast<uint16_t>(
            mask & static_cast<uint16_t>(~observedMask_));
        for (uint8_t i = 0; i < Channels; ++i)
            if (rising & (1U << i))
                hasTemperature_[i] = false;
        observedMask_ = mask;

        if (hasBusSend_ && !elapsed(now, lastBusSend_, MinBusGapMs))
            return {};

        if (!linkSent_ || lastLink_ != input.online)
            return {Kind::LinkOnline, 0, 0, mask, input.online};

        if (!maskSent_ || lastMask_ != mask)
            return {Kind::ValidMask, 0, 0, mask, input.online};

        const uint32_t periodMs = settings.periodicSeconds * 1000UL;
        for (uint8_t count = 0; count < Channels; ++count)
        {
            const uint8_t i = static_cast<uint8_t>(
                (nextChannel_ + count) % Channels);
            if (!(mask & (1U << i)))
                continue;

            const bool isFirst = !hasTemperature_[i];
            const bool periodic = !isFirst &&
                elapsed(now, lastTemperatureAt_[i], periodMs);
            const bool changed = !isFirst &&
                settings.changeDeltaCenti != 0 &&
                elapsed(now, lastTemperatureAt_[i], MinPerSensorMs) &&
                absoluteDelta(input.centiC[i], lastTemperature_[i]) >=
                    settings.changeDeltaCenti;

            if (isFirst || periodic || changed)
                return {Kind::Temperature, i, input.centiC[i], mask,
                        input.online};
        }
        return {};
    }

    void commit(const Proposal& proposal, uint32_t now)
    {
        if (proposal.kind == Kind::None)
            return;
        hasBusSend_ = true;
        lastBusSend_ = now;

        switch (proposal.kind)
        {
        case Kind::LinkOnline:
            linkSent_ = true;
            lastLink_ = proposal.online;
            break;
        case Kind::ValidMask:
            maskSent_ = true;
            lastMask_ = proposal.mask;
            break;
        case Kind::Temperature:
            if (proposal.channel >= Channels)
                return;
            hasTemperature_[proposal.channel] = true;
            lastTemperature_[proposal.channel] = proposal.centiC;
            lastTemperatureAt_[proposal.channel] = now;
            nextChannel_ = static_cast<uint8_t>(
                (proposal.channel + 1) % Channels);
            break;
        case Kind::None:
            break;
        }
    }

private:
    bool hasBusSend_ = false;
    uint32_t lastBusSend_ = 0;
    bool linkSent_ = false;
    bool maskSent_ = false;
    bool lastLink_ = false;
    uint16_t lastMask_ = 0;
    uint16_t observedMask_ = 0;
    uint8_t nextChannel_ = 0;
    bool hasTemperature_[Channels] = {};
    int16_t lastTemperature_[Channels] = {};
    uint32_t lastTemperatureAt_[Channels] = {};
};

static_assert(Channels == 9, "KNX015 wire/ETS channel count changed");
static_assert(SensorMask == 511U, "T0..T8 require 9 validity bits");
} // namespace TemperatureTelemetry

#endif // OPENKNX_TEMPERATURE_TELEMETRY_POLICY_HPP
