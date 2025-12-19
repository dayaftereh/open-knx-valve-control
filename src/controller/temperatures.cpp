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
        this->timers[i] = 10 * i;
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

    int32_t timeout = int32_t(this->config->temperaturesUpdateRate * 1000.0f);
    // request each temperature
    for (uint8_t index = 0; index < TemperaturesCount; index++)
    {
        // get current millis
        uint32_t now = millis();
        // check if the last read to old
        int32_t elapsed = int32_t(now) - int32_t(this->timers[index]);

        if (elapsed < timeout)
        {
            continue;
        }


        this->timers[index] = now;
        // read the temperature for the given index
        this->temperatures[index] = this->readTemperatureViaSPI(index);

        Serial.print(index);
        Serial.print(":s:");
        Serial.println(this->temperatures[index]);
        Serial.flush();
    }
}

[[nodiscard]] float Temperatures::readTemperatureViaSPI(uint8_t index)
{
    // pull cs low for the start
    digitalWrite(Pin::SPI_CS, false);
    SPISettings settings;
SPI.beginTransaction(settings);
  Serial.print(index);
  Serial.print("d");
    Serial.print(SPI0.DATA);
    // get the raw temperature
    byte rawTemperature = SPI.transfer(index);
    // calculate the temperatures
    float temperature = float(rawTemperature) * this->config->spiTemperature;

   
        Serial.print(":r:");
        Serial.println(rawTemperature);

        SPI.endTransaction();

    // make the pin back high
    digitalWrite(Pin::SPI_CS, true);

    return temperature;
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
