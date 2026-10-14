# KNX040 – Real ATtiny3216 Flash, RP2040↔ATtiny temperature UART test

**State:** open (validated hardware experiment, pending ASH QA and commits)
**Date:** 2026-10-14
**Owner:** ChatGPT-OpenKNXValveControl-KNX040-ATtiny3216-Flash-UART
**Session:** ses-20261014T093326-d43f98b15cf6
**Initial Git:** LLO Desktop main CLEAN 9af9436, 27 local commits ahead origin/main, no competing active Write Session.

## Gate 1 – Physical preflight

- [x] User authorized flashing current ATtiny Temperature firmware and testing temperature channel response. User explicitly reports **zero physical temperature probes attached**; KNX and motors not attached per ongoing isolated USB testbench.
- [x] COM4 CH340 VID1A86:7523, RP2040 COM7 VID2E8A:000A serial E464401787522D33, live PnP unchanged.
- [x] KNX039 four original backup files intact, full SHA256 matches, ATtiny known live signature 1E9521, new image SHA256 matches approved KNX038 build.
- [x] Production controller KNX stack remains hazardous due KNX035 STKNX active HIGH / TPUart normal UART; **do not flash**.

## Gate 2 – Real implementation/testing

- [x] ATtiny3216 COM4 `pymcuprog write --erase --verify --timing` actual pass, duration 5.644s, image HEX SHA256 f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a. Original installed firmware overwritten with express user consent.
- [x] Independent postflash full flash/fuses/EEPROM readback. 8655 defined firmware bytes exact; 0 non-FF outside; fuses and EEPROM unchanged. Real evidence outside Git in Desktop Builds/KNX040-ATtiny3216-postflash-20261014.
- [x] New isolated RP2040 USB/Serial2 UART1 diagnostic builds: pins GPIO8/TX PA2/RX and GPIO9/RX PA1/TX, KNX_TX GPIO0 set LOW only after setup, no motor/KNX/ETS. PIO upload deliberately disabled.
- [x] V1 real RP upload/verify SUCCESS, but 0 snapshots, root cause: installed Arduino-Pico SerialUART::availableForWrite returns BOOLEAN 0/1, not FIFO count. Normal production source src/controller/temperature_bridge.cpp has same broken <8 guard, untouched/blocked until own production-safety slice.
- [x] Isolated V2 fixes guard to `<=0`, build SUCCESS, RP2040 picotool ROM COM6 and verified flash 100%, reboot COM7.
- [x] Actual COM7 16s USB read: **8 valid 9-channel CRC snapshots**, 0 timeouts, 0 rejected, every channel T0..T8 `flags=16 fault=1 age_s=65535` (NoSensor) because sensors physically absent. First real v2 trace and JSON outside Git.
- [x] New read-only `tools/knx040_capture_uart.py` probe/plan/capture for repeat measurements. Live 10s real repeat capture **5/5 pass**, at least 153 accepted snapshots total from ATtiny since boot, 0 timeouts/rejects, nine NoSensor status channels, no fabricated 0°C.
- [x] Focused offline diag test 10/10 PASS, USB host parser/identity test 11/11 PASS; genuine raw traces stored outside git and referenced by docs/KNX040_LIVE_TEMPERATURE_UART_EVIDENCE.json. Detailed runbook docs/KNX040_REAL_TEMPERATURE_UART.md, README/ROADMAP/KNX039 updated.

## Gate 3 – QA

- [ ] Desktop focused ASH 30/30; staged diff --check; no native host compiler available on Desktop (known KNX031 issue).
- [ ] Implement and closure commits; no push.
- [ ] Verified local Git bundle sync Desktop → Home and full Home Native offline QA.
- [ ] Checkpoint + clean state and close sessions.

## Gate 4 – Next practical step

After user physically installs at least one real DS18B20 with power OFF and verifies actual 3-wire pinout, keep KNX and motors disconnected, then **read-only** rerun knx040_capture_uart capture on COM7. Expect real Valid flag + centiC for connected channel only. No current real sensor temperature exists or can be invented.

## Hardware block

STKNX R17 and possible U9 overheat damage, D1 jumper/F1 rating, CN1 5V vs U25 3.3V have not been electrically qualified. No KNX or motor use from this slice.
