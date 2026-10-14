# Open KNX Valve Control

Controller for up to **eight motorized underfloor-heating valve actuators** with KNX integration. This repository contains firmware, KNX product-description sources, electronics schematics/PCB exports and DIN-rail enclosure models.

> **Project status (2026-10-12):** KNX013/014 collect nine ATtiny 1-Wire temperatures and deliver CRC-checked UART snapshots to RP2040; KNX015 now implements **ETS-parameterized KNX DPT9.001 telemetry** (KO25..33) and two quality-diagnostic objects (KO34/35) with validity checks and throttling. Native tests, isolated RP2040 build and product generation pass. **No real-board UART/KNX/ETS6 import, real motor positioning, or live room regulation have been tested. KNX008/019/020/021 implement the previously independent portable zone, PI, exclusive motor-lease and virtual feedback models. KNX023 now links the PI/zone computation into the actual RP2040 firmware at a RAM-only 100ms cadence; the real ARDUINO build has NO motor-event backend, NO motor-GPIO path and blocks synthetic arming by compilation. External room KNX inputs and real actuator commands have NOT been connected.** This document separates offline evidence from requirements and hardware gates.

> **Teststatus:** Auf Wunsch wurde **KNX016/KNX009 (ETS6-Import und reale KNX-Abnahme) zurückgestellt**. Der Test soll später auf einem **eigenständigen, mit KNX-Schnittstelle und der Platine verbundenen Labor-Testplatz** stattfinden, nicht als Endabnahme auf dem LLO Desktop Agent. **KNX008 (Zonenmodell), KNX019 (PI-Regler), KNX020 (Exklusiv-Queue) sind offline abgeschlossen; KNX021 prüft erstmals den gemeinsamen Pfad mit virtuellem Motorfeedback und Stopp-Fehlern.** KNX023 integriert ausschliesslich die **hardwareinaktive Softwareberechnung** in die Controller-Firmware, **nicht** KNX-Raumtelegramme oder Motorhardware. KNX016/009 bleiben zurückgestellt. [Testbench-Konzept](docs/KNX_TESTBENCH_PLAN.md) und [Zonen-Entwurf](docs/KNX008_ZONE_CHANNEL_DESIGN.md).

## ASH Project Workflow v1 (verbindlich)

Dieses Projekt arbeitet nach dem **ASH Slice-Konzept** aus dem ChatGPT-Space `/ASH`. **Project** ist der dauerhafte Repository-Zustand, **Slice** ein pruefbares Arbeitspaket, **Session** ein austauschbarer Chat/Agent-Lauf. Ein Slice darf mehrere Sessions ueberleben; die zentrale Quelle fuer aktuellen Projektfortschritt bleibt das Repository, **nicht** der Chatverlauf.

**Standard:** genau **ein aktiver Write-Slice**, markiert durch `docs/slices/_OPEN_<ID>_<SLUG>.md`. Ein Slice durchlaeuft **Gate 1 Checkup/Analysis -> Gate 2 Decision/Plan -> Gate 3 Implementation -> Gate 4 Validation/Commit/Close**. Vor jedem Write Session-/Gitstatus, offene Slice-Marker, Quarantaene fremder Aenderungen und Baseline pruefen. Beim Schliessen `docs/slices/HISTORY.md` ergaenzen und den offenen Marker im Closing-Commit entfernen. **Naechsten Slice nicht automatisch starten.**

- [Projektkonfiguration](.ash/project.yaml) | [projektlokale ASH-Regeln](.ash/WORKFLOW.md)
- [Slice Roadmap & Abnahmeziele](docs/ROADMAP.md) | [Slice- und Recovery-Anleitung](docs/slices/README.md) | [History geschlossener Slices](docs/slices/HISTORY.md)
- [Alle sieben originalen ASH-v1-Workflowquellen (vollstaendig, mit Herkunft)](docs/reference/ash/README.md) - darunter [Slice-Protokoll](docs/reference/ash/SLICE_PROTOCOL.md), [Vorlage](docs/reference/ash/SLICE_TEMPLATE.md), [Recovery/Handoff](docs/reference/ash/RECOVERY_HANDOFF.md) und [Quell-Hash-Manifest](docs/reference/ash/MANIFEST.sha256)
- **Checks:** `python tools/audit_ash_workflow.py` fuer Referenzen, ASH-Regeln und Markdown-Links; `python tools/audit_design.py` fuer die bestehende statische KNX-/PCB-/ETS-Baseline

