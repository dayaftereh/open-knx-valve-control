# Main-board schematic V1.2 - electrical architecture and review

**Review date:** 2026-10-09

**Status:** Original PDF visually inspected at high resolution; correlated with EasyEDA schematic JSON and current source pin definitions. This is **not** an ERC/PCB-layout verification, measurement of assembled hardware, or safety/certification approval.

## Source and revision control

- Main source: [schematic V1.2 (PDF)](../schematic/sch_knx-valve-control_v1.2.pdf), one drawing sheet, title **"KNX 8 Heating Actuators Control"**, rev **1.2**, created 2026-01-14 in the file metadata.
- Machine-readable counterpart: [EasyEDA schematic V1.2 (JSON)](../schematic/sch_knx-valve-control_v1.2.json), one schematic, 192 library-symbol instances.
- Associated [PCB V1.2](../schematic/pcb_knx-valve-control_v1.2.json), **not** electrically/visually reviewed during this audit. Exact parts assembled on actual PCB are not yet verified.
- Different device: [UPDI programmer V1.4](../schematic/sch_updi_programmer_v1.4.pdf); V1.4 is *not* a newer main-board revision.
- PDF SHA-256: `e7e452f1b517dabe077e9ac3987d3c1565464005b7a744beb8b53b3181c52789`.
- Schematic JSON SHA-256: `3c36ba0775ec04b5798b3084b04206ac4e7e4b07a125af9c1239a3e8c7deb367`.
- The original [legacy BOM README](../.github/README.md) describes a 230 V supply and other parts; do **not** use this outdated text as the authoritative V1.2 circuit description or purchasing BOM.

## 1. Verified schematic blocks

| Function | Schematic refs and connections | What is physically shown |
| --- | --- | --- |
| KNX bus | U4 `KNX_OUT`, U5 `KNX_IN`, U9 `STKNXTR`, D2, R2, U2/U8, L1 | Both bus terminals, STKNX physical-layer transceiver and associated input/protection/converter circuitry. `KNX_B` is referenced to the board ground in this non-isolated topology; verify USB/KNX ground interactions. |
| KNX buck converter | U9 `DCDC_LX` -> L1 33 uH -> `KNX_VCC`; R14 110 kOhm and R15 27 kOhm | Feedback is annotated **5.07 V** (ideal calculation 1 V x (1+110/27)). Actual voltage/load rating must be tested. |
| USB/KNX power selection | USB1, D6, Q1 AO3401A, JMP1, F1 630 mA, D1, U6 `TSR 1-2433` | USB `USB_VCC` and KNX-derived `KNX_VCC` feed a `5V_` selection rail, then `5V`, then the 3.3 V step-down. There is **no 230 V mains terminal or mains AC/DC module** in V1.2. Fuse voltage rating does not imply a 230 V supply. |
| MCU + flash + USB | U18 RP2040, U16 W25Q128JVSIM (16 MiB), X1 12 MHz, USB1, R16/R18 27 Ohm | RP2040 controller, external QSPI flash and USB configuration/programming interface. |
| 8 motor H-bridges | U34, U36, U37, U35: four **TB6612FNG** dual DC drivers; U38..U45 motor connectors | Eight two-wire outputs `M1+/-` ... `M8+/-`. Each has an independent PWM/enable line, but **both direction inputs** use common nets `IN_1` and `IN_2`. |
| Motor current measurement | R29 marked **200 mOhm (1 W)** between `3.3V` and `M_VCC`; U23 **INA219AID**, R33/R34 10 Ohm, C31 100 nF | One **high-side, common supply shunt** measuring the total motor-driver rail; not eight independent motor-current sensors. INA219 via shared 3.3 V I2C lines `SDA` / `SCL` (R24/R28 10 kOhm). |
| Temperature module | U25 labelled **ATtiny3216**; U17/U19/U22/U24/U27/U30/U31/U32/U33 | **Nine** local 3-wire temperature sensor terminal groups `T0`..`T8`, each nominally pulled up to 3.3 V via 4.7 kOhm; ATtiny firmware uses OneWire/DallasTemperature. |
| Local HMI | U29 **PCF8574T/TR**, LCD1 **LMB162ADC** 16x2, SW3 rotary encoder, R55 10 kOhm contrast, Q2 BC817 backlight | Only **one PCF8574** is present in this V1.2 schematic; it serves the LCD/HMI, not the motor-enable outputs. |
| Maintenance | SW1 USB_BOOT, SW2 RUN, SW4 KNX programming, S1 SWD, CN1 UPDI, LED1..LED16 | Physical programming/debug controls and individual status LEDs. |

