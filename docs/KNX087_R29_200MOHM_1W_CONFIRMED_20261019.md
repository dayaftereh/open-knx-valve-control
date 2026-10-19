# KNX087 – Bestätigung R29 und Einordnung des INA219-Leerlaufwerts

**Stand: 19.10.2026.** Nachtrag zur realen OpenKNXValveControl V1.2 Testplatine.

## Bestückung R29 – durch Nutzer bestätigt

Der Nutzer bestätigt für die tatsächlich eingesetzte Platine ausdrücklich:

- **R29 = 200 mΩ = 0,200 Ω.**
- **Belastbarkeit = 1 W.**

Diese Aussage ist die aktuelle **Bestückungsangabe aus erster Hand**.
Der früher dokumentierte widersprüchliche EasyEDA-PCB-MPN
`SCR1206F1M1` / `C3017245` ist damit als **Metadatenkonflikt der
Platinendaten** zu führen, nicht als Hinweis, dass zwangsläufig ein
falscher physischer Widerstand eingelötet wurde. Eine separate
Vierleitermessung ist nicht erfolgt und wird hier nicht behauptet.

## Firmware-Prüfung: korrekt auf 200 mΩ konfiguriert

Der unveränderte, bereits real geflashte KNX085-Quellcode
`tools/knx085_motor_diag/src/main.cpp` verwendet:

```cpp
next.currentMa=(static_cast<int32_t>(static_cast<int16_t>(shunt))*10)/200;
```

Der INA219 liefert die Shuntspannung mit **10 µV je Roh-Count**.
Aus `shunt × 10 µV / 200 mΩ` folgt Strom in mA; die Berechnung
entspricht **0,05 mA je Roh-Count**, intern als ganzzahliger mA-Wert.
Auch die Hostprogramme setzen genau 0,200 Ω ein.
Die Bestätigung R29 erfordert deshalb **keinen Firmware-Neubau
und keinen erneuten Flash**.

## Warum die Motorfreigabe weiterhin nicht erfolgt

Nach dem erfolgreichen KNX085-Flash über LLO Home wurden
24 INA219-Abfragen **ohne Motoransteuerung** aufgezeichnet:

| Wert | Ergebnis |
| --- | --- |
| R29-Bestückung laut Nutzer | 0,200 Ω / 1 W |
| KNX085 Motorzustand | IDLE, M1/M2 GPIO LOW |
| INA219 I²C / CONFIG | 0x40 / 0x399F, read_ok=1 |
| M_VCC laut Busregister | 3,144–3,152 V |
| Gemeldeter gemeinsamer Versorgungsstrom | 462–463 mA |
| Differenzspannung am Shunt daraus | ca. 92,4–92,6 mV |
| R29-Verlust bei 463 mA | ca. 0,043 W (weit unter 1 W) |
| Grob abgeleitete 3,3-V-Seite | ca. 3,241 V |

Die **1-W-Belastbarkeit von R29 ist bei diesem Strom nicht der
begrenzende Faktor**. Der Widerspruch ist, dass bei ausgeschalteten
Motortreibern weiterhin ein sehr hoher Wert über die **gemeinsame
M_VCC-Schiene** gemeldet wird.

Der Messwert ist **nicht als tatsächlicher M1-Motorlaufstrom
anzugeben**. Es kommen unerwartete Lasten auf M_VCC, eine
Bestückungs-/Verdrahtungsabweichung an der Messstrecke sowie ein
INA219-Anschluss- oder Messpfadfehler in Frage. Keine dieser
Erklärungen wurde bereits nachgewiesen.

Der bisherige KNX085-Stromschutz ist in
`tools/knx085_motor_diag/src/motor_gate.hpp`:
- Leerlauf-Freigabe bis 25 mA bei 3.100–3.450 mV.
- Während eines Impulses Abschaltung bei mehr als 120 mA.
- Zeitbegrenzung eines Einzelimpulses auf maximal 250 ms.

**463 mA im Motorstillstand sind somit kein Grund, den bekannten
R29-Wert aufzugeben oder die Strombegrenzung blind anzuheben.**
Der 150-ms-M1-Versuch ist an diesem plausibilitätsbezogenen Gate
gescheitert und hat M1 nicht bewegt.

## Nächster technischer Schritt

Zuerst den gemeinsamen M_VCC-Pfad bei ausgeschalteten Motoren
untersuchen: tatsächlicher Ruhestrom, mögliche zusätzliche Lasten,
INA219 VIN+/VIN−-Verdrahtung und Rail-Spannungen.
Der aktuelle Live-USB-Diagnosemodus von KNX086 erlaubt diese
Analyse **ohne erneuten RP2040-Flash und ohne KNX-/UPDI-Abstecken**.
Dann M1 nur mit plausiblen Messwerten kurz testen.

Vorherige Dokumente KNX033, KNX085 und KNX086 enthalten
historische Aussagen, der R29-Bestückungswert sei noch unbekannt.
**Diese Aussagen sind durch die Nutzerbestätigung hiermit ersetzt.**
Die Aufzeichnung der damals real gemessenen 462–463 mA bleibt gültig.

Prüfe weiterhin `docs/KNX086_R17_LIVE_FLASH_INA219_20261019.md`
für Flash- und Messprotokolle.
