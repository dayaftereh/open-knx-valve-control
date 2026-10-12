# ASH Slice History - OpenKNXValveControl

**Protocol:** [ASH Project Workflow v1](../reference/ash/README_PROJECT_WORKFLOW.md)

**Verantwortlich:** jeweils fachlicher Slice; Sitzungen/Chats sind austauschbar.

**Nur tatsaechlich geschlossene, validierte Slices** erscheinen in diesem chronologischen Index. Offene Arbeit liegt in `_OPEN_KNX###_*.md` und die Vorschau in [ROADMAP](../ROADMAP.md).

## Vor der ASH-Aktivierung: bestehende Projektbasis

Diese Git-Arbeiten sind **keine rueckwirkend formal abgeschlossenen Slices**; es gab dabei noch keinen aktiven `_OPEN_...`-Marker, keine dokumentierte vierstufige Slice-Gate-Historie. Ihre technischen Feststellungen und Restrisiken sind in den verlinkten permanenten Dateien dokumentiert.

| Commit | Bestehende Arbeit | Nachweise und Grenzen |
| --- | --- | --- |
| `53b308a` | HmIP-VDMOT, ETS-/Architektur- und README-Konzept | [Antrieb](../ACTUATOR_HMIP_VDMOT.md), [ETS-Konzept](../ETS_AND_CONTROL_CONCEPT.md); keine Aktor-Kalibrierung |
| `4fa28c1` | Schaltplan V1.2 geprueft, Hardware-/R29-/U25-/Power-Risiken dokumentiert | [Schematic-Audit](../SCHEMATIC_V1_2_REVIEW.md); kein Hardwaretest |
| `0045a45` | EasyEDA-PCB- und ETS-XML-Pruefung, reproduzierbarer Static-Checker | [PCB-Audit](../PCB_V1_2_AUDIT.md), [ETS-Produkt-Audit](../ETS_PRODUCT_AUDIT.md); kein EasyEDA-DRC/ETS6-Import |
| `c2e4bee` | Externe 5-V-Alternative und Jumper/Power-Netze dokumentiert | [Power-Konzept](../POWER_SUPPLY_CONCEPT.md); Hardwareversorgung nicht freigegeben |

**Wichtiger gemeinsamer offener Sachstand:** Originalprojekt auf `main`, vier Commits gegenueber `origin/main` lokal bei Beginn KNX001, nicht gepusht. RP2040/Motor-/Regelungsimplementierung bleibt offen, echte Leistungs- und Sicherheitsmessungen stehen aus.

## Abgeschlossene ASH-Slices

## KNX001 - ASH Project Workflow v1 Bootstrap

- **State:** closed
- **Closed:** 2026-10-10
- **Profile:** software, ergaenzt um EasyEDA-/Elektronik-/ETS-/Research-Checks
- **Objective:** Den originalen ASH Project Workflow v1 aus `/ASH` vollstaendig in diesem Repository referenzieren und Project/Slice/Session inklusive Roadmap, Recovery und Gate-4-Regeln aktivieren.
- **Result:** Sieben Quell-MD-Dateien in `docs/reference/ash/`, Hash-Manifest, [lokale Regeln](../../.ash/WORKFLOW.md), [Konfiguration](../../.ash/project.yaml), [Roadmap](../ROADMAP.md), [Slice-Index](README.md), aktualisierte Root-README und reproduzierbares [ASH Audit](../../tools/audit_ash_workflow.py).
- **Implementation commit:** `04eeb48` (`docs(ash): import workflow v1 and bootstrap KNX slices`).
- **Closing:** dieser `HISTORY.md`-Eintrag, Roadmap = closed und Entfernung `_OPEN_KNX001_ASH_WORKFLOW_BOOTSTRAP.md` im eigenen Closing-Commit (`docs(ash): close KNX001 after QA`).
- **Gate-1 / Gate-2:** Root, neue Write-Session, Git-Tree clean, keine offenen Marker, vier bereits vorhandene lokale Doku-Commits als Baseline; Source-of-Truth und Scope eindeutig festgelegt.
- **Gate-3:** Alle sieben ASH-Originaltexte kopiert; projekteigene `.ash`-Regeln, Recovery-Anleitung, Quellenindex, Roadmap KNX002..KNX011 und SHA256-Manifest erstellt. Alle bisherigen Hardware- und ETS-Dokumente erhalten.
- **Gate-4 QA:** `python tools/audit_ash_workflow.py`: **PASS, 30 Checks, 0 Fehler** mit sieben Referenz-Hashes und **165 aufloesbaren internen Markdown-Links**; `python tools/audit_design.py`: **PASS, 0 strukturelle Fehler** (bestehende Hardware-/ETS-Warnungen bleiben); `git diff --cached --check`: **PASS**; Scope gegen Baseline geprueft.
- **No claims:** Keine neue Firmware, ETS-Produktversion, Motorbewegung, Platinenkorrektur, Labor-Messung oder Releasefreigabe.
- **Follow-ups:** KNX002 As-built Hardware/BOM, KNX003 externe 5-V-Versorgung; KNX008 ETS-Zonenmodell kann bei blockierter Hardware separat geplant werden (niemals paralleler Write-Slice).
- **Next exact action:** Bei der naechsten Arbeits-Session Root/Git/Session-/`_OPEN_`-Status pruefen; falls kein Slice offen, den konkreten naechsten Roadmap-Slice begrenzt als `_OPEN_...` anlegen.

