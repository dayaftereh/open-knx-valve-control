#include <status_led.hpp>
#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "error.hpp"
#include "config.hpp"
#include "temperatures.hpp"

#include <SPI.h>

StatusLed statusLed;
Temperatures temperatures;
SerialDispatcher serialDispatcher;
ConfigManager<Config> configManager;

SPIClass spi;
SPISettings settings;

void setup()
{
    // start the serial
    Serial.begin(DefaultSerialBaud);

    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    spi.pins(Pin::MOSI_CS, Pin::MISO_CS, Pin::SCK_CS, Pin::SPI_CS);

    register8_t a = SPI0.CTRLA;
    spi.begin();

    SPI0.CTRLA = a | (SPI_ENABLE_bm);

    /*// setup the dispatcher
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
    }*/

    statusLed.setError(10);
}

void loop()
{
    statusLed.update();
    // temperatures.update();
    // serialDispatcher.update();
}