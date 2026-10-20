# KNX098 – M1-Motortest: Abnahme und eingefrorene Bench-Kalibrierung

**Datum:** 20. Oktober 2026
**Projekt:** OpenKNXValveControl, Platine V1.2
**Prüfumgebung:** LLO Desktop Agent 0.8.2, RP2040 über COM7, ausschließlich USB-C und Motor M1
**Abnahmestatus:** **BENCH ACCEPTED – Stromerkennung und Wiederholgenauigkeit eines vollständigen Motorhubs**
**Beweisbasis:** KNX095, KNX096 und KNX097; finale Kennzahlen aus drei vollständigen KNX097-R/F-Zyklen.

## 1. Abnahmeentscheidung

Der Nutzer betrachtet den Motortest nach sechs erfolgreich erkannten Endlagenkandidaten als abgeschlossen. Die zusätzliche **KNX098-Rohdaten-Replay-Prüfung** bestätigt diese Entscheidung für den M1-Büroteststand: **17.678/17.678 gültige INA219-Abtastungen**, durchgehend mit exakt 8 ms Intervall; sechs korrekt bestätigte LOAD_RISE-Abschaltpunkte; alle sechs Fahrten mit STOP-Bestätigung und anschließendem IDLE/GPIO-LOW.

Es wurde **keine weitere Motorbewegung** benötigt, da der Offline-Nachtest gerade die relevante offene Frage – Auslösung durch eine dauerhafte Stromerhöhung statt kurze Störspitzen – auf den sechs vorhandenen vollständigen Kurven beantwortet.

Diese Abnahme bezieht sich auf die **Reproduzierbarkeit der stromüberwachten Vollhub-Endlagenkandidaten**. Eine unabhängig vermessene mechanische Endlage, der tatsächlich gefahrene Hub in mm und wiederholgenau angefahrene beliebige Zwischenpositionen sind damit **nicht nachgewiesen**.

## 2. Eingefrorene Kalibrierwerte

| Parameter | Richtung R | Richtung F |
|---|---:|---:|
| Zyklus 1 | 24,423 s | 22,767 s |
| Zyklus 2 | 24,479 s | 22,815 s |
| Zyklus 3 | 24,263 s | 22,671 s |
| **Mittelwert (Nominal-Vollhub)** | **24,3883 s** | **22,7510 s** |
| Populations-Standardabweichung | 91,525 ms | 59,867 ms |
| Spannweite | 216 ms | 144 ms |
| Variationskoeffizient | 0,3753 % | 0,2631 % |

Die um rund **1,6373 s** längere R-Fahrzeit muss bei jeder späteren zeitbasierten Stellwertberechnung **richtungsabhängig** berücksichtigt werden. Beide Nominalwerte sind für den konkreten USB-Prüfstand und dessen Last-/Versorgungssituation gültig; sie sind **keine Garantie bei anderer Versorgung oder Ventillast**.

Maschinenlesbares, einmalig eingefrorenes Profil:
`config/knx098_m1_bench_calibration.json`.

## 3. INA219- und Motor-Schutzkontrakt aus der Prüfung

| Einstellung | Eingefrorener Bench-Parameter |
|---|---:|
| Bestückter R29 | 200 mΩ / 1 W |
| Sense-Widerstände R33/R34 | je 10 Ω |
| INA219-Konfiguration | 0x399F |
| Motorstrom-Abtastung | 8 ms |
| Einschwingzeit (Endlagenfilter ausgesetzt) | 450 ms |
| `LOAD_RISE` | mindestens 45 mA über **6 aufeinanderfolgende** gültige Werte |
| Möglicher interner Endschalter `CURRENT_CUT` | 0–5 mA über 6 gültige Werte |
| Laufstrom-Abbruchgrenze | 120 mA |
| Erlaubte Motorspannung | 3.100–3.450 mV |
| Leerlaufstrom-Grenze | 25 mA |
| Minimale plausible Vollhubfahrt **für diese Referenzsuche** | 12.000 ms |
| Maximale Dauer **für diese Referenzsuche** | 30.000 ms |

**Zusätzlicher Rohdaten-Nachtest (KNX098):** Bei allen sechs Messreihen findet der exakt nachgebildete Sechsfach-45-mA-Filter seinen **ersten** bestätigten Abschaltpunkt am tatsächlichen firmwareseitig gespeicherten Endzeitstempel. In der R-Richtung gab es schon früher einzelne Messwerte oberhalb von 45 mA (13, 27 und 19 Rohwerte mindestens 500 ms vor Fahrtende); diese bildeten **keine** Folge von sechs und lösten deshalb korrekt keinen vorzeitigen Stopp aus. Auf der F-Seite gab es vor dem Endbereich keine solchen Einzelwerte. Die `CURRENT_CUT`-Bedingung hatte in allen sechs Fahrten keinen Vorrang.