**KNX025 Software-Faults:** [Faultsupervisor/Recovery-Dokumentation](docs/KNX025_FAULT_RECOVERY_DIAGNOSTICS.md) beschreibt den simulierten KNX-Raum-Input-/Zeit-/ACK-Faultpfad mit sticky Alarm, expliziter ACK-Recovery und der separaten, nicht sperrenden ATtiny-Verteilertelemetrie-Warnung. RP2040 besitzt weiterhin nur einen **passiven** RAM-Diagnosebeobachter: keine V3-KO-Live-Bindung, kein echter Motor-Watchdog und kein kontrollierbares TB6612-STBY auf V1.2.

**KNX024 ETS-Datentypen:** [Offline-KO-Adapter](docs/KNX024_ETS_ROOM_INPUT_CONTRACT.md) testet den KNX008-Vorschlag KO36..67, DPT9.001, DPT5.001, Timeouts und Konfigurationswechsel, ohne echte V3-ETS-KOs zu publizieren. Legacy KO17..24 bleiben DPT5.004, Motoren bleiben gesperrt.

**Laptop-Plan:** [KNX018](docs/KNX018_LAPTOP_UPDI_TESTBENCH.md) beschreibt das separate LLO-Laptop-Agent/KNX-IP/USB-RP2040/CH340G-RTS-UPDI/Test-Sensor-Setup einschliesslich CN1.1-5V-Rueckspeisepruefung. Der Desktop behaelt die ungepushten Commits, der Laptop ist noch nicht umgezogen. [KNX023](docs/KNX023_FIRMWARE_SOFTWARE_RUNTIME.md) integriert die Software-PI-/Queue-Modelle in die RP2040-Firmware **mit ARDUINO-Hardlock gegen jegliche Motorfreigabe**. KNX024 besitzt einen Offline-ETS-Raumeingangsadapter, aber weiterhin **KEIN LIVE ETS-/KNX-Raumeingang** und keinen echten Motor-Output.

**Hardware-Readiness:** [KNX022](docs/KNX022_STATIC_HW_READINESS.md) prueft die V1.2-Netze und Teile-Attribute reproduzierbar. Die bestueckte Platine bleibt wegen offener R29-/U25-/F1-, STBY-/Versorgungs- und ERC/DRC-Nachweise **NICHT zum motorischen Betrieb freigegeben**. Dies schliesst die physischen KNX002/003/004/005/006-Gates nicht ab.

**Aktueller Arbeitsfortschritt:** Unter `docs/slices/_OPEN_*.md` steht nur der tatsaechlich gestartete Slice; ansonsten gilt die [Roadmap](docs/ROADMAP.md) als Plan, nicht als Implementierungs- oder Hardwarefreigabe. Vorherige commits `53b308a` .. `c2e4bee` sind historischer Baseline-Stand, nicht rueckwirkend formal geschlossene Slices.

## Documentation

- [Architecture and verified project inventory](docs/ARCHITECTURE.md)
- [Software-first: zwei Firmwares, ATtiny/RP2040, OneWire/UART und KNX-MVP](docs/FIRMWARE_SOFTWARE_FIRST.md)
- [KNX013: ATtiny nonblocking temperature sampler – implementation and tests](docs/KNX013_ATTINY_SAMPLER.md)
- [KNX014: UART bridge, framed nine-sensor snapshots, CRC, tests](docs/KNX014_UART_BRIDGE.md)
- [KNX015: ETS-parametrisierte KNX-Temperaturtelegramme T0..T8 und Diagnosen](docs/KNX015_TEMPERATURE_PUBLISH.md)
- [KNX008: vorgeschlagene 8-Zonen-/8-Motoren-Zuordnung, Moduskontrakt und Native-Tests](docs/KNX008_ZONE_CHANNEL_DESIGN.md)
- [KNX019: simulierter PI-Raumtemperaturregler, 8-Zonen-Bank, Sensor-Failsafe und Modelltests](docs/KNX019_ROOM_PI_SIMULATION.md)
- [KNX020: Exklusive Motor-Fahrqueue, nur native Software-Simulation mit Start/Stop-Quittungen](docs/KNX020_MOTOR_QUEUE_SIMULATION.md)
- [KNX021: Durchgängige PI-zu-Motorfeedback-Simulation mit Abbruch-/Stopp-Faults](docs/KNX021_END_TO_END_SIMULATION.md)
- [KNX022: statischer Hardware-Preflight V1.2, BOM-Konflikte, Motorversorgung nicht freigegeben](docs/KNX022_STATIC_HW_READINESS.md)
- [KNX023: RAM-only RP2040-Raumregelungs-Runtime, ARDUINO-Armierung gesperrt](docs/KNX023_FIRMWARE_SOFTWARE_RUNTIME.md)
- [KNX024: typisierter Offline-ETS-Eingangsadapter fuer KNX-Raumwerte DPT9.001 und Direktstellwerte DPT5.001, KOs36..67 vorgeschlagen](docs/KNX024_ETS_ROOM_INPUT_CONTRACT.md)
- [KNX025: Software-Fehlerdiagnose, sticky fault, Stoppquittung und kontrollierter Wiederanlauf ohne Motorhardware](docs/KNX025_FAULT_RECOVERY_DIAGNOSTICS.md)
- [KNX018: geplanter Laptop-Teststand mit KNX/IP, RTS-UPDI/UART, RP2040-USB, DS18B20 und M1](docs/KNX018_LAPTOP_UPDI_TESTBENCH.md)
- [KNX-Hardwaretest auf eigenständige Laborumgebung verschoben: Testbench-Konzept](docs/KNX_TESTBENCH_PLAN.md)
- [Schematic V1.2 electrical review and open findings](docs/SCHEMATIC_V1_2_REVIEW.md)
- [5-V-Externversorgung, Jumper und KNX-Leistungsbudget](docs/POWER_SUPPLY_CONCEPT.md)
- [PCB V1.2 static layout/pad audit](docs/PCB_V1_2_AUDIT.md)
- [Verified HmIP-VDMOT actuator specification](docs/ACTUATOR_HMIP_VDMOT.md)
- [ETS application, heating zones and regulation concept](docs/ETS_AND_CONTROL_CONCEPT.md)
- [Actual ETS product XML and OpenKNXproducer audit](docs/ETS_PRODUCT_AUDIT.md)
- [Legacy (potentially outdated) BOM and component list](.github/README.md)

