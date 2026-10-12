# Software-first: zwei Firmwares, Temperaturpfad und KNX-MVP

**Stand:** 2026-10-12. **Typ:** software-first Architektur, urspruenglich aus **KNX012**, mit KNX013-Sampler, [KNX014-UART-Bruecke](KNX014_UART_BRIDGE.md) und [KNX015-ETS-DPT9.001-Sendepfad](KNX015_TEMPERATURE_PUBLISH.md) implementiert. **Achtung:** Die Tabellen zu Bestandsfirmware und Pinfehlern in Kapiteln 2/3 beschreiben den **Vor-KNX013-Ausgangszustand**. Der neue Stand steht in [KNX013_ATTINY_SAMPLER.md](KNX013_ATTINY_SAMPLER.md). Echte Hardware-/KNX-Integration nicht freigegeben.

## 1. Ziel und Prioritaet

Der **ATtiny3216** liest neun voneinander getrennte Dallas-/1-Wire-Sensoreingaenge ein und haelt stets einen **zuletzt gueltigen, mit Zeitstempel/Qualitaet versehenen Snapshot** bereit. Der **RP2040** fragt diese Werte ueber die bestehende serielle Verbindung der PCB V1.2 ab, publiziert sie ueber KNX und uebernimmt spaeter pro Raum die Regelung sowie exklusiv sequenzielle Motorbewegungen. **Der RP2040 wartet niemals auf die DS18B20-Konvertierungszeit.**

### Physikalische Benennung (verbindliches fachliches Mapping)

| Logischer Index | PCB-Netz | Rolle | KNX-Verwendung |
| --- | --- | --- | --- |
| T0 | T0 | Zentraler **Vorlauf** (Heizkreisverteiler) | Vorlauf-Isttemperatur |
| T1 | T1 | **Ruecklauf Heizkreis/Motor M1** | Ruecklauf 1; optional Delta-T 1 = T0 - T1 |
| T2 | T2 | Ruecklauf Heizkreis/Motor M2 | Ruecklauf 2 |
| T3 | T3 | Ruecklauf Heizkreis/Motor M3 | Ruecklauf 3 |
| T4 | T4 | Ruecklauf Heizkreis/Motor M4 | Ruecklauf 4 |
| T5 | T5 | Ruecklauf Heizkreis/Motor M5 | Ruecklauf 5 |
| T6 | T6 | Ruecklauf Heizkreis/Motor M6 | Ruecklauf 6 |
| T7 | T7 | Ruecklauf Heizkreis/Motor M7 | Ruecklauf 7 |
| T8 | T8 | Ruecklauf Heizkreis/Motor M8 | Ruecklauf 8 |

**Wichtig:** Die Sensoren erfassen Vor-/Ruecklauf am Verteiler, **nicht** automatisch die jeweilige **Raumluft-Isttemperatur**. Fuer Modus "Raumtemperatur regeln" wird eine externe KNX-Raumtemperatur oder ein explizit als Raumfuehler installierter Sensor benoetigt. Kein stilles Verwenden von T1..T8 als Raumtemperatur.

## 2. Ist-Zustand in der Firmware (direkt aus dem Repository)

