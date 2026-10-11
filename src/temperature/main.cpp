#include <Arduino.h>
#include <status_led.hpp>
#include <config_manager.hpp>

#include "error.hpp"
#include "config.hpp"
#include "temperatures.hpp"
#include "temperature_link.hpp"

StatusLed statusLed;
Temperatures temperatures;
TemperatureLink temperatureLink;
ConfigManager<Config> configManager;

void setup()
{
    // ATtiny3216 USART0 default PB2/PB3 is only the historical debug port.
    // PCB V1.2 connects USART0 ALT1 PA1(TX) -> RP GPIO9(RX) and
    // PA2(RX) <- RP GPIO8(TX), so switch before starting the UART.
    if (!Serial.swap(1))
    {
        statusLed.setError(Error::UartSetup);
        return;
    }
    Serial.begin(115200);

    // Keep the existing CRC-protected EEPROM configuration layout.
    // Do NOT attach the legacy, UNFRAMED SerialDispatcher to this UART:
    // it would interpret the CRC-framed temperature protocol as commands.
    const bool configReady = configManager.setup(
        0, Serial, [](Config &config) {
            config.resolution = 12;       // DS18B20 12-bit
            config.updateRate = 10.0f;    // one sample / 10 seconds
            config.spiTemperature = 2.5f; // retained layout, no longer used
            return true;
        }, false);
    if (!configReady)
    {
        statusLed.setError(Error::ConfigManager);
        return;
    }

    Config *config = configManager.getConfig();
    if (!temperatures.setup(config, Serial))
    {
        statusLed.setError(Error::Temperatures);
        return;
    }
    if (!temperatureLink.setup(Serial, temperatures))
    {
        statusLed.setError(Error::UartSetup);
        return;
    }
}

void loop()
{
    statusLed.update();
    temperatures.update();    // nine nonblocking conversion schedulers
    temperatureLink.update(); // UART requests answered from RAM snapshots
}