## Hardware and source material

| Topic | Repository files | Notes |
| --- | --- | --- |
| Main board schematic V1.2 | [PDF](schematic/sch_knx-valve-control_v1.2.pdf), [JSON](schematic/sch_knx-valve-control_v1.2.json) | PDF visually reviewed (one sheet); see [electrical findings](docs/SCHEMATIC_V1_2_REVIEW.md) |
| Main board PCB V1.2 | [JSON](schematic/pcb_knx-valve-control_v1.2.json) | Four-layer pad/net static audit documented; no formal DRC or physical validation |
| UPDI programmer V1.4 | [PDF](schematic/sch_updi_programmer_v1.4.pdf), [schematic JSON](schematic/sch_updi_programmer_v1.4.json), [PCB JSON](schematic/pcb_updi_programmer_v1.4.json) | Separate programmer, not main-board revision |
| RP2040 controller | [main.cpp](src/controller/main.cpp), [configuration](src/controller/config.hpp) | KNX startup currently present |
| ATtiny3216 temperature unit | [main.cpp](src/temperature/main.cpp), [configuration](src/temperature/config.hpp) | Separate temperature acquisition firmware |
| ETS product source | [XML](assets/open-knx-valve-control.xml), [sensor XML](assets/Sensor.xml), [generated header](include/knxprod.hpp) | Existing artifacts; not proof of a released/import-tested .knxprod |
| DIN-rail enclosure | [3D models](assets/3d-models/knx-value-control/) | FreeCAD/STL |

Tooling: PlatformIO (Arduino/C++17), RP2040 (Earle Philhower core, OpenKNX stack), ATtiny3216. KNX ETS6 v6.4.1 has been detected on the LLO Desktop computer, but no new application package was built or imported during this documentation pass.

## Functional target

Every physical actuator is individually assignable to a room/heating zone, and a zone may combine **one or several heating circuits**. A room can use one of two configurable control modes:

1. **Room temperature:** KNX setpoint and measured room temperature; one control output shared by all actuators assigned to the zone.
2. **Direct opening:** KNX position demand from **0 to 100%**, without a temperature-controller calculation.

The actual actuator is now identified as **Homematic IP HmIP-VDMOT (153309A0, Amazon ASIN B07RJZ5F1Y)**. The manufacturer specifies **3.3 V DC SELV**, **120 mA maximum current consumption** and **4.3 +/- 0.3 mm mechanical stroke**. The 120 mA specification is **not a verified current-based end-stop threshold**: INA219 traces from the real valve installation are needed. The controller concept can drive **only one motor at a time**. After a reference closing run, travel time maps demanded percentage to an estimated position. Configurable full-stroke timing, timeout, current thresholds and re-reference policy are necessary. Do **not** treat time-derived position as an absolute encoder measurement.

Detailed behavior, ETS parameter tables, safety behavior, scheduling and open design decisions are in [the control concept](docs/ETS_AND_CONTROL_CONCEPT.md).

## Power supply: OPEN DECISION

The V1.2 board currently derives 3.3 V from KNX or USB. The project owner is considering a **dedicated external isolated 5 V SELV supply** because the STKNX 150 mA **buck-output** rating (distinct from the 30 mA KNX-bus extraction) may not cover the full board plus a 3.3 V / 120 mA actuator. This is **not yet measured**.

