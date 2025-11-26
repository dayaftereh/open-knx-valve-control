#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <common.hpp>

namespace Pin
{
    static constexpr Pin_t T0 = 0;        // PA4
    static constexpr Pin_t T1 = 1;        // PA5
    static constexpr Pin_t T2 = 2;        // PA6
    static constexpr Pin_t T3 = 3;        // PA7
    static constexpr Pin_t T4 = 4;        // PB5
    static constexpr Pin_t T5 = 5;        // PB4
    static constexpr Pin_t T6 = 8;        // PB1
    static constexpr Pin_t T7 = 11;       // PC1
    static constexpr Pin_t T8 = 10;       // PC0
    static constexpr Pin_t SPI_CS = 12;   // PC2
    static constexpr Pin_t ErrorLed = 13; // PC3
}

struct __attribute__((packed)) Config
{
    uint8_t resolution;
    float updateRate; // s
};

#endif