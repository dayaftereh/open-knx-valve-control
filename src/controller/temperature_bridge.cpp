#include "temperature_bridge.hpp"

void TemperatureBridge::setup(SerialUART &uart)
{
    uart_ = &uart;
    client_.begin(millis());
}

void TemperatureBridge::update()
{
    if (!uart_)
        return;

    const uint32_t now = millis();
    client_.tick(now);

    // A 67-byte snapshot can arrive across multiple loop iterations.
    // Limit the receive work and preserve one KNX loop per iteration.
    for (uint8_t i = 0; i < 48 && uart_->available() > 0; ++i)
    {
        const int value = uart_->read();
        if (value < 0)
            break;
        client_.feed(static_cast<uint8_t>(value), millis());
    }

    // Arduino-Pico SerialUART::availableForWrite() returns a boolean
    // readiness indication (0/1), not the free TX FIFO byte count.
    // A count-based threshold of 8 suppresses every request.
    if (uart_->availableForWrite() <= 0)
        return;
    uint8_t request[8]{};
    const size_t count = client_.prepareRequest(millis(), request,
                                                sizeof(request));
    if (count)
        uart_->write(request, count);
}
