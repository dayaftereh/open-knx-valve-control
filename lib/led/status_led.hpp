#ifndef STATUS_LED_HPP
#define STATUS_LED_HPP

#include <common.hpp>

class StatusLed
{
public:
    [[nodiscard]] bool setup(uint8_t led);

    void update();

    template <typename T>
    [[nodiscard]] T getError()
    {
        return (T)this->error;
    }

    template <typename T>
    void setError(T err)
    {
        this->error = (uint16_t)err;
    }

private:
    [[nodiscard]] bool isError();
    [[nodiscard]] bool updateTimer();

    void configureReset();

    bool flag;
    bool isReset;

    uint8_t pin;

    uint16_t counts;

    uint16_t error;
    uint16_t errorTimeout;

    uint8_t resetCounts;
    uint16_t resetTimeout;

    uint32_t timer;
    uint16_t timeout;
};

#endif // _STATUS_LED_H