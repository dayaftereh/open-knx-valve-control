# OpenKNXValveControl - ASH Slice Roadmap

**Stand:** 2026-10-12. **Version:** Software-first Repriorisierung KNX012 und KNX015-Temperatur-MVP: Erst ATtiny -> UART -> RP2040 -> KNX-Temperaturen; danach Motor-Safety und Raumregelung. Geplante IDs/Abhaengigkeiten sind **keine Implementierungsfreigabe**.

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

`planned` = nur Plan/kein `_OPEN_`-Marker, `deferred` = bewusst zurueckgestellt, ohne aktiven `_OPEN_`-Marker, `blocked` = gestarteter offener Slice mit dokumentiertem Hindernis, `closed` = in [HISTORY](slices/HISTORY.md) abgeschlossen.

| Slice | Status | Objective | Dependencies | Gate-4-Abnahme (noch nicht erfuellt) |
| --- | --- | --- | --- | --- |
| **KNX001** ASH Workflow Bootstrap | **closed, 2026-10-10** | ASH v1 kopieren, Project/Slice/Session Regeln, Historie, README und Roadmap verankern | vorhandenes Repo und Library-Original | 7 Quelltexte vorhanden, Links/Repo-Audit PASS, Git scope clean, KNX001 in History geschlossen und Marker geloescht |
| **KNX002** As-built Hardware/BOM | planned | R29-Wert, U25-Typ, F1, Pinouts, PCB Rev V1.2, Native EasyEDA DRC/ERC/BOM und Power-Jumper-Bestueckung abgleichen | KNX001; bestueckte Platine/Artefakte | Provenienzfotos/Messwerte, BOM/DRC/Evidence, klare PASS/Blocker fuer KNX003 |
| **KNX003** Stromversorgung 5 V | planned | Gemeinsames externes 5-V-Design vs. separate Motor-3,3-V-Schiene entscheiden, Quellenentkopplung, Schutz und Power-Good spezifizieren/testen | KNX002; geeignete sichere Labormittel | Nachgewiesener Quellentrennungs-/Spannungs-/Rueckspeisetest bei ausgeschalteten Motoren, ggf. PCB V1.3 Vorschlag |
| **KNX004** Motor-Safety und Scheduler | planned | RP2040 sichere Default-Ausgaenge, all-off, exklusives Motor-Token und Fehler-/Timeout-Zustaende implementieren, ohne riskanten Endanschlagbetrieb | KNX002; Versorgungsentscheidung fuer echte Hardwaretests | Unit-/Mock-Tests: niemals zwei Motoren aktiv, Reset/Fail-safe, sauberes Stoppen; Build PASS |
| **KNX005** INA219/HmIP-VDMOT Charakterisierung | planned | Mit freigegebener Versorgung Stromkurven, Motorpolung, Anlauf, Endanschlag und gemessene Laufzeit auf einem Kanal aufnehmen | KNX002 + KNX003 + KNX004; echter Antrieb | Nachvollziehbare Messdaten, Grenzwerte/Filter & unabh. Abschaltkriterien; keine Annahme `120 mA = Endlage` |
| **KNX006** Referenzfahrt und Position | planned | Individuelle Position 0..100 % per Homing + getrennte Laufzeiten, Persistenz/Uncertainty und Diagnose je M1..M8 | KNX004 + KNX005 | 0/25/50/75/100-%-Tests, Reboot/Unterbrechung/Blocker, immer nur ein Antrieb und fehlersicheres Stoppen |
| **KNX007** Temperaturpfad (grober Altplan) | planned, aufgeteilt | Urspruenglich ATtiny3216/OneWire und UART/SPI bis KNX in einem Slice. **Jetzt Arbeitszerlegung KNX013..016 statt eigener paralleler Implementierung.** | Software-Pin-Audit KNX012; KNX002 nur fuer echten Hardwaretest | Bewertung durch die Einzel-Slices, keine fiktive Abnahme/Schliessung von KNX007 |
| **KNX008** ETS Zone/Channel Design | **closed, 2026-10-12** | Acht Motoren auf bis zu acht Räume gruppierbar; Regelungsmodus `Soll/Ist Temperatur` vs. `0..100%` und korrekte DPTs sowie KNX-Objektnamen festlegen | KNX001 und [ETS-Audit](ETS_PRODUCT_AUDIT.md) | Reviewte Nummer-/Parameter-/DPT-Tabelle, migrationsfaehige Versionierung, C-sichere Identifier; **noch keine Aktivierung im Altprojekt** |
| **KNX009** ETS6 Produkt-/Importtest | **deferred, 2026-10-12** | XML/Header/Producer aktualisieren, versionierte `.knxprod` bauen und isoliert in ETS6 importieren | KNX008 | XML Sanity/Generator, Header-Compile, ETS Import-/GA-Sichttest, Version/Release-Manifest |
| **KNX010** Raum-/Heizkreisregelung | planned | Mehrfachzuordnung M1..M8 zu Zonen, PI-/hysteresebasiertes Raumregeln und direktes KNX 0..100 % inklusive Fault Fallback implementieren | KNX006 + KNX007 + KNX009 | Tests fuer Raum mit 1/2/3/4 Motoren, Sensorfehler, Busausfall, konkurrierende Sollwerte, stabile sequenzielle Fahrten |
| **KNX011** HMI, Integration & Release Gate | planned | LCD/Encoder/Diagnostik integrieren, Strom-/Versorgungs-/ETS-/Motorchecks zusammenfuehren, validierte Version dokumentieren | KNX003..KNX010 | End-to-End ETS-Download/Telegramme, Tests am realen Aufbau, BOM/DRC/QA, Fehlerfälle und Release-Artefakte dokumentiert |

