# ASH Recovery and Handoff v1

**Version:** 1.0  
**Stand:** 2026-08-29

## Ziel

Dieses Dokument beschreibt, wie ASH-Projekte nach Chatlimit, haengender Session, Agent-Abbruch, Rechnerneustart oder bewusstem Chatwechsel ohne erneute Vollanalyse fortgesetzt werden.

Der zentrale Grundsatz lautet:

> Recovery beginnt im Projekt und in der Session-Schicht, nicht im alten Chatverlauf.

## Standard-Recovery

Eine neue Session oder ein neuer Chat soll in dieser Reihenfolge vorgehen:

1. Projektroot eindeutig bestimmen.
2. Agent-/Session-Status pruefen.
3. Aktive, stale oder fremde Write-Session fuer denselben Root erkennen.
4. `git status --short --branch` bzw. aequivalent lesen.
5. vorhandene `docs/slices/_OPEN_*.md` Marker suchen.
6. offenen Slice vollstaendig lesen.
7. Baseline, Pre-existing Changes, aktuelles Gate und `Next exact action` pruefen.
8. relevante permanente Fach-/Research-/Architektur-Dokumente lesen.
9. erst danach die Arbeit fortsetzen.

Ein neuer Chat soll nicht pauschal "das ganze Projekt neu analysieren", wenn ein sauberer offener Slice bereits die notwendige Recovery-Basis enthaelt.

## Session-Zustaende

### Aktive fremde Write-Session

Nicht mutieren.

- Status/Owner/Checkpoint lesen.
- Nur read-only analysieren, wenn sinnvoll.
- Keine zweite parallele Schreibarbeit auf demselben Root beginnen.

### Stale Session

Nicht blind uebernehmen.

- letzten Checkpoint und laufende/abgebrochene Jobs pruefen;
- Git-/Runtime-Zustand gegen den Checkpoint vergleichen;
- erst danach einen expliziten Takeover durchfuehren;
- Takeover im Slice dokumentieren, wenn er fuer den Arbeitsverlauf relevant ist.

### Keine Session, aber `_OPEN_`-Slice vorhanden

Der Slice ist wichtiger als das Fehlen einer Session.

- neue Session fuer denselben Projektroot oeffnen;
- vorhandenen Slice weiterfuehren;
- nicht ohne Grund einen neuen Slice anlegen.

## Recovery nach maximaler Chatlaenge

Der alte Chat muss nicht mehr verfuegbar oder benutzbar sein.

Eine neue Unterhaltung sollte genuegen mit einer Anweisung wie:

> Pruefe Projekt `<root>`, Session-Status und den offenen ASH-Slice und setze ab `Next exact action` fort.

Der Agent rekonstruiert dann den Zustand aus:

- Session/Checkpoint;
- offenem Slice;
- Git;
- permanenten Projektdokumenten;
- aktuellen Runtime-/Tooldaten.

Falls der alte Chat noch wichtige, aber nicht materialisierte Entscheidungen enthaelt, ist das ein Workflow-Fehler. Diese Entscheidung muss vor weiterer Arbeit im Slice oder in einem permanenten Dokument nachgetragen werden.

## Recovery nach Prozess-/Job-Abbruch

1. Jobstatus pruefen.
2. Teilweise erzeugte Artefakte erkennen.
3. nicht annehmen, dass ein fehlender MCP-/Chat-Response bedeutet, dass der Prozess nicht gelaufen ist.
4. Output/Dateien/Exitstatus gegen den letzten Checkpoint verifizieren.
5. idempotente Operationen bevorzugen.
6. erst danach erneut starten.

Das verhindert doppelte Builds, Exporte, Uploads oder mutierende Toollaeufe.

## Recovery nach Rechner-/Agent-Neustart

- Agent-Ping/Version pruefen.
- persistente Session-Liste lesen.
- stale/orphaned Jobs bzw. Sessions reconciliieren.
- Projekt-Gitstatus lesen.
- offenen Slice lesen.
- nur bei konsistentem Zustand fortsetzen oder kontrolliert Takeover/Recovery dokumentieren.

## Handoff zwischen Chats oder Agenten

Vor einem bewussten Handoff sollte die abgebende Session mindestens materialisieren:

```text
Current gate
Progress
Changed files/artifacts
Latest validation state
Blockers/warnings
Next exact action
Relevant commit/checkpoint
```

Diese Informationen gehoeren in den Slice und/oder einen Agent-Session-Checkpoint.

### Minimaler guter Handoff

```text
Gate: 3/4
Progress: USB-C schematic and PCB placement complete
Changed: main.kicad_sch, main.kicad_pcb
Validation: ERC PASS; DRC not yet run
Warning: pre-existing README.md modification not part of slice
Next exact action: run DRC and parity, then regenerate STEP/PDF
```

Damit kann eine neue Session sofort zielgerichtet weiterarbeiten.

## Konflikt zwischen Chat und Repository

Wenn der Chat sagt, etwas sei fertig, aber Repository/Runtime/Artefakte zeigen das Gegenteil:

- Repository/Runtime verifizieren;
- Widerspruch nicht still aufloesen;
- Slice korrigieren und den Ist-Zustand dokumentieren;
- fehlende Gates erneut ausfuehren.

## Blockierte Slices

Ein blockierter Slice bleibt offen.

Dokumentiere:

- Blocker;
- bereits gepruefte Wege;
- warum weiteres Probieren ohne neue Information nicht sinnvoll ist;
- welche externe Aktion oder Information benoetigt wird;
- `Next exact action` nach Aufloesung des Blockers.

Nicht als `closed` markieren, nur um die Warteschlange optisch sauber zu halten.

## Dirty-Tree-Recovery

Wenn eine neue Session unbekannte Aenderungen findet:

1. gegen die im Slice dokumentierte Baseline vergleichen;
2. bekannte pre-existing/quarantined Dateien nicht anfassen;
3. neue unerwartete Aenderungen als moegliche Arbeit einer anderen Session behandeln;
4. Ownership/Session-Historie pruefen;
5. bei Unsicherheit erst read-only bleiben.

## Abschluss eines wiederaufgenommenen Slices

Ein wiederaufgenommener Slice wird ganz normal ueber Gate 4 geschlossen. Der Handoff selbst erzeugt keinen Sonderstatus.

Die Historie darf optional mehrere beteiligte Sessions nennen, aber das fachliche Ergebnis bleibt ein Slice.

Beispiel:

```text
Slice S042
|-- Session A: Gate 1
|-- Session B: Gate 2 + Gate 3 partial
`-- Session C: Gate 3 complete + Gate 4 + close
```

Genau dieses Verhalten ist beabsichtigt: Der Slice ist langlebiger als ein einzelner Chat.

## Recovery-Definition of Done

Recovery ist erfolgreich, wenn die neue Session ohne Raten beantworten kann:

- Was ist der aktive Slice?
- Welches Gate ist aktuell?
- Welche Aenderungen gehoeren zum Slice?
- Welche Aenderungen waren vorher schon da?
- Was wurde bereits validiert?
- Gibt es einen Blocker oder fremde Ownership?
- Was ist die naechste konkrete Aktion?
