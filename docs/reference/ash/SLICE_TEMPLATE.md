# ASH Slice Template v1

Diese Vorlage ist fuer projektlokale Dateien nach folgendem Schema gedacht:

```text
docs/slices/_OPEN_<ID>_<SLUG>.md
```

Beim Schliessen wird der relevante Abschluss in `docs/slices/HISTORY.md` uebernommen und der `_OPEN_...`-Marker entfernt.

---

# Slice <ID> - <Titel>

**State:** open  
**Gate:** 1/4  
**Profile:** <generic|software|kicad|cad|research|reverse-engineering|infrastructure>  
**Opened:** <YYYY-MM-DD>  
**Owner/Session:** <optional session id / chat / agent>  
**Project root:** <path>  
**Baseline commit:** <git sha / n-a>

## Objective

<Ein enger, pruefbarer Satz: Was soll dieser Slice erreichen?>

## In scope

- <Punkt 1>
- <Punkt 2>

## Out of scope

- <bewusst nicht Teil dieses Slices>

## Pre-existing / quarantined changes

Aenderungen, die bereits vor diesem Slice vorhanden waren und nicht ungefragt veraendert, geloescht oder committed werden duerfen:

- <file/path oder `none`>

## Gate 1 - Checkup + Analysis

**Status:** pending

### Current state

- Git/project status: <...>
- Existing open slice(s): <...>
- Relevant previous commit/checkpoint: <...>
- Relevant runtime/design state: <...>

### Findings

- <verifizierter Befund>

### Assumptions / unknowns

- <Annahme oder Unknown>

### Risks / blockers

- <Risiko oder `none`>

### Proposed implementation shape

- <kurzer Vorschlag>

### Gate 1 result

<accepted / needs discussion / blocked>

## Gate 2 - Decision / Plan

**Status:** pending

### Accepted target state

- <...>

### Accepted implementation

- <...>

### Validation plan

- <...>

### Explicit deviations / decisions

- <...>

## Gate 3 - Implementation

**Status:** pending

### Progress

- [ ] <Teilaufgabe 1>
- [ ] <Teilaufgabe 2>

### Changed files / artifacts

- <path>

### Checkpoints

- `<timestamp>` - <checkpoint/result>

### Material discoveries

- <neue Erkenntnis, die fuer spaetere Sessions wichtig ist>

## Gate 4 - Validation + Close

**Status:** pending

### Required checks

- [ ] profile-specific validation
- [ ] diff/scope review
- [ ] documentation current
- [ ] artifacts current
- [ ] commit/checkpoint recorded

### Validation results

- <check>: <PASS/FAIL + detail>

### Final result

<Was ist jetzt fachlich anders/fertig?>

### Commit / release / checkpoint

- Commit: `<sha or n-a>`
- Subject: `<commit subject>`
- Release/artifacts: <paths/ids or n-a>

### Follow-ups

- <spaeterer Slice / known issue / none>

## Next exact action

<Genau eine konkrete naechste Aktion. Diese Zeile ist besonders wichtig fuer Recovery und Handoff.>

---

## Closing checklist

Vor dem Entfernen dieses `_OPEN_`-Markers:

- [ ] Ziel und Ergebnis sind nachvollziehbar.
- [ ] QA-/Profilchecks sind dokumentiert.
- [ ] Fremde/pre-existing Aenderungen wurden nicht versehentlich eingesammelt.
- [ ] Commit/Checkpoint ist dokumentiert.
- [ ] Follow-ups sind festgehalten.
- [ ] `docs/slices/HISTORY.md` wurde aktualisiert.
- [ ] Der Marker wird erst im Closing-Schritt geloescht.