| Bereich | Quellstand | Befund |
| --- | --- | --- |
| ATtiny Firmware | [main.cpp](../src/temperature/main.cpp) | `Config.resolution=12`, `updateRate=5.0f` Sekunden, `spiTemperature=2.5f`; initialisiert `Serial`, OneWire/Temperaturen, SPI0-Slave und SerialDispatcher |
| ATtiny Temperaturklasse | [temperature.cpp](../src/temperature/temperature.cpp) | `requestTemperatures()` und `getTempCByIndex(0)` direkt im `update()`; bei 12 Bit potenziell blockierend; `temperature > 0` akzeptiert gueltige 0/negative Werte nicht |
| ATtiny Kanalregister | [temperatures.cpp](../src/temperature/temperatures.cpp) | neun Instanzen, versetzte Start-Offsets um 500 ms; ungueltige Werte werden als `0.0f` zurueckgegeben und sind damit nicht unterscheidbar |
| ATtiny SPI | spi-slave.cpp (historisch im Git; in KNX013 entfernt) | Byte mit Kanalindex einlesen, Wert * 2.5 als ein `uint8_t` abgeben; ohne CRC, Status, Alter und ohne dokumentierte Zweit-Byte-Antwortphase |
| ATtiny SerialDispatcher | [serial_message_dispatcher.cpp](../src/temperature/serial_message_dispatcher.cpp) | Bisher Status-/Konfigurationskommunikation, **keine neun Temperaturwerte per definiertem Request-Snapshot-Protokoll** |
| RP2040 Firmware | [main.cpp](../src/controller/main.cpp) | Init von KNX und Poll `knx.loop()`; **kein** UART/SPI-Sensortreiber, Snapshot, Publikationsscheduler, Soll-/Ist-Regler oder Motorpositionssteuerung |
| ETS XML | [Produkt-Audit](ETS_PRODUCT_AUDIT.md) | neun vorhandene KNX-KO T0..T8 vom Typ DPT 9.001, aber nicht als End-to-End-Telegrammfluss implementiert. Dynamische Produktdarstellung unvollstaendig |

Der DS18B20 ist die **naheliegende Sensorfamilie** anhand von DallasTemperature, OneWire und dem bestehenden Codekommentar, nicht anhand einer geprueften realen Sensoraufschrift. Hersteller: [DS18B20 Datenblatt (Analog Devices)](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf). Maximale Konvertierungszeiten: 9 Bit ~94 ms, 10 Bit ~188 ms, 11 Bit 375 ms, **12 Bit 750 ms**. Nach der Messung liest man das zuletzt fertige Ergebnis aus dem Snapshot.

## 3. Schaltplan/PCB V1.2 und Framework: belegte Pin-Konflikte

**Nachweisbasis:** [EasyEDA PCB V1.2](../schematic/pcb_knx-valve-control_v1.2.json), [ATtiny Pin-Konfiguration](../src/temperature/config.hpp), fruehere SPI-Routine (im Git-Verlauf; in KNX013 entfernt), [Microchip ATtiny3216 SOIC20-Datenblatt](https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny3216-17-DataSheet-DS40002205A.pdf) und **das tatsaechlich installierte** megaTinyCore `variants/txy6/pins_arduino.h` (PIN_PA4=0, PIN_PA5=1 ...). Der [statische Pin-Audit](../tools/audit_temperature_bridge.py) kann dies wiederholt ausgeben.

| Netz | ATtiny SOIC-20 Pin | Physischer Port | MegaTinyCore Arduino-Digitalpin | Bisheriger Firmware-Pin | Abweichung |
| --- | ---: | --- | ---: | ---: | --- |
| T0 | 3 | PA5 | **1** | 0 (PA4) | falsch |
| T1 | 4 | PA6 | **2** | 1 (PA5) | falsch |
| T2 | 5 | PA7 | **3** | 2 (PA6) | falsch |
| T3 | 6 | PB5 | **4** | 3 (PA7) | falsch |
| T4 | 7 | PB4 | **5** | 4 (PB5) | falsch |
| T5 | 10 | PB1 | **8** | 5 (PB4) | falsch |
| T6 | 13 | PC1 | **11** | 8 (PB1) | falsch |
| T7 | 12 | PC0 | **10** | 11 (PC1) | falsch |
| T8 | 11 | PB0 | **9** | 10 (PC0) | falsch |

**Keine dieser neun Konfigurationen passt derzeit zur PCB V1.2**. Hardware-Anschlussnamen folgen dem PCB, nicht den Kommentaren im Quellcode. Beim Debuggen nicht "T0" an den falschen Arduino-Pin schreiben.

Zusatzbefunde:

