#ifndef OPENKNX_TEMPERATURE_CLIENT_CORE_HPP
#define OPENKNX_TEMPERATURE_CLIENT_CORE_HPP

#include <stddef.h>
#include <stdint.h>
#include "temperature_protocol.hpp"

// Platform-independent RP2040 request/response state, tested without a board.
namespace TemperatureProtocol
{
constexpr uint32_t PollEveryMs = 3000U;
constexpr uint32_t ReplyTimeoutMs = 400U;
constexpr uint32_t OfflineAfterMs = 15000U;

inline bool timeElapsed(uint32_t now, uint32_t since, uint32_t interval)
{
    return static_cast<uint32_t>(now - since) >= interval;
}

inline bool timeDue(uint32_t now, uint32_t deadline)
{
    return static_cast<uint32_t>(now - deadline) < 0x80000000UL;
}

class ClientCore
{
public:
    void begin(uint32_t now)
    {
        parser_.reset();
        snapshot_ = Snapshot{};
        hasSnapshot_ = false;
        pending_ = false;
        sequence_ = 0;
        nextRequestAt_ = now;
        lastRequestedAt_ = now;
        lastReceivedAt_ = 0;
        lastByteAt_ = now;
        timeouts_ = 0;
        rejectedResponses_ = 0;
    }

    void tick(uint32_t now)
    {
        if (pending_ && timeElapsed(now, lastRequestedAt_, ReplyTimeoutMs))
        {
            pending_ = false;
            parser_.reset();
            ++timeouts_;
        }
    }

    // Runs independent of physical serial RX; returns 8 if a new request
    // must be transmitted. The caller sends only after it has UART capacity.
    size_t prepareRequest(uint32_t now, uint8_t* out, size_t capacity)
    {
        tick(now);
        if (pending_ || !timeDue(now, nextRequestAt_))
            return 0;

        const uint8_t nextSequence = static_cast<uint8_t>(sequence_ + 1);
        const size_t size = encodeRequest(nextSequence, out, capacity);
        if (size == 0)
            return 0;  // Leave state untouched if TX cannot send.
        sequence_ = nextSequence;
        pending_ = true;
        lastRequestedAt_ = now;
        nextRequestAt_ = now + PollEveryMs;
        return size;
    }

    void feed(uint8_t byte, uint32_t now)
    {
        if (timeElapsed(now, lastByteAt_, MaxInterByteGapMs))
            parser_.reset();
        lastByteAt_ = now;
        Frame frame{};
        if (!parser_.feed(byte, frame))
            return;
        if (!pending_ || frame.type != SnapshotResponse ||
            frame.sequence != sequence_)
        {
            ++rejectedResponses_;
            return;
        }
        Snapshot candidate{};
        if (!decodeSnapshot(frame, candidate))
        {
            ++rejectedResponses_;
            return;
        }
        // Do not accept a response arriving after the actual request TTL.
        if (timeElapsed(now, lastRequestedAt_, ReplyTimeoutMs))
        {
            ++rejectedResponses_;
            return;
        }
        snapshot_ = candidate;
        hasSnapshot_ = true;
        pending_ = false;
        lastReceivedAt_ = now;
    }

    bool online(uint32_t now) const
    {
        return hasSnapshot_ &&
               !timeElapsed(now, lastReceivedAt_, OfflineAfterMs);
    }

    // Only treat a channel as live if the transport itself is online.
    bool channelValid(uint8_t index, uint32_t now) const
    {
        if (!online(now) || index >= Channels)
            return false;
        const Channel& channel = snapshot_.channels[index];
        return (channel.flags & 0x02) != 0 && channel.fault == 0;
    }

    // Consumer must still apply configured publish limits in KNX015.
    // For offline frames, this is last-known-good DIAGNOSTIC data, not live.
    const Snapshot& lastSnapshot() const
    {
        return snapshot_;
    }

    uint32_t snapshotReceivedAt() const { return lastReceivedAt_; }
    bool hasSnapshot() const { return hasSnapshot_; }
    bool pending() const { return pending_; }
    uint16_t timeouts() const { return timeouts_; }
    uint16_t rejectedResponses() const { return rejectedResponses_; }

    uint16_t channelAgeSeconds(uint8_t index, uint32_t now) const
    {
        if (!hasSnapshot_ || index >= Channels)
            return 0xFFFF;
        const uint16_t baseAge = snapshot_.channels[index].ageSeconds;
        if (baseAge == 0xFFFF)
            return baseAge;
        const uint32_t delta = (now - lastReceivedAt_) / 1000UL;
        const uint32_t total = static_cast<uint32_t>(baseAge) + delta;
        return total >= 0xFFFFU ? 0xFFFFU : static_cast<uint16_t>(total);
    }

private:
    Parser parser_;
    Snapshot snapshot_{};
    uint32_t nextRequestAt_ = 0;
    uint32_t lastRequestedAt_ = 0;
    uint32_t lastReceivedAt_ = 0;
    uint32_t lastByteAt_ = 0;
    uint16_t timeouts_ = 0;
    uint16_t rejectedResponses_ = 0;
    uint8_t sequence_ = 0;
    bool hasSnapshot_ = false;
    bool pending_ = false;
};

} // namespace TemperatureProtocol
#endif // OPENKNX_TEMPERATURE_CLIENT_CORE_HPP
