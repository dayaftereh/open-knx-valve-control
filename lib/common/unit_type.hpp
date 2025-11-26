#ifndef UNIT_TYPE
#define UNIT_TYPE

#include <common.hpp>

enum class UnitType : uint8_t
{
    Unknown = 0,
    Temperature,
    Controller,
};

#endif // UNIT_TYPE