- PCB U25 Pin 19 / **PA3 = SPI0 SCK** ist **nicht** mit dem RP2040 verbunden. SPI0 im vorhandenen Signalrouting daher **nicht** als funktionsfaehiger synchroner Transport annehmen.
- ATtiny Standard-SPI0 `SS=PA4` (PCB `CS`, Pin 2), aber Firmware `Pin::SPI_CS = 12` = **PC2**, PCB-Netz `T_INT` (Pin 14); die gewaehlte Initialisierung widerspricht der Hardware.
- **UART-Leitungen sind vorhanden:** ATtiny **PA1/Pin17 = T_RX-Netz** (RP2040 GPIO9, RX), ATtiny **PA2/Pin18 = T_TX-Netz** (RP2040 GPIO8, TX). Das ist elektrisch als UART-Verbindung passend, wenn ATtiny TX auf PA1 und RX auf PA2 per PORTMUX-Alternative gesetzt werden.
- Achtung Framework: megaTinyCore `Serial` liegt fuer ATtiny3216 **standardmaessig auf PB2/PB3** (PCB `TXD`/`RXD` fuer Debug), nicht auf PA1/PA2. Fuer die RP-Verbindung muss USART0 ALT1 (`PA1=TX`, `PA2=RX`) explizit konfiguriert werden. Danach ist die identische USART-Hardware nicht gleichzeitig auf den Debugpins verfuegbar. Genaue Core-API im Implementierungsslice validieren.
- SPI0 MOSI/MISO verwenden PA1/PA2 und kollidieren mit diesem UART-Transport. **SPI-Slave nicht parallel dazu aktivieren**; U25 `CS` und `T_INT` erst nach eigenem Boardtest optional als Handshake nutzen.
- RP2040 `TemperaturesTx = D8`, `TemperaturesRx = D9` existieren schon im [Controller-Header](../src/controller/config.hpp), werden aber nicht als Temperatur-UART initialisiert. Die KNX-UART-Schnittstelle liegt getrennt an RP GPIO0/1.

**Entscheidung fuer bestehende PCB V1.2:** Gerahmtes **UART** auf PA1/PA2 / RP GPIO8/9 als Temperaturtransport spezifizieren, solange die reale Platine nichts anderes beweist. SPI erneut nur fuer eine kuenftige PCB-Revision mit vollstaendiger SCK-Leitung untersuchen.

## 4. ATtiny-Firmware: nicht-blockierender Temperatur-Sammler

Entwicklung in [KNX013](ROADMAP.md), separate Gate-Tests mit kompiliertem ATtiny-Target:

1. Pin-Mapping vor allen Messungen auf die physikalischen PCB-Netze T0..T8 korrigieren und nach festen `PIN_PA5` ... Symbolen statt "magic numbers" benennen.
2. Acht Ruecklauf- plus ein Vorlauf-Fuehler, jeweils **eigener 1-Wire-Bus**. Sensor pro Anschluss identifizieren; `DEVICE_DISCONNECTED_C`, 85 C Power-on-Sentinel, CRC, Adresse und Zeitstempel getrennt behandeln.
3. Nicht blockierende Konversion per Kanalzustand `IDLE -> CONVERTING -> READ -> VALID/FAULT -> WAIT`; Konversionen zeitlich gestaffelt anstossen, so dass keine 750-ms-Wartezeit in `loop()` auftritt. Die DallasTemperature-Bibliothek bzw. ihr Async-Modus ist auf Target zu pruefen.
4. **Double-Buffer/atomarer Snapshot**: Kanalwert, Valid-Flag, Alter, Fehlertyp; nie zwei Byte einer Temperatur waehrend UART-Transfer inkonsistent ueberschreiben; keine I2C/UART-Arbeit aus 1-Wire-ISR.
5. **Konfigurierbarer, langsamer Abtasttakt**: als erster Testwert 10 Sekunden pro Fuehler bei 12 Bit; 5 Sekunden aus Bestandsfirmware bleiben dokumentiert. Temperaturauflosung 11/12 Bit spaeter messbar abwaegen; echte Limits erst nach Test fixieren.
6. Sensorfehler als **ungueltig** ausweisen, nicht `0 C` senden; 0 C und negative Temperaturen sind grundsaetzlich gueltige Messwerte.

