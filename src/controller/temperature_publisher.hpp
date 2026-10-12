#ifndef OPENKNX_CONTROLLER_TEMPERATURE_PUBLISHER_HPP
#define OPENKNX_CONTROLLER_TEMPERATURE_PUBLISHER_HPP

#include <Arduino.h>
#include <temperature_telemetry_policy.hpp>
#include "temperature_bridge.hpp"

// DPT9.001 KNX telemetry ONLY; no actuator enable, position, or homing.
class TemperaturePublisher
{
public:
    void begin(uint32_t now);
    void update(const TemperatureBridge& bridge, uint32_t now);

    uint16_t acceptedConversions() const { return accepted_; }
    uint16_t rejectedConversions() const { return rejected_; }

private:
    TemperatureTelemetry::Scheduler schedule_;
    uint16_t accepted_ = 0;
    uint16_t rejected_ = 0;
};

#endif // OPENKNX_CONTROLLER_TEMPERATURE_PUBLISHER_HPP