### Power budget is NOT established by the 1 A 3.3 V regulator alone

The **upstream** U9 STKNX regulator is manufacturer-rated **150 mA maximum buck output**, and KNX bus power extraction is specified up to **30 mA**. These are different specifications and the usable buck output can be *further* constrained by KNX bus consumption limits. U6 TSR 1-2433 itself can output 1 A, but does not create that available power upstream. The motor's manufacturer-rated maximum consumption is **120 mA at 3.3 V**; MCU, memory, transceiver, HMI, temperature circuitry and losses need headroom **at the same time**.

Also, U6's specified **minimum input is 4.75 V**, while the STKNX buck is set to about **5.07 V** and Schottky diode(s) lie in the power path. The actual regulator input in KNX-powered and USB-powered operation must be measured *at worst-case load and input voltage*. The USB path may contain more diode drop than the KNX path. **No conclusion about adequate headroom can be made without measurements.**

Manufacturer references: [STKNX](https://www.st.com/en/interfaces-and-transceivers/stknx.html), [TSR 1-2433](https://www.tracopower.com/files/7e/tsr-1-2433.pdf).

## 2. Motor hardware - exact channel mapping

| Motor | Driver | H-bridge | Output nets | PWM enable |
| --- | --- | --- | --- | --- |
| M1 | U34 | A | `M1+` / `M1-` | `M1_EN` |
| M2 | U34 | B | `M2+` / `M2-` | `M2_EN` |
| M3 | U36 | A | `M3+` / `M3-` | `M3_EN` |
| M4 | U36 | B | `M4+` / `M4-` | `M4_EN` |
| M5 | U37 | A | `M5+` / `M5-` | `M5_EN` |
| M6 | U37 | B | `M6+` / `M6-` | `M6_EN` |
| M7 | U35 | A | `M7+` / `M7-` | `M7_EN` |
| M8 | U35 | B | `M8+` / `M8-` | `M8_EN` |

- All eight H-bridges have **shared** direction lines `IN_1` / `IN_2`, respectively feeding AIN1/BIN1 and AIN2/BIN2. They **cannot drive different directions simultaneously** as wired. The one-at-a-time software scheduler remains mandatory for reliable shared-current attribution and supply budgeting.
- Each H-bridge's `VM1/VM2/VM3` connects to common `M_VCC`; its `VCC` logic rail goes to 3.3 V.
- TB6612FNG `STBY` (pin 19) is tied **HIGH** to VCC/3.3 V in V1.2; it is **not** a global firmware-controlled hardware kill switch. Its PWM/direction inputs have manufacturer-specified internal 200 kOhm pulldowns, nevertheless verify safe output states through boot, watchdog reset, brownout and firmware crashes. Reference: [Toshiba TB6612FNG datasheet](https://toshiba.semicon-storage.com/info/TB6612FNG_datasheet_en_20141001.pdf?did=10660&prodName=TB6612FNG).
- Nominal R29 shunt 0.200 Ohm -> at 120 mA current, **24 mV** nominal shunt drop and ~**2.9 mW** dissipation. The INA219 reads *combined* current from the motor supply, not motor position. Confirm actual R29 installed value/INA219 calibration before trusting any readings.
- User-selected actuator: [Homematic IP HmIP-VDMOT](ACTUATOR_HMIP_VDMOT.md), 3.3 V, rated **120 mA maximum**. This is **not a specified end-stop signature**. Full stroke 4.3 +/- 0.3 mm; real travel duration and current profile are unmeasured.

## 3. RP2040 pin mapping from V1.2 and existing config

| GPIO | Circuit signal | Firmware config |
| --- | --- | --- |
| 0 / 1 | `KNX_Tx'` / `KNX_Rx'` (via JMP2/JMP3 routing) | KNX serial `Serial1`, GPIO mapping to be runtime verified |
| 2 / 3 | `Button` / `VCC_OK` | `Button=D2`, `VccOK=D3` |
| 4 / 5 | I2C `SDA` / `SCL` | INA219 and PCF8574 shared bus |
| 6 / 7 | Rotary encoder `A` / `B` | `A=D6`, `B=D7` |
| 8 / 9 | `T_Tx` / `T_Rx` | `TemperaturesTx=D8`, `TemperaturesRx=D9` |
| 10 .. 17 | `M1_EN` .. `M8_EN` | `Drive1=D10` .. `Drive8=D17` |
| 18 / 19 | `IN_1` / `IN_2` | `In1=D18`, `In2=D19` |
| 20 / 21 / 22 | `KNX_OK` / `CS` / `T_INT` | `KnxOK=D20`, `TemperaturesCS=D21`, `TemperaturesINT=D22` |
| 23 / 24 / 25 | `Prog_LED` / `Prog_BTN` / `LED` | `ProgramLED=D23`, `ProgramButton=D24`, `ErrorLed=D25` |

The configured *logical* GPIO assignments in [controller config](../src/controller/config.hpp) agree with the named schematic signals. Functional use of those pins is **not implemented by the existing RP2040 main loop**, which presently initializes KNX and polls the stack.

## 4. Temperature acquisition and KNX/ETS implications

- The PCB schematic provides **nine** separate local temperature-sensor ports `T0` through `T8` (three pins per connector, 3.3 V/pull-up/data/GND inferred from drawing). The ATtiny U25 firmware names those ports accordingly.
- How these **nine local probes** relate to **eight physical heating loops** and ETS **logical rooms** is not yet defined. One room may group 2..4 motor channels; it needs **one authoritative actual room temperature** plus a setpoint, not one regulator per motor unless explicitly requested.
- Preferred concept remains configurable sources: KNX room temperature input (external KNX sensor), or a selected correctly installed local sensor. Local manifold/pipe temperature should **not automatically be treated as room air temperature**.
- RP2040 <-> ATtiny has `T_Tx/T_Rx` serial paths plus `CS` and `T_INT`; verify UART polarity/crossover, physical SPI implementation, and temperature firmware interface before writing architecture-level assumptions.
- `JMP2/JMP3` expose KNX Rx/Tx crossover options; test jumper population/serial direction in hardware. The XML product/ETS object routing is **not validated by the schematic alone**.

## 5. Findings / discrepancies - prioritize before motor tests

| Priority | Evidence | Risk / required action |
| --- | --- | --- |
| **P0** | `R29` marked **200 mOhm (1 W)** but its EasyEDA `Manufacturer Part` attribute is **SCR1206F1M1** (and supplier code C3017245). | **Possible incorrect component metadata**: the MPN strongly suggests a megaohm-range resistor, entirely inconsistent with 0.2 Ohm current shunt. Verify physical populated resistor and BOM supplier value; never assume the MPN matches the displayed schematic value. |
| **P0** | U9 STKNX switching regulator maximum 150 mA; bus current extraction up to 30 mA; U6 TSR input min. 4.75 V; diodes upstream; 120 mA rated actuator plus electronics. | Power margin on KNX-only and USB-only operation **unproven**. Measure `KNX_VCC`, `5V_`, `5V`, U6 input, `3.3V`, `M_VCC` under realistic load/KNX minimum supply. Verify KNX bus current/fan-in compliance. |
| **P0** | U25 visible as **ATTINY3216** but EasyEDA `Manufacturer Part` metadata reads **ATTINY1616-SN**. Firmware PlatformIO board is `ATtiny3216`. | **Population/BOM mismatch**; identify physical microcontroller marking before UPDI programming and before ordering PCBA. |
| **P1** | Four TB6612 drivers share two direction lines, plus single INA219 sensor. | Firmware must serialize motor activity. Use mutually exclusive PWM outputs; current-based homing needs motor-specific time/current envelope. |
| **P1** | TB6612 `STBY` pins tied to logic supply instead of an MCU shutdown output; PWM inputs have internal pulldowns. | Check reset/brownout behavior and failure containment. Decide whether existing hardware provides sufficient independent motor-off protection. |
| **P1** | R29/C31/INA219 high-side measurement, nominal current 120 mA only manufacturer maximum. | Confirm shunt value, current direction/offset, INA219 calibration, sampled bandwidth and peak current. A hardcoded 120 mA threshold is not valid without traces. |
| **P1** | Various EasyEDA symbols have generic/stale metadata. Example: U11 displayed 68 Ohm (2 W), but MPN field references a 3.5 mOhm shunt; 0402 resistors of different values share generic `0402WGF1002TCE`. | Schematic **display values and component procurement metadata disagree**. Perform full MPN/footprint/rating audit before ordering or generating a manufacturing BOM. |
| **P1** | Legacy README lists 230 V / IRM-02-5 / different component counts, while V1.2 shows KNX/USB power and one PCF8574. | Treat legacy BOM as historical and reconcile with actual assembled board. Never apply mains wiring based on the old README. |
| **P2** | Nine `T0`..`T8` probes versus eight motors and potentially fewer ETS zones. | Specify zone-to-probe mapping and fault/staleness policy, preserve possibility of an external KNX room sensor. |
| **P2** | PDF inspected and paired EasyEDA JSON parsed, but no ERC/netlist export, PCB-JSON comparison or physical measurements. | Perform formal schematic/ERC, PCB DRC/assembly verification and hardware tests before declaring board safe/complete. |

## 6. Actionable next checks

1. **As-built inspection (no motor motion):** identify actual R29 and U25 markings, KNX/USB power configuration, fuse and diode population, and whether the main-board assembly follows schematic V1.2.
2. **Power test using appropriate isolated equipment:** verify supply/bus-current constraints under KNX-only and USB-only power; inspect regulator input minimum and rail collapse at a controlled representative load.
3. **Motor electrical test with protective timeout:** measure exactly one installed HmIP-VDMOT, output polarity and voltage at connector, free-run/start/stop current signatures, realistic full-open/full-closed stroke duration and temperature dependence. Record raw INA samples versus independent current instrumentation.
4. **Hardware/failsafe:** prove that on boot, reset, stalled CPU, bad INA measurement and lost bus supply, all eight PWM motor outputs are disabled. Check current limits independent of KNX ETS parameters.
5. **Communications:** verify STKNX UART jumpers/programming path, RP2040 <-> ATtiny temperature transport, and I2C addresses/bus reliability with INA219 and PCF8574 concurrently.
6. **Product architecture:** update [ETS requirements](ETS_AND_CONTROL_CONCEPT.md) with source/zone assignment, per-actuator travel/threshold calibration and single-motor arbitration; only then generate, import and test ETS6 `.knxprod` files.

### Scope boundary

**Confirmed** means present in the provided PDF schematic and/or source JSON; **planned** means desired firmware or ETS behavior; **unverified** means on-board population, physical wiring, power, current, timings, electrical safety and successful ETS operation still require tests. No canonical schematic/PCB, firmware or product XML was modified during this review.
