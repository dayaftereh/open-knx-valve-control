# KNX038 – Units CH340 RTS/UPDI electrical gate and ATtiny build

**State:** open
**Date:** 2026-10-14
**Owner:** ChatGPT-OpenKNXValveControl-KNX038-UPDI-RTS-20261014
**Write-Session:** ses-20261014T083359-54467fd6f4fd
**Initial HEAD:** 1b7b649, main CLEAN ahead origin/main23

## Gate 1 – Live verification

- [x] Desktop Agent 0.8.2 online, no foreign session, COM4 CH340 VID/PID 1A86:7523 and COM7 RP2040 VID/PID 2E8A:000A are still enumerated.
- [x] Units Programmer v1.2 Schematic+PCB netlists and web serial service checked: U2/U7 SN74LVC1G3157, logical RTS=True DTR=True selects UPDI. USB-VCC runs both switches. Programmer CN1 pin1 CN1_1, pin3 UPDI, pin5/6 GND.
- [x] ValveControl V1.2: CN1 pin1 5V, pin2 RXD, pin3 UPDI, pin4 TXD, pin5/6 GND. U25 VDD 3.3V, UPDI pin16; intended ATtiny3216, PCB MPN typo ATtiny1616.
- [x] Target 3.3V/Programmer VCC ~USB5V interface cannot be presumed level-translated solely by RTS; real 2x3 cable and measured voltages not confirmed. No COM4 open/RTS/UPDI operation.

## Gate 2 – Offline firmware preparation

- [x] PlatformIO `pio run -e temperature` SUCCESS in 8.63s, 8655 Flash / 983 RAM bytes, output HEX.
- [x] Copied HEX/ELF to Desktop Builds/KNX038-ATtiny3216-offline-20261014; HEX 24356B SHA256 f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a. Manifest flash false.
- [x] `tools/knx038_updi_readiness.py` plan/probe/verify-build pass. Deliberately blocked real `ping` without specific physical gates. After gates, only `pymcuprog -d attiny3216 -t uart -u COM4 ping` read-only; expected reversed printed 21951E for signature 1E9521.
- [x] `tools/test_knx038_updi_readiness.py` 14/14 PASS, no hardware touched.
- [x] `docs/KNX038_UPDI_RTS_ELECTRICAL_GATE.md` + JSON evidence, README/ROADMAP/KNX018/KNX037 updated.

## Gate 3 – Formal QA

Pending final ASH, repository diff review and local commits.

## Gate 4 – Next physical work

Await user disconnecting six-pin cable from target temporarily to measure Programmer CN1.3 UPDI and CN1.1 VCC vs CN1.5/6 GND in RTS False/True modes; only after independent supply/signal gate reconnect target, first read-only signature and then separately approved ATtiny flash. KNX/motors stay off. No Git push.
