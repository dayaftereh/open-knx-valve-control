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


## KNX019 – PI-Raumtemperaturregler nur als Offline-Simulation

- **State:** closed (Native-C++-Software-Gate, **keine** reale KNX-/ETS6-/Ventilfreigabe)
- **Date:** 2026-10-12
- **Baseline:** 025c84e, main clean, 18 lokale Commits ahead origin/main; kein fremder Write-Owner und keine offenen Marker
- **Implementation commit:** 89bd2cd – feat(knx019): simulate PI room control for eight KNX zones
- **Closing commit:** eigener ASH-HISTORY/ROADMAP-Commit mit Entfernung des KNX019-Markers
- **Engineering report:** [KNX019_ROOM_PI_SIMULATION.md](../KNX019_ROOM_PI_SIMULATION.md)

### Gate 1 – Checkup

LLO Desktop Agent 0.8.1 live erreichbar; vorheriger KNX008-Slice erfolgreich abgeschlossen. Das bestehende [KNX008-Zonenmodell](../../lib/common/heating_zone_model.hpp) erlaubt acht Zonen, exklusive Zuordnung eines Motors zu höchstens einer Zone und die Betriebsarten RoomTemperature/DirectPercent. ETS-Produkt V2 mit 35 KOs/21 Parametern ist erhalten. **KNX010** Vollintegration wäre gegenwärtig wegen KNX006/007/009-Abhängigkeiten unzulässig: KNX009/016 ETS-/Bustests sind auf Wunsch bis zur separaten KNX018-Testbench zurückgestellt.

### Gate 2 – Decision

Nur softwareseitige, native Regelungskernvorbereitung statt vollständige KNX010-Firmware: je Zone Eingang externer KNX-Raum-Soll-/Isttemperatur, diskrete PI-Rechnung auf 0..1000 Promille, wählbares Kp/Ti/Sampling/Deadband/Slew und Anti-Windup; die lokalen ATtiny-Rohrtemperaturen T0..T8 dürfen **nicht** automatisch als Raum-Istwerte gelten. Mode DirectPercent umgeht den PI. Bei Stale/Invalid/Mode-/Topologie-/Tuningwechsel, zu langer Regel-Loop-Pause: validen Ausgang entwerten, Integrator resetten und frische externe Telegramme vor erneuter Freigabe verlangen. Nur neue Zielintents, kein physisches All-off oder Abschalten laufender Motorjobs.

### Gate 3 – Implementation

- [Native room PI reference](../../lib/common/room_pi_controller.hpp) mit acht unabhängigen Reglerzuständen, konfiguriertem 60s-Abtastzyklus (30..600), PI-Anti-Windup, Heiz-Stellwert 0..1000, konservativer Slew-Begrenzung, Deadband und Timeouts.
- Anschluss nur im RAM an [KNX008-Zielwertrouter](../../lib/common/heating_zone_model.hpp). Re-Konfiguration, including motor reassignment and timeout changes, invalidiert sämtliche alten Zonen-Outputs/Direct Commands als konservativer globaler Konfigurations-Epoch-Wechsel.
- [Native integration/simulations](../../tests/native/test_room_pi_controller.cpp) inklusive 8-Zonen-Unabhängigkeit, 2–4 Motoren je Zone, 0/100%, keine Modusvermischung, Kp-/Ti-/Grenzwerte, Deadband-Rauschen, Timing, Antiwindup, millis-Rollover, Revalidierung in verschiedener Telegramm-Reihenfolge.
- Synthetische zwei-Raum-48h-Plant mit 4h thermischer Zeitkonstante, 15%-Kopplung und 2%-Punkte/min Begrenzung ergab Zone1 21,60°C (Soll21,5°C), Zone2 20,10°C (Soll20°C). **Nur ein didaktisches deterministisches Beispiel, keine Bestätigung realer Regelgüte/Tuning/Stabilität**.
- [Test runner](../../tools/test_room_pi_controller.py), [unmodified KNX/ETS/firmware audit](../../tools/audit_knx019_room_pi.py), README/Roadmap/KNX008/ETS-Konzept/Testbench-Doku aktualisiert.

### Gate 4 – Validation

- KNX019 native C++17 mit -Wall/-Wextra/-Werror/-pedantic: PASS, echte PI-Klasse + KNX008 Router + Stör- und thermische Simulation.
- KNX008 native 1, KNX013 native 2, KNX014 native 4, KNX015 native 2: **alle bestehenden 9 Suites PASS**. Insgesamt **10 native Suites** mit KNX019.
- Baseline-Vertrag: ETS-XML V2, generierter Header, KNX008 proposed-only JSON und KNX008 C++-Router, RP2040-/ATtiny-Quellmain sowie Publisher/Bridge **byte-identisch** gegen 025c84e (CRLF-normalisiert). Kein Product-XML-/Firmware-Edit.
- KNX008 ETS proposed contract PASS; KNX015 product audit PASS; KNX013/014 Pin/UART static PASS; PCB/ETS static PASS mit 0 Invariant-Fehlern (bekannte 5V-, Shunt-, U25-/BOM-Risiken bleiben).
- **ASH audit 30 Checks PASS, 311 Markdown-Links vor Closing**; Python compile PASS, staged Git diff --check PASS. Endaudit nach Closing wiederholt. Eigene Cygwin-Crash-Stacktrace-Datei aus einem korrigierten Testlauf sicher beseitigt; keine fremden Artefakte berührt.
- Kein realer KNX-Bus-/ETS6-Import, keine Platine versorgt/geflasht, kein Motortest, keine GitHub-Pushes.

### Offene Hardware-/Implementierungs-Gates

- Für echte KNX010-Raumregelung: ETS V3/KO-Nummerierung im KNX009-Slice und KNX018-Testbench nach Freigabe, echtes Telegramm- und Bus-Recovery, Frostschutz, hydraulische Kalibrierung und unabhängige Heizquellen-Schutzfunktionen.
- Für Motoren: KNX002/003 as-built/Power, KNX004 sichere Einzelmotor-Fahrqueue, KNX005 Strom/Endlagenmessungen und KNX006 Homing/Position; der KNX019-Code ist **kein** Ersatz für Motor-Sicherheitsmaßnahmen.
- Folge-Slices nur mit neuem ASH-Checkup und ausdrücklichem Start; KNX009/016 bleiben deferred.


## KNX020 – Exklusive Motorfahrqueue nur als Offline-Simulator

- **Status:** closed (Native-C++-Simulator, KEINE Hardware-Freigabe)
- **Datum:** 2026-10-12
- **Baseline:** 386d305, main clean, 20 lokale Commits ahead origin/main, kein offener fremder ASH-Slice
- **Implementierungscommit:** 2e18813 – feat(knx020): simulate exclusive eight-motor motion queue
- **Closing-Commit:** separater HISTORY/ROADMAP-Commit mit Entfernung des KNX020-Open-Markers
- **Technischer Bericht:** [KNX020_MOTOR_QUEUE_SIMULATION.md](../KNX020_MOTOR_QUEUE_SIMULATION.md)

### Gate 1 – Verifikation

LLO Desktop Agent 0.8.1 live verfügbar. KNX019 und KNX008 abgeschlossen, HEAD 386d305 und sauberer Git-Tree. Produktion: acht Motor-Ausgänge an TB6612FNG mit gemeinsamen Richtungssignalen und einer geteilten INA219-Strommessung. Reales As-built, externes 5-V-/KNX-Strombudget, Motorpolung, Referenzzeiten und Hardware-All-off ungeprüft. KNX004 ist deshalb weiterhin planned und wird durch KNX020 ausdrücklich nicht geschlossen. KNX009/016 (ETS6/KNX-Bus) deferred für separate KNX018-Testumgebung.

### Gate 2 – Konservativer Simulationsvertrag

Ein reiner C++-Zustandsautomat reserviert den exklusiven Motor-Lease **vor** einem abstrakten Start-Event. Automatischer Start nach Boot deaktiviert; fünf simulierte Safety-Guards, ausdrückliche Testfreigabe und unabhängig bestätigtes All-off nötig. Jeweils neue KNX008-Zielintents, virtuelle Referenzpositionen und fiktive kalibrierte Motorlaufzeiten werden geprüft. Laufzeit/Position und Stromgrenzen sind Testparameter, keine Messwerte vom HmIP-VDMOT.

### Gate 3 – Implementation

- [Portable Motor Queue](../../lib/common/motor_queue_simulator.hpp): Disarmed, Idle, StartPending, Running, StopPending, FaultLatched; tokenisierte Start-/Stop-/All-off-Quittungen, Stop-Wiederholung, Timeout, blockierte Folgefahrten bis zum Off-ACK, Round-Robin und Totzeit, Re-Arm-Pflicht bei Target-Stale/Mode-Wechsel/Fault.
- [Funktionstests](../../tests/native/test_motor_queue_simulator.cpp): alle acht Motoren sequenziell, ACK-Token-Mismatch, Stopp ohne Off-Bestätigung, Referenz-/Positionsrevisionen, Fault, Status und Stale, KNX008-Router-integrierter Zustand, Zeitüberlauf, Cancel, Start-/Stop-Timeout.
- [Deterministischer Stress-Test](../../tests/native/test_motor_queue_stress.cpp): 20.000 Ticks mit veränderlichen Zielwerten, Guard-Ausfällen, ACKs und Motor-Exklusivitäts-Invariante (höchstens ein abstrakter Motor aktiv).
- [Native Runner](../../tools/test_motor_queue_simulator.py), [Nonintegration-Quellcodeaudit](../../tools/audit_knx020_motion_offline.py), README/Roadmap/KNX019-Dokulinks aktualisiert.
- Produktionsquellen und ETS V2 (35 KO/21 Parameter), KNX008/KNX019-Libs, RP2040-/ATtiny-Quellen, Controller-Config und PCB V1.2 wurden nicht verändert.

### Gate 4 – Abnahme und Grenzen

- KNX020 **2 Native-C++-Suites PASS**. Belastungsprobe 20.000 Ticks, 703 abstrakte Starts, 702 bestätigte Stopps und **maximal 1** simultan belegter Motor-Lease; eine unvollendete letzte Fahrt am Ende des Zeitfensters ist möglich.
- KNX019 native1, KNX008 native1, KNX013 native2, KNX014 native4, KNX015 native2: alle **10 bestehenden** Suiten PASS. Zusammen **12 native C++ Suiten** mit KNX020.
- KNX020 Offline-Source-/ETS-/PCB-Immutable-Audit PASS; KNX008 vorgeschlagener ETS V3 Kontrakt PASS, KNX015 produktive V2-ABI unverändert PASS.
- ASH-Workflow **30 Checks und 331 Markdown-Links vor Closing PASS**; PCB-/ETS-Static 0 Invariant-Fehler mit den bekannten elektrischen 5-V-/U25-/R29- und DPT5.004-Warnungen. Python-Syntax und gestagter git diff --check PASS.
- Kein physischer Start oder Stopp, keine realen GPIO-Pegel, kein gebrückter STBY, keine KNX-Telegramme, kein ETS6-Import, keine Firmwareänderung, kein Boardflash, kein Push. Simulation kann keine Hardware-Notabschaltung garantieren.

### Nächste echte Voraussetzungen

KNX002/003: Bestückung, 5-V-/3,3-V-/KNX-Pfad und sichere Leistungsreserve prüfen; KNX004: Hardware-Interlock, Off-Annahme und Watchdog bauen; KNX005/006: Motorstrom-/Endlagenkurve, Laufzeit und Positionsreferenz vermessen; KNX018: unabhängigen KNX-Bus mit echter Platine aufbauen, dann KNX009/016; KNX010-Regelung später integrieren. Folge-Slices nur nach neuem ASH-Checkup. Hier wurden nur Hardware-**unabhängige** C++-Tests durchgeführt.


## KNX021 – End-to-End-Integrationstest als reines Softwaremodell

- **State:** closed – nur native Software-/Mock-Abnahme; **keine reale KNX-/Motor-Freigabe**
- **Datum:** 2026-10-12
- **Baseline:** 8dc7577, main clean, 22 lokale Commits ahead origin/main; keine fremde Write-Session/kein offener Marker
- **Implementierungscommit:** e9a82d2 – test(knx021): integrate room PI zones and exclusive virtual motor feedback
- **Closing-Commit:** gesonderter HISTORY-/ROADMAP-Commit mit Entfernung des KNX021-Markers
- **Technische Dokumentation:** [KNX021_END_TO_END_SIMULATION.md](../KNX021_END_TO_END_SIMULATION.md)

### Gate 1 – Live-Baselineprüfung

LLO Desktop Agent 0.8.1 erreichbar; KNX020 sauber geschlossen und Git HEAD 8dc7577. Vorhandene KNX019-Raumregelung, KNX008-Zonenrouter, KNX020-Exklusivfahrqueue separat getestet. KNX002/003 echte Bestückungs-/Versorgungsgates, KNX004–006 Motorhardwaregates, KNX018 separater KNX-Testplatz und KNX009/016 ETS-Import weiter **nicht** abgenommen.

### Gate 2 – Scope / Entscheidung

Nur die vorhandenen portablen C++-Klassen **in einem gemeinsamen Testpfad** verwenden und eine neue, streng hardwarefreie Feedback-Schicht ergänzen. Die virtuellen Positionsdaten werden beim angenommenen planmäßigen Ende **erst nach STOP-All-off-ACK** aktualisiert; bei unplanmäßigem Abbruch sind valid/referenced falsch und ein weiterer Start benötigt explizit neue Referenzevidenz. Fehlende Stopp-Quittung oder ein als belegt simulierter Motorplatz blockiert neue Motorstarts. Keine Produktion-XML/Header-/Firmware-/PCB-Änderungen oder Hardwarebewegung.

### Gate 3 – Umsetzung

- [VirtualMotor::Backend](../../lib/common/virtual_motor_feedback.hpp) konsumiert abstrakte KNX020-Events, produziert tokenisierte simulierte START-/STOP-AllOff-ACKs, hält abstraktes Ausgangsbelegungsbit und Positions-Evidenz mit Revisionsnummer; simuliert abgebrochene Fahrt, fehlende STOP-Quittung und blockiertes Abschalten.
- [KNX021 Native Test](../../tests/native/test_knx021_end_to_end.cpp) führt **tatsächliche KNX019 PI-Klasse → KNX008 resolve → KNX020 Queue → VirtualMotor Backend** als gemeinsames Programm aus, einschließlich Sensor-Stale, Referenzverlust, manuellem Re-Arm, fehlendem All-off-ACK, ausgangsseitig blockiertem STOP und 32-Bit-Zeitüberlauf. Ergebnis M1/M2/M3 = 502/502/30 Promille nach **3 simulierten Starts und 3 Off-ACKs**; die Ergebnisse sind fiktive Sollpositionen, nicht gemessen.
- [Native Runner](../../tools/test_knx021_end_to_end.py) kompiliert C++17 mit -Wall/-Wextra/-Werror/-pedantic und führt den Test isoliert aus.
- [Quellschutz-Audit](../../tools/audit_knx021_e2e.py) sichert ETS/XML/knxprod.hpp, PCB V1.2 und die produktiven RP2040-/ATtiny-Quellen plus alte KNX008/019/020-Libs byteweise (LF/CRLF-normalisiert) gegen Baseline 8dc7577 ab; verbietet im virtuellen Backend jegliche KNX/UART/GPIO/PWM-Zugriffe.
- README, KNX020-Querverweis und Roadmap aktualisiert.

### Gate 4 – Qualitätsnachweis und Einschränkungen

