# KNX014 – UART-Brücke zwischen ATtiny3216 und RP2040

**Stand:** 11.10.2026. **Status:** Quellcode implementiert, native Protokoll- und Adaptertests sowie PlatformIO-Offline-Builds erfolgreich. **Keine Bestätigung eines physisch funktionierenden UART-Kanals**, kein Flashen und noch keine KNX-Gruppenobjekt-Übertragung.

## Ziel und Hardwarepfad

Die neun ATtiny-Messkanäle T0 (zentraler Vorlauf) und T1–T8 (Rückläufe der acht Heizkreise) liegen bereits als [gültigkeitsgeprüfte RAM-Snapshots](KNX013_ATTINY_SAMPLER.md) vor. KNX014 macht diese Snapshots über eine sichere UART-Abfrage für den RP2040 verfügbar. Anders als bei einer synchronen 1-Wire-Abfrage wartet der RP2040 nicht auf den Messzyklus. KNX015 übernimmt später die KNX-DPT9.001-Publikation.

| Richtung | ATtiny3216 U25 | PCB-Netz (aus RP-Sicht benannt) | RP2040 U18 |
| --- | --- | --- | --- |
| Antwort vom ATtiny zum RP | PA1, SOIC Pin 17, USART0 ALT1 TX | T_RX | GPIO9, UART1 RX |
| Anfrage vom RP zum ATtiny | PA2, SOIC Pin 18, USART0 ALT1 RX | T_TX | GPIO8, UART1 TX |
| Programmierschnittstelle KNX TP | kein ATtiny-Pin | separate KNX-Leitungen | Serial1, weiterhin unverändert |
| Optionale Handshake-Signale | PC2 bzw. PA4 | T_INT und CS | GPIO22 / GPIO21 | Nicht genutzt |

Der installierte megaTinyCore 2.6.7 stellt die Umschaltung per Serial.swap(1) bereit (vor Serial.begin). Der RP2040-Core unterstützt Serial2.setTX(D8), Serial2.setRX(D9) vor Serial2.begin. Die bisherige SPI-Slave-Alternative ist wegen nicht geroutetem PA3/SCK **keine funktionierende PCB-V1.2-Schnittstelle**.

## UART-Frame v1 (festes on-wire-Protokoll)

**Parameter:** 115200 Baud, 8 Datenbits, keine Parität, 1 Stopbit (8N1), Byte-Reihenfolge little-endian.

| Position | Bytes | Inhalt |
| --- | ---: | --- |
| 0–1 | 2 | Synchronisierung A5 5A |
| 2 | 1 | Version 01 |
| 3 | 1 | Nachrichtentyp (01 = GET_SNAPSHOT, 81 = SNAPSHOT) |
| 4 | 1 | Sequenznummer uint8, bei 255 wieder 0 |
| 5 | 1 | Nutzdatenlänge uint8, maximal 59 |
| 6… | 0 oder 59 | Nutzdaten |
| Ende | 2 | CRC16-CCITT-FALSE über Position 2 bis zum Ende der Nutzdaten, little-endian |

CRC-Parameter: Polynom 0x1021, Startwert 0xFFFF, ohne Reflection/Final-XOR. GET_SNAPSHOT ist genau **8 Bytes** und hat **keine Nutzdaten**. Golden-Testframe für Sequenz 0x37:

    A5 5A 01 01 37 00 46 59

SNAPSHOT ist genau **67 Bytes** und hat **59 Bytes Nutzdaten**:

| Payload-Feld | Bytes | Format |
| --- | ---: | --- |
| uptime_ms | 4 | ATtiny-Laufzeit uint32 |
| module_status | 1 | derzeit 0, reserviert |
| Kanal T0…T8, jeweils 6 Bytes | 54 | centiC int16 LE (2), ageSeconds uint16 LE (2), flags uint8 (1), fault uint8 (1) |

Die Flagdefinition kommt direkt aus [sampler_core.hpp](../src/temperature/sampler_core.hpp): HasSample=0x01, Valid=0x02, Converting=0x04, Stale=0x08, Error=0x10. fault ist der dort definierte Fehlercode 0–8 (darunter NoSensor, ReadFailed, PowerOn85 und Recovering). Negative Temperaturen behalten ihr Vorzeichen. Eine fehlende Messung hat ageSeconds=0xFFFF und das Valid-Flag **nicht** gesetzt. Der RP verwirft inhaltlich widersprüchliche Pakete auch dann, wenn deren CRC stimmt.

**Stabilitätsregel:** Der ATtiny beantwortet nur korrekt gerahmte GET_SNAPSHOT-Anfragen. Der RP akzeptiert nur vollständige Frames mit passender Version, gültiger CRC, passendem Typ, aktueller Sequenznummer und fehlerfreiem Kanaldatensatz. Alte/gestörte Antworten ersetzen niemals den letzten gültigen Datensatz.

## Implementierung

| Baustein | Datei | Aufgabe |
| --- | --- | --- |
| Wire Codec und Parser | [temperature_protocol.hpp](../lib/common/temperature_protocol.hpp) | Header, CRC, little-endian, Frame-Parser, 9-Kanal-Encoding/Decoding |
| RP Poll-/Offline-Zustand | [temperature_client_core.hpp](../lib/common/temperature_client_core.hpp) | Sequenz, Requesttimeout, Status, gecachte Daten und Altersberechnung |
| ATtiny UART Responder | [temperature_link.cpp](../src/temperature/temperature_link.cpp) | serialisierte Snapshots ohne OneWire-Abfrage auf Request |
| ATtiny Setup | [main.cpp](../src/temperature/main.cpp) | USART0 ALT1, 115200 Baud, bestehende EEPROM-Config laden, temperaturLink starten |
| RP UART-Adapter | [temperature_bridge.cpp](../src/controller/temperature_bridge.cpp) | Serial2-Parser/Anfrage, Online- und Sensorstatus |
| RP Setup / Loop | [main.cpp](../src/controller/main.cpp) | GPIO8/9, separater UART1; die KNX-Serial1-Schnittstelle bleibt bestehen |

