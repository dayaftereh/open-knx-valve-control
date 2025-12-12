#ifndef SPI_SLAVE_HPP
#define SPI_SLAVE_HPP

#include <SPI.h>

#include "config.hpp"

class SPISlave
{
public:
    [[nodiscard]] bool setup(Config *config, Print &print);

    void update();

private:
  
    Print *print;
    Config *config;

    SPISettings settings;

};

#endif // SPI_SLAVE_HPP