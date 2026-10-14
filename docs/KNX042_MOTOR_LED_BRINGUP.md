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

## KNX042 M1 Hold-LED (14.10.2026)

Der Nutzer bestaetigte: KNX-Bus abgeklemmt, Versorgung ausschliesslich USB, keine Motoren angeschlossen. Fuer die menschliche Sichtpruefung wurde das exakte USB-Kommando `HOLD M1 F` ergaenzt. Es setzt M1-EN=GPIO10 HIGH, IN_1=GPIO18 HIGH und IN_2=GPIO19 LOW, laesst M2-M8 ausgeschaltet und schaltet spaetestens nach 180 s selbsttaetig ab. Vorher ist `ARM LEDS_ONLY` erforderlich; `STOP` schaltet sofort ab. GPIO0/KNX_TX wird erst nach Firmwarestart LOW gesetzt, nicht im ROM-Bootloader. Keine KNX-Verbindung freigegeben.

Bild: `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX042-M1-hold-180s-20261014\knx042-m1-hold-180s.uf2`. SHA256 `7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d`. Siehe [Buildnachweis](KNX042_M1_HOLD_BUILD_EVIDENCE.json).

**Live-Gate noch OFFEN:** Der Versuch eines softwareseitigen BOOTSEL-Einstiegs wurde durch die Zugriffssicherheitskontrolle abgelehnt. Ein separater read-only picotool-Aufruf bestaetigte, dass der RP2040 nicht im BOOTSEL-Modus ist. Es fand kein Flash statt; kein Motor-LED-Signal wurde eingeschaltet oder physisch beobachtet. Die KNX040-Firmware bleibt unveraendert installiert.

## KNX042 M1 first real USB LED test (2026-10-14)

User confirmed KNX physically disconnected, only USB power and no motors connected. RP2040 entered ROM BOOTSEL (Rev B2, flash ID E464401787522D33); the isolated KNX042 M1 180s-HOLD UF2 was flashed by picotool load -v -x, write 100%, verify 100%, exit 0 and reboot. USB COM7 returned KNX042 USB MOTOR-LED diagnostic with initial armed=0 active=0. T0=21.31 C and T1=22.00 C remained valid with zero UART timeouts in the read-only capture. At 14:54:34 MESZ, the host received ACK KNX042 ARMED 15s and KNX042 HOLD M1 F 180s, exit 0. M1 GPIO10 should be HIGH, IN_1 GPIO18 HIGH, IN_2 GPIO19 LOW; firmware should stop after 180 s. Actual LED observation is PENDING USER FEEDBACK; no actual motor motion was tested. See [M1 live USB evidence](KNX042_M1_FIRST_REAL_USB_LED_TEST.json).

### KNX042 M1 LED test repeated (2026-10-14)

At **15:06:27 MESZ**, on explicit user request, the same already-installed KNX042 isolated diagnostic received a single USB `ARM LEDS_ONLY`, followed by `HOLD M1 F 180s`. Both commands returned acknowledged success (host exit code 0). GPIO10 M1 enable HIGH, GPIO18 IN1 HIGH, GPIO19 IN2 LOW, M2-M8 remain LOW per firmware. A second USB `STATUS` read returned `armed=0 active=1` at approximately 15:06:51 MESZ. The software has a fixed automatic 180s stop; this run's final OFF transition is not yet verified in this log. Visual M1/IN1/IN2 LED observation remains **PENDING USER FEEDBACK**. No new firmware flash, KNX transmission, or physical motor connection. [Repeat test evidence](KNX042_M1_LED_REPEAT_20261014.json).

**Finale Live-Nachpruefung M1 Wiederholung:** COM7 KNX042 um etwa 15:09:23 MESZ: `KNX042 STATUS armed=0 active=0`. Der Ausgang ist wieder AUS; LED-Beobachtung des Benutzers noch ausstehend. Die Firmware besitzt einen auf 180 s begrenzten HOLD; die Statusmeldung belegt AUS, nicht unabhaengig den genauen Abschaltgrund.

## KNX042 - User LED observation and PCB OPEN/CLOSE labels (2026-10-14)

After the third M1 F 180s diagnostic, the user **visually confirmed OPEN LED illuminated** and reported M1 appeared energized; the user did not identify I1/I2 labels. This is **human LED feedback**, NOT a calibrated current measurement or proof that a physical motor turned. There are no connected motors. User suspects some LEDs may have been soldered in reverse orientation; **not electrically proven**. Do not automatically mark all LEDs reversed, because OPEN visibly worked.

Direct original V1.2 EasyEDA PCB JSON net inspection proves the following mapping (not inferred from a photo):

| PCB reference text | PCB pad/net evidence | RP2040 pin | M1 F hold |
| --- | --- | --- | --- |
| `OPEN` (PCB shape 888) | `OPEN` LED pad1 `R41_1` -> R41 pad2 `IN_1`, pad2 GND | GPIO18 (`IN_1`) | HIGH |
| `CLOSE` (PCB shape 889) | `CLOSE` LED pad1 `LED8_1` -> R43 pad2 `IN_2`, pad2 GND | GPIO19 (`IN_2`) | LOW |
| M1 enable | R48 pad2 `M1_EN` -> indicator LED12 -> GND | GPIO10 (`M1_EN`) | HIGH |

