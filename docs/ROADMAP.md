# OpenKNXValveControl - ASH Slice Roadmap

**KNX042 OPEN:** isolated USB-only M1-M8 400-ms motor-LED verification firmware prepared; power/KNX isolation and real LED evidence required before flashing. [Runbook](KNX042_MOTOR_LED_BRINGUP.md).

**KNX041 software fix:** Product temperature bridge UART write-readiness guard changed to boolean readiness after KNX040 real UART confirmation; regression and remaining hardware gate in [KNX041 notes](KNX041_TEMPERATURE_BRIDGE_READY_FIX.md).

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
| **KNX021** Ende-zu-Ende-Mock der Heizkreisregelung | **closed, 2026-10-12** | Vorhandene C++-Klassen KNX019 PI -> KNX008 Zone -> KNX020 exklusive Queue mit rein virtuellem Start/Stop-/Off-Feedback koppeln; Referenzverlust bei Abbruch und Stop-Timeout-Durchreichung pruefen | KNX008, KNX019, KNX020; KNX004-006 physisch weiter planned | [KNX021 Dokumentation](KNX021_END_TO_END_SIMULATION.md), C++ E2E-Regression, nativer Runner, produktive ETS/Firmware/PCB unveraendert, ASH-Gates |
| **KNX022** Statischer Hardware-Preflight V1.2 | **closed, 2026-10-12** | Reproduzierbare PCB-/Schaltplan-/Firmware-Inventur zu R29/U25/F1, TB6612-STBY hardwired HIGH, KNX/USB/U6-Headroom und fehlenden realen ERC/DRC-/Bestueckungsdaten; kein Motor- oder KNX-Test | KNX021 geschlossen, exportierte V1.2-Designquellen; KNX002 physischer As-built weiter geplant | [KNX022 Static Readiness](KNX022_STATIC_HW_READINESS.md), [JSON-Blockerregister](KNX022_STATIC_HW_PREFLIGHT.json), Netzlisten-Guards und Negativtests, explizites BLOCKED-Readiness-Ergebnis |
| **KNX023** RP2040 Software-Regelpfad + Laptop-Handover | **closed, 2026-10-12** | Fail-closed KNX019 PI -> KNX008 Zonen-Intents -> KNX020 exklusive Queue, KNX021 synthetische ACKs nur in Native-Build; auf RP2040 ARDUINO hart Disarmed und keinerlei Motor-GPIO. Separat die echte KNX018 Laptop/USB-UPDI/RTS-Testplanung dauerhaft ablegen | KNX008/019/020/021 und KNX022 static abgeschlossen; KNX002-006 real und KNX018 physisch weiter offen | [Firmware-Softwareintegration](KNX023_FIRMWARE_SOFTWARE_RUNTIME.md), [Laptop UPDI Plan](KNX018_LAPTOP_UPDI_TESTBENCH.md), Native-Hardlock-Tests, isolierter RP2040 Build, ASH-QA |
| **KNX024** ETS-Raum-DPT-/KO-Adapter Offline | **closed, 2026-10-12** | KO36..67 der unveraenderten KNX008-V3-Proposal maschinenlesbar abbinden; externe Raum-Soll/Ist-DPT9.001-Floatwerte und direkten DPT5.001-Stellwert typisiert in KNX023 RAM-Inputs einspeisen, Zeitfenster/Modi/Invalid-Werte/Legacy5.004 streng trennen; KO39..67 RequestedOutput ausschliesslich offline kodieren, keine ETS-V2-Produktmutation | KNX023 Firmware-RAM-Runtime geschlossen, KNX008 JSON Proposal, KNX018 reale Testumgebung offen | [KNX024 Room-KO-DPT-Vertrag](KNX024_ETS_ROOM_INPUT_CONTRACT.md), C++ DPT/End2End und Arduino Hardlock, strikter KO/P-Audit, 13 Negativtests, isolierter RP2040-Build, ASH Gates ohne Hardware |
| **KNX025** Fehlerdiagnose, Software-Wiederanlauf und Stale-/ACK-Sperren | **closed, 2026-10-12** | Portabler KNX024/KNX023-Supervisor: fehlende externe Raumwerte, falsche DPTs, simulated Transportverlust, 2s software-loop deadline, KNX020 mock STOP-/AllOff-ACK-Timeouts; erste Fehlerursache sticky mit Zonenmaske, kein altes Target nach Recovery, nur explizite Quittierung bei frei gegebener virtueller Lease. ATtiny T0..T8-Ausfall als **separate Warnung**, keine Ersatz-Raumlufttemperatur. Reale RP2040-Firmware hat nur passiven, ausgangslosen RAM-Diagnosebeobachter | KNX023/024 geschlossen, KNX018 physischer Laboraufbau weiterhin unvollstaendig, KNX002–006 Hardware nicht qualifiziert | [KNX025 Fault/Recovery](KNX025_FAULT_RECOVERY_DIAGNOSTICS.md), Native-C++ Fehler-/Firmware-Hardlock-Tests, unveraendertes V2-ETS/PCB/ATtiny, isolierter Controllerbuild, ASH-QA |

