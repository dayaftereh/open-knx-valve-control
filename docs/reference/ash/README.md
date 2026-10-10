# ASH Project Workflow v1 - lokale Quellreferenzen

**Importiert am:** 2026-10-10  
**Herkunft:** ChatGPT Space / Library `/ASH` (sieben Originaldateien des ASH Project Workflow v1, Stand 2026-08-29).  
**Verwendung:** Repository-interne, offline lesbare Referenz fuer das ASH-Slice-/Gate-/Recovery-Protokoll. Die zentrale Library bleibt die Quelle fuer spaetere Standard-Updates.

Die folgenden Texte wurden in voller Laenge aus dem Space `/ASH` in diesen Ordner kopiert; die ausgegebenen Dateigroessen entsprechen den dort gelisteten Originalen. Die Inhalte duerfen bei Aenderungen am Projektworkflow **nicht stillschweigend** gegen neue Fassungen ersetzt werden: zuerst Diff, Version und Auswirkungen dokumentieren.

| Quelldatei | Originalgroesse | Rolle |
| --- | ---: | --- |
| [README_PROJECT_WORKFLOW.md](README_PROJECT_WORKFLOW.md) | 5.049 B | Einstieg, Project/Slice/Session, Source of Truth, Aufbau |
| [PROJECT_PROTOCOL.md](PROJECT_PROTOCOL.md) | 5.153 B | Projektinitialisierung, Quarantaene, Commit, History, Ownership |
| [SLICE_PROTOCOL.md](SLICE_PROTOCOL.md) | 5.083 B | Vier Gates, Open-Marker, Recovery, Abschluss |
| [SLICE_TEMPLATE.md](SLICE_TEMPLATE.md) | 2.977 B | Vorlage fuer einen aktiven `_OPEN_...`-Marker |
| [PROJECT_PROFILES.md](PROJECT_PROFILES.md) | 5.339 B | Profile software, kicad, cad, research und infrastructure |
| [RECOVERY_HANDOFF.md](RECOVERY_HANDOFF.md) | 5.923 B | Wiederaufnahme bei Session-/Job-Abbruch und Handoff |
| [EXAMPLES.md](EXAMPLES.md) | 4.214 B | Beispiele verschiedener Projekttypen und Blocker |

Pruefbarer Snapshot: [MANIFEST.sha256](MANIFEST.sha256) listet normalisierte SHA-256-Pruefsummen dieser sieben Dateien; `python ../../../tools/audit_ash_workflow.py` verifiziert Inhalte und lokale Verweise aus dem Repository-Root (aufgerufen als `python tools/audit_ash_workflow.py`).

Diese sieben Dateien bilden den **Slice-Workflow-Satz**. Der Space `/ASH` enthaelt daneben einen eigenen Corporate-Design-Leitfaden und zwei SVG-Logos. Diese wurden nicht in den technischen Slice-Workflow kopiert, da sie keine Aufgaben-/Recovery-Regeln enthalten; sie bleiben im Space verfuegbar.

## Aktivierung in diesem Projekt

- Projektregeln: [`.ash/project.yaml`](../../../.ash/project.yaml) und [`.ash/WORKFLOW.md`](../../../.ash/WORKFLOW.md)
- Slice-Index: [`docs/slices/README.md`](../../slices/README.md)
- Chronologische Historie: [`docs/slices/HISTORY.md`](../../slices/HISTORY.md)
- Projektspezifische naechste Arbeitspakete: [`docs/ROADMAP.md`](../../ROADMAP.md)
- Einstieg: [Root README](../../../README.md)

**Source-of-Truth-Hierarchie nach PROJECT_PROTOCOL:** verifizierte lokale Projekt-/Runtime-Dateien, projektlokale Workflow-/Slice-Dokumente, Git/Checkpoints, dann zentrale ASH Library, erst danach Chat-Kontext.
