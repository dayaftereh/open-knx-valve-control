#include "temperature_publisher.hpp"

#include <knx.h>
#include "knxprod.hpp"

void TemperaturePublisher::begin(uint32_t now)
{
    schedule_.begin(now);
    accepted_ = 0;
    rejected_ = 0;
}

void TemperaturePublisher::update(const TemperatureBridge& bridge, uint32_t now)
{
    // Do not send if no valid ETS application is commissioned. The existing
    // P19 toggle owns the nine sensor KOs and both diagnostics.
    if (!knx.configured())
        return;

    TemperatureTelemetry::Settings settings{};
    settings.enabled = ParamPrePostTemperaturesOutput;
    settings.periodicSeconds = ParamTemperatureSendIntervalSeconds;
    settings.changeDeltaCenti = ParamTemperatureChangeThresholdCenti;

    TemperatureTelemetry::Inputs input{};
    input.online = bridge.online(now);
    if (input.online && bridge.hasSnapshot())
    {
        const auto& source = bridge.lastSnapshot();
        for (uint8_t i = 0; i < TemperatureTelemetry::Channels; ++i)
        {
            if (!bridge.channelValid(i, now))
                continue;
            // The transport knows whether the last temperature is usable.
            // Never substitute zero when a sensor is missing or stale.
            if (bridge.ageSeconds(i, now) == 0xFFFFU)
                continue;
            input.validMask |= static_cast<uint16_t>(1U << i);
            input.centiC[i] = source.channels[i].centiC;
        }
    }

    // One bounded proposal per loop. The policy shares its intertelegram
    // throttle among temperatures and quality/status diagnostic objects.
    const auto proposal = schedule_.select(now, settings, input);
    if (proposal.kind == TemperatureTelemetry::Kind::None)
        return;

    bool written = false;
    switch (proposal.kind)
    {
    case TemperatureTelemetry::Kind::Temperature:
    {
        const uint16_t ko = static_cast<uint16_t>(KoT0 + proposal.channel);
        const float temperature = static_cast<float>(proposal.centiC) / 100.0f;
        written = knx.getGroupObject(ko).value(temperature, DPT_Value_Temp);
        break;
    }
    case TemperatureTelemetry::Kind::LinkOnline:
        written = knx.getGroupObject(KoTemperatureBridgeOnline)
                      .value(proposal.online, DPT_Bool);
        break;
    case TemperatureTelemetry::Kind::ValidMask:
        written = knx.getGroupObject(KoTemperatureValidMask)
                      .value(proposal.mask, DPT_Value_2_Ucount);
        break;
    case TemperatureTelemetry::Kind::None:
        break;
    }

    if (written)
    {
        schedule_.commit(proposal, now);
        ++accepted_;  // accepted by KNX library; NOT a bus ACK
    }
    else
        ++rejected_; // retry on a later loop, without advancing schedule
}