- **KNX021 native End-to-End-C++-Simulation PASS**, einschließlich aller Ausfallszenarien; die virtuelle Ausgangs-Bitmaske belegt bei jedem Schritt höchstens einen Motor und ist immer durch den aktuellen exklusiven Queue-Lease gedeckt.
- **Zwölf bisherige native Regressionstestsuites PASS:** KNX008 1, KNX019 1, KNX020 2, KNX013 2, KNX014 4, KNX015 2. Zusammen mit KNX021 sind **13 native Suites PASS**.
- KNX021 produktiver Quellschutz PASS; KNX008 ETS-Entwurf und KNX015 aktuelle ETS V2-Produkt-ABI PASS. ETS XML AppVersion2, 35 KOs/P1..21 bleiben unverändert.
- ASH-Workflow **30 Prüfungen, 347 lokale Markdownlinks vor Closing PASS**, PCB-/ETS-Statikaudit 0 Invariant-Fehler (bekannte 5-V-/U25-/R29-/DPT5.004-Warnungen bestehen), Python-Syntaxprüfung PASS und gestagter git diff --check PASS. Nach Markerentfernung erneuter ASH-Audit.
- Keine Platine versorgt, kein Motor angesteuert, kein Firmwareflash, keine KNX-Bustelegramme oder ETS6-Importe, kein GitHub-Push.

### Folgearbeit bleibt hardware-gated

KNX002 Bestückung und KNX003 KNX-/5-V-/3,3-V-Schutz prüfen; KNX004 unabhängigen HW-All-off-/Watchdog-/STBY-Interlock implementieren; KNX005/006 Motorpolung, HmIP-VDMOT-Strom-/Endlagen-/Referenzmessungen durchführen. KNX018 echte KNX-Testbench separat bereitstellen und KNX009/016 ETS6-/Bustests dort wieder aufnehmen. KNX010 volle produktive Raum-/Motorregelung folgt erst nach den Abhängigkeiten. Ein **virtueller** Quittungstest darf nie als reale Hardware-Sicherheitsfreigabe verwendet werden.


## KNX022 – V1.2 Hardware Readiness / PCB-BOM-Firmware-Quellenabgleich

- **State:** closed – nur ein nachvollziehbarer statischer Quellenprüf-Slice; bestückte Hardware und realer Motorbetrieb **NOT READY**
- **Datum:** 2026-10-12
- **Baseline:** 4d12890 / main clean, 24 lokale Commits vor origin/main, keine konkurrierenden Write-Sessions und keine offenen ASH-Marker
- **Implementierungscommit:** 9adb183 – docs(knx022): audit V1.2 hardware blockers against schematic PCB and firmware
- **Closing commit:** gesonderter Commit für HISTORY, Roadmap und Entfernung des offenen KNX022-Markers
- **Technischer Bericht:** [KNX022_STATIC_HW_READINESS.md](../KNX022_STATIC_HW_READINESS.md), [JSON-Blockerregister](../KNX022_STATIC_HW_PREFLIGHT.json)

### Gate 1 – Checkup

LLO Desktop Agent 0.8.1 am Projekt-Root live verifiziert, Git HEAD 4d12890 clean. V1.2 EasyEDA-Schaltplan/PCB-JSON, Controller config/main, ATtiny-PlatformIO-Target und frühere Stromversorgungs-/PCB-Reviews geprüft. **Keine Fotos der tatsächlichen Bestückung, reale Motor-Strom-/Spannungs-Messkurven oder native EasyEDA ERC/DRC/BOM im vorliegenden Repo.** KNX002 bleibt geplant und physisch unabgenommen.

### Gate 2 – Entscheidung

KNX022 trennt konsequent Quellenbefunde von realen Hardwarefreigaben: BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR ist das zwingende Ergebnis auch bei bestandenem Software-Audit. Keine Änderung an EasyEDA V1.2, KNX XML, RP2040-/ATtiny-Firmware, Platine oder externen Versorgungen; keine KNX-/GPIO-/Motoraktion.

### Gate 3 – Implementation

- [Quellenbasierter HW-Auditor](../../tools/audit_knx022_hw_preflight.py) liest PCB-Netze und Herstellerteilenummern aus JSON, Schaltplan-Anzeigewerte, RP2040-D10..D19-Pinbelegung und ATtiny3216-PlatformIO-Ziel; SHA256-Eingangsbelege im [JSON](../KNX022_STATIC_HW_PREFLIGHT.json). **35 statische Invarianten PASS**, bei weiter gesperrter Motor-Inbetriebnahme.
- [In-memory Negativtests](../../tests/test_knx022_hw_preflight.py): 15 künstliche Designabweichungen (STBY, R29, Q1/JMP1/D6/U6, INA219, RP2040-Pinplan, ATtiny-Ziel, Schaltplanannotationen und neue Motor-GPIO-Nutzung) erkannt; Korrektur bloßer Einkaufsmetadaten bewirkt keine reale Freigabe.
- [Readiness-Bericht](../KNX022_STATIC_HW_READINESS.md) priorisiert 10 Blocker (9 P0, 1 P1): R29 200mOhm vs SCR1206F1M1, U25 ATtiny3216 vs ATTINY1616-SN, F1 630mA vs S1032-F-60.0A, vier TB6612-STBY Pin19 fest an 3.3V statt unabhängigem MCU-Kill, KNX/USB-Headroom und Backfeed, STKNX-Leistungsbudget, fehlende Boot-All-off-Messungen, geteilte INA219/Richtung und fehlende native ERC/DRC-/As-built-BOM.
- README, Roadmap, PCB-V1.2-Bericht und KNX021-Doku mit Verweis aktualisiert, ohne einen realen Gateabschluss vorzutäuschen.

### Gate 4 – Validierung

- Report-Reproduktion PASS, 35 PCB/Schaltplan/Firmware-Checks PASS, 15 Negativtests PASS; physischer Readiness-Status bleibt ausdrücklich BLOCKED.
- PCB-/ETS-Statikaudit 0 Invariant-Fehler, bestehende 5V/U25/R29/DPT5.004-Warnungen bleiben. KNX020 (2 native Suites) und KNX021 (1 native Suite) PASS.
- ASH-Workflow 30 Checks, 371 lokale Markdownlinks vor Closing PASS; Python Syntax PASS, gestagter git diff --check PASS. Audit nach Entfernen des Markers wiederholt.
- Keine Bestromung, kein Motor, keine Firmware-Programmierung, kein ETS6-/KNX-Bustest, kein GitHub-Push.

### Next Exact Action

**KNX002 bleibt planned**, ohne neuen automatischen Slice. Für reale Freigabe zuerst stromlose Fotos der Revision, R29/U25/F1/JMP1/Power-Pfad und tatsächliche Bestückungs-BOM, native EasyEDA ERC/DRC-/Netzlisten-Daten sowie eine geplante, qualifizierte **motorlose** KNX003-Versorgungsmessung. Für reale Fahrten zusätzlich KNX004-Hardware-All-off und KNX005/006 Motor-Strom-/Referenzabnahmen. V1.2 ist weiterhin nicht zur motorischen Inbetriebnahme freigegeben. KNX009/016 bleiben deferred bis KNX018.


## KNX023 – Laptop-/RTS-UPDI-Handover und hardwareinaktive RP2040-Softwareintegration

- **Status:** closed, Stand 2026-10-12 – **nur Softwaremodell und echter isolierter PlatformIO-Firmware-Build; KEINE Hardware-Motorfreigabe**
- **Repo:** C:\ASH\Workspace\Projects\open-knx-valve-control, main, Baseline 3b47fa7 (clean, 26 lokale Commits vor origin/main)
- **Eigentümer / Session:** ChatGPT-OpenKNXValveControl-KNX023-20261012 / ses-20261012T110701-938ee188aa65
- **Implementierungscommit:** 7796b5a – feat(knx023): add disarmed firmware room pipeline and laptop UPDI testbench plan
- **ASH Closing-Commit:** separater HISTORY/ROADMAP-Commit mit Entfernung des KNX023-Markers
- **Doku:** [KNX023_FIRMWARE_SOFTWARE_RUNTIME.md](../KNX023_FIRMWARE_SOFTWARE_RUNTIME.md), [KNX018_LAPTOP_UPDI_TESTBENCH.md](../KNX018_LAPTOP_UPDI_TESTBENCH.md)

### Gate 1 – Ausgangslage und Live-Verifikation

Desktop Agent 0.8.1 erreichbar, alle vorherigen KNX-Sessions geschlossen, keine fremde Write-Session. Git main sauber HEAD 3b47fa7; genau null vorhandene _OPEN Marker. Produktiv-RP2040 (KNX014/015) sendet Temperaturtelemetrie/Diagnosen und hat noch keine externe KNX008/019-Raumeingangsumsetzung oder Motor-GPIO-Treiber. KNX008/019/020/021 liegen als getrennte C++-Referenzmodelle vor. KNX022 V1.2 HW preflight zeigt zehn offene elektrotechnische Risiken, u.a. STBY aller vier TB6612 fest auf 3.3V. KNX002/003/004/005/006 und KNX018 real ungeprüft.

### Gate 2 – Freigegebener rein softwareseitiger Scope

Persistenter **geplanter Laptop-KNX018-Teststand**: Laptop mit eigenem ASH Agent im KNX/IP-Netz; RP2040 per USB; ATtiny per zweitem USB-Port durch selbst entwickelten Units-V1.2-CH340G-Programmer mit RTS-gesteuerten U2/U7 SN74LVC1G3157 Umschaltern zwischen UPDI und UART. ATtiny mit DS18B20 T0 (Vorlauf) und T1..T8 (Rückläufe); interner Temperatur-Link verwendet **andere USART0-ALT1-Pins** als Debug CN1. Motor M1 erst nach separater Hardwarefreigabe. Dokumentiert **beidseitigen sechspoligen CN1-Netzvergleich**, insbesondere **Programmer CN1.1 USB-Versorgung/D1 ↔ Target CN1.1 5V**, Target-U25-VCC 3.3V, Signallevel-/Backfeed-Prüfung und mechanische Pin1-Auslesung zwingend vor Direktverbinden. Programmiertarget ATtiny3216 lt. Firmware vs. ATtiny1616-SN PCB-Metadaten: echte Signatur zuerst non-destructive. Laptop Units altes Repo/Branch, OpenKNX noch nicht auf Laptop; unpushed Desktop-Commits per Git-Bundle sicher übertragen, nicht durch altes origin/main ersetzen.

### Gate 3 – Implementierung

- [Firmware-RAM-Pipeline](../../lib/common/room_control_runtime.hpp) integriert **echte** RoomPi::Bank (KNX019), HeatingZone::resolve (KNX008), MotorQueueSim::Queue (KNX020) und ausschließlich in *nativen* C++-Hosttests VirtualMotor::Backend (KNX021). Default alle Modi disabled/alle Motoren unzugeordnet/Inputs invalid und Queue Disarmed. **Beim kompilierten ARDUINO-RP2040 wird der virtuelle Backend ausgeschlossen, Arm- und Position-Injektionsaufrufe liefern IMMER false.** Keine echte Queue-Fahrfreigabe.
- [controller main.cpp](../../src/controller/main.cpp) initialisiert RoomControlRuntime in Setup, berechnet PI/Targets **nur im RAM** alle mindestens 100 ms, ohne GroupObject-Änderung oder Motor-GPIO-Zugriff. Temperatur-UART/KNX-TP-Schnittstellen und KNX015-Produkt unverändert.
- [Laufzeittests](../../tests/native/test_knx023_room_control_runtime.cpp) mit drei synthetischen Motoren (M1/M2 direkt = 502 Promille, M3 Raum-PI = 30 Promille), drei synthetischen Start-/AllOff-Quittungen, Safe-Rearm-/Stale-/Timeout-/Reboot-Fällen.
- [Arduino-Preprocessor-Hardlock](../../tests/native/test_knx023_firmware_hardlock.cpp) prüft native mit ARDUINO-Definition, dass keine synthetische Motor-Armierung oder Position-Injektion überhaupt möglich ist.
- [Test-Runner](../../tools/test_knx023_room_control_runtime.py) kompiliert beide Suites mit C++17 -Wall/-Wextra/-Werror/-pedantic; [Nichtansteuerungs-Quellenaudit](../../tools/audit_knx023_firmware_offline.py) verifiziert nur additiv verändertes main.cpp, ARDUINO compile-fence und unveränderte ETS-/PCB-/ATtiny-Dateien gegen 3b47fa7.
- [Laptop-Teststand](../KNX018_LAPTOP_UPDI_TESTBENCH.md) und bestehender [KNX-Testbenchplan](../KNX_TESTBENCH_PLAN.md), README/Roadmap ergänzt.

### Gate 4 – Tatsächliche Abnahmetests

- **Isolierter controller PlatformIO RP2040 Build PASS**, native OpenKNXproducer-Komponente; UF2 erzeugt unter temporärem, NICHT gepushtem C:\Users\LLO\AppData\Local\Temp\openknx-controller-isolated-bi62ip4j\.pio\build\controller\firmware.uf2. Kanonisches include/knxprod.hpp unverändert. RAM **53.452 / 262.144 (20,4 %)**, Flash **192.708 / 1.048.576 (18,4 %)**.
- **KNX023 zwei neue Native-C++-Suites PASS**, einschließlich Arduino-compile-hardlock. **13 zuvor bestehende** Native-C++-Suites KNX008(1), KNX019(1), KNX020(2), KNX021(1), KNX013(2), KNX014(4), KNX015(2) alle PASS; insgesamt **15 Suites**.
- KNX023 Nichtansteuerungs- und ABI-Quellenaudit **PASS**, KNX008 ETS v3 Entwurf **PASS**, KNX015 Produkt V2 KO/P-ABI **PASS**, PCB/ETS static 0 Invariant-Fails mit weiterhin bekannten Hardwarewarnungen. KNX022 Live-Quellenaudit **35 PASS, 10 BLOCKED** (historischer JSON-Hash-Stand vor KNX023; bei gewolltem neuen main.cpp nicht --check-report gegen altes KNX022-Snapshot anwenden).
- ASH vor Closing **30 Prüfungen / 396 lokale Markdown-Links PASS**, Python-Syntax PASS, git diff --cached --check PASS; Closing-Audit nach Markerentfernung gesondert.
- **Nicht durchgeführt:** Laptop-Repo-Migration, Netz-KNX-IP-Discovery, USB-/UPDI-Signatur/Flash, Boardstromversorgung, KNX-Bustelegramme, ETS6-Import, Motorfahrt, Bestellungen oder GitHub-Push.

### Nächste abgrenzte Aufgaben

KNX023 SOFTWARE-only ist abgeschlossen. **Keinen automatischen Folge-Slice starten.** Als weiterer softwareseitiger Slice ist die offline ETS-Raumeingangs-/DPT5.001-Kontraktbindung mit eigenem Simulationsadapter denkbar, aber produktive KO17..24 sind noch DPT5.004 und dürften nicht stillschweigend umgedeutet werden. Der physische KNX018-Laptop-Teststand benötigt zunächst sicheren Git-Transport einschließlich der lokalen Commit-Historie und danach KNX-/USB-Inventur. CN1.1 5V-Rückspeisepfad und UPDI 3.3V-Pegel prüfen, keine Direktverkabelung aus Netznamen ableiten. KNX002–006 Hardware-Qualifikation bleibt Voraussetzung vor jeder realen Motorbewegung. ETS6 KNX009/016 deferred.


## KNX024 – ETS-V3-Raumeingangsvertrag und DPT9.001/5.001 Offline-Adapter