- **KNX025 offline:** [Fehlerdiagnose und Wiederanlauf](KNX025_FAULT_RECOVERY_DIAGNOSTICS.md) erhaelt synthetische Motor-Leases bis zum ACK, fordert neue Raumdaten nach Quittierung; die RP2040-Produktivfunktion bleibt komplett ohne Motoroutput. KNX004 und echte ETS-Abnahmen bleiben offen.
- **KNX024 offline:** [Raum-DPT9.001-/Stellwert-DPT5.001-KO-Adapter](KNX024_ETS_ROOM_INPUT_CONTRACT.md) verwendet nur geplante V3-KO36..67; aktuelle V2-KO17..24 DPT5.004 bleiben unveraendert. KNX009/016 ETS-/KNX-Realtest bleibt deferred.
- **Laptop KNX018**: [UPDI-/KNX-/RP2040-USB-Aufbauplan](KNX018_LAPTOP_UPDI_TESTBENCH.md) einschliesslich 6-Pin-CN1-Vergleich und sicherem Git-Umzug; im Labor weiterhin nicht aufgebaut. **KNX023** beschraenkt sich auf eine firmware-kompilierbare Software-Runtime ohne Motoroutputs. KNX009/016 bleiben deferred.

## Reihenfolge und Sicherheitsabhaengigkeiten

- **Stand 12.10.2026:** KNX012..015 sind als Offline-Software-Slices abgeschlossen. **KNX016 ETS6-Temperaturimport und KNX009 ETS6-Produktimport sind auf Nutzerwunsch deferred**: Ein eigener KNX-Testrechner mit lokalem KNX-Testbus, echter Controllerplatine und geeigneter Schnittstelle soll erst als KNX018 aufgebaut werden. Nicht automatisch auf dem LLO Desktop Agent fortsetzen. [Testbench-Plan](KNX_TESTBENCH_PLAN.md).
- **KNX022 rein statisch:** [Readiness-Check](KNX022_STATIC_HW_READINESS.md) und [Risiko-JSON](KNX022_STATIC_HW_PREFLIGHT.json) zeigen die Teile-, STBY- und Power-Blocker; **ohne reale Messungen keine Motorfreigabe**.
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


## KNX026 – HMI/Diagnose (Software-Slice, 12.10.2026)

KNX026 wurde auf der KNX025-Basis fuer eine rein lesende [portable HMI und Diagnose](KNX026_HMI_DIAGNOSTICS.md) umgesetzt. Sie zeigt T0..T8 (Wasser, nicht Raum), gueltige externe Raumsoll-/-istwerte, PI und direkte Prozentvorgabe, Zonen-/Motorzuordnung, virtuelle Ziel-/Positionswerte nur aus der Hostsimulation, KNX025-Faults und getrennte Kommunikationsqualitaet; in echter Firmware nur passive RAM-Beobachtung. Ein Display-/Encoder-Hardwaretreiber und alle unabhaengigen Motor-Safety-Gates bleiben offen. **KNX011 ist damit nicht abgeschlossen.**


## KNX027 – USB-Firmware-Upload (softwareseitig, 12.10.2026)

**KNX027 closed (Host-Software only):** [USB-Auto-Upload/Recovery](KNX027_USB_FLASH_AUTOMATION.md) legt picotool fuer RP2040-PlatformIO fest, liefert ein bewusst gesperrtes USB-CLI (probe/plan/build/upload), validiert exakte COM-/VID:PID- und Git-HEAD-Zuordnung und baut den Controller in einem isolierten Verzeichnis. Acht synthetische Tests, Plattform-/ASH-Audit und echter isolierter Controllerbuild gehoeren zum Software-Gate. **KNX018 bleibt fuer den erstmals echten USB-Flash/1200-Baud-Reset, KNX/IP/ETS, Chip-/Power-Verifizierung offen**; KNX002–006 Motor-Safety, KNX009/016 ETS6 weiterhin deferred. Kein GitHub-Push oder USB-Gerateflash.