The tested command `HOLD M1 F` sets GPIO18 HIGH and GPIO19 LOW, so the observed `OPEN` LED is consistent with the PCB. The **actuator movement direction** must still be verified with a separate load-safe motor test; OPEN is the PCB silk designation, not mechanically verified valve movement. Other dark LEDs: check silkscreen/component datasheet polarity, solder orientation, resistor connection and LED diode test **with all power physically off**. Leave KNX physically disconnected and do not attach actuators while resolving the known hardware issues.

Evidence is machine-readable in [KNX042 user LED observation](KNX042_OPEN_LED_OBSERVATION_20261014.json). No firmware, bus, GPIO or motor command was issued in response to this user feedback.

### KNX042 M1 LED retest after reversing indicator LED (2026-10-14)

At 16:56:40 MESZ the user-requested third-party hardware visual retest was started after the user had rotated/re-soldered an LED. KNX042 COM7 identity matched; initial status was `armed=0 active=0`; guarded `ARM LEDS_ONLY` and `HOLD M1 F 180s` were acknowledged (EXIT0), and the independent follow-up at 16:56:54 MESZ returned `armed=0 active=1`. Expected M1_EN GPIO10 HIGH / OPEN IN1 GPIO18 HIGH / CLOSE IN2 GPIO19 LOW, all other motor enables LOW. Board software auto-stop limit 180 s (approx 16:59:40 MESZ); the actual LED condition remains **pending direct user observation**. No firmware flash, KNX bus or connected motors. See [retest evidence](KNX042_M1_LED_AFTER_REWORK_20261014.json).

## Erratum 14.10.2026 – ungewolltes STOP durch Statusabfrage

Der Python-USB-Host hat im ursprünglichen `finally`-Pfad auch nach `STATUS` ein `STOP` verschickt. Beim Test nach dem LED-Umlöten (`HOLD M1 F` um 16:56:40) erfolgte die `STATUS`-Abfrage um 16:56:54; anschließend wurde das Ausgangssignal vom Host sehr wahrscheinlich vorzeitig gestoppt. Die später dunklen M1-/OPEN-LEDs beweisen daher keinen Lötfehler. Die angegebene 180-s-Testdauer wurde bei aktiv abgefragten Tests nicht nachgewiesen. **`active=1` war nur die interne Firmwarevariable, kein gemessener GPIO-Pegel.**

Der Host wurde korrigiert und mittels simuliertem seriellen Port rot/grün getestet (KNX042 insgesamt 10/10 PASS), ohne RP2040-Neuflash oder erneute Motorausgangsaktivierung. Details: [KNX042 Status-Fehleranalyse](KNX042_STATUS_SIDE_EFFECT_FIX_20261014.md).

### KNX042 real retest after fixing host STATUS side effect (2026-10-14)

The user explicitly requested a new M1 F LED-only test after finding an unintended `STOP` in the old host CLI's `STATUS` cleanup path. On the physical COM7 RP2040 with existing KNX042 firmware, initial status `armed=0 active=0` (17:12:51 MESZ), USB host received `ARM LEDS_ONLY` and `HOLD M1 F 180s` acknowledgments (17:13:01 MESZ). **Crucially**, the corrected read-only host queried `STATUS` at 17:13:21 **and again** at 17:13:43; **both returned `armed=0 active=1`** with no stray STOP. The 180s firmware timeout is expected by ~17:16:01 MESZ. USB internal state is not direct measured GPIO voltage or visible LED evidence; physical M1/OPEN indicators still await user confirmation. No new firmware flash, motor load, or KNX. [New retest evidence](KNX042_M1_AFTER_HOST_FIX_20261014.json).

### Reverse-direction M1 + CLOSE blinking verification (2026-10-14)

After the user visually confirmed that M1 and OPEN lit during a corrected 180s hold, M1 was tested in opposite direction without reflashing the RP2040. The installed firmware permits a 400ms bounded reverse pulse (`PULSE 1 R`) rather than a 180s reverse hold, so a guarded host script `tools/knx042_m1_close_led_blink.py` sends one pulse at a time, awaits each `KNX042 AUTO-STOP` and inserts a nominal 200ms off gap. On 2026-10-14 from **17:25:28 to 17:26:29 MESZ**, **100 of 100** reverse pulses completed successfully (host EXIT 0). GPIO intent M1_EN(GPIO10)=HIGH, OPEN/IN1(GPIO18)=LOW, CLOSE/IN2(GPIO19)=HIGH during each 400ms pulse. The USB status was `armed=0 active=0` before and after. **Actual M1/CLOSE indicator illumination is pending user sighting; USB ACK does not measure a GPIO or motor output voltage.** No KNX bus, physical motors or firmware flash were involved. [CLOSE live evidence](KNX042_M1_CLOSE_BLINK_20261014.json).
