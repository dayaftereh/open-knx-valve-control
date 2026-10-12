# KNX015 – ETS-parametrierbare Temperaturtelegramme (RP2040)

**Stand: 12.10.2026.** **Software-Abnahme:** produktiver RP2040-Controller kompiliert mit OpenKNX-KO-Zuordnung; native Scheduler-/Publikationstests und KNX013/014-Regressionstests bestanden. **Keine ETS6-Importfreigabe, kein physischer KNX-Bus-/UART-Test, kein Firmwareflash und keine Motoransteuerung.**

## Datenfluss

1. ATtiny3216 liest die neun 1-Wire-Fühler T0..T8 nichtblockierend ([KNX013](KNX013_ATTINY_SAMPLER.md)).
2. RP2040 holt alle 3 Sekunden aktuelle Snapshots per versioniertem CRC16-UART-Protokoll ([KNX014](KNX014_UART_BRIDGE.md)); ein physikalisch nicht verfügbares Signal wird niemals als gemessene 0 °C ersetzt.
3. Der RP2040 überträgt per KNX DPT **9.001** nur aktuell gültige Temperaturen. Diagnoseobjekte zeigen separat den UART-Linkzustand und die neun Kanäle. Die KNX-Telegramme werden erst **nach KNX-Konfiguration** durch den ETS-Parameter P19 aktiviert.
4. **Einseitig sendend:** Die hier behandelten Sensorgruppenobjekte sind weder Stellwert noch Raumtemperatur-Sollwert, sondern ausschließlich lokale Heizverteiler-Messwerte. KNX-Telegramme führen in KNX015 zu keiner Motorbewegung.

## Objekte und Gültigkeit

| ETS KO | Name | DPT | Inhalt |
| --- | --- | --- | --- |
| 25 | T0 | 9.001, 2 Byte | Zentraler Vorlauf in °C |
| 26–33 | T1–T8 | 9.001, 2 Byte | Rücklauftemperaturen zu Heizkreisen M1–M8 |
| 34 (neu) | TemperatureBridgeOnline | 1.002, 1 Bit | 1 = letzter vollständiger CRC-/Sequenz-geprüfter ATtiny-Snapshot innerhalb 15 s empfangen; sonst 0 |
| 35 (neu) | TemperatureValidMask | 7.001, 2 Byte | 9-Bit-Maske: Bit 0=T0, ..., Bit 8=T8. Nur gültige Sensoren; bei verlorenem UART-Link 0 |

**Bestehende KO1–33 bleiben in Numerierung, Id, DPT, ObjectSize und sichtbarem ETS Text unverändert.** Bestehende teils ungültige C++-Identifiers im internen ComObject.Name wurden für die Generierung durch Unterstriche ersetzt (zum Beispiel Soll-Temperatur_1 zu Soll_Temperatur_1). Dies ist eine **Produktdatenänderung**, keine Garantie einer automatischen Migration von ETS-Projekten. Die KNX ApplicationVersion wurde daher von 1 auf **2** angehoben.

**Sperren:** Kein Temperaturtelegramm bei Offline-Transport, fehlender Probe, NoSample, Stale, Error oder unplausiblem Wert unter -55 °C/über +125 °C. Eine echte 0 °C oder negative Temperatur bleibt zulässig. Bei Wiederverbindung oder erneut gültigem Sensor wird sein Wert erneut gesendet. Ein altes KNX-Temperaturobjekt wird bei Sensorausfall nicht mit einem Fehlerwert überschrieben; die Diagnosemaske zeigt den Fehler. KNX-Gruppenobjekte können nach Sensorverlust deshalb noch ihren letzten gültigen **historischen** Wert enthalten: Verbraucher müssen den Status berücksichtigen.

## ETS-Parameter

Die bisherigen 19 Parameter bleiben in Inhalt und Speicherposition unverändert. Hinzugefügt:

| Parameter | ETS Label | Speicher | Werte | Default |
| --- | --- | --- | --- | --- |
| P19 (vorhanden) | Vor- und Rücklauf-Temperaturen Ausgeben | Offset 6, Bit 0 | Aus/Ein | Ein |
| P20 (neu) TemperatureSendIntervalSeconds | Temperaturen zyklisch senden (Sekunden) | Offset 7, 16 Bit | 10 bis 3600 s | **60 s** |
| P21 (neu) TemperatureChangeThresholdCenti | Senden ab Temperaturänderung (0,01 Grad; 0 = aus) | Offset 9, 16 Bit | 0 bis 1000 (0…10 °C) | **50 = 0,5 °C** |

Die ETS-Temperatursektion zeigt P20/P21 unter den allgemeinen Einstellungen und die KOs T0–T8, 34 und 35 unter der bestehenden Freigabe P19. Bei P19=0 findet **keine** KNX015-Temperatur- oder Statuspublikation statt. Die UART-Datenaufnahme läuft intern dennoch weiter. Der RP2040 liest die Werte aus dem mit OpenKNXproducer generierten Parameterheader via ParamTemperatureSendIntervalSeconds, ParamTemperatureChangeThresholdCenti und ParamPrePostTemperaturesOutput.

Die Begrenzung im Code verhindert bei fehlerhaften Parameterbytes zyklisches Senden unter 10 s oder über 3600 s. Eine Schwelle von 0 deaktiviert nur das Senden aufgrund von Temperaturänderungen, nicht den zyklischen Versand.

## Sendepolitik und Buslast

Der hardwareunabhängige [Scheduler](../lib/common/temperature_telemetry_policy.hpp) entscheidet, ob genau **ein** KNX-Gruppenobjekt pro RP2040-Loop gesendet werden soll:

- **Busabstand:** mindestens 250 ms zwischen allen erfolgreichen KO-Wertübergaben, einschließlich Diagnosen.
- **Je Temperaturkanal:** erste gültige Messung senden; danach periodisch alle eingestellten Sekunden oder bei Betrag der Differenz zur letzten gesendeten Temperatur größer/gleich Schwellwert. Änderungs-Auslösung frühestens **5 s** nach dem letzten Senden desselben Kanals.
- **Fairness:** zyklisch fortschreitende Kanalsuche, damit nicht immer T0 Vorrang bekommt.
- **Diagnose:** BridgeOnline und ValidMask jeweils beim ersten Lauf und bei Änderung; diese Signale haben Vorrang vor Temperaturdaten, unterliegen aber ebenfalls dem Busabstand.
- **Erfolgsdefinition:** Der Scheduler bestätigt die Ausgabe erst, wenn GroupObject.value() das Kodieren/Aktualisieren angenommen hat. Das ist **kein KNX-Bus-ACK oder ETS-Empfangsnachweis**. Bei abgelehnter Wertkodierung wird die noch ausstehende Ausgabe später erneut versucht.

Das KNX-Protokoll und der Hardwaretreiber laufen weiterhin über Serial1; der Temperatur-Poll über Serial2. Im KNX015-Code gibt es **keinerlei Zugriff auf TB6612FNG, INA219 oder Motorausgänge**.

## OpenKNXproducer, generierter Header und Produktversion

Quelle ist [assets/open-knx-valve-control.xml](../assets/open-knx-valve-control.xml); der Header [include/knxprod.hpp](../include/knxprod.hpp) wurde nach erfolgreich geprüftem isoliertem OpenKNXproducer 3.12.2-Lauf neu übernommen.

