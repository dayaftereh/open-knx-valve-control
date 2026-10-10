# ASH Project Workflow v1

**Version:** 1.0  
**Stand:** 2026-08-29  
**Zweck:** Einheitlicher, recovery-sicherer Projekt- und Slice-Workflow fuer ASH-Projekte in Software, Elektronik, CAD, Research und Infrastruktur.

## Ziel

Dieses Paket definiert einen generischen Arbeitsstandard, der aus dem bewaehrten MOOX-Slice-Konzept abgeleitet wurde. Er soll lange oder unterbrochene Chat-/Agent-Arbeiten ueber mehrere Sessions hinweg eindeutig fortsetzbar machen und parallele Arbeiten besser absichern.

Der Standard trennt drei Ebenen bewusst voneinander:

1. **Project** - dauerhaftes Repository bzw. Arbeitsprojekt und seine Regeln.
2. **Slice** - eine klar begrenzte, versionierbare Arbeitseinheit innerhalb des Projekts.
3. **Session** - die aktuelle technische Arbeitsinstanz bzw. der Chat/Agent, der gerade an einem Slice arbeitet.

Kurzform:

> **Session = Wer arbeitet gerade?**  
> **Slice = Woran wird gearbeitet?**  
> **Project = Wo gelten die Regeln dauerhaft?**

Ein Slice darf mehrere Sessions ueberleben. Eine Session darf beendet oder ersetzt werden, ohne dass der Projektfortschritt verloren geht.

## Source of Truth

Die zentrale ASH Library enthaelt die generische Spezifikation und Templates. Der konkrete Projektzustand gehoert immer in das jeweilige Projekt-Repository.

Empfohlene Prioritaet:

1. Projektlokale `.ash/project.yaml` bzw. projektlokale Workflow-Regeln.
2. Projektlokaler aktiver Slice-Marker und permanente Projektdokumentation.
3. Diese zentrale ASH Project Workflow Spezifikation.
4. Chat-Kontext und temporaere Session-Informationen.

Ein Chat ist daher niemals alleinige Source of Truth fuer laufende Projektarbeit.

## Kernregeln

- Pro Projekt standardmaessig genau **ein aktiver Write-Slice**.
- Vor Veraenderungen immer Git-/Projektzustand und vorhandene offene Slices pruefen.
- Unbekannte oder bereits vorhandene Aenderungen niemals ungefragt verwerfen oder in den eigenen Scope ziehen.
- Ein Slice durchlaeuft vier Gates: **Checkup -> Decision -> Implementation -> Validation/Close**.
- Der aktive Slice wird repository-sichtbar markiert.
- Langfristige Ergebnisse, Architekturentscheidungen und Nachweise landen in permanenten Dokumenten, nicht nur im offenen Marker.
- Nach Unterbrechung wird immer zuerst ein vorhandener offener Slice wieder aufgenommen.
- Ein Slice wird erst geschlossen, wenn Ergebnis, QA, offene Punkte und Commit-/Checkpoint-Zustand dokumentiert sind.

## Empfohlene Projektstruktur

```text
<Project>/
|-- .ash/
|   |-- project.yaml
|   `-- WORKFLOW.md              # optional: projektspezifische Abweichungen
|-- docs/
|   `-- slices/
|       |-- README.md
|       |-- HISTORY.md
|       `-- _OPEN_<ID>_<SLUG>.md
|-- README.md
`-- ...
```

Bei kleinen Projekten kann `.ash/WORKFLOW.md` entfallen. Die zentrale Spezifikation bleibt dann Referenz; der aktive Slice und seine Historie muessen trotzdem im Projekt selbst liegen.

## Dokumente in diesem Paket

- `SLICE_PROTOCOL.md` - verbindliches generisches Vier-Gate-Protokoll.
- `SLICE_TEMPLATE.md` - Vorlage fuer einen aktiven `_OPEN_...`-Slice.
- `PROJECT_PROTOCOL.md` - Regeln fuer Projektinitialisierung, Source of Truth, Baseline und Dirty-Tree-Quarantaene.
- `PROJECT_PROFILES.md` - profilabhaengige Checks fuer Software, KiCad, CAD, Research und Infrastruktur.
- `RECOVERY_HANDOFF.md` - Wiederaufnahme nach Chatlimit, Agent-Abbruch, Rechnerneustart oder Session-Wechsel.

## Beziehung zum ASH Local Agent

Der ASH Local Agent kann und soll dieses Protokoll automatisieren, ist aber nicht dessen einzige Source of Truth.

Die bestehende Session-Schicht beantwortet bereits Fragen wie:

- Welche Session arbeitet an welchem Root?
- Ist eine Write-Session aktiv oder stale?
- Welche Jobs laufen?
- Welcher Checkpoint wurde zuletzt gesetzt?

Eine spaetere Project-/Slice-Schicht kann darauf aufbauen, z. B. mit Funktionen wie:

```text
project.detect
project.init
slice.status
slice.open
slice.checkpoint
slice.close
slice.history
```

Die Dateien im Repository bleiben dennoch authoritative, damit auch andere Tools, Menschen oder spaetere Agent-Versionen den Zustand nachvollziehen koennen.

## Minimaler Start eines neuen Projekts

1. Projektprofil waehlen (`generic`, `software`, `kicad`, `cad`, `research`, `reverse-engineering`, `infrastructure`).
2. `.ash/project.yaml` anlegen.
3. `docs/slices/README.md` und `docs/slices/HISTORY.md` anlegen.
4. Vor erster Veraenderung Baseline/Git-Zustand pruefen.
5. Ersten `_OPEN_<ID>_<SLUG>.md` Slice erstellen.
6. Gate 1 durchfuehren und dokumentieren.

## Herkunft

Dieser Standard generalisiert insbesondere folgende bewaehrte MOOX-Prinzipien:

- genau ein aktives Ziel;
- repository-sichtbarer `_OPEN_`-Marker;
- vier Gates;
- Dirty-Tree-Quarantaene;
- Recovery zuerst aus dem Repository statt aus dem Chat;
- permanente Nachweisdokumente fuer abgeschlossene Arbeit;
- explizites Schliessen eines Slices erst nach QA und Dokumentation.

MOOX-spezifische Regeln wie Reverse-Engineering-Evidence-Hierarchien bleiben Profilregeln und werden nicht jedem Projekt aufgezwungen.
