#include "spi-slave.hpp"

[[nodiscard]] bool SPISlave::setup(Config *config, Print &print)
{

    SPI.begin();

    pinMode(Pin::MOSI_CS, INPUT);
    pinMode(Pin::SCK_CS, INPUT);
    pinMode(Pin::MISO_CS, OUTPUT);
    pinMode(Pin::SPI_CS, INPUT);

    SPCR |= _BV(SPE);

    attachInterrupt(Pin::SPI_CS, ISR_SPI, FALLING);
}

void SPISlave::update()
{
}

void ISR_SPI()
{
}