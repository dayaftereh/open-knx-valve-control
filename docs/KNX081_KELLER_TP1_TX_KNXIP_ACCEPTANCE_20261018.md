# KNX081 - Keller TP1 -> KNX/IP acceptance

**Live date: 2026-10-18. Verdict: PASS.**

This is one separately authorized full-TP1 one-shot send from the RP2040
prototype installed at the end of cellar KNX TP line 1.3. Simultaneously
recorded KNX+ bus voltage (PicoScope A), STKNX KNX_TX (PicoScope B),
and incoming telegrams from the existing MDT KNX/IP tunneling interface.
No ETS project change, no actuator write or repeated test message.

## ETS and line address

The Oct 12 verified original ETS6 project archive contains 201 group
addresses. Main group 29 and test group 29/7/241 are unassigned.
The Keller line uses 1.3.0, 1.3.10, 1.3.11 and 1.3.40 through 1.3.45.
The chosen sender IA **1.3.250** is unassigned in this ETS snapshot.
MDT coupler 1.3.0 has mainBasicRouteConfig=3 and
subBasicRouteConfig=3. Manufacturer enum3 means group telegrams are
routed in BOTH directions without a group address filter.
The IP interface is on main line 1.0.

The preceding KNX078 test wrongly used physical sender IA 1.0.250
while the prototype is on physical line 1.3. KNX078 achieved real
bus-frame ACK but the IP monitor did NOT receive the frame.
KNX081 changes only that source address and corresponding checksum,
keeping the same destination, priority, hop count and test value.
The successful new end-to-end result strongly points to this as the
cause of prior invisibility, but the coupler's exact rejection/forwarding
decision for the old source was not instrumented.

## Exact sent telegram

Sender IA: **1.3.250**.
Group destination: **29/7/241**.
APCI: **GroupValueWrite**, single-bit value **0**.

Standard nine-byte TP1 frame:

    BC 13 FA EF F1 D1 00 80 E5

BC control, 13FA source, EFF1 group destination, D1 routing/length,
APDU 00 80, E5 checksum. XOR of all bytes equals FF. Offline
verification with the existing KNX070 TP1 decoder passed even parity
and start/stop bits in all nine characters.

Nine characters times thirteen 104us cells = 117 bit cells (12.168ms).
Exactly 48 logical-zero pulses, each 35us TX HIGH / 69us LOW.
PIO FIFO golden words (LSB first):

    2C3B2087 01D01088 F8FFC4BA 00003507

## Firmware and deployment

The new firmware is in:
- tools/knx081_tx_tp1_oneframe/platformio.ini
- tools/knx081_tx_tp1_oneframe/src/main.cpp
- tools/knx081_tx_tp1_oneframe/knx081_scope_send.py

Supporting tools: tools/knx081_tp1_frame.py,
tools/knx081_scope_analyze.py, tools/knx081_scope_bus_decode.py.

The RP2040 PIO engine emits 104us bit cells with 35us HIGH for a
logical zero and idle LOW for a logical one. There is no automatic
transmission at reset or when idle. A send requires explicit USB
ARM FRAME and FIRE FRAME commands within four seconds and 10ms of
KNX_RX inactivity. First attempted FIRE locks out any second try
until next reboot. Collision guard forces TX LOW on suspected
unexpected bus activity; no retry logic.

PlatformIO build succeeded; UF2 length **150016 bytes**.
SHA256 FFBBA33784CC03A16DF3E118E197882B55FF75A0EFBE524F75FD195EE8CBAC8C

Entered bootloader by official 1200bps CDC reset, verified RPI-RP2
D: mass storage and UF2 board ID, flashed UF2 exactly once. RP2040
re-enumerated as COM8. Non-actuating STATUS confirmed:
KNX081 STATUS tx_low=1 pio_ready=1 armed=0 attempted=0 collision=0
FIXED_SRC_1.3.250_TO_GA29/7/241_VAL0.

All new KNX081 tests passed (8/8); existing KNX070-079 unit suite
also passed (34/34).

## PicoScope dual-channel live measurements

