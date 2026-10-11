#ifndef OPENKNX_TEMPERATURE_LINK_HPP
#define OPENKNX_TEMPERATURE_LINK_HPP

#include <Arduino.h>
#include <temperature_protocol.hpp>
#include "temperatures.hpp"

// ATtiny3216 UART responder on Serial/USART0 ALT1 PA1 TX / PA2 RX.
// No OneWire access occurs while handling a request: just copy RAM snapshots.
class TemperatureLink
{
public:
    bool setup(HardwareSerial& uart, Temperatures& temperatures);
    void update();

private:
    void startResponse(uint8_t sequence, uint32_t now);

    HardwareSerial* uart_ = nullptr;
    Temperatures* temperatures_ = nullptr;
    TemperatureProtocol::Parser parser_;
    uint8_t tx_[TemperatureProtocol::MaxFrameBytes] = {};
    uint8_t txLength_ = 0;
    uint8_t txOffset_ = 0;
    uint32_t lastReceivedByteAt_ = 0;
};

#endif // OPENKNX_TEMPERATURE_LINK_HPP