- **Stand / Status:** 2026-10-12 / closed, ausschließlich Software-/Build-Abnahme. **KEIN** realer ETS6-Import, keine KNX-Gruppenadressbindung, keine Motorbewegung oder zusätzliche Firmware-GPIO-Freigabe.
- **Repo:** C:\ASH\Workspace\Projects\open-knx-valve-control, main, saubere Baseline 99d7244 mit 28 lokalen unpublizierten Commits gegenüber origin/main.
- **Session:** ses-20261012T115932-b5e39af35663, owner ChatGPT-OpenKNXValveControl-KNX024-20261012
- **Implementierungscommit:** 23e29db – feat(knx024): add proposed room DPT9 and DPT5 typed offline KO adapter
- **Closing-Commit:** gesonderter HISTORY/ROADMAP- und Markerentfernungs-Commit (Git HEAD danach verifizieren)
- **Spezifikation:** [KNX024_ETS_ROOM_INPUT_CONTRACT.md](../KNX024_ETS_ROOM_INPUT_CONTRACT.md) und weiter unverändert [KNX008 ETS Proposal JSON](../../assets/knx008_zone_ets_proposal.json)

### Gate 1 – Verifizierter Ausgangspunkt

LLO Desktop Agent 0.8.1 live, Git clean HEAD 99d7244 main 28 ahead, null offene Slice-Marker, alle vorherigen Sessions closed. KNX023 RAM-Pipeline in echter RP2040 Firmware und Arduino-Motor-Hardlock vorhanden, ETS XML weiterhin V2/35 Kommunikationsobjekte KO1..35 und P1..21, vorgeschlagener KNX008 AppV3-Vertrag KO36..100/P22..39 nur JSON, KNX009/016 echte ETS/KNX-Gates bewusst deferred. KNX018 eigenständiger Laptop-/KNX-Bus-Teststand nicht aufgebaut; KNX022 V1.2 Hardware-Readiness weiterhin gesperrt.

### Gate 2 – Ausschließlich Software-DPT-/ABI-Entscheidung

Portabler Offline-Adapter für die je acht vorgeschlagenen KOs:
- Z1: KO36 Soll Raum (DPT9.001 RX), KO37 Ist Raum (DPT9.001 RX), KO38 Direkt DPT5.001 (RX), KO39 RequestedOutput DPT5.001 (TX).
- Z2..Z8 analog +4 bis KO64/65/66/67; 24 RX und 8 nur synthetische TX-Kodierungen.
- DPT9.xxx nach KNX Association 2-Byte Float Vorzeichen/Exponent/Mantisse 0,01°C, 0x7FFF ist invalid. Raum-Soll 5..35°C, Raum-Ist -40..80°C aus bestehendem KNX008-Modell. DPT5.001 1 Byte 0..255 auf 0..100% (Permille), **nicht** DPT5.004 0..255% der alten produktiven KO17..24.
- Bus-GroupValueWrite enthält kein DPT-Typfeld: Adapter erwartet eine spätere **trusted** ETS-/GA-gebundene KO-Nummer samt DPT-Metadaten und die bereits dekodierte Payload, keine ungesicherten Busrohbytes; noch KEIN echter Listener.
- Keine Produktmigration vor isolierter ETS6-Prüfung, kein KNX-, GPIO-, UPDI- oder Motor-Hardware-Test.

### Gate 3 – Umsetzung

- [Portabler KNX024 Room Adapter](../../lib/common/knx024_room_dpt_adapter.hpp): in-memory AppV3-DPT-/KO-Parser mit KOs36..67, 24 RX-Mapping, TX-outbound Serializer nur als Bytes, DPT9-Sentinel-/Grenzenprüfung und exakte 5.001-Skalierung, Input-Frische, Modus-, Reassign- und Boot-Barrieren, invalidiert kaputte aktive Rauminputs statt letzte Werte heimlich weiterzubenutzen.
- [Room Runtime](../../lib/common/room_control_runtime.hpp) nur mit zwei zusätzlichen const-Accessoren (Settings/Inputs); KNX023-PI/Queue/Aktor-Hardlock funktional unverändert.
- [src/controller/main.cpp](../../src/controller/main.cpp) inkludiert das KNX024-Modul und prüft KO36–67 per static_assert. **Keine** Instanziierung von Live-V3-KO-Receivern, weil ETS-AppV2 diese Objekte nicht besitzt; keine neue Motor-GPIO-/KNX-Bus-Ansteuerung.
- [2 Native-C++-Suites](../../tests/native/test_knx024_room_dpt_adapter.cpp) samt [Arduino-Hardlock-Suite](../../tests/native/test_knx024_firmware_hardlock.cpp) und [Runner](../../tools/test_knx024_room_dpt_adapter.py): acht Zonen, DPT9 negatives/positives Vorzeichen/Exponent/Invalid-Wert, 1/2-Byte-Fehler, 5.004-Wrong-DPT, Zeitablauf und millis-Wrap, PI in Z1 mit 2 Motoren, Konfig-/Reboot-Verlust, synthetischer KO39-Output, Compile-Sperre aller realen Motorstarts.
- [ETS-/Quell-ABI-Audit](../../tools/audit_knx024_room_ets_contract.py) verifiziert die unveränderte KNX008-JSON-Proposal mit 65 KO36..100 und P22..39, unveränderte produktive ETS/ATtiny/PCB Dateien, nur additiv ergänzte Firmware und keinen Motor-I/O-Aufruf. [13 KO-/DPT-Regression-Negativfälle](../../tests/test_knx024_room_ets_contract.py) simulieren falsche DPT, direction, size, KO/Parameternummer, Alt-KO5.004 und unzulässige Promotion nur im RAM.
- README, KNX008-/KNX023-Doku und Roadmap mit KNX024-Weiterführung ergänzt.

### Gate 4 – Validierung und harte Grenzen

- **KNX024 2 neue Native-C++-Suites PASS**, **15 bestehende** KNX008/013/014/015/019/020/021/023 Native-Suites PASS, zusammen **17**. **13 separate Python-Vertrag-Negativtests PASS**.
- KNX024 strict ETS/ABI/No-Motor-IO-Audit PASS, KNX023 alter Non-Actuation-Audit PASS, KNX008 proposed ETS P22..39 und KNX015 produktives ETS-V2 KO1..35/P1..21 AUDIT PASS, Python py_compile PASS.
- **Isolierter echter RP2040 PlatformIO-Controller-Build PASS**, UF2 erzeugt ausschließlich unter C:\Users\LLO\AppData\Local\Temp\openknx-controller-isolated-jq6g6jji\.pio\build\controller\firmware.uf2, Quell-knxprod.hpp unverändert, **RAM 53.452/262.144 = 20,4 %, Flash 192.708/1.048.576 = 18,4 %**. Kein USB-RP2040-Flash.
- KNX022 Re-Preflight 35 statische PCB/Schaltplan/Firmware-Invarianten PASS mit weiterhin **10 offenen Hardware-Blockern** und Status BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR. PCB/ETS-Statikaudit 0 Invariantfehler, elektrische/ETS-Importwarnungen unverändert.
- ASH vor Schließen **30 Prüfungen mit 427 lokalen Markdownlinks PASS**, Closing-Validierung nach Markerentfernung wiederholt, git diff --cached --check PASS.
- **Nicht getestet/verbunden:** keine Live-GAs, keine echte ETS6-Promotion von AppV2 zu AppV3, kein KNX-Testbus, kein RP2040/ATtiny-Flash oder USB-UPDI-Signatur, keine Motorsicherheit/Referenzfahrt, kein GitHub-Push.

### Nächste konkrete Arbeit / Freigabegrenzen

KNX024 nur als **reiner Software-Slice** geschlossen. Für spätere echte Verarbeitung müssen über KNX018 (separater Laptop-Agent mit KNX/IP und UPDI-RTS) real geprüft werden: Stromversorgung, typisierte ETS-Kommunikationsobjekte und parametrierte Gruppenadressbindungen, neue AppVersion und Erhaltung der 35 Alt-KOs, dann Live-GroupValueWrite und später rein virtuelle Bus-Tests. Nachfolgende KI-Software-Slices können weitere Offline-Fehlerzustände/HMI vorbereiten, dürfen aber keine echten Motoren freigeben.

KNX002/003/004/005/006 bleiben physisch nicht abgenommen; TB6612-STBY auf V1.2 ist fest an 3,3 V und der virtuelle AllOff-ACK keine Hardware-Sicherheitsfreigabe. KNX009/016 bleiben deferred, KNX018 geplant. **Kein automatischer Folge-Slice**, keine externen Repository-Pushs.


## KNX025 – Software-Faultsupervisor und kontrollierter Wiederanlauf ohne Motorhardware

- **Stand / State:** 2026-10-12 / closed, ausschließlich portables Software-/Build-Gate. **Keine** echte KNX-/ETS6-, Watchdog- oder elektrische Motor-Abnahme.
- **Root:** C:\ASH\Workspace\Projects\open-knx-valve-control, main, clean baseline 044eac5 (30 lokale Commits ahead origin/main) vor KNX025.
- **Owner / Write-Session:** ChatGPT-OpenKNXValveControl-KNX025-20261012 / ses-20261012T124927-24a78824053f
- **Implementierungscommit:** 335d7e4 – feat(knx025): add fail-closed software fault recovery and passive RP2040 diagnostics
- **ASH Closing Commit:** gesonderter Commit für HISTORY / ROADMAP und Entfernung des KNX025-Markers
- **Technischer Bericht:** [KNX025_FAULT_RECOVERY_DIAGNOSTICS.md](../KNX025_FAULT_RECOVERY_DIAGNOSTICS.md)

### Gate 1 – Live verifizierter Ausgangszustand

Desktop-Agent 0.8.1 aktiv, Git main auf 044eac5 sauber und 30 lokale unpublizierte Commits voraus, null aktive Fremd-Writes, KNX024 geschlossen, kein offener Slice-Marker. Vorhandene KNX024-ETS-V3-KOs36..100 nur vorgeschlagen; aktuelles produktives ETS XML unverändert AppV2 (35 KO/P21, Alt-KO17..24 DPT5.004). KNX023 ist ein realer, aber **RAM-only** Firmware-Tick mit ARDUINO-hardcoded Motor-Disarmed. KNX022 zehn physische Hardwareblocker einschließlich TB6612-STBY permanent an 3.3V, KNX018 Laptop-Labor nicht aufgebaut, KNX009/016 echte ETS-Importtests deferred.

### Gate 2 – Abgesperrter Softwareumfang

KNX025 ergänzt nur einen Software-Wächter für den bereits getesteten reinen C++-PI/Zone/Queue/virtuellen Backend: Quelle fehlend/ungültig, DPT-Mismatch, Eingangstimeout, Konfig-/Motorzuordnungswechsel, explizit simulierter KNX-Raum-Transportverlust, manuelles Stoppsignal, Softwareloop-Verzug über 2000 ms und virtuelle Start-/Stop-/All-off-ACK-/Motor-Queue-Fehler. Der Anfangszustand **Unconfigured** ist kein Fehler. Manifold T0..T8-Temperatur-UART-Offline erzeugt **nur diagnostische Warnung**, da Rohr-/Rücklaufwerte keine externen Raumluft-Istwerte sind.

### Gate 3 – Eigentliche Implementierung

- [KNX025 Supervisor](../../lib/common/knx025_fault_supervisor.hpp) mit Phase Unconfigured/WaitingForFreshInputs/HealthySoftwareInputs/FaultLatched, enum Fault (InvalidConfiguration, InvalidRoomTelegram, RoomSourceExpired, DirectDemandExpired, RoomTransportLost, SoftwareLoopStalled, SoftwareConfigurationChanged, MotorQueueFault, MockBackendProtocolFault, OperatorEmergencyStop), sticky first fault mit Zone/Zeit, Countern, Masken der acht Zonen und virtueller Lease-/Queue-Diagnose. physicalOutputsVerifiedOff ist **immer FALSE**.
- Ein aktiver Fault setzt alle vorherigen **Software-Inputs** ungültig und ruft ausschließlich im nativen Simulator Queue-cancel auf. Bei laufender virtueller Fahrt bleibt die **gleiche lease/token** erhalten, STOP wird bis zum richtigen AllOff ACK wiederholt. Ein Timeout oder alter externer Room-Frame gibt keine Fahrt frei; im Test bleibt Re-Arm bis zur sicheren virtuellen Freigabe gesperrt.
- Nur ausdrückliche operatorAcknowledgement plus null leasedMotor und virtuell AllOff/kein Protokollfehler erlaubt **RAM-only** Recovery; auch dann geht der Supervisor auf Unconfigured zurück, verwirft Position, Zonenzuordnung, Soll-/Istwerte und fordert neue Konfiguration **und** neue Telegramme. Kein Auto-Rearm oder persistierter falscher Istwert.
- Schutz vor extern geänderter Konfiguration vergleicht sämtliche acht Zonenmodi, Motorzuordnung, Timings und maskierte Zone. Ein ausdrücklich als offline gekennzeichneter KNX-Raumtransport sperrt **auch beim allerersten** konfigurierten Steuerungstick.
- Die tatsächliche RP2040-Firmware [main.cpp](../../src/controller/main.cpp) instanziiert den Supervisor und ruft im bestehenden, disarmed 100ms-Takt nur observeFirmware() auf. Er liest die ATtiny-Telemetrie via hasSnapshot()/online() zur WARNUNG und ein passives Software-Tick-Deadline-Signal. **Keine** Empfangsbinding von V3-Raum-KOs, kein gesicherter KNX-IP-Status, kein motorischer GPIO, kein Hardware-Watchdog, keine ETS XML/knxprod Mutation.
- [KNX025 nativer Szenariotest](../../tests/native/test_knx025_fault_supervisor.cpp) und [ARDUINO Hardlock](../../tests/native/test_knx025_firmware_hardlock.cpp), [Runner](../../tools/test_knx025_fault_supervisor.py), [Produkt-/Sicherheitsscope-Audit](../../tools/audit_knx025_fault_scope.py) sowie README, Roadmap, KNX024 Querverweis und dieses HISTORY ergänzt.

### Gate 4 – Tatsächlich durchgeführte Tests

- **KNX025 neue 2 Native-C++-Suites PASS**, mit 11 Szenarien: Boot ohne Fehlalarm, frischer 5.001-Direktwert verliert Quelle nach Timeout und löst sticky Fault aus, Raum PI-Setpoint/Actual plus 0x7FFF/-/30s Stale, Manifold-Warnung getrennt, expliziter KNX-Raumtransport erstmalig offline sowie online-zu-offline, falscher 5.004-DPT und ungeprüfte Konfigänderung, Loop-2000ms-Timeout und millis-Rollover, verlorenes Stop-ACK und Lease-Blockade, aktive ETS-Umbindung während Motorlease, Start-ACK-Fault mit Recovery, Not-Stopp und passive RP2040-Diagnose. ARDUINO-Pfad kompiliert ohne virtuelles Backend: Motor-Arm/Position-Injektion **dauerhaft FALSE**.
- **17 bisherige Native-C++-Suites PASS:** KNX008 (1), 013 (2), 014 (4), 015 (2), 019 (1), 020 (2), 021 (1), 023 (2), 024 (2). Zusammen **19 Native-Suites PASS**. 13 separate KNX024-Kontrakt-Negativtests PASS.
- **Echter isolierter RP2040 PlatformIO-Firmware-Build PASS**, UF2 nur temporär unter C:\Users\LLO\AppData\Local\Temp\openknx-controller-isolated-kqax_puy\.pio\build\controller\firmware.uf2, Source-include/knxprod.hpp unverändert. RAM **53.532/262.144 Bytes = 20,4 %**, Flash **193.604/1.048.576 Bytes = 18,5 %**. Keine USB-Verbindung oder Firmwareprogrammierung.
- KNX025 strikter No-Hardware-I/O-/Unverändertheits-Audit PASS. Historische KNX023-/KNX024-Scope-Audits PASS, ETS/KNX008 Vorschlag und tatsächliche KNX015-Produkt-ABI PASS; PCB statischer Audit 0 Invariant-Fails, bekannte Versorgungs-/BOM-DPT-Warnungen bestehen.
- KNX022 Hardwarequellenaudit: 35 Invarianten PASS, aber **10 ungeklärte Hardware-Blocker**, Status BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR unverändert.
- ASH vor Closing **30 Checks / 456 lokale Markdownlinks PASS**, staged git diff --check PASS. Nach HISTORY / Markerentfernung Schluss-Audit wiederholen.

