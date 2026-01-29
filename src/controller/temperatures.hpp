#ifndef TEMPERATURES_HPP
#define TEMPERATURES_HPP

#include <SPI.h>

#include "config.hpp"

#define TemperaturesCount 9

class Temperatures
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);

    void update();

    [[nodiscard]] float getTemperature(uint8_t index);

private:
    [[nodiscard]] float readTemperatureViaSPI(uint8_t index);

    int index;

    Print *print;
    Config *config;

    uint32_t timers[TemperaturesCount];
    float temperatures[TemperaturesCount];
};

#endif // TEMPERATURES_HPP