# KNX070 - Passive TP1 decode and KNX/IP cross-check

Date: 2026-10-17. Tested LIVE on LLO Home.

## Existing KNX framework
The production controller (src/controller/controller.ini) already depends on
https://github.com/OpenKNX/knx.git and includes knx.h.
The flashed KNX048 diagnosis firmware (tools/knx043_passive_rx) is deliberately
different: it captures STKNX U9 RX edges on RP2040 GPIO1 only and holds GPIO0 TX LOW
after startup. It must not be replaced with production TX firmware yet.

KNX070 adds tools/knx070_tp1_decode.py (offline edge-to-telegram parser),
tools/knx070_ip_monitor.py (passive KNXnet/IP tunnelling with xknx 4.0.0)
and tools/knx070_compare.py (offline time-keyed correlation).
The KNX/IP endpoint is the existing MDT SCN-IP000.03. CLI arguments provide
its LAN IP; no private LAN addresses are hard-coded or committed.

The IP monitor performs only KNXnet/IP tunnel setup, keepalive, incoming ACK and
disconnect. No KNX GroupValueRead/Write or state updater. The tunnel occupies
one interface connection slot temporarily. Stop gracefully to release it.

## TP1 physical decoding
9600 bit/s; 104 us nominal bit time; an STKNX RX HIGH pulse ~35 us means logic 0.
Each octet has 1 start bit, 8 LSB-first data bits, even parity, 1 stop bit,
2 idle bits (13 bit-times between character starts). After the last octet,
15 bit-times of idle follow the end of the character, then ACK 0xCC or NAK/BUSY.
XOR of all TP telegram octets including the check octet must equal FF.
The tool also reconstructs source/destination, group address, hop count,
APCI (GroupValueRead/Response/Write) and raw payload.
2-byte values have only a possible DPT9 candidate; ETS DPT mapping is required
to determine real type/unit. No KNX Data Secure decrypt or extended frames.

## VERIFIED results

Earlier KNX069 COM8 log (2026-10-17 00:00 local): 4408 edges, dropped=0,
28 full TP1 telegrams, 28/28 parity and XOR checks valid, 28/28 ACK=CC.
One example: BC 10 02 18 03 D1 00 00 9B decodes as
1.0.2 -> 3/0/3 GroupValueRead; response from 1.2.10 to 3/0/3 is
BC 12 0A 18 03 C1 00 41 C0, GroupValueResponse value=1.

NEW KNX070 simultaneous monitor, 2026-10-17 approximately 12:14-12:15 local:
- IP: 32 received KNXnet/IP tunnel telegrams over the full monitor interval.
- RP2040: 16 valid TP1 telegrams, each with parity/checksum/ACK valid.
- Within the actual serial LISTEN window there are exactly 16 IP telegrams.
- All 16/16 paired with unique same-source, same-group-address, same-APCI,
  byte-identical payloads: 0 unmatched TP; 0 unmatched IP during LISTEN.
- 16 other IP telegrams are OUTSIDE the serial capture window, not RX losses.
- Absolute IP vs Windows USB log timestamp skew: median 27.5ms, max 99ms.
  This measures host/USB reporting lag, NOT physical KNX transmission latency.

Example source / destination / identical payload:
  1.5.50  -> 4/4/2:  19 22
  1.3.43  -> 4/2/1:  1A A8
  1.6.47  -> 4/5/0:  19 2B
  1.6.49  -> 4/5/5:  1A 6A
  1.5.42  -> 4/4/7:  1A 68

## Reproduce offline (Python 3.11)

    python tools/knx070_tp1_decode.py --input serial.log --output tp.json
    python tools/knx070_compare.py --tp-json tp.json --ip-jsonl ip.jsonl --serial-log serial.log --date 2026-10-17 --utc-offset-minutes 120 --window-ms 250 --output comparison.json --matched-csv matching.csv
    python -m unittest discover -s tests -p "test_knx070*.py" -v

Optional passive IP monitor (isolated Python venv with xknx==4.0.0):

    python tools/knx070_ip_monitor.py --gateway GATEWAY_IP --local-ip PC_IP --seconds 60 --output ip.jsonl

Keep the safety gates in tools/knx043_rx_capture.py. USB receive uses
STATUS / ARM LISTEN_ONLY / START LISTEN / STOP only; NO bus TX.

## Local evidence (not committed to public Git)
On LLO Home C:\Users\ll\Downloads:
KNX069_RX_COM8_20261017_000009.log
KNX070_telegram_decode_20261017.json
KNX070_RX_COM8_20261017_121431.log
KNX070_IP_tunnel_overlap_20261017.jsonl
KNX070_TP_frames_overlap_20261017.json
KNX070_TP_vs_IP_result.json
KNX070_TP_vs_IP_matched.csv

## Hardware safety remains UNSOLVED
Prior U11 overheating, D1 diode bypass/backfeed and rejoined JMP3 TX input
remain unresolved. GPIO0 LOW is software-only AFTER firmware startup; BOOTSEL,
reset and brownout are not fail-low proven. This PASSIVE RX success does not
authorize KNX TX or production controller deployment.
Next: import ETS group address/DPT metadata to interpret engineering units.
