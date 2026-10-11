#include "../../lib/common/temperature_client_core.hpp"

#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

namespace P = TemperatureProtocol;

static P::Snapshot goodSample(int16_t celsius100)
{
    P::Snapshot value{};
    value.uptimeMs = 123456;
    value.moduleStatus = 0;
    for (uint8_t i = 0; i < P::Channels; ++i)
    {
        auto &ch = value.channels[i];
        ch.centiC = static_cast<int16_t>(celsius100 + i);
        ch.ageSeconds = i;
        ch.flags = 0x03;
        ch.fault = 0;
    }
    return value;
}

static void deliver(P::ClientCore &client, uint8_t sequence,
                    const P::Snapshot& sample, uint32_t atMs,
                    bool damage = false)
{
    uint8_t packet[P::MaxFrameBytes]{};
    const size_t n = P::encodeSnapshot(sample, sequence, packet, sizeof(packet));
    assert(n == 67);
    if (damage) packet[25] ^= 0x21;
    for (size_t i = 0; i < n; ++i)
        client.feed(packet[i], atMs + static_cast<uint32_t>(i / 10));
}

static void basicPollAndRecovery()
{
    P::ClientCore client;
    client.begin(1000);
    uint8_t packet[8] = {};

    // UART not ready: no request must be marked pending.
    assert(client.prepareRequest(1000, packet, 7) == 0);
    assert(!client.pending());
    assert(client.prepareRequest(1000, packet, sizeof(packet)) == 8);
    assert(client.pending() && !client.online(1000));
    P::Parser requestDecoder;
    P::Frame request{};
    bool complete = false;
    for (uint8_t value : packet)
        complete = requestDecoder.feed(value, request);
    assert(complete && request.sequence == 1);
    assert(client.prepareRequest(1010, packet, sizeof(packet)) == 0);

    deliver(client, 1, goodSample(2000), 1050);
    assert(!client.pending());
    assert(client.online(1100));
    assert(client.hasSnapshot());
    assert(client.lastSnapshot().channels[0].centiC == 2000);
    assert(client.channelValid(1, 1100));
    assert(client.channelAgeSeconds(1, 4100) == 4);
    assert(client.prepareRequest(3999, packet, sizeof(packet)) == 0);

    assert(client.prepareRequest(4000, packet, sizeof(packet)) == 8);
    deliver(client, 1, goodSample(2300), 4020); // previous sequence
    assert(client.pending());
    assert(client.rejectedResponses() == 1);
    deliver(client, 2, goodSample(2300), 4050, true); // bad CRC
    assert(client.pending());
    deliver(client, 2, goodSample(2500), 4110);
    assert(!client.pending());
    assert(client.lastSnapshot().channels[0].centiC == 2500);

    assert(client.prepareRequest(7000, packet, sizeof(packet)) == 8);
    // No response; timeout must preserve the last valid snapshot.
    assert(client.prepareRequest(7399, packet, sizeof(packet)) == 0);
    assert(client.prepareRequest(7400, packet, sizeof(packet)) == 0);
    assert(client.timeouts() == 1);
    assert(client.hasSnapshot());
    assert(client.channelValid(0, 7400));
    assert(!client.online(19200));  // more than 15s since 4116ms response
    assert(!client.channelValid(0, 19200));
    assert(client.channelAgeSeconds(0, 19200) >= 15);
    assert(client.prepareRequest(10000, packet, sizeof(packet)) == 8);
    deliver(client, 4, goodSample(-1525), 10040);
    assert(client.online(10150));
    assert(client.lastSnapshot().channels[0].centiC == -1525);
}

static void rejectBadBodyEvenWithValidCrc()
{
    P::ClientCore client;
    client.begin(0);
    uint8_t req[8]{};
    assert(client.prepareRequest(0, req, sizeof(req)) == 8);

    P::Snapshot faulty = goodSample(3000);
    faulty.channels[3].flags = 0x02; // "Valid" without HasSample
    uint8_t reply[P::MaxFrameBytes]{};
    size_t n = P::encodeSnapshot(faulty, 1, reply, sizeof(reply));
    assert(n == 67);
    for (size_t i = 0; i < n; ++i)
        client.feed(reply[i], 80);
    assert(!client.hasSnapshot());
    assert(client.pending());
    assert(client.rejectedResponses() == 1);
    assert(client.prepareRequest(401, req, sizeof(req)) == 0);
    assert(client.timeouts() == 1);
}

static void rollover()
{
    const uint32_t t0 = 0xFFFFFF00U;
    P::ClientCore client;
    client.begin(t0);
    uint8_t req[8]{};
    assert(client.prepareRequest(t0, req, sizeof(req)) == 8);
    deliver(client, 1, goodSample(0), t0 + 40U);
    assert(client.online(t0 + 100U));
    assert(client.prepareRequest(t0 + 2999U, req, sizeof(req)) == 0);
    assert(client.prepareRequest(t0 + 3000U, req, sizeof(req)) == 8);
}

int main()
{
    basicPollAndRecovery();
    rejectBadBodyEvenWithValidCrc();
    rollover();
    puts("KNX014 client polling, CRC/sequence validation, timeouts and offline tests: PASS");
}
