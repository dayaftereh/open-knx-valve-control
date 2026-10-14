# KNX040 – ATtiny3216 geflasht, RP2040 ↔ ATtiny UART real PASS

**Stand 14.10.2026.** LLO Desktop Agent 0.8.2. **KNX, Motoren und DS18B20-Sensoren weiterhin nicht angeschlossen.** Der Nutzer hat ATtiny-Firmware-Flash und erste Temperaturkommunikationsprüfung explizit beauftragt. Erst die Temperatursensoren selbst muss der Nutzer später physisch anschließen.

## 1. ATtiny3216: echter Write + Verify + unabhängiger Readback

- CH340 Programmer Windows **COM4 VID1A86:PID7523**, zuvor real ausgelesener Chip **ATtiny3216 Signatur 1E 95 21**. Sämtliche originalen Flash/EEPROM/Fuses/USERROW-Backups aus KNX039 vor dem Überschreiben erneut SHA256-verifiziert.
- Ursprüngliches Programm bewusst überschrieben. Vorbereitetes KNX038-Temperaturimage 8655 Flash-Bytes, SHA256 `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`.
- `pymcuprog write --device attiny3216 --tool uart --uart COM4 --filename <image.hex> --erase --verify --timing`: **Exit0**, Ausgabe `Ping response: 1E9521`, `Writing flash`, `Verifying flash`, `OK`, Operation 5,644 s.
- Nach Programmierung echter `pymcuprog read` von Flash (32 KiB), Fuses (9 B), EEPROM (256 B): **8655/8655 definierte Flash-Bytes stimmen exakt**, keine weiteren Nicht-FF-Bytes außerhalb des Imagebereichs, **Fuses UNVERÄNDERT**, **EEPROM UNVERÄNDERT**. Kein expliziter Fuse-Write, keine KNX-/Motoraktion.
- Original-Backups bleiben unter `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX039-ATtiny3216-readback-20261014`; zusätzlicher Nachher-Readback samt Checksums außerhalb Git unter `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX040-ATtiny3216-postflash-20261014\postflash_manifest.json`.

## 2. RP2040: separate Diagnose ohne KNX-Bus-/Motorlogik

Weil die reguläre KNX-Produktivfirmware noch den gefährlichen STKNX-TPUart-Treiber benutzt, **nicht** das Controller-Produktivimage flashen. Stattdessen [knx040_uart_diag](../tools/knx040_uart_diag/platformio.ini) als unabhängiges PlatformIO-Projekt gebaut: USB-CDC-Protokoll zum PC, `Serial2`/UART1 115200 Baud auf RP **GPIO8 (TX) → ATtiny PA2(RX)** und **GPIO9 (RX) ← ATtiny PA1(TX)**. Gemeinsames [KNX014-Paketprotokoll](../lib/common/temperature_protocol.hpp), 8-Byte-GET, 67-Byte-9-Kanal-Antwort, Sequenz-ID und CRC16-CCITT-Prüfung. **Keine ETS-/KNX-/Motorfunktionen.** STKNX-`GPIO0 KNX_TX` wird ab `setup()` LOW geschaltet, aber **nicht bootfest verriegelt**: KEIN KNX-Bus!

Arduino-Pico 5.5.0, RP2040, isolierter PlatformIO-Build **SUCCESS**, RAM 9144 B, Flash 62904 B. `pio upload` im separaten Projekt **gesperrt** (absichtlich fehlendes Uploadkommando), tatsächlicher USB-Flash nur nach Prüfung über ROM-Bootloader/`picotool load -v -x`. Existierendes KNX036-USB-only-Image als Rollback unverändert aufbewahrt.

### Wichtigster beim echten Test gefundener Fehler

V1-Diagnose (UF2 SHA256 `91de63d5e58ae97242c4a2eee7fa319d5fc55541f1548c8bfac1292121746342`) lieferte `uart_configured=1`, aber 0 UART-Requests/Snapshots. Reproduzierbarer Grund in der installierten Datei `C:\Users\LLO\.platformio\packages\framework-arduinopico\cores\rp2040\SerialUART.cpp`, Methode `availableForWrite()`:

    return (uart_is_writable(_uart)) ? 1 : 0;

Der Aufruf gibt **boolesch 0 oder 1**, nicht die freie FIFO-Größe zurück. Die bisherige Prüfung `Serial2.availableForWrite() < 8` verhindert damit dauerhaft jeden 8-Byte-Request. In der **isolierten Testfirmware** auf `Serial2.availableForWrite() <= 0` korrigiert; `Serial2.write(frame,8)` funktioniert.

**Unabhängig neu entdeckter Produktionsfehler (noch NICHT im Originalcode geändert):** `src/controller/temperature_bridge.cpp` verwendet dieselbe falsche `uart_->availableForWrite() < 8`-Prüfung! Vor einem späteren Controller-/KNX-Firmwareeinsatz ist dort im eigenen qualifizierten Slice derselbe Boolean-Fix erforderlich. Die historischen KNX-Audits enthalten diese Datei in ihren eingefrorenen Quellprüfungen. Controller-KNX-Firmware bleibt wegen STKNX-Idle-Pegel-/TPUart-Problems weiter **gesperrt**, nicht flashen.