## 5. Zwischen-MCU-Protokoll: ein "letzter Stand" statt Live-OneWire

Geplanter Vertrag [KNX014](ROADMAP.md), zu versionieren und als identische portable Header/Tests fuer ATtiny und RP2040 bereitzustellen:

- Der RP2040 fragt periodisch mit `GET_SNAPSHOT` an, der ATtiny antwortet sofort aus seinem **zuletzt konsistent gespeicherten Snapshot**. Keine OneWire-Aktion auf den synchronen Anfragepfad.
- **Vorschlag Wire-Frame v1:** zwei Syncbytes `A5 5A`, `version=1`, `message_type`, `sequence`, `payload_len`, `payload`, `CRC16-CCITT`; Multi-Byte-Felder Little-Endian. `GET_SNAPSHOT=0x01`, `SNAPSHOT=0x81`. **Designentwurf, noch nicht implementiert**.
- `SNAPSHOT` Payload vorgeschlagen: `uint32_t uptime_ms`, fuer jeden der neun Kanaele `int16_t temperature_centiC`, `uint16_t age_seconds`, `uint8_t flags` (VALID, CONVERTING, SENSOR_ERROR, STALE), `uint8_t module_status`. Damit ergeben sich 50 Byte Payload, 58 Byte Rahmen.
- Der RP2040 prueft CRC, Version, Sequenz, Laenge und Zeitlimit; **verwirft** Fehlerpakete und markiert zu alte Werte. Keine Rueckmeldung `0.0` als pauschales "kein Sensor".
- Abfrage zum Start beispielsweise alle **2–5 Sekunden**, aber **unabhaengig** vom 10-Sekunden-Sensorzyklus und vom erheblich selteneren KNX-Telegrammversand. Diese Zahlen sind vorgeschlagene Defaults, nicht Hardwaremessungen.
- Jede Firmware hat ihre eigene Verantwortung: ATtiny fuer Sensorfehler und Datenqualitaet; RP2040 fuer Transport-Timeout, KNX-Sendekontrolle, Raumparameter und Motoren.
- Transparente UART-Diagnostik nicht ungeprueft auf denselben Pins/Frames mischen. Debug ggf. getrennt, benoetigt aber wegen USART0-Portmux ein explizites Design.

## 6. RP2040: KNX-Temperaturen zuerst, Motoren spaeter

**KNX015** implementiert fuer einen ersten KNX-Test nur **neun Messwerte** auf den vorhandenen T0..T8-Objekten (DPT **9.001**, 2-Byte-Temperatur) plus mindestens Diagnose "Temperaturmodul online/gueltig". Keine Motorbewegung.

ETS-konfigurierbar und im Firmwarecode begrenzt:

| Vorgesehener Parameter | Erster Entwurfswert | Wirkung |
| --- | --- | --- |
| ATtiny Abtastintervall | 10 s | Intervall der lokalen 1-Wire-Konversion |
| RP2040 Poll-Intervall | 2–5 s | Holt letzten Mess-Snapshot ab |
| KNX Mindestabstand pro KO | 30 s | Kein Telegramm-Fluten |
| KNX zyklisch / Heartbeat | 60–300 s, z.B. 120 s | Geplanter periodischer Messwert |
| KNX send-on-change Schwellwert | z.B. 0,2 C | Zusaetzliche Sendung, begrenzt durch Mindestabstand |
| Stale-Timeout | z.B. 30 s / 3 × Abtastintervall | Erkennbarer Sensorausfall, kein stilles Weiterverwenden alter Werte |

Werte **erst nach KNX-/Busmonitor-Test freigeben**, mit begrenzten ETS-Wertebereichen. Beim Start keine unvalidierten Temperaturen oder alte Sentinel-Werte senden; T0..T8 versetzt versenden, nach Neustart und bei Bus-Reconnect geordnet initialisieren.

KNX-Datenfluss:

