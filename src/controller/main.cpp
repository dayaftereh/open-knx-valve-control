#include <Arduino.h>
#include <SPI.h>

#include <status_led.hpp>

#include "config.hpp"

StatusLed statusLed;

uint32_t timer;
uint32_t count;

SPISettings settings;

void setup()
{
    Serial.begin(DefaultSerialBaud);

    // setup the status led
    statusLed.setup(Pin::ErrorLed);

    bool success = SPI.swap(1);
    if (!success)
    {
        statusLed.setError(1);
        return;
    }

    pinMode(Pin::SPI_CS, OUTPUT);
    digitalWrite(Pin::SPI_CS, true);

    SPI.begin();
}

byte data = 0;

void readAndWriteDataViaSPI()
{
    //SPI.beginTransaction(settings);

    uint32_t start = millis();
    digitalWrite(Pin::SPI_CS, false);

    byte lastData = SPI.transfer(data);
    data++;

    digitalWrite(Pin::SPI_CS, true);

    uint32_t elapsed = millis() - start;

    Serial.print(data);
    Serial.print(" * 10 = ");
    Serial.print(lastData);
    Serial.print(", ");
    Serial.println(elapsed);

   // SPI.endTransaction();
}

void loop()
{
    statusLed.update();

    uint32_t now = millis();
    uint32_t elapsed = now - timer;
    if (elapsed > 2000)
    {
        timer = now;
        readAndWriteDataViaSPI();
    }
}