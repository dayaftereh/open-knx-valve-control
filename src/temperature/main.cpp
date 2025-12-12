#include <status_led.hpp>
#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "error.hpp"
#include "config.hpp"
#include "temperatures.hpp"

StatusLed statusLed;
Temperatures temperatures;
SerialDispatcher serialDispatcher;
ConfigManager<Config> configManager;

void setup()
{
    // start the serial
    Serial.begin(DefaultSerialBaud);

    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    // setup the dispatcher
    bool success = serialDispatcher.setup(
        Serial, [](SerialMessage *message) {},
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
                                    config.resolution = 9; // set the percision to 9 bit

                                    config.updateRate = 5.0f; // 5s                                    
                                    
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
}

void loop()
{
    statusLed.update();
    temperatures.update();
    serialDispatcher.update();
}