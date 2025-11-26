#ifndef _SERIAL_MESSAGE_HPP
#define _SERIAL_MESSAGE_HPP

#include <serial_message_type.hpp>

struct __attribute__((packed)) SerialMessage
{
    // the type of the message
    SerialMessageType type;
    // the length of the message
    uint16_t length;
};

#endif // _SERIAL_MESSAGE_HPP