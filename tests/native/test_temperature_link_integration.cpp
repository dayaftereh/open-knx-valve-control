#include "../../src/temperature/temperature_link.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

uint32_t fakeNowMs = 0;
uint32_t millis() { return fakeNowMs; }
MockOneWireSensor fakeOneWireSensors[18];
namespace P = TemperatureProtocol;

static void advance(Temperatures& bank, uint32_t first, uint32_t last)
{
    for (fakeNowMs = first; fakeNowMs <= last; fakeNowMs += 100)
    {
        bank.update();
        bank.update(); // one cycle may discover, the next starts conversion
    }
}

static P::Snapshot takeReply(HardwareSerial& serial, uint8_t sequence)
{
    P::Parser parser;
    P::Frame frame{};
    bool done = false;
    while (!serial.tx.empty())
    {
        const uint8_t b = serial.tx.front();
        serial.tx.pop_front();
        if (parser.feed(b, frame))
            done = true;
    }
    assert(done);
    assert(frame.type == P::SnapshotResponse);
    assert(frame.sequence == sequence);
    P::Snapshot decoded{};
    assert(P::decodeSnapshot(frame, decoded));
    return decoded;
}

int main()
{
    const uint8_t pins[9] = {
        PIN_PA5, PIN_PA6, PIN_PA7, PIN_PB5, PIN_PB4,
        PIN_PB1, PIN_PC1, PIN_PC0, PIN_PB0
    };
    for (uint8_t i = 0; i < 9; ++i)
    {
        auto &sensor = fakeOneWireSensors[pins[i]];
        sensor.present = true;
        sensor.tempC = 20.0f + i;
    }
    fakeOneWireSensors[PIN_PA5].tempC = 0.0f;
    fakeOneWireSensors[PIN_PA6].tempC = -8.25f;
    fakeOneWireSensors[PIN_PB1].present = false; // T5 sensor missing

    Print debug;
    Config config{12, 10.0f, 2.5f};
    Temperatures bank;
    assert(bank.setup(&config, debug));
    advance(bank, 0, 6000);

    HardwareSerial port;
    TemperatureLink link;
    assert(link.setup(port, bank));

    uint8_t request[8]{};
    assert(P::encodeRequest(9, request, sizeof(request)) == 8);
    unsigned countBefore = fakeOneWireSensors[PIN_PA5].requests;
    fakeNowMs = 6100;
    port.inject(request, sizeof(request));
    for (uint8_t i = 0; i < 10; ++i)
        link.update();  // NO bank.update(): must serve from the RAM cache
    assert(fakeOneWireSensors[PIN_PA5].requests == countBefore);
    auto reply = takeReply(port, 9);
    assert(reply.channels[0].centiC == 0);
    assert(reply.channels[1].centiC == -825);
    assert((reply.channels[0].flags & 0x02) != 0);
    assert(reply.channels[5].fault == 1);
    assert((reply.channels[5].flags & 0x02) == 0);
    assert(reply.channels[5].ageSeconds == 65535);

    // Reject corrupted requests; no reply is allowed.
    request[4] ^= 0x01;
    port.inject(request, sizeof(request));
    link.update();
    assert(port.tx.empty());

    // TX FIFO backpressure: do not block, and preserve the entire reply.
    request[4] ^= 0x01;
    port.setWritable(0);
    port.inject(request, sizeof(request));
    link.update();
    assert(port.tx.empty());
    port.setWritable(5);
    for (uint8_t i = 0; i < 20; ++i)
        link.update();
    reply = takeReply(port, 9);
    assert(reply.channels[1].centiC == -825);

    puts("KNX014 native actual ATtiny UART responder: PASS");
}