**No 5 V may be applied to a 3.3 V motor or to `M_VCC`.** Board V1.2 includes solder jumper `JMP1` for the KNX power path (not a ready external input), two Schottky diodes in the USB-to-U6 path, and a TSR 1-2433 requiring **at least 4.75 V at its own input**. Read the actual jumper/pad map and two proposed external-supply architectures in [POWER_SUPPLY_CONCEPT.md](docs/POWER_SUPPLY_CONCEPT.md) before modifying hardware.

## Prioritaet: Firmware und KNX-Temperatur-MVP

Zuerst nur die **neun Temperaturen** T0 (Vorlauf) und T1..T8 (Ruecklaeufe der Heizkreise) ermitteln und auf den KNX-Bus bringen. Die [Software-first-Planung](docs/FIRMWARE_SOFTWARE_FIRST.md) trennt ATtiny3216 (zyklischer, nicht-blockierender OneWire-Snapshot) und RP2040 (UART-Abruf, KNX-Senden und spaeter Raum-/Motorregelung). Die **ATtiny-Pins sind in KNX013 korrigiert**, das ungeroutete SPI0 ist deaktiviert, und die **UART-Bruecke KNX014** wurde in beide Firmware-Targets integriert. [ATtiny-Sampler](docs/KNX013_ATTINY_SAMPLER.md) und [UART-Protokoll](docs/KNX014_UART_BRIDGE.md) sind offline gebaut und mit simulierten Sensor-/UART-Daten getestet. Der [Pin-/Protokoll-Audit](tools/audit_temperature_bridge.py) besteht fuer den gesamten UART-Scope. **Echte UART-Hardwaretests und KNX-Temperaturtelegramme stehen aus.**

Fuer die ASH-Abfolge siehe [ROADMAP](docs/ROADMAP.md): **KNX013/014/015 Software-Pfad implementiert und offline getestet**. Der naechste geplante Slice KNX016 prueft ETS6-Import, Sichtbarkeit und Nummerierung des Testprodukts. Alle realen KNX-/UART-Hardwaretests bleiben eigenstaendige Gates. Reale Motorfahrten bleiben gesperrt, bis die Hardwareversorgung/INA219-Safety-Gates erfuellt sind.

## Next steps

1. Validate the identified HmIP-VDMOT's wiring polarity, 3.3 V motor rail under load, running and end-stop current profiles, full travel time and installed valve's effective hydraulic opening.
2. Reconcile [V1.2 schematic review findings](docs/SCHEMATIC_V1_2_REVIEW.md) with actual PCB assembly: R29 shunt value/MPN, U25 MCU marking, STKNX power budget, motor output polarity, current sensor and nine sensor ports.
3. Address the [existing ETS product audit](docs/ETS_PRODUCT_AUDIT.md): extend the eight motor objects into zone-based configuration, decide DPT 5.001 versus 5.004, fix invalid generated Ko macro names, and repeat KNX product generation.
4. Prototype safe single-motor arbitration, current-limited endpoint learning and movement timing with real hardware.
5. Implement positioning, feedback and error handling, then temperature-controller mode and room grouping.
6. Import-test the isolated KNX product generation candidate in ETS6, validate group objects, then verify telegrams end-to-end when hardware is ready.

**Audit status:** PCB und Schaltplan unveraendert. **KNX015** hat die ETS-XML auf ApplicationVersion 2 erweitert (KO1..33 unveraendert nummeriert, neu KO34/35 und P20/P21) sowie [knxprod.hpp](include/knxprod.hpp) reproduzierbar regeneriert. [Preservation-Audit](tools/audit_knx015_product.py) prueft die historische ETS-ABI; [isolierter RP-Build](tools/build_controller_isolated.py) hat die Quell-Header nicht implizit veraendert. Keine Hardware geflasht, keine Motoren bewegt. Run the standard-library-only static checks with `python tools/audit_design.py`. A test `.knxprod` was generated **outside the repository**; no ETS6 import or firmware build is claimed.


## KNX026 – Read-only HMI/Diagnose (12.10.2026)

Die [KNX026-HMI-Dokumentation](docs/KNX026_HMI_DIAGNOSTICS.md) beschreibt das neue portable Anzeige-/Menue-Snapshot-Modell fuer T0/T1..T8, Raum-/Heizkreis-Zuordnung, PI/Direktvorgaben, KNX025-Faults, Offline-/Alterdiagnose sowie getrennte synthetische und unbekannte reale Motorposition. Der RP2040 sampelt die Daten ausschliesslich passiv im RAM. Die V1.2-HMI-Pins sind bekannt, ein getesteter LCD-Treiber/physischer Encoder jedoch nicht. **Keine Motorfreigabe, kein physischer LCD-Betrieb, kein KNX-Bus-/ETS6-Test.**


