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

bool volatile hasSPI;

void ISR_SPI_CS()
{
   SPI0.INTCTRL |= (SPI_)
}

void setup()
{
    delay(4000);

    // start the serial
    Serial.begin(DefaultSerialBaud);

    //SPI.pins(Pin::MOSI_CS, Pin::MISO_CS, Pin::SCK_CS, Pin::SPI_CS);

    SPI0.CTRLA

    //SPI.begin();

    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    // spi.pins(Pin::MOSI_CS, Pin::MISO_CS, Pin::SCK_CS, Pin::SPI_CS);

    register8_t a = SPI0.CTRLA;
    register8_t b = SPI0.CTRLB;

    // spi.begin();

    SPI0.CTRLA = a | (SPI_ENABLE_bm);
    SPI0.CTRLB = b; // | (SPI_BUFWR_bm);

    Serial.println(SPI0.CTRLA, BIN);
    Serial.println(SPI0.CTRLB, BIN);

    hasSPI = false;

    int interruptForPin = digitalPinToInterrupt(Pin::SPI_CS);
    attachInterrupt(interruptForPin, ISR_SPI_CS, FALLING);

    pinMode(Pin::MISO_CS, OUTPUT);
    pinMode(Pin::SCK_CS, INPUT);
    pinMode(Pin::MOSI_CS, INPUT);
    pinMode(Pin::SPI_CS, INPUT);

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

byte lastData;

void readAndSendSPI()
{
    asm volatile("nop");
    int c = 0;
    while (((SPI0.INTFLAGS & SPI_RXCIF_bm) == 0) && c < 10000)
    {
        Serial.println(SPI0.INTFLAGS, BIN);
    }
    byte data = SPI0.DATA;
    SPI0.DATA = lastData * 10;
    Serial.print(data);
    Serial.print(", ");
    Serial.println(lastData * 10);
    lastData = data;
}

void loop()
{
    if ((SPI0.INTFLAGS & SPI_IF_bm) == 1)
    {
        Serial.println(SPI0.INTFLAGS, BIN);
    }
    statusLed.update();
    

    // temperatures.update();
    // serialDispatcher.update();
}