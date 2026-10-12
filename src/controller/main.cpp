#include <Arduino.h>

#include <knx.h>
#include <TPUart/Interface/ArduinoSerial.h>

#include "config.hpp"
#include "knxprod.hpp"
#include "temperature_bridge.hpp"
#include "temperature_publisher.hpp"
#include "room_control_runtime.hpp"
#include "knx024_room_dpt_adapter.hpp"
#include "knx025_fault_supervisor.hpp"

TemperatureBridge temperatureBridge;
TemperaturePublisher temperaturePublisher;
// KNX024: compile-check the PROPOSED AppVersion3 room KO parser but do
// not bind any AppVersion2 KNX bus communication object, because KO36+
// exist in the currently generated product). No bus or motor writes.
static_assert(Knx024::FirstRoomObject == 36 &&
              Knx024::LastRoomObject == 67,
              "KNX024 proposed room KO ABI changed");
// KNX023: software-only PI/zone target engine. RP2040 build has no motor
// mock backend, cannot arm simulation, and never touches motor GPIO pins.
RoomControlRuntime::Pipeline roomControlRuntime;
// KNX025: passive software fault diagnostics only; no ETS V3 listener,
// motor GPIO, physical watchdog or KNX diagnostic object is connected.
Knx025::Supervisor roomFaultSupervisor;
uint32_t lastRoomSoftwareTickMs = 0;

void setupKnx()
{
    // KNX TP remains on the independent Serial1/UART0 interface.
    auto platform = knx.platform();
    platform.interface(new TPUart::Interface::ArduinoSerial(Serial1));

    knx.readMemory();
    knx.ledPin(Pin::ProgramLED);
    knx.buttonPin(Pin::ProgramButton);
    knx.start();
}

void setupTemperatureLink()
{
    // RP2040 GPIO8 (UART1 TX) -> ATtiny PA2 RX, GPIO9 (UART1 RX)
    // <- ATtiny PA1 TX. Configure pins before starting the port.
    const bool txReady = Serial2.setTX(Pin::TemperaturesTx);
    const bool rxReady = Serial2.setRX(Pin::TemperaturesRx);
    if (!txReady || !rxReady)
    {
        Serial.println("Temperature UART1 pin setup failed");
        return; // No polling or unconfigured UART activity.
    }
    Serial2.begin(TemperatureBridge::Baud);
    temperatureBridge.setup(Serial2);
}

void setup()
{
    Serial.begin(DefaultSerialBaud);
    ArduinoPlatform::SerialDebug = &Serial;

    // Completely inert, DISARMED reference model until a future verified
    // ETS-input adapter and independent KNX004 hardware safety gate exist.
    lastRoomSoftwareTickMs = millis();
    roomControlRuntime.reset(lastRoomSoftwareTickMs);
    roomFaultSupervisor.reset(lastRoomSoftwareTickMs);

    setupTemperatureLink();
    setupKnx();
    temperaturePublisher.begin(millis());
}

void loop()
{
    knx.loop();

    // UART remains active for internal diagnosis before ETS commissioning.
    temperatureBridge.update();

    // Run the portable KNX019/KNX008 room computation at a bounded
    // cadence. All modes are DISABLED and all inputs invalid by default.
    // Compile-time ARDUINO fence keeps KNX020 permanently DISARMED and
    // emits NO Start/Stop, PWM, GPIO or KNX group-object side effects.
    const uint32_t softwareNow = millis();
    if (static_cast<uint32_t>(softwareNow - lastRoomSoftwareTickMs) >= 100UL)
    {
        lastRoomSoftwareTickMs = softwareNow;
        roomControlRuntime.tick(softwareNow);
        // The ATtiny T0..T8 source is manifold TELEMETRY only. Neither
        // an ETS commissioning flag nor probe-online proves room transport
        // health: future KNX018 must add verified ETS group access.
        Knx025::Signals softwareSignals{};
        softwareSignals.manifoldTelemetryObserved =
            temperatureBridge.hasSnapshot();
        softwareSignals.manifoldTelemetryOnline =
            temperatureBridge.online(softwareNow);
        roomFaultSupervisor.observeFirmware(
            roomControlRuntime, softwareSignals, softwareNow);
    }

    if (!knx.configured())
        return;

    // KNX015: transmit only valid cached T0..T8 and quality diagnostics;
    // at most one KNX GroupObject per loop, bounded by ETS parameters.
    temperaturePublisher.update(temperatureBridge, millis());
}
