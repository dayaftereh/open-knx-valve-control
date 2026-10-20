# KNX096 – Vollständige M1-F-Gegenfahrt zum anderen Endlagen-Kandidaten

**Stand:** 20.10.2026, LLO Desktop Agent 0.8.2.
**Ergebnis:** Endlagen-Kandidat LOAD_RISE bei **22,695 s in Richtung F** erkannt. Motor automatisch abgeschaltet; alle **2.837 von 2.837 INA219-Rohwerten** über den gesamten Fahrzeitraum wiederhergestellt.

## Testaufbau und Ziel

Der Nutzer bestätigte die tatsächliche Bewegung von M1 und wünschte nach der KNX095-R-Suche (LOAD_RISE nach 7,735 s im letzten R-Teilstück) eine vollständige Fahrt in die gegenüberliegende Richtung F, bei unbekannter Fahrtdauer. Board V1.2 über USB-C auf COM7, USB-Seriennummer E464401787522D33, nur ein Motor M1. Kein KNX-Bus, UPDI oder Temperaturfühler. R29 200 mOhm / 1 W, R33 und R34 physisch je 10 Ohm; INA219-Adresse 0x40, CONFIG 0x399F. Vor der Arbeit Git main HEAD 6cfdae7, CLEAN, vier lokale Commits vor origin/main. Live-Preflight KNX095-R-Kandidat, Motor IDLE, GPIO LOW, normaler INA-Ruhestrom ca. 0 mA, Motorbus 3,288–3,292 V.

## Firmware KNX096 und Schutzbedingungen

Eigener Fork aus KNX095, ursprüngliche Firmwaredateien unverändert:
- tools/knx096_m1_fullstroke/src/main.cpp, src/motor_gate.hpp und platformio.ini
- Generierungsprogramme generate_from_knx095.py und generate_host.py
- USB-Host knx096_host.py und passiver Ausleser recover_trace_readonly.py
- Offline-Kontraktprüfung tools/test_knx096_fullstroke.py

Es ist ausschließlich der Befehl PULSE M1 F 30000 nach ARM MOTORS zugelassen. Richtung R, M2 und andere Dauern werden abgelehnt. Kein selbstständiges Anlaufen beim Boot und kein KNX-TX. MCU-seitiges Zeitlimit **30 Sekunden**. INA219 misst etwa alle 8 ms, RAM-Tracespeicher 4200 Slots. Leerlauf-Gate 25 mA, Laufstrom-Grenze 120 mA, Motorspannungsfenster 3100–3450 mV, USB/INA-Fehler -> latched FAULT. Die Endlagensuche ignoriert die ersten 450 ms; anschließend sechs aufeinanderfolgende gültige Messungen >=45 mA -> LOAD_RISE, alternativ sechs gültige Proben zwischen 0 und 5 mA -> CURRENT_CUT. Bei Kandidat schaltet die Firmware sofort alle Motorausgänge LOW. Diese Softwareüberwachung ist keine unabhängige Hardware-STO; sehr kurze Peaks zwischen den Messungen können unerkannt bleiben.

PlatformIO Core 6.1.16: Build PASS, RAM 35,5%, Flash 5,3%. UF2 244224 Bytes, SHA256 4ac733f5a8ad72c4ab3685042f1f390546d66b1b3bb306a0bf8e14db41ffa45c. Python Syntax und 8/8 Offline-Tests PASS. Gepinntes Image über verifizierten RP2040-ROM/Picotool einmalig geflasht; Rückkehr COM7, Versionsfingerprint und INA/GPIO-Idle bestätigt. Flashbeleg auf Desktop: C:\ASH\Workspace\Runtime\KNX096\KNX096_FLASH_20261020_101532.json.

## Dokumentierter sehr kurzer erster Versuch

Bei der ersten Hostausführung bestätigte die Firmware bereits korrekt PULSE_STARTED M1 F duration_ms=30000, aber der PC-Host verglich irrtümlich mit der alten Richtung R und sendete sofort STOP. Kein einziges 8-ms-Rohsample wurde dabei aufgezeichnet (TRACE_BEGIN count=0). Der Motor war danach IDLE, GPIO LOW; ein kurzfristiger negativer INA-Wert unmittelbar nach dem STOP verschwand wieder, zehn ruhige Folgewerte 0 mA / 3288–3292 mV wurden bestätigt.

Dieser Abbruch wurde **nicht als vollständige Fahrt** gezählt. Originalreport und erster Sperrmarker wurden beibehalten: C:\ASH\Workspace\Runtime\KNX096\KNX096_M1_F30000_20261020_101611.json. Der Host-ACK-Vergleich wurde korrigiert, die Kontraktprüfung erneut ausgeführt und ein separater, überprüfter Einmalversuch KNX096B mit eigener Sperrdatei erstellt. Kein weiterer Firmwareflash.