### Nächster Schritt und wichtige Grenze

KNX025 abgeschlossen und mit Git-History dokumentiert, **kein automatischer nächster Slice**. KNX026 LCD/Encoder-Diagnose/Statusansicht oder KNX018 Laptop-Vorbereitung sind sinnvolle nächste getrennte Aufgaben. Der vollständige vorgeschlagene ETS-V3-Raumdatenweg ist weiterhin OFFLINE; KNX009/016 bleiben deferred bis zum separaten KNX018-Laptop-/RTS-UPDI-/KNX-TP-Testplatz.

**Kein echter Motor-/H-Brücken-Sicherheitsabschluss:** Das simulierte STOP-ACK ist keine unabhängige elektrische Freischaltung, ein Software-Deadline-Monitor kein Hardware-Watchdog. KNX002/003/004/005/006 müssen echte Bestückung, Stromversorgung, Abschaltwege, Motorströme und Referenzbewegung nachweisen. Keine Geräte angeschlossen, geflasht oder bewegt, keine KNX-Gruppenadressen geschrieben und kein GitHub-Push.

## KNX026 - Read-only HMI und Diagnosemodell

- **State:** closed
- **Closed:** 2026-10-12
- **Profile:** software, Hardware/ETS6 deferred
- **Objective:** KNX025-Faults und die bestehenden Temperatur-/Raum-/Motor-Softwaredaten ohne reale Aktuatorsteuerung in einem festen, portablen HMI- und Menue-Snapshot darstellen.
- **Gate 1:** Live Agent 0.8.1 und Session-/Gitzustand geprueft; Baseline `52833af` main clean, 32 lokale Commits vor origin/main, KNX025-Sessions closed, kein offener Marker oder fremde Write-Session. LCD-PCF8574 auf V1.2-PCB-Statik und Button D2 / Encoder A D6 / B D7 im Pinheader dokumentiert; kein vorhandener Controller-LCD-/Encoder-Treiber nachgewiesen.
- **Gate 2:** Rein lesendes C++17-Snapshot, synthetische Encoder-Navigation und passive RP2040-RAM-Samplingintegration. Physische Position, sichere Abschaltung, Encoder-GPIO/LCD-Treiber, KNX AppV3, reale Motorfreigabe, ETS-Import und Flash explizit out-of-scope.
- **Gate 3:** [HMI-/Diagnosespezifikation](../KNX026_HMI_DIAGNOSTICS.md), `lib/common/knx026_hmi_diagnostics.hpp` mit 9 Wasser-/8 Zonen-/8 Motor-Slots, unbekannt/frisch/veraltet/ungueltig, Raum-/UART-Transport getrennt und KNX025 als einziger Fehlerquelle; `src/controller/main.cpp` erweitert um passives RAM-Snapshot. Kein realer HMI-Hardwaretreiber. `tools/test_knx026_hmi_diagnostics.py`, zwei neue Host-C++-Testsuites mit ARDUINO-Hardlock; Scope-Audit `tools/audit_knx026_hmi_scope.py`.
- **Implementation commit:** `49fa175` (`feat(knx026): add passive HMI diagnostic snapshot and read-only navigation`).
- **Gate 4:** KNX026 **2/2** C++17 native Testsuites PASS (Quality/KNX025-Fault-Maskierung/Wasser-vs.-Raum/Zone-Motor-/DPT5.001-/Zeitumbruch-/Navigation/ARDUINO Hardlock). KNX023, KNX024 und KNX025 jeweils **2/2** native Regressionstests PASS. Isolierter RP2040 PlatformIO-Build **PASS**, keine Hardware geflasht; KNX026-Read-only Scope-Audit **PASS**. `audit_design.py` **PASS** mit 0 Invariantfehlern (Hardware-/ETS-Warnungen bleiben). ASH-Audit **30/30 PASS**, vor Closing 465 Links. Git staged diff --check PASS.
- **Auditbesonderheit:** Das unveraenderte historische KNX025 Scope-Audit sucht die bisher einmalige Quelltextstelle `temperatureBridge.hasSnapshot();` mit `count == 1`. KNX026 liest denselben Wert zusaetzlich fuer seinen read-only Snapshot und laesst nur deshalb diesen alten KNX025-`count`-Test scheitern; KNX025-Faultsupervisor und alle eingefrorenen Produkt-/PCB-/ATtiny-Quellen sind gegen `52833af` unveraendert, KNX025 native Tests PASS, neues KNX026 Scope-Audit PASS. Dieser veraltete Zaehler-Audit ist kein Beleg fuer veraenderten Fehlerpfad; gegebenenfalls in spaeterem Wartungsslice relativ zum KNX025-Baseline-Commit aktualisieren.
- **No claims:** Kein LCD angezeigt, Encoder physisch gelesen, Motor referenziert/bewegt, Not-Aus elektrisch bewiesen, KNX-Bustelegramm ausgeloest, ETS6-Import durchgefuehrt oder USB/UPDI geflasht. Produkt bleibt AppVersion2, reale Treiber nicht freigegeben; 34 lokale Commits nach beiden KNX026-Commits vor origin/main bleiben unpushed.
- **Closing:** HISTORY aktualisiert, der KNX026-`_OPEN_`-Marker im separaten Abschlusscommit entfernt; kein Push.
- **Follow-ups:** Echten LCD-/Encoder-Anschluss auf freigegebener KNX018-Testbench pruefen; KNX011 Integration/Release und Hardware KNX002-006 sowie ETS6 KNX009/016 bleiben eigenstaendige Gates.
- **Next exact action:** Neue Sitzung live verifizieren; spaeteren separaten Software- oder Hardware-Slice erst nach Review des verbleibenden KNX011-/KNX018-Scopes oeffnen.


## KNX027 - RP2040 USB-Flash-Automatisierung und Recovery-Plan

- **State:** closed
- **Closed:** 2026-10-12
- **Profile:** software; **kein** Hardware-/Motor-/KNX-Test.
- **Objective:** RP2040-USB-Flash mit Arduino-Pico CDC-1200-Baud-Reset und PlatformIO picotool fuer den spaeteren KNX018-Laptop-Teststand sicher und wiederholbar vorbereiten, ohne ein echtes USB-Ziel anzusprechen.
- **Gate 1:** LLO Desktop Agent 0.8.1 erreichbar; main clean HEAD 8ce8de2 (34 lokale Commits vor origin/main), KNX026-Sitzung closed und 0 offene Marker. PlatformIO Core 6.1.19, Arduino-Pico 5.5.0, Serial.begin in Firmware und pio run --upload-port geprueft. Portliste: ausschliesslich COM1 (ACPI) und COM3 (Intel AMT); **kein RP2040** gefunden.
- **Gate 2:** upload_protocol = picotool explizit im Controller-Environment; neues Host-Tool mit probe, plan, isoliertem build und sperrendem upload. Ein realer Upload erfordert vollstaendige 40-stellige erwartete Git-HEAD-ID, sauberen Git-Tree, exakte Windows-COM-/USB-VID:PID-Zuordnung sowie --execute und --confirm-safe-bench. Keine implizite Portwahl, kein automatisches Wiederholen, keine Software-Autorisierung von realer Motorsteuerung.
- **Gate 3:** [Dokumentation/Recovery](../KNX027_USB_FLASH_AUTOMATION.md), [KNX018-Nachtrag](../KNX018_LAPTOP_UPDI_TESTBENCH.md), README/Roadmap, src/controller/controller.ini, tools/usb_flash_controller.py, acht isolierte Unit-Tests tools/test_usb_flash_controller.py, Scope-Audit tools/audit_knx027_usb_flash_scope.py. Das Tool kopiert Firmwarequellen in temporaere Workspace, erzeugt ELF+UF2 und prueft Original-Header via SHA256, bevor ein explizit geforderter Upload im isolierten Verzeichnis moeglich wird.
- **Implementation commit:** d392c82 (feat(knx027): prepare guarded RP2040 USB picotool flashing workflow).
- **Gate 4:** KNX027 **8/8** Python-Testfaelle PASS, inklusive gemocktem Erfolgspfad und Ablehnung von falschem/fehlendem Port, VID:PID, Git-SHA, unsauberem Tree oder fehlender Freigabe. Live probe (read-only) PASS, plan PASS. Echter **Host-seitiger, isolierter** RP2040 PlatformIO-Build **PASS**: firmware.elf und firmware.uf2 erfolgreich erzeugt, RAM **54.108 / 262.144 Byte (20,6 %)**, Flash **198.340 / 1.048.576 Byte (18,9 %)**, UF2 SHA256 2cbe9d7f351d12b562c088471f873bff2adafc87a75116e748e1bf8660522f7a; kein Flashversuch. KNX025 2/2 und KNX026 2/2 native C++ Suites PASS. KNX027-Scope-Audit PASS (Originalfirmware inklusive KNX025/026, ETS XML, knxprod.hpp, PCB und ATtiny unveraendert), audit_design.py 0 strukturelle Fehler, ASH-Workflow Gate4 30/30 PASS, vor Closing 470 Markdownlinks, git diff --cached --check PASS.
- **Sicherheitsgrenze:** Fuer das **tatsaechliche** USB-Flashen sind reale Platine, USB-CDC-/Windows-COM-Test, vorhandene Bootloader-/1200bps-Unterstuetzung, richtige Chip-/Flashgroesse, getestete Stromversorgung und KNX018-/KNX002–006-Sperren offen. Erstprogrammierung/Recovery benoetigt moeglicherweise BOOTSEL-ROM-Laufwerk; keine automatische Flash- oder UF2-Kopie erfolgte.
- **Closing:** HISTORY aktualisiert, _OPEN_KNX027_USB_AUTO_UPLOAD.md im eigenen Closing-Commit entfernt; kein GitHub-Push, keine Laptop-Migration, kein USB-Reset, Motor-/KNX-Telegramm oder ETS-Import.
- **Follow-ups:** KNX018-Laptop nach gesichertem Git-Umzug mit realem RP2040 und elektrisch isoliertem Teststand abnehmen; vor erstem echten Flash die Konfiguration der angenommenen 16-MiB-Flashgroesse gegen den bestueckten Chip pruefen. KNX009/016, KNX011 und KNX002–006 bleiben unveraendert offen.
- **Next exact action:** Fuer hardwarebezogene Folgearbeit neue Write-Session und live Root/Session/Git/Port-Check; KNX027 nicht erneut oeffnen. Die unpublizierten lokalen Git-Commits muessen vor dem Laptop-Umzug erhalten bleiben.

## KNX028 - LLO Home Offline-Entwicklungsinitialisierung und Build-Fix

- **State:** closed
- **Closed:** 2026-10-13
- **Profile:** software/infrastructure; alle physischen Hardware-Gates separat.
- **Objective:** LLO Home `C:\_myspace\workspace\open-knx-valve-control` als primaeren Software- und Offline-Testrechner einrichten, dabei RP2040/ATtiny-Hostbuilds, native C++-Tests und USB-Flash-Mocktests reproduzierbar machen. **Kein angeschlossenes Board**.
- **Gate 1:** LLO Home Agent 0.7.9, initial main `14795c6` clean und GitHub synchron. Kein fremder aktiver Write-Slice; KNX028-Marker vorgefunden und in frischer Session fortgesetzt. Agent läuft als SYSTEM, Repository gehoert ll; Git-Vertrauen nur pro Befehl/Kindprozess auf exakt dieses Repo begrenzt.
- **Gate 2:** Host-only-Installationen mit expliziten Release-Pins und offiziellen Bezugsquellen, Build im temporaeren Quellbaum, keine USB-/UPDI-/KNX-/ETS-/Motoraktionen oder globalen PATH/Registry/Git-Trust-Aenderungen. Das urspruengliche Home-GCC16-Fehlerbild ohne Modifikation fremder Frameworkquellen beheben.
- **Gate 3:** Python 3.11.7 und PlatformIO 6.1.18 im Profil `C:\Users\ll\.platformio` genutzt; OpenKNXproducer 3.12.2 aus offiziellem Release samt PlatformIO RP2040, Arduino-Pico 5.5.0, picotool, OpenKNX/TPUart installiert. ATtiny3216-Isolationsbuild PASS. Fehlgeschlagenen Home-RP2040-Build (GCC16.1.0, `__getreent` undefiniert in Arduino-Pico `malloc-lock.cpp`) auf Geraetetoolchain zurueckgefuehrt: zuvor erfolgreicher Desktop nutzte GCC14.3.0. `src/controller/controller.ini` pinnt jetzt toolchain-rp2040-earlephilhower 5.140200.250530 (Originalrelease 4.1.0) und den Home-getesteten maxgerhardt-platform-Commit `5d4561a05e3b212660ac6fdd3fbfb328d1988aa1`. Der historische KNX027-Scope-Audit erlaubt ausschliesslich genau diese zwei pins und behaelt seine Runtime-/ETS-/PCB-/Upload-Guards.
- **Native Host-GCC:** WinLibs GCC16.2.0 x86_64-UCRT portable aus dem originalen Release, 7z SHA256 `53fb6773fbdf87cdf22b69a6b2a07ee33d3ada413b42d83044bc7cc6481400d2` gegen offizielles Sidecar geprueft, kein globales Installationspaket. `tools/install_home_host_compiler.ps1`, `tools/home_offline_check.ps1 -Native` bzw. `-ControllerBuild`, [Home-Runbook](../KNX028_LLO_HOME_SETUP.md), README/Roadmap dokumentieren Pfade und Validierung.
- **Gate 4 QA:** RP2040 isolierter PlatformIO-Controller-Build dreimal PASS (vor Plattform-Pin, mit beiden Pins, via neuem Home-Runbook), zuletzt Home-Job `job-000072` exit 0. `firmware.elf` und `firmware.uf2` nur temp; reproduzierbare UF2-SHA256 `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805` in allen drei Builds, RAM 54.108/262.144 Byte (20,6 %), Firmwareflash 198.340/1.048.576 Byte (18,9 %). ATtiny3216-Offlinebuild PASS; KNX027 Upload-Mocktests 8/8 PASS; elf native C++17 Testskriptgruppen KNX008/013/014/015/019/020/021/023/024/025/026 **11/11 PASS**, einschliesslich synthetischer Motorqueue-/Failclosed-/ARDUINO-Hardlock-Regressions. KNX026 und KNX027 Software-Scope-Audits PASS; `audit_design.py` 0 statische Invariantfehler und `audit_ash_workflow.py` 30/30 PASS mit 476 internen Links vor Closing; Git staged diff --check PASS.
- **Safety/No claims:** Keine echte RP2040/ATtiny-UF2-Firmware geflasht, keine BOOTSEL-/USB-Reset-/COM-Geraeteaktion, kein ETS6-Import oder KNX-Bustelegramm, keine Motorbewegung. Der KNX022-Preflight bleibt bei 10 realen Hardware-Blockern `BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR` (U25/R29/F1/Power/STBY/INA219/EasyEDA). Der 16-MiB-Hardwareflash muss an der bestueckten Platine verifiziert werden. Temp-Build ist keine elektrische Sicherheitsfreigabe.
- **Implementation commits:** `089a984` (initiale Home-Installation und Runbook), `5128482` (GCC16-vs.-GCC14-Differenz), `acdc850` (`build(knx028): pin reproducible RP2040 toolchain and pass Home native QA`).
- **Closing:** HISTORY-Eintrag und Entfernung `_OPEN_KNX028_HOME_BOOTSTRAP.md` in eigenem Abschlusscommit; alle 4 KNX028-Commits bleiben lokal auf Home, **kein Push**.
- **Follow-ups:** Erst bei fertig bestueckter Platine KNX002-006/KNX018 mit nachvollziehbarer USB-/Versorgungspruefung; getrennte ETS-Import-Gates KNX009/016; danach geregeltes USB-Flashing und KNX-Bus-Tests. Den Folgeslice nicht automatisch oeffnen.
- **Next exact action:** Fuer weitere Softwarearbeit frische ASH-Session auf LLO Home, Git/Checkpoint live abgleichen, dann separaten begrenzten Slice planen; fuer realen Testaufbau physische Power-/STBY-/U25-/R29-/Flash-/KNX-Gates zuerst.

