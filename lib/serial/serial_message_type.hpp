#ifndef SERIAL_MESSAGE_TYPE
#define SERIAL_MESSAGE_TYPE

#include <common.hpp>

enum class SerialMessageType : uint8_t
{
    Unknown = 0,
    Print,
    UnitType,
};

#endif // SERIAL_MESSAGE_TYPE