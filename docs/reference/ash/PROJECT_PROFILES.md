# ASH Project Profiles v1

**Version:** 1.0  
**Stand:** 2026-08-29

## Zweck

Alle ASH-Projekte verwenden dasselbe Vier-Gate-Slice-Protokoll. Die Profile passen nur die fachlichen Checkups, Validierungen und typischen Artefakte an.

Verfuegbare Basisprofile:

```text
generic
software
kicad
cad
research
reverse-engineering
infrastructure
```

Ein Projekt darf projektspezifische Erweiterungen definieren, soll aber die Bedeutung der vier Gates nicht veraendern.

# generic

Fuer Projekte ohne spezielles Toolprofil.

## Gate 1

- Git-/Dateistatus pruefen.
- offenen Slice pruefen.
- Baseline und Zielzustand erfassen.
- Scope und Risiken dokumentieren.

## Gate 4

- fachlichen Soll/Ist-Vergleich durchfuehren;
- Diff pruefen;
- erzeugte Artefakte kontrollieren;
- Dokumentation/Commit aktualisieren.

# software

Typisch fuer Go, Angular, Python, Services, Generatoren und Desktop-Anwendungen.

## Gate 1

- Repository-/Branchstatus;
- Abhaengigkeiten und relevante Versionen;
- laufende Services/Prozesse, falls relevant;
- vorhandene Tests und bekannte Fehler;
- bestehende Architektur-/API-Grenzen.

## Gate 4 - typische Checks

Projektabhaengig z. B.:

```text
formatter
tests
static analysis / lint / vet
build
self-test / smoke test
git diff --check
```

Bei Services zusaetzlich:

- Start/Stop-Verhalten;
- Migration/Config-Kompatibilitaet;
- Health-/API-Smoke-Test;
- relevante Logs.

# kicad

Fuer Schaltplan-/PCB-Projekte.

## Gate 1

- Gitstatus und Board-/Schematic-Baseline;
- KiCad-Version;
- bestehende ERC/DRC-/Parity-Lage;
- ungeroutete Netze bzw. aktueller Routing-Stand;
- Footprint-/3D-Modell-/Library-Abhaengigkeiten;
- vorhandene Release-/Gerber-/STEP-Artefakte.

## Gate 4 - typische Checks

- ERC;
- PCB DRC;
- Schematic-PCB Parity;
- projekt-/ASH-spezifische PCB-QA;
- relevante RefDes-/Silkscreen-Pruefung;
- 3D Top/Bottom/Isometric Render, falls Teil des Projekts;
- Gerber/Drill/STEP/GLB/PDF/BOM je nach Releaseumfang;
- Release-Manifest/Hashes, falls vorgesehen.

Wichtig: Ein Slice darf absichtlich nur einen Teil des Boards routen. Erwartete offene Verbindungen muessen dann als Baseline/Expected State dokumentiert werden und sind nicht automatisch ein Fehler.

# cad

Fuer FreeCAD, Creo und andere mechanische/CAD-Projekte.

## Gate 1

- native Quelldatei und Assembly-Struktur;
- Tool-/Dateiversion;
- bestehende Constraints/Links/Placement;
- externe STEP/STL/Referenzen;
- Sichtbarkeit und benoetigte Unterbaugruppen;
- relevante mechanische Bezugssysteme und Einheiten.

## Gate 4 - typische Checks

- Modell recompute/regenerate;
- keine unerwarteten broken links/constraints;
- Geometrie-/Interferenzpruefung soweit verfuegbar;
- Maße/Orientierung gegen Zielanforderung pruefen;
- STEP/STL/DXF/PDF/Render neu erzeugen, wenn im Scope;
- exportierte Geometrie stichprobenartig wieder einlesen oder vergleichen, wenn kritisch.

# research

Fuer Analyse-, Vergleichs-, Machbarkeits- und Untersuchungsprojekte.

## Gate 1

- Forschungsfrage eng definieren;
- vorhandene interne Evidenz und Dokumentation lesen;
- Annahmen und offene Fragen sichtbar machen;
- Quellen-/Messbasis festlegen.

## Gate 4

- Findings klar von Annahmen trennen;
- Quellen/Provenienz dokumentieren;
- reproduzierbare Daten/Notizen sichern;
- offene Unsicherheiten festhalten;
- naechste konkrete Frage als Follow-up definieren.

# reverse-engineering

Erweiterung von `research`, abgeleitet aus dem MOOX-Workflow.

## Evidence-Hierarchie

Wenn passend, Provenienz sichtbar klassifizieren, z. B.:

1. direkt am Original beobachtet;
2. deterministisch aus Originaldaten/-code abgeleitet;
3. sekundaer verifiziert;
4. pending / nicht ausreichend bewiesen.

Keine Luecken raten, nur um Tabellen oder Mappings zu vervollstaendigen.

## Gate 1

- Originalartefakte identifizieren und wenn sinnvoll hashen;
- Originalverhalten/-daten zuerst untersuchen;
- bestehende abgeschlossene Research-Bereiche nicht ohne neuen Grund wieder oeffnen;
- Such-/Explorationspfade begrenzen und materialisierte Findings erzeugen.

## Gate 4

- Provenienz und reproduzierbare Evidence dokumentieren;
- normalisierte Daten/Tests aktualisieren;
- bewusste Modernisierungen klar vom Originalverhalten trennen.

# infrastructure

Fuer Home Assistant, Server, VMs, Netzwerk, Docker, Deployments und Betriebsautomatisierung.

## Gate 1

- Health-/Erreichbarkeitsstatus;
- laufende Version/Deployment;
- Config-/Secrets-Grenzen beachten;
- Logs und Ressourcenstatus;
- Backup/Rollback-Moeglichkeit;
- aktuelle Nutzer-/Produktivlast.

## Gate 4 - typische Checks

- Config validation;
- Service-/Container-Health;
- API/Netzwerk-Smoke-Test;
- relevante Logs nach Aenderung;
- Restart-/Recovery-Verhalten;
- keine Secrets in Git/Logs;
- Rollback-/Backup-Pfad dokumentiert, wenn die Aenderung riskant ist.

# Profilwahl

Wenn mehrere Profile passen, wird ein Hauptprofil gewaehlt und projektlokal ergaenzt.

Beispiele:

```text
MOOX                          -> reverse-engineering
stepper-rp2040                -> kicad
HMI-RP2350                    -> kicad
ash-local-agent               -> software
Dome Milling Station Cockpit  -> software
Home Assistant                -> infrastructure
glaspipe-measurement-stand    -> cad
Creo -> FreeCAD migration     -> cad + research extension
```

Die Profilwahl veraendert nicht die Recovery- und Ownership-Regeln.
