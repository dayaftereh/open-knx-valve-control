# Verified actuator: Homematic IP HmIP-VDMOT (153309A0)

**Status:** Manufacturer identification confirmed 2026-10-09. Motor-characterization tests and electrical validation are still outstanding. This document is a hardware specification for the custom KNX valve controller, **not** evidence of certified Homematic compatibility.

## Identification and manufacturer data

Owner-supplied purchase link: https://www.amazon.de/gp/aw/d/B07RJZ5F1Y

| Property | Verified specification |
| --- | --- |
| Manufacturer / brand | eQ-3 / Homematic IP |
| Device | HmIP-VDMOT, motorized floor-heating valve actuator |
| Part number | 153309A0 |
| EAN | 4047976533091 |
| Amazon ASIN | B07RJZ5F1Y |
| Supply | 3.3 V DC, SELV |
| Manufacturer-stated maximum current consumption | **120 mA** |
| Mechanical linear stroke | **4.3 +/- 0.3 mm** |
| Valve connection | M30 x 1.5 mm, supplied VA 80 adapter |
| Enclosure protection | IP20 |
| Ambient operating temperature | 0 to 50 degrees C |
| Size without cable | 44 x 54 x 50 mm |
| Weight | 80 g |
| Cable length | 90 cm (manufacturer product page) |

### Evidence and source ranking

1. **Manufacturer operating manual (eQ-3, HmIP-VDMOT)**: https://www.eq-3.com/downloads/download/homematic_ip/bda/HmIP-VDMOT_UM_web.pdf (sections 4-8). Specifies 3.3 V, max. 120 mA, stroke 4.3 +/- 0.3 mm, M30 x 1.5, IP20, dimensions and manufacturer's standard HmIP-FALMOT-C12 controller connection.
2. **Homematic IP manufacturer product page**: https://homematic-ip.com/de/produkt/stellantrieb-motorisch (article number, EAN, cable length and other parameters).
3. **User's actual product listing**: https://www.amazon.de/gp/aw/d/B07RJZ5F1Y . ASIN matched to model/part number by independent listings.

**Crucial distinction:** **120 mA is the manufacturer-rated maximum current consumption, not a manufacturer-specified end-stop detection threshold or approved continuous stall current.** It is unsafe to conclude that current=120 mA necessarily means fully closed. Characterize the running current, startup peak and blocked/end-stop transient on real installed valves before choosing a detection criterion or driving against a stop.

The manual **does not state a guaranteed full-stroke travel time, drive polarity/color code, internal encoder, current signature at endpoints, or a direct KNX interface**. An informal community report describes about 30 s travel, reverse-polarity DC wiring and ~100 mA against the stop. This is anecdotal and valve/installation dependent; do **not** adopt the reported timing or wiring as authoritative. Verify the actual cable conductors, motor polarity and electrical limits at a low-risk isolated test setup.

## Fit to the project hardware

The existing repository documents up to eight physical drive channels, RP2040, PCF8574/driver devices and a shared INA219 sensor. This project currently allows only one selected motor to run at a time. Confirm this topology **against the V1.2 schematic and populated PCB**, including the 3.3 V *motor supply* (distinct from logic 3.3 V), motor-driver output topology, maximum current rating, INA219 shunt placement and fault paths.

The normal Homematic IP system pairs this actuator with a manufacturer floor-heating controller HmIP-FALMOT-C12. The custom controller intends to drive the motor electrically and exposes its own KNX stack. Do not assume proprietary protocol, certification or manufacturer-endorsed third-party operation from the actuator's compatible connector alone.

## Control and calibration engineering requirements (proposed, not implemented)

