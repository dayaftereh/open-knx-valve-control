# KNX024 – ETS-Raumdatentypen und Offline-KO-Eingangsadapter

**Date:** 2026-10-12
**Status:** OPEN, Gate 4 validation/commit; 17 native C++ suites, 13 Python negatives, RP2040 isolated build, no-I/O audits PASS
**Session:** ses-20261012T115932-b5e39af35663
**Owner:** ChatGPT-OpenKNXValveControl-KNX024-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** main clean @ 99d7244, 28 local commits ahead origin/main; no other open slice marker or active writer.

## Gate 1 – Checkup
- [x] LLO Desktop Agent v0.8.1 live, project session list and Git HEAD/status/open slice markers checked.
- [x] KNX023 software runtime closed and build passed, with ARDUINO hardlock against any motor output.
- [x] Existing KNX008 proposal JSON reviewed: proposed-only AppVersion3, 65 KOs36..100, parameters22..39, for each zone Ko36+4*z setpoint DPT9.001 RX, +1 room actual DPT9.001 RX, +2 direct demand DPT5.001 RX, +3 requested output DPT5.001 TX.
- [x] Official KNX DPT specification consulted: DPT9 2-byte float 0.01*M*2^E and 0x7FFF invalid; DPT5.001 scaling 0..255=0..100 percent differs from legacy 5.004 0..255 percent.
- [x] Productive KNX V2 XML / 35 KOs / P1..21 remains unchanged; physical ETS import KNX009/016 deferred for planned KNX018 laptop bench.

## Gate 2 – Scope
- New **portable, purely in-memory** adapter from proposed ETS KO36..67 typed frames to existing KNX023 runtime input structs and valid/fresh timestamps.
- DPT9.001 strict 2-octet signed mantissa/exponent, invalid sentinel 0x7FFF, room-temp/setpoint domain validation; DPT5.001 strict 1-octet scaling. Explicitly reject KO17..24 DPT5.004 and all KO TX objects as input.
- Fail-closed on malformed known input telegrams, stale/sensor loss, configuration changes, wrong type and wrong mode; no unconfigured/bootstrap data reuse. Pure software encoder for proposed requested-output KO (no bus send).
- Native tests: eight-zone KO mapping, positive/negative and exponent DPT9 decoding, invalid-sentinel, wrong sizes, DPT mismatch, DPT5 scaling, time freshness/wrap, PI-to-zone control adapter, reset and mode reassignment, output gating/legacy object rejection.
- Audit exact contract vs KNX008 proposal and production ETS ABI, isolated RP2040 firmware compile if adapter wired into main as inert no live KNX binding. No XML/knxprod/PCB/ATtiny hardware change.
- No actual GroupObject hookup or bus/ETS6 import, no GPIO/motor commands, no flashing, no push.
- Closing ASH Gate4 in two commits, no automatic KNX025 start.

## Gate 3 – Deliverables
- [x] lib/common/knx024_room_dpt_adapter.hpp
- [x] Native tests and runner plus negative DPT/KO suites.
- [x] Reproducible product/proposal + no-actuation source audit.
- [x] Firmware only compile-checks adapter header/static KO36..67 assertions; NO adapter instance bound to live GroupObject or generated V2 ETS KOs; isolated actual Build PASS.
- [x] docs/KNX024_ETS_ROOM_INPUT_CONTRACT.md, README, KNX008/KNX023 crosslinks, Roadmap.

## Gate 4 – QA
- [x] New native suites PASS, prior 15 native suites PASS, strict ETS DPT/KO audit and unchanged existing product PASS.
- [x] Isolated firmware build PASS if firmware touched; PCB/design/ASH gates PASS.
- [ ] Separate implementation commit, HISTORY/ROADMAP update and remove slice marker in closing commit.
- [ ] Git clean, saved checkpoint, session closed. KNX009/016 and physical gates remain deferred.

**Next exact action:** Stage KNX024-owned files only; run git diff --cached --check, commit implementation. After that add HISTORY, mark Roadmap closed, remove marker in separate closing commit, rerun ASH and source/native gate; verify clean Git and close session. No remote push or real KNX/motor action.
