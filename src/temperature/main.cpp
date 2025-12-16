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

byte volatile data;
bool volatile updated = true;

void setup()
{
    delay(4000);

    // start the serial
    Serial.begin(DefaultSerialBaud);

    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    SPI0.CTRLA = (SPI_ENABLE_bm);              // ENABLE Spi in slave mode
    SPI0.INTCTRL = (SPI_IE_bm | SPI_RXCIE_bm); // Enable Interrupts and trigger on recived

    pinMode(Pin::SPI_CS, INPUT);
    pinMode(Pin::SPI_SCK, INPUT);
    pinMode(Pin::SPI_MOSI, INPUT);
    pinMode(Pin::SPI_MISO, OUTPUT);

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
    Serial.println("ss");
}

void loop()
{

    statusLed.update();
    if (updated)
    {
        updated = false;
        Serial.println(data);
    }

    // Serial.println(SPI0.INTFLAGS & SPI_RXCIF_bm, BIN);

    // temperatures.update();
    // serialDispatcher.update();
}

ISR(SPI0_INT_vect)
{
    if ((SPI0.INTFLAGS & SPI_RXCIF_bm) == SPI_RXCIF_bm)
    {
        data = SPI0.DATA;
        SPI0.DATA = data * 10;
        updated=true;
    }
}