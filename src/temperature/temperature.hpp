#ifndef KNX_TEMPERATURE_CHANNEL_HPP
#define KNX_TEMPERATURE_CHANNEL_HPP

#include <common.hpp>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "config.hpp"
#include "sampler_core.hpp"

class Temperature
{
public:
    [[nodiscard]] bool setup(Config *config, Pin_t pin, uint32_t staggerMs, Print &print);
    void update();

    // Non-blocking, in-memory status/last-value view; KNX014 owns UART frames.
    [[nodiscard]] TemperatureSampler::Snapshot getSnapshot(uint32_t now) const;

    // Legacy convenience methods. No fake 0 C on missing/faulted samples.
    [[nodiscard]] bool isConnected() const;
    [[nodiscard]] float getTemperature() const;

private:
    [[nodiscard]] uint32_t periodMs() const;
    [[nodiscard]] uint8_t selectedResolution() const;
    [[nodiscard]] bool discoverSensor(bool &parasitePowered);

    Config *config_ = nullptr;
    OneWire oneWire_;
    DallasTemperature dallas_;
    DeviceAddress address_{};
    uint8_t resolution_ = 12;
    TemperatureSampler::Core sampler_;
};

#endif // KNX_TEMPERATURE_CHANNEL_HPP
