#include "../../lib/common/temperature_telemetry_policy.hpp"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

using namespace TemperatureTelemetry;

static Inputs allValid()
{
    Inputs input{};
    input.online = true;
    input.validMask = SensorMask;
    for (uint8_t i = 0; i < Channels; ++i)
        input.centiC[i] = static_cast<int16_t>(2100 + 20 * i);
    input.centiC[0] = 0;
    input.centiC[1] = -1125;
    return input;
}

static Proposal expected(Scheduler& scheduler, uint32_t t,
                         const Settings& settings, Inputs& input, Kind kind)
{
    const auto proposal = scheduler.select(t, settings, input);
    assert(proposal.kind == kind);
    return proposal;
}

static void offlineAndFirstSamples()
{
    Scheduler scheduler;
    scheduler.begin(0);
    Inputs input{};
    const Settings off{false, 60, 50};
    const Settings on{true, 60, 50};
    assert(scheduler.select(0, off, input).kind == Kind::None);

    auto link = expected(scheduler, 0, on, input, Kind::LinkOnline);
    assert(!link.online);
    // Without commit, a failed KNX library encode must be retried.
    assert(scheduler.select(100, on, input).kind == Kind::LinkOnline);
    scheduler.commit(link, 0);
    assert(scheduler.select(100, on, input).kind == Kind::None);
    auto mask = expected(scheduler, 250, on, input, Kind::ValidMask);
    assert(mask.mask == 0);
    scheduler.commit(mask, 250);
    assert(scheduler.select(500, on, input).kind == Kind::None);

    input = allValid();
    link = expected(scheduler, 500, on, input, Kind::LinkOnline);
    assert(link.online);
    scheduler.commit(link, 500);
    mask = expected(scheduler, 750, on, input, Kind::ValidMask);
    assert(mask.mask == SensorMask);
    scheduler.commit(mask, 750);

    uint32_t last = 750;
    for (uint8_t i = 0; i < Channels; ++i)
    {
        const uint32_t now = static_cast<uint32_t>(last + MinBusGapMs);
        auto temp = expected(scheduler, now, on, input, Kind::Temperature);
        assert(temp.channel == i);
        if (i == 0) assert(temp.centiC == 0);     // genuine zero
        if (i == 1) assert(temp.centiC == -1125); // negative temperatures
        scheduler.commit(temp, now);
        last = now;
    }
    assert(scheduler.select(last + 250, on, input).kind == Kind::None);
    assert(scheduler.select(last + 4900, on, input).kind == Kind::None);
    input.centiC[1] = -1060; // changed by >=50 centiC
    assert(scheduler.select(last + 5000, on, input).kind == Kind::Temperature);
}

static void periodicDeltaAndRecovery()
{
    Scheduler scheduler;
    scheduler.begin(0);
    Settings settings{true, 60, 50};
    Inputs input{};
    input.online = true;
    input.validMask = (1U << 0) | (1U << 1);
    input.centiC[0] = 2300;
    input.centiC[1] = -950;
    scheduler.commit(expected(scheduler, 0, settings, input, Kind::LinkOnline), 0);
    scheduler.commit(expected(scheduler, 250, settings, input, Kind::ValidMask), 250);
    scheduler.commit(expected(scheduler, 500, settings, input, Kind::Temperature), 500);
    scheduler.commit(expected(scheduler, 750, settings, input, Kind::Temperature), 750);
    assert(scheduler.select(1000, settings, input).kind == Kind::None);

    input.centiC[0] = 2330;   // below configured change threshold
    assert(scheduler.select(5500, settings, input).kind == Kind::None);
    input.centiC[0] = 2360;
    auto change = expected(scheduler, 5500, settings, input, Kind::Temperature);
    assert(change.channel == 0);
    scheduler.commit(change, 5500);
    assert(scheduler.select(5750, settings, input).kind == Kind::None);

    // Losing a sensor changes the validity mask, but never sends its cached T.
    input.validMask &= static_cast<uint16_t>(~(1U << 0));
    auto mask = expected(scheduler, 8000, settings, input, Kind::ValidMask);
    assert(mask.mask == 2);
    scheduler.commit(mask, 8000);
    assert(scheduler.select(8250, settings, input).kind == Kind::None);
    input.validMask |= 1;
    mask = expected(scheduler, 9000, settings, input, Kind::ValidMask);
    assert(mask.mask == 3);
    scheduler.commit(mask, 9000);
    auto recovered = expected(scheduler, 9250, settings, input, Kind::Temperature);
    assert(recovered.channel == 0); // first again, despite 5 sec minimum
    scheduler.commit(recovered, 9250);

    // Delta=0 disables change sends; periodic updates still happen.
    settings.changeDeltaCenti = 0;
    input.centiC[0] = 2500;
    assert(scheduler.select(14500, settings, input).kind == Kind::None);
    auto cyclic = expected(scheduler, 60750, settings, input, Kind::Temperature);
    assert(cyclic.channel == 1); // channel 1 sent at 750; round robin fair
}

