# ETS application, heating zones and valve-control concept

**Status:** Historical requirement capture (2026-10-09); not a record of current firmware execution or hardware acceptance. **Update 2026-10-12:** The concrete [KNX008 zone/channel ETS design](KNX008_ZONE_CHANNEL_DESIGN.md) now specifies a PROPOSED ApplicationVersion 3 object/parameter layout and a native-tested, hardware-independent target router. The current real ETS XML remains Version 2 with 35 KO / 21 parameters. The historical sections below were not retrospectively rewritten. [ETS product-data audit](ETS_PRODUCT_AUDIT.md) documents the original inventory.

## Goal and definitions

Support up to eight individually wired **Homematic IP HmIP-VDMOT (153309A0)** actuators, rated 3.3 V DC SELV with manufacturer-specified maximum current consumption of 120 mA; see [actuator documentation](ACTUATOR_HMIP_VDMOT.md). Each physical channel is assigned by ETS to one heating zone/room. Multiple channels can share a zone (e.g. 2, 3 or 4 heating circuits in one room). A zone issues the same requested opening to each member, subject to sequential execution and each motor's calibration. For the V1.2 circuit, **exactly one motor at a time** is a fixed baseline: all eight motor channels share one INA219 high-side sensor and common IN_1/IN_2 direction lines; the KNX bus supply budget is unverified. Do not infer independent current sensing from the eight separate H-bridge outputs.

## Proposed ETS6 structure

- Device-level: KNX physical address, enabled channels, power-on/bus-recovery behavior, telegram/status throttling, recalibration policy, fault reaction, movement scheduling policy.
- Channel 1..8: enable, friendly name, room/zone number, polarity / open-close direction, configurable travel time closed->open and optionally open->closed, endpoint current threshold, current validation/debounce, timeout, optional minimum movement time, periodic reference cycle, calibration status.
- Zone 1..8: enable, associated channels (via channel-to-zone assignment), operation mode (room-temperature regulator or direct position), KNX external temperature selection, temperature setpoint defaults/limits, temperature deadband, controller type and tuning, sensor staleness policy, frost protection and loss-of-bus behavior.
- Product parameters should be expressed as explicit ETS ParameterType bounds, options, units and default values, and mapped to firmware parameter storage. Validate ETS limitations and generated `.knxprod` packaging before relying on these names.

**Proposed new zone-based group objects (not yet assigned final numbers):** The current XML already declares **33 motor-oriented objects** (1..8 setpoint, 9..16 actual, 17..24 position, 25..33 local temperatures), but not the full zone/room model. The existing position objects are DPT **5.004**, not the candidate external scaling DPT **5.001**. See [ETS_PRODUCT_AUDIT.md](ETS_PRODUCT_AUDIT.md) for exact cataloguing and migration risks.

| Object | Direction | Usage |
| --- | --- | --- |
| Zone N target temperature | KNX -> device | Desired room temperature (candidate DPT 9.001) |
| Zone N actual temperature | KNX -> device | Actual room temperature (candidate DPT 9.001), if external bus sensor |
| Zone N direct valve opening | KNX -> device | 0..100% position command (candidate DPT 5.001) |
| Zone N output / actual target | device -> KNX | Controller output 0..100% (candidate DPT 5.001) |
| Channel N estimated position | device -> KNX | 0..100% estimate; explicitly not physical encoder feedback |
| Channel N moving / calibrated / fault | device -> KNX | Individual states and fault codes (DPT and object split TBD) |
| Device fault / busy / reference state | device -> KNX | Diagnostics and optional maintenance triggers |

KNX object visibility should be conditional on the zone's configured operating mode to avoid ambiguous simultaneous setpoint/direct commands. Dynamic parameter/UI visibility and supported product-data conversion must be tested in ETS6.

## Mode A: room temperature

KNX sends target and actual room temperatures. One zone computes a 0..100% valve target and applies it to every associated actuator channel. Sensor sources may be local temperature acquisition (if mapped correctly) or external KNX room sensors, but the mapping and arbitration are **open design decisions**. Temperature algorithms (e.g. PI with anti-windup, hysteresis or PWM-like output adaptation) require testing for slow thermal dynamics; do not claim a specific algorithm is implemented. For a slow valve, rate-limit movement and avoid oscillatory position commands.

## Mode B: direct position

KNX sends a zone valve-opening demand from 0..100%. The internal temperature regulator is bypassed; channels within the zone follow the same requested percentage. Each channel should retain its own travel times and calibrated reference so that the same percentage produces a consistent estimated stroke. Distinguish requested zone output, channel target and estimated channel position in telegrams and logs.

## End-stop learning and position tracking: proposed state machine

