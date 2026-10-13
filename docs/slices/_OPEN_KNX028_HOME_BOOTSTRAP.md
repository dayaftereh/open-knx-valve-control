# KNX028 - LLO Home Offline-Initialisierung

**State:** ready-for-validation
**Gate:** 4/4
**Profile:** software/infrastructure
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX028-HomeResume-20261013 / `ses-20261013T094818-64b5967e87b2`
**Project root:** `C:\_myspace\workspace\open-knx-valve-control`
**Baseline commit:** `14795c6c7af6808bcff210d3a98bce814bac7461`
**Previous KNX028 commits:** `089a984`, `5128482` (home only, not pushed)

## Objective

Make LLO Home the primary offline development machine for OpenKNXValveControl:
establish reproducible host tools, ATtiny and RP2040 builds, USB upload mock
tests and portable software regressions without attached electronics.

## Scope and hard exclusions

- In scope: Windows SYSTEM/ll Git handling via per-process safe.directory,
  Python/PlatformIO/producer setup, exact Arduino-Pico/GCC/Platform pins,
  native x86_64 host compiler, offline tests/builds, README/ROADMAP docs.
- Out: USB/UPDI bootloader reset/flash, ETS/KNX bus, pin/GPIO interaction,
  motor outputs, any physical assembly qualification, force push, global
  PATH/registry/Git trust modifications.
- Original ETS XML, schematics/PCB, generated canonical `knxprod.hpp`,
  ATtiny source, motor GPIO and KNX firmware core must not be changed.

## Gate 1 - Checkup + analysis

**Status:** accepted

- LLO Home Agent 0.7.9, root `C:\_myspace\workspace\open-knx-valve-control`. Source started clean at `14795c6`.
- `main` tracks same GitHub `origin/main`; original Desktop and Home sync
  had been completed in KNX027. No foreign active Write session.
- Home Python3.11.7 / PlatformIO6.1.18 under `C:\Users\ll\.platformio`.
  Agent runs as SYSTEM, repo belongs to ll: repo-scoped Git trust only.
- Home started with no RP2040 platform, OpenKNXproducer, or host g++.
- Existing AppVersion2 and USB flash safety fences must be preserved.

## Gate 2 - Decision / plan

**Status:** accepted

- Install only pinned toolchain binaries under local user/Tools paths.
- Use upstream official OpenKNXproducer 3.12.2 release and verify WinLibs
  host compiler archive against the release SHA256 checksum sidecar.
- Keep PlatformIO RP2040 build in a temporary copied tree with canonical
  header SHA check. Never issue upload, USB reset, KNX or motor command.
- Fix `__getreent` using the proven Desktop compiler instead of patching
  foreign framework files. Pin selected PlatformIO fork commit.
- Preserve KNX027 historical scope-audit strength, allowing only exact
  intended platform/compiler pin changes.

## Gate 3 - Implementation

**Status:** complete

- [x] Install Raspberry Pi PlatformIO, Arduino-Pico 5.5.0, OpenKNX/TPUart,
  picotool/pioasm and OpenKNXproducer 3.12.2 for Home.
- [x] ATtiny3216 isolated temp build PASS (previous Home job-000032).
- [x] Diagnose Home failure: GCC16.1.0 plus Arduino-Pico5.5.0 reported
  `__getreent` missing from `malloc-lock.cpp:122`.
- [x] Pin `toolchain-rp2040-earlephilhower 5.140200.250530` (GCC14.3.0),
  official 4.1.0 URL, and PlatformIO fork Git SHA
  `5d4561a05e3b212660ac6fdd3fbfb328d1988aa1` in controller.ini.
- [x] RP2040 isolated builds PASS both before and after full pin.
  UF2 SHA256 `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805`,
  RAM 54108/262144, Flash 198340/1048576.
- [x] Windows native g++ 16.2.0 installed locally from the WinLibs pinned
  release, upstream checksum verified; no global system modification.
- [x] Native simulations: 11/11 script groups PASS incl KNX008, KNX013-15,
  KNX019-21, KNX023-26, Arduino-hardlock tests. KNX027 mock USB 8/8 PASS.
- [x] Update `tools/home_offline_check.ps1` (-Native, -ControllerBuild),
  `tools/install_home_host_compiler.ps1`, producer/compiler docs and
  KNX027 source guard to validate exact new pins.
- [x] Hardware preflight still reports 10 blockers; no real power qualification.

## Gate 4 - Validation, commit and close

**Status:** in progress

- [x] Isolated RP2040 success with toolchain+platform pins, no firmware/ETS change.
- [x] 11 native script-group regressions and 8 USB mocks PASS.
- [x] KNX027 historic scope guard repaired and PASS.
- [x] Reproducible `home_offline_check.ps1 -ControllerBuild` job-000072 exit 0. Identical UF2 SHA256 after whole smoke-test script.
- [x] Final ASH 30/30, 476 Markdown links, design 0 invariant failures, KNX026/027 scope PASS, staged diff --check PASS; README/Roadmap updated.
- [ ] Implementation commit; HISTORY and marker removal in separate
  ASH closing commit; no GitHub push.

## Known remaining hardware gates

KNX002..006 electrical and motor interlock qualification, KNX018 hardware
testbench, KNX009/016 real ETS6 import, USB ROM/1200-baud reset, external
supply/backfeed/actual flash chip size, INA219 current limits and STBY output
disable remain NOT verified. Host build/simulators are not release approval.

## Next exact action

Implementation software changes and snapshot evidence are validated; commit reviewed KNX028 files locally. Then append HISTORY and remove this open marker in an isolated ASH closing commit. No GitHub push.
