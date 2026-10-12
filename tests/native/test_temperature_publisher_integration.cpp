#include "../../src/controller/temperature_publisher.hpp"
#include <knx.h>
#include <temperature_protocol.hpp>

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

uint32_t mockNow = 0;
uint32_t millis() { return mockNow; }
KNXMock knx;
namespace P = TemperatureProtocol;

static P::Snapshot sourceSnapshot()
{
    P::Snapshot s{};
    s.uptimeMs = 9000;
    for (uint8_t i = 0; i < P::Channels; ++i)
    {
        auto &ch = s.channels[i];
        ch.flags = 0x10; // no valid reading
        ch.fault = 1;    // no probe
        ch.ageSeconds = 0xFFFF;
    }
    s.channels[0] = {0, 1, 0x03, 0};
    s.channels[1] = {-1050, 0, 0x03, 0};
    return s;
}

static void sendToBridge(TemperatureBridge &bridge, SerialUART &serial,
                         uint8_t seq, const P::Snapshot& snapshot)
{
    uint8_t packet[P::MaxFrameBytes]{};
    const size_t n = P::encodeSnapshot(snapshot, seq, packet, sizeof(packet));
    assert(n == 67);
    serial.inject(packet, n);
    bridge.update();
    bridge.update(); // production bridge reads 48 bytes per iteration
}

int main()
{
    SerialUART serial;
    TemperatureBridge bridge;
    bridge.setup(serial);
    TemperaturePublisher publisher;
    publisher.begin(0);

    mockNow = 0;
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == 0); // ETS not commissioned

    knx.commissioned = true;
    knx.param6 = 0x80;  // P19 ON
    knx.period = 60;
    knx.delta = 50;

    publisher.update(bridge, mockNow);
    assert(knx.objects[34].calls == 1);
    assert(knx.objects[34].last == 0);
    assert(knx.objects[34].main == 1 && knx.objects[34].sub == 2);

    mockNow = 250;
    publisher.update(bridge, mockNow);
    assert(knx.objects[35].calls == 1);
    assert(knx.objects[35].last == 0);
    assert(knx.objects[35].main == 7 && knx.objects[35].sub == 1);

    mockNow = 500;
    bridge.update();
    assert(serial.tx.size() == 8); // GET_SNAPSHOT request, sequence 1
    serial.tx.clear();
    auto sample = sourceSnapshot();
    sendToBridge(bridge, serial, 1, sample);
    assert(bridge.online(mockNow));

    publisher.update(bridge, mockNow);
    assert(knx.objects[34].calls == 2 && knx.objects[34].last == 1);
    mockNow = 750;
    publisher.update(bridge, mockNow);
    assert(knx.objects[35].calls == 2 && knx.objects[35].last == 3);

    mockNow = 1000;
    publisher.update(bridge, mockNow);
    assert(knx.objects[25].calls == 1 && knx.objects[25].last == 0);
    assert(knx.objects[25].main == 9 && knx.objects[25].sub == 1);

    // Verify a failed KNX value conversion doesn't discard a pending update.
    mockNow = 1250;
    knx.objects[26].allow = false;
    publisher.update(bridge, mockNow);
    assert(publisher.rejectedConversions() == 1);
    assert(knx.objects[26].calls == 0);
    knx.objects[26].allow = true;
    mockNow = 1251;
    publisher.update(bridge, mockNow);
    assert(knx.objects[26].calls == 1 && knx.objects[26].last == -10.5f);
    assert(knx.objects[27].calls == 0); // missing T2 cannot publish

    // P19 OFF suppresses all further temperature & diagnostic traffic.
    mockNow = 3500;
    bridge.update(); // seq 2 poll
    assert(serial.tx.size() == 8);
    serial.tx.clear();
    sample.channels[1] = {-980, 0, 0x03, 0};
    sendToBridge(bridge, serial, 2, sample);
    knx.param6 = 0;
    const uint16_t before = publisher.acceptedConversions();
    publisher.update(bridge, mockNow);
    assert(publisher.acceptedConversions() == before);

    knx.param6 = 0x80;
    mockNow = 6500;
    publisher.update(bridge, mockNow);
    assert(knx.objects[26].calls == 2 && knx.objects[26].last == -9.8f);

    // More than 15 seconds without UART response: no temperature KO gets
    // stale data. Only diagnostic KO34/KO35 reports offline and no validity.
    const uint16_t t0count = knx.objects[25].calls;
    const uint16_t t1count = knx.objects[26].calls;
    mockNow = 19500;
    publisher.update(bridge, mockNow);
    assert(knx.objects[34].last == 0);
    mockNow = 19750;
    publisher.update(bridge, mockNow);
    assert(knx.objects[35].last == 0);
    assert(knx.objects[25].calls == t0count);
    assert(knx.objects[26].calls == t1count);

    puts("KNX015 actual publisher + real bridge + mock KNX GroupObject: PASS");
}