PicoScope 3205D MSO via the Pico SDK. Both analog probes are assumed
to be physically x10, sharing a verified test reference.
Channel A is KNX+; Channel B is KNX_TX at JMP3.

Before FIRE: A KNX+ approximately 31.065V median, B TX 0.086V
median with maximum idle 0.129V. A second STATUS confirmed no
pre-existing armed attempt. Concurrent xknx KNX/IP tunnel monitor
was connected and receiving unrelated bus traffic before triggering.

A single ARM FRAME command, then ONE FIRE FRAME command were sent.
Firmware acknowledged the fixed frame was attempted and completed
without a reported collision. No retries, no automatic reboot.

**1,800,000 synchronized samples per channel at 1us/sample.**
PicoScope callbacks 119, dropped/overflow buffers 0; PicoSDK
STOP and CLOSE returned success.

- B: **48/48** high pulses, exactly **35us** each.
- B high typically 3.323-3.366V. One brief peak 4.014V
  in pulse47, but the pulse median remained 3.323V.
- A bus voltage drops synchronously by **7.439-7.876V**.
- Relative bit edge timing error at most 1us.

The short 4.014V overshoot needs separate electrical review,
especially relative to U9's VCCCORE, and does not by itself prove
that the STKNX absolute maximum rating is respected.

## Real bus decode and ACK independent of firmware

A separate decoder parsed PicoScope **Channel A only**, not the
firmware-reported frame nor Channel B. It identified **54** bus
active pulses: 48 from the outgoing standard TP1 frame and six
from a later bus ACK. Reconstructed full frame:

    BC 13 FA EF F1 D1 00 80 E5

All nine bytes passed framing/parity; checksum XOR FF, and
the decoded application service is 1.3.250 -> 29/7/241
GroupValueWrite value0. Received and decoded bus ACK: **0xCC**,
valid; ACK start offset +4us from the expected timing.

## KNX/IP monitor also received the exact message

The existing passive xknx TUNNELING monitor connected to the
MDT KNX/IP interface before firing. It logged 21 telegrams
during the observation window and exactly ONE match:

2026-10-18T19:19:05.299Z
1.3.250 -> 29/7/241 GroupValueWrite 0

Local time (Europe/Berlin) 2026-10-18 **21:19:05 MESZ**.

The matched source, destination, APCI and payload prove that the
test frame crossed from the board on TP1 line 1.3 through
coupler 1.3.0 and the main line to the KNX/IP tunnel.
This complements the previously completed KNX071 IP->board RX
verification. It does not establish production KNX certification
or actual valve group-object application behavior.

## Post-test board state

A separate non-actuating COM8 STATUS after acquisition confirmed:

KNX081 STATUS tx_low=1 pio_ready=1 armed=0 attempted=1 collision=0
rx_edges=96 FIXED_SRC_1.3.250_TO_GA29/7/241_VAL0

The test firmware is still installed, TX is idle LOW, and further
transmissions are locked until a deliberate reboot. No second
frame was sent. The scope was stopped and closed.
No ETS settings, couplers or other KNX actuators were modified.

## Private evidence on LLO Home Downloads

- KNX081_IP_preflight_20261018.jsonl
- KNX081_IP_live_20261018.jsonl
- KNX081_SCOPE_AB_TP1_20261018_211901_A_KNXPLUS.s16le
- KNX081_SCOPE_AB_TP1_20261018_211901_B_TX.s16le
- KNX081_SCOPE_AB_TP1_20261018_211901_result.json
- KNX081_SCOPE_AB_TP1_20261018_211901_event.csv
- KNX081_TP1_BUS_ACK_IP_CONFIRMED_20261018.json

Raw private IP/bus captures are NOT included in Git.

## Future production gates

Parameterizable KNX IA/group objects via ETS, GPIO fail-LOW on
reset/BOOTSEL/brownout, confirmed VCCCORE supply under KNX bus,
U11 thermal and value after prior overheating, D1/F1 and backfeed
review, proper TP1 arbitration/collision detection and ACK retry,
many-bit sustained stability, source mapping to device-object
layer and valve controls. The current one-shot test firmware is
not a complete KNX stack.

No Git push.
