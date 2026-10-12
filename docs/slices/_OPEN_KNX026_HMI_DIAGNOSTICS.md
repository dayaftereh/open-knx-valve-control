# Slice KNX026 - Read-only HMI- und Diagnosemodell

**State:** open
**Gate:** 2/4 (Gate 1/2 akzeptiert, Gate 3 als naechstes)
**Profile:** software
**Opened:** 2026-10-12
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX026-20261012 / ses-20261012T134127-e6b5d94c44e8
**Project root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`
**Baseline commit:** `52833af`

## Objective

Ein portables, aus realen Softwarediagnosequellen abgeleitetes und mit synthetischen Messwerten pruefbares KNX026-Anzeige-/Navigationsmodell fuer T0..T8, Raum-/Heizkreiszuordnung, Regelung, angeforderte Stellwerte, Kommunikationsstatus und KNX025-Faults. Keine physische Bedien-/Motorfreigabe.

## In scope

- Hardware- und Quellinventur zu LCD/Encoder/BUTTON und fehlenden Treibern dokumentieren.
- Portable C++17-Anzeige-Snapshots direkt aus KNX025::Diagnostics und KNX023 RoomControlRuntime, Temperaturprotokoll T0..T8 mit expliziter Live-/Offline-Qualitaet.
- Virtuelle Position nur auf nativen Hosts und stets getrennt von unbekannter echter Motorposition ausweisen.
- Reines Anzeige-Menue mit virtuellen Encoder-Impulsen und Button ohne Aktuator-/Recovery-Aktion.
- Native Regressionstests, Arduino-hardlock-Kompiliertest, isolierter RP2040-Build wenn main veraendert wird, Scope-/ASH-Audit, Dokumentation.

## Out of scope

- LCD-Typ/Panel/I2C/SPI-Displaytreiber, tatsaechliche Encoder-ISR/GPIO- oder Taster-Bindung.
- Jede reale Motoransteuerung, All-off-Freigabe, Quittierung, automatische Fehlerruecksetzung, Referenzierung.
- KNX/IP-/ETS6-Produkt-/Bus-Integration, AppV3-Umstellung, Flash-/UPDI-Vorgaenge, Git-Push.
- Hardware- oder Stromversorgungs-Freigabe (KNX002-006, KNX018).

## Pre-existing / quarantined changes

- Keine: Git main clean, 32 lokale Commits vor origin/main, keine offenen Marker und keine Fremd-Write-Session bei Gate 1. History/Branches bleiben erhalten.

## Gate 1 - Checkup + Analysis

**Status:** accepted

- Agent 0.8.1 erreichbar; KNX025 Write-Session closed/completed, lesende Handover-Session closed.
- HEAD `52833af`, voriger KNX025-Implementierungscommit `335d7e4`, main CLEAN.
- `src/controller/config.hpp` deklariert nur HMI Button D2 / A D6 / B D7. In `src/` und `lib/` ist keine LCD-/Display-/Encoder-Runtime implementiert.
- RP2040 Hauptschleife hat KNX025 passive RAM-Beobachtung; kein aktueller ETS V3 Input, kein reales Motorbackend.
- `TemperatureBridge` bietet Snapshot/Online/Kanalgueltigkeit/Kanalalter/Fault, `Knx025::Diagnostics` Fault/Phase/Transport/Queue, `RoomControlRuntime::Pipeline` Zone/PI/Softwaretargets, native virtuelle Position.
- Echte Position, freigeschaltete H-Bruecke und sichere All-off-Quittung bleiben UNBEKANNT/nicht nachgewiesen. KNX-/Raumtransport darf ohne Monitor nicht als online etikettiert werden.

### Risiken und Entscheidung

T0..T8 sind Vorlauf/Ruecklauf, **keine** Raum-Istwerte. Alte/offline/unplausible Samples duerfen keine gueltige Temperatur simulieren. `DPT5.001` der vorgeschlagenen Raum-KOs nie mit produktivem `DPT5.004` verwechseln. Kein GPIO-/Bus-/Displaytreiber ohne gesicherte Hardware.

## Gate 2 - Decision / Plan

**Status:** accepted

- Header `lib/common/knx026_hmi_diagnostics.hpp`: fester RAM-Snapshot, explizite Quality-Stati, 9 Kanale/8 Zonen/8 Motoren, fault-first KNX025, read-only virtual UI.
- `src/controller/main.cpp`: nur passives Snapshot-Sampling im schon vorhandenen 100-ms-Softwareblock (kein neuer KNX/Pin/Timer/Bus/GPIO-Aufruf).
- Native Tests mit unbekannter/offline UART, falschen Sensor-Flags, Zeitueberlauf, mehreren Ventilen/Zonen, frischen/alten Raumwerten, virtual-only position, fault latch, read-only Navigation, Format und Arduino-Compile-Hardlock.
- Regression von KNX025 sowie aelteren Suites, Scope-Audit, isolierter PlatformIO Controller-Build; nur KNX026-Dateien und dokumentierte README/Roadmap/HISTORY-Aktualisierung committen.
- Gate 4: separater Implementierungscommit und separater ASH-Close-Commit, kein Push.

## Gate 3 - Implementation

**Status:** pending

### Progress

- [ ] Header und nativer HMI-Formatter/Navigation
- [ ] Passives Firmware-Sampling
- [ ] Native Tests, Audit und Doku

## Gate 4 - Validation + Close

**Status:** pending

### Required checks

- [ ] Native Tests und Regression
- [ ] Arduino-Hardlock und isolierter RP2040-Build
- [ ] produktive ETS-/PCB-/ATtiny-Quellen unveraendert
- [ ] ASH-/Link-Audit, Diff-Check, Umsetzung und Closing-Commit

## Next exact action

Implementiere das portable read-only KNX026-Modell und seine synthetischen Tests ohne Hardwarezugriffe.
