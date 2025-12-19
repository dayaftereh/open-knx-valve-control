#ifndef TEMPERATURE_HPP
#define TEMPERATURE_HPP

#include <common.hpp>

#include <OneWire.h>
#include <DallasTemperature.h>

#include "config.hpp"

class Temperature
{
public:
    [[nodiscard]] bool setup(Config *config, Pin_t pin, uint32_t seed, Print &print);

    void update();

    [[nodiscard]] bool isConnected();
    
    [[nodiscard]] float getTemperature();

private:
    uint32_t timer;

    float temperature;

    Pin_t pin;

    Print *print;
    Config *config;

    OneWire *oneWire;
    DallasTemperature *dallasTemperature;
};

#endif // TEMPERATURE_HPP