# KNX072 – USB-only RP2040 GPIO0 → JMP3 TX PicoScope test

**2026-10-17, LLO Home. Result: timing PASS; HIGH-level FAIL / TX NOT CLEARED.**
No KNX telegram transmitted; no KNX+ or KNX- conductor connected according to user.

## 1. Physical test gate

User reported:
- Both KNX bus conductors (+ and -) fully detached.
- USB-C only, RP2040 started in BOOTSEL ROM mode.
- PicoScope 3205D MSO channel B at JMP3 pads 2/3, probe attenuation 10:1,
  common reference to board KNX-GND.
- All tested activity is logic-level GPIO0; no KNX bus power was supplied.
  Physical disconnection/probe setting are based on the user's report, not
  electrically or optically independently confirmed by the agent.

Live Agent PnP: RPI-RP2 mass-storage D: (VID_2E8A&PID_0003), PicoScope
3000-series present (VID_0CE9&PID_1211). Local Git main clean before changes.

**Before flashing (BOOTSEL):** passive PicoScope B acquisition, 20,000 samples
at 5 us, raw input +/-500 mV scaled by the physically presumed x10 probe:
baseline 0.0461 V, minimum 0.0 V, maximum 0.1387 V. This is a local
LOW-level observation, not proof of safe behavior in *all* supply states.

## 2. USB-only diagnostic firmware

