# KNX023 – Laptop-UPDI-Teststand und firmware-sicherer Offline-Regelpfad

**Datum:** 2026-10-12
**Status:** OPEN – Gate 4 QA/Commitvorbereitung, Implementierung und Build PASS
**Session:** ses-20261012T110701-938ee188aa65
**Owner:** ChatGPT-OpenKNXValveControl-KNX023-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** 3b47fa7, main clean, 26 lokale Commits vor origin/main, keine bestehenden _OPEN_ Marker

## Gate 1 – Checkup
- [x] Desktop Agent 0.8.1 live, previous KNX022/UPDI read-only sessions closed, keine konkurrierende Write-Session.
- [x] Git clean, HEAD 3b47fa7, 26 local ahead; kein gepushter/übertragener Laptop-Klon.
- [x] Units-Projektreferenz gelesen: Desktop C:\ASH\Workspace\Projects\Units mit V1.2 CH340G/RTS-UPDI/UART Programmer; Laptop Units alt und kein OpenKNX Repo vorhanden.
- [x] Produktions-RP2040 Firmware: KNX-TP und Temperatursnapshots aktiv; KNX019/008/020/021 bisher nur native und nicht in src/controller/main.cpp eingebunden.
- [x] Real KNX, Board/Fuse/Shunt/3.3-V-Level/Hardware-All-off ungeprüft; keine reale Motorfreigabe.

## Gate 2 – Scope & Grenzen
- Dokumentiere geplanten Laptop-Teststand KNX018: eigener Laptop-Agent und lokales Netzwerk-KNX/IP, RP2040 per USB, ATtiny über V1.2 RTS-gesteuerten CH340G-UPDI/UART-Programmer, DS18B20 T0..8, später EIN Ventilantrieb M1 nach KNX002–006.
- Dokumentiere CN1-Steckerbelegung und kritischen Unterschied: Programmer CN1.1 stammt aus USB-Versorgungs-/Diodenpfad, Controller CN1.1 = 5V, ATtiny selbst VCC 3.3V; elektrischen Pegel-/Rückspeiseschutz vor Direktanschluss prüfen. U25 physischer 3216 vs BOM 1616 ungeprüft. Keine Autodetect-/Flash-/Motoraktionen.
- Integriere KNX019 PI -> KNX008 Zonen-Routing -> KNX020 exklusiver Queue -> KNX021 virtueller Feedback-Treiber in ein **software-only, hardwareausgangsloses** RP2040-fähiges Laufzeitobjekt. Default DISARMED, vollständig synthetische Quellen und Positionen, auf ARDUINO/Produktivbuild ist Armierung zur Laufzeit abgeschaltet. Keine neuen KNX-KO-Interpretationen, keine Firmware-GPIO-Motorupdates.
- Native Tests für Normalfall, Fail-Closed, Reboot, Temperatur/Zielstale, ACK-Timeout, Output-Lease, Firmware-Verdrahtung. Isolierter RP2040 Build und ABI/ASH-Regressionen soweit reproduzierbar.
- KEINE realen UPDI-/RP2040-Flashvorgänge, KNX-TP-/ETS6-Aktionen, Motor-GPIO, Bestellvorgänge oder GitHub-Push; KNX002/003/004/005/006 und KNX018 Tests offen, KNX009/016 deferred.
- Füge keine EEPROM-Schreibvorgänge hinzu, belasse KNX-DPT5.004-Altobjekte unverändert.

## Gate 3 – Deliverables
- [x] docs/KNX018_LAPTOP_UPDI_TESTBENCH.md mit Quellen, Stecker-/RTS-Tabelle, Stufenplan und Freigabeliste.
- [x] lib/common/room_control_runtime.hpp: portabler Koordinator für echte KNX008/019/020/021 C++-Modelle, virtual-only Backend, default disarmed, ARDUINO-simulation-arm blocked.
- [x] src/controller/main.cpp: nur RAM-basierte Registrierung/Tick des Simulationsmodells (niemals Hardware-GPIO/KNX write).
- [x] tests/native/test_knx023_room_control_runtime.cpp und tools/test_knx023_room_control_runtime.py: Test-Armierung nur im Native-Test, Sicherheitsaudit.
- [x] tools/audit_knx023_firmware_offline.py, Doku, README/Roadmap/KNX018-Referenz.

## Gate 4 – Validation & Abschluss
- [x] Neue Native-Suite inklusive Failsafe, Regression KNX008/013-015/019-021 PASS, isolierter Firmware-Build geprüft.
- [x] Produktions-ETS/PCB/ATtiny unverändert, No-Motor-GPIO-Audit; ASH 30 Checks, relative Markdownlinks, git diff --check.
- [ ] Implementierungscommit nur owned files, HISTORY/ROADMAP/Markerentfernung separater ASH Closing-Commit.
- [ ] Git clean, Session-Checkpoint und Close; kein Push.

**Next exact action:** Testbench dauerhaft dokumentieren, dann fail-closed RP2040 Software-Runtime implementieren und native/isolierte Build-Tests. Niemals tatsächliche 5-V-Leitungen, Programmer oder Motorports ohne Hardwarefreigabe schalten.
