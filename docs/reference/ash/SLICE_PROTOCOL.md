# ASH Slice Protocol v1

**Version:** 1.0  
**Stand:** 2026-08-29

## Definition

Ein **Slice** ist die kleinste eigenstaendig planbare, implementierbare, pruefbare und abschliessbare Arbeitseinheit eines Projekts.

Ein guter Slice ist:

- fachlich klar begrenzt;
- unabhaengig checkpointbar;
- so klein, dass er abgeschlossen oder eindeutig blockiert werden kann;
- so dokumentiert, dass ein anderer Chat oder Agent ihn ohne Rekonstruktion aus dem Gespraech fortsetzen kann.

Schlecht:

> PCB fertig machen.

Besser:

> USB-C-Eingangsschaltung auf den freigegebenen ESD-/CC-Stand bringen, DRC/Parity pruefen und Release-Artefakte aktualisieren.

## Open-Slice-Marker

Ein unfertiger Slice wird im Projekt repository-sichtbar markiert:

```text
docs/slices/_OPEN_<ID>_<SLUG>.md
```

Beispiele:

```text
docs/slices/_OPEN_S042_POPULATION_GROWTH.md
docs/slices/_OPEN_K17_USB_C_INPUT.md
docs/slices/_OPEN_CAD08_LS7010_ADAPTER.md
```

Der Marker ist ein kompakter Recovery-/Checklist-Stand. Dauerhafte Ergebnisse gehoeren zusaetzlich in die passende Projekt-, Architektur-, Research- oder Release-Dokumentation.

Standardregel: **genau ein aktiver Write-Slice pro Projekt.** Parallele Slices sind nur erlaubt, wenn sie explizit geplant wurden, unterschiedliche Ownership besitzen und sich ihre Write-Scope nicht ueberschneidet.

# Die vier Gates

## Gate 1 - Checkup + Analyse

Vor jeder fachlichen Veraenderung:

1. Projektroot und aktuelle Session/Ownership bestimmen.
2. `git status` bzw. aequivalenten Projektzustand pruefen.
3. vorhandene `_OPEN_*.md` Marker pruefen.
4. letzten relevanten Commit/Checkpoint lesen.
5. bereits vorhandene, fremde oder unbekannte Aenderungen erfassen.
6. aktuellen Ist-Zustand fachlich analysieren.
7. Scope, Risiken, Annahmen, Unknowns und Blocker dokumentieren.
8. vorgeschlagene Umsetzung formulieren.

**Gate-1-Regel:** Noch keine fachliche Implementierung beginnen, solange Analyse und Scope nicht klar sind.

Bei rein mechanischen/risikoarmen Aufgaben kann die Decision sehr kurz ausfallen, sie muss aber trotzdem nachvollziehbar sein.

## Gate 2 - Decision / Plan

Hier wird festgelegt, **was genau gebaut/geaendert wird**.

Festzuhalten sind mindestens:

- Zielzustand;
- In-Scope;
- Out-of-Scope;
- akzeptierte Architektur/Regeln/Datenstruktur;
- relevante bewusste Abweichungen;
- erwartete QA-/Release-Gates.

Erst nach einer klaren Entscheidung wird Gate 2 abgeschlossen.

## Gate 3 - Implementation

- nur den vereinbarten Slice implementieren;
- bestehende fremde Dirty-Tree-Aenderungen nicht ungefragt veraendern;
- laenger laufende Arbeiten mit Session-/Slice-Checkpoints versehen;
- Tests, Generatoren, Exporte und Dokumentation synchron mitfuehren;
- neue fachliche Erkenntnisse dokumentieren, wenn sie den vereinbarten Plan materiell veraendern;
- bei groesserem Scope-Drift zurueck in Gate 2 statt still weiterzubauen.

## Gate 4 - Validation + Commit + Close

Die konkreten Checks haengen vom Projektprofil ab. Generisch gehoeren dazu:

- projektspezifische Tests/Validierungen;
- statische Checks bzw. DRC/Parity/Recompute/Healthcheck;
- `git diff` bzw. Aenderungsvergleich;
- keine unbeabsichtigten Dateien im Scope;
- relevante Exporte/Artefakte aktuell;
- Dokumentation und Slice-Ergebnis aktuell;
- Commit-/Checkpoint-Zustand dokumentiert;
- offene Risiken oder Follow-ups explizit vermerkt.

Danach:

1. Ergebnis im Slice bzw. permanenten Dokument festhalten.
2. `HISTORY.md` aktualisieren.
3. `_OPEN_...` Marker im Closing-Commit entfernen.
4. naechsten Slice **nicht automatisch** oeffnen; erst wenn die Arbeit daran wirklich beginnt.

Ein geschlossener Slice hinterlaesst permanente Historie, aber keinen `_OPEN_`-Marker.

# Zustandsmodell

Empfohlene Slice-Zustaende:

```text
open
blocked
ready-for-validation
closed
```

Die Gates bleiben unabhaengig davon numerisch nachvollziehbar:

```text
gate: 1/4
```

Bei Blockierung wird der Slice nicht geloescht. Stattdessen werden Blocker und naechste konkrete Aktion dokumentiert.

# Scope-Drift-Regel

Vor einer groesseren Nebenarbeit fragen:

> Traegt diese Aktion direkt zum aktuellen Slice-Ziel oder zum naechsten dokumentierten Schritt bei?

Wenn nein:

- nicht spontan implementieren;
- als Follow-up festhalten;
- zum aktiven Slice zurueckkehren.

# Recovery-Regel

Beim Start jeder neuen Arbeits-Session:

1. Projektroot bestimmen.
2. Session-/Write-Ownership pruefen.
3. `git status` pruefen, ohne unbekannte Aenderungen zu verwerfen.
4. `docs/slices/_OPEN_*.md` pruefen.
5. Existiert ein offener Slice: diesen zuerst lesen und fortsetzen.
6. Erst ohne offenen Slice den naechsten neuen Slice bestimmen.

Der Chatverlauf darf als Zusatzkontext dienen, aber nie benoetigt werden, um den aktiven Projektzustand zu rekonstruieren.

# Abschlusskriterium

Ein Slice ist nur dann wirklich abgeschlossen, wenn eine neue Session aus Repository + Slice-Historie erkennen kann:

- was das Ziel war;
- was geaendert wurde;
- welche Checks bestanden wurden;
- welche Artefakte entstanden sind;
- welcher Commit/Checkpoint dazu gehoert;
- welche Restpunkte bewusst offen sind.
