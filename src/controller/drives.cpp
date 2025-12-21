#include "drives.hpp"

[[nodiscard]] bool Drives::setup(Config *config, Print &print)
{
    this->print = &print;
    this->config = config;

    // create the PCF8574
    static PCF8574 pcf8574(this->config->drivesAddress, &Wire);
    // set the pointer to the PCF8574
    this->pcf8574 = &pcf8574;

    // begin and set all outputs low
    bool success = this->pcf8574->begin(0);
    if (!success)
    {
        return false;
    }

    this->active = 0;
    this->lastActive = 0;

    pinMode(Pin::IN_1, OUTPUT);
    pinMode(Pin::IN_2, OUTPUT);

    digitalWrite(Pin::IN_1, false);
    digitalWrite(Pin::IN_2, false);

    this->in1 = false;
    this->in2 = false;

    return true;
}

void Drives::update()
{
    this->updateIn();
    this->updateActive();
}

void Drives::updateActive()
{
    // get the last active
    uint8_t active = this->lastActive;
    // update last active with the current active
    this->lastActive = this->active;
    // check if the active has changed
    if (active == this->lastActive)
    {
        return;
    }
    // write the new active to io expander
    this->pcf8574->write8(this->lastActive);
}

void Drives::updateIn()
{
    digitalWrite(Pin::IN_1, this->in1);
    digitalWrite(Pin::IN_2, this->in2);
}

void Drives::close(uint8_t index)
{
    if (index >= DrivesCount)
    {
        return;
    }
    this->active = 1 << index;
    this->in1 = this->config->inverseOpenClose;
    this->in2 = !this->config->inverseOpenClose;
}

void Drives::open(uint8_t index)
{
    if (index >= DrivesCount)
    {
        return;
    }
    this->active = 1 << index;
    this->in1 = !this->config->inverseOpenClose;
    this->in2 = this->config->inverseOpenClose;
}

void Drives::stop()
{
    this->in1 = false;
    this->in2 = false;
    this->active = 0;
}