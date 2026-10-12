#ifndef OPENKNX_NATIVE_KNX_MOCK_HPP
#define OPENKNX_NATIVE_KNX_MOCK_HPP
#include <stdint.h>
#include <assert.h>

struct Dpt
{
    uint8_t main;
    uint8_t sub;
};
static constexpr Dpt DPT_Value_Temp{9, 1};
static constexpr Dpt DPT_Bool{1, 2};
static constexpr Dpt DPT_Value_2_Ucount{7, 1};

struct KNXValue
{
    float value = 0;
    KNXValue(bool v) : value(v ? 1.0f : 0.0f) {}
    KNXValue(uint16_t v) : value(static_cast<float>(v)) {}
    KNXValue(float v) : value(v) {}
};

struct GroupObject
{
    float last = 0;
    uint8_t main = 0;
    uint8_t sub = 0;
    uint16_t calls = 0;
    bool allow = true;

    bool value(const KNXValue& v, Dpt d)
    {
        if (!allow) return false;
        last = v.value;
        main = d.main;
        sub = d.sub;
        ++calls;
        return true;
    }
};

class KNXMock
{
public:
    bool commissioned = false;
    uint8_t param6 = 0;
    uint16_t period = 60;
    uint16_t delta = 50;
    GroupObject objects[36] = {};

    bool configured() const { return commissioned; }
    uint8_t paramByte(uint16_t addr) const
    {
        assert(addr == 6);
        return param6;
    }
    uint16_t paramWord(uint16_t addr) const
    {
        assert(addr == 7 || addr == 9);
        return addr == 7 ? period : delta;
    }
    GroupObject& getGroupObject(uint16_t number)
    {
        assert(number > 0 && number <= 35);
        return objects[number];
    }
};
extern KNXMock knx;
#endif