## KNX029 – Software-Erstkontaktpaket fuer RP2040, ATtiny3216 und KNX-Teststand

- **State:** closed
- **Closed:** 2026-10-13
- **Profile:** software, first-contact preparation; keine Hardware-Freigabe.
- **Objective:** Ein offline erzeugbares und pruefbares Doppel-Firmware-Kit mit RP2040-UF2/ELF, ATtiny3216-HEX/ELF, Source-Git-SHA, Sicherheits-Gates und SHA256-Manifests fuer die spaetere KNX018/V1.2-Inbetriebnahme vorbereiten.
- **Gate 1:** LLO Home Agent 0.7.9 online, Root `C:\_myspace\workspace\open-knx-valve-control`, initial HEAD `a35d6be`, main CLEAN 4 Commits vor `origin/main`. KNX029-Session `ses-20261013T101642-e0e1a1f3f57b` wurde zwischenzeitlich `stale` mit 0 aktiven Jobs/4 letzten Erfolgen; kontrolliert unter neuer Ownership uebernommen. Keine anderen aktiven Write-Sessions, keine fremden Dateien verworfen.
- **Gate 2:** Nur softwareseitiger Build und Integritaetspruefung mit vollstaendiger 40-Hex-Commitbindung und clean Git; `plan` ohne subprocess, `build` nur temporäre Quelle und `pio run -e controller/temperature`; ATtiny-Konfig in Temp-Kopie ohne jegliche Programmer-/COM-/RTS-/UPDI-Aktion. Externer, neuer Outputordner ohne Ueberschreiben. `verify` kontrolliert exakt vier Binaries und Manifest/5 Checksummen, Source-Commit und acht `false`-Hardware-Gates.
- **Gate 3:** `tools/knx029_prepare_bringup.py`, `tools/test_knx029_bringup_kit.py`, `tools/audit_knx029_bringup_scope.py`, [KNX029 Runbook](../KNX029_FIRST_CONTACT_RUNBOOK.md), README, Roadmap und bestehender `tools/home_offline_check.ps1` erweitert. Historische KNX027-Upload-CLI, Originalfirmware, ETS-XML, ATtiny-UPDI-Konfiguration, Motor- und PCB-Dateien unveraendert gegen `a35d6be`.
- **Fehlerbehandlung:** Erster realer Doppelbuild `job-000112` kompilierte Controller und ATtiny3216 **beide PASS**, aber PlatformIO entfernte beim Environmentwechsel Controller `.pio/build`-Artefakte; das neue Tool hat korrekterweise die unvollstaendige Ausgabe blockiert. Controller-UF2 und ELF werden seit Fix **sofort** mit SHA256 in einen separaten Temp-Bereich kopiert. Adversarial Test loescht Controller-Ausgabe im FakeRunner und prueft, dass das fertige Kit dennoch beide verifizierten Images enthaelt.
- **Gate 4:** KNX029 **14/14** negative/positive unittest-Faelle PASS, inklusive dirty HEAD, SHA-Mismatch, vorhandener Pfad, fehlendes HEX, doppelte Buildordnerbereinigung, falsche UPDI-Konfiguration, verweigerte Freigabe, Manifest- und Firmware-Tampering. KNX029 Originalquell-/No-Hardware-Audit PASS; Home-Baseline-Checks (KNX027-Mocks 8/8, ASH 30/30, statisches Design 0 Invariantfehler) PASS.
- **Realbuild:** `job-000122` **exit 0**. Build aus sauberem Git-Commit `b016a16243ca207b491383d7f9bdd446ace2f288`; beide Firmwares erfolgreich kompiliert und ausserhalb Git abgelegt unter `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX029-b016a16-v1`. `tools/knx029_prepare_bringup.py verify` **exit 0**, 4/4 Artefakte und 5/5 SHA256SUMS-Eintraege exakt PASS, alle realen Freigabefelder `false`. RP2040 UF2 SHA256 `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805` (420864 Byte); ATtiny3216 HEX SHA256 `72c962c038a077d23fbb7ecb160fcffab2c705bb111219de0840637610c954e8` (24467 Byte). Controller RAM 20,6 % / Programmpartition 18,9 %; ATtiny RAM 48,0 % / Flash 26,5 %. Dateien im Manifest dokumentiert.
- **Implementation commits:** `0dfb518` (initiales passives Kit), `b016a16` (sichere RP2040-Artefaktbewahrung beim Multi-Environment-Build). Eigenstaendiger Abschlusscommit aktualisiert HISTORY, Roadmap und entfernt _OPEN_KNX029.
- **Kein Hardwareclaim:** U25 real ATtiny3216 vs. moeglich ATtiny1616 unbekannt, 16-MiB RP2040-Flashchip unbestaetigt, CN1 Pin1/UPDI-3,3V gegen Programmer-5V ungeklaert, USB/KNX-Backfeed und sichere Motor-STBY-Gates nicht abgenommen. Keine reale USB-/UPDI-Programmierung, keine KNX/IP-Verbindung, kein ETS6-Import, kein Ventil bewegt, kein Git-Push. KNX002..006/018 und KNX009/016 bleiben separat offen.
- **Next exact action:** Nach fertig bestueckter Platine, und nur nach Live-Agent-/Git-/Sessioncheck, KNX018 nach Runbook Gate A/B beginnen: Fotos/BOM/U25/R29/F1/Flash-Capacity, stromlose CN1-Pin1-Pruefung, sichere Spannungsversorgung strombegrenzt **ohne Motor**, erst danach USB/UPDI-Geraeteidentifizierung; vor einem echten Flash/KNX-Telegramm ausdrueckliche Freigabe einholen.

## KNX030 – Passive Windows-Erstkontaktinventur auf LLO Home

- **State:** closed
- **Closed:** 2026-10-13
- **Profile:** software, hardware entirely unconnected / no electrical release.
- **Objective:** LLO Home zur spaeteren Identifizierung neu angeschlossener RP2040-/USB-/UPDI-Adapter per ausschliesslich passiver, reproduzierbarer Windows-OS-Inventur und Vorher/Nachher-Differenz vorbereiten, ohne COM/KNX, Reset, Flash oder Motoren anzusprechen.
- **Gate 1:** LLO Home Agent 0.7.9 online, Root `C:\_myspace\workspace\open-knx-valve-control`, baseline main HEAD `846bb93`, CLEAN, 7 lokale Commits vor origin/main, keine anderen aktiven Write-Sessions und keine `_OPEN_*`-Marker. KNX029 Offline-Firmwarepaket unbeschaedigt vorhanden, KNX002–006 Hardwareblocker offen.
- **Gate 2:** `plan` ohne subprocess, `capture` nur Windows Get-PnpDevice -PresentOnly, Get-Volume, Get-NetAdapter und nur in **neue** JSON-Datei **ausserhalb Git**, `compare` nur lokale JSON-Dateien ohne OS-Kommandos. Keine USB-Serial-/UPDI-/KNX/IP-Sockets oder Filesystem-Access zum ROM-Volume. PnP-Instanz-IDs SHA256 gehasht, VID:PID/COM/Name/Linkstatus als unbestatigte Hinweise, sieben physische Freigabefelder immer false.
- **Gate 3:** `tools/knx030_passive_inventory_probe.ps1`, `tools/knx030_passive_inventory.py`, `tools/test_knx030_passive_inventory.py`, `tools/audit_knx030_passive_scope.py`, [KNX030 Runbook](../KNX030_PASSIVE_FIRST_CONTACT.md), README, ROADMAP, KNX018-Ergaenzung und Home offline smoke erweitert. Live Windows stdout Windows-CP1252-vs.-UTF8 Dekodierfehler in erster Capture-Probe gefunden und mit explizitem PS/Python UTF8 behoben.
- **Realer passiver Ausgangs-Snapshot:** `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-before-board-20261013.json` liegt ausserhalb Repository. **15** vorhandene USB-/Port-Kandidaten, **0** RPI-RP2-Volume-Labels, **21** lokale Netzwerkadapter, keine Serien-/Roh-PnP-IDs, keine MAC-/IP-Daten gespeichert. Selbstvergleich ohne OS-Zugriff ergibt 0 neue/entfernte Kandidaten, 0 geaenderte Links. WLAN Up ist kein KNX/IP-Gateway-Nachweis.
- **Gate 4:** **11/11** gemockte Windows-Inventory-Tests PASS (kein subprocess im Plan/Diff, fail closed bei tamper/ungueltiger Quelle/raw ID/dirty Ausgabepfad, korrekte USB VID/PID/COM/RPI-RP2 und Netzlink-Differenz), KNX030 Source Scope PASS gegen `846bb93`: Firmware, ETS XML, V1.2 PCB/Schaltplan, KNX027 und KNX029 unveraendert. `tools/home_offline_check.ps1` inkl. KNX030/KNX029/KNX027-Regression/Audits **exit 0**, `audit_design.py` 0 Invariantfehler, ASH Workflow 30/30 PASS mit **492** gueltigen Markdown-Links vor Closing. Git staged diff --check PASS.
- **Implementation commit:** `4d4331d` (`feat(knx030): add passive LLO Home device baseline and first-contact diff`).
- **Closing:** HISTORY aktualisiert und einziger KNX030-`_OPEN_`-Marker im eigenen Abschlusscommit entfernt; **kein Push**.
- **Physical claims expressly not made:** Keine echte Board-Anbindung, keine RP2040-USB-CDC/BOOTSEL-Freigabe, kein ATtiny Device-ID-/UPDI-Signaturtest, kein KNX/IP-Discovery/ETS6, keine reale Spannungsversorgung, keine Motor-/STBY-/INA219-Testfreigabe. KNX022 benoetigt weiterhin U25/Flash/R29/F1/U6/CN1/JMP1/Backfeed-Pruefungen. Nur nach sicherer KNX002/003-Stromversorgungs- und Kabelpruefung kann spaeter ein neues passives OS-Snapshot bei angestecktem Einzelgeraet erfolgen.
- **Next exact action:** Bei fertig bestueckter und elektrisch freigegebener Platine auf LLO Home neuen ASH-Slice KNX018 oeffnen, zuerst stromlose Bestueckung und Power-/UPDI-CN1-Messungen dokumentieren; nach Freigabe die Snapshot-Vorher/Nachher-Differenz fuer RP2040-USB und getrennten UPDI-Adapter vergleichen. Keine USB/UPDI Flash-, KNX- oder Motoraktionen ohne separate Freigaben; Git vorher live auf Home verifizieren.

## KNX031 – KNX014 UART Trace Decoder / C++ Golden-Vektor

- **State:** closed
- **Closed:** 2026-10-13
- **Profile:** software, offline diagnostic tools only.
- **Objective:** Bestehende KNX014 UART-Rohdaten aus **lokalen gespeicherten Dateien** fuer den spaeteren ATtiny/RP2040-Diagnosefall dekodieren, inklusive 9 Temperaturkanälen, Statusflags, CRC16, Sequenzen und Fehler. Native Golden-Vektor-Gegenpruefung mit dem unveraenderten Produktions-C++-Header; kein serial/KNX/UPDI/Flash/Motorzugriff.
- **Gate 1:** Live Home Agent 0.7.9, Root `C:\_myspace\workspace\open-knx-valve-control`, HEAD `688e7ce` clean und 9 lokale Commits vor origin/main, 0 laufende Sessions/kein _OPEN_ Marker. KNX014 TemperatureProtocol v1: Sync A5 5A, 8 Byte GET, 67 Byte Snapshot mit 9 x 6 Byte, CRC16/CCITT-FALSE, reserved moduleStatus0, flags/fault 0..8. ClientCore hat 400ms Antworttimeout/100ms Bytegap/15s Online; reine Bytefolge kann diese Zeiten **nicht** verifizieren.
- **Gate 2:** `tools/knx031_uart_trace.py` mit `plan` (ohne Filesystem/Subprocess) und `inspect` nur fuer lokale binaere oder ASCII-Hex-Dateien (max 8 MiB, Windows COM/LPT-Geraetealias und Netzwerk-/UNC-Pfade abgewiesen). Nur read_bytes, strukturierte JSON-Diagnose und `--summary-only` fuer Remote-Agent-Ausgaben; niemals Port-/Bus-/Hardware-IO, keine Motorfreigabe. Alle Messergebnisse strikt als *reported* markiert.
- **Gate 3:** KNX014 native Goldendaten mit `tests/native/knx031_uart_vector_oracle.cpp` (echter `temperature_protocol.hpp`; GET Sequenz 0x37 = `A5 5A 01 01 37 00 46 59`; Snapshot T0=0, T1=-10.5, T5 NoSensor, T6 ReadFailed). `tools/test_knx031_uart_trace.py` **15/15 PASS** (C++17 compiler golden, CRC, invalid-header, semantic-invalid but CRC-good, truncated, noise/resync, request/response sequence wrap, HEX/BIN, file alias limits, low output, no IO in plan). `tools/audit_knx031_uart_scope.py` PASS: produktive KNX014/015, RP2040, ATtiny, KNX027/029/030, ETS XML, PCB V1.2 unveraendert gegen `688e7ce`.
- **Externe Beispiel-Datei:** `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX031-native-oracle-example.hex` aus dem lokalen C++-Oracle erzeugt, explizit *synthetisch*, 78 Byte mit 3 Rauschbytes, einer Anfrage und einer Antwort. Python `inspect --summary-only`: **2/2 CRC-Frames**, 1 GET, 1 Snapshot mit 9 Kanaelen, 0 CRC-Fehler, 0 fehlende Requests; alle Hardware-Release-Gates unveraendert false.
- **Gate 4:** `tools/home_offline_check.ps1 -Native` Home Job `job-000172` **exit 0** mit KNX031 und bisherigen KNX029/030/027 Tests, Design/ASH und 11 bestehenden C++-Scriptgruppen. KNX031 Python-Tests 15/15 PASS. ASH 30/30 PASS, 502 gueltige Markdown-Links vor Closing; `git diff --cached --check` PASS. Runbook [KNX031 UART](../KNX031_UART_TRACE_OFFLINE.md), README/ROADMAP/KNX018 und QA-Runner aktualisiert.
- **Implementation commit:** `3c22aca` – `feat(knx031): add offline UART trace decoder and C++ golden vectors`.
- **Closing:** HISTORY in eigenem Abschlusscommit erweitert und KNX031-_OPEN_-Marker entfernt; kein Push.
- **Hard safety limits:** Keine physische Platine angeschlossen, keine COM-Portoeffnung, kein UART-Live-Mitschnitt, kein USB-/UPDI-/KNX-/ETS6-Programmieren, keine Motorbewegung. Raw UART ohne Zeit/Quellrichtung beweist weder RP-Client-Acceptance, 100/400ms Timing, 15s Online, Sensorphysik, KNX-Bus-ACK noch Motor-Interlock. KNX002..006 und KNX018/009/016 bleiben unabgenommen.
- **Next exact action:** Auf LLO Home neue ASH Session und Gitstatus live pruefen. Nach fertig aufgebauter Platine und dokumentiertem KNX002/003-Power-/CN1-Pegel-Gate die KNX030 OS-Baseline vergleichen, RP/ATtiny rein lesend identifizieren; fuer KNX031 nur sicher separat erfasste passive UART-Datei analysieren. Echte ETS/KNX-/Flash-/Motoraktivitaeten ausschliesslich in eigenen freigegebenen Test-Gates.