## KNX028 – LLO Home Bootstrap (13.10.2026)

Die Entwicklung wechselt auf den synchronisierten **LLO Home Agent** mit Repo `C:\_myspace\workspace\open-knx-valve-control`. [Offline-Initialisierung](KNX028_LLO_HOME_SETUP.md) und [Host-Checks](../tools/home_offline_check.ps1) dokumentieren System-/Git-/Python-/PlatformIO-Abhaengigkeiten, Mock-USB-Checks und Hardware-Sperren. Ein RP2040/ATtiny-Offlinebuild kann bestanden haben, ohne dass USB, KNX, ETS oder die Motor-Stromversorgung freigegeben sind. Der Teststand KNX018 und Hardware KNX002-006 bleiben separat offen.


**KNX028 Software-Gate (13.10.2026):** Der LLO Home Host ist mit gepinntem PlatformIO/RP2040-GCC14, OpenKNXproducer 3.12.2 sowie eigenem nativen WinLibs-g++ eingerichtet. ATtiny3216-Isolationsbuild sowie RP2040-Isolationsbuilds PASS, USB-Mock-Tests 8/8 und native Testgruppen 11/11 PASS; Details, Checkpoints und Reproduktionsbefehle stehen in [KNX028 Home Setup](KNX028_LLO_HOME_SETUP.md). Das zuvor auf Home aufgetretene `__getreent`-Problem mit GCC16.1.0 ist durch die gepinnte GCC14.3.0-Toolchain behoben. **Alle realen Hardware-/ETS-Gates unveraendert offen.**


## KNX029 – Erstkontaktpaket und Inbetriebnahmereihenfolge (13.10.2026)

[KNX029 Runbook](KNX029_FIRST_CONTACT_RUNBOOK.md) bereitet auf LLO Home **ohne angeschlossene Platine** ein versionsgebundenes Zwei-Controller-Firmwarepaket und Gate-Protokoll für den späteren KNX018-Teststand vor. `tools/knx029_prepare_bringup.py` mit `plan`, `build`, `verify` ist offline; der Build erzeugt nur Kandidaten und fordert sauberes Git/volle Commit-SHA. Die tatsächlich bestückte U25-Signatur, die 16-MiB-Flash-Annahme, UPDI-Pegel/CN1.1 und USB-/KNX-Rückspeisung sind bei KNX002/003/018 zu prüfen; KNX004–006 Motoren, KNX009/016 ETS6 verbleiben offen.

**KNX029 Softwareabschluss (13.10.2026):** Der Home-Offline-Doppelbuild ist abgeschlossen und mit SHA256 verifiziert: [Erstkontaktpaket und Gate-Plan](KNX029_FIRST_CONTACT_RUNBOOK.md). RP2040-UF2/ELF und konfiguriertes ATtiny3216-HEX/ELF liegen als Buildkandidaten unter `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX029-b016a16-v1`; 14/14 isolierte Bundle-Sicherungstests inklusive geloeschtem PlatformIO-Buildverzeichnis PASS. Noch keine fertig angeschlossene Platine; echte USB-/UPDI-/KNX-/ETS-/Motor-Gates gesperrt.

## KNX030 – LLO Home First-Contact OS-Inventur (13.10.2026)

[Passive Geräte-Inventur](KNX030_PASSIVE_FIRST_CONTACT.md): Windows PnP/USB/COM, RPI-RP2-Volume-Label und lokale Netzwerklinks lassen sich auf LLO Home softwareseitig lesen und zwischen zwei Snapshots vergleichen, ohne COM, UPDI, KNX/IP oder Motoren anzusprechen. Vorab-Baseline außerhalb Git dokumentiert (15 USB/Port-Kandidaten, kein RPI-RP2-Laufwerk, 21 lokale Netzwerkadapter); Geräteserien aus PnP-Instanzen werden nur gehasht gespeichert. Der später sichtbare neue Eintrag ist ein *Kandidat*, nie eine Flash-/KNX-/Motorfreigabe. KNX002..006, KNX018 und ETS6-Prüfung bleiben unabhängig offen.