## KNX027 – RP2040 USB-Flash-Automatisierung (12.10.2026)

Das USB-Flash-Verfahren fuer die spaetere KNX018-Laptop-Testbank ist [softwareseitig vorbereitet](docs/KNX027_USB_FLASH_AUTOMATION.md). Der Controller verwendet ausdruecklich `upload_protocol = picotool`; das neue CLI unter [tools/usb_flash_controller.py](tools/usb_flash_controller.py) bietet passive USB-Port-Erkennung, Uploadplan, isolierten Firmwarebuild und **nur mit expliziten Teststand-/Port-/VID:PID-/Git-Freigaben** einen spaeteren USB-Upload. Arduino-Pico erlaubt bei bereits laufender kompatibler USB-CDC-Firmware ueblicherweise den 1200-Baud-Auto-Reset ohne BOOTSEL. Die Erstprogrammierung oder ein Recovery benoetigt weiterhin gegebenenfalls BOOTSEL und UF2. **Bisher kein RP2040 am LLO Desktop angeschlossen, kein echter Flash und keine Hardware-/Motorfreigabe.** Die KNX018-Testbank, alle ETS-/KNX-Bustests und elektrische Schutzpruefungen bleiben offen.


## LLO Home Offline-Entwicklung (KNX028, 13.10.2026)

Primärer Entwicklungsrechner nach Git-Synchronisierung: **LLO Home** unter `C:\_myspace\workspace\open-knx-valve-control`. Installation, festgelegte Toolchain-Pfade, Offline-Testbefehle und offene Hardwaregrenzen stehen in [KNX028 Home Setup](docs/KNX028_LLO_HOME_SETUP.md). Die reproduzierbaren hostseitigen Diagnosetests starten mit `powershell -NoProfile -File tools/home_offline_check.ps1`. Keine angeschlossene Platine, kein Upload und keine KNX-/Motorfreigabe.


**KNX028 Home-QA (13.10.2026):** RP2040-Compilerproblem behoben: `src/controller/controller.ini` pinnt ARM GCC 14.3.0 und den getesteten Raspberry-Pi-PlatformIO-Commit, der isolierte Controller-Build ist erfolgreich (RAM 20,6 %, Sketch 18,9 % des 1-MiB-Firmwarebereichs). Ein separater WinLibs-g++ ist per upstream SHA256 installiert; `powershell -NoProfile -ExecutionPolicy Bypass -File tools/home_offline_check.ps1 -Native` hat alle 11 nativen Test-Skriptgruppen samt ARDUINO-Hardlock bestanden. `-ControllerBuild` prueft zusaetzlich rein offline die RP2040-Firmware. **Dies ist kein USB-Flash, keine KNX-/ETS-Abnahme und keine Freigabe der acht Motoren.**


## KNX029 – Offline-Erstkontaktpaket für RP2040 + ATtiny (13.10.2026)

Auf **LLO Home** steht die [KNX029-Erstkontakt-Anleitung](docs/KNX029_FIRST_CONTACT_RUNBOOK.md) bereit. `tools/knx029_prepare_bringup.py` erstellt nach Clean-HEAD-Prüfung in einem **neuen Ordner außerhalb des Repos** ein versionsgebundenes Offlinepaket mit RP2040-UF2/ELF, ATtiny3216-HEX/ELF, Manifest und SHA256SUMS. `plan` und `verify` sind rein lesend, `build` führt nur isolierte Builds aus, kein USB-/UPDI-/KNX-/Motorzugriff. Bei der echten Platine muss U25 zunächst als ATtiny3216 oder ATtiny1616 identifiziert werden; vor jeder Versorgung die [KNX022-Sicherheitsblocker](docs/KNX022_STATIC_HW_READINESS.md) beachten. Bis KNX002–006 bleibt jeder Motor ausdrücklich gesperrt.

## KNX030 – Passive Geräteerkennung auf LLO Home (13.10.2026)

Wenn die V1.2-Platine nach Abschluss der elektrischen KNX002/003-Prüfung angeschlossen werden darf, kann [KNX030](docs/KNX030_PASSIVE_FIRST_CONTACT.md) neue Windows-USB/COM-Geräte und RPI-RP2-Laufwerke durch **Vorher-/Nachher-Snapshots** identifizieren. Die Baseline vom unbelegten Teststand liegt außerhalb Git unter `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-before-board-20261013.json`. `tools/knx030_passive_inventory.py plan`, `capture` und `compare` sind ausschließlich passiv/OS-lesend; keine COM-Öffnung, kein KNX/IP-Scan, keine Programmierung, keine Motorfreigabe. Ein lokaler WLAN-Link beweist keine KNX/IP-Verbindung.

## KNX031 – Offline UART-Trace-Diagnose (13.10.2026)