static void transportOfflineAndInvalidValues()
{
    Scheduler s;
    s.begin(0);
    auto input = allValid();
    Settings settings{true, 60, 50};
    s.commit(expected(s, 0, settings, input, Kind::LinkOnline), 0);
    s.commit(expected(s, 250, settings, input, Kind::ValidMask), 250);

    input.online = false;  // UART timeout
    auto link = expected(s, 500, settings, input, Kind::LinkOnline);
    assert(!link.online);
    s.commit(link, 500);
    auto mask = expected(s, 750, settings, input, Kind::ValidMask);
    assert(mask.mask == 0);
    s.commit(mask, 750);
    assert(s.select(1000, settings, input).kind == Kind::None);

    // Prevent publishing a value outside the installed DS18B20 range.
    input.online = true;
    input.centiC[3] = 16000;
    s.commit(expected(s, 1500, settings, input, Kind::LinkOnline), 1500);
    mask = expected(s, 1750, settings, input, Kind::ValidMask);
    assert(mask.mask == (SensorMask & ~(1U << 3)));
    s.commit(mask, 1750);
    for (uint32_t t = 2000; t <= 5000; t += 250)
    {
        const auto ev = s.select(t, settings, input);
        if (ev.kind == Kind::Temperature)
        {
            assert(ev.channel != 3);
            s.commit(ev, t);
        }
    }
}

static void wrapAndClamping()
{
    Settings cfg{true, 1, 65535};
    cfg = bounded(cfg);
    assert(cfg.periodicSeconds == 10);
    assert(cfg.changeDeltaCenti == 1000);
    assert(bounded(Settings{true, 9000, 0}).periodicSeconds == 3600);

    Scheduler scheduler;
    uint32_t nearWrap = 0xFFFFFF00U;
    scheduler.begin(nearWrap);
    Inputs input{};
    input.online = true;
    input.validMask = 1;
    input.centiC[0] = 2050;
    scheduler.commit(expected(scheduler, nearWrap, cfg, input, Kind::LinkOnline), nearWrap);
    assert(scheduler.select(nearWrap + 249U, cfg, input).kind == Kind::None);
    scheduler.commit(expected(scheduler, nearWrap + 250U, cfg, input, Kind::ValidMask), nearWrap + 250U);
    scheduler.commit(expected(scheduler, nearWrap + 500U, cfg, input, Kind::Temperature), nearWrap + 500U);
    assert(scheduler.select(nearWrap + 600U, cfg, input).kind == Kind::None);
}

int main()
{
    offlineAndFirstSamples();
    periodicDeltaAndRecovery();
    transportOfflineAndInvalidValues();
    wrapAndClamping();
    puts("KNX015 telemetry native scheduler: PASS");
}