Ein Slice-Closing ist kein Git-Push und kein Release. Der lokale Branch bleibt vorerst vor `origin/main`.


## Vorgehen bei Folgeslices

Bei Gate 4 fuer jeden echten Slice mindestens ID, Datum, Objective/Result, Profil, Tests mit PASS/FAIL-Status, Implementierungscommit bzw. Checkpoint, geaenderte Artefakte, Restrisiken und Follow-ups eintragen. Den `_OPEN_...`-Marker im Closing-Commit entfernen. Nicht getestete technische Subsysteme nicht als freigegeben darstellen.


## KNX012 - Software-first Firmwarearchitektur und Temperatur-UART (Design-Slice)

- **State:** closed
- **Closed:** 2026-10-10
- **Profile:** software + research (kein physisches Board, keine Motorbewegung)
- **Objective:** Die Prioritaet auf neun ATtiny-Temperaturwerte mit gueltigem Snapshot, RP2040-UART-Abruf und anschliessender KNX-DPT9.001-Ausgabe legen; Source/PCB/Framework-Pins vor Firmwareumbau abgleichen.
- **Baseline:** `4bffbcc`, Git clean und sechs lokale Commits vor `origin/main`. Andere aktive Write-Sessions bzw. offene Slice-Marker: **keine**.
- **Implementation commit:** `a183271` (`docs(ash): KNX012 plan software-first temperature and UART bridge`).
- **Closing:** Dieser HISTORY-Eintrag, ROADMAP KNX012 auf closed und Entfernen des eigenen `_OPEN_KNX012_SOFTWARE_FIRST.md`-Markers im separaten Closing-Commit.

### Gates und Evidenz

1. **Gate 1 Checkup/Analysis:** PCB V1.2, ATtiny/RP2040 C++ und `txy6/pins_arduino.h` des installierten megaTinyCore abgeglichen. Alle neun bestehenden `Pin::T0..T8` stimmen **nicht** mit den realen PCB-Netzen ueberein. SPI0-SCK PA3/SOIC-Pin19 hat keine PCB-Netzverbindung; SPI-CS-Code zeigt auf PC2/T_INT statt PA4/CS. USART0 nutzt standardmaessig PB2/PB3 (Debug), ALT1 PA1/PA2 ist mit RP2040 GPIO9/8 verdrahtet.
2. **Gate 2 Decision:** Fuer PCB V1.2 gerahmte UART-Anfrage als Ziel, ATtiny non-blocking OneWire Snapshot, Sensorrollen `T0=Vorlauf`, `T1..T8=Ruecklauf Kreis1..8`, RP KNX-DPT9.001-Publizieren und getrennte spaetere Soll-/Ist-Raum- versus Direkt-0..100%-Regelung. Vollstaendiger Entwurf in [FIRMWARE_SOFTWARE_FIRST.md](../FIRMWARE_SOFTWARE_FIRST.md).
3. **Gate 3 Implementation:** Rein dokumentarischer Slice mit neuer [reproduzierbarer Pin-/Interface-Analyse](../../tools/audit_temperature_bridge.py); [ROADMAP](../ROADMAP.md) um KNX013..016 fuer Temperatur-MVP ergaenzt und [README](../../README.md) verlinkt. **Keine Aenderungen** an ATtiny-/RP-Firmware, PCB, Schaltplan oder ETS-Produkt-XML.
4. **Gate 4 Validierung:** `pio run -e temperature` **PASS (Exit 0)** mit `.pio/build/temperature/firmware.hex` (23.506 Bytes); `python tools/audit_ash_workflow.py` **30/30 PASS**, 187 Dokumentationslinks zur offenen Slice-Phase; `python tools/audit_design.py` **0 strukturelle Fehler**; `python tools/audit_temperature_bridge.py` **0 Script-Fehler / 16 offengelegte Integrationsluecken**, mit `--strict` **erwarteter Exit 2** (kein erfolgreicher Verbindungs-/Hardwaretest); `git diff --cached --check` PASS. Nach Schliessung ASH und Linkpruefung erneut ausfuehren.