```text
DS18B20-artige Fuehler T0..T8
 -> ATtiny3216 non-blocking 1-Wire Sampler / Snapshot
 -> UART (gerahmte Abfrage, CRC/Alter)
 -> RP2040 Snapshot Store
 -> KNX KNX-TP Bus (DPT 9.001 T0..T8, per ETS einstellbare Rate)
 -> ETS6 / KNX-Gruppenadressen / Busmonitor
```

**KNX016** importiert eine getrennt erzeugte, versionierte `.knxprod` in ein Testprojekt ETS6. Das bestehende XML enthaelt 9 Temperatur-KOs, aber [ETS_PRODUCT_AUDIT.md](ETS_PRODUCT_AUDIT.md) dokumentiert nur eine dynamische Channel-Seite, gemischte 5.004-Stellwerte und generierte ungueltige C++-Ko-Namen. Diese Produktdatenfehler fuer den Temperatur-MVP beheben, ohne ein produktives ETS-Projekt unkontrolliert umzunummerieren.

## 7. Zweite Ausbaustufe: zwei Betriebsarten pro Raum, mehrere Heizkreise

1. **Modus A: Raum-Soll/Ist**: pro Zone (Raum) 1 Solltemperatur und 1 gueltige Ist-Raumtemperatur von geeignetem KNX-Raumfuehler; langsamer PI-Regler mit Anti-Windup, Begrenzung und Totzone erzeugt Stellziel in **0..100 %**. Ein hydraulischer Stellantrieb kann Zwischenstellungen fahren, also **keine alleinige Zweipunktregelung**.
2. **Modus B: Direkter KNX-Stellwert**: ein Stellwert pro Zone, DPT **5.001** (skalierte 0..100 %) und ohne lokalen Raum-PI. Bestehender DPT 5.004 muss bewusst migriert/abgebildet werden.
3. **Gruppierung:** M1/M2/M3 koennen bspw. zu Zone1 gehoeren; alle bekommen den gleichen Zonenbedarf, aber jeder seine eigene Referenzposition/Hubzeit. Nur **ein** Motor gleichzeitig wegen gemeinsamem INA219-Shunt/Richtungsleitungen.
4. **Hydraulik ist gekoppelt:** Wenn ein Ventil drosselt, aendern sich je nach Pumpenkennlinie und Ventileinstellung die Druckdifferenzen/Volumenstroeme anderer Kreise. Deshalb keine schnelle gegenseitige Nachregelung nur anhand der Ruecklauftemperaturen. Delta-T = T0 - Ti ist **Diagnose/Optimierungsindiz**, kein direkter Volumenstromsensor. Erst stabile Raumregelung, dann vorsichtige optionale hydraulische Balancierung mit Zeitkonstanten, Limits und Messbasis.
5. **Schutz/Fehler:** ungueltige Raumtemperatur, alter Snapshot, blockierter Motor, unbekannte Position, KNX-Ausfall, Stromversorgungswechsel -> klares konfigurierbares Safe-State-Konzept; Firmware-Safety-Grenzen unabhaengig von ETS setzen.
6. **Hardware-Gate bleibt bestehen:** Motorbewegungen und INA219-Endanschlagverfahren erst nach den vorhandenen KNX002/003/004/005-Pruefungen fuer Shunt, reale 3,3-V-Versorgung und sichere Ausgaenge.

## 8. Software-First-Slice-Abfolge

| Phase | Slice | Minimales lauffaehiges/abnehmbares Ergebnis |
| --- | --- | --- |
| A | **KNX012** (diese Planung) | Gepruefte Pin-Spezifikation, UART-Entscheidung und Task-Chain; bestehende Firmwares unangetastet |
| B | **KNX013** ATtiny-Sampler | Alle neun physischen Pins korrekt, asynchroner OneWire-Zyklus, Validitaet/Alter, Build und Host-Tests |
| C | **KNX014** UART-Bridge | RP fragt neun Snapshots vom ATtiny mit CRC/Timeout ab; Mock-Tests und Build beider Firmwares |
| D | **KNX015** KNX-Publish | RP versendet T0..T8 DPT 9.001 und meldet Fehler; Rate/delta ETS-konfigurierbar, Bus-Simulation/Messung |
| E | **KNX016** ETS6-Temperatur-MVP | Neue `.knxprod` reproduzierbar erzeugt und isoliert in ETS6 getestet; GroupObjects/Busmonitor |
| F | **KNX008/009** ETS-Raeume und **KNX004..006/010** Antrieb/Regelung | Zonen, direkte 0..100 %, langsamer Raumregler und sicher kalibrierte Ventilpositionen; eigene Gate-Freigaben |

