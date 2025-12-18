#include "temperatures.hpp"

[[nodiscard]] bool Temperatures::setup(Config *config, Print &print)
{
    this->config = config;
    this->print = &print;

    // swap the spi
    bool success = SPI.swap(1);
    if (!success)
    {
        return false;
    }

    // set all temperatures to -1
    for (int i = 0; i < TemperaturesCount; i++)
    {
        this->temperatures[i] = -1.0f;
    }

    // set cs pin to output
    pinMode(Pin::SPI_CS, OUTPUT);

    // make the pin high
    digitalWrite(Pin::SPI_CS, true);

    // start the spi
    SPI.begin();

    return true;
}

void Temperatures::update()
{
    // get current millis
    uint32_t now = millis();
    // claculate elapsed
    uint32_t elapsed = now - this->timer;
    // caluclate timeout
    uint32_t timeout = uint32_t(this->config->temperaturesUpdateRate * 1000.0);
    // check if timeout reached
    if (elapsed < timeout)
    {
        return;
    }
    // update the timer
    this->timer = now;
    // read the current temperatures
    this->readTemperaturesViaSPI();
}

void Temperatures::readTemperaturesViaSPI()
{
    // pull cs low for the start
    digitalWrite(Pin::SPI_CS, false);

    // request each temperature
    for (uint8_t index = 0; index < TemperaturesCount; index++)
    {
        // get the raw temperature
        byte rawTemperature = SPI.transfer(index);
        // calculate the temperatures
        this->temperatures[index] = float(rawTemperature) * this->config->spiTemperature;
    }

    // make the pin back high
    digitalWrite(Pin::SPI_CS, true);
}

[[nodiscard]] float Temperatures::getTemperature(uint8_t index)
{
    if (index < 0 || index >= TemperaturesCount)
    {
        return 0.0f;
    }

    float value = this->temperatures[index];
    return value;
}