Die sechs Rohdateien und die sechs zugehörigen USB-Ergebnisprotokolle wurden beim Einfrieren jeweils mit SHA256-Fingerprints versehen. Jede Manipulation/Änderung an den Originalkurven oder ihrer Reihenfolge führt bei der erneuten KNX098-Prüfung zu einer fehlgeschlagenen Übereinstimmung. Der Test ist **rein lesend** und enthält keinerlei Motor- oder USB-Befehle.

## 4. Akzeptanzkriterien und Teststatus

| Prüfkriterium | Ergebnis |
|---|---|
| 3 vollständige Zyklen in Folge R–F–R–F–R–F | PASS |
| 6/6 Stromabschaltungen durch dauerhaftes `LOAD_RISE` | PASS |
| 17.678/17.678 gültige, lückenlose 8-ms-Samples | PASS |
| Kein früherer sechsfacher Stromtrigger in einer Rohkurve | PASS |
| Zeitabweichungs-Spannweite je Richtung max. 500 ms | PASS – 216 / 144 ms |
| Variationskoeffizient je Richtung unter 1 % | PASS – 0,3753 / 0,2631 % |
| Plausibler Ruhestrom nach dem Stopp, alle GPIO LOW | PASS |
| SHA256-gebundenes Bench-Profil und wiederholbare Datenverifikation | PASS |
| KNX098 Negativtests zu Datenlücke, Falschtrigger und fehlerhafter Abschaltung | PASS |
| Mechanische Bestätigung von 0 %/100 % und Stellwert-Zwischenpositionen | **NICHT Bestandteil der Bench-Abnahme** |
| Betrieb mit KNX-Bus, Temperaturregelung, ETS-Parametern | **NOCH NICHT in KNX098 getestet** |

## 5. Reproduzierbare Validierung

Auf dem LLO Desktop Agent im Repository-Root:

```powershell
python tools/knx098_motor_acceptance.py
python tools/test_knx098_motor_acceptance.py
```

Beim ersten einmaligen Einfrieren wurde `--freeze` aufgerufen; danach verweigert das Programm absichtlich ein erneutes Überschreiben des akzeptierten Profils. Normale Aufrufe prüfen die sechs Archivdaten gegen den eingefrorenen JSON-Inhalt. **Keine Motorbewegung, kein Flash, keine Änderungen an produktiver KNX-Firmware.**

Die zwölf KNX098-Tests prüfen u. a. zusammenhängende Strom-Trigger, die 450-ms-Einschwingzeit, Vor- und Nachbedingungen, Hashes/Quellwerte, Timingstatistik und gezielt manipulierte Messreihen (fehlende Daten, beschädigte Zeitstempel, verfrühte Stromschwelle, falscher Abschaltgrund).

Belegpfad auf LLO Desktop:
`C:\ASH\Workspace\Runtime\KNX097`
mit `KNX097_LEG_01_R` bis `KNX097_LEG_06_F`, jeweils CSV und JSON. Original-Rohdaten verbleiben auf dem Bürorechner; im Git liegen nur Profil, Fingerprints und prüfender Programmcode.

## 6. Abgrenzung und Übergabe in die nächste Phase

**Eingefroren:** Hardwarekonfiguration des geprüften Aufbaus, Richtungszeiten, Stromerkennung und Grenzwerte der experimentellen Vollhub-Referenzsuche. Motor-Bench-Gate **GREEN/ABGESCHLOSSEN**.

**Nicht automatisch festgelegt:** Richtung F = Öffnen oder Schließen, physische Endlagenzuordnung zu 0/100 %, absoluter Ventilweg, lineare 50-%-Stellposition, KNX-Gruppenadressen oder ETS-Parameter.

Die folgenden Implementierungen müssen deshalb anfangs beide Richtungen intern als `endpoint_R` und `endpoint_F` behandeln, unter laufender Strom-/Spannungsüberwachung und unabhängigem Maximalzeitlimit arbeiten. Für spätere Sollpositionsregelung ist eine **separate Validierung von Zwischenstellungen sowie Abweichung unter realer mechanischer Last** nötig. Die Produktions-Firmware darf diesen Bench-Datensatz nicht kommentarlos als geprüfte reale Positionsrückmeldung deklarieren.

**Sicherheitsgrenze:** TB6612 STBY ist auf V1.2 hart HIGH. Die Stromabschaltung ist firmwarebasiert (etwa 8 ms Abtastung), keine unabhängige Hardware-STO. Der derzeit installierte KNX097-Bench-Build hat `legs_done=6` und akzeptiert keine weiteren Testfahrten. Keine neue Motorfahrt und kein Git-Push während der KNX098-Abnahme.
