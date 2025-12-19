#include <status_led.hpp>
#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "error.hpp"
#include "config.hpp"
#include "spi-slave.hpp"
#include "temperatures.hpp"
#include "serial_message_dispatcher.hpp"

StatusLed statusLed;
Temperatures temperatures;
SerialDispatcher serialDispatcher;
ConfigManager<Config> configManager;
SerialMessageDispatcher serialMessageDispatcher;

void setup()
{
    // start the serial
    Serial.begin(DefaultSerialBaud);

    // setup the status led

    // setup the dispatcher
    bool success = serialDispatcher.setup(
        Serial, [](SerialMessage *message)
        { serialMessageDispatcher.onMessage(message); },
        UnitType::Temperature,
        1);
    if (!success)
    {
        statusLed.setError(Error::SerialDispatcher);
        return;
    }

    // setup the config-manager
    success = configManager.setup(0, serialDispatcher, [](Config &config)
                                  {
                                    config.resolution = 12; // set the percision to 9 bit

                                    config.updateRate = 5.0f; // 5s

                                    config.spiTemperature = 2.5f;

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

    // setup the spi slave
    success = SPISlave::setup(config, temperatures, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::SPISlave);
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

uint32_t timer;

void loop()
{
    statusLed.update();
    temperatures.update();
    //SPISlave::update();
    serialDispatcher.update();

    uint32_t elapsed = millis() - timer;
    if (elapsed < 10000)
    {
        return;
    }
    timer = millis();

    // set all temperatures to -1
    for (int i = 0; i < TemperaturesCount; i++)
    {
        float temperature = temperatures.getTemperature(i);
        Serial.print(i);
        Serial.print(" : ");
        Serial.println(temperature, 2);
    }
}
