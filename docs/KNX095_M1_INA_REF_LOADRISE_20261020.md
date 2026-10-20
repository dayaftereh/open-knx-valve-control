# KNX095 - M1 Referenzsuche mit INA219 Lastanstieg

Stand: 20.10.2026, LLO Desktop Agent 0.8.2.
Status: erster Endanschlag-Kandidat LOAD_RISE gefunden; Motor kontrolliert abgeschaltet. Referenz-Null noch NICHT gesetzt.

## Ausgangslage

Der Nutzer hat die mechanische Motorbewegung im vorherigen KNX094-Test bestaetigt und wollte nun eine kontrollierte Referenzfahrt Richtung mechanischem Endanschlag. KNX094 hatte 10 Sekunden R bei konstanten 23-35 mA ohne erkennbare Endlage durchgefuehrt.

OpenKNXValveControl V1.2, LLO Desktop COM7, USB-Serial E464401787522D33, VID:PID 2E8A:000A. Testplatine laut Nutzer nur mit RP2040 USB-C und Motor M1 verbunden; ohne KNX, UPDI, Temperatursensoren oder M2. R29 = 200 Milliohm 1W, Sense-Widerstaende R33/R34 beide auf 10 Ohm korrigiert. INA219 Leerlaufmessung plausibel, CONFIG 0x399F, Motorversorgung ca.3,29V.

Git-Ausgangslage: main CLEAN, HEAD 1e5f79b, drei Commits vor origin/main.

## Firmware KNX095

Neue, separat generierte KNX095-Testfirmware, Quelle tools/knx095_m1_reference, aus der vorherigen KNX094-Firmware abgeleitet ohne aeltere Dateien zu aendern.

Firmware- und USB-Kommandos:
- Nur M1 Richtung R und maximal genau 15000ms nach ausdruecklichem ARM (5s Gueltigkeit).
- Keine Bewegung beim Start/Flash, KNX TX permanent LOW.
- INA219 waehrend der Motorfahrt alle ca.8ms, TRACE-Puffer fuer 2200 Rohwerte.
- Versorgung 3100..3450mV, Leerlauf maximal25mA, Laufstrom maximal120mA; Ausfall USB, Stromsensor oder Versorgung => FAULT.
- Endstop-Suche erst ab t=450ms (Anlauf ignoriert): sechs unmittelbar aufeinanderfolgende gueltige INA-Werte mit >=45mA -> LOAD_RISE Kandidat. Alternativ sechs unmittelbar aufeinanderfolgende Werte 0..5mA -> CURRENT_CUT Kandidat (moeglicher interner Endschalter).
- Bei Kandidat sofort latched Motor-FAULT, Treibereingaenge LOW, zeitgenaue USB-Meldung. Host sendet STOP danach zusaetzlich.
- Kein weiteres Anlaufen, kein Backoff, kein Auf-Block-Halten. Einmal-Marker verhindern automatische Wiederholung.
- Diese Abschaltung ist Software, keine unabhaengige Hardware-STO. TB6612 STBY auf Board v1.2 fest HIGH.

PlatformIO Core6.1.16 KNX095 BUILD PASS. UF2 244224 Byte.
SHA256 11e6ee28a6620102426e2af96969861089a6d19fd47ecdf32535f0f9543130b0.
Syntaxpruefung Python PASS, sieben Offline-Tests PASS.
Vor Flash genaues RP2040 Board und INA/GPIO-Idle bestaetigt. Einmaliger ROM-Picotool-Flash (exakte ID) mit Verify und Neustart; KNX095-Signatur und INA/GPIO-Idle danach PASS.

## Live-Test: ein einziger M1-R-Impuls

Start: ARM MOTORS, danach PULSE M1 R 15000. Die Firmware beendete den Motor vorzeitig durch LOAD_RISE bei t=7735ms. Rohmeldung:

KNX095 ENDSTOP_CANDIDATE kind=LOAD_RISE t_ms=7735 current_ma=46 bus_mv=3280

Danach KNX085 MOTOR_ENDED state=FAULT, anschliessend redundanter STOP mit Quittierung. GPIO Motoren/KNX_TX LOW, Motorstate nach STOP IDLE, INA Leerlauf nominal0mA und Bus3288mV.

| Messgroesse | Messwert |
| --- | ---: |
| Erlaubtes Zeitmaximum | 15000ms |
| Tatsaechliche INA-Trace-Zeit | 7..7735ms |
| Gueltige INA-Samples | 967 / 967 |
| Maximaler Anlaufstrom bei 7ms | 109,85mA |
| Median 400..3000ms | 28,25mA |
| Median 3000..5000ms | 29,12mA |
| Median 5000..6000ms | 34,15mA |
| Median 6000..7000ms | 40,15mA |
| Median 7000..7500ms | 43,17mA |
| Median 7500..7700ms | 45,05mA |
| Letzter Messwert bei 7735ms | 46,75mA |
| Ganzzahliger INA Strom bei Abschaltung | 46mA |
| M_VCC waehrend Fahrt | 3260..3288mV |
| Firmware-Abschaltursache | LOAD_RISE, dann FAULT |
| Nach STOP | IDLE, alle Outputs LOW, 0mA nominal |

## Schlussfolgerung

Der Strom blieb nicht konstant wie im vorherigen 10-Sekunden-Test. Ab ca.5 Sekunden stieg er zunehmend bis ueber die konservative Schwelle45mA, die sechs Mal unmittelbar hintereinander ueberschritten wurde. Das ist ein plausibler MECHANISCHER LASTANSTIEG in Naehe des Endanschlags.

Es ist kein vollstaendiger Nachweis, dass exakt der konstruktive Endanschlag und nicht ein Reibungs-/Klemmereignis erreicht wurde. Deshalb wird NICHT automatisch eine Referenz-Position0 oder ETS-Status0 gesetzt. Nur ein Endanschlag-Kandidat wird protokolliert. Es fand kein zusaetzlicher Impuls und kein Backoff statt.

Fuer eine belastbare Referenzfahrt sind die Beobachtung des Nutzers, spaeter eine kontrollierte Entlastungsfahrt in Gegenrichtung sowie Wiederholbarkeit der Lastsignatur sinnvoll. Es ist kein weiterer Lauf ohne getrennten bewussten Testauftrag vorgesehen.

## Originaldaten, lokal auf LLO Desktop

C:\ASH\Workspace\Runtime\KNX095

- KNX095_FLASH_20261020_094725.json
- KNX095_M1_R15000_20261020_094805.json
- KNX095_M1_R15000_20261020_094805.csv
- KNX095_FLASH_STARTED.flag
- KNX095_M1_R15000_STARTED.flag

Firmwarequelle/Host:
tools/knx095_m1_reference/
tests: tools/test_knx095_reference.py

Git lokal committen, kein Git-Push ohne Freigabe.
