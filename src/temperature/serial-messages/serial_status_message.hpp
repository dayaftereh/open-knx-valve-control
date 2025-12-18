#ifndef _SERIAL_STATUS_MESSAGE_HPP
#define _SERIAL_STATUS_MESSAGE_HPP

#include <Arduino.h>

#include "../config.hpp"
#include "serial_message.hpp"

typedef struct __attribute__((packed)) : public SerialMessage
{
    Config config;
} SerialStatusMessage;

#endif // _SERIAL_STATUS_MESSAGE_HPP