## KNX031 – KNX014 UART-Trace-Diagnose offline (13.10.2026)

[KNX031 UART-Runbook](KNX031_UART_TRACE_OFFLINE.md) ergänzt KNX029/030 um einen read-only Host-Decoder für **gespeicherte** KNX014-UART-Rohdaten und native C++-Golden-Vektoren. Der Decoder validiert CRC, Framing, Uptime, 9 Temperaturkanäle, Flags/Faults und markiert Zeit-/Richtungs-/Online-Aussagen ausdrücklich als unbekannt. Das gemeinsame Firmwareprotokoll, ETS, PCB, Upload und Motorsteuerung bleiben unverändert. Reale UART-/USB-/KNX-/ETS-Gates erfordern weiterhin eine geprüfte Platine.

## KNX032 – Offline-End-to-End UART/KNX-Mock (13.10.2026)

Mit [KNX032](KNX032_UART_TO_KNX_OFFLINE.md) ist die bisherige Luecke zwischen KNX031-UART-Rohdatenpruefung und produktivem KNX015-TemperaturePublisher unter einem **C++-Hosttest** geschlossen: Protokollbytes aus dem echten KNX014-Codec durch echte `TemperatureBridge`-/`TemperaturePublisher`-Quellen bis zu in-memory KO25–35. Der Test prueft DPT, neun Kanäle, negative/0-Grad-Werte, Offline/Faults, P19, KNXMock-Gap sowie CRC/Sequenzfailclosed, ohne ESP/ETS/USB-/Motorhardware. KNX002–006/018 bleiben offen, KNX009/016 ETS6 deferred.

## KNX033 – As-built Foto- und Prepower-Gates (13.10.2026)

[KNX033 Foto-/Netzreview](KNX033_AS_BUILT_PCB_REVIEW.md) dokumentiert die erste reale V1.2-Bestueckungsseite, JMP1/2/3 sowie den D1-Draht-Bypass. **Foto-F1 T 2,5 A** weicht von der Quelle (**630 mA**) ab; D1 spart zwar den Vorwaertsabfall, verliert aber die Rueckstromsperre. U6 auf der gezeigten Seite nicht zweifelsfrei identifizierbar, Rueckseitenfoto fehlt; U25-Markierung TINY3216 wahrscheinlich, R29-Wert offen. [Strukturierte, rein fotografische Evidenz](KNX033_AS_BUILT_PREFLIGHT.json), Messfelder null, Power-/USB-/KNX-/UPDI-/Motor-Gates false. KNX002–006, KNX018 bleiben hardwareseitig gesperrt.

## KNX034 – USB-only ohne KNX-Versorgung, Rueckseiten-Foto (13.10.2026)

Die Rueckseite zeigt U6 als real bestueckten schwarzen Baukoerper an der Stelle `U6` nahe 5V-/3.3V-Markierungen, aber ohne lesbare exakte Typaufschrift. [KNX034 Vorabnahmekonzept](KNX034_USB_ONLY_PREPOWER_GATE.md): **JMP1 Oeffnung nur vorgeschlagen, NICHT ausgefuehrt**; trennt V1.2-Netz `KNX_VCC` von `R9_2` am MOSFET Q1, nicht alle Masse-/Rueckspeisungswege. Bereits bei **komplett abgetrenntem KNX** ist USB die einzige externe Quelle; erst nach stromlosen JMP1/D1-Pruefungen und korrekter F1-Schutzwahl wird ein separat freizugebender USB-only-Gate diskutiert. D6-Drop bleibt und TSR benoetigt >=4,75 V am tatsaechlichen VIN-Pin. [Maschinenlesbarer BLOCKED-Status](KNX034_USB_ONLY_PREFLIGHT.json). Keine Power-/Flash-/KNX-/Motorfreigabe.

## KNX035 – kritischer R17/STKNX-TX-Startzustand (14.10.2026)

