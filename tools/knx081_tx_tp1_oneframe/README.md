# KNX081: one fixed KNX TP1 frame from cellar line 1.3

Hardware: RP2040 U18 GPIO0 -> JMP3 -> STKNX U9 KNX_TX; RP2040 GPIO1
receives STKNX KNX_RX. This is diagnostic one-shot firmware, NOT a
production KNX TP1 stack or a configured ETS device.

Fixed nine-byte TP1 GroupValueWrite value 0:
BC 13 FA EF F1 D1 00 80 E5
Source 1.3.250 (verified free in the 2026-10-12 ETS export)
Destination 29/7/241 (unallocated test group)
XOR checksum FF, all even-parity bytes valid.

The PIO0 state machine sends exactly 48 logical-zero pulses (35us HIGH),
among nine 13-bit/104us standard TP1 characters. TX is LOW when idle.
No pulse is emitted at boot or on STATUS. A single transmit may occur
only after ARM FRAME and FIRE FRAME within 4s, while KNX_RX bus is quiet,
and exactly one attempt is allowed per firmware boot. No retries.

The associated host script knx081_scope_send.py controls one intentional
test: first check the firmware identity, idle bus 27-35V, TX LOW, start
synchronized PicoScope 3205D channels A KNX+ and B KNX_TX, repeat the
idle check, only then send one frame, and save both raw waveforms.
Run only with the user's authorization and a controlled KNX test bus.

Offline golden generator: ../knx081_tp1_frame.py
Waveform analyzer: ../knx081_scope_analyze.py
Independent Channel A TP1+ACK decoder: ../knx081_scope_bus_decode.py

Live acceptance: docs/KNX081_KELLER_TP1_TX_KNXIP_ACCEPTANCE_20261018.md
The real 2026-10-18 test passed:
- Channel B: 48 pulses, 35us each; typical high3.32V
- Channel A: coincident 7.44-7.88V bus dips
- Channel A-independent frame checksum/parity and 0xCC ACK valid
- MDT KNX/IP TUNNELING monitor received exactly one matching telegram
- No collision or retry; later STATUS attempted=1 and TX LOW

Keep physical ETS source address synchronized with the bus line and
do not copy the unassigned diagnostic group address into production.
The brief 4.014V spike in one TX pulse and prior U11/VCCCORE
supply/hardware issues still need characterization.

No new bus writes or Git push without user authorization.
