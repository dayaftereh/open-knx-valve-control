# KNX017 – Testumgebung zurückstellen und Software-Reihenfolge festlegen

**Datum:** 2026-10-12
**Status:** OPEN, Gate 4/4 – Planung dokumentiert und auditiert; Commits ausstehend
**Session:** ses-20261012T060449-cc55237faae8
**Owner:** ChatGPT-OpenKNXValveControl-Planning-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** `8b404a3`, `main`, clean, 14 Commits vor `origin/main`

## Gate 1 – Checkup

- [x] LLO Desktop Agent erreichbar, Repository und Sessionstatus live geprüft.
- [x] Git clean, kein offener `_OPEN_`-Marker, vorherige KNX015-Session geschlossen.
- [x] KNX015 Software-/Produktgenerator-Gates abgeschlossen, physischer ETS6-/KNX-/UART-/Platinentest ausdrücklich nicht nachgewiesen.

## Gate 2 – Entscheidung

- [x] Nutzerwunsch: KNX-/ETS6-Integrationstest vorerst **zurückstellen**.
- [x] Nicht auf dem Desktop Agent final testen, sondern später eine **eigenständige KNX-Testumgebung mit angeschlossener KNX-Schnittstelle und echter Platine** aufbauen.
- [x] KNX016 bleibt als *deferred* in der Roadmap ohne gestarteten Implementierungsslice. KNX018 als geplanter Testbench-Aufbau; spätere ETS6-/Busabnahme benötigt die entsprechende Infrastruktur.
- [x] Nächster empfohlener, eigenständig möglicher Slice: **KNX008 ETS-Zonen-/Heizkreis-/Regelmoduskonzept** (ohne ETS6-Import, Telegrammversand, Hardwarebewegung und Stromversorgungseingriff).

## Gate 3 – Dokumentation

- [x] Eigenständige Testbench-Anforderungen mit Voraussetzungen und Abnahmetests dokumentieren.
- [x] KNX016 deferred und Testbench KNX018, Reihenfolge/Abhängigkeiten in Roadmap dokumentieren.
- [x] README mit Verweis und zurückgestelltem Gate aktualisieren.

## Gate 4 – QA und Abschluss

- [x] Markdown-Links/ASH-Audit und `git diff --check` bestehen.
- [ ] Implementation Commit nur für Planungs-/Dokumentationsdateien.
- [ ] Abschluss in HISTORY, Marker entfernen, Roadmap schließen und separater Closing Commit.
- [ ] Git clean, Checkpoint, Session schließen. Kein Push, kein ETS6-/Bustest, kein Motorbetrieb.

## Next exact action

Nur die vier selbst angelegten/geänderten Dokumentationsdateien stage/committen, anschließend HISTORY/Roadmap schließen, Marker in separatem Commit entfernen und Session-Checkpoint sichern. **KNX008 nicht automatisch eröffnen.**
