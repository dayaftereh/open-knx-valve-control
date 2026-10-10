# KNX013 – ATtiny3216: nichtblockierender 9-Kanal-Temperatursammler

**Stand:** 11.10.2026. **Status:** Firmware implementiert, native C++ Tests sowie PlatformIO-Build erfolgreich. **Nicht freigegeben:** reale Sensor- und Boardtests, Flashen, UART-Kommunikation zum RP2040, KNX-Telegramme oder Motorbetrieb.

## 1. Fachliche Zuordnung

Der ATtiny sammelt neun unabhängige Dallas/1-Wire-Messungen, speichert jeweils den letzten gültigen Wert und meldet Gültigkeit, Fehler und Alter. Der RP2040 fragt diese Daten erst in KNX014 per UART ab. Die Rücklauftemperatur ersetzt **keine** Raumtemperatur für einen Raumregler.

| Sensor | Board-Port ATtiny3216 / megaTinyCore | Heizungsfunktion |
| --- | --- | --- |
| T0 | PA5 / PIN_PA5 (Arduino 1) | Zentraler Vorlauf |
| T1 | PA6 / PIN_PA6 (2) | Rücklauf Heizkreis M1 |
| T2 | PA7 / PIN_PA7 (3) | Rücklauf Heizkreis M2 |
| T3 | PB5 / PIN_PB5 (4) | Rücklauf Heizkreis M3 |
| T4 | PB4 / PIN_PB4 (5) | Rücklauf Heizkreis M4 |
| T5 | PB1 / PIN_PB1 (8) | Rücklauf Heizkreis M5 |
| T6 | PC1 / PIN_PC1 (11) | Rücklauf Heizkreis M6 |
| T7 | PC0 / PIN_PC0 (10) | Rücklauf Heizkreis M7 |
| T8 | PB0 / PIN_PB0 (9) | Rücklauf Heizkreis M8 |

Die Zuordnung wurde mit dem [EasyEDA-PCB V1.2](../schematic/pcb_knx-valve-control_v1.2.json) und der installierten megaTinyCore-Pinliste verglichen. Die Bestückung U25 (ATtiny3216/1616-Metadatenkonflikt) ist noch nicht physisch verifiziert.

## 2. Implementierung im Repository

- [src/temperature/config.hpp](../src/temperature/config.hpp): Alle neun Pin-IDs auf die tatsächlich gerouteten Ports geändert. Das gespeicherte Config-Layout aus Auflösung, Abtastintervall und historischem SPI-Skalierungsfeld bleibt kompatibel; letzteres wird nicht mehr verwendet.
- [src/temperature/sampler_core.hpp](../src/temperature/sampler_core.hpp): Hardwareunabhängige C++-Zustandsmaschine Discover → StartConversion → FinishConversion → Wait mit Zeitüberlauf-sicherem Millisekundentimer, wiederholtem Verbindungsversuch, Messwert-/Fehler-Snapshot.
- [src/temperature/temperature.cpp](../src/temperature/temperature.cpp): Neun OneWire-Instanzen, keine Heap-Neuanlage pro Kanal, DallasTemperature 4.0.5 mit setWaitForConversion(false), spätere CRC-geprüfte getTempC-Lesung. Ein Fühler wird nur bei Erstsuche oder nach Fehler erneut gesucht.
- [src/temperature/temperatures.cpp](../src/temperature/temperatures.cpp): Neun Sensoren jeweils 500 ms versetzt. Ein Speicher-Snapshot ist ohne neue 1-Wire-Abfrage abrufbar.
- [src/temperature/main.cpp](../src/temperature/main.cpp): Konfigurierter Default jetzt 10 Sekunden bei 12 Bit (vorher 5 Sekunden); vorhandene gespeicherte 5-Sekunden-Einstellungen bleiben erhalten. Serieller Debug-/Konfigurationspfad bleibt vorerst auf PB2/PB3.
- Die alten Dateien src/temperature/spi-slave.cpp und .hpp wurden entfernt. Die SCK-Leitung SPI0/PA3 ist auf PCB V1.2 nicht zum RP2040 verdrahtet; SPI0 darf nicht aus Versehen im neuen Firmwarestand aktiviert werden.

### Messablauf und Timing

Bei einer vorhandenen 3-adrig versorgten DS18B20-artigen 1-Wire-Sonde wird die Konversion sofort gestartet und die Steuerung kehrt in den Hauptloop zurück. Erst nach Ablauf der Wartezeit wird die Temperatur gelesen. Der ATtiny kann währenddessen die übrigen Kanäle und seine lokale Serial-Verarbeitung bedienen.

| Auflösung | Hersteller-Maximalzeit | Software-Wartezeit inklusive 20-ms-Puffer |
| --- | ---: | ---: |
| 9 Bit | ca. 94 ms | 114 ms |
| 10 Bit | ca. 188 ms | 208 ms |
| 11 Bit | 375 ms | 395 ms |
| 12 Bit | 750 ms | 770 ms |

