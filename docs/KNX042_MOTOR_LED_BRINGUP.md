# KNX042 - Isolated eight-channel TB6612 LED bring-up (preparation)

**Date:** 2026-10-14. **State:** software image built, *NO real motor output pulse or firmware flash yet*. The KNX040 temperature diagnostic currently remains installed on the RP2040. A future physical gate is required before any action.

## PCB V1.2 evidence

| Channel | RP2040 PWM enable | TB6612 | Output terminals | Logic LED |
| --- | --- | --- | --- | --- |
| M1 | GPIO10 | U34 | M1+/M1- | LED12 via R48 |
| M2 | GPIO11 | U34 | M2+/M2- | LED16 via R54 |
| M3 | GPIO12 | U36 | M3+/M3- | LED11 via R47 |
| M4 | GPIO13 | U36 | M4+/M4- | LED15 via R53 |
| M5 | GPIO14 | U37 | M5+/M5- | LED9 via R45 |
| M6 | GPIO15 | U37 | M6+/M6- | LED13 via R51 |
| M7 | GPIO16 | U35 | M7+/M7- | LED10 via R46 |
| M8 | GPIO17 | U35 | M8+/M8- | LED14 via R52 |

GPIO18/19 drive **shared IN_1/IN_2** for all eight channels. They have separate LED indicators. Driver STBY pin 19 is **permanently 3.3 V** (no controllable hardware standby); VM/M_VCC is joined to 3.3 V through R29 in the V1.2 exported PCB metadata. As-built deviations must be checked before any motor testing. Logic LEDs confirm the GPIO drive, **not** H-bridge output voltages, direction under load, or motor motion.

## Isolated firmware

`tools/knx042_motor_led_diag` uses Arduino-Pico with no KNX stack or motor production controller. The KNX040 ATtiny3216 UART temperature polling and USB reports remain present, including the boolean UART write guard.

- All eight enable GPIOs LOW and common directions LOW after program setup. GPIO0 KNX_TX driven LOW at software startup (NOT guaranteed during MCU reset/ROM).
- No motor GPIO pulses on boot or periodic loop. Every pulse requires the *exact* USB commands `ARM LEDS_ONLY` and `PULSE <1..8> F|R`.
- The arming token lasts 15 seconds; one channel at a time, direction settles before enable, **400 ms fixed maximum pulse**, then output LOW automatically. `STOP` immediately disables all outputs and disarms.
- Arduino loop timing is a software watchdog **not hardware STO**: resets, deadlocks, pin float, STBY high, and independent power faults have not been characterized.
- `platformio.ini` intentionally disables uploading; a distinct reviewed `picotool` host procedure is required only after all physical gates are met.

## Physical verification required BEFORE upload or pulses

1. Disconnect the **KNX bus physically** (including KNX-derived power) and any other external supply. USB-only supply during the test; confirm no hot U9/U11, no abnormal current.
2. Keep **all motor/valve actuators unplugged**. Confirm indicators are fitted with series resistors and the real V1.2 board wiring agrees with the PCB mapping.
3. Confirm safe USB power on 3.3V/M_VCC/GND. No modification of the known KNX035 STKNX/R17/U9 hazard, D1 bypass, F1 mismatch, or permanently-high STBY is implied by a successful LED test.
4. Preserve/verify currently installed KNX040 diagnostic UF2 backup; identify RP2040 by VID:PID 2E8A:000A plus exact serial. Forbid any production KNX firmware flashing.
5. Only then flash the isolated verified UF2 using the previously proven guarded RP2040 procedure, check KNX042 diagnostic identity and T0/T1 telemetry, send **one M1 F pulse**, observe LEDs, stop. Repeat M1 R if safe, then M2–M8 one by one. Record observed LEDs rather than inventing them.
6. For output qualification, use isolated differential measurements M1+ to M1- for F/R and stopped, separately; logic indicators alone are insufficient. No current/torque/thermal qualification without actual loads.

Read-only device identity probe (no port open, flash or outputs):
`tools/knx042_motor_led_control.py probe --port COM7 --expect-serial E464401787522D33`

Once all physical prerequisites are confirmed and this isolated UF2 has **actually been flashed**, the USB host can issue one time-limited pulse with all four required assertions:
`tools/knx042_motor_led_control.py pulse --port COM7 --expect-serial E464401787522D33 --channel 1 --direction F --knx-disconnected --motors-unplugged --usb-only --leds-current-limited`

## Current verified offline build

- **UF2:** `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX042-motor-led-usb-only-20261014\knx042-motor-led-usb-only.uf2`
- **SHA256:** `e31d4083c1ee9f381592e6b0dbb712623d6eeec55cf4dadd973af0a77df08c3d`
- **Size:** 152576 bytes.
- **Original KNX040 UF2:** `e9de4dcb66a0afd4fa906d5a5591bc7785cb6c8bc71f57e20bb4104069c31639` (preserved).
- Machine-readable evidence: [KNX042 offline build](KNX042_OFFLINE_BUILD_EVIDENCE.json).

## Validation/evidence

- Offline scope/command checks: `tools/test_knx042_motor_led_diag.py`.
- Isolated PlatformIO RP2040 compilation, SHA256 UF2, diffs and ASH audit.
- No claim of observed LED or output voltage until tested physically.
- No GitHub push without user authorization.
