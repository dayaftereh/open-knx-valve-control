# KNX015 - KNX DPT9.001 temperature publishing and ETS configuration

**Status:** open (Gate 3 complete; Gate 4 validation passed, commits pending)
**Date:** 2026-10-12
**Session/Owner:** ses-20261012T051005-0c6ad855a3af / ChatGPT-OpenKNXValveControl-KNX015-20261012
**Repo:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** e2e54c6 (main clean, 12 local commits ahead origin/main)
**Profile:** software + KNX product generator offline QA

## Gate 1 - Verified live
- LLO Desktop Agent 0.8.1 online. KNX014 and KNX013 sessions closed; no prior open slice.
- main clean at e2e54c6, 12 local commits ahead origin/main; no push.
- Existing XML has 33 objects: T0..T8 are fixed KO25..33, DPT 9.001; parameter P19 PrePostTemperaturesOutput gates their ETS UI (default 1).
- Source KNX groupObjectTable.get(asap) indexes by 1-based KO number; DPT_Value_Temp equals Dpt(9,1), GroupObject.value sends.
- Product generator emits invalid hyphenated KO macro names and duplicate macros, not reliable as-is. KO1..33 MUST NOT change.
- Existing app version is 1; no previous proven ETS6 import.

## Gate 2 - Accepted decision and scope
- Transmit only valid and nonstale cached temperature values to KO25..33 using DPT9.001. KNX configured plus P19 enabled required. No fabricated temperatures.
- Append ETS parameters for periodic interval default 60s (bounds 10..3600) and change threshold default 50 centi-Celsius (0 disables change-trigger).
- Bounded scheduling: one KO per loop, at least 250ms between bus sends, 5s minimum between updates per sensor. Only mark sent after KNX conversion succeeds.
- Append diagnostics KO34 UART bridge online DPT1.002 and KO35 nine-bit valid-sensor mask DPT7.001. Do not touch existing KO1..33 or legacy DPT5.004.
- Sanitize bad C-identifier ComObject Name while preserving Text, Number, RefId and DPT; make producer-generated header safe regarding repeated numeric/object macros. Bump app version for changed schema; ETS6 installed product migration unverified.
- Native scheduler tests, isolated RP PlatformIO build, XML/index audit, ASH links and Gate4 QA. Never flash or move motors.

## Out of scope
Temperature room regulation, actuator scheduling, homing, motor power, real KNX/ETS6 hardware import test; no remote push.

## Gate 3 - Implementation
- [x] Generator/KO names fixed; append ETS interval/delta/diagnostics while preserving KO1..33
- [x] Hardware-independent telemetry policy + native tests
- [x] Integrate GroupObject DPT9.001 sends, ETS params and diagnostic KOs
- [x] README, technical doc and repeatable QA

## Gate 4 - Validation / Close
- [x] Native and KNX014 regression tests PASS
- [x] Isolated RP2040 PlatformIO build and generated header audit PASS
- [x] Source XML/index/KO/parameter layout audit and ASH/PCB/Markdown links PASS
- [ ] Scope implementation commit and separate Gate-4 close commit
- [ ] Clean Git, checkpoint, close write session; no push

## Next exact action
All firmware builds, eight native suites (two KNX013 + four KNX014 + two KNX015),
strict pin/ETS-product+ZIP/ASH/PCB audits passed. Stage owned KNX015 files only,
run git diff --cached --check, implementation commit. Then HISTORY/ROADMAP to
closed, remove marker in a separate closing commit, checkpoint and close
session. No push or hardware movement.
