#ifndef TEMPERATURES_HPP
#define TEMPERATURES_HPP

#include "temperature.hpp"

#define TemperaturesCount 9

class Temperatures
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);

    void update();
private:
  
    Print *print;
    Config *config;

    Temperature temperatures[TemperaturesCount];
};

#endif // TEMPERATURES_HPP