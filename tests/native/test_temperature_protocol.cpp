#include "../../lib/common/temperature_protocol.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

namespace P = TemperatureProtocol;

static P::Snapshot example()
{
    P::Snapshot result{};
    result.uptimeMs = 0x12345678;
    result.moduleStatus = 0;
    for (uint8_t i = 0; i < P::Channels; ++i)
    {
        P::Channel& sensor = result.channels[i];
        sensor.centiC = static_cast<int16_t>(2000 + i * 53);
        sensor.ageSeconds = i;
        sensor.flags = 0x03;   // HasSample and Valid
        sensor.fault = 0;
    }
    result.channels[0].centiC = 0;        // real zero degrees
    result.channels[1].centiC = -1050;    // -10.5 degrees
    result.channels[5].ageSeconds = 0xFFFF;
    result.channels[5].flags = 0x10;      // error, no sample
    result.channels[5].fault = 1;        // NoSensor
    result.channels[6].flags = 0x11;      // retained bad value
    result.channels[6].fault = 3;        // ReadFailed
    return result;
}

static void goldenRequest()
{
    uint8_t packet[P::MaxFrameBytes] = {};
    const size_t len = P::encodeRequest(0x37, packet, sizeof(packet));
    assert(len == 8);
    // Independently calculated CRC16/CCITT-FALSE(01 01 37 00) = 0x5946.
    const uint8_t golden[8] = {
        0xA5, 0x5A, 0x01, 0x01, 0x37, 0x00, 0x46, 0x59
    };
    for (size_t i = 0; i < 8; ++i)
        assert(packet[i] == golden[i]);
    assert(P::encodeRequest(0x37, packet, 7) == 0);
    assert(P::encodeFrame(P::GetSnapshot, 0, nullptr, 1,
                          packet, sizeof(packet)) == 0);
}

static void roundtripAndSequence()
{
    const auto sample = example();
    uint8_t packet[P::MaxFrameBytes] = {};
    const size_t len = P::encodeSnapshot(sample, 42, packet, sizeof(packet));
    assert(len == 67);
    assert(packet[0] == 0xA5 && packet[1] == 0x5A);
    assert(packet[2] == P::Version && packet[3] == 0x81);
    assert(packet[4] == 42 && packet[5] == 59);
    assert(packet[6] == 0x78 && packet[7] == 0x56);
    assert(packet[8] == 0x34 && packet[9] == 0x12);
    P::Parser parser;
    P::Frame frame{};
    bool completed = false;
    for (size_t i = 0; i < len; ++i)
    {
        completed = parser.feed(packet[i], frame);
        if (i + 1 < len)
            assert(!completed);
    }
    assert(completed);
    assert(frame.type == P::SnapshotResponse);
    assert(frame.sequence == 42);
    P::Snapshot decoded{};
    assert(P::decodeSnapshot(frame, decoded));
    assert(decoded.uptimeMs == sample.uptimeMs);
    assert(decoded.channels[0].centiC == 0);
    assert(decoded.channels[1].centiC == -1050);
    assert(decoded.channels[5].ageSeconds == 65535);
    assert(decoded.channels[5].flags == 0x10);
    assert(decoded.channels[6].fault == 3);
    for (uint8_t i = 0; i < P::Channels; ++i)
    {
        assert(decoded.channels[i].centiC == sample.channels[i].centiC);
        assert(decoded.channels[i].flags == sample.channels[i].flags);
        assert(decoded.channels[i].fault == sample.channels[i].fault);
    }
    // A client must additionally match the sequence of its own request.
    assert(frame.sequence != 43);
}

static void corruptedAndPartialPackets()
{
    const auto sample = example();
    uint8_t packet[P::MaxFrameBytes] = {};
    const auto len = P::encodeSnapshot(sample, 31, packet, sizeof(packet));
    P::Parser parser;
    P::Frame frame{};
    bool completed = false;

    packet[11] ^= 0x80; // damaged payload; CRC must fail
    for (size_t i = 0; i < len; ++i)
        completed |= parser.feed(packet[i], frame);
    assert(!completed);

    packet[11] ^= 0x80;
    // An incomplete/truncated packet must not emit a decoded snapshot.
    for (size_t i = 0; i < 12; ++i)
        assert(!parser.feed(packet[i], frame));
    parser.reset(); // caller resets state after RX silence/timeout
    // Garbage and a repeated sync byte must not prevent resynchronization.
    assert(!parser.feed(0xF2, frame));
    assert(!parser.feed(P::Sync0, frame));
    assert(!parser.feed(P::Sync0, frame));
    assert(!parser.feed(P::Sync1, frame));
    bool ok = false;
    for (size_t i = 2; i < len; ++i)
        ok = parser.feed(packet[i], frame);
    assert(ok && frame.sequence == 31);

    // Unsupported version, even with a valid CRC, is rejected.
    packet[2] = 2;
    P::put16(packet + len - 2, P::crc16(packet + 2, len - 4));
    ok = false;
    for (size_t i = 0; i < len; ++i)
        ok |= parser.feed(packet[i], frame);
    assert(!ok);

    packet[2] = 1;
    packet[5] = 0xFF; // length over maximum: reject before copying
    ok = false;
    for (size_t i = 0; i < len; ++i)
        ok |= parser.feed(packet[i], frame);
    assert(!ok);

    // A legitimate new packet after invalid input still parses.
    const auto goodLen = P::encodeRequest(255, packet, sizeof(packet));
    ok = false;
    for (size_t i = 0; i < goodLen; ++i)
        ok = parser.feed(packet[i], frame);
    assert(ok && frame.type == P::GetSnapshot && frame.sequence == 255);
}

static void invalidContentAndRequestReply()
{
    P::Snapshot sample = example();
    uint8_t request[8]{};
    assert(P::encodeRequest(8, request, sizeof(request)) == 8);
    P::Parser atTinyParser;
    P::Frame atTinyRequest{};
    bool gotRequest = false;
    for (uint8_t b : request)
        gotRequest = atTinyParser.feed(b, atTinyRequest);
    assert(gotRequest && atTinyRequest.length == 0);
    assert(atTinyRequest.type == P::GetSnapshot);

    uint8_t response[P::MaxFrameBytes]{};
    const auto count = P::encodeSnapshot(
        sample, atTinyRequest.sequence, response, sizeof(response));
    P::Parser rpParser;
    P::Frame rpFrame{};
    bool gotReply = false;
    for (size_t i = 0; i < count; ++i)
        gotReply = rpParser.feed(response[i], rpFrame);
    assert(gotReply && rpFrame.sequence == 8);
    P::Snapshot recv{};
    assert(P::decodeSnapshot(rpFrame, recv));
    assert(recv.channels[1].centiC == -1050);

    // Well-formed CRC with impossible "valid but no sample" is rejected.
    rpFrame.payload[5 + 4] = 0x02;
    assert(!P::decodeSnapshot(rpFrame, recv));
    // Same framing but unexpected type never decodes a snapshot.
    rpFrame.payload[5 + 4] = 0x03;
    rpFrame.type = P::GetSnapshot;
    assert(!P::decodeSnapshot(rpFrame, recv));
}

int main()
{
    goldenRequest();
    roundtripAndSequence();
    corruptedAndPartialPackets();
    invalidContentAndRequestReply();
    puts("KNX014 native framing, CRC, stream parser and nine-channel snapshot tests: PASS");
}