### Offene Risiken und Naechstes

- **KNX013** ist der naechste **geplante**, noch **nicht gestartete** Software-Slice: richtige ATtiny-Ports T0..T8, Sensor-FSM ohne blockierende 12-Bit-Wartezeit, Qualitaet und Alter, Host-Tests und Firmwarebuild. Dann KNX014 UART und KNX015/016 KNX/ETS6.
- RP2040-Temperaturkommunikation fehlt noch; im Controller Build existiert ein OpenKNX-Producer-Pre-Script, das `include/knxprod.hpp` veraendern koennte. **Kein unkontrollierter RP2040 Build/ETS-Import in KNX012.**
- Physische U25-Bestueckung, genaue Dallas-Fuehler, KNX-Versorgungsreserve, echte UART-Kommunikation und KNX-Busmonitor sind **ungeprueft**; die Motor-Safety-Gates bleiben unveraendert bindend.
- **Kein Push** nach GitHub und keine behauptete Firmware-Funktionsfreigabe.


## KNX013 – ATtiny3216: asynchroner 9-Kanal-Temperatursammler

- **State:** closed
- **Closed:** 2026-10-11
- **Profile:** software, mit nativen C++ Unit-/Mock-Tests und ATtiny-PlatformIO-Build; kein Hardwaretest
- **Objective:** PCB-V1.2-korrekte T0..T8-Pins, 1-Wire-Messungen ohne blockierende Konversionswartezeit, gespeicherte Messwerte mit Gültigkeit/Fehler/Alter und zuverlässiges Verhalten bei fehlenden Sensoren.
- **Baseline:** bfb6745 auf sauberem main, acht lokale, noch nicht gepushte Commits vor origin/main; kein anderer offener Slice oder fremde aktive Write-Session.
- **Implementation commit:** 34b0dc3 (feat(knx013): add asynchronous ATtiny nine-sensor sampler).
- **Closing commit:** der separate Commit mit diesem HISTORY-Eintrag, Roadmap-Status closed und Entfernung des _OPEN_KNX013_ATTINY_SAMPLER.md-Markers.
- **Detailed engineering record:** [KNX013_ATTINY_SAMPLER.md](../KNX013_ATTINY_SAMPLER.md); Software-Roadmap [FIRMWARE_SOFTWARE_FIRST.md](../FIRMWARE_SOFTWARE_FIRST.md).

### Gate-Protokoll

