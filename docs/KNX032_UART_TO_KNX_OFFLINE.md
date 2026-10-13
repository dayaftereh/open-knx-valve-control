# KNX032 – UART-Daten bis zur KNX-Temperaturpublikation (Offline-End-to-End)

**Stand 13.10.2026 – rein softwareseitig auf LLO Home geprüft.** Die OpenKNXValveControl V1.2 ist physisch noch nicht qualifiziert; **keine USB-/UPDI-Programmierung, kein KNX-/ETS6-Bus, keine Motorfreigabe**.

## Zweck

Nach KNX013–015 und KNX031 wird nicht nur das 67-Byte-ATtiny-UART-Format geprüft, sondern ein **vollständiger nativer Testpfad** durch die tatsächlichen unveränderten Firmware-C++-Module `TemperatureBridge` und `TemperaturePublisher` bis zu simulierten KNX-Objekten KO25–35:

```text
KNX031 C++ TemperatureProtocol Golden-Frame (GET + SNAPSHOT)
    ↓ Datei/Bytes, CRC und 9 Sensorflags unabhängig geprüft
KNX032 Source-Level-Hosttest mit SerialUART-Mock
    ↓ originale Snapshot-Payload auf frische Test-Request-Sequenz eingerahmt
RP2040 TemperatureBridge / ClientCore (Produktionsquellen)
    ↓ age/online/channelValid & Poll/Timeout
TemperaturePublisher / KNX015 Scheduler (Produktionsquellen)
    ↓ DPT/Konvertierung/250-ms-Gap/ETS P19 ON-OFF
KNXMock GroupObject.value(KO25..35) – keine KNX-Busübertragung
```

**Wichtiger Unterschied:** Die alte externe GET-Sequenz 0x37 und die neue, rein simulierte Request-Sequenz 1 sind unterschiedlich. KNX032 übernimmt die tatsächlich CRC-geprüfte Payload, erzeugt aber über den originalen C++-Codec einen **neuen gültigen Antwortrahmen mit Sequenz 1**, damit die echte ClientCore-Implementierung den Testvorgang als passende Antwort akzeptieren kann. Das ist **keine bitidentische Wiederholung einer realen UART-Aufnahme** und kein physischer Empfangsnachweis. Ein aufgezeichneter Rohdatenstrom ohne Zeitstempel beweist keinen echten Reply-Timeout, keine Byte-Lücken oder Busverfügbarkeit.

## Umgesetzte Prüfungen

| Bereich | Was der native Test tatsächlich nachweist |
| --- | --- |
| UART-Framing | Eine gespeicherte korrekte KNX014-GET+SNAPSHOT-Paarung wird von originalem C++-Parser und Python-CRC/Flags geprüft |
| Sensorwerte | T0 = 0,00 °C (echte Null zulässig), T1 = −10,50 °C, T2–T4/T7–T8 gültig; T5 NoSensor und T6 ReadFailed bleiben ohne Temperaturausgabe |
| KNX-Telemetrie | Für gültige T0–T8 werden **KO25–33 / DPT9.001** als simulierte KNX-Objektkonvertierungen geprüft |
| Diagnose | KO34 BridgeOnline DPT1.002: offline → online → offline; KO35 ValidMask DPT7.001: 0x019F (= 415) → 0 |
| Fehlerbehandlung | CRC-Manipulation, falsche Request/Response-Sequenz und fachlich ungültiges Valid-Flag bei korrekter CRC werden verweigert |
| P19/Freigabe | Keine KNX-Objektkonvertierung vor simuliertem ETS-Commissioning oder bei P19 AUS |
| Buslast/Retry | Mindestens 250 ms Abstand zwischen angenommenen **KNXMock-Konvertierungen**; abgewiesene Konvertierungen bleiben offen und werden erneut versucht |
| Offline-Verhalten | Abgelaufener 15-s-UART-Onlinezustand stoppt neue Temperaturupdates, setzt Diagnosemasken zurück; alte historische KO-Werte werden nicht aktiv mit 0 ersetzt |
| Motoren | Keine Motor-, Homing-, INA219-, GPIO-, Knx-Produktionsbus- oder Freigabefunktion wird verwendet |

