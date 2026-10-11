#ifndef OPENKNX_NATIVE_MOCK_ARDUINO_HPP
#define OPENKNX_NATIVE_MOCK_ARDUINO_HPP

#include "common.hpp"
#include <deque>
#include <stddef.h>
#include <stdint.h>

// In-memory fake UART. RX is injected by tests; writes append directly to TX.
// No host serial port is ever opened.
class HardwareSerial : public Print
{
public:
    std::deque<uint8_t> rx;
    std::deque<uint8_t> tx;

    int available() { return static_cast<int>(rx.size()); }

    int read()
    {
        if (rx.empty()) return -1;
        const uint8_t value = rx.front();
        rx.pop_front();
        return value;
    }

    int availableForWrite() { return writable_; }

    size_t write(const uint8_t* bytes, size_t length)
    {
        if (writable_ <= 0) return 0;
        const size_t allowed = length < static_cast<size_t>(writable_)
                            ? length : static_cast<size_t>(writable_);
        for (size_t i = 0; i < allowed; ++i)
            tx.push_back(bytes[i]);
        return allowed;
    }

    size_t write(uint8_t byte) { return write(&byte, 1); }
    void inject(const uint8_t* bytes, size_t length)
    {
        for (size_t i = 0; i < length; ++i)
            rx.push_back(bytes[i]);
    }

    void setWritable(int capacity) { writable_ = capacity; }
    bool swap(uint8_t) { return true; }
    void begin(uint32_t) {}

private:
    int writable_ = 64;
};

#endif
