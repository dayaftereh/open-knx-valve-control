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
