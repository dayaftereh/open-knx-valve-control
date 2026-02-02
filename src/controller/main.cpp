#include <Arduino.h>

#include <knx.h>
#include <TPUart/Interface/ArduinoSerial.h>

#include "config.hpp"
#include "knxprod.hpp"

void setupKnx()
{
    // Setup the interface
    auto platform = knx.platform();
    platform.interface(new TPUart::Interface::ArduinoSerial(Serial1));

    // read address table, association table, groupobject table and parameters from eeprom
    knx.readMemory();

    // set the program-led pin
    knx.ledPin(Pin::ProgramLED);

    // set the program-button pin
    knx.buttonPin(Pin::ProgramButton);

    if (knx.configured())
    {
    }

    // start the framework.
    knx.start();
}

void setup()
{
    Serial.begin(DefaultSerialBaud);

    ArduinoPlatform::SerialDebug = &Serial;

    // setup the knx stack
    setupKnx();
}

void loop()
{
    knx.loop();

    if (!knx.configured())
    {
        return;
    }
}
