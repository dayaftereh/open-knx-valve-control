# KNX031 – Offline UART-Analyse für T0…T8 (ATtiny → RP2040)

**Stand:** 13.10.2026. **Softwarestatus:** Rein dateibasierte Diagnose, mit dem produktiven C++-Protokoll KNX014 gegengeprüft. **Die Platine ist noch nicht angeschlossen.** Kein serieller Port, KNX-Bus, ETS6, UPDI oder Motor wurde angesprochen.

## Ziel und Beobachtungsgrenze

Wenn die V1.2-Platine später elektrisch freigegeben und ein passender, sicherer UART-Mitschnitt vorhanden ist, können wir die eigentliche Protokollübertragung des ATtiny unabhängig von einer KNX-/ETS-Konfiguration analysieren: KNX014 GET_SNAPSHOT-Anfragen, SNAPSHOT-Antworten, CRC16, Sequenz, T0–T8, Datenalter sowie Valid-/Fehlerkennzeichen.

**Wichtige Trennung:** RP2040 Serial2 GPIO8/9 ist die interne Verbindung zum ATtiny3216 auf PA2/PA1 (UART1 115200/8N1). Die RP2040-USB-CDC-Schnittstelle ist **nicht** automatisch ein Rohmitschnitt dieser Leitung. Die CN1-TXD/RXD-Pins des UPDI-Programmers sind ebenfalls **nicht** die interne aktive UART1-Leitung. Ein späterer Rohmitschnitt braucht eine eigens freigegebene hochohmige 3,3-V-geeignete Messverbindung und qualifizierte Masse/Versorgung. Kein Logikanalysator/Programmer wird von KNX031 geöffnet oder konfiguriert.

## Protokollquelle KNX014

Die Referenz ist ausschließlich [temperature_protocol.hpp](../lib/common/temperature_protocol.hpp) und der bereits native-getestete KNX014-Transport.

| Feld | Format | Regel |
| --- | --- | --- |
| Start | A5 5A | Synchronisationsbytes |
| Header | Version, Typ, Sequenz, Länge | Version 01, Payload höchstens 59 Byte |
| GET_SNAPSHOT | Typ 01, Länge 0 | 8 Byte insgesamt |
| SNAPSHOT | Typ 81, Länge 59 | 67 Byte insgesamt |
| CRC | 16 Bit little-endian | CRC-16/CCITT-FALSE, Polynom 1021, Start FFFF; über Header und Payload ohne Sync |
| Snapshot-Payload | Uptime u32 LE, Modulstatus 0, 9 × 6 Byte | Temperatur signed int16 in 0,01 °C; Age uint16 s, Flags, Fehlercode |

T0 = **Vorlauf**, T1…T8 = **Rückläufe M1…M8**. Diese Messstellen sind keine externen Raum-Isttemperaturen.

Flags: 0x01 HasSample, 0x02 Valid, 0x04 Converting, 0x08 Stale, 0x10 Error. Fehlercode 0…8: None, NoSensor, ParasitePower, ReadFailed, PowerOn85, OutsideRange, SampleStale, NoSample, Recovering. Keine unbekannten Flags/Fehlerwerte akzeptieren. Wenn Valid gesetzt ist, müssen HasSample gesetzt, Stale/Error gelöscht und fault=0 sein. Ohne HasSample gilt ageSeconds=FFFF. Reservierter Modulstatus muss 0 sein.

Eine reale **0 °C** oder negative Temperatur ist zulässig; ungültige/fehlende Sensoren werden **nicht** mit 0 °C aufgefüllt. Der Decoder zeigt einen Rohwert immer ausdrücklich als *reported_centiC* und nur mit bestätigtem Valid-Flag einen *reported_celsius_if_valid*. Er bestätigt dabei keine echte physische Temperatur.

## Kommandozeile auf LLO Home

