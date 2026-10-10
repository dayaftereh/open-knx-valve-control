#include "../../src/temperature/temperatures.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

uint32_t fakeNowMs = 0;
uint32_t millis() { return fakeNowMs; }
MockOneWireSensor fakeOneWireSensors[18];

using namespace TemperatureSampler;

static void advance(Temperatures &bank, uint32_t start, uint32_t end)
{
    for (fakeNowMs = start; fakeNowMs <= end; fakeNowMs += 100U)
    {
        // First call discovers; a later loop iteration starts conversion.
        bank.update();
        bank.update();
    }
}

int main()
{
    const uint8_t pins[TemperaturesCount] = {
        PIN_PA5, PIN_PA6, PIN_PA7, PIN_PB5, PIN_PB4,
        PIN_PB1, PIN_PC1, PIN_PC0, PIN_PB0
    };
    for (uint8_t index = 0; index < TemperaturesCount; ++index)
    {
        fakeOneWireSensors[pins[index]].present = true;
        fakeOneWireSensors[pins[index]].tempC = 20.0f + index;
    }
    // Real 0 C, negative C, and unplugged probe must have different states.
    fakeOneWireSensors[PIN_PA5].tempC = 0.0f;
    fakeOneWireSensors[PIN_PA6].tempC = -10.5f;
    fakeOneWireSensors[PIN_PB1].present = false;

    Config config{12, 10.0f, 2.5f};
    Print serial;
    Temperatures bank;
    assert(bank.setup(&config, serial));

    advance(bank, 0, 6000);
    for (uint8_t index = 0; index < TemperaturesCount; ++index)
    {
        const auto value = bank.getSnapshot(index, fakeNowMs);
        if (index == 5)
        {
            assert((value.flags & Valid) == 0);
            assert(value.fault == Fault::NoSensor);
            assert(bank.getTemperature(index) == DEVICE_DISCONNECTED_C);
        }
        else
        {
            assert((value.flags & Valid) != 0);
            assert(fakeOneWireSensors[pins[index]].requests >= 1);
        }
    }
    assert(bank.getSnapshot(0, fakeNowMs).centiC == 0);
    assert(bank.getSnapshot(1, fakeNowMs).centiC == -1050);
    assert(bank.getTemperature(0) == 0.0f);
    assert(bank.getTemperature(1) == -10.5f);

    // Plug the T5 probe in after the initial failed discovery: retry recovers.
    fakeOneWireSensors[PIN_PB1].present = true;
    fakeOneWireSensors[PIN_PB1].tempC = 32.25f;
    advance(bank, 6100, 14000);
    const auto recovered = bank.getSnapshot(5, fakeNowMs);
    assert((recovered.flags & Valid) != 0);
    assert(recovered.centiC == 3225);

    // Disconnect T3 after known-good data; retain value, mark current
    // sensor invalid, never return fabricated zero as live temperature.
    const int16_t oldT3 = bank.getSnapshot(3, fakeNowMs).centiC;
    fakeOneWireSensors[PIN_PB5].present = false;
    advance(bank, 14100, 23500);
    const auto failed = bank.getSnapshot(3, fakeNowMs);
    assert((failed.flags & Valid) == 0);
    assert((failed.flags & HasSample) != 0);
    assert((failed.flags & Error) != 0);
    assert(failed.centiC == oldT3);
    assert(bank.getTemperature(3) == DEVICE_DISCONNECTED_C);

    const auto outOfRange = bank.getSnapshot(99, fakeNowMs);
    assert((outOfRange.flags & Valid) == 0);
    assert(outOfRange.fault == Fault::NoSensor);

    puts("KNX013 native 9-channel Dallas mock integration: PASS");
    return 0;
}
