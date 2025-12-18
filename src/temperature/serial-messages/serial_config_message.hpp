#ifndef _SERIAL_CONFIG_MESSAGE_HPP
#define _SERIAL_CONFIG_MESSAGE_HPP

#include <Arduino.h>

#include "../config.hpp"
#include "serial_message.hpp"

typedef struct __attribute__((packed)) : public SerialMessage
{
    Config config;
} SerialConfigMessage;

#endif // _SERIAL_CONFIG_MESSAGE_H