## KNX032 – Native UART-Snapshot → KNX-Temperaturpipeline

- **State:** closed
- **Closed:** 2026-10-13
- **Profile:** software / no connected hardware.
- **Objective:** Zwischen KNX031 gespeicherter UART-Rahmenanalyse und KNX015 produktivem TemperaturePublisher den kompletten Host-RAM-Testpfad herstellen, ohne Firmware, ETS, KNX-Bus oder V1.2-Hardware zu aendern.
- **Gate 1:** LLO Home Agent 0.7.9 online, Root `C:\_myspace\workspace\open-knx-valve-control`, Branch main HEAD `e0efd61` CLEAN, 11 lokale Commits vor origin/main, 0 aktive Sessions und 0 offene Marker. C++-Quellstand von TemperatureProtocol/ClientCore/TemperatureBridge/TemperaturePublisher, native SerialUART/KNXMock und bestehende KNX015 Teiltests geprueft. Letztere deckten T0/T1 und Status, nicht alle 9 Kanaele mit aufgenommener Rohpayload durch dieselbe Produktionskette ab.
- **Gate 2:** Neuer Software-only KNX032-Kontrollslice. KNX031 C++-Oracle liefert 8-Byte-GET und 67-Byte-Snapshot. Gespeicherte Frames vor Import mit KNX031-Decoder CRC/Sequenz/Flags pruefen; nur **Payload** auf frische lokale Requestsequenz 1 neu rahmen und im In-Memory SerialUART-Mock an die echten Produktions-C++-Module geben. **Keine bitidentische Wiedergabe einer realen Capture; keine realen Zeitstempel, KNX-ACKs oder Messwerte.** Kein Motor/COM/SW-Flash/KNX/ETS.
- **Gate 3:** [KNX032-Dokumentation](../KNX032_UART_TO_KNX_OFFLINE.md), `tests/native/test_knx032_uart_to_knx.cpp`, `tools/test_knx032_uart_to_knx.py`, `tools/test_knx032_replay_contract.py`, `tools/audit_knx032_replay_scope.py`, README/ROADMAP/Home QA erweitert. Native Integration bezieht realen `src/controller/temperature_bridge.cpp` und `src/controller/temperature_publisher.cpp` direkt ein; der Source-Scope-Audit verifiziert KNX014/015, RP/ATtiny, ETS XML, Header, V1.2 PCB, KNX027..031 und native Mocks immutable vs `e0efd61`.
- **Gate 4 Testresultat:** Home Host-Nativtest **PASS**: T0=0 C, T1=-10.50 C, T2/3/4/7/8 gueltig, T5=NoSensor und T6=ReadFailed ohne Temperatur-KO; 7/9 gültige Kanaele ergeben KO35-Maske `0x019F`. Echte, aber ausschließlich native `TemperaturePublisher`-Aufrufe geben an KNXMock KO25..33 DPT9.001, KO34 DPT1.002 (offline/online/offline), KO35 DPT7.001 (415->0). >=250 ms Mindestintervall der akzeptierten virtuellen Konvertierungen, abgewiesene Konvertierung Retry, 15s Offline no new temperature KOs, ETS/P19 off no output. Andere Testvarianten pruefen CRC corrupt, richtige CRC/falsche Sequenz, richtige CRC/falsche Valid-Flags, abgeschnittene Frames fail-closed. `tools/test_knx032_replay_contract.py` **8/8 PASS** inklusive explizitem lokalen KNX031-Hexfile, ohne serial.
- **Gesamtabnahme:** `tools/home_offline_check.ps1 -Native` LLO Home Job `job-000194` exit 0 (nun **12** native Skriptgruppen und bestehende USB/KNX027/029/030/031, ASH und Source-Audits); `audit_design.py` 0 statische Invariantverletzungen; `audit_ash_workflow.py` 30/30 PASS, **515** interne Markdown-Links vor Close; staged `git diff --check` PASS. Keine Build-Datei auf echte MCU geladen und keine KNX- oder Motorhardware angesprochen.
- **Implementation commit:** `cf8b991` – `test(knx032): replay KNX014 UART through actual KNX015 publisher offline`.
- **Closing:** HISTORY ergaenzt und _OPEN_KNX032_REPLAY.md in separatem lokalen Abschlusscommit entfernt. **Kein Git-Push**.
- **Safety gates unchanged:** U25 As-built (ATtiny3216 vs. ATtiny1616), R29/Shunt, U6/VIN/USB-KNX-Powerbackfeed, CN1.1 UPDI 5V/3,3V, physische Flashgroesse, TB6612-STBY hardwired HIGH ohne unabhängigen Motor-Kill sowie KNX002..006/018 bleiben offen; KNX009/016 ETS6 deferred. Native KNXMock `.value()` ist kein realer KNX-TP-ACK/ETS6-Empfang.
- **Next:** Bei fertig bestueckter Platine erst KNX002/003 stromlose Sichtkontrolle und Versorgung/UPDI/Motorisolationsfreigaben, danach KNX030 Windows-PnP-Veränderung pruefen und nur separat sicher erfasste, gespeicherte Rohdaten mit KNX031/KNX032 offline auswerten. Jede weitere Softwarearbeit in neuer ASH-Session mit Live-Gitcheck und eigenen Gates; lokale Commits nicht verlieren.

## KNX033 – As-built-Fotopruefung V1.2 mit D1-Drahtbruecke und F1-Abweichung

- **State:** closed / PHOTO-ONLY. **Real HW gate: BLOCKED_NO_POWER_NO_FLASH_NO_MOTOR**
- **Closed:** 2026-10-13
- **Scope:** Reale, vom Nutzer gepostete Bilder einer bestueckten V1.2-Platine und explizit gemeldete Brueckenstellungen auf dem LLO-Home-Repo **offline** mit den V1.2 PCB/Schematic-Netzen abgleichen. Keine Versorgung, KNX-/USB-/UPDI-Kabel, Flash oder Motoraktionen.
- **Gate 1:** LLO Home Agent 0.7.9, Repository `C:\_myspace\workspace\open-knx-valve-control`, `main` sauber HEAD `7d8f835`, 13 lokale Commits vor `origin/main`, 0 aktive Sessions und keine fremden Slice-Marker. Drei Bilder `20261013_160055.jpg`, `20261013_160046.jpg`, `20261013_160042.jpg` direkt als Chat-Anhaenge gelesen und SHA256 protokolliert; **Originalfotos nicht auf LLO Home kopiert**, nur Namen/Hashes/Evidenztext im Repo.
- **Visuelle Evidenz:** V1.2-Silkscreen, U18 RP2040, U25 Atmel 20-pin, U23 INA219, R29 Bauform, U16 QSPI-IC, 4x TB6612 U34/U36/U37/U35, KNX/USB-Schutz D2/D6/F1/JMP1/Q1 etc. vorhanden. U25-Aufdruck sieht nach `TINY3216` aus, ist **nicht** durch volle Aufschrift/UPDI-Signatur bestaetigt; R29 0,200-Ohm-Bestueckung bleibt nicht ablesbar. U6/TSR-1-2433 auf gezeigter Bauteilseite nicht sicher identifiziert (eventuell Rueckseite); Rueckseitenfoto fehlt.
- **Userbericht und Netze:** JMP1 Loetbruecke geschlossen; JMP2 und JMP3 jeweils »nach oben« gebrueckt. PCB-JMP1 Pad1 `KNX_VCC`, Pad2 `R9_2`; JMP2 Pad1 `KNX_RX'`, Pad2 `KNX_RX`, Pad3 `KNX_TX'`; JMP3 Pad1 `KNX_RX'`, Pad2 `KNX_TX`, Pad3 `KNX_TX'`. Bei passender realer Padlage ist JMP2 Pad1–2 und JMP3 Pad2–3 die gerade RX-/TX-Schaltung; alle Bruecken **ohmsch unbestaetigt**.
- **D1-Bypass:** Nutzer hat D1 entfernt und eine sichtbare Draht-/Loetbruecke an D1 gesetzt. Im PCB Pad2=`5V`, Pad1=`D1_1` gleich U6 VIN; nun bidirektional verbunden. D1-Vorwaertsabfall entfaellt (wichtig, weil U6 laut Datenblatt mindestens 4,75 V VIN benoetigt), aber ebenso die D1-Rueckstromsperre. D6/Q1/JMP1 bleiben gesondert auf USB/KNX-Rueckspeisung/Anomalien zu pruefen. Sichtbare Kupferspitze der D1-Bruecke erfordert mechanische/Nachbarpad-Kurzschlusspruefung. PCB D1 MPN `1N5819HW-7-F` unterscheidet sich von Schematic-JSON-D1-Text `SL1MDIO`.
- **F1 kritisch:** Auf der Nutzeraufnahme mit `T 2.5A ... AC250V` markiert, waehrend Schematic-F1 **630mA 275V** erwartet; Nennstromabweichung als **P0 STOP** dokumentiert. Nicht automatisch 2,5 A als geeigneten Schutz akzeptieren; echte Bestueckungs-/Sicherungskoordination und passender Fuse-Type vor Power-On zu klaeren.
- **Gate 2/3:** [Fotosoll-/Istbericht](../KNX033_AS_BUILT_PCB_REVIEW.md), [JSON-Preflight](../KNX033_AS_BUILT_PREFLIGHT.json), `tools/audit_knx033_asbuilt.py`, `tools/test_knx033_asbuilt_gate.py`. Alle Messfelder `null`, alle Freigaben `false`; Foto/Useraussage ist kein DMM-Resultat. Alle Produktionsfirmware, ETS XML, Schaltplan/PCB und KNX027..032-Tools gegen `7d8f835` FROZEN. README/ROADMAP/POWER_SUPPLY_CONCEPT/KNX022 und KNX029 auf echte neue Erkenntnisse aktualisiert.
- **Gate 4 QA:** KNX033 Fotogate/Audit **PASS**, 15/15 negative unit tests PASS (F1-Mismatch darf nicht verschwinden, D1-Rueckwaertssperre nicht fiktiv, keine gefaelschten Messwerte, U25-Signatur oder U6-Rueckseite, niemals GO). Home full offline `tools/home_offline_check.ps1 -Native` Job `job-000219` **exit0**, 12 bestehende native C++-Testskriptgruppen und statische/Upload-Mocks weiter PASS, 0 realer Hardwarezugriff. ASH 30/30 PASS, 529 lokale Markdownlinks vor Close; `git diff --cached --check` PASS.
- **Implementation commit:** `d5b3f50` – `docs(knx033): record real V1.2 jumper and D1 bypass photo preflight`.
- **Closing:** HISTORY aktualisiert, KNX033-_OPEN_-Marker entfernt im separaten lokalen Abschlusscommit, **kein Git-Push**.
- **Unveraendert BLOCKED:** KNX002/003 Stromversorgung, F1 Nennwert/Charakteristik, U6 physisch, R29 0,2 Ohm, U25/Flash-Chip-ID, D1-Freigabefreiheit, JMP1 und Q1 Quellenrueckspeisung, CN1.1 5V/UPDI Pegel, KNX004–006 TB6612 hardwaremotorisches Fail-safe, KNX018 Teststand, KNX009/016 ETS6. Keine USB-Verbindung allein aus dem Foto ableiten.
- **Next action:** Benutzer um **Rueckseitenfoto** des vollen PCB (mit U6) und Dokumentation der F1-Absicherung bitten. Danach nur stromlos D1 Pad1–2, D1-Nachbarpads/F1, JMP1/JMP2/JMP3 mit tatsaechlichen Netzbezeichnungen durchmessen und Messergebnisse liefern. Erst danach separater KNX002/003-Real-Gate fuer Strombegrenzungs-/Rueckspeisungsversuche **ohne Motoren**.

## KNX034 – Rueckseitenfoto und geplanter USB-only-Erstkontakt (JMP1 OFFEN)

- **State:** closed, **Scope: documentation/plan only**
- **Closed:** 2026-10-13
- **Physical gate:** `BLOCKED_PENDING_UNPOWERED_MEASUREMENTS_AND_F1_REVIEW` (power/USB/KNX/UPDI/motor all false).
- **Live baseline:** LLO Home Agent0.7.9, Git `main` clean HEAD `e8033c7`, 15 lokale Commits vor origin/main, keine laufende Write Session, KNX033 zuvor sauber geschlossen. Neue eigene Write-Session `ses-20261013T144950-46742678097e`.
- **New visual evidence:** Fourth uploaded reverse-side photo `20261013_164325.jpg` SHA256 `932bfac8982d03ebee0e23087a8da03d7480d40fc89b5677eec800fb3d392e82` (original photograph in user conversation, **not stored on LLO Home**). Black power converter housing at PCB U6 with adjacent 5V/3.3V silkscreen now **visually confirmed installed** on reverse side, unlike earlier front view. Exact TSR1-2433 component marking, three solder joints and U6 VIN/VOUT voltages remain unproven. CN1 2x3 header and RUN/PROG/USB_BOOT switches visible; none were connected or used.
- **User proposal – NOT performed:** Desolder/open **JMP1** to ensure USB-only intended 3.3-V main power feed. Last as-built claim remains **JMP1 solder-closed** until user actually confirms removal plus powered-off resistance measurements. PCB contract checked: JMP1 pad1 KNX_VCC / pad2 R9_2, Q1 gate USB_VCC / source 5V_ / drain R9_2 with R9 100k to GND. Open jumper interrupts the intended KNX buck-to-main-source path, but it is **not galvanic separation or proof against KNX/USB backfeed via other paths**. If KNX is not physically connected USB is already the only installed external supply, even with JMP1 closed.
- **Potential USB-only path:** `USB_VCC -> D6 -> 5V_ -> F1 -> 5V -> D1 copper-wire-bypass -> D1_1 -> U6 VIN -> 3.3V`. D1 former Schottky forward drop removed AND reverse isolation lost; D6 drop remains, U6 specified minimum VIN 4.75V may not be met under USB/board load. Photo F1 **T 2.5A** versus schematic F1 **630mA** remains critical unresolved protection mismatch. No guarantee of USB supply stability or safe KNX/USB coexistence.
- **Gate2/3 deliverables:** [KNX034 instructions](../KNX034_USB_ONLY_PREPOWER_GATE.md) and [immutable photo/preflight JSON](../KNX034_USB_ONLY_PREFLIGHT.json), plus `tools/audit_knx034_usb_only.py` enforcing original V1.2 PCB pad-nets and frozen production FW/PCB/ETS/KNX033 since `e8033c7`, and `tools/test_knx034_usb_only.py` **16/16 PASS** negative checks (no falsely applied JMP1 or power/motor GO, fake DMM measurements, false no-backfeed, F1 mismatch or U6 certainty). README, ROADMAP, KNX033 addendum and Home smoke runner updated. No firmware/PCB/ETS changes.
- **Gate4 QA:** LLO Home `tools/home_offline_check.ps1 -Native` Job `job-000240` **exit 0**, all twelve native script-group regression suites and recent offline tests PASS; KNX034 static PCB-audit PASS; ASH 30/30 PASS, **540** Markdown links before close, zero Git whitespace errors.
- **Implementation commit:** `419437c` `docs(knx034): plan USB-only jumper isolation from V1.2 reverse photo`. Closing HISTORY/marker change in a separate local commit, **no push**.
- **Next action on physically unplugged board:** Confirm whether owner removes JMP1. Obtain real DMM resistance/continuity results JMP1 pad1↔pad2 before/after, KNX_VCC↔5V_/5V, D1 bridge 5V↔D1_1 and short exclusion to D5/R7/GND. Validate F1 actual part/value/trip characteristics and full power budget; check safe D6/Q1 USB isolation and correct U6 module before separate motorless initial 5V USB/source evaluation. Never attach KNX during initial USB-only check. No power/flash/KNX/UPDI/motor actions until actual electrical qualification. Preserve local Git commits.

