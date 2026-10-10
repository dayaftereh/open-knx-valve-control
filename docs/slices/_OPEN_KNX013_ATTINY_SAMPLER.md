# KNX013 — ATtiny Temperature Sampler

**State:** open
**Gate:** 4/4 (tests passed; closing commit pending)
**Profile:** software
**Opened:** 2026-10-11
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX013-20261011 / `ses-20261010T234330-d1ae08bd195f`
**Root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`
**Baseline:** `bfb6745`

## Objective

Correct all nine ATtiny3216 sensor pins for PCB V1.2; implement nonblocking 1-Wire conversions and retain trustworthy per-channel last-value, validity, fault and age state. Build and test without flashing or motor motion.

## In scope

- `src/temperature/config.hpp`, `temperature.hpp/.cpp`, `temperatures.hpp/.cpp`; initialization changes in ATtiny `main.cpp` to disable physically unrouted legacy SPI0.
- Small portable sampling/snapshot helpers, tests, read-only checker and documentation to make outcomes reproducible.
- Preserve legacy serial config and status messaging on PB2/PB3 in this slice. No new UART transport (KNX014).

## Out of scope

- RP2040 code, ETS XML/KNX transport, actual 1-Wire sensor hardware tests, flashing, KNX telegrams, motor movement, power/PCB changes.
- Any claim of successful on-board calibration/physical availability; as-built ATtiny part remains unverified.
- Remote push.

## Pre-existing / quarantined changes

- Git `main` clean before starting KNX013, locally 8 commits ahead `origin/main`.
- No `docs/slices/_OPEN_*.md` before this slice, no foreign active write.
- Existing firmware builds but all 9 ATtiny `Pin::T*` are inconsistent with V1.2; SPI SCK PA3 is physically unconnected.

## Gate 1 - Checkup and Analysis

**State:** complete

- Cross-checked PCB V1.2 U25 pads with installed megaTinyCore `variants/txy6/pins_arduino.h`.
- Pin mapping: T0=PA5/1; T1=PA6/2; T2=PA7/3; T3=PB5/4; T4=PB4/5; T5=PB1/8; T6=PC1/11; T7=PC0/10; T8=PB0/9.
- Firmware `requestTemperatures()` blocks by default, `temperature>0` rejects valid zero/negative, and `getTemperature` returns fake 0 for errors.
- DallasTemperature 4.0.5 supports `setWaitForConversion(false)`, `millisToWaitForConversion()`, address and CRC-checked reads. OneWire default constructor supports `begin(pin)`.
- PCB SPI0 PA3 SCK unconnected and legacy SPI CS mapping wrong. Legacy SPI source removed from the current build; its Git history is retained.

## Gate 2 - Accepted Plan

**State:** complete

1. Use PCB-correct named pins (`PIN_PA5`, etc.), eliminate invalid SPI runtime initialization.
2. Each of nine independent 1-Wire inputs cycles through: discover/address -> nonblocking convert -> wait conversion interval -> read -> retain last sample or flag fault -> wait next update; bounded retry if probe absent.
3. Store explicit validity/fault/age; preserve 0 C/negative measurements; reject DS18B20 power-on 85 C sentinel and disconnected/fault values; mark stale readings rather than forging temperature=0.
4. Keep last-known-good value separated from current validity; provide immutable snapshot interface for KNX014.
5. Unit/host simulation or invariant tests, PlatformIO ATtiny build, project ASH/PCB/link audits, Git diff/check, separate gate-4 closing commit.

## Gate 3 - Implementation

**State:** complete

- [x] Pin mapping and SPI disable (legacy SPI files removed)
- [x] Async sampler and snapshot data API
- [x] Native unit tests and 9-channel mock integration tests
- [x] README, firmware notes, KNX013 documentation and KNX014 risks

## Gate 4 - Validation

**State:** validation PASS for KNX013 software scope; Git closing gate pending

- [x] ATtiny PlatformIO build PASS, RAM 924/2048 bytes, Flash 8554/32768 bytes
- [x] Native C++ Core and real Temperature/Temperatures mock integration PASS; negative/zero, rollover, stale, recovery and disconnected
- [x] ASH 30 checks and 202 Markdown links PASS, PCB invariant audit 0 fail, KNX013 strict sensor audit 0 gap
- [ ] HISTORY and ROADMAP closed in the separate Gate-4 commit; marker removed
- [ ] Final clean Git after closing commit and session checkpoint; no push

## Next exact action

Stage/check ONLY KNX013 files; make implementation commit, then update HISTORY/ROADMAP to closed and remove this marker in separate closing commit.
