# KNX078 - Full TP1 board TX, PicoScope ACK and KNX/IP monitor

**18 October 2026, LLO Home. Result: physical TP1 frame and ACK PASS; KNX/IP visibility NOT verified.**

## Task and controlled setup

User requested exactly one KNX GroupValueWrite from RP2040/STKNX on ETS-unallocated GA 29/7/241. Simultaneous PicoScope A = KNX+ bus and B = KNX_TX at JMP3, physical x10 probes with common KNX-/board GND. Passive MDT KNXnet/IP interface tunnel monitored concurrently. No retries.

Current private ETS export: 201 configured GAs, none in main group 29. Source individual address 1.0.250 is also unused among its devices. ETS topology contains IP interface at 1.0.1 and several KNX line couplers at x.x.0; the prototype's actual physical test-bus line relative to those couplers has not been established. The earlier KNX071 IP->board test succeeded on this address with IP tunnelling source 1.0.3.

## One deliberately harmless test telegram

- Source: 1.0.250
- Destination: 29/7/241
- Type: GroupValueWrite, 1-bit value 0
- Standard TP1 bytes: **BC 10 FA EF F1 D1 00 80 E6**
- Nine characters, 13 bits each, 104us/bit, 35us active logical-zero pulse
- 50 active pulses, 117 total frame bits, 12.168ms on bus
- Byte layout: control BC; source 10FA; group destination EFF1; routing/length D1; APDU 0080; checksum E6
- XOR over all nine bytes FF. All 9 byte start, stop and even-parity checks passed with the existing KNX070 decoder before flashing.

The fixed frame and 128-bit PIO packed words were validated by the offline tools/knx078_tp1_frame.py test:
2C3BE087 01D01088 F8FFC4BA 00003307. The last eleven bits are idle LOW, not active pulses.

## Firmware and strict one-shot safety

Firmware sources: tools/knx078_tx_tp1_oneframe/platformio.ini and src/main.cpp.
PIO0 at 1MHz clocks an 18-instruction loop, 104us per bit on either 0 or 1 path, 35us HIGH pulse only for bit0. PIO FIFO starvation or padding holds TX LOW. RX active-edge IRQ monitors bus, requires 10ms quiet before start and aborts/forces LOW on suspect collision. Only ARM FRAME and then FIRE FRAME within 4s can trigger one burst. Any FIRE attempt locks the firmware to prevent retries until reboot. No automatic sends at boot, STATUS, DISARM or STOP. This is an experimental diagnostic, not a KNX-certified link-layer implementation.

PlatformIO UF2 build SUCCESS, image 150016B, SHA256:
BCBCB4A16EFA1FB1E4D069727068D423D53BB00BE33B590836F4C44E84AA489F.

LLO Home live RP2040 entered BOOTSEL through CDC 1200baud, D: RPI-RP2 board ID and UF2 hash checked, flashed once, reenumerated COM8. Nonactuating USB STATUS: KNX078 STATUS tx_low=1 pio_ready=1 armed=0 attempted=0 collision=0.

## Real oscilloscope result

Host tools/knx078_tx_tp1_oneframe/knx078_scope_send.py started the PicoScope dual-channel stream before serial ARM. Scope preflight KNX+ median31.065V, TX 0.086V (maximum0.129V). After repeated STATUS and firmware ACK for ARM, it sent FIRE FRAME exactly once.

Firmware confirmation:
KNX078 FIRING_FIXED_FRAME_ONCE BC10FAEFF1D10080E6
KNX078 FRAME_TX_COMPLETED_ONCE collision=0 unexpected_rx_rises=0 edge_overflows=0
KNX078 STATUS tx_low=1 pio_ready=1 armed=0 attempted=1 collision=0 rx_edges=100.

PicoScope sample rate **1us**, **1,800,000 samples per channel**, 119 callbacks, **zero driver overflows**.

- **50** B/GPIO0 TX HIGH pulses, each exactly **35us** by scope sampling
- B peak voltage **3.323-3.366V**
- A KNX+ depression during those pulses **7.439-7.876V** vs baseline31.065V
- Pulse positions match intended 104us cells within 1us scope resolution
- No repeat, no abort, no collision; TX LOW and firmware locked afterwards

## Independent real KNX-bus A-channel decode and ACK

