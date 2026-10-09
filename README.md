# Open KNX Valve Control

Controller for up to **eight motorized underfloor-heating valve actuators** with KNX integration. This repository contains firmware, KNX product-description sources, electronics schematics/PCB exports and DIN-rail enclosure models.

> **Project status (2026-10-09):** Architecture and ETS parameterization are being specified. The current RP2040 controller firmware initializes KNX, but does **not yet implement the complete valve-control, positioning, grouping or room-temperature control algorithms**. This document separates confirmed repository contents from requirements and concepts.

## Documentation

- [Architecture and verified project inventory](docs/ARCHITECTURE.md)
- [Schematic V1.2 electrical review and open findings](docs/SCHEMATIC_V1_2_REVIEW.md)
- [Verified HmIP-VDMOT actuator specification](docs/ACTUATOR_HMIP_VDMOT.md)
- [ETS application, heating zones and regulation concept](docs/ETS_AND_CONTROL_CONCEPT.md)
- [Legacy (potentially outdated) BOM and component list](.github/README.md)

## Hardware and source material

| Topic | Repository files | Notes |
| --- | --- | --- |
| Main board schematic V1.2 | [PDF](schematic/sch_knx-valve-control_v1.2.pdf), [JSON](schematic/sch_knx-valve-control_v1.2.json) | PDF visually reviewed (one sheet); see [electrical findings](docs/SCHEMATIC_V1_2_REVIEW.md) |
| Main board PCB V1.2 | [JSON](schematic/pcb_knx-valve-control_v1.2.json) | PCB export; no layout/DRC verification yet |
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

## Next steps

1. Validate the identified HmIP-VDMOT's wiring polarity, 3.3 V motor rail under load, running and end-stop current profiles, full travel time and installed valve's effective hydraulic opening.
2. Reconcile [V1.2 schematic review findings](docs/SCHEMATIC_V1_2_REVIEW.md) with actual PCB assembly: R29 shunt value/MPN, U25 MCU marking, STKNX power budget, motor output polarity, current sensor and nine sensor ports.
3. Design ETS room/channel topology, parameters and group objects; verify the existing XML/product header against the new design.
4. Prototype safe single-motor arbitration, current-limited endpoint learning and movement timing with real hardware.
5. Implement positioning, feedback and error handling, then temperature-controller mode and room grouping.
6. Generate and import-test an ETS6-compatible KNX product database (`.knxprod`) and validate telegrams end-to-end.

**Documentation-only update:** No PCB, firmware or KNX product exports were modified as part of this concept capture.
