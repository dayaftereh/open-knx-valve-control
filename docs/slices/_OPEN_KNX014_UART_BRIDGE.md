# KNX014 - UART-Temperatur-Snapshot ATtiny3216 zu RP2040

**Status:** open | **Gate:** 3/4 (implemented; final QA pending) | **Opened:** 2026-10-11
**Owner:** ChatGPT-OpenKNXValveControl-KNX014-20261011
**Session:** ses-20261011T122225-2b4d35567707
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** 1e45868 (main clean, 10 lokale Commits vor origin/main)

## Ziel
Zuverlaessigen versionierten CRC-geprueften UART-Kanal fuer T0 Vorlauf und T1..T8 Ruecklaeufe, aktuelle Messungen mit Status/Alter. KNX-Publikation erst KNX015.

## Gate 1 - Checkup: PASS
- Agent online, keine fremde Write-Session und keine offenen Slices.
- Git clean main, letzte KNX013-Schliessung 1e45868.
- ATtiny KNX013 haelt neun Samples im RAM.
- megaTinyCore HardwareSerial::swap(1) fuer ATtiny3216: PA1 TX/PA2 RX. PCB PA1 (T_RX) mit RP GPIO9 RX, PA2 (T_TX) mit RP GPIO8 TX.
- RP Earle-Philhower-Core: Serial2.setTX / setRX vor begin, KNX Serial1 separat.
- Legacy ATtiny SerialDispatcher ist ungerahmt und darf nicht auf neuem UART parallel laufen.
- Controller PlatformIO Pre-Script kann kanonische knxprod.hpp uebereschreiben; Build nur in isolierter Kopie.

## Gate 2 - Decision: PASS
- Portable Codec/Parser in lib/common/temperature_protocol.hpp.
- UART 115200 8N1. Frame: A5 5A, version, type, sequence, length, payload, CRC16-CCITT little endian.
- GET_SNAPSHOT 0x01 (payload 0), SNAPSHOT 0x81 (payload 59 Byte): uptime uint32, moduleStatus uint8, neun Kanaele zu je 6 Byte (centiC int16, ageSeconds uint16, flags uint8, fault uint8).
- RP Poll alle 3s, Timeout 400ms, Offline/Transport-Stale nach 15s; unpassende Version/CRC/Sequenz nicht uebernehmen.
- ATtiny antwortet aus dem Snapshot; keine OneWire-Konvertierung im Request.
- Alte Debug-/Config-Telegramme werden nicht parallel transportiert; EEPROM-Config und Defaults bleiben, serielle Config-Steuerung wird erst in spaeterem Slice migriert.
- Nichtblockierende Byte-Parser und begrenzte Sendezeit, ohne Motoransteuerung, ohne KNX-Senden.
- Native Codec-/UART-Mocktests, ATtiny Build, RP isolierter Build, ASH/PCB/Link QA, Git-Scopes.

## Gate 3 - Implementation
- [x] Portable CRC-Framing/Parser und Tests
- [x] ATtiny ALT1 UART Responder, bisheriges SerialDispatcher-Protokoll abschalten
- [x] RP2040 Serial2 Poller, Antwortvalidation, Fehler- und Timeout-Status
- [x] README und Protokoll-/Handover-Doku

## Gate 4 - Validation / Close
**Status:** in progress (four native tests PASS, both firmware builds PASS,
strict sensor/transport pin audit 0 gaps; ASH/link/Git checks pending).
- [ ] Native Tests, Sensorpin-Audit, ATtiny PlatformIO PASS
- [ ] Isolierter RP2040 Controller PlatformIO PASS
- [ ] ASH Audit, PCB Audit, Markdown-Links und Git diff --check
- [ ] Implementation Commit + separater Closing Commit, Marker entfernen
- [ ] Git clean, Checkpoint, Session schliessen; kein Push

## Out of scope
Kein Flashen, keine KNX-Telegramme, keine Motorbewegung/Netzteil-/PCB-Aenderung; keine Realhardware-Abnahme.

## Next exact action
Verify ASH/PCB/links/whitespace and build scope, commit KNX014 implementation,
then update HISTORY/ROADMAP and remove the marker in a separate closing commit.
Do not start KNX015 automatically.
