#ifndef ERROR_HPP
#define ERROR_HPP

#include "common.hpp"

enum class Error : uint8_t
{
    NoError = 0,
    ConfigManager,
    SerialDispatcher,
    Temperatures,
    SPISlave, // reserved legacy error code: SPI0 is disabled on PCB V1.2
    SerialMessageDispatcher,
    UartSetup,
};

#endif // ERROR_HPP