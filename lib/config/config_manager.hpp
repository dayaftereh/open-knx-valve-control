#ifndef CONFIG_MANAGER_HPP
#define CONFIG_MANAGER_HPP

#include <crc.hpp>
#include <EEPROM.h>
#include <Arduino.h>

using Crc8_t = uint8_t;           //@brief typedef for 1-byte crc
using EepromAddress_t = uint16_t; //@brief typedef for internal-eeprom addresses

typedef bool (*Callback_t)(T& n);

template <typename T>
class ConfigManager
{
public:
    [[nodiscard]] bool setup(EepromAddress_t baseAddr, Print &pr, Callback_t func, bool autosave = true)
    {
        this->print = &pr;
        this->baseAddress = baseAddr;
        this->callback = func;
        this->eepromSize = 512;

        return this->load(autosave);
    }

    void setEEPROMSize(size_t eepromSize)
    {
        this->eepromSize = eepromSize;
    }

    void setConfig(T conf, bool saveConf = true)
    {
        this->config = conf;

        if (saveConf)
        {
            this->save();
        }
    }

    [[nodiscard]] constexpr const T *getConfig() const
    {
        return &(this->config);
    }

    [[nodiscard]] constexpr const T &getConfigRef() const
    {
        return this->config;
    }

    [[nodiscard]] constexpr T *getConfig()
    {
        return &(this->config);
    }

    [[nodiscard]] constexpr T &getConfigRef()
    {
        return this->config;
    }

    [[nodiscard]] bool printConfig() const
    {
        if (this->print == nullptr)
        {
            return false;
        }

        this->config.print(*this->print);

        return true;
    }

    [[nodiscard]] bool save() const
    {
        bool success = this->writeConfigToEeprom(this->config);
        return success;
    }

    [[nodiscard]] bool load(bool autosave = true)
    {
        // try to read from eeprom
        bool success = this->readConfigFromEeprom(this->config);
        if (success)
        {
            return true;
        }

        return this->callbackAndSave(autosave);
    }

    [[nodiscard]] bool loadDefault() noexcept
    {
        return this->callback(this->config);
    }

protected:
    [[nodiscard]] bool callbackAndSave(bool autosave = true)
    {

        // load config from calback
        bool success = this->callback(this->config);

        // check if callback was success
        if (!success)
        {
            return false;
        }

        // save config if autosave true
        if (autosave)
        {
            success = this->save();
        }

        return success;
    }

    void openEEPROM() const
    {
#if defined(ESP8266) || defined(ESP32)
        // start the read for the espXX boards
        EEPROM.begin(this->eepromSize);
#endif
    }

    [[nodiscard]] bool closeEEPROM() const
    {
#if defined(ESP8266) || defined(ESP32)
        // close the eeprom
        bool success = EEPROM.end();
        return success;
#else
        return true;
#endif
    }

    [[nodiscard]] bool writeConfigToEeprom(const T &t) const
    {

        // open the eeprom for writting
        this->openEEPROM();

        auto crcAddress = this->baseAddress + sizeof(t);

        // return false if the address is not valid
        if (crcAddress + sizeof(Crc8_t) >= EEPROM.length())
        {
            this->closeEEPROM();
            return false;
        }

        Crc8_t crc = this->calculateConfigCrc(t);

        EEPROM.put(this->baseAddress, t);
        EEPROM.put(crcAddress, crc);

        // close the eeprom
        bool success = this->closeEEPROM();
        return success;
    }

    [[nodiscard]] bool readConfigFromEeprom(T &t)
    {
        // open the eeprom for reading
        this->openEEPROM();

        auto crcAddress = this->baseAddress + sizeof(t);

        // return false if the address is not valid
        if ((crcAddress + sizeof(Crc8_t)) >= EEPROM.length())
        {
            // close the eeprom
            this->closeEEPROM();
            return false;
        }

        Crc8_t crc;
        EEPROM.get(this->baseAddress, t);
        EEPROM.get(crcAddress, crc);

        // close the eeprom
        bool success = this->closeEEPROM();
        if (!success)
        {
            return false;
        }

        // check the crc
        bool b = (this->calculateConfigCrc(t) == crc);
        return b;
    }

    [[nodiscard]] Crc8_t calculateConfigCrc(const T &t) const
    {
        return calculateCrc((uint8_t *)&t, sizeof(t), Crc8Options);
    }

private:
    size_t eepromSize;

    T config;
    Print *print;
    Callback_t callback;
    EepromAddress_t baseAddress;
};

#endif // _CONFIG_MANAGER_HPP