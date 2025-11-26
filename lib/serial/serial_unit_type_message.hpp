#ifndef SERIAL_UNIT_TYPE_MESSAGE_HPP
#define SERIAL_UNIT_TYPE_MESSAGE_HPP

#include <unit_type.hpp>
#include <serial_message.hpp>

struct __attribute__((packed)) SerialUnitTypeMessage: public SerialMessage
{
    UnitType unitType;
    uint8_t version;
};

#endif // SERIAL_UNIT_TYPE_MESSAGE_HPP