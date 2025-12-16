#include "spi-slave.hpp"

[[nodiscard]] bool SPISlave::setup(Config *config, Print &print)
{

    pinMode(Pin::SPI_CS, INPUT);
    pinMode(Pin::SPI_SCK, INPUT);
    pinMode(Pin::SPI_MOSI, INPUT);
    pinMode(Pin::SPI_MISO, OUTPUT);
}

void SPISlave::update()
{
}

void ISR_SPI()
{
}