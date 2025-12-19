#include "temperature.hpp"

[[nodiscard]] bool Temperature::setup(Config *config, Pin_t pin, uint32_t seed, Print &print)
{
    this->pin = pin;
    this->print = &print;
    this->config = config;
    // create the one-wire
    this->oneWire = new OneWire(pin);
    // create the dallas temperature
    this->dallasTemperature = new DallasTemperature(this->oneWire);
    // start the dallas temperature
    this->dallasTemperature->begin();
    // change the resolution
    this->dallasTemperature->setResolution(this->config->resolution);

    this->timer = millis() + seed;
    this->temperature = DEVICE_DISCONNECTED_C;

    return true;
}

void Temperature::update()
{
    uint32_t now = millis();
    // calulcate elapsed
    uint32_t elapsed = now - this->timer;
    // calulcate update duration in millis
    uint32_t duration = uint32_t(this->config->updateRate * 1000.0);
    if (elapsed < duration)
    {
        return;
    }
    // update the timer
    this->timer = now;
    // request the temperature
    this->dallasTemperature->requestTemperatures();
    // update the temperature
    this->temperature = this->dallasTemperature->getTempCByIndex(0);
}

[[nodiscard]] bool Temperature::isConnected()
{
    return this->temperature > 0.0;
}

[[nodiscard]] float Temperature::getTemperature()
{
    return this->temperature;
}