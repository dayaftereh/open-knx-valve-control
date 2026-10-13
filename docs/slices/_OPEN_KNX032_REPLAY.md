# KNX032 - Recorded UART to virtual KNX KO25..35 full-pipeline regression

**State:** open
**Gate:** 2/4 accepted (live check / decision)
**Profile:** software
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX032-UARTtoKNX-20261013 / `ses-20261013T132826-46f2db69bae6`
**Root:** `C:\_myspace\workspace\open-knx-valve-control`
**Baseline:** `e0efd61`; `main` CLEAN, ahead 11 origin/main; no foreign active session / other open slice.

## Goal

Integrate the previously tested offline KNX014 trace validation (KNX031) with the **real source-level** RP2040 TemperatureBridge and TemperaturePublisher (KNX015) in a native PC process using a simulated serial queue and KNX GroupObject mock, without touching boards, KNX bus, or production code. Check all nine T0..T8, 0 °C, negative values, invalid probe, CRC mutation, stale transport, and P19 disabled gating.

## Gate 1 – live inventory (accepted)

- LLO Home Agent 0.7.9, HEAD e0efd61, working tree clean, no open markers, 11 unpushed local commits (must preserve, no push).
- Source truth unchanged: `temperature_protocol.hpp` KNX014 8-byte GET / 67-byte 9-channel reply, 115200/8N1, CRC16, per-frame payload flag checks; `temperature_bridge.cpp` receives 48 bytes per loop, request sequence starts at 1, rejects stale/wrong sequence/CRC and expires after 15s.
- KNX015 `temperature_publisher.cpp`: KO25..33 nine measurements DPT9.001, KO34 bool DPT1.002, KO35 validmask DPT7.001; minimum 250ms between accepted conversions; disabled until ETS `configured()` and P19.
- Existing `tests/native/test_temperature_publisher_integration.cpp` tests T0/T1 and status but not full 9-channel replay from an external saved KNX014 trace.

## Gate 2 – scope decision (accepted)

- Native host-only `tests/native/test_knx032_uart_to_knx.cpp` simulates a recorded sequence with production `TemperatureProtocol`, production `TemperatureBridge`, `TemperaturePublisher`, local SerialUART and KNXMock. No physical serial file/device or KNX.
- C++ oracle golden snapshot from KNX031 is input to a fail-closed validation/replay path. Incoming frame content is CRC+payload checked with production parser and then re-encoded with the mock RP client's current sequence for transaction consistency; this **is not literal on-wire replay**.
- Validate all 9 temps/flags, invalid/CRC/sequence cases, staleness offline, KO age/gating, P19 off, explicit rejection/retry, 250ms bus spacing, KO35 mask, no motor KO/GPIO.
- Include Python build/test runner using existing portable host g++, no new Toolchain requirement, and read-only fixture provenance.
- No ETS XML, firmware, motor logic, PCB, KNX027 flashing, KNX029/030/031 scripts changed. No USB, COM, UPDI, KNX sockets, reset, board power, motor; no GitHub push.
- Gate4: native tests + all existing Home QA, immutable source scope audit, docs/README/Roadmap, two local commits/ASH close.

## Gate 3 – implementation
Pending.

## Gate 4 – validation/close
Pending.

## Gate 3 – Implementation complete

- [x] New `tests/native/test_knx032_uart_to_knx.cpp`: in-memory, source-linked `TemperatureBridge` and `TemperaturePublisher`; validate saved KNX014 pair with original C++ parser/CRC/9-sensor quality, then re-encode snapshot on simulator's own sequence. Strict 4096-byte file limit checked before reading.
- [x] KO25..33 expected DPT9.001 for 7 valid sensors from original C++ KNX031 oracle, T0=0 °C, T1=-10.50 °C, T2..4/T7..8 realistic; T5 NoSensor and T6 ReadFailed must emit zero temperature updates. KO34 DPT1.002 offline->online->offline and KO35 DPT7.001 validmask 0x19F->0.
- [x] Real KNX015 publisher behavior under mock: P19 off and uncommissioned emit nothing, >=250ms between accepted virtual KO conversions, failed KO conversion retried, stale after 15s prevents new temps, false sensor values rejected.
- [x] Bad CRC, correct-CRC wrong sequence, correct-CRC impossible HasSample/Valid and malformed/truncated source all fail closed.
- [x] New `tools/test_knx032_uart_to_knx.py` compiles latest native KNX031 oracle plus actual `temperature_bridge.cpp` and `temperature_publisher.cpp` with native g++, optionally reads local saved KNX031 file using KNX031 validator. Default `plan` has no subprocess. No Arduino/USB/KNX/UPDI/GPIO/motor.
- [x] New `tools/test_knx032_replay_contract.py`: **8/8 PASS** independent contract cases, including native full replay, synthetic bad traces and explicit local HEX input. Native test runner itself also exercises 4 negative trace-file variants; real C++ native output PASS.
- [x] New `tools/audit_knx032_replay_scope.py`: PASS immutable prior files vs `e0efd61`, including RP2040+ATtiny firmware, ETS XML/header, KNX014/015 core, KNX027..031 tooling, PCB/schematic.
- [x] `docs/KNX032_UART_TO_KNX_OFFLINE.md`, README, Roadmap and home_offline_check.ps1 updated; 12 native test-script groups enabled with `-Native`.

## Gate 4 – Final QA

- [ ] Finish complete Home offline smoke (job-000194).
- [ ] ASH workflow/link audit and staged Git diff --check.
- [ ] Implementation commit, separately append HISTORY and remove this open marker in closing commit; no push.

**Not a real UART capture or device acceptance:** C++ source-derived bytes are synthetic and replay *reframes* response sequence. No physical Board, KNX bus, Motor or ETS6 test performed; KNX002..006 and KNX018 are still blocked.

## Gate 4 – Verification on LLO Home

- [x] Native full pipeline via `tools/test_knx032_uart_to_knx.py test` **PASS**; observed synthetic source-derived 77 bytes / 2 CRC-good frames / nine channels. 7 valid temperatures publish only as KNXMock GroupObject.value(KO25..33) with KO34/35 diagnosis, 15s timeout, 250ms gap, retry, P19/ETS gate. Four deliberately modified traces rejected.
- [x] Independent `tools/test_knx032_replay_contract.py` **8/8 PASS**: no-I/O plan, wrong sequence, corrupted CRC, semantic invalid flags, good native pipeline, explicit saved HEX path, missing compiler and Windows device alias negative cases.
- [x] Source scope audit PASS: all original production RP2040/ATtiny/KNX015/014/ETS/PCB/KNX027..031 sources unchanged, in-memory mocks only.
- [x] Home full offline smoke **job-000194 exit 0**, now 12 native-script test groups plus existing native regressions, USB/flash mocks, static guard and ASH gate checks; no controller build/upload invoked.
- [x] ASH audit 30/30 PASS with 515 local Markdown links, design audit 0 invariant failures. Existing hardware warnings unchanged (U6/5V, R29, STBY, U25).
- [ ] Stage selected files, Git diff --check, implementation local commit, separate HISTORY/marker closing commit.
- [ ] Confirm final clean main and checkpoint session, no GitHub push.

**This remains a native simulation, not a real KNX bus or physical-board acceptance.**
