#ifndef DRIVE_CURRENT_HPP
#define DRIVE_CURRENT_HPP

#include <Wire.h>
#include <INA219.h>
#include "config.hpp"

class DriveCurrent
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);

    void update();

    [[nodiscard]] float getCurrent();

private:
    float current;

    Print *print;
    Config *config;
    INA219 *ina219;
};

#endif // #define DRIVE_CURRENT_HPP
