#include "../../src/temperature/sampler_core.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace TemperatureSampler;

static void startup_missing_and_recovery()
{
    Core core;
    core.begin(1000, 500, 10000, conversionWaitMs(12));
    assert(core.nextAction(1000) == Action::None);
    assert(core.nextAction(1499) == Action::None);
    assert(core.nextAction(1500) == Action::Discover);

    core.onDiscovered(1500, false, false);
    auto missing = core.snapshot(1500);
    assert((missing.flags & Valid) == 0);
    assert((missing.flags & Error) != 0);
    assert(missing.fault == Fault::NoSensor);
    assert(missing.ageSeconds == 65535);
    assert(core.nextAction(11499) == Action::None);
    assert(core.nextAction(11500) == Action::Discover);

    core.onDiscovered(11500, true, false);
    assert(core.nextAction(11500) == Action::StartConversion);
    core.onConversionStarted(11500, true);
    assert(core.nextAction(12269) == Action::None);
    assert((core.snapshot(12000).flags & Converting) != 0);
    assert(core.nextAction(12270) == Action::FinishConversion);

    core.onConversionFinished(12270, 0.0f);
    auto zero = core.snapshot(12270);
    assert((zero.flags & Valid) != 0);
    assert((zero.flags & Error) == 0);
    assert(zero.centiC == 0);
    assert(zero.ageSeconds == 0);
    assert(core.nextAction(21499) == Action::None);
    assert(core.nextAction(21500) == Action::StartConversion);

    core.onConversionStarted(21500, true);
    core.onConversionFinished(22270, -15.125f);
    auto negative = core.snapshot(23270);
    assert((negative.flags & Valid) != 0);
    assert(negative.centiC == -1513);
    assert(negative.ageSeconds == 1);

    core.onConversionStarted(31500, true);
    core.onConversionFinished(32270, -127.0f);
    auto bad = core.snapshot(32270);
    assert((bad.flags & Valid) == 0);
    assert((bad.flags & HasSample) != 0); // keep last-known-good
    assert((bad.flags & Error) != 0);
    assert(bad.fault == Fault::ReadFailed);
    assert(bad.centiC == -1513);
    assert(core.nextAction(41500) == Action::Discover);
    core.onDiscovered(41500, true, false);
    const auto recovering = core.snapshot(41500);
    assert((recovering.flags & Valid) == 0);
    assert(recovering.fault == Fault::Recovering);
    core.onConversionStarted(41500, true);
    core.onConversionFinished(42270, -9.25f);
    assert((core.snapshot(42270).flags & Valid) != 0);
    assert(core.snapshot(42270).centiC == -925);
}

static void test_stale_and_parasite()
{
    Core core;
    core.begin(0, 0, 10000, 770);
    core.onDiscovered(0, true, false);
    core.onConversionStarted(0, true);
    core.onConversionFinished(770, 25.5f);
    auto fresh = core.snapshot(770);
    assert((fresh.flags & Valid) != 0);
    assert(fresh.centiC == 2550);
    auto stale = core.snapshot(30770);
    assert((stale.flags & Stale) != 0);
    assert((stale.flags & Valid) == 0);
    assert(stale.fault == Fault::SampleStale);
    assert(stale.ageSeconds == 30);

    Core parasite;
    parasite.begin(0, 0, 10000, 770);
    parasite.onDiscovered(0, true, true);
    auto denied = parasite.snapshot(0);
    assert(denied.fault == Fault::ParasitePower);
    assert(parasite.nextAction(5000) == Action::None);
    assert(parasite.nextAction(10000) == Action::Discover);
}

static void sensor_faults_and_time_wrap()
{
    Core core;
    const uint32_t nearWrap = 0xFFFFFF00UL;
    core.begin(nearWrap, 500, 10000, 770);
    assert(core.nextAction(nearWrap) == Action::None);
    const uint32_t atStart = static_cast<uint32_t>(nearWrap + 500U);
    assert(core.nextAction(atStart) == Action::Discover);
    core.onDiscovered(atStart, true, false);
    core.onConversionStarted(atStart, true);
    assert(core.nextAction(atStart + 769U) == Action::None);
    core.onConversionFinished(atStart + 770U, 85.0f);
    assert(core.snapshot(atStart + 770U).fault == Fault::PowerOn85);
    assert((core.snapshot(atStart + 770U).flags & Valid) == 0);
    assert(core.nextAction(atStart + 10000U) == Action::StartConversion);

    core.onConversionStarted(atStart + 10000U, true);
    core.onConversionFinished(atStart + 10770U, 20.0f);
    auto recovered = core.snapshot(atStart + 10770U);
    assert((recovered.flags & Valid) != 0);
    assert(recovered.centiC == 2000);
    assert((core.snapshot(atStart + 11770U).flags & Valid) != 0);
}

static void bounds_and_rate()
{
    static_assert(boundedPeriod(10) == 2000, "minimum interval");
    static_assert(boundedPeriod(99999999UL) == 3600000, "maximum interval");
    static_assert(conversionWaitMs(10) == 208, "10 bit");
    static_assert(conversionWaitMs(11) == 395, "11 bit");
    static_assert(acceptableTemperature(-55.0f), "minimum sensor temperature");
    static_assert(acceptableTemperature(125.0f), "maximum sensor temperature");
    static_assert(!acceptableTemperature(-254.0f), "sensor fault");
    static_assert(!acceptableTemperature(126.0f), "above sensor range");

    Core core;
    core.begin(0, 0, 100, 114);
    core.onDiscovered(0, true, false);
    core.onConversionStarted(0, true);
    core.onConversionFinished(114, 3.0f);
    assert(core.nextAction(1999) == Action::None);
    assert(core.nextAction(2000) == Action::StartConversion);
}

int main()
{
    startup_missing_and_recovery();
    test_stale_and_parasite();
    sensor_faults_and_time_wrap();
    bounds_and_rate();
    puts("KNX013 native sampler core tests: PASS");
    return 0;
}
