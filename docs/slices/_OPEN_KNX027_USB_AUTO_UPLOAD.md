# Slice KNX027 - RP2040 USB-Auto-Upload-Vorbereitung

**State:** open
**Gate:** 2/4 (Gate 1 Checkup + Gate 2 Entscheidung abgeschlossen)
**Profile:** software
**Opened:** 2026-10-12
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX027-USBFlash-20261012 / ses-20261012T141553-1dcb14ee98ad
**Project root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`
**Baseline commit:** `8ce8de2`

## Objective

Einen dokumentierten und hostseitig vorbereiteten, wiederholbaren RP2040-USB-Firmwareupload ohne routinemaessige BOOTSEL-Betaetigung schaffen, mit expliziter Port-Identifikation, sicherem Default und automatisierter Offline-QA. Noch kein reales Board flashen.

## In scope

- PlatformIO-`controller`-Uploadprotokoll `picotool` explizit konfigurieren; das vorhandene USB-CDC-`Serial.begin()` unveraendert belassen.
- USB-Port-Inventur, Plan/Dry-Run und explizit bestaetigter Auto-Upload via separatem CLI-Tool mit isolierter Build-Kopie gegen `knxprod.hpp`-Ueberschreiben.
- Sicherungsregeln: Port+VID:PID-Abgleich, eindeutiger existierender COM-Port, ausdrueckliche Ausfuehrungs-/Teststandfreigabe, kein Fallback auf andere COMs oder automatische Uploads.
- Unit-Tests/Mocks fuer Kommandos, absichtliche Sperren und Git-/Firmware-Audits; realer Firmware-Build nur in isoliertem temporarem Arbeitsverzeichnis.
- USB-Erstflash-/Recovery-Dokumentation, LLO-Laptop-Voraussetzungen und bestehende KNX018-Sicherheitsgrenzen in README/Roadmap.

## Out of scope

- Kein RP2040 angeschlossen oder im KNX018-Teststand nachgewiesen; kein realer Upload, BOOTSEL/Reset/Flash, USB-Debug/Log, KNX-/ETS-/Motorbetrieb.
- Keine Aenderung am Controller-Firmwaremotorpfad, ATtiny-UPDI, Stromversorgung, ETS XML/Produkt oder PCB.
- Kein GitHub-Push, Repo-Umzug oder Wiederverwendung alter Sessions.

## Pre-existing / quarantined changes

- Keine; live `git status --short --branch` main clean, HEAD `8ce8de2`, 34 lokale Commits vor `origin/main`, null offene Marker, letzte KNX026 Session CLOSED.

## Gate 1 - Checkup + Analysis

**Status:** accepted

- LLO Desktop Agent v0.8.1 online, PlatformIO Core v6.1.19, Python v3.13.15, Git clean.
- `src/controller/controller.ini`: Earle Philhower Arduino-Pico 5.5.0, RP2040 `board = rpipico`, `upload_protocol` bisher nicht explizit.
- `src/controller/main.cpp`: `Serial.begin(DefaultSerialBaud)` aktiviert USB-CDC; KNX `Serial1`, Temperaturlink `Serial2`.
- PlatformIO CLI `run --upload-port TEXT` vorhanden. `pio device list --json-output` zeigte **nur COM1 (ACPI) und COM3 (Intel AMT)**, kein per USB angeschlossener RP2040.
- Earle Arduino-Pico USB-CDC 1200-Baud-Reset und PlatformIO `picotool` sind laut Upstreamdokumentation verfuegbar; Erstflash ggf. BOOTSEL, Haenger via ROM-BOOTSEL/SWD.
- Der bestehende `tools/build_controller_isolated.py` umgeht Generatorueberschreibungen. Ein echter Upload ohne Teststand ist nicht erlaubt.

## Gate 2 - Decision / Plan

**Status:** accepted

- Explicit `upload_protocol = picotool` im Controller-Environment.
- Neues `tools/usb_flash_controller.py` fuer `probe`, `plan`, `upload`: nur letzter Befehl und nur mit `--execute`, `--confirm-safe-bench`, `--port COMx`, `--expect-vidpid XXXX:YYYY` darf I/O zum Ziel haben; niemals stilles Autodiscovery auf Fremdgeraeten.
- Vor echtem Upload builden wir eine isolierte Kopie, verifizieren `firmware.uf2` und `firmware.elf`, pruefen canonical `include/knxprod.hpp` auf Unveraenderlichkeit. `pio run -e controller -t upload --upload-port COMx` ausschliesslich im isolierten Build.
- Software tests mit simulierten USB-Port-Listen und Subprocess-Runner; offline `probe`, `plan`, isolierter Firmware-Build, ASH/Git-Audits.
- Die 16-MiB-`board_upload.maximum_size`-Annahme wird im Hardwaretest separat verifiziert; damit keine automatisch angenommene physische Flashfreigabe.

## Gate 3 - Implementation

**Status:** pending

## Gate 4 - Validation + Close

**Status:** pending

## Next exact action

Implementiere USB-Probe/Plan/Upload-CLI mit expliziter Sicherheitsfreigabe und isoliertem Build; teste negative Faelle ohne physisches USB-Geraet.
