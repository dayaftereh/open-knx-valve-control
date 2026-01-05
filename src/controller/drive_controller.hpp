#ifndef DRIVE_CONTROLLER_HPP
#define DRIVE_CONTROLLER_HPP

#include "config.hpp"

#include "drives.hpp"
#include "drive_current.hpp"

class DriveController
{
public:
    [[nodiscard]] bool setup(Config *config, Drives &drives, DriveCurrent &driveCurrent, Print &print);

    void update();

    [[nodiscard]] bool isHomed();

private:
    bool homed;

    Drives &drives;
    DriveCurrent &driveCurrent;

    Print *print;
    Config *config;
};

#endif // #define DRIVE_CONTROLLER_HPP
