#ifndef OPENKNX_TEMPERATURE_PROTOCOL_HPP
#define OPENKNX_TEMPERATURE_PROTOCOL_HPP

#include <stddef.h>
#include <stdint.h>

// KNX014 UART protocol v1. Shared by ATtiny3216 and RP2040; no Arduino
// includes, packed structs, dynamic allocation or native endianness assumptions.
namespace TemperatureProtocol
{
constexpr uint8_t Sync0 = 0xA5;
constexpr uint8_t Sync1 = 0x5A;
constexpr uint8_t Version = 1;
constexpr uint8_t GetSnapshot = 0x01;
constexpr uint8_t SnapshotResponse = 0x81;
constexpr uint8_t Channels = 9;
constexpr uint8_t SnapshotPayloadBytes = 4 + 1 + Channels * 6; // 59
constexpr uint8_t MaxPayloadBytes = SnapshotPayloadBytes;
constexpr uint8_t HeaderBytes = 4;   // version, type, sequence, payload length
constexpr uint8_t FrameOverhead = 2 + HeaderBytes + 2;
constexpr uint8_t MaxFrameBytes = FrameOverhead + MaxPayloadBytes; // 67
constexpr uint32_t MaxInterByteGapMs = 100U;

struct Channel
{
    int16_t centiC = 0;             // signed LE value / 100
    uint16_t ageSeconds = 0xFFFF;   // 0xFFFF means no valid previous sample
    uint8_t flags = 0;
    uint8_t fault = 0;
};

struct Snapshot
{
    uint32_t uptimeMs = 0;
    uint8_t moduleStatus = 0;       // reserved zero for protocol v1
    Channel channels[Channels];
};

struct Frame
{
    uint8_t type = 0;
    uint8_t sequence = 0;
    uint8_t length = 0;
    uint8_t payload[MaxPayloadBytes] = {};
};

inline void put16(uint8_t* out, uint16_t value)
{
    out[0] = static_cast<uint8_t>(value);
    out[1] = static_cast<uint8_t>(value >> 8);
}

inline uint16_t get16(const uint8_t* data)
{
    return static_cast<uint16_t>(data[0]) |
           (static_cast<uint16_t>(data[1]) << 8);
}

inline void put32(uint8_t* out, uint32_t value)
{
    put16(out, static_cast<uint16_t>(value));
    put16(out + 2, static_cast<uint16_t>(value >> 16));
}

inline uint32_t get32(const uint8_t* data)
{
    return static_cast<uint32_t>(get16(data)) |
           (static_cast<uint32_t>(get16(data + 2)) << 16);
}

// CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, xorout 0.
// The CRC covers VERSION, TYPE, SEQ, LENGTH and the payload, not sync/CRC.
inline uint16_t crc16(const uint8_t* bytes, size_t count)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < count; ++i)
    {
        crc ^= static_cast<uint16_t>(bytes[i]) << 8;
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc & 0x8000)
                  ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                  : static_cast<uint16_t>(crc << 1);
    }
    return crc;
}

inline size_t encodeFrame(uint8_t type, uint8_t sequence,
                          const uint8_t* payload, uint8_t length,
                          uint8_t* out, size_t capacity)
{
    const size_t total = static_cast<size_t>(FrameOverhead) + length;
    if (!out || capacity < total || length > MaxPayloadBytes ||
        (length && !payload))
        return 0;
    out[0] = Sync0;
    out[1] = Sync1;
    out[2] = Version;
    out[3] = type;
    out[4] = sequence;
    out[5] = length;
    for (uint8_t i = 0; i < length; ++i)
        out[6 + i] = payload[i];
    const uint16_t crc = crc16(out + 2, HeaderBytes + length);
    put16(out + 6 + length, crc);
    return total;
}

inline size_t encodeRequest(uint8_t sequence, uint8_t* out, size_t capacity)
{
    return encodeFrame(GetSnapshot, sequence, nullptr, 0, out, capacity);
}

