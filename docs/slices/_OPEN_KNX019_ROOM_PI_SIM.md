# KNX019 – Software-only PI-Raumtemperaturregler für KNX010 vorbereiten

**Datum:** 2026-10-12
**Status:** OPEN, Gate 4/4 – Offline-Tests und Audits bestanden; Commits ausstehend
**Session/Owner:** ses-20261012T063501-41f9d1691ce4 / ChatGPT-OpenKNXValveControl-KNX019-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Git baseline:** 025c84e, clean main, 18 lokale Commits vor origin/main
**Profil:** Simulations- und Offline-C++-Software, **keine Firmware-/KNX-/ETS-Produktintegration**

## Gate 1 – Checkup

- [x] Desktop Agent erreichbar, vorheriger KNX008-Slice geschlossen, Checkpoint vorhanden; keine fremden aktiven Write-Sessions.
- [x] Git main clean, HEAD 025c84e; keine offenen ASH-Slice-Marker.
- [x] KNX008 stellt bereits 8-Zonen/8-Motoren-Zuordnung, Mode=RoomTemperature/DirectPercent und zeitgestempelte Inputs/RAM-Routing.
- [x] KNX010 (vollständige Raumregelung mit Motorfahrt, KNX Rx und ETS) hängt laut Roadmap von KNX006/007/009 ab; KNX009/016 auf Wunsch wegen fehlender separater Testumgebung KNX018 **deferred**.

## Gate 2 – Entscheidung und Grenzen

- Eigenständiger **KNX019-Vorbereitungsslice** als portable, KNX008-kompatible PI-Regelung im RAM; **KNX010 bleibt planned und seine Abhängigkeiten bleiben erhalten**.
- Pro Zone: externes KNX-Raum-Soll und -Ist, keine T0..T8 Heizkreis-Wassertemperaturen; Ziel 0..1000 Promille (0..100%). Der Reglerausgang darf nur in Mode=RoomTemperature in KNX008 eingehen.
- Soll-Algorithmus: langsamer PI mit Sättigung, Anti-Windup, Anti-Hunting-Slew-Limit, Deadband und begrenztem Sampling. Keine experimentell nicht bestätigte hydraulische Durchfluss-Kennlinie.
- Beim Wechsel Disabled/Direct/Room, Profiltuning, ungültigen/stale Inputs oder zu großem Loop-Gap ist der Reglerausgang zu invalidieren; **keine** alte Anforderung wiederverwenden; sauberes, neues Empfangsdaten-Gate zur Wiederaktivierung.
- Tests mit nativen Mock-Raumdaten und vereinfachter thermischer Pflanze, integriertem KNX008-Zonen-Router, Fehlerfällen und Zeitüberlauf.
- **Keine** Änderung von produktiver ETS XML, generiertem Header, RP2040/ATtiny-Firmware; keine reale KNX-Hardware oder ETS6-Importe, kein Motor-PWM, kein GitHub-Push.
- KNX004/005/006 Motor-Safety/Homing/Power-Gates bleiben offen. Die reine Regelung kann keine reale Bewegungs- oder Busausfallsicherheit belegen.

## Gate 3 – Implementation

- [x] Portable 8-Zonen-PI-Kern in lib/common/room_pi_controller.hpp und explizite Konfiguration/Status.
- [x] Simulations-/Integrationstests (KNX019 zu KNX008) für Begrenzungen, Sensorstörung, Recovery, Modiwechsel, millis-Overflow und langsamem Temperaturverlauf.
- [x] Technische Dokumentation mit Tuning-/Regelgates, README/Roadmap und Scope-Abgrenzung.

## Gate 4 – Validation und Abschluss

- [x] Native PI-/Regelungstests, KNX008 Router-Regression, KNX013–015 Regression PASS.
- [x] ETS V2 Produkt bleibt byte-identisch zur Baseline; KNX008 proposed-only ETS ABI bleibt intakt.
- [x] ASH 30/30, Markdown-Links, PCB-Static-Checks und Git staged diff check.
- [ ] Implementierungscommit, HISTORY/Roadmap-Closing-Commit mit Markerentfernung, Git clean.
- [ ] Session checkpoint+close; **nicht** automatisch KNX010/004/009/016 oder Hardwaretests starten.

## Next exact action

Eigene KNX019-Dateien explizit stagen, staged Git-Whitespace-Audit und QA wiederholen, Implementierungscommit, dann ASH-HISTORY/ROADMAP Closing-Commit, Markerentfernung, Git clean und Checkpoint. Keine Folge-Slices automatisch eröffnen.