| **KNX012** Software-First Pin-/Protokollplan | **closed, 2026-10-10** | ATtiny/RP2040-Quell- und PCB-Pin-Review, T0 Vorlauf/T1..T8 Ruecklauf, UART-Protokollentwurf und Roadmap | KNX001; Schaltplan/PCB V1.2 und Source-Code | Pin-Audit reproduzierbar, Konzept und Folge-Slices dokumentiert, QA + ASH Close; keine voreilige Hardware-/KNX-Funktionsbehauptung |
| **KNX013** ATtiny nichtblockierender Sampler | **closed, 2026-10-11** | Neun korrekte OneWire-Pins, 12-/11-Bit-Aufloesung, nichtblockierende Messungen und Snapshot mit Valid/Alter/Fehler | KNX012, vorhandener Source; Hardware spaeter fuer Realtest | ATtiny Build/Host-Tests, neun Pins korrekt, gueltiges 0 C und negative T, keine Loop-Blockierung, Timeout/CRC/Sentinel-Tests |
| **KNX014** UART ATtiny<->RP2040 | **closed, 2026-10-11** | USART0 ALT1 PA1/PA2, RP GPIO8/9 Serial2, framing+CRC, GET_SNAPSHOT und Kommunikations-Timeout | KNX013, KNX012 Interface-Contract | Host-Frame-/CRC-/Stale-Tests, Builds beider Targets, gefaehrdungsfreie UART-Simulation; echte Hardware spaeter |
| **KNX015** KNX-Sensordaten MVP | **closed, 2026-10-12** | T0..T8 DPT9.001 ueber RP2040 KNX publizieren, konfigurierbare Mindest-/Zyklusintervalle und Aenderungsschwelle, Status/Fault | KNX014; vorhandene 9 KO, erforderlicher ETS-Minimalvertrag | synthetische neun Temperaturwerte -> KNX-Encoder, keine ungueltigen/stale Telegramme, Throttling, Build; echter Bus noch separat |
| **KNX016** ETS6-Temperatur-Importtest | **deferred, 2026-10-12** | Nur Temperatur-MVP-Produkt versioniert erzeugen, sichere KO-Identifiers und ETS6-Testprojekt-Import/GA-Pruefung | KNX015; OpenKNXproducer vorhanden | Generator/ZIP/Header-Pruefung, ETS6-Import in isoliertes Projekt und 9 Temperatur-KO nachgewiesen; kein produktives KNX-Download |
| **KNX017** KNX-Testbench-Umplanung | **closed, 2026-10-12** | Auf Nutzerwunsch KNX016/KNX009 zurückstellen; eigenständige Testumgebung skizzieren und Softwarearbeit priorisieren | KNX015 abgeschlossen | [KNX-Testbench-Plan](KNX_TESTBENCH_PLAN.md), Roadmap/README und ASH-Gate-4-Audit; kein ETS-/KNX-Test |
| **KNX018** Eigenständige KNX-Testumgebung | planned, Infrastruktur | Dedizierter Testrechner, lokales KNX-IP/USB-Interface, eigener KNX-TP-Testbus und echte Controllerplatine; Testmittel und sicherer Aufbau | KNX002/003 As-built-/Power-Freigaben, passende KNX-Hardware; [Plan](KNX_TESTBENCH_PLAN.md) | Dokumentierter Testaufbau mit geprüftem Versorgungsweg, Schnittstellen-/Busdiagnose und Testprojekt; danach KNX016/009 fortsetzbar |
| **KNX019** PI-Raumregler-Kernsimulator | **closed, 2026-10-12** | Portabler langsamer 8-Zonen-PI, Deadband, Anti-Windup, Slew-Limit, Zeitstempel-/Modus-Sperren und toy-plant Tests; **keine KNX-/Motorfirmware** | KNX008; KNX010 Vollintegration weiterhin von KNX006/007/009 abhängig | [Reglermodell](KNX019_ROOM_PI_SIMULATION.md), Native-Tests inkl. KNX008-Zielwertrouter, ABI- und ASH-Audit ohne KNX/ETS-/Hardwareeingriff |
| **KNX020** Exklusive Motor-Fahrqueue Simulator | **closed, 2026-10-12** | Reiner C++-Simulator: ein Motor-Lease von acht, Start-/Stopp-ACK-Token, Fairness, Stale-Ziele und Safety-/Timeout-Stopps; KEINE H-Brücken-Pins, Motorfahrt oder KNX-Firmware | KNX008, KNX019; KNX004 bleibt separat geplant und benoetigt KNX002/003 vor Hardwarearbeit | [Simulationsdokument](KNX020_MOTOR_QUEUE_SIMULATION.md), 2 Native-Tests inklusive 20k Ticks, ASH-/PCB-/Firmware-Unveraendertheitschecks; keine Hardwarefreigabe |

