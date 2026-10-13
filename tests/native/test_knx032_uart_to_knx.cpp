// KNX032 native-only: saved KNX014 frames -> real TemperatureBridge
// -> real TemperaturePublisher -> KNXMock GroupObject KO25..35.
// Input file is a separately produced local binary stream, never a COM port.
// This test must NEVER link Arduino board pin functions, network or motors.

#include "../../src/controller/temperature_bridge.hpp"
#include "../../src/controller/temperature_publisher.hpp"
#include <knx.h>
#include <temperature_protocol.hpp>
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <fstream>
#include <iterator>
#include <vector>

uint32_t mockNow = 0;
uint32_t millis() { return mockNow; }
KNXMock knx;

namespace P = TemperatureProtocol;

static void at(uint32_t time)
{
    mockNow = time;
}

static bool savedTrace(const char* path, P::Frame& response)
{
    std::ifstream stream(path, std::ios::binary);
    if (!stream)
        return false;
    stream.seekg(0, std::ios::end);
    const auto length = stream.tellg();
    if (length < 75 || length > 4096)
        return false; // bounded BEFORE any input allocation
    stream.seekg(0, std::ios::beg);
    std::vector<uint8_t> bytes(
        (std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    if (stream.bad() || bytes.size() != static_cast<size_t>(length))
        return false;
    P::Parser parser;
    P::Frame frame{};
    bool hasRequest = false;
    bool hasReply = false;
    uint8_t seq = 0;
    unsigned frames = 0;
    for (const auto b : bytes)
    {
        if (!parser.feed(b, frame))
            continue;
        ++frames;
        if (frames == 1 && frame.type == P::GetSnapshot && frame.length == 0)
        {
            seq = frame.sequence;
            hasRequest = true;
        }
        else if (frames == 2 && hasRequest &&
                 frame.type == P::SnapshotResponse &&
                 frame.length == P::SnapshotPayloadBytes &&
                 frame.sequence == seq)
        {
            P::Snapshot decoded{};
            if (!P::decodeSnapshot(frame, decoded))
                return false;
            response = frame;
            hasReply = true;
        }
        else
        {
            return false;
        }
    }
    return hasRequest && hasReply && frames == 2;
}

static size_t reframe(const P::Frame& content, uint8_t sequence,
                      uint8_t* output)
{
    // KNX031's recorded request used seq 0x37. The simulated
    // RP2040 initial client request is seq 1; preserve original bytes
    // of the validated payload but encode a *new* CRC and seq.
    // This tests value transport, NOT literal on-wire replay or bus ACK.
    return P::encodeFrame(P::SnapshotResponse, sequence, content.payload,
                          content.length, output, P::MaxFrameBytes);
}

static uint8_t initialRequest(TemperatureBridge& bridge, SerialUART& uart)
{
    bridge.update();  // starts the actual production ClientCore request.
    assert(uart.tx.size() == 8);
    P::Parser parser{};
    P::Frame frame{};
    bool found = false;
    while (!uart.tx.empty())
    {
        const uint8_t value = uart.tx.front();
        uart.tx.pop_front();
        found = parser.feed(value, frame);
    }
    assert(found && frame.type == P::GetSnapshot && frame.length == 0);
    return frame.sequence;
}

static void feedResponse(TemperatureBridge& bridge, SerialUART& uart,
                         const uint8_t* data, size_t size)
{
    uart.inject(data, size);
    bridge.update(); // production RX bounded to 48 bytes / loop
    bridge.update(); // production RX consumes remaining up to 19
    assert(uart.rx.empty());
}

static void checkDpt(uint16_t object, uint8_t main, uint8_t sub)
{
    assert(knx.objects[object].main == main);
    assert(knx.objects[object].sub == sub);
}

static void goodPath(const P::Frame& recorded)
{
    knx = KNXMock{};
    at(0);
    SerialUART uart;
    TemperatureBridge bridge;
    bridge.setup(uart);
    TemperaturePublisher publisher;
    publisher.begin(mockNow);

    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == 0); // KNX not configured

    knx.commissioned = true;
    knx.param6 = 0; // P19 disable: no temperature or diagnostic KO updates
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == 0);
    knx.param6 = 0x80; // P19 enabled in read-only fake KNXMock
    knx.period = 60;
    knx.delta = 50;
    publisher.update(bridge, mockNow);
    assert(knx.objects[34].calls == 1);
    assert(knx.objects[34].last == 0);
    checkDpt(34, 1, 2);

    const uint8_t sequence = initialRequest(bridge, uart);
    assert(sequence == 1);
    uint8_t adapted[P::MaxFrameBytes]{};
    const size_t length = reframe(recorded, sequence, adapted);
    assert(length == P::MaxFrameBytes);
    at(20);
    feedResponse(bridge, uart, adapted, length);
    assert(bridge.hasSnapshot());
    assert(bridge.online(mockNow));
    assert(bridge.lastSnapshot().uptimeMs == 0x12345678U);

    // At 20ms the global KNX KO minimum bus gap is not yet elapsed.
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == 1);
    at(249);
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == 1);
    at(250);
    publisher.update(bridge, mockNow);
    assert(knx.objects[34].calls == 2 && knx.objects[34].last == 1);
    checkDpt(34, 1, 2);

    at(499);
    publisher.update(bridge, mockNow);
    assert(knx.objects[35].calls == 0);
    at(500);
    publisher.update(bridge, mockNow);
    // All nine channels except T5 (NoSensor) and T6 (ReadFailed).
    assert(knx.objects[35].calls == 1);
    assert(knx.objects[35].last == 0x19F);
    checkDpt(35, 7, 1);

    // KNX library rejects a value conversion: scheduler retries it,
    // does not count a real bus ACK and does not advance to T1.
    knx.objects[25].allow = false;
    at(750);
    publisher.update(bridge, mockNow);
    assert(publisher.rejectedConversions() == 1);
    assert(knx.objects[25].calls == 0);
    knx.objects[25].allow = true;
    at(751);
    publisher.update(bridge, mockNow);
    assert(knx.objects[25].calls == 1);
    checkDpt(25, 9, 1);
    assert(knx.objects[25].last == 0.0f); // real 0C is valid

    // KOs 26..29, 32..33: exactly the seven valid probe readings.
    const uint8_t channels[] = {1, 2, 3, 4, 7, 8};
    const float expected[] = {-10.5f, 21.06f, 21.59f,
                               22.12f, 23.71f, 24.24f};
    for (size_t i = 0; i < 6; ++i)
    {
        at(static_cast<uint32_t>(1001 + i * 250));
        publisher.update(bridge, mockNow);
        const uint16_t ko = static_cast<uint16_t>(25 + channels[i]);
        assert(knx.objects[ko].calls == 1);
        checkDpt(ko, 9, 1);
        assert(fabsf(knx.objects[ko].last - expected[i]) < 0.011f);
    }
    assert(knx.objects[30].calls == 0); // T5 NoSensor
    assert(knx.objects[31].calls == 0); // T6 ReadFailed
    assert(publisher.acceptedConversions() == 10);

    // A last-known-good old KO may retain a historical value, but never
    // re-send it as new temperature after the UART is offline.
    at(15300);
    publisher.update(bridge, mockNow);
    assert(!bridge.online(mockNow));
    assert(knx.objects[34].calls == 3);
    assert(knx.objects[34].last == 0);
    at(15550);
    publisher.update(bridge, mockNow);
    assert(knx.objects[35].calls == 2 && knx.objects[35].last == 0);
    for (uint16_t ko = 25; ko <= 33; ++ko)
        assert(knx.objects[ko].calls == (ko == 30 || ko == 31 ? 0 : 1));

    knx.param6 = 0; // disable even diagnostics
    const auto accepted = publisher.acceptedConversions();
    at(16000);
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == accepted);
    puts("KNX032 FULL PIPELINE: 9 channels, 7 valid, KO25..35, "
         "250ms gap, retry, stale/offline and P19 disabled PASS");
}