```powershell
Set-Location 'C:\_myspace\workspace\open-knx-valve-control'
$py = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'
$sample = 'C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX031-native-oracle-example.hex'

# Erklärt unterstützte Offline-Funktionen, ohne Dateien/Geräte zu öffnen
& $py tools/knx031_uart_trace.py plan

# Kompakte Statistik aus gespeichertem Muster, ohne reale UART-Verbindung
& $py tools/knx031_uart_trace.py inspect --input $sample --format hex --summary-only

# Komplette 9-Kanal-Diagnose aus einem gesondert aufgezeichneten Binärdump
& $py tools/knx031_uart_trace.py inspect --input 'C:\Messungen\knx_uart_dump.bin' --format binary --max-records 10

# Host-Golden-Vektor und negative Tests
& $py tools/test_knx031_uart_trace.py
```

**Unterstützte Formate:** binär `.bin`/`.dat` oder ASCII-Hexdump `.hex`/`.txt` mit Leerzeichen/0x-Präfix, maximal 8 MiB. UNC-/Gerätepfade und unzulässige Dateitypen werden verworfen. Der Befehl öffnet niemals COM-Ports und bietet **keine** Geräte-/Uploadaction an. Bei langen Dumps schützt `--max-records` die ausgegebenen Einzeldatensätze (maximal 500); `--summary-only` eignet sich für die Agent-Ausgabe.

### Native Referenzdaten, bereits auf LLO Home erzeugt

Testquelle: [knx031_uart_vector_oracle.cpp](../tests/native/knx031_uart_vector_oracle.cpp) kompiliert die **echte C++ KNX014-Protokolldatei** mit WinLibs-g++ und erzeugt den GET-Frame für Sequenz 0x37 sowie eine gültige SNAPSHOT-Antwort für T0…T8. Eingebaut sind T0=0,00 °C, T1=−10,50 °C, T5=NoSensor und T6=ReadFailed. Der Golden-Request lautet:

    A5 5A 01 01 37 00 46 59

Beispieldatei außerhalb des Repositories: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX031-native-oracle-example.hex`. Im von C++ erzeugten Muster mit zwei Nutzframes erkennt die Python-Prüfung **2 gültige CRC-Frames**, davon 1 GET und 1 gültigen 9-Kanal-Snapshot, 0 CRC-Fehler und 0 unpassende Antwortsequenzen. Zusätzlich stehen absichtlich vorangestellte Rauschbytes im Testdump. Das sind **synthetische Prüfbytes**, keine Messung der echten Platine.

## Grenzen der Aussage

- **Keine Zeitstempel / Richtungsdaten:** Ein gespeicherter Hexdump belegt weder den RP2040-Requesttimeout (400 ms), den Byte-Gap-Reset (100 ms), noch die 15-s-Onlineerkennung oder die tatsächliche UART-Ausgaberichtung. Eine vorher beobachtete gleiche Sequenz bedeutet nicht, dass der RP2040 die Antwort angenommen hat.
- **Kein KNX-/ETS6-Nachweis:** Das Auswerten des internen ATtiny-Snapshots beweist nicht, dass OpenKNX KO25…35 Werte tatsächlich sendet oder dass ein KNX/TP-Gateway/ETS6-Testprojekt funktioniert.
- **Keine Motorfreigabe:** Unabhängig von CRC und Temperatur bleiben KNX002–006 inklusive TB6612-Standby, R29/INA219, U25-Identität und Versorgungs-/Rückspeisung sowie KNX018 offen.
- **Keine Firmwareänderung:** Die Auswertung läuft ausschließlich auf dem Host; RP2040, ATtiny, ETS-XML, V1.2-PCB, KNX027-Flash-CLI und KNX029-Kit wurden nicht geändert.

Weitere Schritte: [KNX029 Erstkontakt](KNX029_FIRST_CONTACT_RUNBOOK.md), [KNX030 Windows-USB-Inventur](KNX030_PASSIVE_FIRST_CONTACT.md), [KNX014 UART-Protokoll](KNX014_UART_BRIDGE.md) und [KNX022 Hardwareblocker](KNX022_STATIC_HW_READINESS.md).