**KNX007** war vorher ein zu grober "Temperaturpfad"-Plan. Diese Aufgaben sind fuer die Ausfuehrung in **KNX013–KNX016** aufgeteilt. Das ist eine Aufgabenzerlegung, **kein** rueckwirkend geschlossener oder implementierter Slice.

## 9. Explizite Abnahmekriterien und noch offene Evidenz

- **Ohne Hardware machbar:** Quellen-/Pin-Audit, Protokoll-Unit-Tests, ATtiny-/RP-PlatformIO-Build, synthetische 9-Kanal-Snapshots, KNX-DPT9.001 Encode-/Decode-Tests, XML/Producer-Sanity.
- **Hardware erforderlich:** Messen der realen DS18B20/sonstigen 1-Wire-Topologie, tatsaechlicher U25-Chiptyp, live PA1/PA2 UART, Stromversorgung unter Last; KNX-Busmonitor/ETS Download an physischem Geraet.
- **Niemals behaupten:** Ein statischer PCB-Test sei ein echter DRC oder ein erfolgreich gebautes Produkt ein ETS Import. Keine laufenden Motoren, solange Safety- und Power-Gates ausstehen.
- **KNX013 (implementiert):** Pin-Korrektur, nichtblockierende OneWire-Messungen und Sensor-Snapshots: [KNX013-Abnahme](KNX013_ATTINY_SAMPLER.md).
- **KNX014 (implementiert, Softwaretests):** 115200-Baud-UART ALT1 PA1/PA2 zu RP Serial2 GPIO8/9, Request/Response-CRC16, Fallback/Stale/Sequenzpruefung, beide Firmware-Builds offline PASS: [KNX014-Dokumentation](KNX014_UART_BRIDGE.md). **KNX015 Software implementiert:** KO25..33 DPT9.001 und KO34/35 Diagnosen, ETS-Intervall und Schwelle; siehe [KNX015](KNX015_TEMPERATURE_PUBLISH.md). **Naechster Slice: KNX016 ETS6-Importtest.** Noch keine Motoren/Hardwaretests.

## 10. Bereits ausgefuehrte Baseline-Softwarepruefungen (2026-10-10)

- **ATtiny PlatformIO Build:** `C:\Users\LLO\.platformio\penv\Scripts\pio.exe run -e temperature` beendet mit **Exit 0 / SUCCESS**; erzeugtes ignoriertes Artefakt `.pio/build/temperature/firmware.hex`, **23.506 Byte**. **Ein erfolgreicher Build beweist nicht korrekte Pinbelegung, reale OneWire-Messungen oder UART/SPI-Kommunikation.**
- **PCB/Core/Source-Audit:** `python tools/audit_temperature_bridge.py` Exit 0 als **Bestandsanalyse**, meldet 16 Software-/Integrationsluecken (davon 9 falsche T-Pins); `--strict` beendet absichtlich mit **Exit 2**, solange diese Befunde nicht behoben sind. Dieses strikte Gate ist fuer KNX013/014 vorgesehen.
- **RP2040 Build:** in KNX012 **nicht** angestossen. Das bestehende `assets/open-knx-producer.py` wird beim Controller-Build ausgefuehrt und schreibt ggf. die kanonische `include/knxprod.hpp` um; Generator/Header-Migration erst im isolierten Folgeslice sichern.
- **Keine Firmwarequellen veraendert**, kein ATtiny geflasht, kein KNX-Telegramm versendet, keine Motorbewegung.
