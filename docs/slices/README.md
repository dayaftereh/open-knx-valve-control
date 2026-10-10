# Slice-Verwaltung - OpenKNXValveControl

**Protokoll:** [ASH Project Workflow v1](../reference/ash/README_PROJECT_WORKFLOW.md) und [ASH Slice Protocol v1](../reference/ash/SLICE_PROTOCOL.md).

**Projektprofil:** `software` mit [lokalen Elektronik-/EasyEDA- und ETS6-Gates](../../.ash/WORKFLOW.md).

**Roadmap:** [`docs/ROADMAP.md`](../ROADMAP.md).

**Abgeschlossene Slices:** [`HISTORY.md`](HISTORY.md).

## Grundbegriffe

- **Project**: Repo und permanente technische Entscheidungen.
- **Slice**: ein eindeutig abgrenzbares, pruefbares Arbeitspaket, das ueber Chats/Sessions weiterlaufen darf.
- **Session**: austauschbare technische Agent- oder Chat-Sitzung, mit eigenem Write-Lock und Checkpoints.

**Maximal ein aktiver Write-Slice** fuer dieses Repository. Der offene Slice ist stets unter `docs/slices/_OPEN_<ID>_<SLUG>.md` sichtbar. Kein Marker bedeutet, dass kein Write-Slice offen ist. Ein geplanter Roadmap-Eintrag ist **noch kein aktiver Slice**.

## Vier Gates (verbindlich)

1. **Checkup / Analysis:** Root, Session/Owner, `git status`, bereits offene Marker, Baseline und fachlichen Ist-Zustand verifizieren. Fremde Dirty-Tree-Aenderungen quarantainieren; noch nicht implementieren.
2. **Decision / Plan:** Ziel, Scope, explizit Out-of-Scope, Abhaengigkeiten, Implementationsentscheidung und Gate-4-Abnahmen festlegen. Keine stillen Erweiterungen.
3. **Implementation:** nur geplante Teilaufgaben; Artefakte und Checkpoints ins Repo uebernehmen; Scope-Aenderungen zurueck nach Gate 2.
4. **Validation / Commit / Close:** profilgerechte Tests und QA dokumentieren, Scope diff pruefen, `HISTORY.md` ergaenzen, Closing-Commit erstellen und `_OPEN_...` Marker entfernen.

Slice-Zustaende: `open`, `blocked`, `ready-for-validation`, `closed`. Blockierte Slices bleiben als `_OPEN_...` sichtbar und erhalten einen konkreten Blocker und `Next exact action`.

## Standard-Wiederaufnahme

1. LLO Desktop Agent, Projektroot `C:\ASH\Workspace\Projects\open-knx-valve-control` und Sessionliste/Ownership pruefen. Fremde aktive Write-Session **nicht uebernehmen**.
2. `git status --short --branch`, Git HEAD, Checkpoint und bereits vorhandene Dirty-Tree-Dateien lesen; fremde Dateien weder verwerfen noch stagen.
3. `docs/slices/_OPEN_*.md` suchen und gegebenenfalls vollstaendig lesen.
4. Bei vorhandenem offenem Slice **diesen** fortsetzen und `Next exact action` befolgen; keine parallele Neuanlage.
5. Nur ohne offenen Slice, nach Abgleich mit [Roadmap](../ROADMAP.md), eine frische Write-Session und einen begrenzten neuen Slice oeffnen.
6. Bei Agent-/Job-Abbruch erst Output, Teil-Artefakte und laufende Jobs verifizieren. Gleiche Mutation nicht blind erneut ausfuehren.

Ausfuehrlicher Ablauf: [RECOVERY_HANDOFF.md](../reference/ash/RECOVERY_HANDOFF.md).

## Einen neuen Slice beginnen

- Nächste ID aus der [Roadmap](../ROADMAP.md) bestimmen, solange kein anderer offen ist.
- [ASH-Vorlage](../reference/ash/SLICE_TEMPLATE.md) als `_OPEN_KNX###_<SLUG>.md` verwenden.
- Baseline SHA, Eröffnungsdatum, Owner/Session, Profil, Scope/Out-of-Scope, vorhandene Aenderungen, Gate 1 und **Next exact action** eintragen.
- Fuer Elektronik/KNX nur die zugehoerigen Mess-, ERC-/DRC-, Strom-, KNX-/ETS- und Sicherheitstests als PASSED kennzeichnen, die tatsaechlich durchgefuehrt wurden. Ein statischer Export-Check ist kein Hardwaretest.
- Bei Handoff: aktuelles Gate, Fortschritt, geaenderte Dateien, QA-Paesse/Fehler, Blocker, Next exact action und Session-Checkpoint materialisieren.

## Schliessen

- Ergebnis und Profiltests dokumentieren; `python tools/audit_ash_workflow.py`, `python tools/audit_design.py`, `git diff --check` und nur Slice-spezifischen Scope pruefen (zusaetzliche fachliche Tests je Slice).
- Permanente Aenderungen in Fachdokumentation ablegen; offenen Marker nicht als einziges Wissensartefakt verwenden.
- `HISTORY.md` mit Ergebnis, Referenzcommit(s), Evidenz und Follow-ups ergaenzen.
- `_OPEN_...`-Marker **im Closing-Commit entfernen**; naechsten geplanten Slice **nicht automatisch** starten.
- Push und Release sind **separate** Aktionen.

## Fachliche Grenzen dieses Repositories

- Schaltplan/PCB V1.2, RP2040, ATtiny, ETS6-Produktdaten und HmIP-VDMOT sind verschiedene Teilbereiche; nur innerhalb des definierten Slice-Scope mutieren.
- Ein Motor zurzeit, INA219 mit einzigem R29-Shunt; 120 mA ist Herstellermaximum, **keine** bewiesene Endanschlag-Schwelle.
- KNX-/USB-/externe 5-V-Power-Architektur ist noch nicht mit Hardwaremessungen freigegeben.
- Ausgangspunkt und offene technische Punkte stehen in [ARCHITECTURE.md](../ARCHITECTURE.md), [PCB-Audit](../PCB_V1_2_AUDIT.md), [ETS-Audit](../ETS_PRODUCT_AUDIT.md) und [Power-Konzept](../POWER_SUPPLY_CONCEPT.md).

**ASH-Kernquellen:** [PROJECT_PROTOCOL](../reference/ash/PROJECT_PROTOCOL.md), [PROJECT_PROFILES](../reference/ash/PROJECT_PROFILES.md), [SLICE_PROTOCOL](../reference/ash/SLICE_PROTOCOL.md), [SLICE_TEMPLATE](../reference/ash/SLICE_TEMPLATE.md), [RECOVERY_HANDOFF](../reference/ash/RECOVERY_HANDOFF.md) und [EXAMPLES](../reference/ash/EXAMPLES.md).