Das Intervall ist über die existierende Temperaturkonfiguration wählbar, mit Codegrenzen von 2 bis 3600 Sekunden. Die neun Kanäle beginnen zeitlich versetzt. Ein nicht mehr erreichbarer Fühler wird alle zehn Sekunden wieder gesucht; gemessene Werte werden nach dem dreifachen Intervall als veraltet markiert. Eine Änderung der Auflösung benötigt eine erneute Initialisierung.

Die Dallas-Konvertierung blockiert nicht mehr für 750 ms. Einzelne ROM-/Scratchpad-Transaktionen sind weiterhin synchron und dauern kurz; reale Worst-Case-Latenzen wurden noch nicht mit Instrumenten vermessen.

## 3. Status-Snapshot für spätere UART-Übertragung

Die interne, noch nicht serialisierte C++-Struktur [TemperatureSampler::Snapshot](../src/temperature/sampler_core.hpp) besteht aus:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| centiC | int16 | Letzter gültiger Celsius-Wert × 100 |
| ageSeconds | uint16 | Alter seit letzter gültiger Messung, maximal 65535; 65535 falls noch nie gültig |
| flags | uint8 | HasSample=0x01; Valid=0x02; Converting=0x04; Stale=0x08; Error=0x10 |
| fault | uint8 Enum | None, NoSensor, ParasitePower, ReadFailed, PowerOn85, OutsideRange, SampleStale, NoSample, Recovering |

Ein ungültiger Kanal wird **niemals als aktuell gemessene 0 °C** ausgegeben. Die Legacy-Abfrage liefert dafür den Dallas-Sentinel DEVICE_DISCONNECTED_C (-127 °C). Gültige 0 °C und negative Werte sind erlaubt. 85 °C wird wegen des DS18B20-Power-On-Sentinels bewusst zurückgewiesen; damit ist ein wirklich exakt 85 °C messender Wert nicht unterscheidbar. Werte außerhalb -55 bis +125 °C und gemeldete Dallas-Fühlerfehler werden abgelehnt.

Das Board stellt 3-Draht-Sensorleitungen bereit. Parasitär versorgte Sensoren sind ohne qualifizierte Strong-Pullup-Schaltung nicht freigegeben. Das aktuelle Protokoll liefert die Daten nur im RAM der ATtiny-Hauptschleife; eine UART-ISR darf in KNX014 nicht ohne atomaren Snapshot-Copy zugreifen.

## 4. Wiederholbare Tests auf dem LLO Desktop Agent

Die folgenden Befehle aus dem Repository-Root prüfen ausschließlich Code und simulierte Fühler:

    C:\Users\LLO\.platformio\penv\Scripts\pio.exe run -e temperature
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_sampler.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_temperature_bridge.py --scope sensors --strict
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py

Der native Runner kompiliert mit GCC die echten C++-Dateien und zwei Testgruppen:

- [Core-Tests](../tests/native/test_sampler_core.cpp): Sensor fehlt/kommt wieder, 0 °C, Negativwerte, Sensorfehler, 85 °C, Parasitärversorgung, Stale-Status und Millis-Überlauf.
- [9-Kanal-Integration](../tests/native/test_temperature_integration.cpp): Produktionsdateien temperature.cpp und temperatures.cpp gegen simulierte OneWire-/Dallas-Schnittstellen, inklusive Rücklaufsensoren, Wiederanschluss und Abstecken.
- [Pin- und Integritätsaudit](../tools/audit_temperature_bridge.py): überprüft PCB/Quellcode für T0–T8, den nicht blockierenden Sensorpfad und die entfernte SPI0-Initialisierung. Im Modus all --strict meldet der Audit absichtlich die noch nicht implementierte KNX014-UART-Seite.

Ein erfolgreicher Compiler- oder Mock-Test **belegt weder reale Sensorfunktion noch erfolgreiche KNX-Buskommunikation**. U25-Chiptyp, reale Sensorfamilie, Netzteilqualität und Sensoranschlüsse müssen vor einem realen Flash-/Laborversuch geprüft werden.

## 5. Übergabe an KNX014

- USART0 des ATtiny3216 explizit auf ALT1 PA1(TX)/PA2(RX) konfigurieren. Diese Leitungen sind bereits zum RP2040 GPIO9(RX)/GPIO8(TX) verbunden. Der bisherige PB2/PB3-Debugkanal und die SerialConfig-Nachrichten müssen bewusst migriert werden.
- Ein versioniertes und CRC-geschütztes UART-Frame für GET_SNAPSHOT und neun Werte implementieren. Der ATtiny antwortet ausschließlich aus dem gespeicherten Snapshot ohne neue Dallas-Abfrage.
- RP2040-Timeouts, Alter, Gültigkeit und Fehler für jeden Sensor prüfen; erst anschließend KNX015-DPT9.001-Telegramme und ETS-Sendeintervalle implementieren.
- Motorfreigaben, INA219-Homing und externe 5-V-Einspeisung bleiben separat gesperrt, bis KNX002/003/004/005 Hardware- und Sicherheitsprüfungen erfolgreich abgeschlossen sind.
