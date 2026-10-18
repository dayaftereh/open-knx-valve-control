# KNX076 – hardware-bounded RP2040 GPIO0 one-shot TX firmware

**Live on LLO Home: 2026-10-18. Phase complete: BUILD + UF2 FLASH + IDLE MEASUREMENT.**
**NO knx-transmit pulse was fired; NO KNX group telegram transmitted.**

## Preconditions and live state

- Repo: C:\_myspace\workspace\open-knx-valve-control, branch main.
- User has R17 TX pull-up removed and connected the controlled KNX test bus.
- RP2040 USB-C powered, BOOTSEL initially active, USB volume D: RPI-RP2.
- PicoScope 3205D MSO physically connected (per user), Channel A = KNX+
  to common GND; Channel B = KNX_TX on JMP3 pads 2/3 to common GND.
  Physical probes assumed 10:1 for voltage conversions.
- Prior live passive scope run KNX075: bus 31.065 V median, TX 0.086 V median
  in BOOTSEL. Still-important unresolved hardware history: U11 overheat,
  removed R17 and bridged D1; VCCCORE not measured under current bus supply.
  USB-only earlier C1 VCCCORE was 0.3 V, NOT a current bus-powered reading.

## Firmware

Separate isolated PlatformIO environment:
- tools/knx076_tx_single_pio/platformio.ini
- tools/knx076_tx_single_pio/src/main.cpp
- tools/knx076_tx_single_pio/README.md

New driver uses the RP2040 PIO0 side-set output rather than Serial1/TP-UART.
At 1 MHz the hardware PIO instruction sequence is:
1. PULL BLOCK side 0 (idle LOW until a software token enters the FIFO)
2. NOP side 1 [15] = 16 us HIGH
3. NOP side 1 [15] = 16 us HIGH
4. NOP side 1 [2]  = 3 us HIGH
5. NOP side 0, return to blocking PULL = LOW indefinitely.

Therefore 35 us HIGH in hardware regardless of what the main RP2040 core
does during the pulse, and no autonomous transmit while booting/idle.

Gate requires BOTH serial commands ARM ONE and FIRE ONE, within 4 seconds.
One pulse maximum per firmware boot; disarms/locks before token enqueue.
STATUS, STOP, DISARM are non-actuating. Generic PlatformIO upload remains
disabled (custom command exits nonzero).

Caution: software idle LOW on setup and observed BOOTSEL LOW cannot guarantee
physical TX behavior during every supply/reset/brownout state. This is a
diagnostic waveform, NOT a KNX GroupValueWrite or valid KNX TP frame.

## Build, upload and verification

PlatformIO build: SUCCESS; Arduino-Pico 5.5.0, RP2040 target, 60680-byte
program image footprint, 8684 bytes RAM.
Created .pio/build/knx076_tx_single_pio/firmware.uf2, **145,920 bytes**,
SHA-256:
70382721F95F5AD71129A1DC1DDF43D7B3DFA43EE3C4920A59E60BADD785E486

Five local KNX076 source safety regressions passed.

Verified BOOTSEL D: volume label RPI-RP2, USB boot device PID0003, and
INFO_UF2.TXT manufacturer/board ID RPI-RP2; checked image SHA-256.
Copied **once** to D:\firmware.uf2.
RP2040 left BOOTSEL, enumerated as USB Serial **COM8** PID000A.
Non-actuating USB STATUS returned exactly:

    KNX076 STATUS gpio0_measured=LOW pio_ready=1 armed=0 shots=0 SINGLE_35US_PIO_NO_AUTO_TX

**No ARM ONE, FIRE ONE or PIO FIFO trigger was sent.**

## Passive two-channel PicoScope after flashing

Captured 100,000 sample pairs at 10 us / sample (~1.0 s) with **zero**
Pico SDK streaming overflows. Both channels were passive.
Physical voltage scales assume analog probes at x10.

- A / KNX+: **31.065 V median**; min 20.565 V; max 38.941 V.
  The extrema can include pre-existing KNX communication/transients and
  measurement anomalies; do not ascribe them to this firmware, which sent no
  pulse. Characterization of A outliers remains open.
- B / KNX_TX: **0.086 V median**, min -0.043 V, max 0.173 V.
  No observable unintended TX HIGH after flash.
- PicoScope API reported STOP=0 and CLOSE=0.

This confirms firmware deployed and TX held LOW after boot in the measured
steady state. It DOES NOT yet establish pulse amplitude or KNX_A bus voltage
drop during a pulse.

## Next separate, deliberate test

1. Confirm real VCCCORE at accessible C1 pad 2 / pad 1 GND with KNX bus
   presently powered; previous USB-only C1=0.3V is inapplicable.
2. Check U11 68-ohm actual state, absence of overheating, connected scope
   grounds, stable baseline ~31V on A and near0V B.
3. Start a synchronized PicoScope capture (A and B simultaneously).
4. With separate operator approval, send USB ARM ONE then FIRE ONE.
5. Compare B peak HIGH and duration 35 us against A KNX+ timed droop;
   save raw ADC and edge-aligned summary, never attempt repeated pulses.
6. If unexpected high/thermal/bus collapse, disconnect power. Observe B LOW
   after test and leave the firmware locked/disarmed.

No Ethernet/KNXnetIP or bus group transmissions and no Git push in KNX076.