**P0 Designfehler im V1.2-Layout:** R17 ist ein 10-kΩ-Pull-up nach 3,3 V auf U9 STKNX KNX_TX, doch nach dem offiziellen ST-Datenblatt ist **LOW Bus-Idle**, HIGH nur 35-µs-Sendepuls. Ein RP2040 mit high-Z-Pin kann so beim 5-V-Zuschalten U11/R68 dauerhaft belasten. Der Nutzer hat U11 **als 68 Ω real bestueckt** gemeldet (PCB-MPN 3,5 mΩ ist ein Metadatenfehler) und eine echte U11-Überhitzung am KNX-Bus beobachtet. [KNX035 Source-/Risiko-Abgleich](KNX035_STKNX_TX_IDLE_HAZARD.md) trennt diesen Hardwarebias von **unpassendem TPUart-Serial1-Backend** (normaler UART mit Idle HIGH statt direkter STKNX-Pulse). ECO V1.3: Pull-up entfernen; **4,7–10 kΩ KNX_TX -> GND** auf neuer Netzzuordnung und fail-LOW-Sendegate, STKNX-konformer KNX-Treiber statt normalem UART. V1.2-Nacharbeit R17 stromlos entfernen, aber **kein direkter Bus-Retest**, U9/U11 nach Übertemperatur als ungeprueft behandeln. [Unverifizierte physische Gates](KNX035_STKNX_TX_HAZARD.json); KNX002..006 und KNX034-F1/D1-Power-Gates bleiben offen.

## KNX036 – LLO Desktop USB/COM First Contact (14.10.2026)

19 von Home unveröffentlichte Commits wurden per sicherem SHA256-geprüftem Git-Bundle direkt in den sauberen Desktop-Klon fast-forward übernommen, ohne GitHub-Push. [KNX036 Runbook](KNX036_DESKTOP_USB_FIRST_CONTACT.md) enthält erste **passive Windows-Geräte-Baseline**: COM1/COM3 sind PC-interne Ports; kein RP2040/CH340G, auch beim zweiten Scan keine neuen USB-/COM- oder RPI-RP2-Einträge. [Isolierte RP2040-USB-CDC-Diagnose](../tools/knx036_usb_diag/platformio.ini) mit nach Setup LOW gehaltenem GPIO0 KNX_TX, ohne KNX, UART1, Motoren; **Offline-PlatformIO-Build SUCCESS**, UF2/ELF+SHA256-Manifest im Desktop Builds-Ordner (kein Upload). [Statische Vertragsprüfungen](../tools/test_knx036_usb_diag.py) 8/8 PASS. Das ursprüngliche Controller-KNX-Image bleibt wegen TPUart-UART/KNX035 gefährlich. Hardware-R17, F1, D1, UPDI-CN1 und unabhängige Motor-Gates bleiben offen. Für reale nächste Identifikation zuerst CH340G USB-Adapter **ohne Verbindung zu CN1** am Desktop erkennen; separater RP2040-USB-Power-Test erst nach fachlicher Strombegrenzungs-/3,3V-Gate.

## KNX037 – erste reale RP2040-Hardwareabnahme USB/Flash (14.10.2026)

[KNX037 Live-Protokoll](KNX037_DESKTOP_LIVE_USB_AND_UPDI.md): Nach User-Auftrag wurden COM5 RP2040 (VID2E8A:PID00C0) und COM4 CH340 (VID1A86:PID7523) am LLO Desktop erkannt. ROM-Reset via 1200 Baud und DTR-Puls **ohne BOOTSEL-Taste**, RP2040 B2 und **16 MiB Flash real ausgelesen**, KNX036-only UF2 auf RP2040 geschrieben/100%-verifiziert, Neustart auf **COM7 / 2E8A:000A** und mehrere USB-CDC-Heartbeats PASS. Das [neue KNX037-CLI](../tools/knx037_rp_usb_workflow.py) verhindert ungesicherte Uploads, COM4-Missbrauch und zufaellige Device-Auswahl. ATtiny-UPDI bleibt **blocked**: Units-RTS=true/DTR=true verifiziert als Programmiermodus, jedoch USB-VCC-Programmer-MUX vs. ValveControl ATtiny 3,3V, CN1 Pin1=5V und fehlende Signatur nicht gemessen. Kein `pymcuprog` auf COM4 ausgefuehrt. KNX_TX U9/R17, F1, D1 und Motor/KNX-Gates weiter offen.

## KNX038 – ATtiny-UPDI-RTS elektrischer Gate und Offline-HEX (14.10.2026)

