#ifndef MOCK_OPENKNX_COMMON_HPP
#define MOCK_OPENKNX_COMMON_HPP
#include <stdint.h>

using Pin_t = uint8_t;
class Print {};
uint32_t millis();

// Exact megaTinyCore txy6 Arduino numbering for PCB V1.2 sensor pins.
static constexpr Pin_t PIN_PA5 = 1;
static constexpr Pin_t PIN_PA6 = 2;
static constexpr Pin_t PIN_PA7 = 3;
static constexpr Pin_t PIN_PB5 = 4;
static constexpr Pin_t PIN_PB4 = 5;
static constexpr Pin_t PIN_PB1 = 8;
static constexpr Pin_t PIN_PC1 = 11;
static constexpr Pin_t PIN_PC0 = 10;
static constexpr Pin_t PIN_PB0 = 9;
static constexpr Pin_t PIN_PC3 = 13;
#endif
