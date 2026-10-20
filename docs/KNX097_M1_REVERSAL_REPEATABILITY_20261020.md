# KNX097 – Wiederholgenauigkeit von M1 (3 R/F-Zyklen)

**Stand:** 20.10.2026, LLO Desktop Agent 0.8.2, OpenKNXValveControl V1.2.

## Aufgabe und Hardware

Drei vollständige Umkehrzyklen vom vorher gemessenen F-Endlagenkandidaten in der Reihenfolge **R–F–R–F–R–F**. Testaufbau: RP2040 per USB-C auf COM7 (Seriennummer E464401787522D33), Motor M1, keine KNX-/UPDI-/Temperatursensor-Verbindungen. INA219-Adresse 0x40, CONFIG 0x399F, Shunt R29 200 mOhm, R33 und R34 physisch je 10 Ohm. Vor der Serie KNX096 F-LOAD_RISE bei 22,695 s, GPIO LOW, INA-Ruhestrom nominal 0 mA.

## Live-Ergebnisse

| Zyklus | Richtung | Fahrzeit | Abschaltstrom | Normalstrom-Median | Vollständige INA-Samples |
|---:|:---:|---:|---:|---:|---:|
| 1 | R | 24,423 s | 46 mA | 26,050 mA | 3053 |
| 1 | F | 22,767 s | 56 mA | 18,650 mA | 2846 |
| 2 | R | 24,479 s | 46 mA | 25,600 mA | 3060 |
| 2 | F | 22,815 s | 57 mA | 18,375 mA | 2852 |
| 3 | R | 24,263 s | 46 mA | 25,300 mA | 3033 |
| 3 | F | 22,671 s | 52 mA | 18,275 mA | 2834 |

**Gesamt:** 17.678 von 17.678 Rohstromwerten gültig und ohne Zeitlücken, mit 8-ms-Abstand. Alle sechs Fahrten endeten wegen eines anhaltenden LOAD_RISE-Stromanstiegs und wurden jeweils mit STOP, GPIO-LOW und plausiblen Leerlaufmessungen abgeschlossen.

## Statistik der Abschaltzeiten

- **R:** Mittelwert **24,3883 s**, Populationsstandardabweichung **0,0915 s**, Spannweite **0,216 s**, Variationskoeffizient **0,375 %**.
- **F:** Mittelwert **22,7510 s**, Populationsstandardabweichung **0,0599 s**, Spannweite **0,144 s**, Variationskoeffizient **0,263 %**.
- **R minus F:** Im Mittel **1,6373 s** längere Fahrt in Richtung R.
- Vorheriger einzelner KNX096-F-Test: 22,695 s. Der neue F-Mittelwert liegt nur 0,056 s darüber.

Die strombasierte Abschaltstelle ist damit über diese drei Zyklen **zeitlich sehr gut reproduzierbar**. Wegen der unterschiedlichen Richtungszeiten sollte die spätere Positionssteuerung getrennte Fahrzeitparameter für R und F erhalten.

## Firmware, Schutz und Kommunikation

KNX097 ist ein eigener Fork aus KNX096, erstellt mit PlatformIO Core 6.1.16; UF2-Größe 244736 Byte, SHA256 d54632979a63dd6895f898f8923b6e9c94b72b93c6f874b9469dfe8dd792a2eb. Die Firmware gestattet maximal sechs einzelne, bewusst via ARM freigegebene Schritte R–F–R–F–R–F; sie reversiert nicht autonom. Motorlauf jeweils maximal 30 s, INA219 alle 8 ms, Laufstromlimit 120 mA, Versorgung 3100–3450 mV, Ruhegrenze 25 mA; nach 450 ms führt sechsfacher Strom >=45 mA zu LOAD_RISE, sechsfach 0–5 mA zu CURRENT_CUT. Nur LOAD_RISE nach mindestens 12 s berechtigt zur nächsten Gegenfahrt. Jede Fahrt hat eine eigene Einmalsperre und CSV/JSON-Aufzeichnung. Host bricht bei fehlerhaftem Trace, unplausibler Stromversorgung oder größerer Fahrzeitabweichung ab. Offline-Tests 9/9 PASS.

Beim Wechsel COM7 -> RP2040 ROM trat eine Windows-Portkonfigurations-SerialException auf, obwohl das Board bereits im ROM-Modus COM6 war. Die exakte Flash-ID E464401787522D33 wurde geprüft und das gepinnte UF2 genau einmal mit picotool load/verify/start übertragen. Danach COM7, Firmware-ID und INA219 bestätigt; keine doppelte Programmierung.

**Einschränkung:** Nur elektrische LOAD_RISE-Kandidaten, keine mechanisch unabhängig vermessenen Endschalter oder absoluten 0-/100-%-Positionen. Die Schutzgrenzen sind softwarebasiert; TB6612 STBY liegt auf PCB V1.2 fest HIGH. Eine automatische ETS-Referenzposition wurde nicht gesetzt.

## Gesicherte Daten und Stand

Auf LLO Desktop unter C:\ASH\Workspace\Runtime\KNX097: je eine vollständige JSON-/CSV-Messung für KNX097_LEG_01_R bis KNX097_LEG_06_F, außerdem KNX097_REPEATABILITY_SUMMARY.json/.csv. Die Firmware meldet nach sechs erfolgreich abgeschlossenen Schritten legs_done=6, der Motor ist IDLE, GPIOs LOW und INA im Leerlauf nominal 0 mA. Ein weiteres Motorprogramm bedarf einer neuen bewusst geplanten Firmware/Testfreigabe. Kein Git-Push ohne Auftrag.
