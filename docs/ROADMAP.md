# OpenKNXValveControl - ASH Slice Roadmap

**Stand:** 2026-10-10. **Version:** initialer, projektbezogener Plan; geplante IDs/Abhaengigkeiten sind **noch keine Implementierungsfreigabe**.

**Workflow:** [ASH Slice Protocol v1](reference/ash/SLICE_PROTOCOL.md) und [lokale Regeln](../.ash/WORKFLOW.md).

**Ablauf:** pro Write-Slice Gate 1 Checkup -> Gate 2 Decision -> Gate 3 Implementation -> Gate 4 Validation/Close; eine frische Session darf einen vorhandenen Slice weiterfuehren.

## Gesicherter Ist-Zustand vor ASH-Bootstrap

- Repository: `C:\ASH\Workspace\Projects\open-knx-valve-control`, Branch `main`.
- Stand vor KNX001: `c2e4bee`; vier dokumentationsorientierte Commits nach `origin/main`, damals clean; **kein Remote-Push erfolgt**.
- Hardware V1.2: [visuell gepruefter Schaltplan](SCHEMATIC_V1_2_REVIEW.md), [PCB-Static-Audit](PCB_V1_2_AUDIT.md), **keine vollstaendige ERC/DRC/BOM-/Bestueckungsfreigabe**.
- Antriebe: [HmIP-VDMOT](ACTUATOR_HMIP_VDMOT.md), 3,3 V, maximal 120 mA laut Hersteller, 4,3 +/- 0,3 mm Hub; **keine** validierten Stromprofil- oder Laufzeitmessungen.
- Motoransteuerung: vier TB6612FNG, acht Ausgaenge, gemeinsame `IN_1/IN_2`-Richtung, ein INA219/R29-Shunt, **ein Motor gleichzeitig**.
- KNX-/USB-/externes 5-V-Konzept [dokumentiert, nicht verifiziert](POWER_SUPPLY_CONCEPT.md); keine externen Versorgungsklemmen/5-V-Verbinder auf V1.2 freigegeben.
- ETS6 auf LLO Desktop vorhanden; XML 19 Parameter/33 KO, nur ein dynamischer Kanal, 5.004 statt geplantem 5.001 Stellwert, [OpenKNXprodukt-Audit](ETS_PRODUCT_AUDIT.md), temporaere Produktgenerierung ohne ETS-Importnachweis.
- Controller-Firmware initialisiert aktuell KNX, aber noch keine vollstaendige Motor-, Positions- und Raumregelung. [Architektur](ARCHITECTURE.md).

## Slice-Portfolio

`planned` = nur Plan/kein `_OPEN_`-Marker, `blocked` = gestarteter offener Slice mit dokumentiertem Hindernis, `closed` = in [HISTORY](slices/HISTORY.md) abgeschlossen.

