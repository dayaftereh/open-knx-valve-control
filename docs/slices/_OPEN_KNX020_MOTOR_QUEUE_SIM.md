# KNX020 – Exclusive motor motion queue, mock-only

**Date:** 2026-10-12
**State:** OPEN, Gate 2 complete; Gate 3 implementation
**Session:** ses-20261012T065524-cf5653ce7709
**Owner:** ChatGPT-OpenKNXValveControl-KNX020-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** 386d305, main clean, 20 local commits ahead origin/main

## Gate 1 – Verified

- [x] LLO Desktop Agent online, KNX019 session completed, no competing active Write session.
- [x] Git clean at 386d305 with zero existing _OPEN slice markers.
- [x] KNX008 returns software-only eight-channel MotorTargets; KNX019 eight-zone PI produces software demand only.
- [x] KNX004 production motor safety & scheduler planned, but requires KNX002 As-built and power decision for any actual motor/driver build and test.
- [x] Existing board uses common IN_1/IN_2 direction pins and one shared INA219 upstream of eight TB6612 channels, so physical motor concurrency must be ONE.
- [x] KNX009/016 live ETS/KNX integration deferred until standalone KNX018 setup.

## Gate 2 – Decision

**KNX020** is an explicitly scoped, purely native C++ **simulator and contract prototype**, not implementation/closure of KNX004.

- Maximum eight pending intents derived on each step from KNX008 eligibleMotorMask, never from unverified hardware firmware output. No stored stale queue: current targets re-evaluated before starting.
- Simulator positions and hypothetical full-stroke travel durations must be injected separately with referenced + revision evidence; do not assume HmIP-VDMOT current endpoints, motor polarity or travel time from manufacturer's 120mA maximum rating.
- Default DISARMED. Explicit qualified guard + an all-off acknowledgement required before the simulator accepts grants; guards represent mock evidence ONLY, cannot certify physical safety.
- Reserve exclusive motor lease before issuing Start event; acknowledge Start with matching token; on target loss, changed demand, fault, timeout, operator cancel or power/interlock loss issue Stop intent and await matching all-off acknowledgement before releasing the lease.
- Repeat Stop intent until acknowledged; missing Stop ACK latches Fault and never releases any second motor lease without explicit reset and verified off condition.
- Simulate bounded per-channel travel duration, Start/Stop ACK deadlines, deadtime between motors, round-robin fairness, and no same-request replay without position-estimator revision.
- Expose test events (Start, Stop), NEVER PWM pins, KNX objects, motor driver's enable or real actuation. Do not copy code into src/controller, do not flash hardware.
- No ETS product XML/header modifications, KNX009/016 stay deferred. No push.

## Gate 3 – Deliverables

- [ ] lib/common/motor_queue_simulator.hpp with explicit states, lease/token and guard/ACK semantics
- [ ] tests/native/test_motor_queue_simulator.cpp exercising concurrency, fairness, stale/changed targets, fault/safety, ACK mismatches, timeout/reboot, wraparound, and integration with KNX008
- [ ] tools/test_motor_queue_simulator.py native runner
- [ ] tools/audit_knx020_motion_offline.py verifying immutable production firmware/ETS and source contains no hardware APIs
- [ ] docs/KNX020_MOTOR_QUEUE_SIMULATION.md and README/Roadmap updates

## Gate 4 – Validation and ASH

- [ ] Native simulator tests and KNX008/KNX019/KNX013-015 regressions PASS
- [ ] Immutable product and hardware firmware audits PASS, ASH/link and PCB static PASS
- [ ] git diff --cached --check and two-phase commit/closing marker removal
- [ ] Clean main, checkpoint and session close

**Next exact action:** implement mock-only queue contracts with fail-closed ACK handling and exhaustive tests. No actual motor output, GPIO or KNX write. Close KNX020 as standalone mock slice; KNX004 remains planned with hardware prerequisites.
