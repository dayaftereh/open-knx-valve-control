#include "../../lib/common/temperature_protocol.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

namespace Protocol = TemperatureProtocol;

// KNX031: generate immutable golden vectors directly from the production
// shared C++ wire codec. This executable has no Arduino/USB/KNX dependencies.
static void printHex(const uint8_t* bytes, size_t count)
{
    for (size_t i = 0; i < count; ++i)
        printf("%02X", static_cast<unsigned int>(bytes[i]));
    printf("\n");
}

int main()
{
    uint8_t packet[Protocol::MaxFrameBytes] = {};
    const size_t get = Protocol::encodeRequest(0x37, packet, sizeof(packet));
    assert(get == 8);
    const uint8_t knownRequest[8] = {
        0xA5, 0x5A, 0x01, 0x01, 0x37, 0x00, 0x46, 0x59
    };
    for (size_t i = 0; i < get; ++i)
        assert(packet[i] == knownRequest[i]);
    printf("REQUEST ");
    printHex(packet, get);

    Protocol::Snapshot snapshot{};
    snapshot.uptimeMs = 0x12345678;
    snapshot.moduleStatus = 0;
    for (uint8_t i = 0; i < Protocol::Channels; ++i)
    {
        Protocol::Channel& ch = snapshot.channels[i];
        ch.centiC = static_cast<int16_t>(2000 + i * 53);
        ch.ageSeconds = i;
        ch.flags = 0x03;
        ch.fault = 0;
    }
    snapshot.channels[0].centiC = 0;
    snapshot.channels[1].centiC = -1050;
    snapshot.channels[5].flags = 0x10;
    snapshot.channels[5].fault = 1;
    snapshot.channels[5].ageSeconds = 0xFFFF;
    snapshot.channels[6].flags = 0x11;
    snapshot.channels[6].fault = 3;
    const size_t count = Protocol::encodeSnapshot(
        snapshot, 0x37, packet, sizeof(packet));
    assert(count == Protocol::MaxFrameBytes);
    Protocol::Parser parser{};
    Protocol::Frame frame{};
    bool parsed = false;
    for (size_t i = 0; i < count; ++i)
        parsed = parser.feed(packet[i], frame);
    assert(parsed && frame.type == Protocol::SnapshotResponse);
    assert(frame.sequence == 0x37);
    Protocol::Snapshot decoded{};
    assert(Protocol::decodeSnapshot(frame, decoded));
    assert(decoded.channels[0].centiC == 0);
    assert(decoded.channels[1].centiC == -1050);
    assert(decoded.channels[5].ageSeconds == 0xFFFF);
    printf("SNAPSHOT ");
    printHex(packet, count);
    return 0;
}
