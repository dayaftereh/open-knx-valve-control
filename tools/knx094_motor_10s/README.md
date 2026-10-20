# KNX094 – einzelner 10-Sekunden-Motortest M1 R

**Aktuelle Firmware am LLO-Desktop-Pruefstand:** KNX094.
Stand 20.10.2026; COM7, RP2040-Seriennummer E464401787522D33.
Nur USB-C am RP2040 und ein Motor M1 an der Platine.

## Ergebnisse

Einmalige Ansteuerung M1 R 10000ms mit Live-INA219-Strommeldungen.
100% Zeitlimit erreicht, danach Motor automatisch IDLE,
zusaetzlicher STOP quittiert, alle Motorpins und KNX TX LOW.

- 1250/1250 Stromsamples gueltig, t=7..9999ms.
- Aufgezeichneter Anlaufpeak 112,05mA (t=7ms).
- Laufstrom-Median gesamt 28,0mA, ab400ms 27,825mA.
- Ab400ms war der maximale Strom nur 34,5mA.
- Ende bei t=9999ms: 31,55mA.
- M_VCC waehrend Lauf 3,260..3,288V, nachher ca.3,292V.
- Kein Strom-/Blockier-FAULT, kein Stromanstieg zur
  vermuteten Hard-Endlage.
- Keine visuelle oder akustische Motorbewegung unabhaengig
  durch den Agenten bestaetigt. Nutzerfeedback dazu ausstehend.

## Firmware und Schutzkonzept

Separater Fork vom KNX093-R800-Versuch:
- src/main.cpp und src/motor_gate.hpp
- platformio.ini mit Environment knx094_m1_reverse_10000
- generate_from_knx093.py reproduziert Firmwarequellen
- knx094_host.py und generate_host.py
- Offline-Test: ../test_knx094_motor_10s.py (6/6 PASS)

Firmware erlaubt ausschliesslich M1 R 10000 nach ARM.
Zeitlimit 10s, Stromlimit 120mA, Spannungsfenster 3,10..3,45V,
Leerlaufgrenze25mA; INA219-Abtastrate ca.8ms.
Frueherkennung eines moeglichen mechanischen Anschlags
bei >=60mA in 6 aufeinanderfolgenden validen Messungen
nach t400ms. 1500 Rohtrace-Slots und 5Hz-USB-Liveausgabe.
Kein automatischer Motorstart nach Boot.

WARNUNG: TB6612 STBY ist auf V1.2 hart HIGH.
Alle Abschaltungen sind Software, keine separate
Hardware-Leistungsunterbrechung. Die Stromkurve
allein bestaetigt keinen mechanischen Endanschlag.
Ein Peak <7ms kann unbemerkt bleiben.

PlatformIO Core6.1.16 Build PASS, UF2 243712 Bytes,
SHA256 c59596c3e3ba27fdd30adc094219953d47a7c59185ce2f55e00b1d04a2d5e284.
Einmalig via RP2040 ROM picotool load -v -x uebertragen.

Versionsdetail: Obwohl die Rueckgabe KNX094 meldet,
fragt der aktuelle Host dafuer den alten Diagnosebefehl
KNX093 ab. Das wurde erst nach erfolgreichem
Firmwareflash entdeckt, am Board passiv verifiziert und
im Host korrigiert; **kein doppelter Flash**.

## Wichtige Dateipfade

Ausfuehrlicher Testbericht:
docs/KNX094_M1_R_10S_LIVE_20261020.md
Runtime-Logs (nur LLO Desktop):
C:\ASH\Workspace\Runtime\KNX094\
  KNX094_FLASH_20261020_092752.json
  KNX094_M1_R10000_20261020_093009.json
  KNX094_M1_R10000_20261020_093009.csv

Die Marker-Dateien KNX094_FLASH_STARTED.flag und
KNX094_M1_R10000_STARTED.flag verhindern weitere
unabsichtliche Tests; nicht loeschen, um ohne
neuen Auftrag zu wiederholen.

## Fortsetzung

User bitte fragen, ob sich M1/Mechanik in den
10 Sekunden sichtbar/hoerbar bewegte. Mangels
Stromanstieg noch keine Endstop-Position gelernt.
Keine weitere Hard-End-Fahrt ohne neuen Testplan,
keine automatische Kalibrierung.
