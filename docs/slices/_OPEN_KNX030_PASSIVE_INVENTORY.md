# KNX030 - Passive Windows-Erstkontaktinventur (LLO Home)

**State:** open
**Gate:** 2/4 (Checkup and decision accepted)
**Profile:** software / offline testbench
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX030-Home-20261013 / `ses-20261013T110257-cb30d1888c61`
**Project root:** `C:\_myspace\workspace\open-knx-valve-control`
**Baseline HEAD:** `846bb93`
**Initial Git:** main CLEAN, 7 commits ahead of origin/main

## Objective

Use the unplugged interval to prepare repeatable, strictly read-only Windows enumeration of USB/COM candidates, RP2040 BOOTSEL drive labels and **local** network adapters on LLO Home, and a before/after snapshot comparison for the later KNX018 bench. The probe must not open a serial device, reset CDC baud, invoke UPDI tools, scan LAN, flash firmware or touch motor power.

## Gate 1: Checkup / analysis — accepted

- LLO Home Agent 0.7.9 online, no competing sessions and no open slices, HEAD `846bb93`, clean.
- KNX029 produced an offline, verified RP2040 UF2/ELF and configured ATtiny3216 HEX/ELF, but hardware not connected and all 8 hardware release gates false.
- Passive `Get-PnpDevice -PresentOnly`, `Get-NetAdapter` and `Get-Volume` were verified available on Home. Before-baseline probe counts included 15 present USB/port candidates and 0 RPI-RP2 volumes. Device names alone do not identify OpenKNX board.
- KNX018 needs first confirm physical U25 signature, UPDI CN1 pin1 voltage, USB/KNX backfeed and independent motor interlock before any programming, KNX telegrams or energizing a motor.

## Gate 2: decision / plan — accepted

- Add `tools/knx030_passive_inventory_probe.ps1`: local OS metadata only, no driver/device access or network transmissions.
- Add `tools/knx030_passive_inventory.py` supporting `plan`, `capture --output <NEW JSON> --label disconnected|connected`, and offline `compare --before ... --after ...`.
- Capture stores SHA256 of the original PnP instance ID, but **never the raw serial/instance ID**; keep VID:PID, COM, friendly name, status and local adapter status to compare physical arrival. No IP/MAC/address or port traffic.
- Host mock tests and source-scope audit verify unknown/empty/multiple devices, COM extraction, drive appearance, diff, tampering, offline no-subprocess compare, immutable KNX022/027/029 firmware/ETS/hardware files. Save a real baseline outside Git on LLO Home.
- A change, Raspberry VID:PID or RPI-RP2 label is **only a candidate**, not verified flash permission. KNX/IP not discovered: network adapter links are not KNX interfaces.
- Document workflow and update README/Roadmap/HISTORY, implementation commit + separate closing commit, no Git push.

## Explicit exclusions

No opening COM ports, pyserial serial reads, 1200-baud toggling, picotool, pymcuprog, KNX/IP multicast discovery, ETS6 writes, motor or GPIO activation, network probes, flash, UPDI or firmware changes. No hardware tests without assembled board and independent safety clearance.

## Gate 3

**Pending.** Implement passive collector, normalization/diff, tests, baseline and documentation.

## Gate 4

**Pending.** Run mocked tests, audited real baseline (USB not connected), existing ASH/KNX audits, stage and diff --check, commit and close.

## Gate 3 – Implementierung und Livebeleg

**Status:** complete

- [x] `tools/knx030_passive_inventory_probe.ps1` führt ausschließlich lokale `Get-PnpDevice -PresentOnly`, `Get-Volume` und `Get-NetAdapter` aus; UTF-8 für Windows Python-Subprozess erzwungen (CP1252-Decoding wurde im Erstversuch auf LLO Home reproduzierbar erkannt und behoben).
- [x] `tools/knx030_passive_inventory.py`: `plan` ohne Subprocess, `capture` nur in eine neue JSON-Datei außerhalb Repo, `compare` nur Dateianalyse. PnP-Instanz-ID in SHA256 gehasht, nur VID:PID, COM-Port, begrenzter Anzeigename und lokale Linkstatus. Kein MAC/IP, kein Netzwerk-Scan.
- [x] `tools/test_knx030_passive_inventory.py`: 11/11 gemockte Tests inklusive manipulierter Motorfreigabe, anderer Quelle, vorhandener Ausgabedatei, fehlerhafter Windows-JSON-Daten, neuer COM-/BOOTSEL-Kandidaten, keinem Subprozess bei `compare`.
- [x] Echter passiver LLO-Home-Basis-Snapshot unter `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-before-board-20261013.json`: **15 USB-/Port-Kandidaten, 0 RPI-RP2 Volumes, 21 lokale Netzwerkadapter**. Capture exit 0. Selbstvergleich offline: keine Änderungen, alle sieben Hardwarefreigaben false.
- [x] `tools/audit_knx030_passive_scope.py`: gefrorene Firmware-/ETS-/PCB-/KNX027/029-Quellen gegenüber `846bb93` unverändert; OS-Query ohne aktive Verbindung/Programmierung; PASS.
- [x] Runbook `docs/KNX030_PASSIVE_FIRST_CONTACT.md`, README, Roadmap, KNX018 und Home-Offline-Smoke-Tests aktualisiert.
- [x] Design-Audit weiterhin 0 Invariantfehler, Warnungen zu Hardware/ETS bleiben.

## Gate 4 – Validation / Close

**Status:** pending

- [ ] Aktualisiertes Home-Offline-Testskript + ASH-Audit PASS
- [ ] Git staged diff --check, Implementierungscommit und separater HISTORY-Close-Commit
- [ ] Abschluss mit sauberem main, keiner offenen Marker-Datei, ohne Push

## Next exact action

Run end-to-end Home offline smoke/audits. Commit reviewed KNX030 files, then append HISTORY and delete _OPEN marker in separate local closing commit. No power or hardware operations.
