#ifndef TEMPERATURE_CONFIG_HPP
#define TEMPERATURE_CONFIG_HPP

#include <common.hpp>

// Correct Arduino pin IDs for the actually routed ATtiny3216 SOIC-20 on PCB V1.2.
// See docs/FIRMWARE_SOFTWARE_FIRST.md and tools/audit_temperature_bridge.py.
namespace Pin
{
    static constexpr Pin_t T0 = PIN_PA5; // PCB T0, supply flow
    static constexpr Pin_t T1 = PIN_PA6; // PCB T1, return loop M1
    static constexpr Pin_t T2 = PIN_PA7; // PCB T2, return loop M2
    static constexpr Pin_t T3 = PIN_PB5; // PCB T3, return loop M3
    static constexpr Pin_t T4 = PIN_PB4; // PCB T4, return loop M4
    static constexpr Pin_t T5 = PIN_PB1; // PCB T5, return loop M5
    static constexpr Pin_t T6 = PIN_PC1; // PCB T6, return loop M6
    static constexpr Pin_t T7 = PIN_PC0; // PCB T7, return loop M7
    static constexpr Pin_t T8 = PIN_PB0; // PCB T8, return loop M8

    static constexpr Pin_t ErrorLed = PIN_PC3;

    // PCB V1.2 routes PA1/PA2 UART to the RP2040, but does not connect
    // ATtiny SPI0 SCK PA3. The historical SPI0 slave is NOT initialized.
    // UART/PORTMUX and CS/T_INT transport are the responsibility of KNX014.
}

// Retain the existing serial-config layout for backwards compatibility.
// In KNX013 the SPI scale field is intentionally deprecated/unconsumed.
struct __attribute__((packed)) Config
{
    uint8_t resolution;     // DS18B20, 9..12 bits, default 12
    float updateRate;       // seconds per sensor, default 10
    float spiTemperature;   // legacy, not used by the new sampler
};

#endif // TEMPERATURE_CONFIG_HPP
