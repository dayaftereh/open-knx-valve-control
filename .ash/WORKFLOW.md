# ASH Workflow fuer OpenKNXValveControl

**Protocol:** [ASH Project Workflow v1](../docs/reference/ash/README_PROJECT_WORKFLOW.md)

**Project root:** `C:\ASH\Workspace\Projects\open-knx-valve-control`

**Git:** `main`, origin `https://github.com/dayaftereh/open-knx-valve-control.git`

**Profil:** `software`, erweitert um Elektronik-/EasyEDA-, ETS6- und `research`-Pruefungen. Eine pauschale KiCad-DRC-Bestaetigung waere fuer die hier hinterlegten EasyEDA-JSONs unzutreffend.

## Verbindliches Arbeitsmodell

- **Project**: Repository und permanente Spezifikationen/Artefakte; **Slice**: ein pruefbares, abgeschliessbares Arbeitspaket; **Session**: ersetzbare Agent-/Chat-Arbeitsinstanz.
- Standardmaessig **genau ein aktiver Write-Slice**. Die LLO-Desktop-Session-Sperre ersetzt nicht den offenen repo-sichtbaren Slice-Marker.
- Bei einer neuen Session stets zuerst Root, Agent-/Session-Eigner, laufende Jobs/Checkpoint, `git status --short --branch`, `docs/slices/_OPEN_*.md` und relevante Fachdokumente verifizieren.
- Existiert ein offener Slice, **denselben** ab dessen `Next exact action` weiterbearbeiten; nicht parallel einfach einen neuen Slice eroeffnen.
- Ein neuer Slice bekommt Baseline-Commit, Scope, Out-of-Scope, Quarantaene bereits vorhandener Aenderungen, vier Gates und einen exakten naechsten Schritt.
- Fremde und vorbestehende Dirty-Tree-Aenderungen weder resetten/loeschen noch ohne explizite Ownership stagen oder committen.
- **Gates:** 1 Checkup + Analysis -> 2 Decision/Plan -> 3 Implementation -> 4 Validation/Commit/Close. Scope-Drift erfordert erneut Gate 2.
- Bei Gate 4 QA-Evidenz, Checkpoint, geaenderte Artefakte und Follow-ups dokumentieren, `docs/slices/HISTORY.md` aktualisieren und offenen Marker im Closing-Commit entfernen.
- Der naechste geplante Slice wird **nicht automatisch** geoeffnet. Eine geschlossene Session hebt kein offenes Slice auf.
- **Nur der verifizierte Projekt-/Git-/Runtime-Zustand ist massgeblich**, nicht einzelne Behauptungen aus alten Chats.

Details: [zentrales Slice-Protokoll](../docs/reference/ash/SLICE_PROTOCOL.md), [Projektprotokoll](../docs/reference/ash/PROJECT_PROTOCOL.md), [Recovery/Handoff](../docs/reference/ash/RECOVERY_HANDOFF.md), [Slice-Vorlage](../docs/reference/ash/SLICE_TEMPLATE.md).

## Projektspezifische Validierung

**Software/ETS** (nur wenn im Slice-Scope):
- `python tools/audit_design.py` und `python tools/audit_ash_workflow.py`, Git diff/status/check, passende PlatformIO-Builds und statische Analysen.
- OpenKNXproducer XML-/Header-Konsistenz, generator-sichere KO-Namen, versionierter `.knxprod`-Build und isolierter ETS6-Import-/Telegrammtest. **Generatorerfolg ist noch kein ETS-Importbeweis**.
- Firmware-/Hardware-Grenzen vor Motorbewegung zwingend in [ARCHITECTURE.md](../docs/ARCHITECTURE.md), [ETS-Konzept](../docs/ETS_AND_CONTROL_CONCEPT.md) und [ETS-Produkt-Audit](../docs/ETS_PRODUCT_AUDIT.md) beachten.

**Elektronik/EasyEDA** (wenn im Scope):
- Schaltplan V1.2, PCB V1.2, Bauteile, Pins/Netze, Layout und echte Bestueckung getrennt betrachten.
- Autoritativer DRC/ERC-/Netlist-Export muss aus dem tatsaechlich genutzten EDA-System kommen. `tools/audit_design.py` ist nur ein **statischer Invariantentest**, kein echter DRC.
- Die Hardware prueft aktuell nur **einen Motor gleichzeitig** (vier TB6612FNG, gemeinsame Richtungsnetze `IN_1/IN_2`, einziger INA219/R29-Shunt).
- Vor motorischen Tests: R29-Bestueckung, U25-Identitaet, sichere Abschaltung bei Reset/Brownout, isolierte Versorgung und 3,3-V-Motorrail verifizieren.
- 5 V externe Versorgung ist bislang nur **Konzept**; keine 5 V auf `M_VCC`, keine unkontrollierte Parallel- oder Rueckspeisung Richtung KNX/USB; [POWER_SUPPLY_CONCEPT.md](../docs/POWER_SUPPLY_CONCEPT.md).
- Antrieb HmIP-VDMOT: 3,3 V, Herstellermaximum 120 mA **nicht** gleich freigegebener Endanschlag-Schwelle; Stromprofil und Laufzeit real messen.

**Research/Design**:
- Herstellerangaben, vermessene Hardware, statische Dateibefunde, Annahmen und noch offene Hypothesen explizit unterscheiden.
- Mess- und Quellenprovenienz sowie Dateirevisionen/Hashes dokumentieren, wenn sie eine Entscheidung begruenden.

## Lokale Dokumentation und Navigation

- [ROADMAP](../docs/ROADMAP.md): **geplante**, nicht gestartete Slices, Reihenfolge und Abnahmekriterien.
- [Slices-Index](../docs/slices/README.md), [HISTORY](../docs/slices/HISTORY.md), jeweils aktueller `docs/slices/_OPEN_*.md` (nur bei laufendem Slice).
- [ASH-Quellkopien und Provenienz](../docs/reference/ash/README.md).
- [README](../README.md): Projekt-Einstieg; spezifische Hardware- und ETS-Informationen bleiben in den bestehenden `docs/*.md`.

## Git- und Release-Regeln

- Nur dem Slice gehoerende Dateien stagen; `git diff --check`/Diff lesen und reproduzierbare Checks ausfuehren.
- Eine Releasefreigabe verlangt zusaetzliche Profil-/Hardwarepruefungen. Ein Dokumentations-Slice ist kein PCB-/Firmware-Release.
- Local Git commit und remote Git push sind **unterschiedliche** Aktionen. Kein Push ohne expliziten Auftrag bzw. passende Projektfreigabe.
- Fuer Handoffs immer Current gate, Progress, Changed files, Validation, Blockers, `Next exact action`, relevanten Commit und Session-Checkpoint materialisieren.
