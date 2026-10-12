#define ARDUINO 10800
#include "../../lib/common/knx026_hmi_diagnostics.hpp"
#include <assert.h>
int main()
{
    RoomControlRuntime::Pipeline p;
    p.reset(0);
    Knx025::Supervisor supervisor;
    supervisor.reset(0);
    auto display = Knx026::capture(p, supervisor.diagnostics(), {}, 50);
    assert(!display.actualPhysicalAllOffProven);
    assert(!display.actualMotorReferenceProven);
    assert(display.hardwareDriveBlocked);
    for (auto& motor : display.motors)
    {
        assert(!motor.virtualPositionValid);
        assert(motor.physicalPositionQuality == Knx026::Quality::Unknown);
    }
    assert(!p.armNativeSimulation(50, {}));
}
