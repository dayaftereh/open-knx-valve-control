#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <common.hpp>

namespace Pin
{

    static constexpr Pin_t SPI_CS = 0; // PA4

    static constexpr Pin_t ErrorLed = 13; // PC3
}

struct __attribute__((packed)) Config
{
    float temperaturesUpdateRate; // the update rate to request the temperatures

    float spiTemperature; // factor to convert temperature for spi transfer
};

#endif