#include <status_led.hpp>
#include <config_manager.hpp>
#include <serial_dispatcher.hpp>

#include "error.hpp"
#include "config.hpp"
#include "temperatures.hpp"
#include "serial_message_dispatcher.hpp"

StatusLed statusLed;
Temperatures temperatures;
SerialDispatcher serialDispatcher;
ConfigManager<Config> configManager;
SerialMessageDispatcher serialMessageDispatcher;

void setup()
{
    // megaTinyCore ATtiny3216 default USART0 PB2/PB3:
    // this remains the legacy local debug/config link in KNX013.
    // KNX014 will explicitly move USART0 to PA1/PA2 for RP2040 UART.
    Serial.begin(DefaultSerialBaud);
    delay(1000);

    bool success = serialDispatcher.setup(
        Serial, [](SerialMessage *message)
        { serialMessageDispatcher.onMessage(message); },
        UnitType::Temperature, 1);
    if (!success)
    {
        statusLed.setError(Error::SerialDispatcher);
        return;
    }

    success = configManager.setup(0, serialDispatcher, [](Config &config)
    {
        config.resolution = 12;       // DS18B20 12 bit; max 750 ms conversion
        config.updateRate = 10.0f;   // default: one sample / 10 s / probe
        config.spiTemperature = 2.5f; // deprecated layout-preserving field
        return true;
    }, false);
    if (!success)
    {
        statusLed.setError(Error::ConfigManager);
        return;
    }

    Config *config = configManager.getConfig();
    success = temperatures.setup(config, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::Temperatures);
        return;
    }

    // KNX013: intentionally NO SPI0 slave initialization.
    // The PCB V1.2 leaves ATtiny PA3/SPI0_SCK unconnected to RP2040.
    // Current firmware must never drive PA1/PA2 as SPI if they will be
    // selected for the RP2040 temperature UART in KNX014.

    success = serialMessageDispatcher.setup(
        temperatures, serialDispatcher, configManager, serialDispatcher);
    if (!success)
    {
        statusLed.setError(Error::SerialMessageDispatcher);
        return;
    }
}

void loop()
{
    statusLed.update();
    temperatures.update(); // bounded short bus operations; no 750 ms delay
    serialDispatcher.update();
}