inline void encodePayload(const Snapshot& in,
                          uint8_t (&out)[SnapshotPayloadBytes])
{
    put32(out, in.uptimeMs);
    out[4] = in.moduleStatus;
    for (uint8_t i = 0; i < Channels; ++i)
    {
        const uint8_t pos = static_cast<uint8_t>(5 + i * 6);
        const Channel& ch = in.channels[i];
        put16(out + pos, static_cast<uint16_t>(ch.centiC));
        put16(out + pos + 2, ch.ageSeconds);
        out[pos + 4] = ch.flags;
        out[pos + 5] = ch.fault;
    }
}

inline size_t encodeSnapshot(const Snapshot& snapshot, uint8_t sequence,
                             uint8_t* out, size_t capacity)
{
    uint8_t payload[SnapshotPayloadBytes];
    encodePayload(snapshot, payload);
    return encodeFrame(SnapshotResponse, sequence, payload,
                       SnapshotPayloadBytes, out, capacity);
}

inline bool decodeSnapshot(const Frame& frame, Snapshot& result)
{
    if (frame.type != SnapshotResponse ||
        frame.length != SnapshotPayloadBytes ||
        frame.payload[4] != 0)
        return false;

    Snapshot candidate{};
    candidate.uptimeMs = get32(frame.payload);
    candidate.moduleStatus = frame.payload[4];
    for (uint8_t i = 0; i < Channels; ++i)
    {
        const uint8_t pos = static_cast<uint8_t>(5 + i * 6);
        Channel& ch = candidate.channels[i];
        ch.centiC = static_cast<int16_t>(get16(frame.payload + pos));
        ch.ageSeconds = get16(frame.payload + pos + 2);
        ch.flags = frame.payload[pos + 4];
        ch.fault = frame.payload[pos + 5];
        // KNX013 quality flags: HasSample=1, Valid=2, Converting=4,
        // Stale=8, Error=16. Fault enum range currently 0..8.
        if ((ch.flags & static_cast<uint8_t>(~0x1FU)) ||
            ch.fault > 8 ||
            ((ch.flags & 0x02) && (!(ch.flags & 0x01) ||
              (ch.flags & 0x18) || ch.fault != 0)) ||
            (!(ch.flags & 0x01) && ch.ageSeconds != 0xFFFF))
            return false;
    }
    result = candidate; // only accept completely verified snapshots
    return true;
}

// Nonblocking parser with fixed storage. Valid complete frames are copied
// into out. Bad CRC/version/length is discarded, then the next sync is sought.
class Parser
{
public:
    void reset()
    {
        phase_ = 0;
        count_ = 0;
        target_ = 0;
    }

    bool inProgress() const { return phase_ != 0; }

    bool feed(uint8_t value, Frame& out)
    {
        if (phase_ == 0)
        {
            if (value == Sync0)
                phase_ = 1;
            return false;
        }
        if (phase_ == 1)
        {
            if (value == Sync1)
            {
                phase_ = 2;
                count_ = 0;
                target_ = HeaderBytes;
            }
            else if (value != Sync0)
                reset();
            return false;
        }
        bytes_[count_++] = value;
        if (count_ == HeaderBytes)
        {
            const uint8_t payloadLength = bytes_[3];
            if (bytes_[0] != Version || payloadLength > MaxPayloadBytes)
            {
                reset();
                return false;
            }
            target_ = static_cast<uint8_t>(HeaderBytes + payloadLength + 2);
        }
        if (count_ < target_)
            return false;
        const uint8_t len = bytes_[3];
        const uint16_t expected = get16(bytes_ + HeaderBytes + len);
        const bool good = crc16(bytes_, HeaderBytes + len) == expected;
        if (good)
        {
            out.type = bytes_[1];
            out.sequence = bytes_[2];
            out.length = len;
            for (uint8_t i = 0; i < len; ++i)
                out.payload[i] = bytes_[HeaderBytes + i];
        }
        reset();
        return good;
    }

private:
    uint8_t bytes_[HeaderBytes + MaxPayloadBytes + 2] = {};
    uint8_t phase_ = 0;
    uint8_t count_ = 0;
    uint8_t target_ = 0;
};

static_assert(MaxFrameBytes == 67, "Wire format changed: update tests/docs");
static_assert(SnapshotPayloadBytes == 59, "Snapshot format changed");
} // namespace TemperatureProtocol

#endif // OPENKNX_TEMPERATURE_PROTOCOL_HPP