static void failedFramePath(const P::Frame& recorded)
{
    // CRC-corrupt response cannot refresh the bridge.
    at(0);
    SerialUART uart;
    TemperatureBridge bridge;
    bridge.setup(uart);
    const auto seq = initialRequest(bridge, uart);
    uint8_t packet[P::MaxFrameBytes]{};
    const size_t size = reframe(recorded, seq, packet);
    assert(size == 67);
    packet[11] ^= 0x40; // CRC is deliberately not updated
    at(20);
    feedResponse(bridge, uart, packet, size);
    assert(!bridge.online(mockNow));
    assert(!bridge.hasSnapshot());
    at(420);
    bridge.update();
    assert(bridge.timeoutCount() == 1);
    // Wrong sequence with correct CRC is also rejected.
    at(3000);
    const uint8_t nextSeq = initialRequest(bridge, uart);
    reframe(recorded, static_cast<uint8_t>(nextSeq + 1), packet);
    at(3020);
    feedResponse(bridge, uart, packet, size);
    assert(!bridge.online(mockNow));
    assert(bridge.rejectedCount() == 1);
    // Semantically impossible Valid without HasSample, but correct CRC:
    at(6000);
    const uint8_t thirdSeq = initialRequest(bridge, uart);
    uint8_t badPayload[P::SnapshotPayloadBytes]{};
    for (size_t i = 0; i < P::SnapshotPayloadBytes; ++i)
        badPayload[i] = recorded.payload[i];
    badPayload[5 + 4] = 0x02;
    const size_t n = P::encodeFrame(
        P::SnapshotResponse, thirdSeq, badPayload, P::SnapshotPayloadBytes,
        packet, sizeof(packet));
    at(6020);
    feedResponse(bridge, uart, packet, n);
    assert(!bridge.online(mockNow));
    assert(bridge.rejectedCount() == 2);
    puts("KNX032 FAIL CLOSED: wrong CRC, wrong sequence, and false Valid PASS");
}

int main(int argc, char** argv)
{
    if (argc != 2)
    {
        fputs("KNX032 accepts exactly one LOCAL prerecorded test-byte file\n", stderr);
        return 2;
    }
    P::Frame response{};
    if (!savedTrace(argv[1], response))
    {
        fputs("KNX032 rejects incomplete/invalid/nonmatching UART trace\n", stderr);
        return 3;
    }
    goodPath(response);
    failedFramePath(response);
    puts("KNX032 OFFLINE test PASS; no actual KNX/group write or device I/O");
    return 0;
}
