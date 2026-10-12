# PCB V1.2 static audit - layout versus schematic

**Update 2026-10-12:** Der getrennte [KNX022 Hardware-Preflight](KNX022_STATIC_HW_READINESS.md) erstellt einen maschinenlesbaren Blockerstatus mit reproduzierbarem PCB-/Firmware-/BOM-Check. Diese Seite bleibt historische V1.2-Analyse und belegt keine reale Motorsicherheit.

**Date:** 2026-10-09

**Source:** [EasyEDA PCB JSON V1.2](../schematic/pcb_knx-valve-control_v1.2.json), cross-checked with [schematic JSON V1.2](../schematic/sch_knx-valve-control_v1.2.json) and the [visually reviewed PDF](../schematic/sch_knx-valve-control_v1.2.pdf).

**Scope limitation:** The board file is an *export*, not evidence of an assembled PCB. This pass parses exported pads, nets, copper track shapes and component attributes. It is **not** EasyEDA ERC, PCB DRC, 3D clearance validation, complete copper connectivity proof, BOM approval, as-built inspection or electrical testing.

## 1. Machine-readable board inventory

| Property | Parsed from V1.2 |
| --- | --- |
| PCB component LIB records | 191 (some silkscreen designator text has been replaced by functional labels) |
| Schematic component LIB records | 192, including one drawing-frame library instance (not a PCB device) |
| PCB copper trace records | 736 TRACK objects total, **including some non-copper layers** |
| PCB VIA records | 347 |
| PCB COPPERAREA records | 1, GND on BottomLayer |
| Copper layers used by TRACKs | TopLayer=1, BottomLayer=2, Inner1=21, Inner2=22 (**four**) |
| Other layer records | Some tracks on silkscreen and BoardOutLine; these must not be counted as copper routing |
| Distinct displayed PCB footprint names | 183 (not 183 physical components; some repeated functional silkscreen identifiers) |
| Distinct PCB TRACK net names | 134 |
| PCB BBox (EasyEDA native coords) | x=3820, y=3403.4, width=418, height=402.3 |

The schematic-to-PCB raw label sets do **not** match exactly: a number of PCB footprint display labels are friendly names such as `M1` .. `M8`, `T0` .. `T8`, `DEBUG`, `PROG`, `RUN`, instead of conventional schematic component references. **Do not infer that a component is missing solely from this display-name mismatch**; a proper UUID/netlist/assembly comparison is still needed.

## 2. Confirmed electrical intent present in PCB pads

| Circuit | PCB reference and pin data | Audit result |
| --- | --- | --- |
| Eight drive channels | U34 = M1/M2, U36 = M3/M4, U37 = M5/M6, U35 = M7/M8, all TB6612FNG (24 pads each) | All eight pairs M1+/- .. M8+/- and channel enables M1_EN .. M8_EN appear on driver pads |
| Direction | All four drivers use `IN_1` and `IN_2` nets; corresponding pads appear on RP2040 U18 | Direction shared across all actuators; software must arbitrate |
| Driver standby | Pin 19 of U34/U35/U36/U37 has net `3.3V` | Standby is tied high, **not** available as an independent MCU global shutdown output |
| Current shunt | R29 pad 1 = `3.3V`, pad 2 = `M_VCC`; schematic value 200 mOhm | One **shared motor supply current** path |
| Current IC | INA219 U23 has 8 pins, pin 3 `SDA`, pin 4 `SCL`, pins 7/8 `U23_7`/`U23_8` | INA219 present. Verify series protection, actual shunt and calibration |
| Motor output supply | Drivers connect VM pins to `M_VCC`, VCC pins to `3.3V` | Same nominal voltage domain; 3.3 V load regulation must be measured |
| Temperature MCU | U25, 20-pad SOIC, exposes `T0` ... `T8` | Nine distinct local sensor inputs are exported |
| LCD expander | U29 PCF8574 (16 pins), SDA/SCL pins 15/14 | HMI expander shares I2C bus with INA219 |
| MCU output mapping | U18 RP2040 pads include all M1_EN .. M8_EN and IN_1/IN_2 nets | Mapping aligns with firmware [controller/config.hpp](../src/controller/config.hpp) assignments D10..D19 |

### Motor scheduler is mandatory for valid current attribution

