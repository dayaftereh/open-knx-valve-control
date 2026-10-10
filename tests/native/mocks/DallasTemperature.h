#ifndef MOCK_OPENKNX_DALLAS_HPP
#define MOCK_OPENKNX_DALLAS_HPP
#include <stdint.h>
#include "OneWire.h"

#define DEVICE_DISCONNECTED_C (-127.0f)
typedef uint8_t DeviceAddress[8];

class DallasTemperature
{
public:
    struct request_t
    {
        bool result;
    };
    void setOneWire(OneWire *) {}
    void setWaitForConversion(bool) {}
    void setCheckForConversion(bool) {}
    void setAutoSaveScratchPad(bool) {}

    bool validAddress(const uint8_t *address) { return address[0] == 0x28; }
    bool validFamily(const uint8_t *address) { return address[0] == 0x28; }
    bool readPowerSupply(const uint8_t *address)
    {
        return fakeOneWireSensors[address[1]].parasite;
    }
    bool setResolution(const uint8_t *address, uint8_t, bool)
    {
        return fakeOneWireSensors[address[1]].present;
    }
    request_t requestTemperaturesByAddress(const uint8_t *address)
    {
        auto &sensor = fakeOneWireSensors[address[1]];
        sensor.requests++;
        return {sensor.present};
    }
    float getTempC(const uint8_t *address)
    {
        const auto &sensor = fakeOneWireSensors[address[1]];
        return sensor.present ? sensor.tempC : DEVICE_DISCONNECTED_C;
    }
};
#endif
