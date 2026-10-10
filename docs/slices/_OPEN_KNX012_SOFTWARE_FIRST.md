# Slice KNX012 - Software-first Firmwarearchitektur und Interface-Audit

**State:** open
**Gate:** 3/4
**Profile:** software + research
**Opened:** 2026-10-10
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX012-SoftwarePlan-20261010 / `ses-20261010T174312-b04b3fb8be83`
**Project root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`
**Baseline commit:** `4bffbcc`

## Objective

Die Prioritaet auf einen gefahrlosen KNX-Temperatur-MVP mit zwei separaten Firmwareprojekten verschieben: vorhandenen ATtiny-/RP2040-Code und PCB V1.2 auf Anschluss- und Protokollfehler pruefen, den seriellen Temperatur-Snapshot und KNX-Publikation spezifizieren und die Arbeit in kleine Software-Slices gliedern.

## In scope

- Verifizierter Pin-/Protokoll-Befund fuer ATtiny3216, RP2040, T0..T8, UART vs. SPI.
- Genau definierte neun Sensorrollen: T0 Vorlauf; T1..T8 Ruecklauf fuer M1..M8.
- Architektur, Mess-/Telegrammfrequenz, Fault/Stale-Verhalten, zwei Raum-Betriebsarten und hydraulische Grenzen.
- Software-first Roadmap/README und reproduzierbares, read-only Interface-Audit.
- Dokumentation und lokale Git-Commits nach ASH vier Gates.

## Out of scope

- Keine motorische Ansteuerung oder Hardware-Einspeisung; keine Aenderung an kanonischem Schaltplan/PCB.
- Noch keine Firmware-Pinfixes, Protokollimplementierung, XML/ETS6-Produktueberschreibung oder echte KNX-Telegramme.
- Keine Behauptung, dass die reale ATtiny-Bestueckung oder die OneWire-Sensorfamilie schon vermessen/identifiziert ist.
- Kein Remote-Push.

## Pre-existing / quarantined changes

- Vorheriger Git-Tree: clean; lokale Commits bis `4bffbcc` bleiben erhalten; `main` sechs Commits ahead origin.
- Keine vorhandenen `_OPEN_` Slice-Marker.

## Gate 1 - Checkup + Analysis

**Status:** accepted

- LLO Agent online, Root und ASH-Gitstatus verifiziert, keine aktive fremde Write-Session; vorheriges KNX001 geschlossen.
- `tools/audit_ash_workflow.py` 30/30 PASS, `tools/audit_design.py` 0 strukturelle Fehler.
- ATtiny Firmware initialisiert bereits neun `DallasTemperature`-/OneWire-Kanaele und SPI-Slave; RP2040 `main.cpp` implementiert derzeit nur KNX-Start.
- PCB U25 SOIC20 hat `T0` auf Pin 3/PA5 ... `T8` Pin 11/PB0; Pin 19/PA3 (SPI SCK) hat kein Netz. Vorhandene Firmware-Kommentare konfigurieren Sensorpins verschoben, `SPI_CS=PC2`, PCB PC2 ist `T_INT`.
- U25 PA1/PA2 (`T_RX`/`T_TX`) sind auf RP2040 GPIO9/GPIO8 verdrahtet; UART als bevorzugter PCB-V1.2 Transport. Dies ist noch kein erfolgreicher Laufzeittest.
- Baseline `Temperature::update()` fragt synchron ab; Ungueltig `0.0f`, `temperature>0`; SPI liefert ein einziges skaliertes Byte ohne Status/Alter.
- DS18B20 12-bit bis 750 ms (Hersteller); der genau verbaute Sensortyp ist noch nicht abgelesen.

## Gate 2 - Decision / Plan

**Status:** accepted (dokumentationsorientiert)

- **Zielbild:** ATtiny arbeitet mit nicht-blockierendem Mess-Zeitplan und atomarem Snapshot samt Status/Alter; RP2040 holt Snapshot per gerahmter UART-Anfrage und publiziert neun KNX-DPT9.001-Werte in konfigurierbarer Rate.
- **Zweiter Schritt:** erst nach Temperatur-KNX-MVP die parametrierbare Raumtemperatur-/Direkt-0..100%-Regelung und sicher sequenziellen Motortreiber.
- **Validation:** Read-only Test fuer Pin-/Signalvertrag plus ASH-/Hardware-Static-Audit, Markdown-Links, Git whitespace/check.
- **Folge-Slices:** KNX013 ATtiny sampler, KNX014 UART transport, KNX015 KNX Publish, KNX016 ETS Temperature MVP, danach KNX008/009/004/005/006/010 fuer Zonen/Antrieb.

## Gate 3 - Implementation

**Status:** complete

- [x] Firmware-Konzept schreiben und in README verlinken
- [x] Read-only Interface-/Pin-Audit mit nachpruefbaren Netzen
- [x] ROADMAP updaten und Software-first Reihenfolge explizit machen

## Gate 4 - Validation + Close

**Status:** pending; ATtiny Build Exit 0, ASH 30/30 PASS, PCB Static 0 FAIL, Interface-Audit mit 16 bewusst offenen Firmware-Punkten (strict Exit 2), 187 Markdown-Links PASS, Git diff --check PASS.

- [ ] Audits und lokale Links
- [ ] Git-Scope check und Commit
- [ ] HISTORY fortschreiben, ROADMAP-Status `closed` und Marker entfernen

## Next exact action

Implementation-Commit fuer KNX012 erstellen; danach Gate-4 History/Roadmap auf close setzen und den `_OPEN_KNX012_SOFTWARE_FIRST.md`-Marker im separaten Closing-Commit entfernen.