## Erfolgreiche einzige vollständige F-Suchfahrt (KNX096B)

Nach erneuter passiver Version-, COM7-, INA- und GPIO-Prüfung erfolgten ARM MOTORS und PULSE M1 F 30000. Nach **22,695 s** erkannte die Firmware einen anhaltenden Stromanstieg und beendete die Ansteuerung mit absichtlichem FAULT. Originalmeldung:

KNX096 ENDSTOP_CANDIDATE kind=LOAD_RISE t_ms=22695 current_ma=56 bus_mv=3276

Redundanter STOP wurde bestätigt. Danach Motor IDLE, sämtliche Motor- und KNX_TX-Pins LOW, Ruhestrom nominal 0 mA, Motorbus 3292 mV. Keine weitere Motorfahrt. Im Host sind 113 Live-Strommeldungen enthalten.

### Vollständige INA219-Stromspur

Die Firmware hatte laut TRACE_BEGIN alle **2837 Werte** im RAM. Der erste zeilenweise USB-Dump übertrug davon nur **2424** (eine Lücke von 11,775 bis 15,071 Sekunden, ca. 3,3 s), obwohl TRACE_END vorhanden war. Das ist ein Übertragungs- und KEIN Aufzeichnungsausfall.

Der INA219-RAM-Puffer wurde deshalb nur lesend und ohne erneute Motorbewegung mit blockweisen 8192-Byte-USB-Reads erneut ausgelesen. **2837/2837 eindeutige gültige Rohsamples** bei exakt 8 ms Abstand von t=7 bis t=22695 ms konnten vollständig und widerspruchsfrei wiederhergestellt werden. Der erste passive Wiederholungsvorgang lieferte alle Werte (0 fehlende Samples).

| Intervall | INA219-Motorstrom |
| --- | ---: |
| Erfasster Anlaufpeak bei 7 ms | 105,55 mA |
| 0,45–2 s, Median | 25,38 mA |
| 2–5 s, Median | 21,30 mA |
| 5–10 s, Median | 20,40 mA |
| 10–15 s, Median | 19,20 mA |
| 15–20 s, Median | 18,35 mA |
| 20–22 s, Median | 17,12 mA |
| 22–22,4 s, Median | 13,32 mA |
| 22,4–22,6 s, Median | 20,45 mA |
| 22,6–22,7 s, Median | 47,27 mA |
| Kurz vor Abschaltung, höchster Endwert | 59,65 mA |
| Letzter Rohwert bei 22,695 s | 56,45 mA |
| Gesamtmedian | 20,15 mA |
| Motorspannung während Fahrt | 3264–3288 mV |

Die letzten sechs Samples t=22655, 22663, 22671, 22679, 22687 und 22695 ms lagen jeweils über 45 mA; das Auslösen des LOAD_RISE-Schutzes war korrekt. Die Laufrichtung F zeigt einen überwiegend niedrigeren Strom als R und einen recht steilen Anstieg am Ende. Die R-Endlage hatte zuvor einen langsam steigenden Laststrom. Beide Merkmale sind plausible **Endlagen-Kandidaten**, noch keine unabhängig vermessenen konstruktiven Endanschläge.

### Originaldaten auf LLO Desktop

Verzeichnis: C:\ASH\Workspace\Runtime\KNX096

- KNX096_FLASH_20261020_101532.json – Flash- und Board-Prüfung.
- KNX096_M1_F30000_20261020_101611.json – erster, sofort abgebrochener Hostversuch, keine Rohsamples.
- KNX096B_M1_F30000_20261020_102101.json und .csv – tatsächlicher F-Lauf; erster USB-Dump unvollständig.
- **KNX096_RECOVERED_TRACE_20261020_102511.json und .csv – die komplette, verifizierte Fahrt mit 2837/2837 Samples.**
- Eindeutige Flash-/Start-Flags gegen automatische Wiederholung.

## Interpretation und nächster Schritt

R-Kandidat (KNX095) zuletzt bei t=7,735 s innerhalb des letzten R-Teilstücks; F-Kandidat (KNX096) nach **22,695 s Fahrt ab dem R-Kandidaten**. Die rund 22,7 s sind somit ein erster strombasierter vollständiger Fahrweg, aber noch **kein kalibrierter Zeit-/Positionsweg**. Keine KNX- oder ETS-Position 0/100 % wurde gesetzt. Zur belastbaren Referenzierung sind eine mechanische Gegenprüfung beider Endpunkte, kontrollierte Entlastung und Wiederholbarkeit sowie richtungsabhängige Last-/Stromschwellen sinnvoll. Kein weiterer Motorlauf ohne neuen Auftrag; kein Git Push ohne separate Freigabe.