1. **Unknown / unreferenced:** Disable percentage tracking until a safe reference exists. Start calibration only on command or according to an explicitly configured safe startup policy.
2. **Reference close:** Reserve exclusive motor access; run close direction and measure INA219 current continuously. **120 mA is the manufacturer's maximum rated current consumption, NOT a proven end-stop threshold.** Establish an endpoint signature from real current/time traces at installed valves, with independent current protection, startup blanking, persistence filtering and absolute movement timeout. Detect sensor failure, overcurrent or timeout independently.
3. **Closed reference established:** Record estimated position = 0% only if a credible end-stop signature was detected; otherwise fault and stay unreferenced.
4. **Timed opening:** Run for fraction of independently calibrated full-open travel time; 100% needs a verified end condition or a safe measured upper limit. Stop/brake motor safely on completion.
5. **Intermediate movement:** Estimate position from elapsed direction-dependent motor-on time; update after every completed or interrupted movement. Never assume unpowered motion, stall or supply variation cannot change real position.
6. **Periodic recalibration:** Offer configurable reference-on-start, after N movements / elapsed time, on position uncertainty or by explicit KNX service command. Avoid disruptive motion during active heat demand.
7. **Fault:** Stop all motor outputs and report current measurement invalid, end-stop not found, open/close timeout, driver error, overtemperature or communication loss as appropriate. Fault reset should be deliberate and safe.

A measured stop-current threshold must be characterized for motor type and operating voltage; use hysteresis and a multi-sample persistence window. Establish a definite watchdog/maximum travel timeout before hardware testing. No automatic stall run should be enabled without these protections.

## Exclusive motor arbitration

Queue/channel scheduler accepts requests for all eight channels but energizes only one at once. Favor safety/reference requests and coalesce repeated target commands; stale intermediate movements should not be executed unnecessarily. Queue starvation prevention and fairness policy must be specified. Preemption must always de-energize a motor and persist uncertain position. Each channel has a separate state machine; a zone only owns aggregate demand.

## Open design decisions / acceptance plan

1. Motor model confirmed as HmIP-VDMOT; verify real connector polarity, 3.3 V motor supply capacity, normal/stall/endpoint current profiles and full-stroke time on the installed valves.
2. Mechanical stop behavior on full open vs full close; whether the motor's open end can be identified via measured current and whether 0% = fully closed is correct for the selected drive.
3. How many logical zones ETS should expose (fixed 8 maximum vs configured enabled count), what happens if a channel has no zone, and whether cross-zone grouping is forbidden.
4. Control method: PI, two-point controller or valve-position-only as default; controller tuning and sample cycle. Frost protection, summer shutoff, offline fallback.
5. Actual room temperature source (KNX/local), local temperature channel mapping, sensor failure/stale telegram handling.
6. ETS product metadata/manufacturer ID, application/version, group-object assignments and naming; whether XML/knxprod generation pipeline passes import validation in installed ETS6 v6.4.1.
7. Address the remaining [V1.2 schematic review issues](SCHEMATIC_V1_2_REVIEW.md), especially populated shunt R29, regulator headroom, U25 identity, shared-motor scheduling and failsafe tests before any motor energization.
8. Build static configuration tests; test single-channel reference, 0/25/50/75/100% movement, multiple channels in one room, two rooms competing for motor access, KNX telegram loss and reboot/fault recovery.

## Verification status

ETS6 installation found on LLO Desktop: **KNX ETS6 v6.4.1 (6.4.8718)**. [OpenKNXproducer 3.12.2](ETS_PRODUCT_AUDIT.md) successfully generated a **temporary** `.knxprod` candidate and a header, but **no import into ETS6 or functional KNX test** has been performed. Header macro naming and the one-channel product layout still need correction. The V1.2 PDF was visually reviewed; [PCB static invariants](PCB_V1_2_AUDIT.md) pass, while full DRC, BOM and hardware measurements remain open.

## V1.2 hardware restrictions for ETS and firmware

Refer to the [actual schematic review](SCHEMATIC_V1_2_REVIEW.md) before assigning ETS parameters or generating `.knxprod`. The hardware supplies:
- Eight motor channels on four TB6612FNG dual H-bridges; all channels share the direction pair `IN_1`/`IN_2`, and each has one independent `M*_EN` output.
- A **single** INA219 / nominal 200 mOhm supply shunt for all motors. Its actual populated resistor value must be confirmed; EasyEDA manufacturer-part metadata does **not** match the drawn shunt value.
- Nine local temperature inputs `T0` through `T8`, distinct from eight motor circuits. ETS must explicitly select a zone's temperature source (a suitable local room sensor or an external KNX temperature group object). Never implicitly map manifold/pipe temperature to room-air control.
- `STBY` permanently tied high to the driver logic rail; hardware does not offer an MCU-controlled global bridge disable. On boot, reset and fault, all eight PWM signals must go inactive before direction changes.
- An **unverified power budget** from STKNX through a 3.3 V DC/DC converter. The 1 A output rating of the downstream TSR 1-2433 is not proof of 1 A available from KNX.

For each channel, ETS may ultimately expose its calibrated travel time, direction inversion, current/end-stop detection policy, min. change and re-reference policy; **firmware-independent hard timeouts/current protection must not be removable through ETS**. Grouping several circuits into one room always creates a sequence of individual moves, not simultaneous movement. Any status telegram claiming valve position should be labelled **estimated** unless feedback hardware is added.