## KNX035 – STKNX U9 KNX_TX Pull-up-R17 und unpassender normaler UART

- **State:** closed, *static design hazard established; physical root cause NOT yet verified*.
- **Closed:** 2026-10-14.
- **Baseline:** LLO Home Agent 0.7.9, main HEAD 374dbc4f837169057b2000b0f19a3b91f240784e CLEAN ahead17 of origin/main. Fresh ASH write session ses-20261014T062618-0631fe85bcbf. No competing write sessions and no Git push.
- **Real symptom:** User reports KNX + 5V caused U11 to become extremely hot and apparently drag down KNX bus. User actually populated **68 Ω**, matching schematic **68 Ω / 2W**. PCB stored manufacturer MPN HoJLR2512-3W-3.5mR-1% was wrong **footprint placeholder metadata**, NOT demonstrated 3.5-mΩ actual part. No ohmmeter reading at U11; U9 condition post-overheat unknown. User says JMP1 was desoldered/open, independent resistor/ground verification not logged. User's *blink firmware binary* was not inspected.
- **Static net-source:** R17 10 kΩ has pad1 KNX_TX to U9 STKNXTR pin24 and pad2 3.3V; U11 connects R68 pin3 to KNX_A U9 pin11. JMP3 pad2 KNX_TX, pad3 KNX_TX' RP2040 U18 pad2/GPIO0. **Pull-up is the wrong bias.**
- **Official datasource:** ST DS12399 Rev3 (https://www.st.com/resource/en/datasheet/stknx.pdf), section 5.1.1: KNX_TX **LOW at bus idle**, HIGH for 35-us active pulse then LOW for 69-us; internal weak pulldown typical 6uA. 10k to 3.3V sources ~330uA with high-Z MCU, plausibly keeps TX active and causes bus load. This is a source-level design fault; it does **not** prove measured actual HIGH during the incident.
- **Separate blocking firmware conflict:** Production setupKnx uses TPUart::Interface::ArduinoSerial(Serial1), which selects SERIAL_8E1 and 19200/38400 Baud on ordinary UART. A normal UART outputs **HIGH at idle**; directly connecting it to STKNX KNX_TX without proper STKNX pulse PHY can again cause continuous active bus drive even with R17 removed. Prepared offline controller firmware not safe for live STKNX KNX-TP acceptance.
- **Safe V1.2 rework plan:** With KNX, USB, 5V, UPDI, motors all disconnected and caps discharged, remove R17 and inspect for solder shorts. **Never put a pulldown in the existing R17 pads**, since the other pad is 3.3V. STKNX internal pull-down may idle LOW for high-impedance MCU GPIO but cannot override GPIO/UART output HIGH. No immediate reconnect to KNX. Post-overheat U9/U11 integrity and proper TX-LOW in every boot/brownout state remain independently unverified.
- **V1.3 ECO proposal (not yet changed on schematic/PCB):** Delete R17 3.3V pull-up, add new 4.7–10k pull-down KNX_TX-to-GND near U9, consider independent fail-low transmitter enable, replace ordinary TPUart Serial1 driver with STKNX-specific direct-timed pulse PHY (e.g. PIO/Timer) and offline 35/69us timing tests; correct U11 metadata to a real 68-ohm >=2W approved part. Separate KNX034 F1 2.5A vs 630mA, D1-bypass backfeed and KNX002–006 hardware gates remain OPEN.
- **QA:** docs/KNX035_STKNX_TX_IDLE_HAZARD.md, docs/KNX035_STKNX_TX_HAZARD.json; tools/audit_knx035_stknx_tx.py source plus immutable prior-revision audit PASS, tools/test_knx035_tx_hazard.py 12/12 negative tests PASS. README/ROADMAP/KNX022/Home offline smoke updated, whole Home -Native job-000270 exit0 including 12 native C++ script groups. ASH initial 30/30 PASS and 546 Markdown links, staged git diff --check PASS.
- **Implementation commit:** 991968f (docs(knx035): flag STKNX TX idle-high pullup and UART PHY hazard). Separate HISTORY/marker close commit follows; no remote push.
- **Result:** Design-level issue documented and tests PASS. Physical **KNX_TX=LOW** not yet measured, R17 not confirmed physically removed, MCU firmware not inspected, U9/U11 may already be damaged. NO POWER, KNX bus, USB/UPDI flash, ETS6 or motor authorization. Future work only after separate qualified electrical measurement; preserve local commits.

## KNX036 – LLO Desktop USB/COM-Teststand ohne KNX-Bus (14.10.2026)

- **State:** closed (Software-/Hostvorbereitung vollständig, echter USB-/UPDI-Board-Erstkontakt aus Sicherheitsgründen weiterhin ausstehend).
- **Live Desktop:** LLO Desktop Agent 0.8.2, `C:\ASH\Workspace\Projects\open-knx-valve-control`. Initial `main` CLEAN HEAD `14795c6` / origin/main (KNX027), keine fremde Write-Session oder _OPEN-Marker. Frische ASH-Session `ses-20261014T070830-4573d715007f`.
- **Git-Migration:** LLO Home HEAD `65011e9` 19 lokale Commits vor `origin/main`, dort CLEAN. Git bundle unter `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX036-home-19commits.bundle` erzeugt und via base64-Dateistrom an Desktop `C:\ASH\Workspace\Runtime\KNX036\home-19-20261014.bundle` übertragen. SHA256 **beider identisch**: `2C3B7FE59AFAB9B6F1B919A7A9AF0C94D0969472B1BAC28089D0196C57B86DB8`; `git bundle verify` PASS; Desktop Git `fetch --no-tags` aus lokalem Bundle + `merge --ff-only FETCH_HEAD` PASS, HEAD jetzt `65011e9`, vorherige 19 Commits vollständig erhalten. **Kein GitHub-Push**.
- **Erste OS-Beobachtung:** Windows COM1 ist ACPI PNP0501 PC-Serial, COM3 Intel AMT SOL, **kein RP2040/CH340G**. KNX030 Windows-Snapshot vor Board unter `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-before-board-20261014.json`: 11 USB/Port-Kandidaten, 0 `RPI-RP2`-Volumes, 5 lokale Netzwerkadapter. Zweiter rein passiver Snapshot `KNX036-desktop-current-01.json` und Offlinevergleich: **0 neue COM/USB/RPI-RP2-Einträge**, keine Adapteränderungen. **Keinerlei COM-Port geöffnet, keine USB-Deskriptoren mit Gerätetreiber geschrieben, keine echte USB-Hardwareaktion**.
- **Sichere Testsoftware:** Neues, eigenständiges `tools/knx036_usb_diag/` Projekt mit gepinntem RP2040 Arduino-Pico Toolchain wie controller. Eigener C++-Sketch: GPIO0/KNX_TX per digitalWrite LOW dann pinMode OUTPUT vor Serial.begin, USB-CDC-Heartbeat `KNX036 USB-ONLY RP2040 ALIVE` 2 s, **keine** Produktions-KNX-/TPUart/ETS-Komponenten, kein UART0/1/ATtiny, keine Motor-Pins GPIO10..19. PlatformIO `upload_protocol=custom`, `upload_command=cmd /c exit 91` soll versehentlichen Upload blockieren. Low gilt erst **nach Setup**, nicht während Boot/Reset; keinesfalls als Hardware-TX-Gate ansehen.
- **Offline-Build real:** Desktop `C:\Users\LLO\.platformio\penv\Scripts\pio.exe` PlatformIO 6.1.19, `pio run --project-dir tools/knx036_usb_diag -e knx036_usb`: **SUCCESS** nach 37,99 s; RAM 8740 Bytes, Flash 58444 Bytes. Keine Hardware verbunden / kein Firmwareupload. UF2 + ELF samt No-Release-Metadaten und Prüfsummen unter `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-usb-diagnostic-20261014`, UF2 141312 Bytes, SHA256 `ad8df9ba4426102fb240f2ebfbb9526071b91e563fab897ab04034ed766866de`.
- **Gate3/4 Tests:** `tools/test_knx036_usb_diag.py --check-build` **8/8 PASS** (PICO-only build, unerwünschte Upload-Config blockiert, GPIO0-LOW vor Serial, kein KNX/ATtiny/Motor, UF2-Magic). `tools/test_knx030_passive_inventory.py` 11/11 PASS, KNX035 statische Source-Sicherheitsaudit PASS, audit_design 0 Invariantfehler, ASH Workflow 30/30 PASS / 554 Markdownlinks vor Abschluss, gestagter `git diff --check` PASS. Runbook [KNX036](../KNX036_DESKTOP_USB_FIRST_CONTACT.md), README, Roadmap und KNX018 ergänzt.
- **Implementation commit:** `4241f94` – `feat(knx036): sync desktop and prepare upload-blocked USB-only RP2040 diagnostics`. Closing HISTORY und _OPEN-Marker separat committet. No remote push; Desktop hat zwei neue lokale Commits nach importierten 19.
- **Physical STOP-Gates:** R17 wurde nur zur Entfernung diskutiert, nicht eindeutig als entfernt bestätigt; vorheriger KNX+5V U11/U9-Überhitzungsfall, KNX035 aktiver-HIGH TX/TPUart-Serial1-Konflikt. Foto-F1 T2.5A gegen 630mA Schaltplansoll, D1-Draht und D6-Drop mit U6 Vin mindestens 4,75V, mögliche KNX/USB-Rückspeisung und UPDI-CN1 Pin1 5V bei U25 3,3V-Logik bleiben ungeprüft; Motor-TB6612 STBY hardwarefest HIGH. **Keine reale USB-Board-Bestromung, kein ATtiny-UPDI-Signaturlesen, keine RP2040-CDC-Portöffnung, kein BOOTSEL/UF2/Flash, kein KNX, keine Motoren**.
- **Next exact step:** Benutzer kann, wenn vorhanden, **nur den Units-UPDI-Programmer an den PC-USB anschließen, ausdrücklich ohne 2x3-CN1-Kabel zum ValveControl**, dann neuer passiver KNX030-Snapshot und VID/PID/COM-Diff; nicht mit COM1/COM3 verwechseln. Vor Board-USB erst R17-Abnahme, F1/D1-Schutz- und Spannungsmessungs-Gate mit begrenzter Quelle, KNX und Motoren physisch getrennt. Upload bleibt ohne separate Freigabe untersagt.

## KNX037 – RP2040 erster realer USB-Flash/Heartbeat PASS, ATtiny-UPDI RTS-Gate offen

- **State:** closed (RP2040 USB flash/CDC actual hardware PASS, ATtiny no action).
- **Closed:** 2026-10-14.
- **Live baseline:** LLO Desktop 0.8.2, repo `C:\ASH\Workspace\Projects\open-knx-valve-control`, main CLEAN prior HEAD `6f7dee7` with 21 local ahead origin/main, no concurrent write sessions, fresh KNX037 `ses-20261014T073953-b472c2b1389c`.
- **Windows hardware:** RP2040 initially **COM5, VID:PID 2E8A:00C0**, CH340G/Units Programmer **COM4, VID:PID 1A86:7523**. COM1 ACPI and COM3 Intel AMT SOL not touched. Actual USB scan both Windows and PySerial, first snapshot outside repo `KNX037-20261014-two-ports.json`.
- **No KNX/motors** according to user; remote tool did not energize other supply or touch motor pins. Initially COM5 serial 115200 read-only 0 bytes, no CDC bootloader reset.
- **First RP2040 flash:** SHA256-verified KNX036 isolated USB-only UF2 (141312 bytes; SHA256 `ad8df9ba4426102fb240f2ebfbb9526071b91e563fab897ab04034ed766866de`). The first direct picotool -f load attempt failed to locate BOOTSEL, no write. One targeted **COM5 1200 baud DTR True→False with RTS False**, no payload, entered ROM VID/PID `2E8A:0003`, temporary **COM6**. Real `picotool info -a` **RP2040 Revision B2 / 16 MiB external flash**. One `picotool load -v -x` returned 100% flash, 100% verify, OK, auto reboot. Resulting app **COM7 VID:PID 2E8A:000A** and multiple real 115200 USB heartbeat lines `KNX036 USB-ONLY RP2040 ALIVE uptime_ms=... seq=...` (3/3 then 4/4, and repeat 3/3). No KNX stack, no ATtiny UART, no motor activity; GPIO0 KNX_TX LOW **after setup** only; no hardware reset-state safety proven.
- **Second OS snapshot:** `KNX037-20261014-after-diag.json` shows new COM7/2E8A:000A and removed COM5/2E8A:00C0; CH340 COM4 unchanged.
- **ATtiny COM4 gate:** Units service `serial-updi-programmer.service.ts` uses logical `requestToSend:true / dataTerminalReady:true` in UPDI mode, false on close. Programmer U1 CH340G and U2/U7 muxes fed by USB VCC; ValveControl U25 ATtiny VCC 3.3V and CN1 pin1 5V/pin3 UPDI, actual UPDI pin3 voltage and CN1 pin1 reverse current not measured. **No COM4 port opened, no RTS/DTR toggled, no pymcuprog ping/erase/write, no ATtiny flash.** Need user confirmation whether 2×3 CN1 cable is physically plugged and 3.3/5V line-level measurements before UPDI.
- **Reproducible source:** [KNX037 runbook](../KNX037_DESKTOP_LIVE_USB_AND_UPDI.md) and [JSON evidence](../KNX037_LIVE_USB_RESULTS.json); `tools/knx037_rp_usb_workflow.py` commands plan (no I/O), probe (metadata), listen (VID/PID+USB serial exact), deliberately multi-gated flash one-shot with 1200baud boot and full UF2 SHA; cannot select CH340. `tools/test_knx037_rp_usb_workflow.py` **11/11 PASS** failclosed tests; existing KNX036 isolated source audit 8/8 PASS and KNX035 STKNX source risk unchanged.
- **QA:** Design audit 0 static invariant failures; ASH workflow 30/30 PASS and 562 resolved Markdown links before close, staged `git diff --cached --check` PASS. Implementation local commit **`aa8b59a`** (feat(knx037): verify real RP2040 USB flashing and guard repeat workflow). Closing HISTORY+marker commit follows. **No GitHub push**.
- **Critical unresolved:** KNX035 R17 external KNX_TX pullup, post-overheat U9/U11, production TPUart Serial1 incompatible with STKNX; KNX034 F1 photo T2.5A vs schematic 630mA, D1 wire bypass, U6 VIN reserve and KNX/USB backfeed; UPDI CN1 pin1 5V vs ATtiny3.3; all motor/H-bridge STBY safeguards. RP2040 USB success does **not** imply KNX/UPDI/motor safe.
- **Next:** Only with 2×3 cable fully unplugged from ValveControl and a known measurement arrangement, characterize COM4 programmer RTS True/False and CN1.3 actual voltages vs GND; do not test COM4 electrical output while unknown 3.3V target is connected. Once UPDI voltage level and separate target supply qualified, do read-only ATtiny signature with correct expected chip type before any write. Preserve all local commits, synchronize with LLO Home by offline verified Git bundle, no push.

## KNX038 – Units RTS-Multiplexer gegen ValveControl ATtiny3216, Offline-Firmware und UPDI-Spannungsgate

- **State:** closed (Software-/Schaltplananalyse und ATtiny-Build abgeschlossen; physische COM4-UPDI-Signatur und Firmwareupload absichtlich ausstehend).
- **Closed:** 2026-10-14.
- **Live Desktop:** Agent 0.8.2, `C:\ASH\Workspace\Projects\open-knx-valve-control`, initial CLEAN HEAD `1b7b649` ahead23, eigene Write-Session `ses-20261014T083359-54467fd6f4fd`, kein Konflikt.
- **Live USB:** COM4 CH340 VID:PID `1A86:7523` und RP2040 COM7 `2E8A:000A` weiter unter Windows/PySerial erkannt. **COM4 nicht geöffnet, RTS/DTR nicht geschaltet, keine UPDI-Frames gesendet**.
- **Gepruefter Programmer V1.2:** Units `sch_updi_programmer_v1.2.json` und `pcb_updi_programmer_v1.2.json` plus WebSerial-Service. U1=CH340G, U2/U7=SN74LVC1G3157 (aus USB-VCC gespeist) schalten mit `RTS` TX/RX oder UPDI durch. Units Service verwendet `requestToSend:true` + `dataTerminalReady:true` fuer UPDI und beim Close false. Programmer Pinout CN1: 1 CN1_1, 2 TX, 3 UPDI, 4 RX, 5/6 GND. Programmer USB-VCC über Q1/D1 auf CN1_1 wird noch nicht als elektrisch sicher isoliert qualifiziert.
- **Valveknoten:** ValveControl V1.2 CN1 Pin1=5V, Pin2=RXD, Pin3=UPDI, Pin4=TXD, Pin5/6=GND. U25 ATtiny VDD=3.3V Pin1, UPDI Pin16; Source/Firmware erwartet ATtiny3216 (`1E 95 21`), PCB-MPN ATTINY1616-SN (`1E 94 21`) falsch/abweichend, ein echter Signature-Read noch nicht vorhanden. Nutzer meldet Programmer-Steckverbindung zum Board als wahrscheinlich; dies ist keine gemessene Pinsicherheit.
- **Pegelquelle:** TI SN74LVC1G3157 signal pass-through bis VCC, keine automatische 5V→3.3V-Anpassung. Microchip ATtiny3216/3217 36.2 Absolute Maximum Ratings normale I/O VDD+0.5V, RESET mit separater VRST-Spezifikation. Eine erlaubte HV-Pulseigenschaft beweist nicht, dass sämtliche Board-/Programmer-Pfade mit 3.3/5V-Mischversorgung sicher sind. U25-VDD, UPDI High an CN1.3, CN1.1 Versorgungsrueckspeisung, Kabelorientierung bleiben **nicht gemessen**.
- **Build:** Desktop `pio run -e temperature` **SUCCESS 8.63s**, 8655B Flash / 983B RAM ATtiny3216; HEX 24356B und ELF + SHA256 No-Release-Manifest unter `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX038-ATtiny3216-offline-20261014`, HEX SHA256 `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`. Nie auf Target geflasht.
- **CLI:** `tools/knx038_updi_readiness.py` mit `plan` ohne I/O, `probe` passive COM4 USB VID/PID, `verify-build` HEX hash und vorgesehenem `ping` nur nach expliziter externer Fuenffach-Mess-/Schutzfreigabe. `pymcuprog` wuerde bei `ping` 8E2 seriell oeffnen und initial UPDI BREAK senden; ist **keine** physisch passive Aktion. ATtiny3216-Signaturpruefung akzeptiert auch das umgedrehte `pymcuprog`-Ausgabeformat `21951E`, lehnt 1616 `21941E` ab.
- **Tests:** `tools/test_knx038_updi_readiness.py` **14/14 PASS**; Fehlzuordnung COM, fehlende Einzel-Gates, falsche Firmware und falsche ATtiny-Signatur blockiert. ASH Workflow **30/30 PASS**, 572 Markdown-Links, staged Git diff --check PASS, keine anderen Quelldateien geaendert. Dokumentation README/ROADMAP/KNX018/KNX037, [KNX038 Runbook](../KNX038_UPDI_RTS_ELECTRICAL_GATE.md) und [Preflight JSON](../KNX038_UPDI_PREFLIGHT.json).
- **Implementation commit:** `2ce9d4d` (feat(knx038): prepare ATtiny3216 UPDI RTS and voltage-gated signature check). Separate lokaler HISTORY-Close-Commit; **kein Git-Push**.
- **Next:** Benutzer soll sechspoliges Kabel auf **ValveControl-Seite** voruebergehend abziehen und bestaetigen. Dann darf der Agent am isolierten Programmer-USB/COM4 RTS False/True testen, waehrend der Nutzer mit Multimeter oder PicoScope CN1 Pin3 UPDI und Pin1 VCC gegen Pin5/6 GND misst. Nach Messung, sicherer Pegel-/Rueckspeisungs- und 3.3V-VDD-Pruefung Verbindung korrekt herstellen, zuerst **read-only** 3216-Signatur, erst danach separate schreibende Firmware-Freigabe. KNX und Motoren bleiben abgeklemmt; U9/R17, F1 und D1 Gates aus KNX035/034 bleiben offen.

## KNX039 – Echte ATtiny3216-Gerätesignatur und bestehender Flash-/EEPROM-/Fuse-/USERROW-Readback über COM4

- **State:** closed (physischer UPDI-Lesezugriff erfolgreich, neue Temperature-Firmware absichtlich NICHT geschrieben).
- **Closed:** 2026-10-14.
- **Live Baseline:** LLO Desktop Agent 0.8.2, Repo `C:\ASH\Workspace\Projects\open-knx-valve-control`, CLEAN HEAD `90dfc8e` ahead25, keine fremde Session; eigene Write-Session `ses-20261014T090511-ab1ae57f4086`. CH340 COM4 VID:PID1A86:7523 und RP2040 USB-CDC COM7 VID:PID2E8A:000A real enumeriert.
- **User consent:** Nutzer bestaetigte direkt verbundene Programmierleitung sei bereits getestet und ein Programm laufe auf ATtiny; ausdrueckliche Freigabe, RTS/UPDI ohne Abstecken auszulesen. Nutzer sagte „ATtiny 2316“, echte Typbestimmung nur nach gemessener Signatur.
- **Hardware gelesen:** Direktes `C:\Users\LLO\.platformio\penv\Scripts\pymcuprog.exe --device attiny3216 --tool uart --uart COM4 ping` Exit0: `Connecting to SerialUPDI`, `Ping response: 1E9521`, `Done`. Echte **ATtiny3216**-Identitaet nachgewiesen, nicht ATtiny2316 und nicht PCB-Metadaten-ATTINY1616. Der Treiber verwendet PySerial default RTS/DTR True und sendet Initial-UPDI-BREAK; funktionierender UPDI-Weg bestaetigt, kein Oszilloskop-/DMM-Pegelnachweis.
- **Read-only Memory:** Danach je ein erfolgreiches `pymcuprog ... read` fuer **flash**, **eeprom**, **fuses**, **user_row**, jeweils Exit0 und wiederholtes 1E9521. Flash 32.768 Bytes komplett ausgelesen (1.888 != FF), EEPROM 256 Bytes FF, Fuses 9 Bytes, USERROW 32 Bytes FF. Alle Intel HEX Checksums PASS. **Kein FLASH WRITE, kein ERASE, keine Fuse-/EEPROM-/USERROW-Schreiboperation.**
- **Original-Backup:** `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX039-ATtiny3216-readback-20261014` mit vier original ausgelesenen Intel HEX-Dateien und `readback_manifest.json` (Hashes, Bytebereiche, Fusewerte). Originale absichtlich **außerhalb Git**; Git nur Provenienz-/Hash-Metadaten. Flash-HEX SHA256 `048d09437f46cd7b6107fb7649ef1a7dcf469dab4ada59d125a7a6f1846bd5b7`.
- **Offline-Vergleich:** Gegen den bisherigen, noch nicht aufgespielten KNX038-ATtiny3216 Temperature-Build HEX SHA256 `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`: 8655 definierte Build-Bytes; 8450 davon stimmen nicht mit dem Live-Readback ueberein; erste Differenz 0x0002. Bestehendes Programm unbekannt, aber nicht leer und nicht identisch mit neuer Temperatur-Firmware.
- **Git-Dateien:** [KNX039 Runbook](../KNX039_LIVE_UPDI_READBACK.md), [Evidenz JSON](../KNX039_UPDI_READBACK_EVIDENCE.json), `tools/test_knx039_live_readback.py` 8/8 PASS inkl. tatsaechlichem SHA256-Recheck der vier Desktop-Sicherungsdateien; README, ROADMAP, KNX038-Hardwaregate-Nachtrag. Home-/Desktop `tools/home_offline_check.ps1` Python-/PIO-Pfade dynamisch und KNX036-039-Tests in Runliste aufgenommen.
- **QA:** KNX038 Tests 14/14 PASS, KNX039 8/8 PASS, ASH 30/30 PASS und 581 Markdownlinks mit einem zulässigen Marker, `git diff --cached --check` PASS. Vollständige Desktop-Native-Regression **nicht bestanden** aufgrund fehlendem Host-`g++` bei altem `tools/test_knx031_uart_trace.py` (kein Fehler am UPDI/ATtiny, nicht wegdiskutieren). Vollstaendige QA daher auf LLO Home mit dort vorhandenem Host-`g++` nach Git-Transfer durchführen.
- **Implementation commit:** `ec90b78` `test(knx039): verify live ATtiny3216 UPDI readback and preserve original memories`; separater History-/Markerabschlusscommit folgt. **Kein GitHub-Push**.
- **Offen:** Reale Programmer-Pegel CN1.3 UPDI und 5-V-Rueckspeisung CN1.1 bei U25 VDD=3.3V wurden weiter **nicht gemessen**; funktionierende UPDI-Auslesung ist kein Garant der Gesamtschaltungssicherheit. KNX035 R17-STKNX-Sendepegel, moeglicher U9/U11-Hitzeschaden, KNX034 F1/D1/USB-KNX-Power-Bereiche und Motorfreigabe weiterhin OFFEN. Kein weiteres ATtiny-Flash unter stillschweigender Annahme; vor Schreibaktionen Backups erhalten, Gerät 1E9521 prüfen und gezielt verifizieren. RP2040-Diagnose-USB auf COM7 unveraendert.

## KNX040 – live ATtiny3216 Temperature-Firmware + RP2040 Serial2/KNX014 9-Kanal-Status PASS

- **State:** closed (real ATtiny firmware upload+verify, RP2040↔ATtiny CRC-UART without sensors PASS).
- **Closed:** 2026-10-14.
- **Live baseline:** LLO Desktop Agent 0.8.2, repo `C:\ASH\Workspace\Projects\open-knx-valve-control`, main CLEAN initial HEAD `9af9436` ahead27, no competing session. Fresh ASH write session `ses-20261014T093326-d43f98b15cf6`. User explicitly authorized ATtiny firmware flash and temperature readout, with **NO temperature sensors attached**. KNX bus and motors physically not connected during USB-only test.
- **Backup gate:** Before write, previously live verified 1E 95 21 ATtiny3216, CH340 COM4 VID/PID1A86:7523 and RP2040 COM7 VID/PID2E8A:000A confirmed; all four KNX039 full original HEX backups present with valid SHA256. New KNX038 HEX SHA256 `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`.
- **Genuine ATtiny programming:** `pymcuprog write --device attiny3216 --tool uart --uart COM4 --filename <temperature.hex> --erase --verify --timing` exit0, echoed signature1E9521 and `Writing flash, Verifying flash, OK`, operation took 5.644s. Old flash image overwritten with user permission, backup retained. **No explicit fuse write**.
- **Post-verify independent actual hardware read:** `pymcuprog read` again for flash32768B, fuses9B, eeprom256B; parsing/CRC of IntelHEX and full image comparison gave **8655/8655 defined firmware bytes exact, 0 unauthorized programmed data beyond image; Fuses UNCHANGED and EEPROM UNCHANGED**. Readbacks and manifest in Desktop outside Git `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX040-ATtiny3216-postflash-20261014`.
- **Isolated RP2040 diagnostic:** `tools/knx040_uart_diag` separate PIO RP2040/Arduino-Pico build SUCCESS (Flash62904/RAM9144). Only USB CDC logging, GPIO0/STKNX_TX LOW **after setup only**, UART1 `Serial2` GPIO8 TX→ATtiny PA2 RX, GPIO9 RX←ATtiny PA1 TX, 115200 8N1 and actual shared KNX014 CRC 8-byte GET / 67-byte reply, no KNX/ETS/TBUart/motor pins. `pio upload` blocked with intentional custom command, flash controlled via RP ROM/picotool.
- **First real RP-UART attempt:** Initial UF2 SHA256 `91de63d5e58ae97242c4a2eee7fa319d5fc55541f1548c8bfac1292121746342` was written and verified but produced 0 requests/snapshots. Root cause traced to installed `framework-arduinopico/cores/rp2040/SerialUART.cpp`: `availableForWrite()` returns **BOOLEAN 0/1** via `uart_is_writable`, not available byte count! Checking `availableForWrite()<8` prevents all polls. Isolated new diag corrected to `<=0` and rebuilt.
- **Final RP2040 V2 image:** SHA256 `e9de4dcb66a0afd4fa906d5a5591bc7785cb6c8bc71f57e20bb4104069c31639` stored outside Git. RP COM7 USB 1200-baud DTR→ ROM COM6 PnP2E8A:0003 (port disappearance caused benign serial Windows exception; ROM recognized independently), `picotool load -v -x` 100% written, verified OK, auto reboot COM7 2E8A:000A.
- **True inter-MCU real telemetry:** USB-CDC COM7 115200 read-only capture 16s: **8/8 valid CRC9-channel snapshot frames**, 72 channel lines, timeout0, rejected0, **9/9 channels per frame NoSensor** with flags16 (Error), fault1 (NoSensor), ageSeconds65535, valid0 – **exactly as expected because user has zero actual DS18B20 probes**. No false 0°C temperature displayed. Additional live capture from new read-only `tools/knx040_capture_uart.py` 10s: further **5/5** valid snapshots, 9/9 NoSensor each, cumulative accepted sequence counter153, timeouts0/rejected0.
- **Source-fixed diag / production follow-up:** **DO NOT** flash regular controller KNX main source due KNX035 unsafe STKNX active-high TPUart driver. **Critical separate bug** `src/controller/temperature_bridge.cpp` still checks `uart_->availableForWrite()<8`, preventing all regular bridge requests. Production file intentionally **NOT changed** in KNX040 because historical safety scope audits freeze it; add isolated KNX041 follow-up for corrected `<=0` plus appropriate static/native tests (still not flash normal KNX image until STKNX fixed). This hardware discovery recorded in [runbook](../KNX040_REAL_TEMPERATURE_UART.md) and [evidence](../KNX040_LIVE_TEMPERATURE_UART_EVIDENCE.json).
- **QA:** `tools/test_knx040_uart_diag.py --check-build` **10/10 PASS**, `tools/test_knx040_capture_uart.py` **11/11 PASS**, KNX039 backup test 8/8 PASS, design audit0 invariants, ASH workflow30/30 PASS and 594 Markdown links before closing; `git diff --cached --check` PASS. Full Desktop Native suite isn't available because no host g++ (historical); run full suite after verified Git sync on LLO Home.
- **Implementation commit:** `8c5ddde` (feat(knx040): flash ATtiny and validate real nine-channel UART no-sensor protocol), closing marker removal and HISTORY separate local commit to follow. **No Github push**.
- **Next:** User installs at least one DS18B20 to the correctly identified T0..T8 3-wire terminal only with power disconnected, verifies schematic physical pinout and source protection; leave KNX and motor wiring off. Then monitor COM7 read-only with `tools/knx040_capture_uart.py` – no further firmware flash needed. Expect valid-bit/fault=0 and non-FF age only for fitted sensor. Prior KNX035 R17/U9 overheating and KNX034 F1/D1/power/backfeed and motor safeguards remain OPEN.
