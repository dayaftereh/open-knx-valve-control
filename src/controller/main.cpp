#include <Arduino.h>

#include <status_led.hpp>
#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "error.hpp"
#include "config.hpp"
#include "drives.hpp"
#include "config.hpp"
#include "temperatures.hpp"
#include "drive_current.hpp"
#include "serial_message_dispatcher.hpp"

Drives drives;
StatusLed statusLed;
DriveCurrent driveCurrent;
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
                                    config.ina219Address = 0x40;
                                    
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

    // setup the drive-current
    success = driveCurrent.setup(config, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::DriveCurrent);
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

void loop()
{
    drives.update();
    statusLed.update();
    temperatures.update();
    driveCurrent.update();
    serialDispatcher.update();
}
