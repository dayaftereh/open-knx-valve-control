#ifndef KNX_TEMPERATURE_SAMPLER_CORE_HPP
#define KNX_TEMPERATURE_SAMPLER_CORE_HPP

#include <stdint.h>

// Hardware-independent scheduling/quality state. Tested by a native C++ harness.
// All durations must stay below 2^31 ms for wrap-safe "due" comparisons.
namespace TemperatureSampler
{
    constexpr uint32_t MinPeriodMs = 2000U;
    constexpr uint32_t MaxPeriodMs = 3600000U;
    constexpr uint32_t RetryPeriodMs = 10000U;
    constexpr uint32_t MinIdleGapMs = 50U;

    constexpr uint8_t HasSample = 0x01;
    constexpr uint8_t Valid = 0x02;
    constexpr uint8_t Converting = 0x04;
    constexpr uint8_t Stale = 0x08;
    constexpr uint8_t Error = 0x10;

    enum class Fault : uint8_t
    {
        None = 0,
        NoSensor = 1,
        ParasitePower = 2,
        ReadFailed = 3,
        PowerOn85 = 4,
        OutsideRange = 5,
        SampleStale = 6,
        NoSample = 7,
        Recovering = 8
    };

    enum class Action : uint8_t
    {
        None = 0,
        Discover,
        StartConversion,
        FinishConversion
    };

    // Values are transport-ready but *not* a transport message: KNX014 owns UART.
    struct Snapshot
    {
        int16_t centiC = 0;
        uint16_t ageSeconds = 0xFFFF;
        uint8_t flags = Error;
        Fault fault = Fault::NoSensor;
    };

    constexpr bool elapsed(uint32_t now, uint32_t previous, uint32_t period)
    {
        return static_cast<uint32_t>(now - previous) >= period;
    }

    constexpr bool due(uint32_t now, uint32_t deadline)
    {
        return static_cast<uint32_t>(now - deadline) < 0x80000000UL;
    }

    constexpr uint32_t boundedPeriod(uint32_t periodMs)
    {
        return periodMs < MinPeriodMs ? MinPeriodMs
             : (periodMs > MaxPeriodMs ? MaxPeriodMs : periodMs);
    }

    constexpr uint16_t conversionWaitMs(uint8_t resolution)
    {
        // DS18B20 maximum 9/10/11/12-bit conversion times, plus 20 ms margin.
        return resolution <= 9 ? 114U : resolution == 10 ? 208U
             : resolution == 11 ? 395U : 770U;
    }

    constexpr bool acceptableTemperature(float value)
    {
        // Reject DallasTemperature error sentinels and the DS18B20 85 C
        // power-on value. A real exactly-85 C sample is deliberately ambiguous.
        return value >= -55.0f && value <= 125.0f && value != 85.0f;
    }

    constexpr int16_t toCentiC(float celsius)
    {
        // Only call after acceptableTemperature() has succeeded.
        return static_cast<int16_t>(celsius * 100.0f +
                                     (celsius >= 0.0f ? 0.5f : -0.5f));
    }

    class Core
    {
    public:
        void begin(uint32_t now, uint32_t staggerMs, uint32_t periodMs, uint16_t waitMs)
        {
            periodMs_ = boundedPeriod(periodMs);
            waitMs_ = waitMs;
            nextStartAt_ = now + staggerMs;
            conversionStartedAt_ = 0;
            lastGoodAt_ = 0;
            lastCentiC_ = 0;
            hasAddress_ = false;
            hasSample_ = false;
            converting_ = false;
            fault_ = Fault::NoSensor;
        }

        void setPeriod(uint32_t periodMs)
        {
            periodMs_ = boundedPeriod(periodMs);
        }

        Action nextAction(uint32_t now) const
        {
            if (converting_)
            {
                return elapsed(now, conversionStartedAt_, waitMs_)
                           ? Action::FinishConversion : Action::None;
            }
            if (!due(now, nextStartAt_))
                return Action::None;
            return hasAddress_ ? Action::StartConversion : Action::Discover;
        }

