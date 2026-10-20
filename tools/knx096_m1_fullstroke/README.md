# KNX096 – Gegenüberliegende M1-Endlage, 30-s-Maximalfahrt F

**Aktueller echter Prüfling:** LLO Desktop COM7, RP2040 E464401787522D33, nur USB-C + M1; KNX096 installiert. Die M1-F-Gegenfahrt wurde einmal vollständig ausgeführt und bei **22.695 ms** durch einen INA219-LOAD_RISE-Kandidaten gestoppt.

## Benutzerauftrag und Ergebnis

Nach der R-Lastanstiegserkennung (KNX095) sollte das Ventil in der Gegenrichtung bis zur anderen Endlage laufen und der komplette Stromverlauf aufgezeichnet werden.

KNX096-Firmware erlaubt nur M1 Richtung F, maximal 30000 ms nach explizitem ARM MOTORS. INA219-Abtastung 8 ms, 4200 Rohtrace-Slots, Versorgung 3100–3450 mV, Laufstrommaximum 120 mA, Erkennung ab 450 ms bei sechs aufeinanderfolgenden Werten >=45 mA oder 0–5 mA (möglicher Endschalter), dann sofort latched Motor-FAULT und Treiberausgänge LOW. Keine automatische Wiederholung und kein Start beim Boot; keine KNX-TX-Telegramme.

PlatformIO Core 6.1.16 BUILD PASS; UF2 244224 Bytes, SHA256:
4ac733f5a8ad72c4ab3685042f1f390546d66b1b3bb306a0bf8e14db41ffa45c

Testprogramm: knx096_host.py, Generator generate_host.py.
Quellgenerator: generate_from_knx095.py.
Read-only Trace-Nachleser: recover_trace_readonly.py.
Tests: tools/test_knx096_fullstroke.py (8/8 PASS).

## Lauf und vollständige Auswertung

Der erste PC-Testskriptversuch wurde wegen eines falschen Host-Acknowledgement-Vergleichs sofort durch STOP beendet und getrennt protokolliert (0 INA-Samples). Nach Kontrolle der Motorpins und des INA219-Ruhestroms wurde der Host korrigiert und der gesondert dokumentierte, einmalige Test KNX096B gestartet. Keine zweite Firmwareübertragung.

- M1 F: 22,695 Sekunden bis zum LOAD_RISE-Kandidaten.
- Ende durch sechs aufeinanderfolgende gültige Stromwerte >=45 mA.
- Endstrom bei Abschaltung: Integer 56 mA (Rohwert 56,45 mA).
- Maximalwert nahe Ende: 59,65 mA.
- Maximaler gemessener Anlaufstrom: 105,55 mA bei t=7 ms.
- Median des Laufstroms: 20,15 mA, motorspannung 3264–3288 mV.
- Firmware danach FAULT/STOP, anschließend IDLE und alle Motorausgänge LOW, INA wieder nominal 0 mA.

Wichtig: Der erste USB-Rohdaten-Dump verlor 413 zusammenhängende Samples, der Firmwarepuffer war intakt. Mit rein passivem großen USB-Block-Read wurden **2837/2837 gültige Samples** von 7 bis22695 ms mit genau8 ms Abstand vollständig wiederhergestellt. Keine erneute Motorfahrt dafür nötig.

## Dateien

Ausführlicher Bericht: docs/KNX096_F_OPPOSITE_FULLSTROKE_20261020.md

LLO Desktop Runtime: C:\ASH\Workspace\Runtime\KNX096

- KNX096B_M1_F30000_20261020_102101.json/.csv – echter Lauf, erster USB-Dump mit Lücke.
- **KNX096_RECOVERED_TRACE_20261020_102511.json/.csv – vollständige Stromkurve mit 2837/2837 Werten.**
- KNX096_M1_F30000_20261020_101611.json – erster Sofort-STOP wegen Host-ACK-Fehler.
- KNX096_FLASH_20261020_101532.json – einmaliger verifizierter Flash.
- Einmalmarker gegen versteckte Wiederholungen.

## Status und Grenzen

Wir haben nun zwei plausible INA-Stromanstiegs-Kandidaten: R in KNX095 und F in KNX096. Der neue Zeitweg R->F beträgt etwa 22,7 s. Beides sind **noch keine unabhängig mechanisch bestätigten Endanschläge**, und es wurde keine ETS-/KNX-Position 0 oder100% gespeichert.

Der Motor ist aktuell IDLE. TB6612 STBY ist auf Platine V1.2 fest HIGH, daher ist der Schutz rein softwarebasiert. Kein autonomer weiterer Versuch, keine längere Fahrt ohne neuen Auftrag.
