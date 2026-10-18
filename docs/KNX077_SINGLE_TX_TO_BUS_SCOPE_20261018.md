# KNX077 — STKNX transmit pulse and live KNX+ bus correlation

**Live measurement on LLO Home, 2026-10-18. Test: PASS (physical bit impulse).**
**Exactly one output pulse. Not a KNX TP1 application telegram.**

## Objective

Prove that the STKNX output modulates the KNX bus voltage when RP2040 GPIO0
sends a 35-us high pulse, by simultaneous analog sampling:

- PicoScope 3205D MSO **channel A:** KNX+ relative to common board/KNX- GND.
- PicoScope 3205D MSO **channel B:** KNX_TX at JMP3 pads 2/3, same common GND.
- Both analog probes are assumed to be physically 10x as reported by user.

The KNX test bus was powered at about 31V. This is a live electrical test,
not the former USB-only bench case. The hardware history of R17 pullup removal,
U11 overheat and D1 bypass is documented elsewhere. U9 VCCCORE has **not**
been independently remeasured at C1 in this powered-bus setup.

## Firmware/agent preflight

- LLO Home agent v0.7.9 responded OK; Windows; Git project main clean,
  initial local HEAD ea0b6cc, origin/main behind four commits.
- RP2040 detected via USB VID_2E8A/PID_000A, firmware already flashed KNX076.
- Non-actuating COM8 STATUS reply strictly matched:

      KNX076 STATUS gpio0_measured=LOW pio_ready=1 armed=0 shots=0 SINGLE_35US_PIO_NO_AUTO_TX

- PicoScope SDK ps3000a.dll available, no competing PicoScope UI process.
- Added tools/knx076_tx_single_pio/knx077_scope_one_shot.py, with explicit
  execute and lab confirmation options. It checks strict firmware version/state,
  starts BOTH scope inputs, and refuses to fire unless a passive preflight
  shows KNX+ between 27V and 35V and KNX_TX LOW below 0.6V peak.
- Separate STATUS check repeated while the scope was running, to exclude
  unexpected arming or earlier shots.

**Measured immediately before the pulse:** A=31.065V, B=0.086V median,
B preflight maximum0.129V.

## Exactly one physical GPIO0 transmit pulse

Only after active two-channel recording and positive hardware idle gates, the
host issued one USB command ARM ONE, received positive firmware ACK, and sent
**FIRE ONE once**. No retries were implemented or executed.

Serial transcript:
    KNX076 ARMED ONE_SHOT_4S_TTL (no pulse yet)
    KNX076 COMMITTING_ONE_35US_PIO_PULSE
    KNX076 ONE_SHOT_QUEUED_LOCKED_REBOOT_TO_REARM
    KNX076 STATUS gpio0_measured=LOW pio_ready=1 armed=0 shots=1 SINGLE_35US_PIO_NO_AUTO_TX

Subsequently DISARM and STATUS again, still LOW / armed0 / shots1.
The PIO hardware itself ended the pulse after 35 clock cycles; the one-shot
firmware remains loaded but locked against re-triggering until reboot.

PicoScope simultaneously acquired **1,800,000 samples on each channel**,
at **1 microsecond/sample**, 119 callback transfers, **0 driver overflows**.
Scope stopped/closed cleanly, no persistent recording job.

### Measured waveform, directly from saved ADC data

| Measurement | Live result |
|---|---:|
| Channel B KNX_TX peak HIGH | **3.3664V** |
| Channel B HIGH duration >1.35V | **35us** |
| Count of B pulses in entire 1.8s recording | **exactly one** |
| Channel A KNX+ baseline before pulse | **31.0655V** |
| Channel A KNX+ minimum during HIGH | **23.6267V** |
| Coincident bus voltage dip | **7.4388V** |
| Channel A droop more than 2V below baseline | from relative t=0us through t=+34us inclusive |
| Bus overshoot just after trailing TX edge | approx. **35.879V** |
| Return to 31.07V baseline | approximately 220us after first B rising edge |
| B LOW after pulse | approximately 0.086V |
| Firmware one-shot counter and status | shots=1, armed=0, GPIO0 LOW |
| Missing PicoScope buffers | **0** |

At relative t=0us B jumps to approx 3.32V, at the very same sample A falls
to about 27.56V; at t=+1us A reaches minimum 23.63V with B still HIGH.
At t=+34us both are still in their pulse states; at t=+35us B returns
to LOW and A rebounds to above 33V. This near-exact edge alignment
demonstrates a **causal physical transmit modulation** by the prototype,
not merely an unrelated ambient telegram. The prior 20V excursions in idle
captures cannot be conclusively categorized as normal KNX traffic without
a simultaneous telegram decode and may include scope transients.

The USB-only case KNX072 previously measured B peak1.94V and C1=0.3V
(no KNX supply). With powered bus, B now reaches 3.37V and modulates KNX+.
This is consistent with a power-domain/load difference but does not alone
prove the earlier low level was solely due to the STKNX VCCCORE.

## Evidence (kept private on LLO Home Downloads)

- C:\Users\ll\Downloads\KNX077_SCOPE_AB_ONESHOT_20261018_131602_result.json
- C:\Users\ll\Downloads\KNX077_SCOPE_AB_ONESHOT_20261018_131602_A_KNXPLUS.s16le
- C:\Users\ll\Downloads\KNX077_SCOPE_AB_ONESHOT_20261018_131602_B_TX.s16le
- C:\Users\ll\Downloads\KNX077_SCOPE_AB_ONESHOT_20261018_131602_event.csv
- C:\Users\ll\Downloads\KNX077_SCOPE_AB_ONESHOT_20261018_131602_aligned.svg

Raw scope analog traces and absolute system paths are **not committed** to
the public GitHub repository. The scripted method and generic test summary
are committed for reproducibility. No push performed.

## Interpretation and next gates

**Proven:** RP2040 PIO GPIO0 HIGH -> STKNX U9 TX output drive ->
measurable approx. 7.44V voltage dip on KNX+ for 35us -> clean return LOW.
The RP2040-to-STKNX-to-KNX line *physical TX modulation* works for one bit.

**Not yet proven:** a whole, valid KNX TP1 standard telegram from this board,
KNX/IP reception of board telegram, collision avoidance, parity/checksum,
ACK behavior, load/thermal behavior on many bits or over temperature,
boot/reset/brownout fail-low safety, U9 VCCCORE rating, U11 current/temperature
and sustained KNX bus health. Do not confuse KNX077 with completed bidirectional
KNX telegram exchange. The next engineering step is a bounded, valid TP1
single-frame sender with checksum, per-byte even parity, ACK handling and
bus arbitration, validated first offline and then on the scoped test bus.

**Do not send additional pulses without a new explicit test request.**
