#include "temperature_link.hpp"

bool TemperatureLink::setup(HardwareSerial& uart, Temperatures& temperatures)
{
    uart_ = &uart;
    temperatures_ = &temperatures;
    parser_.reset();
    txLength_ = 0;
    txOffset_ = 0;
    lastReceivedByteAt_ = millis();
    return true;
}

void TemperatureLink::startResponse(uint8_t sequence, uint32_t now)
{
    TemperatureProtocol::Snapshot snapshot{};
    snapshot.uptimeMs = now;
    snapshot.moduleStatus = 0;

    for (uint8_t i = 0; i < TemperatureProtocol::Channels; ++i)
    {
        const auto source = temperatures_->getSnapshot(i, now);
        auto &dest = snapshot.channels[i];
        dest.centiC = source.centiC;
        dest.ageSeconds = source.ageSeconds;
        dest.flags = source.flags;
        dest.fault = static_cast<uint8_t>(source.fault);
    }
    const size_t count = TemperatureProtocol::encodeSnapshot(
        snapshot, sequence, tx_, sizeof(tx_));
    txLength_ = static_cast<uint8_t>(count);
    txOffset_ = 0;
}

void TemperatureLink::update()
{
    if (!uart_ || !temperatures_)
        return;

    // Drop incomplete/stalled byte streams; never block waiting for bytes.
    const uint32_t now = millis();
    if (parser_.inProgress() &&
        static_cast<uint32_t>(now - lastReceivedByteAt_) >=
            TemperatureProtocol::MaxInterByteGapMs)
        parser_.reset();

    // Bounded RX work, even if the peer floods the line.
    for (uint8_t budget = 0; budget < 24 && uart_->available() > 0; ++budget)
    {
        const int value = uart_->read();
        if (value < 0)
            break;
        lastReceivedByteAt_ = millis();
        TemperatureProtocol::Frame frame{};
        if (parser_.feed(static_cast<uint8_t>(value), frame))
        {
            if (frame.type == TemperatureProtocol::GetSnapshot &&
                frame.length == 0 && txLength_ == 0)
                startResponse(frame.sequence, millis());
        }
    }

    // Send bounded chunks from the prepared 67-byte reply. No flush() or
    // multi-millisecond busy-wait, so the 1-Wire scheduler still runs.
    if (txLength_ == 0)
        return;
    int available = uart_->availableForWrite();
    if (available <= 0)
        return;
    uint8_t send = static_cast<uint8_t>(txLength_ - txOffset_);
    if (send > 16)
        send = 16;
    if (send > available)
        send = static_cast<uint8_t>(available);
    txOffset_ = static_cast<uint8_t>(
        txOffset_ + uart_->write(tx_ + txOffset_, send));
    if (txOffset_ >= txLength_)
    {
        txOffset_ = 0;
        txLength_ = 0;
    }
}