        void onDiscovered(uint32_t now, bool found, bool parasitePowered)
        {
            if (found && !parasitePowered)
            {
                hasAddress_ = true;
                // Do not revalidate a retained old sample merely because
                // the 1-Wire address has been found again. Only a successful
                // *new conversion/read* may clear a previous sensor fault.
                if (fault_ != Fault::None)
                    fault_ = hasSample_ ? Fault::Recovering : Fault::NoSample;
                nextStartAt_ = now;
            }
            else
            {
                hasAddress_ = false;
                fault_ = parasitePowered ? Fault::ParasitePower : Fault::NoSensor;
                nextStartAt_ = now + RetryPeriodMs;
            }
        }

        void onConversionStarted(uint32_t now, bool successful)
        {
            if (successful)
            {
                converting_ = true;
                conversionStartedAt_ = now;
            }
            else
            {
                converting_ = false;
                hasAddress_ = false;
                fault_ = Fault::ReadFailed;
                nextStartAt_ = now + RetryPeriodMs;
            }
        }

        void onConversionFinished(uint32_t now, float celsius)
        {
            if (!converting_)
                return;
            converting_ = false;
            if (acceptableTemperature(celsius))
            {
                lastCentiC_ = toCentiC(celsius);
                lastGoodAt_ = now;
                hasSample_ = true;
                fault_ = Fault::None;
            }
            else
            {
                fault_ = celsius == 85.0f ? Fault::PowerOn85
                       : (celsius < -55.0f || celsius != celsius) ? Fault::ReadFailed
                       : Fault::OutsideRange;
                // A missing/broken sensor needs a fresh address discovery.
                if (fault_ == Fault::ReadFailed)
                    hasAddress_ = false;
            }
            // Rate is start-to-start; never recursively catch up a missed cycle.
            const uint32_t nominal = conversionStartedAt_ + periodMs_;
            nextStartAt_ = due(now, nominal) ? now + MinIdleGapMs : nominal;
        }

        Snapshot snapshot(uint32_t now) const
        {
            Snapshot result{};
            result.fault = fault_;
            if (!hasSample_ && result.fault == Fault::None)
                result.fault = Fault::NoSample;
            if (hasSample_)
            {
                result.centiC = lastCentiC_;
                result.flags |= HasSample;
                const uint32_t ageMs = now - lastGoodAt_;
                const uint32_t ageSeconds = ageMs / 1000U;
                result.ageSeconds = ageSeconds > 65535U
                                      ? 65535U : static_cast<uint16_t>(ageSeconds);
                if (ageMs >= periodMs_ * 3U)
                {
                    result.flags |= Stale;
                    if (result.fault == Fault::None)
                        result.fault = Fault::SampleStale;
                }
            }
            if (converting_)
                result.flags |= Converting;
            if (hasSample_ && result.fault == Fault::None)
                result.flags |= Valid;
            if (result.fault != Fault::None)
                result.flags |= Error;
            else
                result.flags &= static_cast<uint8_t>(~Error);
            return result;
        }

    private:
        uint32_t nextStartAt_ = 0;
        uint32_t conversionStartedAt_ = 0;
        uint32_t lastGoodAt_ = 0;
        uint32_t periodMs_ = 10000;
        uint16_t waitMs_ = 770;
        int16_t lastCentiC_ = 0;
        bool hasAddress_ = false;
        bool hasSample_ = false;
        bool converting_ = false;
        Fault fault_ = Fault::NoSensor;
    };

    static_assert(conversionWaitMs(9) == 114, "9 bit conversion wait");
    static_assert(conversionWaitMs(12) == 770, "12 bit conversion wait");
    static_assert(acceptableTemperature(0.0f), "0 C is valid");
    static_assert(acceptableTemperature(-15.125f), "negative temperatures valid");
    static_assert(!acceptableTemperature(-127.0f), "disconnected is invalid");
    static_assert(!acceptableTemperature(85.0f), "85 C power-on sentinel");
    static_assert(due(0U, 0xFFFFFFFEUL), "deadline wrap is safe");
} // namespace TemperatureSampler

#endif // KNX_TEMPERATURE_SAMPLER_CORE_HPP