1. **Gate 1 / Checkup:** LLO Desktop Agent online, Git/Session/Slice-Markierungen verifiziert. Neun bisherige ATtiny-Pin-Zuordnungen falsch gegenüber EasyEDA V1.2. Legacy-SPI0 unbrauchbar, weil PA3/SCK nicht geroutet. Firmware hatte blockierende DallasTemperature-Wartezeit und gab für fehlende Sensoren künstlich 0 °C zurück.
2. **Gate 2 / Decision:** T0 als Vorlauf, T1..T8 als Rücklauf je Heizkreis; neun getrennte 1-Wire-Eingänge, versetzter Messzyklus, Snapshot mit Fehler-/Alterstatus. Legacy-SPI entfernen, UART/RP2040 erst KNX014. Motor- und Stromversorgungsarbeiten vollständig ausgeschlossen.
3. **Gate 3 / Implementation:** Portzuordnung auf PIN_PA5, PIN_PA6, PIN_PA7, PIN_PB5, PIN_PB4, PIN_PB1, PIN_PC1, PIN_PC0, PIN_PB0 korrigiert. Hardwareunabhängiger Sampler-Core mit asynchronem DallasTemperature-Adapter, Wiedererkennung/CRC-Fehler, 85-C-Power-On- und Parasitenwarnung sowie Stale-/Valid-Flags. Arduino-Config-Layout kompatibel belassen. Alte SPI0-Quellmodule und SPI-Dependency entfernt; kein UART-Protokoll vorgezogen.
4. **Gate 4 / Validation:** ATtiny PlatformIO Build **PASS**, 924/2048 B RAM und AVR-size 8426/32768 B Program. Zwei native C++ Testsuites **PASS** (reiner Scheduler und produktive Temperature/Temperatures mit neun OneWire-/Dallas-Mocks), inklusive 0/negativ, Steckverlust/Wiederanschluss, Stale, 85 °C, Wraparound und Recovering-Status. KNX013 Pin-/Sensor-Audit --scope sensors --strict **PASS, 0 Sensorlücken**. ASH Workflow Audit **PASS, 30 Checks**, lokaler Markdown-Linkcheck, PCB/ETS Static Audit ohne neue strukturelle Fehler. Gestagter Git-Diff-Whitespacecheck **PASS**. Abschlussprüfungen nach Markerentfernung erneut verifiziert.

### Grenzen und nächste Schritte

- **Nichts geflasht**; reale ATtiny-Bestückung, echte Sensor-Genauigkeit/Latenz, externe 3,3-/5-V-Versorgung und KNX-Telegramme weiterhin ungetestet. Host-/Compiler-PASS ist keine Hardwarefreigabe.
- **KNX014 geplant, nicht gestartet:** USART0-Pinmux ATtiny PA1/PA2 und RP2040 GPIO8/9, gerahmtes CRC-gesichertes GET_SNAPSHOT/Response, Timeout/Stale-Behandlung. Die beiden übergeordneten Transportlücken bleiben im Gesamtaudit sichtbar.
- Nach KNX014 folgen KNX015 KNX DPT9.001 Publish und KNX016 ETS6-Temperaturprodukt. Keine Motorbewegung vor separaten Hardware-/Safety-Slices KNX002..006.
- **Kein GitHub-Push** und keine Releasefreigabe durch KNX013.


## KNX014 – CRC-framed UART bridge ATtiny3216 to RP2040

- **State:** closed
- **Date:** 2026-10-11
- **Profile:** software, offline build and native simulation. **No physical UART/KNX hardware acceptance.**
- **Initial HEAD:** 1e45868 (main clean, 10 commits ahead origin/main); no other active write sessions or open Slice markers.
- **Implementation:** 48eb2cb — feat(knx014): add CRC framed UART temperature bridge.
- **Closing:** Separate commit of this HISTORY, ROADMAP closed state and deletion of _OPEN_KNX014_UART_BRIDGE.md.
- **Technical documentation:** [KNX014_UART_BRIDGE.md](../KNX014_UART_BRIDGE.md).

### ASH Gate 1 – Checkup / Analysis

- Confirmed PCB V1.2 UART nets: ATtiny PA1/Pin17 TX via T_RX -> RP2040 GPIO9 RX; ATtiny PA2/Pin18 RX via T_TX <- RP2040 GPIO8 TX.
- megaTinyCore 2.6.7 supports Serial.swap(1) to USART0 ALT1; Arduino-Pico Serial2 on UART1 GPIO8/9 is separate from KNX Serial1.
- KNX013 provided nine valid/age/fault snapshots; older ATtiny SerialDispatcher was an incompatible unframed binary protocol; existing RP build pre-script could regenerate the canonical knxprod.hpp.
- Project baseline and ASH protocol checked before changes.

### ASH Gate 2 – Decision / Plan

- Fixed 115200 8N1 polling transport with A5 5A sync, version/type/seq/length, CRC16-CCITT-FALSE; GET_SNAPSHOT request 8 bytes, SNAPSHOT reply 67 bytes with nine six-byte channels and ATtiny uptime.
- Shared platform-independent codec/parser, explicit request timeout 400 ms, poll period 3 seconds, offline after 15 seconds, no acceptance of wrong CRC/version/sequence.
- ATtiny responds **only from cached RAM snapshots**, with no live OneWire call on the serial request; no KNX publish until KNX015.
- Existing ATtiny EEPROM config preserved, but former PB2/PB3 serial configuration protocol intentionally not attached to PA1/PA2; future KNX/ETS configuration migration remains open.

