#include "temperatures.hpp"

[[nodiscard]] bool Temperatures::setup(Config *config, Print &print)
{
    this->config = config;
    this->print = &print;

    int index = 0;
    int seed = 133;

    this->temperatures[index++].setup(config, Pin::T0, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T1, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T2, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T3, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T4, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T5, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T6, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T7, index * seed, print);
    this->temperatures[index++].setup(config, Pin::T8, index * seed, print);
}

void Temperatures::update()
{
    for (int i = 0; i < TemperaturesCount; i++)
    {
        Temperature *temperature = &this->temperatures[i];
        temperature->update();
    }
}

[[nodiscard]] float Temperatures::getTemperature(int index)
{
    if (index < 0 || index >= TemperaturesCount)
    {
        return 0.0f;
    }

    Temperature *temperature = &this->temperatures[index];
    float value = temperature->getTemperature();
    return value;
}
