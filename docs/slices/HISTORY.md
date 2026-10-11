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