### ASH Gate 3 – Implementation

- Shared codec [temperature_protocol.hpp](../../lib/common/temperature_protocol.hpp) and client state [temperature_client_core.hpp](../../lib/common/temperature_client_core.hpp).
- ATtiny responder [temperature_link.cpp](../../src/temperature/temperature_link.cpp), USART0 ALT1 in [main.cpp](../../src/temperature/main.cpp).
- RP poller [temperature_bridge.cpp](../../src/controller/temperature_bridge.cpp), Serial2 GPIO8/9 initialization in [main.cpp](../../src/controller/main.cpp).
- Four native C++ test suites and repeatable [test runner](../../tools/test_temperature_uart.py). Safe [isolated controller build](../../tools/build_controller_isolated.py) prevents tracked OpenKNX header modifications.
- [README](../../README.md), [firmware roadmap](../FIRMWARE_SOFTWARE_FIRST.md) and [ROADMAP](../ROADMAP.md) updated.

### ASH Gate 4 – Validation

- **ATtiny PlatformIO temperature PASS**, 983/2048 bytes RAM, program 8480/32768 bytes.
- **RP2040 PlatformIO controller PASS** in isolated copy; RAM 52,008/262,144, flash 154,320/1,048,576, UF2 generated. SHA256 comparison confirmed original include/knxprod.hpp unchanged. Initial repository test-script attempt built successfully but cleanup failed on a read-only Windows Git pack; script cleanup was hardened and full repeat PASS (Exit 0).
- **Four KNX014 native C++ suites PASS**: golden CRC/frame/endian/parser, sequence/timeout/offline and rollover, real ATtiny UART responder with 9 mocked sensors/backpressure, real RP2040 UART adapter with mocked hardware serial.
- **Two KNX013 regression suites PASS**: 1Wire core and actual 9-sensor mocked adapters.
- **Strict sensor+UART static audit PASS**, zero mismatches. **ASH audit PASS (30 checks, 222 local Markdown links before closing)**. **PCB static audit PASS (0 new invariant failures)**, with pre-existing BOM/power/ETS warnings. Python compile check PASS; staged Git diff --check PASS.
- Closing checks after removing marker confirm only closed slice, current HEAD, Git clean and no push.

### Remaining restrictions / next slice

- Never flashed either chip; ATtiny U25 actual populated part, supplied 3.3 V and true end-to-end UART waveforms/OneWire behavior remain unverified.
- OpenKNXproducer output still warns about macro redefinitions / malformed Ko names in the existing product XML. Generator/build success is **not** ETS6 import or bus Telegram proof.
- **KNX015 planned (NOT started):** Consume the cached, validity-checked T0..T8 snapshots and publish KNX DPT9.001 temperatures with configurable scheduling and diagnostics, after repairing KNX product identifier macros without silently renumbering active projects.
- Hardware checks KNX002/003/004/005 remain mandatory for motor/supply work. No remote push.


## KNX015 – KNX DPT9.001 telemetry and ETS minimum product

- **State:** closed (offline software and product-generator gates)
- **Closed:** 2026-10-12
- **Baseline:** e2e54c6, main clean, 12 local commits ahead origin/main; no foreign write session or open marker.
- **Implementation commit:** f73b61c (feat(knx015): publish ETS-configurable KNX temperature telemetry)
- **Closing commit:** separate commit to close ROADMAP/HISTORY and remove _OPEN_KNX015_KNX_TEMPERATURE.md; see Git history.
- **Detailed engineering record:** [KNX015_TEMPERATURE_PUBLISH.md](../KNX015_TEMPERATURE_PUBLISH.md).

### Gate 1 – Checkup

Verified via LLO Desktop Agent: KNX013+014 sessions completed, repository clean and no current open Slice. Confirmed KOs **25..33** carry T0..T8 DPT9.001; earlier ETS baseline contains 33 KOs/19 params. KNX getGroupObject(ASAP) is **1-based**, DPT_Value_Temp is Dpt(9,1). Source-XML KO names and generator double-defined C++ macros were defective; old application version was 1. Physical hardware/bus remained untested.

### Gate 2 – Decision

