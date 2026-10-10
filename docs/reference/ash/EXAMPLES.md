# ASH Project Workflow Examples v1

**Version:** 1.0  
**Stand:** 2026-08-29

Diese Beispiele zeigen, wie derselbe Slice-Standard in unterschiedlichen Projekttypen verwendet wird.

# Beispiel 1 - MOOX / Reverse Engineering

```yaml
protocol: ash-project/v1
name: moox
profile: reverse-engineering
slices:
  max_active_write: 1
  marker_dir: docs/slices
```

Aktiver Marker:

```text
docs/slices/_OPEN_S042_POPULATION_GROWTH.md
```

Typischer Gate-Verlauf:

1. Originaldaten/-code und aktuellen MOOX-Stand analysieren.
2. Verhalten/Implementation Shape mit Nutzer festlegen.
3. Gameplay-/Datenlogik plus Tests implementieren.
4. Tests/Vet/Diff/Evidence-Dokumentation, Commit und Close.

# Beispiel 2 - KiCad / RP2040 Board

```yaml
protocol: ash-project/v1
name: stepper-rp2040
profile: kicad
slices:
  max_active_write: 1
  marker_dir: docs/slices
```

Slice:

```text
_OPEN_K017_USB_C_POWER_INPUT.md
```

Objective:

> USB-C-Eingangsschaltung und zugehoerige PCB-Platzierung auf den freigegebenen Stand bringen und anschliessend ERC/DRC/Parity pruefen.

Gate 4 kann enthalten:

```text
ERC
DRC
Schematic-PCB parity
ASH PCB QA
Top/Bottom render
STEP/PDF export
git diff --check
```

# Beispiel 3 - FreeCAD / mechanische Baugruppe

```yaml
protocol: ash-project/v1
name: glaspipe-measurement-stand
profile: cad
slices:
  max_active_write: 1
```

Slice:

```text
_OPEN_CAD008_LS7010_ADAPTER_PLATE.md
```

Gate 1:

- vorhandene Assembly/Placements pruefen;
- LS70-10 Referenzteile und Profilpositionen lesen;
- vorhandene nicht zum Slice gehoerende CAD-Aenderungen quarantainen.

Gate 4:

- recompute;
- Constraints/Links pruefen;
- Maße kontrollieren;
- STEP/STL exportieren;
- Export auf Plausibilitaet pruefen;
- Commit/Checkpoint dokumentieren.

# Beispiel 4 - Software / ASH Local Agent

```yaml
protocol: ash-project/v1
name: ash-local-agent
profile: software
slices:
  max_active_write: 1
```

Slice:

```text
_OPEN_SW031_DUPLICATE_TUNNEL_GUARD.md
```

Objective:

> Verhindern, dass zwei Core-Instanzen mit denselben Tunnel-Credentials gleichzeitig dieselbe Connector-Identitaet verwenden.

Gate 4 beispielsweise:

```text
gofmt
go test ./...
go vet ./...
git diff --check
core build
self-test
controlled live test
```

# Beispiel 5 - Home Assistant / Infrastruktur

```yaml
protocol: ash-project/v1
name: homeassistant
profile: infrastructure
slices:
  max_active_write: 1
```

Slice:

```text
_OPEN_INF014_SOLAR_GRAPH_PERFORMANCE.md
```

Gate 1:

- Erreichbarkeit/NetBird pruefen;
- Home-Assistant-Health und Logs lesen;
- betroffene Dashboard-/REST-Abfragen identifizieren;
- aktuelle Scanintervalle und Runtime-Zustand dokumentieren.

Gate 4:

- Config validation;
- Reload/Restart nur wenn erforderlich;
- Health/API-Test;
- Logs nach Aenderung;
- Dashboard-Funktion pruefen;
- keine Secrets im Diff.

# Beispiel 6 - Slice ueber mehrere Chats

```text
Slice K017 - USB-C Power Input
|
|-- Session/Chat A
|   `-- Gate 1 abgeschlossen
|
|-- Session/Chat B
|   |-- Gate 2 abgeschlossen
|   `-- Gate 3 zu 70 %
|
`-- Session/Chat C
    |-- offenen Slice gelesen
    |-- Gate 3 fertiggestellt
    |-- Gate 4 bestanden
    `-- Slice geschlossen
```

Die neue Session benoetigt den alten Chat nicht. Entscheidend sind:

- `_OPEN_...` Marker;
- Baseline und Dirty-Tree-Quarantaene;
- letzter Session-/Slice-Checkpoint;
- `Next exact action`;
- Git-/Runtime-Zustand.

# Beispiel fuer HISTORY.md

```markdown
# Slice History

## K017 - USB-C Power Input
- Closed: 2026-08-29
- Result: implemented and validated
- Commit: abc1234
- Profile: kicad
- Artifacts: Gerber, STEP, PDF
- Follow-up: K018 connector silkscreen cleanup

## K016 - RP2040 Decoupling Audit
- Closed: 2026-08-28
- Result: validated; no changes required
- Commit: n/a
- Profile: kicad
```

# Beispiel fuer einen bewusst blockierten Slice

```text
State: blocked
Gate: 3/4
Blocker: Hersteller-STEP fuer den finalen Steckverbinder fehlt.
Tried: lokale Library und freigegebene Projektressourcen geprueft.
Do not: beliebiges aehnliches 3D-Modell als final markieren.
Next exact action: STEP vom Hersteller beschaffen oder Nutzerfreigabe fuer Platzhalter erhalten.
```

Der Slice bleibt offen und kann spaeter ohne erneute Analyse fortgesetzt werden.
