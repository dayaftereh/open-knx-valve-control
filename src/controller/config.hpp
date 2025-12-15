#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <common.hpp>

namespace Pin
{    

    static constexpr Pin_t SPI_CS = 12;  // PC2 
    
    static constexpr Pin_t ErrorLed = 13; // PC3
}

struct __attribute__((packed)) Config
{
    uint8_t resolution;
    float updateRate; // s
};

#endif