# Slice KNX001 - ASH Project Workflow v1 Bootstrap

**State:** ready-for-validation

**Gate:** 4/4

**Profile:** software (Elektronik/EasyEDA und Research als lokale Erweiterungen)

**Opened:** 2026-10-10

**Owner/Session:** ses-20261010T081749-6781943fd6b1

**Project root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`

**Baseline commit:** `c2e4bee`

## Objective

ASH Project Workflow v1 aus dem ChatGPT-Space `/ASH` fuer OpenKNXValveControl unveraendert referenzierbar lokal ablegen, die Regeln aktivieren, Roadmap und Slice-Historie einrichten und die README verankern.

## In scope

- Sieben Workflow-Quellen aus `/ASH` als Repositoriumsreferenzen materialisieren.
- `.ash/project.yaml`, `.ash/WORKFLOW.md`, `docs/slices/README.md`, `docs/slices/HISTORY.md`, `docs/ROADMAP.md` und zentrale README aktualisieren.
- Dokumentierte bisherige Hardware-, Versorgungs-, ETS- und Firmware-Risiken in geordnete Zukunfts-Slices uebertragen (nur planen).
- Statische Dokumentations-/Repositorypruefung und sauberer Closing-Commit.

## Out of scope

- Keine Aenderung an PCB V1.2, Schaltplan, Firmwares, ETS XML, `.knxprod`, bestueckter Platine oder Netzversorgung.
- Kein automatisch gestarteter Folgeslice, keine Hardwarebeaufschlagung, kein Git-Push ohne Auftrag.
- Corporate-Design-Dateien/Logos im ASH-Space sind keine Slice-Workflow-Quellen und werden hier nicht eingefuehrt.

## Pre-existing / quarantined changes

- `none`; `git status --short --branch` vor Slice: `## main...origin/main [ahead 4]`; Tree clean.
- Vier bestehende, nicht gepushte Commits (`53b308a`, `4fa28c1`, `0045a45`, `c2e4bee`) sind bestehende Projektgeschichte und kein Teil von KNX001.

## Gate 1 - Checkup + Analysis

**Status:** PASS

- LLO Desktop Agent erreichbar; `C:\ASH\Workspace\Projects\open-knx-valve-control` verifiziert.
- Keine aktiven fremden Write-Sessions; bisherige Sessions abgeschlossen, neu eroeffnete Write-Session KNX001.
- Es gab keine `_OPEN_*.md`-Marker, keine `.ash`-Konfiguration, keine Slice-Historie.
- Die Originalquelle `/ASH` in der ChatGPT Library enthaelt sieben Workflow-MD-Dateien v1, plus Corporate-Design-/Logo-Dateien ohne Slice-Bezug.
- Bisheriger technischer Stand ist bereits in README und sieben Fachdokumenten sowie vier lokalen Commits materialisiert.
- Risiko: Slice-Historie darf vorherige Arbeit nicht rueckwirkend als abgeschlossene Slices deklarieren; bestehende technische Tests duerfen nicht durch Dokumentationscheck als PASS gelten.

## Gate 2 - Decision / Plan

**Status:** PASS

- Als Projektprofil `software`, erweitert um hardwarebezogene EasyEDA-/Schaltplan-/PCB-Pruefungen und `research`-Provenienz, anlegen. `kicad`-Checks nicht unbesehen auf EasyEDA anwenden.
- Genau ein aktiver Write-Slice; jeweils `docs/slices/_OPEN_<ID>_<SLUG>.md`, vier Gates, Baseline, Quarantaene, `Next exact action`.
- Permanente Ergebnisse in Fachdokus und `docs/slices/HISTORY.md` archivieren, Marker im Closing-Commit entfernen.
- ASH-Originalquellen unter `docs/reference/ash/` als Schnappschuss, einschliesslich Quelle/Datum dokumentieren; zentrale Library bleibt Normquelle, Projektdateien bleiben Source of Truth fuer den Projektzustand.
- `docs/ROADMAP.md` mit KNX002+ als **planned**, unabhaengig von diesem Bootstrap; keine vorschnellen Implementierungen.
- Validieren: sieben Quellen vorhanden, 0 offene Marker nach Close, Links intakt, Python-Design-Audit weiterhin PASS, YAML plausibel, Git diff --check, Scope und Commit sauber.

## Gate 3 - Implementation

**Status:** PASS

### Progress

- [x] Sieben Originaldokumente uebertragen (Dateigroessen, SHA-256-Manifest pruefbar)
- [x] ASH-Projektdokumente und Roadmap erstellt (KNX001..KNX011)
- [x] README-Index und lokales Slice-Protokoll erstellt; Audit-Skript `tools/audit_ash_workflow.py` eingebunden

### Changed files / artifacts

- `docs/reference/ash/*.md` (sieben Originaltexte plus Herkunftsindex)
- `.ash/project.yaml`, `.ash/WORKFLOW.md`
- `docs/slices/README.md`, `docs/slices/HISTORY.md`, `docs/ROADMAP.md`, `README.md`

## Gate 4 - Validation + Close

**Status:** QA PASS; Implementation- und Closing-Commit noch ausstehend

### Required checks

- [x] ASH-Quellenvollstaendigkeit (7/7) und Inhaltsintegritaet (MANIFEST.sha256 mit 7/7 PASS)
- [x] Interne README-/Dokumentationslinks (160 PASS / 0 broken)
- [x] `python tools/audit_design.py` (0 Invariant-Fehler; bestehende Hardwarewarnungen unveraendert)
- [x] `git diff --cached --check` PASS (nach Erhalt originaler ASH-Hardbreaks ueber .gitattributes); nur Scope KNX001
- [ ] Projekthistorie dokumentiert, Closing-Commit eindeutig
- [ ] `_OPEN_KNX001_ASH_WORKFLOW_BOOTSTRAP.md` im Closing-Commit entfernt

## Next exact action

Den KNX001-Implementierungscommit erstellen; dessen SHA in `docs/slices/HISTORY.md` referenzieren, `docs/ROADMAP.md` auf closed setzen, `_OPEN_KNX001_ASH_WORKFLOW_BOOTSTRAP.md` im Closing-Commit entfernen und alle Checks nochmals pruefen.
