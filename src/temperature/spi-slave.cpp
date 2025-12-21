#include "spi-slave.hpp"

namespace SPISlave
{

    Print *print;
    Config *config;
    Temperatures *temperatures;

    [[nodiscard]] bool setup(Config *config, Temperatures &temperatures, Print &print)
    {
        SPISlave::print = &print;
        SPISlave::config = config;
        SPISlave::temperatures = &temperatures;

        SPI0.CTRLA = (SPI_ENABLE_bm); // ENABLE Spi in slave mode
        SPI0.INTCTRL = (SPI_IE_bm);   // Enable Interrupts and trigger on recived

        // make the pin's ready
        pinMode(Pin::SPI_CS, INPUT);
        pinMode(Pin::SPI_SCK, INPUT);
        pinMode(Pin::SPI_MOSI, INPUT);
        pinMode(Pin::SPI_MISO, OUTPUT);

        return true;
    }

    void onISR()
    {
        // read the flag
        uint8_t flags = SPI0.INTFLAGS;
        if ((flags & SPI_IF_bm) == 0)
        {
            return;
        }
        // read the index for the temperature
        uint8_t index = SPI0.DATA;
        // get the temperature for the given index
        float temperature = SPISlave::temperatures->getTemperature(index);
        // convert the temperature to spi
        uint8_t data = uint8_t(temperature * SPISlave::config->spiTemperature);
        // send the temperature back
        SPI0.DATA = data;
    }

}

ISR(SPI0_INT_vect)
{
    // call the interrupt function
    SPISlave::onISR();
}