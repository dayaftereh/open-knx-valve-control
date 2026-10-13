# KNX031 – Offline UART-Frame-Diagnose und Golden-Vektor-Regression

**State:** open
**Gate:** 2/4 (Checkup & Decision accepted)
**Profile:** software
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX031-UARTTrace-20261013 / ses-20261013T112103-5136c7e6a837
**Project root:** C:\_myspace\workspace\open-knx-valve-control
**Baseline HEAD:** 688e7ce
**Git at checkup:** main CLEAN, 9 local commits ahead origin/main; no other sessions, no _OPEN marker

## Goal

Prepare an offline, read-only decoder for **existing** KNX014 ATtiny-to-RP2040 UART bytes, including per-frame CRC, sequence, nine sensor values, fault/age flags, and a native C++ codec golden-vector oracle. Helps discriminate UART framing/payload faults once separately captured bytes are eventually provided from an explicitly authorized measurement. Does NOT capture serial traffic on its own.

## Gate 1: live inventory – accepted

- LLO Home 0.7.9 and Git HEAD 688e7ce verified; no active write session or foreign edits.
- Native source of truth: lib/common/temperature_protocol.hpp KNX014 v1, 115200/8N1, A5 5A, header (version 1,type,seq,length), max payload 59, CRC16/CCITT-FALSE LE across header+payload. GET_SNAPSHOT 0x01 = 8 bytes, SNAPSHOT_RESPONSE 0x81 = 67 bytes (uptime LE32, reserved module status zero, 9 x [centiC signed LE16,age LE16,flags,fault]).
- RP client adds request sequence, 400 ms reply timeout, 100 ms interbyte reset, 15s offline; raw bytes **without timestamps and directions do not prove these timing properties or transport online**.
- Sensor flags from sampler_core.hpp (HasSample 1, Valid 2, Converting 4, Stale 8, Error 16); fault 0..8. T0 Vorlauf, T1..8 Ruecklauf, never substitute as room actual.
- KNX031 must keep all real firmware, ETS XML, PCB, KNX027 upload, KNX029 bundles, KNX030 passive OS snapshots unchanged. No physical board attached.

## Gate 2: decision – accepted

- New tools/knx031_uart_trace.py with plan (no I/O) and inspect --input <local file> --format binary|hex (reads local regular file only, maximum size bounded); no COM, socket, GPIO, reset, flash, ETS/KNX.
- Reconstruct frames as C++ Parser, CRC and v1 snapshot quality rules; label observed values vs usable values. Requests/responses cannot establish timeouts/online without timestamps and known capture direction. Distinguish unknown data and malformed response; fail closed; never issue outgoing GET bytes to hardware.
- Native C++ codec fixture oracle from exact project header; compare Python analyzer to C++ request and nine-sensor snapshot output and negative byte-stream tests.
- Add docs and hooks to existing LLO Home smoke runner, frozen-source scope audit, no new firmware outputs or implicit upload. Code & docs via implementation + ASH close commits, no Git push.
- Source only: trace analyzer/test/docs, no hardware driving.

## Gate 3
**Pending:** implement parser / fixture oracle / regression and docs.

## Gate 4
**Pending:** native+mock tests, frozen source audit, home smoke, history close, Git clean, no push.

## Next exact action
Implement safe offline Python UART trace decoder and C++ reference vectors, verify real producer-formatted sample and deliberate bad CRC/flags, document no source-of-truth timing or bus claims.

## Gate 3 – Verified implementation

**Status:** complete

- [x] Portable Python read-only `tools/knx031_uart_trace.py`: KNX014 v1 Sync/CRC16, request and 67-byte response parser, 9-channel little-endian snapshot decoder, flags/age/fault and no invented physical online status.
- [x] C++ golden-vector oracle `tests/native/knx031_uart_vector_oracle.cpp` compiles against unchanged `temperature_protocol.hpp`, validates known GET frame A55A010137004659 plus negative/zero/NoSensor/ReadFailed 9-channel snapshot.
- [x] Unit tests `tools/test_knx031_uart_trace.py` **15/15 PASS**; includes malformed length/version/CRC, semantically invalid flags with correct CRC, corrupted/resynchronized streams, truncated packet, sequence wrap, size/fmt/device-alias denial, no file I/O in plan and low-output remote-agent summary.
- [x] Real **synthetic** host-generated sample outside Git: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX031-native-oracle-example.hex`, GET + SNAPSHOT, 78 total source bytes including three prefix bytes; analysis 2 CRC-valid frames, 1 GET, 1 9-sensor response, zero CRC and sequence-pairing errors. Not a physical device capture.
- [x] Frozen source/firmware/ETS/PCB/upload audit `tools/audit_knx031_uart_scope.py` PASS vs `688e7ce`; no real USB, COM, KNX, UPDI or motor access.
- [x] Documented `docs/KNX031_UART_TRACE_OFFLINE.md`, README, ROADMAP, KNX018 and integrated Home Offline QA.
- [x] Whole `tools/home_offline_check.ps1 -Native` job `job-000172` **exit 0**, including KNX031/KNX029/KNX030 etc and all 11 previous C++ native script groups. No flashed hardware.

## Gate 4 – Next

- [ ] Recheck complete ASH source/reference and Markdown links after final docs, Git diff --check.
- [ ] Implementation commit (no firmware changes).
- [ ] Separate HISTORY close commit and remove _OPEN_KNX031_UART_TRACE marker.
- [ ] Confirm Git clean, no push, finalize ASH checkpoint and close session.

**Hard boundaries:** KNX018 physical test stand and KNX002–006 independent power/motor hardware gates remain open; offline frame validity is not link availability, KNX bus/ETS reception, 3,3V safety or motor qualification.