1. **Electrical qualification:** verify isolated SELV motor rail, driver current capability, actual cable conductor connections, motor direction, H-bridge disable state and independent fail-safe stop. Do not use MCU GPIO to power the motor.
2. **Exclusive access:** only one actuator may be energized. Ensure driver outputs are de-energized on boot, reset, exception, communication errors and channel switches. Sample current only when the intended motor is selected.
3. **Current measurement:** characterize INA219 calibration, shunt tolerance, update frequency, startup transients, background draw and loaded motion current at 3.3 V supply. Acquire real traces from several installed valves.
4. **Referencing:** close slowly/safely according to a confirmed direction; detect a credible endpoint from *validated* current-profile change and elapsed time, not from a hard-coded 120 mA comparator. Use startup blanking, filtered persistence, independent maximum move duration and a driver-level current protection strategy. If no unambiguous stop indication occurs, switch off and report an unreferenced fault.
5. **Travel calibration:** measure full closed-to-open and open-to-closed effective run times per channel and retain separate times if needed. The full-open mechanical reference is also unverified; do not run into that endpoint blindly.
6. **Position estimate:** control using elapsed motor-on time after a reliable reference; store position confidence, direction, remaining motion and error conditions. Motor position is an *estimate*, not encoder feedback.
7. **Hydraulic calibration:** rated actuator stroke of 4.3 mm does **not** imply a linear heat/water flow versus command %. An installed valve can have preload, free travel, deadband and different effective flow range. Separate motor stroke % from effective hydraulic valve opening %, and allow per-channel soft limits or characteristic curves only after flow observations.
8. **Fault handling:** current above tested envelope, INA219 read failure, motor timeout, no movement/end stop signature, unknown calibration and reset/power failure -> de-energize, report status; consider re-homing when safe.

### Suggested ETS channel parameters

These are design candidates, not current parameter names or validated numerical ranges:

| Parameter | Scope | Rationale |
| --- | --- | --- |
| Actuator type | Device or each channel | HmIP-VDMOT / 3.3 V profile, future-proofing |
| Direction invert | Channel | Verify open/close polarity on PCB and valve |
| Zone/room assignment | Channel | Allow multiple 1..8 channels in one room |
| Close-to-open travel time | Channel | Measured travel time, NOT manufacturer rated |
| Open-to-close travel time | Channel | Optional asymmetric travel compensation |
| Current endpoint detection mode/threshold | Channel or global | Profile-based, calibrated; independent safety limit |
| Startup blanking/filter window | Global or channel | Exclude inrush; reject false positives |
| Maximum movement / homing timeout | Channel | Independently limit duration |
| Min change / anti-hunting delay | Zone and channel | Reduce small, unnecessary moves |
| Re-home strategy | Channel | User-triggered, power-up, periodic/uncertainty |
| Effective valve range / offset | Channel | Compensate non-linear hydraulic travel after tests |

Do not let ETS expose unsafe parameter ranges unchecked. A defective ETS value must not remove firmware and hardware time/current cutoffs. For temperature mode, one zone setpoint and measured temperature control all associated channels; direct position mode accepts a zone-level KNX 0..100% target.

## Acceptance measurements to capture

- Date, actual PCB V1.2 revision, motor serial/batch and valve manifold type.
- At least several individual drive channels: supply voltage at **motor connector under load**, driver drop and inactive-channel leakage.
- Motor current versus time: free movement in both directions, startup, expected closed and open ends, highest ambient/load; verify stop signature without unsafe prolonged stalling.
- Physical and hydraulic effective travel range, observed direction, travel time both ways.
- INA219 sample interval/accuracy and stop detection latency versus driver protection.
- Reset, lost power, duplicate KNX telegram, queued commands, sensor failure and two-room concurrent demands.
- Explicitly mark all raw readings as measurements, not manufacturer rated values.

See [ETS and control concept](ETS_AND_CONTROL_CONCEPT.md) and [architecture](ARCHITECTURE.md).

## Hardware cross-check (schematic V1.2)

The original [V1.2 schematic review](SCHEMATIC_V1_2_REVIEW.md) identifies dedicated 3.3 V-powered outputs from four TB6612FNG dual H-bridges, common `IN_1/IN_2` direction lines, independent channel PWM enables, and **one** INA219 watching `M_VCC` through nominally 0.2 Ohm shunt R29.

**Do not start current-based homing until actual R29 population is verified.** Its EasyEDA part metadata is inconsistent with the displayed 200 mOhm/1 W value. Likewise, the KNX-powered supply budget, motor voltage at the output terminals, wiring polarity and running/end-stop current profiles remain unmeasured. The HmIP-VDMOT's manufacturer rating of 120 mA maximum is not an endpoint threshold.
