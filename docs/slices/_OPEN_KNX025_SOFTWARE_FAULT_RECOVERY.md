# KNX025 – Software-Faultsupervisor, Wiederanlauf und Diagnosen

**Date:** 2026-10-12
**State:** OPEN, Gate 4 QA done; implementation staging/commit next
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Session:** ses-20261012T124927-24a78824053f
**Owner:** ChatGPT-OpenKNXValveControl-KNX025-20261012
**Git baseline:** main clean @ 044eac5, 30 local ahead origin/main. All prior sessions closed, no other open slices.

## Gate 1 – Verified Checkup

- [x] LLO Desktop Agent v0.8.1 responsive; no other active writers, git clean, no _OPEN_ marker.
- [x] KNX024 strict, proposal-only DPT9.001/DPT5.001 room adapter and KNX023 100-ms RAM-only runtime confirmed; native simulation exclusively with fake backend and independent ACK token semantics, no real H-bridge.
- [x] Current actual ETS V2 KO1..35 P1..21 unchanged; V3 KO36..100/P22..39 proposed; real KNX009/016 deferred to KNX018.
- [x] KNX022 real physical hardware gate remains BLOCKED with ten unresolved electrical/BOM issues including four TB6612-STBY hardwired high.

## Gate 2 – Scope and Decision

- Software-only, portable fault supervisor on top of existing KNX024 room adapter and KNX023 PI/zone/motor-queue contract. No new GPIO, electrical/KNX/ETS product changes.
- Explicit initial state Unconfigured, not a false fault during boot. Diagnose WaitingForInputs until each used zone has fresh external room temp/setpoint or valid DPT5.001 (never use ATtiny manifold T0..T8 as room actual).
- Once a zone has had healthy inputs, stale/invalid active telegrams cause sticky fault, clear all software target inputs, cancel native mock queue (with matching stop ACK required before lease release), NO automatic restore when values return.
- Distinct simulated upstream KNX network offline vs independent ATtiny/manifold telemetry outage: online-to-offline simulated room input transport latches and inhibits software motion; T0..T8 bridge disappearance is diagnostic warning only and must not be substituted as room actual.
- Detect delayed supervisor ticks (software loop deadline only, not physical watchdog), DPT invalid frame (status-specific), configuration drift, synthetic backend/lease stop-ack fault, manual stop. Keep first fault sticky, zone index, time, queue state and counters.
- Explicit operator-authorized recovery allowed only when no software lease remains and virtual backend confirms all-off in native tests. Recovery destroys former inputs/positions and requires NEW configuration and NEW room telegrams; cannot bypass ARDUINO compile-time permanent motor hardlock.
- RP2040 main compiles and passively observes diagnostics while no ETS V3 KO binding exists. No new KNX transmitter or real motor-control integration.
- Native tests for boot/recovery, direct/PI mode, room source stale, malformed type, transport drop, delayed loop, virtual ACK timeout and late recovery, millis rollover, manifold telemetry warning isolation, Arduino hardlock.
- Run original 17 native suites, design/ETS/historical no-I/O checks, fresh isolated controller PlatformIO build, ASH 4 gates, two separate commits, checkpoint/close; NO push or board actuation.

## Gate 3 – Deliverables

- [x] lib/common/knx025_fault_supervisor.hpp standalone supervisor and diagnostic interface.
- [x] src/controller/main.cpp passive observer (not a live controller, no V3/GroupObject/hardware).
- [x] tests/native/test_knx025_fault_supervisor.cpp native synthetic fault/recovery/ACK modes.
- [x] tests/native/test_knx025_firmware_hardlock.cpp compile ARDUINO forever no motor arming.
- [x] tools/test_knx025_fault_supervisor.py native test runner and source audit.
- [x] docs/KNX025_FAULT_RECOVERY_DIAGNOSTICS.md and README/Roadmap links.

## Gate 4 – Validation

- [x] All KNX025 fault scenarios pass, plus prior 17 native suites and safety audits.
- [x] Isolated RP2040 UF2 firmware build passes with no I/O/KNX XML/PCB/ATtiny changes.
- [ ] Staged Git whitespace validation, ASH 30 gates and all Markdown links PASS.
- [ ] Own-only implementation commit and separate ASH closing HISTORY/ROADMAP/marker removal commit.
- [ ] Git clean, checkpoint, session closed, no GitHub push, no physical action.

**Next exact step:** Stage only KNX025-owned files, verify diff --cached --check, implementation commit. Then add HISTORY, set Roadmap to closed, remove marker in separate closing commit, rerun ASH/19 native + no-I/O audits, persist checkpoint and close the write session. No GitHub push, no electrical motor or ETS action.