Nach Reparatur RP2040 v2-UF2 SHA256 `e9de4dcb66a0afd4fa906d5a5591bc7785cb6c8bc71f57e20bb4104069c31639` gebaut, USB-CDC COM7 1200 Baud DTR→ROM `2E8A:0003`, `picotool load -v -x` 100 % geschrieben und verifiziert, automatischer Neustart wieder COM7 `2E8A:000A`.

## 3. Tatsächliche Temperatur-UART-Prüfung: PASS (ohne Sensoren)

Erste 16-s-COM7-USB-CDC-Liveaufnahme ergab:

| Messgröße | Live-Ergebnis |
| --- | --- |
| CRC-/Sequenz-/Typ-geprüfte 67-Byte-Snapshot-Antworten | **8/8** |
| Kanalzeilen | **72** (je T0–T8) |
| Timeouts | **0** |
| Verworfene Protokollantworten | **0** |
| Gültige Temperaturmessungen | **0**, da keine DS18B20 angeschlossen |
| Gemeldete NoSensor-Kanäle | **9/9** in allen Snapshots |

Beispiel vom echten Board:

    KNX040 SNAPSHOT seq=11 up_ms=597814 valid=0 no_sensor=9 faults=9 accepted=11 timeout=0 rejected=0
    KNX040 CH T0 flags=16 fault=1 age_s=65535 centiC=0
    KNX040 CH T1 flags=16 fault=1 age_s=65535 centiC=0
    ...
    KNX040 CH T8 flags=16 fault=1 age_s=65535 centiC=0

**Wichtig:** `flags=16` ist `Error`, `fault=1` bedeutet `NoSensor`, `age_s=65535` bedeutet *noch kein jemals gültiger Wert*. Die im Frame stehenden `centiC=0` dürfen NICHT als reale 0 °C ausgegeben werden.

Zusätzlich neues, **ausschließlich lesendes** [USB-CDC-Monitorwerkzeug](../tools/knx040_capture_uart.py) mit Aktionen `plan / probe / capture` aufgebaut und **live getestet**: zweite unabhängige 10-s-Aufnahme **5/5 erfolgreiche Snapshots**, 9/9 NoSensor je Frame, keine Timeouts. Der ATtiny hatte zu diesem Zeitpunkt bereits **153 gültige GET-Abfragen** beantwortet, weiterhin keine verworfenen Antworten.

Rohlogs und JSON-Beobachtungen ausschließlich lokal außerhalb Git:
- `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX040-rp2040-uart-temp-20261014\com7-live-observation.json` (V1-Fehler)
- `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX040-rp2040-uart-temp-v2-20261014\com7-live-cdc-v2.txt`
- `...\KNX040-rp2040-uart-temp-v2-20261014\com7-live-observation-v2.json` und `knx040-repeat-capture.txt`.
- Projektweites [maschinenlesbares Ergebnis](KNX040_LIVE_TEMPERATURE_UART_EVIDENCE.json).

## 4. Nächster realer Sensor-Test

Die Sensoren sind **nicht montiert** und können nicht vom Agenten physisch angeschlossen werden. Der Nutzer soll **spannungsfrei und ohne KNX oder Motoren** nach tatsächlichem Schaltplan/Steckerpinout **einen DS18B20 an einen vorgesehenen 1-Wire-Kanal** anschließen und die Leitung/3-Draht-Versorgung kontrollieren. Firmware-Terminologie: **T0 gemeinsamer Vorlauf**, **T1–T8 einzelne Rücklaufkreise**; jeder Kanal besitzt eine eigene 1-Wire-Datenleitung.

Danach reicht es, die bereits auf dem RP2040 laufende KNX040-Diagnose abzuhören – kein neuer Flash nötig:

    Set-Location 'C:\ASH\Workspace\Projects\open-knx-valve-control'
    $py = 'C:\Users\LLO\.platformio\penv\Scripts\python.exe'
    & $py tools/knx040_capture_uart.py probe
    & $py tools/knx040_capture_uart.py capture --port COM7 --expect-serial E464401787522D33 --seconds 15

Nur ein Sensor mit `flags & 0x02` (Valid), `fault=0` und aktueller Probe darf als Celsius-Wert dargestellt werden. Fehlerkanäle weiterhin als NoSensor statt `0 °C` anzeigen.

## 5. Offene Hardware-Sicherheit

Das reale USB-/Temperatur-Protokoll ist gelungen, aber **keine KNX-Freigabe**: KNX035 R17 (externer Pull-up an STKNX TX mit aktivem HIGH, vorher U11 überhitzt, möglicher U9-Schaden), TPUart direkt am KNX-Sender unpassend; KNX034 F1-Bestückung T2,5 A vs. Schematic 630 mA, D1-Draht-Bypass und Quellen-/KNX-/USB-Rückspeisung noch offen. H-Brücken-Motorhardware ebenfalls nicht qualifiziert. COM4-UPDI arbeitet real, aber Spannung CN1.3/3,3 V und CN1.1 5-V-Rückspeisung nicht messtechnisch bewertet.

**Status:** `ATtiny3216_FLASH_WRITE_VERIFY_AND_POSTREAD_PASS`, `RP2040_TO_ATTINY_9_CHANNEL_UART_NO_SENSOR_PASS`, **keine echten Temperaturen, da keine Fühler angeschlossen**.
