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
