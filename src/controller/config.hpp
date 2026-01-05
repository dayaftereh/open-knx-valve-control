#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <common.hpp>

namespace Pin
{
    static constexpr Pin_t IN_1 = 3; // PA7
    static constexpr Pin_t IN_2 = 4; // PB5

    static constexpr Pin_t SPI_CS = 0; // PA4

    static constexpr Pin_t ErrorLed = 13; // PC3
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