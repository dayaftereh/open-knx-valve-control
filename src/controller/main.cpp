#include <Arduino.h>
#include <SPI.h>

#include <status_led.hpp>

#include "error.hpp"
#include "config.hpp"
#include "drives.hpp"
#include "config.hpp"
#include "temperatures.hpp"
#include "serial_message_dispatcher.hpp"

Drives drives;
StatusLed statusLed;
Temperatures temperatures;
SerialDispatcher serialDispatcher;
ConfigManager<Config> configManager;
SerialMessageDispatcher serialMessageDispatcher;

void setup()
{
    // start the i2c bus
    Wire.begin();
    // start the serial
    Serial.begin(DefaultSerialBaud);
    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    // setup the dispatcher
    bool success = serialDispatcher.setup(
        Serial, [](SerialMessage *message)
        { serialMessageDispatcher.onMessage(message); },
        UnitType::Controller,
        1);
    if (!success)
    {
        statusLed.setError(Error::SerialDispatcher);
        return;
    }

    // setup the config-manager
    success = configManager.setup(0, serialDispatcher, [](Config &config)
                                  {
                                    config.drivesAddress = 0x20;
                                    
                                    config.temperaturesUpdateRate = 10.0f; // 10s

                                    config.spiTemperature = 0.4f;

                                    config.inverseOpenClose = false;

                                    return true; }, false);
    if (!success)
    {
        statusLed.setError(Error::ConfigManager);
        return;
    }

    // get the loaded configuration
    Config *config = configManager.getConfig();

    // setup the temperatures
    success = temperatures.setup(config, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::Temperatures);
        return;
    }

    // setup the drives
    success = drives.setup(config, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::Drives);
        return;
    }

    // setup the serial-message-dispatcher
    success = serialMessageDispatcher.setup(temperatures, serialDispatcher, configManager, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::SerialMessageDispatcher);
        return;
    }
}

int counter = 0;
uint32_t timer;

void loop()
{
    drives.update();
    statusLed.update();
    temperatures.update();
    serialDispatcher.update();

    uint32_t elapsed = millis() - timer;
    if (elapsed < 10000)
    {
        return;
    }
    timer = millis();

    drives.open(counter++);
    if (counter > 3)
    {
        counter = 0;
    }

    // set all temperatures to -1
    for (int i = 0; i < TemperaturesCount; i++)
    {
        float temperature = temperatures.getTemperature(i);
        Serial.print(i);
        Serial.print(" : ");
        Serial.println(temperature, 2);
    }

    Serial.println('---');
}