Die Zahlen stammen aus dem **synthetischen Golden-Test**, nicht aus gemessenen Temperaturen des echten Heizungsverteilers. Der Simulationswert 0x019F meldet 7/9 nutzbare Sensoren, während T5 und T6 absichtlich auf Fehler stehen.

## Ausführung auf LLO Home

```powershell
Set-Location 'C:\_myspace\workspace\open-knx-valve-control'
$py = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'

# Rein informativ, führt noch keinen Compiler oder Serial-Port aus
& $py tools/test_knx032_uart_to_knx.py plan

# Native C++-Referenz & Host-Simulator inkl. Negativvektoren bauen und ausführen
& $py tools/test_knx032_uart_to_knx.py test

# Alternativ explizite, zuvor sicher gespeicherte Hexdump-Datei verwenden;
# Testprogramm öffnet kein Gerät und greift weiterhin nur auf KNXMock zu:
& $py tools/test_knx032_uart_to_knx.py test --trace 'C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX031-native-oracle-example.hex' --format hex

# Vertrags-/Fail-Closed-Tests
& $py tools/test_knx032_replay_contract.py
& $py tools/audit_knx032_replay_scope.py
```

Wenn keine Datei angegeben wird, erzeugt das Testwerkzeug die Golden-GET+SNAPSHOT-Bytes durch Kompilieren und Starten des **bestehenden** [KNX031-C++-Oracles](../tests/native/knx031_uart_vector_oracle.cpp) neu und führt den Test ausschließlich mit temporären Dateien in einem Host-Verzeichnis aus. Eine explizite Datei muss vom lokalen [KNX031-Decoder](KNX031_UART_TRACE_OFFLINE.md) akzeptiert werden und genau ein GET+SNAPSHOT-Paar enthalten. Ein abweichendes Format, ein verlorenes Paket oder ein echter defekter Trace wird **nicht passend gemacht**.

Die native Suite benötigt den bereits installierten lokalen C++-Compiler (WinLibs g++ auf Home); **weder PlatformIO-Upload noch ein angeschlossenes Board sind erforderlich**. Der optional übergebene `CXX`-Pfad muss existieren; andernfalls wird der Test abgebrochen statt still mit einem Gerätetool zu arbeiten.

## Quellcode und Regressionssicherheit

- **Neue Dateien:** [C++-Integration](../tests/native/test_knx032_uart_to_knx.cpp), [Test-Runner](../tools/test_knx032_uart_to_knx.py), [Vertrags-Regression](../tools/test_knx032_replay_contract.py), [Scope-Prüfung](../tools/audit_knx032_replay_scope.py).
- **Echte unveränderte Quellen:** [temperature_bridge.cpp](../src/controller/temperature_bridge.cpp), [temperature_publisher.cpp](../src/controller/temperature_publisher.cpp), [temperature_protocol.hpp](../lib/common/temperature_protocol.hpp), [temperature_telemetry_policy.hpp](../lib/common/temperature_telemetry_policy.hpp).
- **Kein Eingriff** in ATtiny/RP2040-Firmware, KNX-ETS-XML/AppVersion2, Schaltplan/PCB, KNX027/029-Flash-Vorbereitungen, KNX030-Windows-Geräteinventur, KNX031-Rohdaten-Decoder oder USB-Verbindungen.

## Noch offen bis zur bestückten Platine

KNX002/003 müssen erst den tatsächlichen U25-Typ (ATtiny3216 oder abweichendes PCB-Teil), 3,3-V-/5-V-UPDI-Pegel und CN1.1, U6-VIN mit Diodenabfall, USB-/KNX-Rückspeisung, reale Flashbestückung und die sichere Versorgung nachweisen. KNX004–006 müssen eine echte unabhängige sichere Abschaltmöglichkeit der acht TB6612-Motorausgänge nachweisen, bevor ein Motor bewegt werden darf. Für KNX018/009/016 sind ein sicherer Testbus sowie realer ETS-Import/Telegrammempfang weiterhin getrennte Gates.

**Ein PASS der KNX032-Tests bedeutet ausschließlich, dass die Host-Softwarekette die Testdaten akzeptiert oder sicher ablehnt. Es ist keine reale KNX- oder Hardwarefreigabe.**