The four physical H-bridge ICs allow independent output pairs but there is only one INA219 measurement of the common `M_VCC` rail. The shared `IN_1/IN_2` direction lines also prohibit different simultaneous motor directions. For this project **only one PWM enable may be active at a time**, and every channel switch must first disable the previous motor and settle the measurement. Position is only an elapsed-time estimate after calibration; no encoder position feedback is present in this design.

## 3. Open PCB-to-schematic and electrical issues

| Priority | Finding | Required follow-up |
| --- | --- | --- |
| P0 | R29 drawn as 200 mOhm, supplier/manufacturer field `SCR1206F1M1` carried into PCB | Inspect the mounted component and original order/BOM; confirm shunt resistance and INA219 current calibration before homing |
| P0 | U25 symbol/firmware targets ATtiny3216, but PCB manufacturer field `ATTINY1616-SN` | Confirm assembled chip type and UPDI target; do not program blindly |
| P0 | Motor supply 3.3 V comes via shared KNX/USB chain, with previously documented STKNX and downstream TSR/DC/DC headroom concerns | Characterize worst-case rails and bus current under motor and logic load; the presence of traces proves no supply budget |
| P1 | Four TB6612 standby pins permanently high | Verify inactive PWM states on reset/brownout, firmware watchdog and cross-channel transitions |
| P1 | PCB uses four copper layers with high via count; sole GND COPPERAREA is layer 2 | Export manufacturer stack-up and verify actual plane continuity, clearance, isolation, copper fills and vias with EasyEDA DRC |
| P1 | 191 PCB LIB records and 191 non-frame schematic LIB records, but PCB display reference names are not a reliable exact match | Compare canonical UUIDs/pads/netlist with the original design tool rather than treating counts as BOM equivalence |
| P1 | No machine-readable DRC pass report or tested netlist completeness was present in this review | Export native EasyEDA DRC/ERC report and PCB assembly BOM; verify unconnected ratsnest, polygons and silkscreen |

## 4. How to reproduce the static evidence

The read-only [tools/audit_design.py](../tools/audit_design.py) script uses Python's standard library to check key schematic/PCB/KNX invariants. On the installed agent:

```powershell
cd C:\ASH\Workspace\Projects\open-knx-valve-control
python tools\audit_design.py
```

It checks that all four dual motor driver footprints provide the intended motor output/enable nets and STBY, that the RP2040 carries eight enables plus common direction, that R29 bridges the intended supply nets, that INA219 and PCF8574 use I2C, and that the ATtiny provides nine local sensor inputs. It also checks the **current** KNX XML baseline. **Passing is explicitly not a DRC**.

## 5. Recommended next hardware gate

Before energized motor tests:

1. Photograph **the actual populated R29 and U25 markings**, and compare with assembly BOM.
2. Use isolated/appropriate test equipment to validate KNX-only versus USB-only 3.3 V rail under worst-case logic load *before* applying a motor.
3. Confirm no unintended motor output drive during reset/boot with safe supply current limits.
4. Connect only one confirmed HmIP-VDMOT motor and record INA219 current-vs-time plus an independent measurement, respecting the manufacturer's 120 mA maximum rating.
5. Define safe homing detection from measurements, not a constant 120 mA comparator; implement timeouts and error handling.
6. Export EasyEDA DRC, netlist and manufacturing BOM for a proper board release gate.

See [SCHEMATIC_V1_2_REVIEW.md](SCHEMATIC_V1_2_REVIEW.md) for the detailed power discussion and [ETS_AND_CONTROL_CONCEPT.md](ETS_AND_CONTROL_CONCEPT.md) for zone and actuator control requirements.

## Power jumper verification and external-supply planning

Static pad/net analysis now explicitly checks **JMP1** (`KNX_VCC` <-> `R9_2`), **Q1** (pins 1=`USB_VCC`, 2=`5V_`, 3=`R9_2`), **D6**, **F1**, **D1**, and **U6** (pin 1=`D1_1`, 2=`GND`, 3=`3.3V`). The documented two-pad `JMP1` is a normally-open SMD solder bridge, **not** a DuPont cable socket. A dedicated, protected external-5-V entry point **does not exist** in this V1.2 pad-net map. See [POWER_SUPPLY_CONCEPT.md](POWER_SUPPLY_CONCEPT.md) for the two hardware options, possible backfeed paths, and required physical tests. No modification to the PCB has been approved or performed.