## Reihenfolge und Sicherheitsabhaengigkeiten

- **Stand 12.10.2026:** KNX012..015 sind als Offline-Software-Slices abgeschlossen. **KNX016 ETS6-Temperaturimport und KNX009 ETS6-Produktimport sind auf Nutzerwunsch deferred**: Ein eigener KNX-Testrechner mit lokalem KNX-Testbus, echter Controllerplatine und geeigneter Schnittstelle soll erst als KNX018 aufgebaut werden. Nicht automatisch auf dem LLO Desktop Agent fortsetzen. [Testbench-Plan](KNX_TESTBENCH_PLAN.md).
- **Naechster zweckmaessiger Hardware-Slice (separat):** KNX002. Ohne Fotos/Bestueckung kann er `blocked` werden; das darf nicht als Erfolg gewertet werden.
- **KNX008/KNX019 sind softwareseitig abgeschlossen; KNX020 ergaenzt eine isolierte Motor-Fahrqueue-Simulation** ohne KNX-/GPIO-/Motor-Hardware. [Fahrqueue-Entwurf](KNX020_MOTOR_QUEUE_SIMULATION.md). **KNX008 und KNX019 sind softwareseitig abgeschlossen**; der rein simulierte PI-Raumregelungskern ist als Offline-Referenzmodell dokumentiert: [KNX019 Doku und Testmodell](KNX019_ROOM_PI_SIMULATION.md). Die produktive KNX-XML, KNX-/Motor-Firmware und alle Hardware-/ETS-Gates bleiben unberuehrt. Der vollstaendige KNX010-Integrationsslice bleibt von KNX006/007/009 abhaengig; KNX009/016 bleiben deferred.
- KNX003 und KNX005 duerfen keine gefaehrlichen Blindversuche mit 5 V/3,3 V, Netzteilen oder Antrieben ausloesen. Stromversorgung, Diodenpfad, Schutz und reale Bestueckung muessen vorher freigegeben sein.
- KNX009 baut nur ein separates Produkt und importiert es zum Test; keine ungepruefte Aenderung am produktiven KNX-/ETS-Projekt.
- Projektrelease nur nach KNX011 oder anderem expliziten Release-Gate, **nicht automatisch beim Abschluss einzelner Slices**.


