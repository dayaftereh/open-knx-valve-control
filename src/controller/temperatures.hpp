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

    void readTemperaturesViaSPI();
  
    Print *print;
    Config *config;

    uint32_t timer;

    float temperatures[TemperaturesCount];
};

#endif // TEMPERATURES_HPP