Mit [KNX031](docs/KNX031_UART_TRACE_OFFLINE.md) kann der KNX014-Datenrahmen zwischen ATtiny und RP2040 später aus einer **gespeicherten, separat und sicher aufgezeichneten Bytefolge** geprüft werden: A5-5A, CRC16, Sequenz, neun T0…T8-Kanäle und Sensorfehler. Ein nativer C++-Golden-Vektor-Test verwendet die tatsächliche gemeinsame Protokolldatei; die LLO-Home-Beispieldatei liegt außerhalb Git im Builds-Ordner. Der rein lokale Befehl tools/knx031_uart_trace.py inspect --format hex|binary öffnet **keinen COM-Port** und erlaubt keine Programmierung/KNX-/Motoraktion. Ohne zeitgestempelten und gerichteten Mitschnitt ist damit keine Bus-/Link-Onlinefreigabe verbunden.

## KNX032 – kompletter Softwarepfad UART → KNX-Temperatur (13.10.2026)

Auf LLO Home ist der [KNX032-Offline-End-to-End-Test](docs/KNX032_UART_TO_KNX_OFFLINE.md) neu: Ein aus dem **produktiven KNX014-C++-Protokoll** erzeugter GET/SNAPSHOT-Datenstrom wird ueber die originalen RP2040-C++-Module `TemperatureBridge` und `TemperaturePublisher` in **rein virtuelle KNX GroupObjects KO25..35** eingespielt. Geprueft werden neun T0..T8-Werte (0 °C, negative Werte), DPT9.001/DPT1.002/DPT7.001, CRC-/Sequenzfehler, Sensorqualitaet, 250-ms-Sendegap, Retry, 15-s-Ausfall und P19-Sperre. `tools/test_knx032_uart_to_knx.py test` und `tools/test_knx032_replay_contract.py` benoetigen nur den nativen Host-Compiler, **keine Platine und keinen KNX-Bus**. AppVersion2, Hardware und Motor-Gates bleiben unangetastet.

## KNX033 – reale V1.2-Bestueckungsfotos und D1-Bypass (13.10.2026)

Drei Fotos der bestueckten Platine sowie die Nutzerangaben **JMP1 geschlossen, JMP2/JMP3 jeweils »oben«, D1 entfernt und durch Draht gebrueckt** sind in der [KNX033 As-built Review](docs/KNX033_AS_BUILT_PCB_REVIEW.md) und dem [maschinellen Preflight](docs/KNX033_AS_BUILT_PREFLIGHT.json) mit den echten V1.2-PCB-Padnetzen verknuepft. **P0:** Foto F1 `T 2,5 A` gegen Schaltplan `630 mA` sowie D1 ohne Rueckwaertssperre. U6 sitzt moeglicherweise auf Rueckseite, U25-Markierung wirkt wie TINY3216, R29-Wert weiter unbekannt. **Keine Versorgung, keine USB/UPDI/KNX- oder Motorfreigabe.** Die Originalfotos befinden sich in dieser Unterhaltung, nicht im LLO-Home-Git.

## KNX034 – Rueckseitenfoto / geplanter USB-only-Betrieb (13.10.2026)

Ein viertes Foto zeigt nun **U6 als tatsaechlich montierten schwarzen Spannungswandler auf der Rueckseite** der V1.2-Platine (exakte TRACO-Aufschrift / elektrische Funktion noch nicht bestaetigt). Der Vorschlag, **JMP1 stromlos aufzutrennen**, ist in [KNX034](docs/KNX034_USB_ONLY_PREPOWER_GATE.md) samt [Preflight-JSON](docs/KNX034_USB_ONLY_PREFLIGHT.json) festgehalten. JMP1 offen unterbricht den vorgesehenen KNX_VCC→R9_2/Q1-Quellzweig; es ist keine galvanische Trennung. **Nicht bereits durchgefuehrt:** JMP1 gilt bis zur Nutzerbestaetigung weiterhin als geschlossen. USB-only bleibt vorerst ungeprueft, weil **F1 T2.5A statt 630mA**, D6-Spannungsabfall (U6 min. 4.75V VIN), D1-Draht-Bypass und Backfeed ungeprueft sind. Fuer Erstpruefung KNX, UPDI und Motoren abgeklemmt lassen; kein USB-Stecken vor gesondertem Power-Gate.

## KNX035 – KNX-Bus-Ueberlastung: R17 Pull-up muss entfallen (14.10.2026)

