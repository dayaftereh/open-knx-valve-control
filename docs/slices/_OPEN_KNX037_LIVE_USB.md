# KNX037 – erster Live-Flash RP2040 / COM5→COM7, ATtiny-UPDI RTS-Gate

**State:** open for local test/docs+Git close.
**Agent:** LLO Desktop 0.8.2
**ASH Write-Session:** ses-20261014T073953-b472c2b1389c
**Prior HEAD:** 6f7dee7, `main` CLEAN ahead21
**Safety:** KNX und Motoren laut Nutzer abgeklemmt. ATtiny-CN1-Verkabelung, 3.3V vs USB-5V-Pegel ungeklärt; COM4 niemals durch unseren Toolpfad geöffnet.

## Gate 1 – real USB baseline

- [x] COM5 VID/PID 2E8A:00C0 (RP2040 Blink), COM4 VID/PID 1A86:7523 CH340, COM1/COM3 intern. Windows/PlatformIO/PySerial stimmen überein.
- [x] Git CLEAN, 21 nicht gepushte lokale Commits vom vorherigen KNX036 Slice, keine laufenden Write-Sessions.
- [x] Nach KNX035 ist die normale TPUart/Serial1-Produktivfirmware für den STKNX **NICHT flashbar**; nur der KNX036-USB-only-Build ohne KNX- oder Motoransteuerung kommt in Frage.

## Gate 2 – Durchführung

- [x] RP2040 COM5 115200 read-only 0 Bytes; keine RTS/DTR auf COM4.
- [x] Verifizierte isolierte KNX036-UF2-Checksumme, 141312 Bytes.
- [x] Direktes `picotool -f` zuerst ohne ROM-Gerät abgewiesen (keine Schreibaktion). Anschließend ein `COM5 1200baud DTR True→False, RTS False` Touch, 0 Payload-Bytes.
- [x] Rom-PnP VID2E8A:0003, temporär COM6. `picotool info -a`: RP2040 Revision B2, Flashgröße **16 MiB**.
- [x] `picotool load -v -x` isoliertes KNX036 UF2: **100% write, 100% verify, OK**, automatischer Reboot.
- [x] Neue App COM7 VID2E8A:000A, USB-CDC 115200, echte Heartbeats 3/3 und 4/4 PASS. Re-Listen mit neuem Tool 3/3 PASS.
- [x] Zweites KNX030-PnP-Snapshot und Diff: COM5 entfernt, COM7 hinzugefügt, CH340 COM4 unverändert.
- [x] Units-Programmer U1 CH340 VCC per USB, U2/U7 SN74LVC1G3157 VCC ebenfalls USB, KNX-V1.2 CN1.1=5V/U25 VCC3.3V. Units Service `requestToSend:true` / `dataTerminalReady:true` für UPDI; **ohne Messung keine COM4-RTS- oder UPDI-Aktion**.
- [x] `tools/knx037_rp_usb_workflow.py` mit plan/probe/listen/guarded flash, nie COM4 oder Motor/KNX, und `tools/test_knx037_rp_usb_workflow.py` mit 11/11 Pass.
- [x] Dokumentation `docs/KNX037_DESKTOP_LIVE_USB_AND_UPDI.md`, JSON-Evidenz, README, ROADMAP, KNX036/KNX018 nachgetragen.

## Gate 3 – Verifikation

- [x] 11/11 neue Mock-/Contract-Tests PASS, reale wiederholte CDC-Heartbeat-Probe PASS.
- [x] KNX036-Diagnosequellen statisch 8/8 PASS, bevor Flash; AST/run-time notwendige Sicherheitsgrenzen dokumentiert.
- [x] audit_design 0 Invariantverletzungen, ASH 30/30 bei erstem Dokumentationslauf. Weitere Schlussprüfung offen.

## Gate 4 – Git und Abschluss

- [ ] Quellen und Docs stage, `git diff --cached --check`, Implementierungscommit.
- [ ] HISTORY, Marker löschen, Abschlusscommit und sauberes `main` prüfen.
- [ ] Desktop→Home Git-Differenz ohne GitHub Push synchronisieren (wenn konfliktfrei), Device-Live-Stand nur als Dokumentation, keine Hardware-Freigabe.
- [ ] Nutzer fragt zu 2×3-CN1-Kabel und 3,3-V-/5-V-Pegel. Ohne diese Belege **kein ATtiny-Flash, kein RTS auf COM4**.

**Wichtig:** Hardwarebus KNX und Motoren, sicherer U9-Ausfallzustand, F1/D1-Versorgung bleiben OFFEN; kein KNX-Produktivimage geladen.
