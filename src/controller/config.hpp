#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <common.hpp>

namespace Pin
{
    static constexpr Pin_t ErrorLed = D25;

    // Temperatures
    static constexpr Pin_t TemperaturesCS = D21;
    static constexpr Pin_t TemperaturesINT = D22;
    static constexpr Pin_t TemperaturesTx = D8;
    static constexpr Pin_t TemperaturesRx = D9;

    // Drives
    static constexpr Pin_t Drive1 = D10;
    static constexpr Pin_t Drive2 = D11;
    static constexpr Pin_t Drive3 = D12;
    static constexpr Pin_t Drive4 = D13;
    static constexpr Pin_t Drive5 = D14;
    static constexpr Pin_t Drive6 = D15;
    static constexpr Pin_t Drive7 = D16;
    static constexpr Pin_t Drive8 = D17;
    static constexpr Pin_t In1 = D18;
    static constexpr Pin_t In2 = D19;

    // KNX
    static constexpr Pin_t VccOK = D3;
    static constexpr Pin_t KnxOK = D20;
    static constexpr Pin_t ProgramLED = D23;
    static constexpr Pin_t ProgramButton = D24;

    // HMI
    static constexpr Pin_t Button = D2;
    static constexpr Pin_t A = D6;
    static constexpr Pin_t B = D7;
}

struct __attribute__((packed)) Config
{
    // the i2c address of the drives PCF8574
    uint8_t drivesAddress;

    // the i2c address of the INA219
    uint8_t ina219Address;

    float temperaturesUpdateRate; // the update rate to request the temperatures

    float spiTemperature; // factor to convert temperature for spi transfer

    bool inverseOpenClose;
};

#endif