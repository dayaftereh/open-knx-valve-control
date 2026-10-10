#ifndef MOCK_OPENKNX_ONEWIRE_HPP
#define MOCK_OPENKNX_ONEWIRE_HPP
#include <stdint.h>

struct MockOneWireSensor
{
    bool present = false;
    bool parasite = false;
    float tempC = -127.0f;
    unsigned int requests = 0;
};
extern MockOneWireSensor fakeOneWireSensors[18];

class OneWire
{
public:
    void begin(uint8_t pin) { pin_ = pin; }
    void reset_search() { searched_ = false; }
    bool search(uint8_t *address)
    {
        if (searched_ || !fakeOneWireSensors[pin_].present)
            return false;
        address[0] = 0x28; // DS18B20 family
        address[1] = pin_;
        for (uint8_t i = 2; i < 8; ++i)
            address[i] = i;
        searched_ = true;
        return true;
    }

private:
    uint8_t pin_ = 0;
    bool searched_ = false;
};
#endif