Nach realem U11-Hitzeereignis bei KNX + 5 V ist **R17 (10 kΩ von KNX_TX nach 3,3 V)** mit dem aktiven STKNX-Sendepegel unvereinbar: ST-Datenblatt [DS12399](https://www.st.com/resource/en/datasheet/stknx.pdf) legt **LOW=Idle**, **HIGH=35-µs-Sendepuls**, eigenen internen TX-Pulldown (typ. 6 µA) fest. Nutzer berichtet **tatsächlich 68 Ω an U11** – die PCB-Teilenummer 3,5 mΩ war nur als falscher Footprint-Platzhalter hinterlegt; keine nachgewiesene Fehlbestueckung. **R17 stromlos ausloeten** ist eine sinnvolle erste Reparatur, aber **keine Freigabe zum erneuten KNX-Anschluss**. Denn die vorhandene Offline-Firmware bindet TPUart/Serial1 als normalen UART (8E1/19200 bzw. 38400 Baud, Idle HIGH) ein und ist damit **kein STKNX-kompatibler direkter Pulstreiber**. Fuer neue Platine Pull-down 4,7–10 kΩ **von KNX_TX nach GND auf neuem Footprint** und idealerweise fail-LOW TX-Freigabe sowie eigene STKNX-Phy/PIO pruefen. [KNX035 Risikobericht](docs/KNX035_STKNX_TX_IDLE_HAZARD.md), [Gates JSON](docs/KNX035_STKNX_TX_HAZARD.json). Ursache am realen U9-Pin und nach Überhitzung moeglicher Defekt von U9/U11 bleiben offen. Keine Power-/Bus-/Motorfreigabe.

## KNX036 – Wechsel auf LLO Desktop / isolierter USB-Erstkontakt (14.10.2026)

Der führende KNX035-Stand wurde aus LLO Home per **lokalem Git-Bundle** mit SHA256-Verify und 19 Commits ohne GitHub-Push auf `C:\ASH\Workspace\Projects\open-knx-valve-control` übertragen. Der [KNX036-Desktop-Erstkontaktplan](docs/KNX036_DESKTOP_USB_FIRST_CONTACT.md) erfasst COM1 (PC-Standardport) und COM3 (Intel-AMT-SOL), eine passive `before_board`-Windows-Baseline und eine zweite unveränderte USB-Inventur. **Keine realen neuen RP2040- oder CH340-Ports identifiziert.** Ein völlig getrenntes, **BUILD-ONLY / Upload-gesperrtes** [RP2040-USB-CDC-Diagnoseprojekt](tools/knx036_usb_diag/platformio.ini) baut erfolgreich und hält GPIO0 KNX_TX nach Setup LOW; es enthält **keine KNX-/ATtiny-/Motoransteuerung**. Realer USB-/UPDI-Anschluss/Flash und jede KNX-Busaktivität warten auf Sicherheitsfreigaben für R17, F1, D1, U6 und CN1-Pegel. Keine neue Versorgung wurde durch den Agent aktiviert.

## KNX037 – erster realer RP2040-USB-Flash und COM4-UPDI-Gate (14.10.2026)

Auf **LLO Desktop** wurden live **RP2040 COM5 / 2E8A:00C0** und **CH340 Programmer COM4 / 1A86:7523** nachgewiesen. Der RP2040 wurde ueber **1200-baud CDC DTR True→False** ohne BOOTSEL-Taste in ROM-Bootmodus gebracht (**2E8A:0003**); `picotool info -a` bestaetigt **RP2040 B2 mit realen 16 MiB Flash**. Die bereits isoliert gebaute **KNX036-USB-Heartbeat-UF2** wurde real mit `picotool load -v -x` geschrieben, **100 % verifiziert** und gestartet. Neue Firmware: **COM7 / 2E8A:000A**, 115200 Baud, echte Heartbeats alle 2 s **PASS**. Reproduzierbarer, streng auf RP2040-USB begrenzter [KNX037-Workflow](tools/knx037_rp_usb_workflow.py) mit Port/Seriennummer/SHA-/Bootloader-Check und [Live-Protokoll](docs/KNX037_DESKTOP_LIVE_USB_AND_UPDI.md) vorhanden. **ATtiny nicht programmiert:** Der Units-Programmer hat RTS=true/DTR=true im UPDI-Modus, aber seine USB-5-V-MUX-Pegel zum 3,3-V-ATtiny und CN1.1-5-V-Rueckspeisung sind noch ungeprueft. COM4 blieb zu, keine KNX-Telegramme und keine Motorbefehle.

## KNX038 – Units-UPDI/RTS und ATtiny3216 Temperature-Firmware (14.10.2026)

Auf **LLO Desktop** wurde der **Programmer-V1.2-Schaltplan** samt PCB und Units-WebSerial-Implementierung erneut geprueft: **COM4 = CH340 1A86:7523**, **RTS=True + DTR=True** in UPDI, U2/U7 SN74LVC1G3157 schalten TX/RX auf UPDI um. Programmer-MUX werden aus USB-VCC versorgt; das ist **keine automatische 5V→3.3V-Pegelwandlung**. ValveControl **U25 VDD=3.3V**, CN1 Pin1=5V, Pin3=UPDI; der Nutzer vermutet angeschlossenes 2x3-CN1-Kabel, aber reale Pinorientierung, UPDI-Ausgangs-High, Pin1-Rueckspeisung und ATtiny-Signatur sind noch **nicht gemessen**. [KNX038 vollstaendiger Pegel-/Signaturplan](docs/KNX038_UPDI_RTS_ELECTRICAL_GATE.md) + [Gates JSON](docs/KNX038_UPDI_PREFLIGHT.json). Die unveraenderte **ATtiny3216-Temperatur-Firmware** wurde live auf Desktop mit `pio run -e temperature` offline kompiliert (SUCCESS: 8655 B Flash, 983 B RAM); HEX/ELF + SHA256-Manifeste im Desktop Builds-Ordner. [Guarded COM4 Preflight-Tool](tools/knx038_updi_readiness.py) erlaubt vor Pegelpruefung **nur PnP/Build-Checks**, noch keinen RTS- oder UPDI-Zugriff; 14 Negativtests PASS. **Kein ATtiny-Flash oder Erase bisher**; der RP2040 laeuft weiterhin mit dem KNX036-USB-Heartbeat auf COM7.

## KNX039 – ATtiny3216 per UPDI auf COM4 wirklich ausgelesen (14.10.2026)

Mit ausdruecklicher Nutzerfreigabe wurde der **verbundene Units CH340 Programmer** am LLO Desktop auf **COM4 / VID1A86:PID7523** via `pymcuprog` auf UPDI angesprochen (logischer RTS-/DTR-UPDI-Modus). **Echte Signatur `1E 95 21` = ATtiny3216**, somit ist die spontan genannte `2316`-Bezeichnung nicht der reale Chip und die alte PCB-BOM `ATTINY1616-SN` unzutreffend fuer das bestueckte Testboard. [KNX039 Readback](docs/KNX039_LIVE_UPDI_READBACK.md): Flash **32 KiB**, EEPROM **256 Byte**, Fuses **9 Byte** und USERROW **32 Byte** erfolgreich per **READ** ausgelesen und mit Checksums/SHA256 privat im Desktop-Builds-Ordner gesichert. Flash enthaelt 1.888 Bytes ungleich FF, EEPROM und USERROW sind FF; das Ist-Programm unterscheidet sich vom neuen **ATtiny3216-Temperatur-Build** um 8.450 definierte Bytes. **Kein Erase, kein Flash-/Fuse-Schreiben, keine KNX- oder Motor-Aktion.** Elektrische UPDI-Spannungs-/Rueckspeisungspruefung bleibt trotz funktionierender Kommunikation ungemessen. [Maschinenlesbare Evidenz](docs/KNX039_UPDI_READBACK_EVIDENCE.json).

## KNX040 – beide Firmware-Images real programmiert, echte 9-Kanal-UART-Diagnose PASS (14.10.2026)

[KNX040 Live-Protokoll](docs/KNX040_REAL_TEMPERATURE_UART.md): Auf LLO Desktop wurde die neue **ATtiny3216-Temperaturfirmware** über CH340/UPDI COM4 geflasht (\`pymcuprog --erase --verify\` **OK**) und durch unabhängigen kompletten Flash-Readback bestätigt: **8655 von 8655 Flash-Bytes identisch, Fuses und EEPROM vor/nachher unverändert**, alle früheren KNX039-Originalbackups erhalten. Anschließend eine **separate, KNX- und motorfreie RP2040 USB/Serial2 UART1-Diagnose** über USB-Bootloader geflasht: GPIO8→ATtiny PA2, GPIO9←ATtiny PA1; echte CRC-/Seq-gültige Antworten **8/8**, **0 Timeouts**, **0 rejected**, auf allen **9 T0–T8** korrekt **NoSensor** (keine Sensoren angeschlossen); wiederholter Live-Capture weitere **5/5 PASS**, bereits insgesamt 153 akzeptierte Antworten. [Read-only USB-Capture](tools/knx040_capture_uart.py) bleibt für Sensor-Nachmontage nutzbar. **Kritische Entdeckung:** installierter Arduino-Pico SerialUART \`availableForWrite()\` ist 0/1 statt FIFO-Länge; die alte \`<8\`-Prüfung verhindert jegliche Temperaturabfrage. Im isolierten Test repariert; derselbe Fehler liegt noch in \`src/controller/temperature_bridge.cpp\` und muss in einem gesonderten Controller-Slice behoben werden. Wegen gefährlichem STKNX/TPUart/KNX035 den ursprünglichen Controller weiterhin nicht flashen, keine KNX-/Motorfreigabe.
