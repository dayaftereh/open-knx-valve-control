# ASH Project Protocol v1

**Version:** 1.0  
**Stand:** 2026-08-29

## Zweck

Dieses Dokument definiert, wie ein Projekt den ASH Project Workflow aktiviert und wie dauerhafter Projektzustand von temporaeren Chat-/Agent-Sessions getrennt wird.

## Grundprinzip

Der Projektzustand muss aus dem Repository rekonstruierbar sein. Wichtige Entscheidungen, offene Arbeit und QA duerfen nicht nur im Chat stehen.

Empfohlene Struktur:

```text
<Project>/
|-- .ash/
|   |-- project.yaml
|   `-- WORKFLOW.md              # optional
|-- docs/
|   `-- slices/
|       |-- README.md
|       |-- HISTORY.md
|       `-- _OPEN_<ID>_<SLUG>.md
`-- ...
```

## `.ash/project.yaml`

Empfohlene Minimaldefinition:

```yaml
protocol: ash-project/v1
name: <project-name>
profile: <generic|software|kicad|cad|research|reverse-engineering|infrastructure>
slices:
  max_active_write: 1
  marker_dir: docs/slices
  gates:
    - checkup
    - decision
    - implementation
    - validation
```

Optionale projektspezifische Felder:

```yaml
validation:
  commands:
    - <project-specific check>
artifacts:
  release_dir: <path>
workflow:
  require_git_commit_on_close: true
```

Das YAML ist fuer Automatisierung gedacht. Projektspezifische Erlaeuterungen koennen in `.ash/WORKFLOW.md` stehen.

## Initialisierung

Beim erstmaligen Einfuehren des Workflows:

1. Projektroot eindeutig bestimmen.
2. Git-/Versionskontrollstatus lesen.
3. Bestehende Checkpoint-/Task-/Research-Dokumentation erfassen.
4. passendes Profil waehlen.
5. `.ash/project.yaml` anlegen.
6. `docs/slices/README.md` mit kurzer lokaler Referenz auf den ASH Slice Standard anlegen.
7. `docs/slices/HISTORY.md` anlegen.
8. Bestehende Arbeit nicht automatisch als neuen Slice umdeuten; zuerst Ist-Zustand dokumentieren.
9. Falls aktuell bereits eine konkrete Arbeit laeuft, daraus einen Recovery-Slice erstellen.

## Source-of-Truth-Hierarchie

Wenn Informationen kollidieren, gilt standardmaessig:

1. aktuelle projektlokale Dateien und verifizierter Runtime-/Designzustand;
2. projektlokale `.ash`- und Slice-Dokumente;
3. Git-Historie / native Checkpoints / Release-Artefakte;
4. zentrale ASH Workflow Library;
5. Chat-/Session-Kontext.

Der Chat darf bei der Interpretation helfen, darf aber einen widersprechenden Repository-Zustand nicht still ueberschreiben.

## Dirty-Tree-Quarantaene

Eine zentrale Sicherheitsregel fuer alle ASH-Projekte:

> Bereits vorhandene oder nicht eindeutig zum aktuellen Slice gehoerende Aenderungen sind fremder Zustand, bis das Gegenteil geklaert ist.

Vor dem ersten Write eines Slices:

- `git status --short --branch` bzw. aequivalent pruefen;
- vorhandene modifizierte/untracked Dateien im Slice unter `Pre-existing / quarantined changes` erfassen;
- diese Dateien nicht loeschen, resetten oder ungefragt formatieren;
- sie nicht automatisch in den eigenen Commit aufnehmen;
- nur dann veraendern, wenn sie explizit in Scope genommen wurden.

Beispiel:

```text
M  board.kicad_pcb
?? prototype.step
M  README.md
```

Der Slice kann festhalten:

```text
Pre-existing / quarantined changes:
- board.kicad_pcb
- prototype.step
- README.md
```

Spaetere Sessions koennen dadurch zwischen Baseline-Fremdzustand und Slice-Aenderungen unterscheiden.

## Baseline

Jeder Slice soll seinen Ausgangspunkt dokumentieren:

- Git commit SHA oder Revision;
- Datum/Zeit;
- relevante native Projekt-/Toolversion;
- vorhandene Dirty-Tree-Aenderungen;
- falls sinnvoll: Hash/Manifest wichtiger Quelldaten oder Releases.

Das ist besonders wichtig bei CAD, EPLAN, KiCad, generierten Dateien und externen Quelldaten.

## Ownership und parallele Arbeit

Der projektlokale Slice-Marker ersetzt keine technische Session-Sperre. Beide Ebenen ergaenzen sich:

- **Session-/Write-Lock:** verhindert oder erkennt gleichzeitige technische Schreibarbeit auf demselben Root.
- **Slice-Marker:** dokumentiert fachlich, welche Arbeit noch offen ist.

Standard:

```text
max_active_write: 1
```

Parallele Write-Slices sind nur sinnvoll, wenn:

- ihre Pfade/Subsysteme klar getrennt sind;
- Ownership dokumentiert ist;
- ihre Abschluss- und Merge-Reihenfolge geklaert ist.

## Commits

Ein Closing-Commit soll nur den Scope des Slices enthalten. Falls das wegen bereits vorhandener Aenderungen nicht moeglich ist, muss der Slice den Grund explizit dokumentieren.

Empfohlene Commit-Nachricht:

```text
<area>: <slice result>
```

oder projektkonform entsprechend bestehender Git-Konventionen.

## HISTORY.md

`docs/slices/HISTORY.md` ist die kompakte chronologische Uebersicht geschlossener Slices.

Empfohlener Eintrag:

```markdown
## S042 - Population Growth
- Closed: 2026-08-29
- Result: implemented and validated
- Commit: abc1234
- Profile: reverse-engineering
- Evidence/Docs: docs/research/...
- Follow-up: S043 ...
```

Die Historie ersetzt keine detaillierte Fachdokumentation. Sie ist ein Navigationsindex.

## Projektabschluss / Release

Ein Release darf mehrere geschlossene Slices umfassen. Slice-Close und Release sind daher getrennte Konzepte.

Ein Projekt kann einen Slice schliessen, wenn dieser fachlich fertig und validiert ist, auch wenn der naechste Release erst spaeter erfolgt.
