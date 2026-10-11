#ifndef OPENKNX_CONTROLLER_TEMPERATURE_BRIDGE_HPP
#define OPENKNX_CONTROLLER_TEMPERATURE_BRIDGE_HPP

#include <Arduino.h>
#include <SerialUART.h>
#include <temperature_client_core.hpp>

// RP2040 UART1/Serial2 temperature receiver, independent of KNX UART0.
// The KNX015 slice will consume cached values; this module never sends KNX.
class TemperatureBridge
{
public:
    static constexpr uint32_t Baud = 115200U;

    void setup(SerialUART &uart);
    void update();

    bool online(uint32_t now) const { return client_.online(now); }
    bool channelValid(uint8_t index, uint32_t now) const
    {
        return client_.channelValid(index, now);
    }
    uint16_t ageSeconds(uint8_t index, uint32_t now) const
    {
        return client_.channelAgeSeconds(index, now);
    }
    const TemperatureProtocol::Snapshot &lastSnapshot() const
    {
        return client_.lastSnapshot();
    }
    bool hasSnapshot() const { return client_.hasSnapshot(); }
    uint16_t timeoutCount() const { return client_.timeouts(); }
    uint16_t rejectedCount() const { return client_.rejectedResponses(); }

private:
    SerialUART *uart_ = nullptr;
    TemperatureProtocol::ClientCore client_;
};

#endif // OPENKNX_CONTROLLER_TEMPERATURE_BRIDGE_HPP
