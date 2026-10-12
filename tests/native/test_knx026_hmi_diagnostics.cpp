#include "../../lib/common/knx026_hmi_diagnostics.hpp"
#include <assert.h>
#include <stdio.h>
using namespace Knx026;

static void checkDefaultAndOffline()
{
    RoomControlRuntime::Pipeline p;
    p.reset(0);
    Knx025::Supervisor supervisor;
    supervisor.reset(0);
    WaterInput water{};
    const Snapshot start = capture(p, supervisor.diagnostics(), water, 200);
    assert(start.roomKnx == LinkState::Unknown);
    assert(start.manifoldUart == LinkState::Unknown);
    assert(start.water[0].quality == Quality::Unknown);
    assert(start.water[8].quality == Quality::Unknown);
    assert(start.hardwareDriveBlocked && !start.actualPhysicalAllOffProven);
    assert(!start.actualMotorReferenceProven);
    for (const auto& m : start.motors)
    {
        assert(m.physicalPositionQuality == Quality::Unknown);
        assert(!m.requestedValid);
        assert(!m.virtualPositionValid);
    }
    water.observed = true;
    water.online = false;
    water.channels[0].quality = Quality::Fresh;
    water.channels[0].centiC = -250;
    const Snapshot stale = capture(p, supervisor.diagnostics(), water, 250);
    assert(stale.water[0].quality == Quality::Stale);
    assert(stale.water[0].centiC == -250);
    assert(stale.manifoldUart == LinkState::Offline);
    assert(stale.roomKnx == LinkState::Unknown);
    puts("KNX026 unknown/offline water and physical hardlock PASS");
}

static void checkZoneAndWaterSeparation()
{
    RoomControlRuntime::Pipeline p;
    p.reset(0);
    auto& settings = p.settings();
    settings.motorZone[0] = 1;
    settings.motorZone[1] = 1;
    settings.motorZone[2] = 2;
    settings.modes[0] = HeatingZone::Mode::RoomTemperature;
    settings.modes[1] = HeatingZone::Mode::DirectPercent;
    auto& a = p.inputs().zones[0];
    a.setpointCentiC = {2150, 100, true};
    a.roomActualCentiC = {1975, 100, true};
    a.regulatorOutputPermille = {350, 100, true};
    auto& b = p.inputs().zones[1];
    b.directDpt5001Raw = {128, 100, true};
    p.tick(200); // first mode change deliberately invalidates prior direct command
    b.directDpt5001Raw = {128, 250, true};
    p.tick(500);
    Knx025::Diagnostics fault{};
    fault.roomTransportMonitored = true;
    fault.roomTransportOnline = true;
    WaterInput water{};
    water.observed = true;
    water.online = true;
    water.channels[0] = {3400, 0, 0, Quality::Fresh};
    water.channels[1] = {2800, 0, 0, Quality::Fresh};
    const auto view = capture(p, fault, water, 500);
    assert(view.roomKnx == LinkState::Online);
    assert(view.water[0].centiC == 3400);
    assert(view.zones[0].actual.centiC == 1975);
    assert(view.zones[0].actual.quality == Quality::Fresh);
    assert(view.zones[0].setpoint.centiC == 2150);
    assert(view.zones[0].motorMask == 3);
    assert(view.zones[1].motorMask == 4);
    assert(view.zones[1].directFresh);
    assert(view.zones[1].directPermille == 502);
    assert(view.motors[0].zoneId == 1);
    assert(view.motors[1].zoneId == 1);
    assert(view.motors[2].zoneId == 2);
    assert(view.motors[2].requestedValid);
    assert(view.motors[2].requestedPermille == 502);
    assert(view.motors[2].physicalPositionQuality == Quality::Unknown);
    assert(!view.motors[2].virtualPositionValid);
    puts("KNX026 independent zone/water mapping and DPT5.001 PASS");
}

static void checkAgeAndFaultNeverRearms()
{
    RoomControlRuntime::Pipeline p;
    p.reset(0);
    p.settings().modes[0] = HeatingZone::Mode::DirectPercent;
    p.settings().motorZone[0] = 1;
    p.inputs().zones[0].directDpt5001Raw = {255, 100, true};
    p.tick(500);
    Knx025::Diagnostics d{};
    d.phase = Knx025::Phase::FaultLatched;
    d.firstFault = Knx025::Fault::RoomTransportLost;
    d.firstFaultZone = 1;
    d.firstFaultAtMs = 600;
    const auto view = capture(p, d, {}, 800);
    assert(view.fault.firstFault == Knx025::Fault::RoomTransportLost);
    assert(view.fault.firstFaultAtMs == 600);
    assert(!view.motors[0].requestedValid);
    assert(!view.zones[0].requestedValid);
    // input may be deliberately invalidated by PI epoch on initial reconfiguration.
    HeatingZone::TimedValue<int16_t> room{};
    room.value = 2100;
    room.receivedAtMs = 0xFFFFFF00UL;
    room.valid = true;
    assert(roomValue(room, 0x50U, 1000, true).quality == Quality::Fresh);
    assert(roomValue(room, 0x50U, 100, true).quality == Quality::Stale);
    room.value = 9000;
    assert(roomValue(room, 0x50U, 1000, false).quality == Quality::Invalid);
    puts("KNX026 fault-first masking, wrap-safe age and quality PASS");
}

static void checkMenuReadOnly()
{
    Menu menu;
    assert(menu.page == Page::Overview);
    menu.rotate(-1);
    assert(menu.page == Page::Faults);
    menu.rotate(2);
    assert(menu.page == Page::Water);
    menu.press();
    assert(menu.detail && menu.index == 0);
    menu.rotate(-1);
    assert(menu.index == 8);
    menu.rotate(2);
    assert(menu.index == 1);
    menu.press();
    assert(!menu.detail && menu.index == 0);
    menu.rotate(1);
    assert(menu.page == Page::Zones);
    menu.press();
    menu.rotate(9);
    assert(menu.index == 1);
    puts("KNX026 encoder model is navigation-only PASS");
}
int main()
{
    checkDefaultAndOffline();
    checkZoneAndWaterSeparation();
    checkAgeAndFaultNeverRearms();
    checkMenuReadOnly();
}
