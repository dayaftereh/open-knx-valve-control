# KNX039 – Real UPDI signature / readback of existing ATtiny3216

**State:** open, documentation/test phase after successful live UPDI operations
**Opened:** 2026-10-14
**Agent:** LLO Desktop 0.8.2
**Session:** ses-20261014T090511-ab1ae57f4086
**Initial HEAD:** 90dfc8e (main CLEAN, 25 unpublished commits ahead origin/main)

## Gate 1 – User-authorized live signature

- [x] User explicitly approved switching logical RTS to UPDI on connected CH340 and reading already flashed ATtiny; user states hardware/programmer previously tested. No KNX/motors requested.
- [x] Real desktop COM4 CH340 USB VID1A86:PID7523, RP2040 COM7 USB VID2E8A:PID000A, no competing session.
- [x] `pymcuprog --device attiny3216 --tool uart --uart COM4 ping`: Exit0, **Ping response 1E9521**, actual ATtiny3216 confirmed. User's 2316 utterance corrected by real chip response, PCB BOM 1616 metadata known wrong.
- [x] PySerial's default RTS=True/DTR=True selects programmer's UPDI MUX per Units V1.2 schematic. Exact physical voltage not measured; success proves communication only.

## Gate 2 – No-NVM-write backups

- [x] `pymcuprog ... read -m flash`: 32768 bytes fully read, 1888 bytes != FF, Intel HEX saved locally.
- [x] `... read -m eeprom`: 256 bytes all FF.
- [x] `... read -m fuses`: 9 bytes read, not written.
- [x] `... read -m user_row`: 32 bytes all FF.
- [x] Four source HEX files + SHA256 manifest private outside Git in `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX039-ATtiny3216-readback-20261014`.
- [x] Intel HEX validation PASS, existing readback does NOT match new 8655-byte temperature build: 8450 different defined image bytes, first diff at 0x0002. New image **not uploaded**.
- [x] No `write`, `--erase`, fuses, HV UPDI recovery, motor, KNX, or RP2040 reflash. All live evidence in `docs/KNX039_UPDI_READBACK_EVIDENCE.json`.

## Gate 3 – Documentation and QA

- [x] `docs/KNX039_LIVE_UPDI_READBACK.md`, README, ROADMAP, KNX038 postscript.
- [x] `tools/test_knx039_live_readback.py` 8/8 PASS on Desktop, re-verifies hashes of all four local backup files; KNX038 14/14 PASS.
- [x] Offline regression script extended to include KNX036/037/038/039 tests in host-only Python selection.
- [ ] Full Desktop `tools/home_offline_check.ps1 -Native` job-001367 status.
- [ ] Final ASH, staged diff --check, local implementation commit.

## Gate 4 – History, synchronization

- [ ] Append HISTORY and delete marker in closing commit.
- [ ] Verify Desktop and LLO Home clean, sync new local commits via SHA256-verified offline bundle, no GitHub push.
- [ ] User-facing report actual real read-only ATtiny3216 result; future temperature firmware program must be separately planned and previous readback preserved.

**Electrical note:** Tested user-supplied attached configuration worked for UPDI, but CN1.3 actual voltage and CN1.1 5V backfeed not independently measured; KNX035 R17/U9 and KNX034 F1/D1 gates still OPEN. Successful UPDI reading is not a blanket KNX/motor/power safety authorization.
