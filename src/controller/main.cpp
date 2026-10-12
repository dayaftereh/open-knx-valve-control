#include <Arduino.h>

#include <knx.h>
#include <TPUart/Interface/ArduinoSerial.h>

#include "config.hpp"
#include "knxprod.hpp"
#include "temperature_bridge.hpp"
#include "temperature_publisher.hpp"

TemperatureBridge temperatureBridge;
TemperaturePublisher temperaturePublisher;

void setupKnx()
{
    // KNX TP remains on the independent Serial1/UART0 interface.
    auto platform = knx.platform();
    platform.interface(new TPUart::Interface::ArduinoSerial(Serial1));

    knx.readMemory();
    knx.ledPin(Pin::ProgramLED);
    knx.buttonPin(Pin::ProgramButton);
    knx.start();
}

void setupTemperatureLink()
{
    // RP2040 GPIO8 (UART1 TX) -> ATtiny PA2 RX, GPIO9 (UART1 RX)
    // <- ATtiny PA1 TX. Configure pins before starting the port.
    const bool txReady = Serial2.setTX(Pin::TemperaturesTx);
    const bool rxReady = Serial2.setRX(Pin::TemperaturesRx);
    if (!txReady || !rxReady)
    {
        Serial.println("Temperature UART1 pin setup failed");
        return; // No polling or unconfigured UART activity.
    }
    Serial2.begin(TemperatureBridge::Baud);
    temperatureBridge.setup(Serial2);
}

void setup()
{
    Serial.begin(DefaultSerialBaud);
    ArduinoPlatform::SerialDebug = &Serial;

    setupTemperatureLink();
    setupKnx();
    temperaturePublisher.begin(millis());
}

void loop()
{
    knx.loop();

    // UART remains active for internal diagnosis before ETS commissioning.
    temperatureBridge.update();

    if (!knx.configured())
        return;

    // KNX015: transmit only valid cached T0..T8 and quality diagnostics;
    // at most one KNX GroupObject per loop, bounded by ETS parameters.
    temperaturePublisher.update(temperatureBridge, millis());
}