[KNX038 Analyse](KNX038_UPDI_RTS_ELECTRICAL_GATE.md) vergleicht Units **Programmer v1.2** (CH340 COM4 VID1A86:PID7523, SN74LVC1G3157 U2/U7 auf USB-VCC, Umschaltung per RTS=True/DTR=True, Programmer CN1 Pin3 UPDI) mit ValveControl V1.2 (U25=3.3V, CN1 Pin1=5V/Pin3 UPDI). Die Nutzerangabe „Programmer sollte angeschlossen sein“ ist kein Pinbelegungs-/Pegeltest; die UPDI-Leitung und alle MUX-Ausgangspegel sind derzeit unbekannt. Der `pymcuprog`-UART-Treiber setzt beim oeffnen ein UPDI BREAK ab und PySerial haelt RTS/DTR ueblicherweise True; das ist **nicht rein lesendes COM-Probing**. **Erfolgreicher offline Build der ATtiny3216-Temperature-Firmware** und HEX+SHA256-Manifest, aber Signatur und Flash weiterhin aus Sicherheitsgruenden ungeprueft. [Failclosed Preflight-CLI](../tools/knx038_updi_readiness.py) und 14 Negativtests; read-only 3216-Signatur (erwartet 1E9521 vs 1616 1E9421) erst nach Pegel-/CN1-Belegungsfreigabe. KNX- und Motorblocker unveraendert.

## KNX039 – Live UPDI ATtiny3216 Signatur und bestehender Flash gesichert (14.10.2026)

[KNX039 Protokoll](KNX039_LIVE_UPDI_READBACK.md) und [read-only Evidenz](KNX039_UPDI_READBACK_EVIDENCE.json): Benutzer bestaetigte bisher getesteten verbundenen Programmer und gab Lesen frei. LLO Desktop `pymcuprog --device attiny3216 --tool uart --uart COM4 ping` **Exit0, `Ping response: 1E9521`** = realer ATtiny3216. Weitere nur lesende UPDI-Aufrufe: **Flash 32.768 B**, **EEPROM 256 B**, **Fuses 9 B**, **USERROW 32 B**, Intel HEX Checksums PASS und lokale SHA256-Backups unter Desktop Builds KNX039 (nicht Git). 1.888 Flash-Bytes ungleich FF; EEPROM + USERROW FF; **8.450 definierte Byte-Differenzen** zum vorbereiteten, NOCH NICHT geflashten Temperature-Build. [8 statische Integritaetstests](../tools/test_knx039_live_readback.py) PASS. Fuer den naechsten Schreibschritt die Backup-Files erhalten, Typ strikt per 1E9521 pruefen und keine blindes `pio -t upload` (enthielte erase). Spannung CN1.3 bei RTS und CN1.1 Rueckspeisung weiterhin nicht instrumentell gemessen; KNX/Motor blockiert. **Real USB/UPDI-Leseweg jetzt nachgewiesen; keine NVM-Schreibfreigabe daraus ableiten.**

## KNX040 – ATtiny3216 real geflasht, 9-Kanal-UART-KNX014 real bewiesen (14.10.2026)

[Live-Abnahme](KNX040_REAL_TEMPERATURE_UART.md) und [Evidenz JSON](KNX040_LIVE_TEMPERATURE_UART_EVIDENCE.json): ATtiny3216 \`1E9521\` über COM4 mit der neuen Firmware \`8655B\` geflasht und \`pymcuprog --verify\` PASS, zusätzlich unabhängiger kompletter Flash-Readback **0 Unterschiede**, Fuses und EEPROM unverändert. Separates [RP2040-UART1-Testimage](../tools/knx040_uart_diag/platformio.ini) über ROM-USB und picotool 100% verifiziert (COM7); knx014 CRC16-Snapshot T0–T8 echte **8/8** und weitere **5/5** PASS, keine Timeouts/CRC-Rejects. **9/9 NoSensor** je Antwort korrekt, da Nutzer noch keine DS18B20 angeschlossen hat; keine erfundenen °C-Werte. Read-only [USB-Monitor](../tools/knx040_capture_uart.py) für Sensor-Nachmontage bereit. Aus echtem Test entdeckt: Arduino-Pico \`SerialUART::availableForWrite()\` liefert 0/1, daher <8 unterdrückt alle Requests. Im isolierten RP2040-Diagnoseimage auf \`<=0\` behoben; **P0 Folge-TODO** in \`src/controller/temperature_bridge.cpp\` die gleiche Fehlerprüfung nach eigener Scope-Freigabe korrigieren (altes MCU-Produktivimage aufgrund KNX035-STKNX/TPUart weiterhin gesperrt). Hardware-F1/D1 und Motor/KNX-Gates bleiben offen.
