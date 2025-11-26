#ifndef COMMON_HPP
#define COMMON_HPP

#include <Arduino.h>

using Pin_t = uint8_t;
using Crc8_t = uint8_t;
using EepromAddress_t = uint16_t;

static constexpr uint32_t DefaultSerialBaud = 115200;

#endif // COMMON_HPP