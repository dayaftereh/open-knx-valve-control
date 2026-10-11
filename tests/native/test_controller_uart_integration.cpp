#include "../../src/controller/temperature_bridge.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

uint32_t fakeNowMs = 0;
uint32_t millis() { return fakeNowMs; }
namespace P = TemperatureProtocol;

static P::Snapshot nineSensors()
{
    P::Snapshot s{};
    s.uptimeMs = 14000;
    for (uint8_t i = 0; i < 9; ++i)
    {
        auto &ch = s.channels[i];
        ch.centiC = static_cast<int16_t>(2500 + i * 5);
        ch.ageSeconds = i;
        ch.flags = 0x03;
        ch.fault = 0;
    }
    s.channels[0].centiC = 0;
    s.channels[1].centiC = -1125;
    s.channels[6].flags = 0x10;
    s.channels[6].fault = 1;
    s.channels[6].ageSeconds = 65535;
    return s;
}

int main()
{
    SerialUART uart;
    TemperatureBridge bridge;
    bridge.setup(uart);
    assert(!bridge.online(fakeNowMs));
    assert(!bridge.hasSnapshot());

    // Actual production TemperatureBridge::update queues GET_SNAPSHOT.
    bridge.update();
    assert(uart.tx.size() == 8);
    P::Parser parser;
    P::Frame req{};
    bool validReq = false;
    while (!uart.tx.empty())
    {
        uint8_t b = uart.tx.front();
        uart.tx.pop_front();
        validReq = parser.feed(b, req);
    }
    assert(validReq && req.type == P::GetSnapshot);
    assert(req.sequence == 1 && req.length == 0);

    uint8_t response[P::MaxFrameBytes]{};
    const size_t bytes = P::encodeSnapshot(
        nineSensors(), req.sequence, response, sizeof(response));
    assert(bytes == 67);
    fakeNowMs = 20;
    uart.inject(response, bytes);
    bridge.update(); // only 48 received
    assert(!bridge.online(fakeNowMs));
    fakeNowMs = 22;
    bridge.update(); // remaining 19
    assert(bridge.online(fakeNowMs));
    assert(bridge.hasSnapshot());
    assert(bridge.channelValid(0, fakeNowMs));
    assert(bridge.lastSnapshot().channels[0].centiC == 0);
    assert(bridge.lastSnapshot().channels[1].centiC == -1125);
    assert(!bridge.channelValid(6, fakeNowMs));
    assert(bridge.ageSeconds(1, fakeNowMs) == 1);

    // Bad CRC is silently ignored, and old data goes offline after TTL.
    fakeNowMs = 3000;
    bridge.update();
    assert(uart.tx.size() == 8);
    uart.tx.clear();
    response[28] ^= 0x40;
    uart.inject(response, bytes);
    bridge.update();
    bridge.update();
    assert(bridge.lastSnapshot().channels[1].centiC == -1125);
    fakeNowMs = 3400;
    bridge.update();
    assert(bridge.timeoutCount() == 1);
    assert(bridge.online(fakeNowMs));
    fakeNowMs = 15100;
    bridge.update();
    assert(!bridge.online(fakeNowMs));
    assert(!bridge.channelValid(0, fakeNowMs));

    puts("KNX014 native actual RP2040 UART client adapter: PASS");
}