**Nichtblockierendes Verhalten:** Der ATtiny verarbeitet maximal 24 RX-Bytes und gibt höchstens 16 Antwortbytes pro loop()-Aufruf aus. Ein 67-Byte-Frame wird über mehrere Iterationen übertragen; bei vollem Sendepuffer wird nicht busy-waited oder flush() aufgerufen. Der RP verarbeitet maximal 48 RX-Bytes pro loop()-Aufruf. Zwischen unvollständigen Byteströmen von mehr als 100 ms setzt der Parser zurück. Neue Polls werden nicht parallel zu einer laufenden RP-Anfrage gestartet.

**Polling-Defaults (noch nicht ETS-konfigurierbar):**

| Parameter | Wert |
| --- | ---: |
| RP GET_SNAPSHOT Intervall | 3 Sekunden |
| Antworttimeout | 400 ms |
| Transport offline nach letzter gültiger Antwort | 15 Sekunden |
| UART Baudrate | 115200 Baud |
| Sensorabtastung (ATtiny, aus KNX013) | 10 Sekunden Default, ältere EEPROM-Einstellungen können abweichen |

Der RP liefert einen Status online nur, wenn innerhalb der letzten 15 s ein vollständiger gültiger Snapshot einging. Für jeden Temperaturwert ist zusätzlich das Valid-Flag und der jeweilige Fühlerfehler zu berücksichtigen. Ein alter gespeicherter Messwert ist **kein aktueller Temperaturwert**; die Anwendung KNX015 darf offline/stale Werte nicht als live publizieren. Empfang ist bewusst **auch vor einer ETS-Programmierung** aktiv, damit Diagnose später unabhängig von der KNX-Konfiguration möglich ist.

## Konfiguration, Kompatibilität und Grenzen

Der frühere serielle Debug-/Config-Dispatcher auf den ATtiny-Standardpins PB2/PB3 ist für die neue PA1/PA2-UART-Leitung **deaktiviert**. Die alten Quellmodule bleiben zunächst zur Migration im Git erhalten, werden aber nicht initialisiert. Das ursprüngliche ConfigManager-EEPROM-Format ist erhalten, ebenso der 10-Sekunden-Default. **Eine externe Änderung der ATtiny-Konfiguration über die bisherige serielle API ist derzeit nicht möglich**. Das ist eine bewusst dokumentierte Übergangsanforderung für das ETS-/Konfigurations-Folgepaket; der neue Binärkanal darf nicht mit ungerahmten Legacy-Serial-Nachrichten vermischt werden.

Der RP2040 bearbeitet die UART-Daten **nur im RAM**. Noch nicht implementiert: KNX-T0…T8-DPT9.001-Gruppenobjekte, ETS-parametrierbare Sendehäufigkeit, Raumregler und Motorantrieb. Die Hersteller-/Bestückungsfrage U25 (ATtiny3216 versus ATTINY1616 im alten MPN) und die Spannungsversorgung bleiben physisch offen.

## Reproduzierbare Qualitätssicherung

Im Repo-Root des LLO Desktop Agents:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_uart.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_sampler.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_temperature_bridge.py --scope all --strict
    C:\Users\LLO\.platformio\penv\Scripts\pio.exe run -e temperature
    C:\ASH\Tools\python-3.13.15\python.exe tools\build_controller_isolated.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py

Die vier KNX014 Native-C++-Suites prüfen den tatsächlichen [Codec](../tests/native/test_temperature_protocol.cpp), die [Client-Zustandsmaschine](../tests/native/test_temperature_client.cpp), den [ATtiny-Responder mit neun simulierten Fühlern](../tests/native/test_temperature_link_integration.cpp) und den [RP2040-UART-Adapter](../tests/native/test_controller_uart_integration.cpp). Dazu kommen die bestehenden zwei KNX013-Suites.

**Build-Gates:** ATtiny PlatformIO temperature: **PASS**, 983/2048 B RAM, 8480 B Programm (im letzten Stand vor dem Scope-Commit). RP2040 controller: **PASS**, isolierter Build mit 52.008/262.144 B RAM und 154.320 B Flash im Test-Build. Der RP-Build ist absichtlich außerhalb des Repo-Roots gelaufen, da das vorhandene OpenKNXproducer-Pre-Script sonst die kanonische include/knxprod.hpp überschreiben könnte. Der Hash der Originaldatei blieb unverändert. Die **tatsächliche Hardwarekommunikation** wurde nicht getestet.

**Offene ETS-Produktwarnungen:** Der OpenKNXproducer erzeugt im isolierten Build weiterhin Makro-Neudefinitionen für KoT0–KoT8 sowie ältere ungültige, durch Bindestriche gebrochene Ko-Bezeichner. Der Compiler baut den UART-Code trotz dieser Warnungen. Das ist **keine Freigabe** für den späteren KNX-Gruppenobjektzugriff. Die Produkt-XML-/Header-Bereinigung aus [ETS_PRODUCT_AUDIT.md](ETS_PRODUCT_AUDIT.md) muss spätestens vor KNX015/016 erfolgen.

## Gate 4 und nächster Slice

ASH KNX014 schließt erst nach erfolgreich geprüftem Code-/Dokumentations-Diff sowie zwei Git-Commits (Implementation und Closing). KNX015 übernimmt später DPT 9.001 KNX-Übertragungen, Telegrampufferung und ETS-Senderaten. Hardware-Power-Gates und Motorschutz bleiben davon unabhängig.