Keep KO1..33 and P1..19 numbered/layout- and metadata-compatible. Add ETS P20 periodic send interval 10..3600 s (default 60) at memory offset 7 and P21 temperature change threshold 0..1000 centiC (default 50=0.5C) at offset 9. Retain P19 as global temperature-output enable. Append KO34 UART connection online, DPT1.002 and KO35 T0..T8 9-bit validity mask, DPT7.001; bump application version to 2. Implement safe DPT9.001 publish from valid cached KNX014 samples, one event per loop, 250 ms shared bus gap and >=5s per channel on change. No motor actuation or ETS6/live-bus commissioning.

### Gate 3 – Implementation

- [Publisher](../../src/controller/temperature_publisher.cpp) reads generated ETS parameters, transfers real negative or 0 C sensor values as DPT9.001 on KO25..33, and sends KO34/35 diagnostic changes; gate on knx.configured and P19, never send stale/missing samples.
- [Pure schedule](../../lib/common/temperature_telemetry_policy.hpp) applies periodic/delta and per-KO throttling, priority diagnostics, fairness and revalidation after sensor return.
- [XML](../../assets/open-knx-valve-control.xml) preserves original KO IDs/numbers, DPT and visible descriptions plus parameter memory layout. Only internal names normalized. App version 2; now 35 KOs and 21 parameters.
- OpenKNXproducer pre-script was hardened to fail on generator errors, and [KO header normalizer](../../assets/knxprod_header_fix.py) retains numeric macros while giving KNX accessor aliases unique Object suffixes. Canonical [generated header](../../include/knxprod.hpp) updated from verified isolated output. Independent [ETS ABI audit](../../tools/audit_knx015_product.py) guards against silent historic KO/P changes.
- Updated README, [software plan](../FIRMWARE_SOFTWARE_FIRST.md), ETS historical baseline and [roadmap](../ROADMAP.md).

### Gate 4 – Validation

- **RP2040 controller PlatformIO isolated build PASS**, 52,240 / 262,144 RAM, 186,268 / 1,048,576 flash. UF2 created, original canonical header SHA unchanged during isolated build; copied deliberately only after validation. No duplicate/illegal KO macros in newly generated header.
- **ATtiny3216 PlatformIO regression build PASS**, no new ATtiny source modifications.
- **All 8 native C++ test suites PASS**: two KNX015 (full scheduler, production TemperaturePublisher plus actual TemperatureBridge with simulated serial and KNX GroupObjects), four KNX014 (CRC/sequence/timeout and both real adapters), two KNX013 (sampler and 9-probe mocks). Includes negative/0 C, offline, missing/returning sensor, throttling and no stale-temperature publishing.
- **ETS ABI auditor PASS**, explicitly compares historic KO1..33 and P1..19 with immutable KNX014 baseline e2e54c6, validates appVersion2/KO35/P21, generator header and diagnostic DPTs.
- **Generated .knxprod integrity PASS**: 6 ZIP entries, CRC clean, application XML version 2, 35 communication objects and 21 parameters. **No ETS6 import performed**; producer reported unavailable local XSD and historical channel-number placeholder warning.
- **Bridge/Pins audit PASS** (0 mismatches), **PCB/ETS static audit PASS** (0 invariant failures, existing 5 V/BOM/DPT5.004 warnings remain), **ASH workflow PASS** (30 checks, 252 Markdown links pre-close), Python syntax PASS, staged Git diff --check PASS.
- Post-closing ASH/ABI audits run again with no open Slice and clean Git tree. No remote push.

### Open risks and next step

- No actual KNX Telegram Monitor proof, ETS6 import, KNX associations or UART/OneWire physical verification. Current KO values can retain **last historical reading** after fault; consumers need KO34/35 quality state.
- Existing valve position KO17..24 remain DPT5.004 (not revised to 5.001); single motor/current-sensor safety and 5V power gating remain untested/blocked until separate hardware slices.
- **Next planned software slice KNX016:** isolated ETS6 import of version-2 KNXprod, inspect KO25..35 and P19..21 and perform product/GA visibility validation. Must start with fresh write session and Git/session check; do not auto-start.
- Not a production release, no hardware flash, no motor movement, no GitHub push.


## KNX017 – KNX-Hardwaretest zurückgestellt, eigenständige Testumgebung geplant

