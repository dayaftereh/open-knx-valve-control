#include "drive_current.hpp"

[[nodiscard]] bool DriveCurrent::setup(Config *config, Print &print)
{
    this->config = config;
    this->print = &print;

    // create the INA219
    static INA219 ina219(this->config->ina219Address, &Wire);
    // set the pointer to the INA219
    this->ina219 = &ina219;

    // start the ina219
    bool success = this->ina219->begin();
    if (!success)
    {
        return false;
    }

    // MaxCurrent is 200mA
    // Shunt is 200mOhm
    success = this->ina219->setMaxCurrentShunt(0.2, 0.2);
    if (!success)
    {
        return false;
    }

    return true;
}

void DriveCurrent::update()
{
    this->current = this->ina219->getCurrent_mA();
}

[[nodiscard]] float DriveCurrent::getCurrent()
{
    return this->current;
}