#ifndef SPI_SLAVE_HPP
#define SPI_SLAVE_HPP

#include <SPI.h>

#include "config.hpp"
#include "temperatures.hpp"

namespace SPISlave
{
    [[nodiscard]] bool setup(Config *config, Temperatures &temperatures, Print &print);

    void onISR();

}

#endif // SPI_SLAVE_HPP