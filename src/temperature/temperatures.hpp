#ifndef KNX_TEMPERATURES_HPP
#define KNX_TEMPERATURES_HPP

#include "temperature.hpp"

static constexpr uint8_t TemperaturesCount = 9;

class Temperatures
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);
    void update();

    // Pure in-memory copy: no 1-Wire transactions, suitable for the UART
    // transport implementation in KNX014.
    [[nodiscard]] TemperatureSampler::Snapshot getSnapshot(uint8_t index,
                                                            uint32_t now) const;

    // Historical API, retained for source compatibility; never returns
    // synthetic 0 C for missing channels.
    [[nodiscard]] float getTemperature(uint8_t index) const;

private:
    Temperature channels_[TemperaturesCount];
};

#endif // KNX_TEMPERATURES_HPP