| Slice | Status | Objective | Dependencies | Gate-4-Abnahme (noch nicht erfuellt) |
| --- | --- | --- | --- | --- |
| **KNX001** ASH Workflow Bootstrap | **open, Gate 3** | ASH v1 kopieren, Project/Slice/Session Regeln, Historie, README und Roadmap verankern | vorhandenes Repo und Library-Original | 7 Quelltexte vorhanden, Links/Repo-Audit PASS, Git scope clean, KNX001 in History geschlossen und Marker geloescht |
| **KNX002** As-built Hardware/BOM | planned | R29-Wert, U25-Typ, F1, Pinouts, PCB Rev V1.2, Native EasyEDA DRC/ERC/BOM und Power-Jumper-Bestueckung abgleichen | KNX001; bestueckte Platine/Artefakte | Provenienzfotos/Messwerte, BOM/DRC/Evidence, klare PASS/Blocker fuer KNX003 |
| **KNX003** Stromversorgung 5 V | planned | Gemeinsames externes 5-V-Design vs. separate Motor-3,3-V-Schiene entscheiden, Quellenentkopplung, Schutz und Power-Good spezifizieren/testen | KNX002; geeignete sichere Labormittel | Nachgewiesener Quellentrennungs-/Spannungs-/Rueckspeisetest bei ausgeschalteten Motoren, ggf. PCB V1.3 Vorschlag |
| **KNX004** Motor-Safety und Scheduler | planned | RP2040 sichere Default-Ausgaenge, all-off, exklusives Motor-Token und Fehler-/Timeout-Zustaende implementieren, ohne riskanten Endanschlagbetrieb | KNX002; Versorgungsentscheidung fuer echte Hardwaretests | Unit-/Mock-Tests: niemals zwei Motoren aktiv, Reset/Fail-safe, sauberes Stoppen; Build PASS |
| **KNX005** INA219/HmIP-VDMOT Charakterisierung | planned | Mit freigegebener Versorgung Stromkurven, Motorpolung, Anlauf, Endanschlag und gemessene Laufzeit auf einem Kanal aufnehmen | KNX002 + KNX003 + KNX004; echter Antrieb | Nachvollziehbare Messdaten, Grenzwerte/Filter & unabh. Abschaltkriterien; keine Annahme `120 mA = Endlage` |
| **KNX006** Referenzfahrt und Position | planned | Individuelle Position 0..100 % per Homing + getrennte Laufzeiten, Persistenz/Uncertainty und Diagnose je M1..M8 | KNX004 + KNX005 | 0/25/50/75/100-%-Tests, Reboot/Unterbrechung/Blocker, immer nur ein Antrieb und fehlersicheres Stoppen |
| **KNX007** Temperaturpfad | planned | ATtiny3216/OneWire T0..T8, UART/SPI-Anbindung und KNX-Isttemperaturquelle eindeutig modellieren | KNX002, Software-Baseline | Frischewerte, Timeouts, Fehler-/Sensorstaleness, Zuordnung `T0..T8` vs. Raum und relevante Tests |
| **KNX008** ETS Zone/Channel Design | planned | Acht Motoren auf bis zu acht Räume gruppierbar; Regelungsmodus `Soll/Ist Temperatur` vs. `0..100%` und korrekte DPTs sowie KNX-Objektnamen festlegen | KNX001 und [ETS-Audit](ETS_PRODUCT_AUDIT.md) | Reviewte Nummer-/Parameter-/DPT-Tabelle, migrationsfaehige Versionierung, C-sichere Identifier; **noch keine Aktivierung im Altprojekt** |
| **KNX009** ETS6 Produkt-/Importtest | planned | XML/Header/Producer aktualisieren, versionierte `.knxprod` bauen und isoliert in ETS6 importieren | KNX008 | XML Sanity/Generator, Header-Compile, ETS Import-/GA-Sichttest, Version/Release-Manifest |
| **KNX010** Raum-/Heizkreisregelung | planned | Mehrfachzuordnung M1..M8 zu Zonen, PI-/hysteresebasiertes Raumregeln und direktes KNX 0..100 % inklusive Fault Fallback implementieren | KNX006 + KNX007 + KNX009 | Tests fuer Raum mit 1/2/3/4 Motoren, Sensorfehler, Busausfall, konkurrierende Sollwerte, stabile sequenzielle Fahrten |
| **KNX011** HMI, Integration & Release Gate | planned | LCD/Encoder/Diagnostik integrieren, Strom-/Versorgungs-/ETS-/Motorchecks zusammenfuehren, validierte Version dokumentieren | KNX003..KNX010 | End-to-End ETS-Download/Telegramme, Tests am realen Aufbau, BOM/DRC/QA, Fehlerfälle und Release-Artefakte dokumentiert |

## Reihenfolge und Sicherheitsabhaengigkeiten

- **Naechster zweckmaessiger Hardware-Slice:** KNX002. Ohne Fotos/Bestueckung kann er `blocked` werden; das darf nicht als Erfolg gewertet werden.
- **Bereits ohne laufende Hardwaretests moegliche konzeptionelle Arbeit:** KNX008 (ETS-Datenmodell), sobald KNX001 geschlossen wurde. Unabhaengige Planung ist moeglich; **kein zweiter paralleler Write-Slice**.
- KNX003 und KNX005 duerfen keine gefaehrlichen Blindversuche mit 5 V/3,3 V, Netzteilen oder Antrieben ausloesen. Stromversorgung, Diodenpfad, Schutz und reale Bestueckung muessen vorher freigegeben sein.
- KNX009 baut nur ein separates Produkt und importiert es zum Test; keine ungepruefte Aenderung am produktiven KNX-/ETS-Projekt.
- Projektrelease nur nach KNX011 oder anderem expliziten Release-Gate, **nicht automatisch beim Abschluss einzelner Slices**.

## Nutzung der Roadmap

- Jeder Slice muss beim tatsaechlichen Start aus diesem Plan als [ASH-Vorlage](reference/ash/SLICE_TEMPLATE.md) unter `docs/slices/_OPEN_KNX###_<SLUG>.md` materialisiert werden.
- Die vier Gates und die jeweils konkreten Scope-/QA-Bedingungen im Marker festhalten.
- Ein bereits laufender Slice wird ueber Session-/Git-Checkpoint und `Next exact action` fortgesetzt.
- Nach Gate 4 nur den geschlossenen Slice in [HISTORY](slices/HISTORY.md) schreiben, Marker entfernen und den Roadmap-Status auf `closed` setzen. **Den Folgeslice nicht nur aus Bequemlichkeit voroeffnen.**

## Historische Arbeiten vor Einfuehrung des ASH-Protokolls

Die Commits `53b308a` (Antrieb/ETS-Konzept), `4fa28c1` (Schaltplan), `0045a45` (PCB/ETS), `c2e4bee` (5-V-Versorgung) bilden eine **bereits dokumentierte Ausgangsbasis**. Sie werden nicht nachtraeglich in fiktive, formal gate-validierte Slices umetikettiert.
