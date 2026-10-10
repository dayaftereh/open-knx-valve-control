#include "temperature.hpp"

[[nodiscard]] bool Temperature::setup(Config *config, Pin_t pin,
                                      uint32_t staggerMs, Print &print)
{
    (void)print; // Keep the original setup signature; no debug on the sensor bus.
    if (config == nullptr)
        return false;

    config_ = config;
    resolution_ = selectedResolution();

    oneWire_.begin(pin);
    dallas_.setOneWire(&oneWire_);

    // DallasTemperature 4.0.5 can return immediately after STARTCONVO.
    // External 3-wire powering is expected by the PCB; reject parasite mode
    // when discovered. Avoid DallasTemperature::begin() which retries and
    // delays even when no probe is connected.
    dallas_.setWaitForConversion(false);
    dallas_.setCheckForConversion(false);
    dallas_.setAutoSaveScratchPad(false);

    sampler_.begin(millis(), staggerMs, periodMs(),
                   TemperatureSampler::conversionWaitMs(resolution_));
    return true;
}

[[nodiscard]] uint8_t Temperature::selectedResolution() const
{
    const uint8_t requested = config_->resolution;
    return requested >= 9 && requested <= 12 ? requested : 12;
}

[[nodiscard]] uint32_t Temperature::periodMs() const
{
    float seconds = config_->updateRate;
    if (seconds != seconds || seconds <= 0.0f) // NaN/broken persisted data
        seconds = 10.0f;
    if (seconds < 2.0f)
        seconds = 2.0f;
    if (seconds > 3600.0f)
        seconds = 3600.0f;
    return static_cast<uint32_t>(seconds * 1000.0f);
}

[[nodiscard]] bool Temperature::discoverSensor(bool &parasitePowered)
{
    parasitePowered = false;
    DeviceAddress found{};

    // The channel has its own 1-Wire bus. A short ROM search is scheduled
    // only when probing/re-probing, rather than on every temperature read.
    oneWire_.reset_search();
    if (!oneWire_.search(found))
        return false;
    if (!dallas_.validAddress(found) || !dallas_.validFamily(found))
        return false;

    parasitePowered = dallas_.readPowerSupply(found);
    if (parasitePowered)
        return true; // The state machine rejects unqualified parasite power.

    // No EEPROM wear on every reboot/probe. Only scratchpad configuration;
    // setResolution() validates the scratchpad via DallasTemperature.
    if (!dallas_.setResolution(found, resolution_, true))
        return false;

    for (uint8_t i = 0; i < sizeof(address_); ++i)
        address_[i] = found[i];
    return true;
}

void Temperature::update()
{
    if (config_ == nullptr)
        return;

    sampler_.setPeriod(periodMs());
    const uint32_t now = millis();

    switch (sampler_.nextAction(now))
    {
    case TemperatureSampler::Action::Discover:
    {
        bool parasite = false;
        const bool found = discoverSensor(parasite);
        sampler_.onDiscovered(millis(), found, parasite);
        break;
    }
    case TemperatureSampler::Action::StartConversion:
    {
        // The library does not wait for 9..12-bit conversion to complete.
        const auto requested = dallas_.requestTemperaturesByAddress(address_);
        sampler_.onConversionStarted(millis(), requested.result);
        break;
    }
    case TemperatureSampler::Action::FinishConversion:
    {
        // DallasTemperature checks the scratchpad CRC and reports failures
        // as negative sentinel values; the core keeps the last good value.
        const float celsius = dallas_.getTempC(address_);
        sampler_.onConversionFinished(millis(), celsius);
        break;
    }
    case TemperatureSampler::Action::None:
        break;
    }
}

[[nodiscard]] TemperatureSampler::Snapshot
Temperature::getSnapshot(uint32_t now) const
{
    return sampler_.snapshot(now);
}

[[nodiscard]] bool Temperature::isConnected() const
{
    return (getSnapshot(millis()).flags & TemperatureSampler::Valid) != 0;
}

[[nodiscard]] float Temperature::getTemperature() const
{
    const auto result = getSnapshot(millis());
    if ((result.flags & TemperatureSampler::Valid) == 0)
        return DEVICE_DISCONNECTED_C;
    return static_cast<float>(result.centiC) / 100.0f;
}
