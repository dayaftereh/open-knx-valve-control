# KNX036 – Desktop USB/COM First Contact (no KNX)

**State:** open
**Opened:** 2026-10-14
**Agent:** LLO Desktop 0.8.2
**Session:** ses-20261014T070830-4573d715007f
**Project root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Live Git baseline:** main, CLEAN, initial HEAD 14795c6 before local bundle synchronization
**Home migration:** 19 commits 14795c6..65011e9 transferred offline as Git bundle (SHA256 both sides 2C3B7FE59AFAB9B6F1B919A7A9AF0C94D0969472B1BAC28089D0196C57B86DB8), verified/fast-forwarded, now local HEAD 65011e9 ahead origin/main 19. No GitHub push.

## Gate 1 – Real desktop inventory

- The only OS serial ports on first read: **COM1 ACPI PNP0501 standard serial**, **COM3 Intel AMT SOL**. **Neither is proved to be RP2040 or UPDI**.
- Desktop .platformio Core 6.1.19 and Python available, but no g++/pio/pymcuprog in default PATH. Explicit `C:\Users\LLO\.platformio\penv\Scripts\pio.exe` exists. Use this Python (not isolated `C:\ASH\Tools\python-3.13.15\python.exe`) for repo scripts importing sibling modules.
- KNX030 read-only Windows snapshot captured successfully in `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-before-board-20261014.json` outside repo: 11 USB/PnP candidates, 0 RPI-RP2 volumes, 5 local network entries; seven real release gates false. No COM opened.
- Current prepared controller/main.cpp **must not be flashed to physical board**: setupKnx invokes TPUart ArduinoSerial Serial1 (UART idle HIGH incompatible with STKNX idle-LOW); KNX035 R17 pullup fault and post-overheat U9/U11 uncertain.
- KNX033–035 safety blockers: real R17 removal still not confirmed, actual U11 68 ohm user reported; D1 wire bypass, F1 T2.5A vs 630mA, U6 4.75V minimum VIN with D6 drop, CN1 UPDI 5V vs 3.3V IO; motor outputs not qualified. User says no KNX bus for first test; no motor connections.

## Gate 2 – Implementation decision

1. Prepare separate **no-KNX/no-motor RP2040 USB-CDC diagnostic firmware** not linked to existing controller KNX/ETS/TPUart. Keep KNX TX GPIO0 driven LOW after setup, do not use Serial1, Serial2, GPIO8..19, UPDI or any motor operation. This does NOT guarantee idle LOW during boot; no KNX is permitted at any time during first-contact trials.
2. Compile diagnostic UF2 **offline only**; no target upload/BOOTSEL/reset and no serial port opening. Require user to confirm R17 removed, F1/power setup and USB/UPDI voltage separation before any hardware action.
3. Document safe staged tests: OS passive per-device USB descriptor, then only after separate approval a single RP2040 USB CDC, then UPDI adapter **connected to PC only** for descriptor; connection of header CN1 and signature read require confirmed 3.3-V/5-V topology and correct device identity; never open COM1/COM3.
4. Static/negative tests to guarantee diagnostic build does not link motor/KNX driver; regression offline and separate Git commit(s). Do not push.

## Gate 3

Pending isolated diagnostic build and static contract.

## Gate 4

Pending QA, history close and Git status. Physical contact remains blocked until relevant electrical facts are supplied.

## Gate 3 – Implementation and real local host results

- [x] Transferred Home-only 19 Git commits to LLO Desktop via verified SHA256 offline Git bundle; no remote push and fast-forward to HEAD 65011e9, local working tree clean before KNX036 edits.
- [x] Desktop PnP baseline before-board recorded outside Git (11 present USB/port candidates, no RPI-RP2, 5 local adapters). First and second checks: **no additional COM, USB, RP2040 or bootloader candidates**, so no arbitrary COM1/COM3 opens.
- [x] Added completely independent `tools/knx036_usb_diag` source/config: USB CDC 115200 and 2s heartbeat only, GPIO0 KNX_TX driven LOW before Serial.begin, no KNX/TPUart/ATtiny UART/motor, upload forced to fail with `cmd /c exit 91`.
- [x] Actual desktop `pio run --project-dir tools/knx036_usb_diag -e knx036_usb`: **SUCCESS (37.99 s)**, 58,444 bytes flash / 8,740 bytes RAM. **No MCU connected, no upload attempted.**
- [x] Copied UF2 and ELF to external `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-usb-diagnostic-20261014` with manifest, all release flags false. UF2 SHA256 `ad8df9ba4426102fb240f2ebfbb9526071b91e563fab897ab04034ed766866de`, 141312 bytes.
- [x] `tools/test_knx036_usb_diag.py --check-build`: **8/8 PASS**, including UF2 magic, GPIO0-low ordering, source isolation and explicit reject-upload. KNX030 passive inventory 11/11 PASS, KNX035 STKNX source audit PASS, design audit 0 invariants.
- [x] [KNX036 Desktop first contact](../KNX036_DESKTOP_USB_FIRST_CONTACT.md), README, Roadmap and KNX018 bench docs updated; no source modifications to real control firmware or PCB/ETS.

## Gate 4 – Next

- [ ] Final ASH link/workflow and Git staged diff --check.
- [ ] Local implementation commit; append HISTORY and delete open marker in separate local closure commit; no GitHub push.
- [ ] Live hardware next: user's separately plugged-in **CH340 USB programmer alone** (no CN1 cable) can be detected only by safe OS inventory. Do not attach board's USB or UPDI until electrical gating and R17 status provided. USB CDC diag UF2 is built-only, no firmware/hardware release.
