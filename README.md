# Open KNX Valve Control

Controller for up to **eight motorized underfloor-heating valve actuators** with KNX integration. This repository contains firmware, KNX product-description sources, electronics schematics/PCB exports and DIN-rail enclosure models.

> **Project status (2026-10-09):** Architecture and ETS parameterization are being specified. The current RP2040 controller firmware initializes KNX, but does **not yet implement the complete valve-control, positioning, grouping or room-temperature control algorithms**. This document separates confirmed repository contents from requirements and concepts.

## Documentation

- [Architecture and verified project inventory](docs/ARCHITECTURE.md)
- [Schematic V1.2 electrical review and open findings](docs/SCHEMATIC_V1_2_REVIEW.md)
- [5-V-Externversorgung, Jumper und KNX-Leistungsbudget](docs/POWER_SUPPLY_CONCEPT.md)
- [PCB V1.2 static layout/pad audit](docs/PCB_V1_2_AUDIT.md)
- [Verified HmIP-VDMOT actuator specification](docs/ACTUATOR_HMIP_VDMOT.md)
- [ETS application, heating zones and regulation concept](docs/ETS_AND_CONTROL_CONCEPT.md)
- [Actual ETS product XML and OpenKNXproducer audit](docs/ETS_PRODUCT_AUDIT.md)
- [Legacy (potentially outdated) BOM and component list](.github/README.md)

## Hardware and source material

| Topic | Repository files | Notes |
| --- | --- | --- |
| Main board schematic V1.2 | [PDF](schematic/sch_knx-valve-control_v1.2.pdf), [JSON](schematic/sch_knx-valve-control_v1.2.json) | PDF visually reviewed (one sheet); see [electrical findings](docs/SCHEMATIC_V1_2_REVIEW.md) |
| Main board PCB V1.2 | [JSON](schematic/pcb_knx-valve-control_v1.2.json) | Four-layer pad/net static audit documented; no formal DRC or physical validation |
| UPDI programmer V1.4 | [PDF](schematic/sch_updi_programmer_v1.4.pdf), [schematic JSON](schematic/sch_updi_programmer_v1.4.json), [PCB JSON](schematic/pcb_updi_programmer_v1.4.json) | Separate programmer, not main-board revision |
| RP2040 controller | [main.cpp](src/controller/main.cpp), [configuration](src/controller/config.hpp) | KNX startup currently present |
| ATtiny3216 temperature unit | [main.cpp](src/temperature/main.cpp), [configuration](src/temperature/config.hpp) | Separate temperature acquisition firmware |
| ETS product source | [XML](assets/open-knx-valve-control.xml), [sensor XML](assets/Sensor.xml), [generated header](include/knxprod.hpp) | Existing artifacts; not proof of a released/import-tested .knxprod |
| DIN-rail enclosure | [3D models](assets/3d-models/knx-value-control/) | FreeCAD/STL |

Tooling: PlatformIO (Arduino/C++17), RP2040 (Earle Philhower core, OpenKNX stack), ATtiny3216. KNX ETS6 v6.4.1 has been detected on the LLO Desktop computer, but no new application package was built or imported during this documentation pass.

## Functional target

Every physical actuator is individually assignable to a room/heating zone, and a zone may combine **one or several heating circuits**. A room can use one of two configurable control modes:

1. **Room temperature:** KNX setpoint and measured room temperature; one control output shared by all actuators assigned to the zone.
2. **Direct opening:** KNX position demand from **0 to 100%**, without a temperature-controller calculation.

The actual actuator is now identified as **Homematic IP HmIP-VDMOT (153309A0, Amazon ASIN B07RJZ5F1Y)**. The manufacturer specifies **3.3 V DC SELV**, **120 mA maximum current consumption** and **4.3 +/- 0.3 mm mechanical stroke**. The 120 mA specification is **not a verified current-based end-stop threshold**: INA219 traces from the real valve installation are needed. The controller concept can drive **only one motor at a time**. After a reference closing run, travel time maps demanded percentage to an estimated position. Configurable full-stroke timing, timeout, current thresholds and re-reference policy are necessary. Do **not** treat time-derived position as an absolute encoder measurement.

Detailed behavior, ETS parameter tables, safety behavior, scheduling and open design decisions are in [the control concept](docs/ETS_AND_CONTROL_CONCEPT.md).

## Power supply: OPEN DECISION

The V1.2 board currently derives 3.3 V from KNX or USB. The project owner is considering a **dedicated external isolated 5 V SELV supply** because the STKNX 150 mA **buck-output** rating (distinct from the 30 mA KNX-bus extraction) may not cover the full board plus a 3.3 V / 120 mA actuator. This is **not yet measured**.

**No 5 V may be applied to a 3.3 V motor or to `M_VCC`.** Board V1.2 includes solder jumper `JMP1` for the KNX power path (not a ready external input), two Schottky diodes in the USB-to-U6 path, and a TSR 1-2433 requiring **at least 4.75 V at its own input**. Read the actual jumper/pad map and two proposed external-supply architectures in [POWER_SUPPLY_CONCEPT.md](docs/POWER_SUPPLY_CONCEPT.md) before modifying hardware.

## Next steps

1. Validate the identified HmIP-VDMOT's wiring polarity, 3.3 V motor rail under load, running and end-stop current profiles, full travel time and installed valve's effective hydraulic opening.
2. Reconcile [V1.2 schematic review findings](docs/SCHEMATIC_V1_2_REVIEW.md) with actual PCB assembly: R29 shunt value/MPN, U25 MCU marking, STKNX power budget, motor output polarity, current sensor and nine sensor ports.
3. Address the [existing ETS product audit](docs/ETS_PRODUCT_AUDIT.md): extend the eight motor objects into zone-based configuration, decide DPT 5.001 versus 5.004, fix invalid generated Ko macro names, and repeat KNX product generation.
4. Prototype safe single-motor arbitration, current-limited endpoint learning and movement timing with real hardware.
5. Implement positioning, feedback and error handling, then temperature-controller mode and room grouping.
6. Import-test the isolated KNX product generation candidate in ETS6, validate group objects, then verify telegrams end-to-end when hardware is ready.

**Audit status:** PCB, schematic, firmware and canonical KNX XML/header are unchanged. Run the standard-library-only static checks with `python tools/audit_design.py`. A test `.knxprod` was generated **outside the repository**; no ETS6 import or firmware build is claimed.