Das historische OpenKNXproducer-Template hatte zwei voneinander unabhängige Probleme:
1. Bindestriche/Leerzeichen in internen ComObject.Name erzeugten ungültige C++-Makros; **nur die C-Namen wurden normalisiert**, die sichtbaren ETS-Texte bleiben unverändert.
2. Producer 3.12.2 schreibt jeweils zwei gleichnamige KO-Makros, einmal Nummer und einmal KNX-Zugriff; dadurch kommt es zu Überschreiben und Selbstreferenz. [knxprod_header_fix.py](../assets/knxprod_header_fix.py) behält strikt die numerische Kennung, benennt den zweiten Makrozugriff zu KoNameObject um und verwirft mehrdeutige/inkonsistente Header. Der PlatformIO-[Producer-Pre-Script](../assets/open-knx-producer.py) schlägt jetzt bei Generator-/Normalisierungsfehlern fehl, statt still mit einem alten Header weiterzubauen.

[KNX015 Produktinvarianten-Audit](../tools/audit_knx015_product.py) vergleicht XML KOs und Parameter mit dem unveränderlichen KNX014-Baseline-Commit e2e54c6: **KO1–33 sowie P1–19 müssen strukturell und numerisch erhalten bleiben**. Zusätzlich werden P20/P21, KO34/35, DPT und Header geprüft.

**Zusätzlicher Offline-Pakettest:** Der isoliert erzeugte KNX-Produktcontainer mit 6 ZIP-Einträgen bestand die ZIP-CRC-Prüfung; der enthaltene ApplicationProgram-XML ist Version 2 und enthält 35 Kommunikationsobjekte sowie 21 ETS-Parameter. Das ist mit dem optionalen --knxprod-Argument von [audit_knx015_product.py](../tools/audit_knx015_product.py) erneut prüfbar.

**Verbleibende Einschränkungen:** OpenKNXproducer erzeugt einen knxprod-Container im isolierten Testverzeichnis, aber ohne verfügbare lokale XSD-Prüfdatei und mit einer Warnung zum alten Kanalnummern-Platzhalter. Ein Generator-Exitcode 0 oder eine compilierte Firmware beweist **noch keinen ETS6-Import**. KNX016 muss die Version 2 in einem isolierten ETS6-Testprojekt importieren und die GA-/DPT-Sicht prüfen. Das ursprüngliche [ETS-Preschema-Audit](ETS_PRODUCT_AUDIT.md) bleibt als Referenz erhalten.

## Reproduzierbare Abnahme auf dem LLO Desktop Agent

Im Repo Root:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_telemetry.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_uart.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_temperature_sampler.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx015_product.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_temperature_bridge.py --scope all --strict
    C:\ASH\Tools\python-3.13.15\python.exe tools\build_controller_isolated.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py
    git diff --check

Die beiden KNX015-Native-Suites testen [Policy](../tests/native/test_temperature_telemetry.cpp) (Fehler, 0 °C, negative Werte, Kanäle, Sendeschwellen, Deadtime, Recovery, Zeitüberlauf) und die **tatsächliche Publisher-Klasse** gegen [Mock-KNX-Objekte](../tests/native/test_temperature_publisher_integration.cpp) mit realer, aber simuliert gespeister TemperatureBridge (DPT9/1/7, Parameterfreigabe, fehlender Sensor, CRC-UART-Offline-Fallback).

**Letzte isolierte Controller-Buildprüfung:** PASS; RAM **52.240/262.144 B** (19,9 %), Firmware-Flash **186.268/1.048.576 B** (17,8 %), UF2 erstellt. Die originale kanonische Datei war während der Isolation hash-identisch; die anschließend bewusst synchronisierte, normierte Headerfassung stammt aus dem geprüften isolierten Generator. Kein Flash und kein Live-KNX-Telegramm.

## Nächste Gates

**KNX016:** Versioniertes ETS6-Testprodukt importieren, KO25–35 und P19–21 in ETS prüfen, Kontrolltelegramme nur in einem ausdrücklich freigegebenen Testaufbau. **Noch nicht gestartet.** Hardware-As-built/Spannungsversorgung und Motor-Referenzfahrten folgen in separaten Slices nach KNX002–006. KNX015 beinhaltet keinerlei physische Motorfreigabe.