Added isolated PlatformIO environment:
\`tools/knx072_tx_scope_usb/platformio.ini\`
\`tools/knx072_tx_scope_usb/src/main.cpp\`.

Arduino-Pico v5.5.0 / RP2040 GPIO0. On boot it sets the output latch LOW before
making GPIO0 an output. It **never auto-sends**; only an explicit
\`ARM USB_ONLY\` (8-second time-to-live) followed by \`PULSE8\` can produce
exactly eight bounded pulses, nominally HIGH 35 us / LOW 69 us. It immediately
disarms and drives LOW after the single train. USB \`STATUS\`, \`STOP\`,
\`DISARM\` do not cause pulses. The PlatformIO automatic upload command
remains deliberately disabled to prevent mistaken deployment.

Fresh clean build success, UF2 143,360 bytes, SHA-256:
\`5604A5E98D58C7D0744BF3DF2C5FB6B16F72040857F48F5001B294045935DE59\`.
Physically user-reported USB-only, correct RPI-RP2 drive confirmed, UF2 copied
once to ROM mass-storage; RP2040 enumerated COM8 again. Explicit status
confirmed \`tx_low=1 armed=0 oneshots=0\` before any test stimulus.

## 3. Scope waveform and result

\`tools/knx072_tx_scope_usb/knx072_capture.py\` streams PicoSDK
\`ps3000a.dll\` channel B, DC-coupled, +/-500mV raw range, reported voltage
multiplied by physical probe factor 10. Driver supports temporary
\`PICO_BUSY (0x27)\` and \`PICO_NO_SAMPLES_AVAILABLE (0x25)\` before data
are available; both are retried. The first no-stimulus attempt stopped on
\`PICO_BUSY\`, no GPIO pulses; the corrected run captured successfully.

**Successful one-shot sequence:** PicoScope stream already active, then USB
\`ARM USB_ONLY\`, ACK, then \`PULSE8\` once. Scope captured **2,000,000 samples
at 1 us/sample**, no overflow, scope stop+close success. Firmware returned
\`TX_BENCH_COMPLETE 8_PULSES PIN_LOW\`, \`oneshots=1\`, \`armed=0\`,
\`tx_low=1\`.

Waveform from the *actual scope*:

| Measurement | Result |
|---|---|
| Raw 10x-scaled GPIO0/JMP3 probe LOW before and after | 0.0461 V median |
| Count of pulses (0.5 V threshold) | **8** |
| HIGH widths (>0.5 V) | 38, 34, 35, 36, 34, 34, 36, 35 us |
| LOW gaps | 70, 70, 68, 69, 70, 69, 68 us |
| Rising edge periods | 108, 104, 103, 105, 104, 103, 104 us |
| Absolute measured highest HIGH level | **1.942 V** |
| Peak first to fourth pulse | **1.618 → 1.757 → 1.850 → 1.942 V** |
| Fifth through eighth peak | approximately 1.942 V |
| Driver ring overflow | 0 |

At a 1.5 V threshold, the **first pulse measures only 24 us above
threshold** because its peak was only 1.62 V; later pulses are 34–36 us.
Do NOT confuse threshold-limited apparent width with intentional duration.

This demonstrates GPIO0/JMP3 pulse generation and correct approximate timing,
but **does NOT pass a valid digital HIGH-level test**.

## 4. Hardware analysis and next measurement

The STKNX official datasheet (ST DS12399 Rev 3, pp 11 and 13) specifies:
- \`VCCCORE = 3.3 V\`: guaranteed KNX_TX digital HIGH threshold **2.2 V**.
- KNX_TX maximum absolute input level \`min(5.5 V, VCCCORE + 0.3 V)\`.
- KNX_TX is digital input pin 24, \`VCCCORE\` is pin 20.

Measured 1.94 V is **below** the guaranteed HIGH threshold at nominal
3.3 V VCCCORE. Furthermore, if the STKNX is *not powered* by USB without KNX
voltage, GPIO0 HIGH may backfeed/clamp through its input protection.
The 1.62→1.94 V successive peak ramp is consistent with a loading or
power-domain interaction but does not establish it. Wrong measurement
reference/probe ratio or another hardware fault remain possible.

**STOP additional GPIO0 HIGH trials until the power domain is identified.**
Next hardware check with KNX bus still fully disconnected:
1. Measure U9 **VCCCORE pin 20** against board GND while USB only; independently
   measure MCU 3.3V rail against board GND. Validate probe/ground arrangement.
2. If VCCCORE is not valid, DO NOT drive KNX_TX while coupled to U9; first
   unplug USB and isolate JMP3 pad 3 (GPIO0) from pad 2 (U9 KNX_TX).
   Any subsequent pin-alone bench test requires safe grounds and USB-only power.
3. Resolve R17 history, U11 overheating, D1 bypass/USB-KNX backfeed and
   GPIO0 reset/BOOTSEL behavior before attaching **any live KNX bus**.
4. Only then consider buffered/fail-LOW STKNX TX PHY, scope observation on a
   current-limited isolated KNX test bus, and a single test GroupValueWrite
   to compare against the existing KNX/IP interface.

The receiver side **KNX071 IP→TP→GPIO1** already passed. KNX072 makes NO claim
that the prototype's real bus transmit path works.

Official manufacturer reference:
https://www.st.com/resource/en/datasheet/stknx.pdf

## 5. Evidence and safe firmware restored

Raw PicoScope ADC, JSON and sampled waveform are stored **only on LLO Home**:
\`C:\Users\ll\Downloads\KNX072_SCOPE_TX_20261017_215217.s16le\`
\`C:\Users\ll\Downloads\KNX072_SCOPE_TX_20261017_215217.json\`
\`C:\Users\ll\Downloads\KNX072_SCOPE_TX_20261017_215217_waveform.csv\`
\`C:\Users\ll\Downloads\KNX072_SCOPE_TX_20261017_215217_waveform.svg\`

After the test, a software-triggered 1200-baud CDC reset switched the RP2040
back to the ROM \`RPI-RP2\` mass-storage drive without requiring manual
BOOTSEL. The original known-good **KNX048 RX-only** UF2 (166,400 bytes,
SHA-256 \`AF6AA0F228BB6B294BD31F35A3C68B8758AFE2E3213DA7344A7FFFA5F236E70A\`)
was copied back. Board re-enumerated COM8 and its STATUS confirmed
\`armed=0 listen=0 buffered=0 dropped=0 observed=0\`.
**The pulse-generating test firmware is no longer running.** The source
and build output remain available for a later approved USB-only retest.

**NO Git push without user's explicit permission.**
