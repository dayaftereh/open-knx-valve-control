#include "spi-slave.hpp"

namespace SPISlave
{
    volatile bool rx;
    volatile uint8_t index;

    Print *print;
    Config *config;
    Temperatures *temperatures;

    [[nodiscard]] bool setup(Config *config, Temperatures &temperatures, Print &print)
    {
        SPISlave::rx = false;
        SPISlave::print = &print;
        SPISlave::config = config;
        SPISlave::temperatures = &temperatures;

        SPI0.CTRLA = (SPI_ENABLE_bm); // ENABLE Spi in slave mode
        SPI0.CTRLB = (SPI_BUFWR_bm);
        SPI0.INTCTRL = (SPI_IE_bm | SPI_TXCIE_bm); // Enable Interrupts and trigger on recived

        // make the pin's ready
        pinMode(Pin::SPI_CS, INPUT);
        pinMode(Pin::SPI_SCK, INPUT);
        pinMode(Pin::SPI_MOSI, INPUT);
        pinMode(Pin::SPI_MISO, OUTPUT);

        return true;
    }

    void onISR()
    {
        SPISlave::onReceiveCompleted();
    }

    void onTransmitCompleted()
    {
    }

    void onReceiveCompleted()
    {

        // read the index for the temperature
        uint8_t index = SPI0.DATA;
        SPISlave::index = index;
        SPISlave::rx = true;
        Serial.print("onReceiveCompleted");
        Serial.print(index);
        Serial.print("d");
        Serial.println(SPI0.INTFLAGS, BIN);
        // get the temperature for the given index
        float temperature = SPISlave::temperatures->getTemperature(index);
        // convert the temperature to spi
        uint8_t data = uint8_t(temperature * SPISlave::config->spiTemperature);
        // send the temperature back
        SPI0.DATA = data;
        Serial.println(SPI0.INTFLAGS,BIN);
        while ((SPI0.INTFLAGS & SPI_IF_bm) == 0)
        {
        }
        SPI0.DATA = 0;
        Serial.println("done");
    }

    void update()
    {
        if (!SPISlave::rx)
        {
            return;
        }
        SPISlave::rx = false;

        float temperature = SPISlave::temperatures->getTemperature(SPISlave::index);
        // convert the temperature to spi
        uint8_t data = uint8_t(temperature * SPISlave::config->spiTemperature);
        // send the temperature back
        SPI0.DATA = data;

        //  SPI0.DATA = 0;
    }

}

ISR(SPI0_INT_vect)
{
    // call the interrupt function
    SPISlave::onISR();
}