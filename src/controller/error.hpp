#ifndef ERROR_HPP
#define ERROR_HPP

#include "common.hpp"

enum class Error : uint8_t
{
    NoError = 0,
    ConfigManager,
    SerialDispatcher,
    Temperatures,
    SerialMessageDispatcher,
};

#endif // ERROR_HPP