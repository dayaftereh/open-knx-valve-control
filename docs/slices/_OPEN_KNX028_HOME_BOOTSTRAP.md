# KNX028 – LLO Home Offline-Initialisierung

**State:** open
**Gate:** 2/4 (Gate 1+2 verified)
**Profile:** software/infrastructure
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX028-HomeInit-20261013 / `ses-20261013T091101-f5813049ea1d`
**Project root:** `C:\_myspace\workspace\open-knx-valve-control`
**Baseline commit:** `14795c6c7af6808bcff210d3a98bce814bac7461`

## Objective

LLO Home zum primaeren OpenKNXValveControl-Entwicklungsrechner machen und Git, Python, PlatformIO, gepinnte RP2040/ATtiny-Abhaengigkeiten und OpenKNXproducer fuer **Offline-Builds und Mock-Tests** initialisieren; alle Nachweise dokumentieren, ohne fertige oder angeschlossene Platine vorauszusetzen.

## In scope

- Host-/Rechte-/Git-/Toolchain-Pruefung mit reproduzierbarem Home-Bootstrap.
- Nach Moeglichkeit die vorhandene PlatformIO-Installation des Windows-Benutzers `ll` nutzen, nicht ungefragt global installieren.
- Projektkompatiblen OpenKNXproducer 3.12.2 mit gepruefter Release-Herkunft bereitstellen, sofern Download moeglich.
- RP2040- und ATtiny-Builds **nur im isolierten temporaeren Workspace**, niemals Firmware laden oder produktive KNX-Produkte/Header ueberschreiben.
- Native Softwaretests, USB-Upload-Mocktests und statische ASH-/Design-Audits ausfuehren, externe/fehlende Abhaengigkeiten ehrlich kennzeichnen.
- Home-Onboarding/Umgebungsdiagnostik dokumentieren und in Git lokal committen.

## Out of scope

- USB/UPDI-Flash, ROM BOOTSEL oder 1200-Baud-Reset, physische USB-/COM-Probe die Geraete veraendert, PIN-/Motor-/KNX-/ETS-IO.
- Aenderungen an ETS XML, knxprod.hpp, PCB und Leistungs-/Motor-Firmware.
- Behauptung einer elektrisch sicheren V1.2-Platine oder Freigabe des Aufbaus.
- Push, Force-Push, Loeschen fremder Dateien, ungepruefte globale Git-/OS-Konfigurationsaenderungen.

## Pre-existing / quarantined changes

- Keine: Home main CLEAN und synchron zu origin/main, HEAD `14795c6`; keine offenen Slice-Marker und keine fremde aktive Session.
- Bekannte Git-SYSTEM-vs.-`ll`-Eigentuemerabweichung: nur pro Prozess `safe.directory`, keine globale Git-Konfiguration.
- Nur Benutzer `ll` hat PlatformIO 6.1.18/Python 3.11.7; auf Home fehlen Raspberry-Pi-Plattform und OpenKNXproducer.exe. Kein RP2040 verbunden.

## Gate 1 – Checkup + Analysis

**Status:** accepted

- Home Agent 0.7.9 reachable, Projekt unter `C:\_myspace\workspace\open-knx-valve-control`.
- Python + PlatformIO im Benutzerprofil `C:\Users\ll\.platformio\penv\Scripts\` vorhanden; Arduino-Pico/RP2040 Plattformpakete fehlen.
- `OpenKNXproducer.exe` nicht in HOME Tool-Verzeichnis gefunden; offizielle OpenKNX GitHub v3.12.2 Release vorhanden, separates ZIP.
- Fuer PIO/Python und Git Jobs Pfade/Umgebung explizit setzen, keine Hardwaretransaktionen.

## Gate 2 – Decision/Plan

**Status:** accepted

- Originale Hersteller-/OpenKNX-Toolchain-Versionen beibehalten; keine stillen Updates zu neueren nicht validierten Major-Versionen.
- Tooling nur in bewusst dokumentierten lokalen Pfaden des Home Hosts, isolierte Builds.
- Sicherheitsgrenze: echte Hardware voraussetzungslos **nicht** testen, selbst bei vorhandenem COM-Port.
- Tests/Builds/Audits und QA-Log; Zustand PASS/PARTIAL/BLOCKED jeweils nach Live-Ergebnis.

## Gate 3 – Implementation

**Status:** pending

- [ ] Python/Pio Toolchain Probe und Build-Dependencies
- [ ] Gepinnter OpenKNXproducer bereitstellen
- [ ] Native Tests, RP2040/ATtiny Builds soweit moeglich
- [ ] Home Runtime Runbook + README/Roadmap

## Gate 4 – Validation/Commit/Close

**Status:** pending

- [ ] Host-Builds/tests + ASH-Audit
- [ ] Git Scope-Diff / clean / separate Closing-Commit
- [ ] Hardware-Gates als offen dokumentiert

## Next exact action

Host-Python/PlatformIO und gepinnte Tools pruefen, OpenKNXproducer aus verifiziertem Release installieren soweit erreichbar und reproduzierbare Offline-Builds / Tests ausfuehren.

## Gate 3 – Live implementation status 13.10.2026

- [x] Home Python 3.11.7 / PlatformIO 6.1.18 found under `C:\Users\ll\.platformio\penv\Scripts`; setting `PLATFORMIO_CORE_DIR=C:\Users\ll\.platformio`.
- [x] RP2040 platform, Arduino-Pico 5.5.0, picotool, GNU Arm toolchain, OpenKNX knx/TPUart dependencies installed.
- [x] OpenKNXproducer 3.12.2 ZIP downloaded, x64 binary inside `tools/Windows/OpenKNXproducer-x64.exe` runs and generates the temporary V2 35-KO header/knxprod.
- [x] ATtiny3216 in isolated temp directory built PASS, job-000032; no upload.
- [x] Native KNX027 mock USB tests 8/8 PASS; ASH 30 checks and 472 links PASS; design audit 0 structural failures.
- [x] Reusable `tools/home_offline_check.ps1` and `docs/KNX028_LLO_HOME_SETUP.md`, README and Roadmap.
- [ ] RP2040 build **BLOCKED:** `framework-arduinopico 5.5.0` `malloc-lock.cpp:122` compiler error `__getreent was not declared` with Home currently resolved toolchain (see `docs/KNX028_LLO_HOME_SETUP.md`, job-000035).
- [ ] Native C++ suite requires a Home `g++` binary; not present.

## Gate 4 – Current validation

**Status:** blocked (do not close the slice as complete). Original `src/`, `assets/`, ETS XML, knxprod.hpp, and schematics unchanged. Need Home RP2040/host C++ build regression before a full Gate4 close. No push, no USB/UPDI, no KNX/motor/ETS.

## Next exact action

Compare compiler/PlatformIO Raspberry Pi framework/toolchain package versions and compile flags between the previously passing LLO Desktop isolated controller build and LLO Home's failing `__getreent` framework build; repair using a reviewed/pinned external toolchain, then re-run isolated controller build and host tests. Keep this same KNX028 slice open.