Tools/knx078_scope_bus_decode.py analyzed A KNX+ only, not the TX GPIO or firmware serial payload.
It reconstructed 56 analog active pulses: **50 from the entire nine-byte frame, 6 from the separate receiving node ACK**.

Frame: **BC 10 FA EF F1 D1 00 80 E6**. Nine valid start/stop+even-parity characters, checksum XOR FF. Decoded 1.0.250 -> 29/7/241 GroupValueWrite 0.
ACK: **0xCC**, valid parity and stop, at **+4us** from expected 13520us ACK start separation.

This proves full physical TP1 bus transmission and link-layer acknowledgement by **some** receiver or line coupler. A local ACK does not establish that the IP interface received the frame, nor identify who acknowledged.

## Actual IP monitor: no matching telegram

The existing xknx >=4 passive TUNNELING connection to MDT KNX/IP interface (the existing MDT KNX/IP gateway (port 3671)) was CONNECTED during the frame. It logged **6 unrelated GroupValueWrite** telegrams. It logged **ZERO** frames matching source 1.0.250 -> destination 29/7/241. No retry was attempted.

**DO NOT label the end-to-end board->KNX/IP route as passing.** It remains the only incomplete acceptance milestone.

Hypotheses, not confirmed:
- GA29/7/241 does not exist in the live ETS group-address list. A line coupler may have filtered it out of the path to the IP interface.
- Prototype's test segment versus the IP interface's line address and routing topology has not been established.
- The xknx TUNNELING group monitor may not expose every physical bus frame; a proper ETS Bus Monitor on the target segment is a useful additional diagnostic.
- KNX coupler ACK behavior may be set to always acknowledge even when no telegram is forwarded.

Supporting technical documents:
https://support.knx.org/hc/en-us/articles/115003363245-Filter-tables
https://support.knx.org/hc/en-us/articles/360007439260-Couplers
https://support.knx.org/hc/en-us/articles/360018712880-Bus-Monitor-Group-Monitor-and-ETS-Bus-Activity-Monitor
https://doc.bab-technologie.com/kscen/telegram-acknowledgement
https://www.st.com/resource/en/datasheet/stknx.pdf

## End state / health / no further transmissions

Post-TX passive PicoScope sampling for another 10s (no additional GPIO pulses) showed KNX+ median **31.065V** (range30.19-31.504) and KNX_TX median **0.043V** (max0.129); zero scope overflows. Later COM8 STATUS confirmed **tx_low=1, armed=0, attempted=1, collision=0**. Board's experimental KNX078 firmware remains loaded and locked. No pulse can be sent again without a deliberate restart/authorization. A further passive IP/scope comparison was inconclusive due to no natural telegrams during the scope's recorded window.

Full private raw evidence in the LLO Home Downloads directory:
- KNX078_TX_FRAME_GOLDEN_20261018.json
- KNX078_IP_Preflight_20261018.jsonl
- KNX078_IP_Live_20261018.jsonl
- KNX078_SCOPE_AB_TP1_20261018_142900_A_KNXPLUS.s16le
- KNX078_SCOPE_AB_TP1_20261018_142900_B_TX.s16le
- KNX078_SCOPE_AB_TP1_20261018_142900_result.json
- KNX078_SCOPE_AB_TP1_20261018_142900_event.csv
- KNX078_SCOPE_TP1_ACK_IP_COMPARED_20261018.json
- KNX078_IP_PassiveCrosscheck_20261018.jsonl
- KNX078_PASSIVE_20261018_143440_A.s16le and _B.s16le
- KNX078_PASSIVE_20261018_143440_meta.json

## Suggested next action

Without automatically editing ETS or sending again, inspect the actual prototype bus line relative to interface physical address 1.0.1 and the installed line couplers/filter tables. Compare ETS Bus Monitor and Group Monitor on the correct physical segment. If an explicit temporary coupler setting is needed for GA29, coordinate user approval; do not silently create production group objects or change actuator configuration. Only after determining the visibility block, perform a separately authorized single-repeat test.

U11 prior overheating, D1 bypass/backfeed and reset/brownout fail-low safety remain longer-term hardware/product gates. U9 VCCCORE was 0.3V in earlier USB-only test but was not measured today on the live KNX bus. Full KNX certification not claimed.

**Local-only Git commit; no push.**
