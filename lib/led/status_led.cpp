#include "status_led.hpp"

[[nodiscard]] bool StatusLed::setup(uint8_t led)
{
    this->pin = led;

    this->flag = false;
    this->isReset = false;

    this->counts = 0;

    this->error = 0;
    this->errorTimeout = 1000;

    this->resetCounts = 3;
    this->resetTimeout = 250;

    this->timer = 0;
    this->timeout = this->errorTimeout;

    pinMode(led, OUTPUT);

    return true;
}

void StatusLed::update()
{
    // write the flage
    digitalWrite(this->pin, this->flag);

    // check for error
    if (!this->isError())
    {
        this->flag = false;
        return;
    }

    // update timer and check if completed
    bool completed = this->updateTimer();
    if (!completed)
    {
        return;
    }

    // toggle the flage
    this->flag = !this->flag;

    // check for high flag, only count down on low flag
    if (this->flag)
    {
        return;
    }

    // decrement counts for blinks
    if (this->counts > 1)
    {
        this->counts--;
        return;
    }

    // check if current state was error
    if (!this->isReset)
    {
        this->configureReset();
        return;
    }

    // configure the error
    this->isReset = false;
    this->counts = this->error;
    this->timeout = this->errorTimeout;
}

[[nodiscard]] bool StatusLed::updateTimer()
{
    uint32_t now = millis();
    uint32_t elapsed = now - this->timer;
    if (elapsed < this->timeout)
    {
        return false;
    }

    this->timer = now;
    return true;
}

[[nodiscard]] bool StatusLed::isError()
{
    return this->error != 0;
}

void StatusLed::configureReset()
{
    this->isReset = true;
    this->counts = this->resetCounts;
    this->timeout = this->resetTimeout;
}