## Temperatur-MVP zuerst: fachliche Abnahme

- **ATtiny3216**: Temperatur **T0 = gemeinsamer Vorlauf**, **T1..T8 = Ruecklauf Heizkreis 1..8**; die neun OneWire-Sensoren werden zyklisch und ohne blockierende Konversionswarteschleifen erfasst, wobei Qualitaet und Alter im Snapshot festgehalten werden.
- **Transportschicht**: PCB V1.2 hat ATtiny-PA3/SPI-SCK nicht verdrahtet; UART-ALT1 auf PA1/PA2 zum RP GPIO8/9 ist der zu pruefende Zielpfad. Der installierte Core nutzt USART0 standardmaessig auf PB2/PB3. Siehe [Firmwareplan](FIRMWARE_SOFTWARE_FIRST.md) und [statischen Pin-Audit](../tools/audit_temperature_bridge.py).
- **KNX**: T0..T8 als DPT9.001 in ETS; Publikationsintervall, Mindestabstand und Delta-T-Schwelle individuell bzw. global parametrierbar. Sensoralter und Verbindungsverlust loesen Diagnose aus.
- **Spaetere Regelung**: Raumsoll/-ist (externer KNX-Raumfuehler) mit langsamer Positions-PI-Regelung **oder** direkter DPT5.001-Stellwert; Heizkreise sind zu Raeumen gruppierbar. Ruecklauftemperatur ist keine Raumtemperatur, Durchflussveraenderungen anderer Kreise werden nicht blind mit Ruecklauf-Pseudo-PI korrigiert.
- **Motor-Gates bleiben blockierend fuer echte Fahrten**: KNX002/003 Versorgung und Bestueckung, KNX004/005 Sicherheitsabschaltung und INA219-Messung vor KNX006/010.


## Nutzung der Roadmap

- Jeder Slice muss beim tatsaechlichen Start aus diesem Plan als [ASH-Vorlage](reference/ash/SLICE_TEMPLATE.md) unter `docs/slices/_OPEN_KNX###_<SLUG>.md` materialisiert werden.
- Die vier Gates und die jeweils konkreten Scope-/QA-Bedingungen im Marker festhalten.
- Ein bereits laufender Slice wird ueber Session-/Git-Checkpoint und `Next exact action` fortgesetzt.
- Nach Gate 4 nur den geschlossenen Slice in [HISTORY](slices/HISTORY.md) schreiben, Marker entfernen und den Roadmap-Status auf `closed` setzen. **Den Folgeslice nicht nur aus Bequemlichkeit voroeffnen.**

## Historische Arbeiten vor Einfuehrung des ASH-Protokolls

Die Commits `53b308a` (Antrieb/ETS-Konzept), `4fa28c1` (Schaltplan), `0045a45` (PCB/ETS), `c2e4bee` (5-V-Versorgung) bilden eine **bereits dokumentierte Ausgangsbasis**. Sie werden nicht nachtraeglich in fiktive, formal gate-validierte Slices umetikettiert.
