#include "temperatures.hpp"

[[nodiscard]] bool Temperatures::setup(Config *config, Print &print)
{
    // These are PCB V1.2 terminal labels, not a "room air" sensor array.
    // T0 is common supply; T1..T8 are returns for motor loops M1..M8.
    const Pin_t pins[TemperaturesCount] = {
        Pin::T0, Pin::T1, Pin::T2, Pin::T3, Pin::T4,
        Pin::T5, Pin::T6, Pin::T7, Pin::T8
    };

    for (uint8_t index = 0; index < TemperaturesCount; ++index)
    {
        // Discovery and measurements staggered 500 ms apart to avoid
        // synchronous bus scans; each 1-Wire channel has its own bus.
        if (!channels_[index].setup(config, pins[index],
                                    static_cast<uint32_t>(index) * 500U, print))
            return false;
    }
    return true;
}

void Temperatures::update()
{
    for (uint8_t index = 0; index < TemperaturesCount; ++index)
        channels_[index].update();
}

[[nodiscard]] TemperatureSampler::Snapshot
Temperatures::getSnapshot(uint8_t index, uint32_t now) const
{
    if (index >= TemperaturesCount)
        return TemperatureSampler::Snapshot{};
    return channels_[index].getSnapshot(now);
}

[[nodiscard]] float Temperatures::getTemperature(uint8_t index) const
{
    if (index >= TemperaturesCount)
        return DEVICE_DISCONNECTED_C;
    return channels_[index].getTemperature();
}
