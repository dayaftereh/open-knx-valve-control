# KNX022 – Hardware Readiness Preflight (STATIC ONLY)

**Stand:** 2026-10-12
**Status:** OPEN / Gate 4 – static risk report, negative guards, ASH/PCB regression PASS; commits pending
**Owner:** ChatGPT-OpenKNXValveControl-KNX002-StaticAsBuilt-20261012
**Session:** ses-20261012T085932-60961adfbfe9
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** main @ 4d12890, clean, 24 local commits ahead origin/main
**Slice-ID:** KNX022 (bounded preflight), **NOT** the physical as-built acceptance KNX002.

## Gate 1 – Checkup

- [x] Live LLO Desktop Agent 0.8.1; all previous sessions closed, no foreign Write locks.
- [x] Git main clean, baseline 4d12890, zero _OPEN_ markers; closed KNX021.
- [x] Verified existing V1.2 EasyEDA schematic/PCB exports, firmware config and prior schematic/PCB/power source audits.
- [x] Physical PCB assembly, voltage/current measurement, motor characterization and native EasyEDA ERC/DRC/BOM exports **not supplied**.

## Gate 2 – Decision

- Produce a **reproducible static** board-to-firmware/parts/rail/net check, with an explicit **NOT READY FOR ENERGIZED MOTOR** verdict. Do not mutate schematic, PCB, firmware, ETS XML or parts orders.
- Ensure automatic checks **detect** rather than accidentally waive blockers: TB6612 STBY permanently tied to 3.3 V; no controllable global motor kill; R29 supplier metadata vs nominal 200 mOhm; U25 ATtiny1616 supplier MPN vs ATtiny3216 firmware; F1 60 A metadata vs 630 mA schematic; shared INA219 and direction nets; U6 headroom and two-diode USB path; JMP1 not an external 5-V entry.
- Validate GPIO-to-net map (eight independent enable lines D10..D17, IN_1 D18 and IN_2 D19) statically. A mapping is NOT proof of safe boot output defaults.
- Create deterministic machine-readable risk/status report and human-readable evidence matrix with exact requests for physical as-built and deferred EasyEDA ERC/DRC and power testing.
- Do **not** imply KNX002/003/004/005/006 physical gates are passed; KNX009/016 stay deferred until separate KNX018 test setup. No physical interaction, KNX telegram, flash, motor movement, remote push.
- KNX022 can close after software-only QA; KNX002 remains planned, not automatically started.

## Gate 3 – Deliverables

- [x] tools/audit_knx022_hw_preflight.py read-only PCB+firmware+documentation evidence gate, deterministic JSON mode.
- [x] tests/test_knx022_hw_preflight.py checks known risk flags and detects altered critical nets/pin assumptions in synthetic copies.
- [x] docs/KNX022_STATIC_HW_READINESS.md with P0/P1 priorities, specific physical test checklist, no unsafe power entry advice; generated JSON artifact.
- [x] README/Roadmap cross-reference to preflight and unfulfilled KNX002 physical gate.

## Gate 4 – Validation

- [x] Preflight + tamper/guard tests PASS with readiness=NOT_READY, no contradictory PASS on physical safety.
- [x] Existing hardware static audit + native software regressions PASS, ASH links & diff --check PASS.
- [ ] Explicit implementation commit; HISTORY/ROADMAP update, remove marker in separate closing commit.
- [ ] Git clean, saved checkpoint, session closed, no remote push.

## Next exact action

Stage only KNX022-owned audit, unit-tests, risk report, documentation and roadmap/README edits; run git diff --cached --check and create implementation commit. Then write HISTORY, set Roadmap closed and remove this marker in separate closing commit. Verify clean Git, persist checkpoint and close session; KNX002 physical as-built remains planned and BLOCKING. No hardware actuation.