- **Status:** closed (Planungs-/Dokumentationsslice, keine Hardwareaktivität).
- **Datum:** 2026-10-12.
- **Ausgangs-HEAD:** `8b404a3`, `main` clean, 14 lokale Commits vor `origin/main`.
- **Planungs-Commit:** `63283c8` – KNX-Abnahme auf eigenständige Testbench verschoben.
- **Closing-Commit:** separater Commit für HISTORY, Roadmap-Status closed und Entfernung des offenen KNX017-Markers.
- **Entscheidungsdokument:** [KNX-Testbench-Plan](../KNX_TESTBENCH_PLAN.md).

### Gate 1 – Checkup
LLO Desktop Agent online; Git/Session/Marker geprüft. KNX015 technisch offline abgeschlossen, KNX016 **nicht geöffnet**. Reale ETS6-Import-, KNX-Bus-, Controller-Flash-, UART- und Antriebsmessungen weiterhin nicht erbracht.

### Gate 2 – Decision
Auf Nutzerwunsch KNX016 (ETS6-Temperatur-Import) und KNX009 (späterer ETS6-Produkt-Import) **deferred**, ohne offene Write-Slices. Echte ETS-/KNX-Integration soll nicht am bisherigen LLO Desktop Agent abgeschlossen werden, sondern später mit eigenem ETS-Testrechner, separatem KNX-Bus/Interface und der real angeschlossenen OpenKNXValveControl-Platine stattfinden. KNX018 als geplanter Testbench-Slice vorgemerkt; vorher elektrische As-built-/Power-Gates KNX002/003. Keine Datumszusage und kein Hardwaretest in KNX017.

### Gate 3 – Implementation
Roadmap und [README](../../README.md) aktualisiert; dedizierte [Testbench-Anforderungen](../KNX_TESTBENCH_PLAN.md) und passive/aktive Abnahmereihenfolge dokumentiert. **KNX008** (ETS-Raum-/Heizkreis-Zonenmodell und Soll-/Ist- vs. Prozent-Regelmodus) als nächste hardwareunabhängige Aufgabe empfohlen, nicht gestartet.

### Gate 4 – Validation
ASH-Workflow-Audit **PASS, 30 Checks**, **271 Markdown-Links** vor Closing; unveränderte PCB-/ETS-Statik **PASS mit 0 Invariant-Fehlern** (bestehende Power-/Bestückungswarnungen); gestagter `git diff --check` **PASS**. Nach dem Closing Roadmap/Marker/Git-Status erneut geprüft. Kein Push, keine Platinen-/KNX-/ETS6-Aktion, kein Motorbetrieb.

### Wiederanlauf
Nach Aufbau der dedizierten Testumgebung über **KNX018** die Hardware-/Schnittstellenfreigaben dokumentieren, dann **KNX016/KNX009** in frischen Write-Sessions fortsetzen. Bis dahin Softwarearbeiten wie KNX008 möglich, aber nur nach separatem Slice-Start und Checkup.


## KNX008 – Zonen-/Heizkreis-Zuordnung und ETS-Modusvertrag

- **State:** closed (Software-/ETS-Design-Gate, keine Produkt- oder Hardwarefreigabe)
- **Closed:** 2026-10-12
- **Baseline:** `c171d17`, `main` clean, 16 lokale Commits vor origin/main, keine fremden Write-Sessions oder offenen Marker
- **Implementation commit:** `1b5ead4` – feat(knx008): specify zone ETS contract and offline target router
- **Closing commit:** separater Commit mit diesem HISTORY-Eintrag, Roadmap/README-Status und Entfernung des KNX008-Markers
- **Detailed record:** [KNX008_ZONE_CHANNEL_DESIGN.md](../KNX008_ZONE_CHANNEL_DESIGN.md)
- **Proposed ETS schema (NOT LIVE):** [knx008_zone_ets_proposal.json](../../assets/knx008_zone_ets_proposal.json)

### Gate 1 – Checkup

LLO Desktop Agent online; vorheriger KNX017 vollständig geschlossen; HEAD `c171d17`, sauberer Git-Tree. Aktuelles ETS-Produkt ApplicationVersion **2**, **35 KO und 21 Parameter**. Die alten motorbezogenen Objekte KO1..16 (DPT9.001) und KO17..24 (DPT5.004) dürfen nicht stillschweigend zu Raumzonen-/DPT5.001-Objekten umgedeutet werden. T0..T8 sind Vorlauf-/Rücklaufsensorik, ausdrücklich keine Raum-Istwerte. KNX009 und KNX016 sind für eigenständige KNX-Testbench KNX018 deferred.

