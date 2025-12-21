#ifndef DRIVES_HPP
#define DRIVES_HPP

#include <Wire.h>
#include <PCF8574.h>
#include "config.hpp"

#define DrivesCount 9

class Drives
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);

    void update();

    void close(uint8_t index);

    void open(uint8_t index);

    void stop();

private:
    void updateIn();
    void updateActive();

    bool in1;
    bool in2;

    uint8_t active;
    uint8_t lastActive;

    Print *print;
    Config *config;

    PCF8574 *pcf8574;
};

#endif // #define DRIVES_HPP
