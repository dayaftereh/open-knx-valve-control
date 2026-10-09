# Architecture and repository inventory

Baseline: 2026-10-09. This page distinguishes observed project files from unimplemented requirements.

## Existing architecture

- Main electronics: schematic V1.2 at [PDF](../schematic/sch_knx-valve-control_v1.2.pdf), [schematic JSON](../schematic/sch_knx-valve-control_v1.2.json), and [PCB JSON](../schematic/pcb_knx-valve-control_v1.2.json). Files verified present; detailed PDF visual inspection remains pending.
- The UPDI programmer has separate schematic/PCB V1.4 files and is not evidence of a newer main controller PCB.
- RP2040 controller environment: [controller.ini](../src/controller/controller.ini); Arduino-Pico, OpenKNX stack, INA219 and PCF8574 dependencies.
- RP2040 [main.cpp](../src/controller/main.cpp): serial KNX startup, programming LED/button and framework loop; no complete motor positioning or room thermostat implementation here yet.
- Controller [config.hpp](../src/controller/config.hpp): eight drive pins D10-D17, shared control inputs D18/D19, temperature interface, KNX pins, INA219 and PCF8574 addresses and inverse direction setting.
- Temperature unit: ATtiny3216 [temperature.ini](../src/temperature/temperature.ini), OneWire/DallasTemperature, serial dispatcher and SPI slave in [main.cpp](../src/temperature/main.cpp).
- KNX artifacts: [product XML](../assets/open-knx-valve-control.xml), [Sensor XML](../assets/Sensor.xml), and [generated header](../include/knxprod.hpp). Existing files are not by themselves proof of successful ETS import.
- Mechanical design: [FreeCAD/STL DIN-rail assets](../assets/3d-models/knx-value-control/).
- Earlier README with proposed BOM: [component inventory](../.github/README.md).
- Verified motor information: [Homematic IP HmIP-VDMOT actuator](ACTUATOR_HMIP_VDMOT.md), article 153309A0 / Amazon B07RJZ5F1Y.

## Proposed data flow

```text
ETS6 parameters ---> KNX product database and device configuration
KNX setpoint / actual temperature or 0..100% target
   -> KNX bus -> RP2040
   -> logical zone controller (up to 8 zones)
   -> assigned physical valve channels (up to 8)
   -> single-motor motion scheduler
   -> driver outputs plus INA219 shared current sensing
   -> endpoint detection, timing estimate and diagnostic/status telegrams
ATtiny3216 temperature acquisition -> controller, pending confirmed mapping
```

Each physical channel belongs to at most one room zone. Multiple channels can share one zone. One zone target applies to all member valves; each valve has independent stroke timing and state. Only one motor moves at a time per current hardware constraint. Refer to [ETS and control concept](ETS_AND_CONTROL_CONCEPT.md) for state machines and parameter proposals.

## Electrical facts and open checks

The actual actuator is **Homematic IP HmIP-VDMOT (153309A0)** with manufacturer-rated **3.3 V DC SELV**, **120 mA maximum current consumption**, **4.3 +/- 0.3 mm stroke** and M30 x 1.5 connection. **120 mA is NOT an official end-stop threshold**. Running/stall current, end-stop signature and real movement time must be measured; see [motor documentation](ACTUATOR_HMIP_VDMOT.md). Motor power supply, protection, stall behavior, driver selection, INA219 shunt/current path and switching require explicit schematic V1.2 and hardware verification. Timed travel estimates are not encoder position measurements.

The existing former README describes a 230 V supply and mentions STKNX, ATTINY3216, INA219, PCF8574 and TB6612FNG. Confirm their precise presence/usage against the hardware and PDF before drawing electrical conclusions. Do not test powered end-stop operation without safe electrical protections, independent movement timeout and validated current sensing.

## Open verification tasks

1. Render and visually inspect every sheet of main-board schematic V1.2; compare with PCB JSON and firmware pin definitions.
2. Test the identified HmIP-VDMOT and installed valve: polarity, motor supply, running/stall/endpoint current characteristics and opening/closing timing (not in the manual).
3. Verify the shared-current signal identifies the selected motor and no other drive is enabled concurrently.
4. Map local temperature channels to logical zones, including the external KNX sensor option.
5. Validate the KNX XML, generated headers, product IDs, parameter constraints and ETS6 product import.
6. Execute reproducible builds and hardware tests before claiming features implemented.

Current documented Git baseline before writing: `main`, clean, `ef245de` (2026-02-11). Work in this pass is documentation-only.