### Gate 2 – Designentscheidung

- Acht logische Zonen und acht Motoren; Zuordnung M1..M8 jeweils genau Zone 0 (unassigned) oder Zone 1..8. Beliebig viele Motoren einer Zone können denselben Zielwert erhalten; jeder Motor gehört höchstens einer Zone.
- ETS-Modus 0 Disabled, 1 RoomTemperature (externes KNX Soll-/Raum-Ist plus **erst später von KNX010 berechneter** Reglerausgang), 2 DirectPercent (DPT5.001 scaling byte 0..255). Keine automatische Quervermischung.
- Default alle Zonen aus und Motoren unzugeordnet; gültige Signale und Zeitstempel erforderlich. Bei stale/invalid/disabled **keine neue Fahranforderung**, aber physischer All-off und bereits laufende/gewartete Fahrten sind **KNX004/010**, nicht KNX008.
- ETS-ABI: Bestehendes AppVersion2 mit KO1..35 und P1..21 bleibt unverändert. Vorgeschlagen AppVersion3, KO36..100 und P22..39 mit eindeutigem C-Identifiern, DPT und überschneidungsfreiem Speicher ab Byte11. Kein ETS-Import, XML-/Headeränderung oder Busdownload.

### Gate 3 – Umsetzung

- [Heating zone C++ model](../../lib/common/heating_zone_model.hpp) ohne Arduino/KNX/GPIO-Anbindung prüft Konfiguration und Zeitstempel und fächert logische, noch nicht ausführbare 0..1000-Promille-Ziele auf 1..8 Motoren auf. Keine Motorbewegung.
- [Native tests](../../tests/native/test_knx008_zone_model.cpp) für 1/2/3/4 Motoren je Zone, 4+3+1 über acht Motoren, verschiedene Räume/Modi, echte 0%, raw5.001/legacy5.004-Verwechslung, ungültige Parameter, fehlende/stale Eingänge und `millis()`-Wraparound.
- [ETS contract JSON](../../assets/knx008_zone_ets_proposal.json) enthält 65 nur vorgeschlagene KOs und 18 nur vorgeschlagene ETS-Parameter; [read-only audit](../../tools/audit_knx008_zone_contract.py) gleicht das mit dem unveränderten Produkt V2 und seinen bestehenden Bitspeicherbelegungen ab.
- README, Roadmap und historisches Konzept ETS_AND_CONTROL_CONCEPT mit korrekter Ist-/Soll-Trennung und Dokumentlinks aktualisiert.

### Gate 4 – Tests und Einschränkungen

- **KNX008 C++ native: PASS**, die bisherigen **KNX013 zwei + KNX014 vier + KNX015 zwei = acht** Regressionstests ebenfalls **PASS** (zusammen neun Suites).
- **KNX008 ETS-Kontrakt-Audit PASS:** V2 App/KO1..35/P1..21 Byte-identisch zu Baseline, proposed-only-KO36..100/P22..39 ohne Kollisionen, DPT-Flags/Namen/ETS-Speicheroffsets prüfbar.
- Bestehender KNX015-Produktheader-Audit PASS, ATtiny/RP-Brücken-/PCB-Pinaudit PASS; **PCB/ETS-Static 0 Invariant-Fehler** mit den unveränderten Power-/Bestückungswarnungen. **ASH-Workflow PASS, 30 Checks, 289 lokale Markdown-Links vor Closing**. Native C++17 mit -Wall/-Wextra/-Werror/-pedantic; Python Syntaxprüfung PASS; gestagter `git diff --cached --check` PASS. Abschlussaudit nach Markerentfernung wiederholt.
- **Keine produktive ETS-XML/knxprod.hpp/Firmware geändert; kein Motor GPIO, keine physische Fahrt/KNX-Telegramme/ETS6-Import und kein GitHub-Push.**
- **Nächste technische Abhängigkeiten:** KNX004/005/006 für sichere Einzelmotorfahrten und Referenz, KNX010 für langsame echte Raumtemperaturregelung inkl. PI/Anti-Windup und Busfailover, KNX009/016 für ETS-Produktumsetzung/Import erst auf späterem KNX018-Testplatz. ASH öffnet keinen Folgeslice automatisch.
