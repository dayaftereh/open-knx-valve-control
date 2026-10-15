# KNX043: USB-5-V-Einsteckversuch – gemeinsame PicoScope-Messung

**Datum:** 15.10.2026. **PicoScope:** 3205D MSO GX118/0047, Kanal A: KNX_TX JMP3 Pad 2 (Tastkopf **10:1**, SDK-Eingang ±0,5 V), Kanal B: benutzerseitig ausgewählter USB-5-V-Punkt (Tastkopf **1:1**, SDK-Eingang ±10 V). Beide Kanäle wurden im selben Zeitraster mit 7,984 µs/Sample aufgenommen, 500.000 Samples je Kanal, insgesamt 3,992 s. Die tatsächliche Netz- und Massezuordnung der Tastköpfe ist nicht vom Agenten optisch verifiziert.

## Beobachtungen

| Ereignis | Zeit relativ zum Kanal-B-Trigger |
| --- | ---: |
| Der Messpuffer beginnt mit B ca. 4,26 V | −798,4 ms; **kein neuer Power-On-Impuls** |
| B fällt unter 2 V | **−8,383 ms** |
| B steigt bei tatsächlichem 2,5-V-Trigger wieder über 3 V | **0 ms** |
| B fällt erneut unter 2 V | **+11,233 ms** |
| B unterschreitet 0,2 V | **+335,887 ms** |
| A überschreitet zum ersten Mal 0,5 V | **+79,353 ms** |
| A erreicht +0,567483 V; B gleichzeitig nur ca. 0,087 V | **+699,989 ms** |

Das ist ein real aufgezeichneter **Versorgungseinbruch mit kurzem Wiederanstieg und anschließendem erneuten Einbruch** am benutzerseitigen 5-V-Messpunkt. Es passt zu der beschriebenen schwierigen USB-Steckverbindung, beweist aber nicht allein, ob die Ursache Kontaktprellen, Kabel, Buchse oder eine elektrische Schutz-/Versorgungsstörung ist.

**Korrelation:** Bei gemessenem B über 3 V hatte A **0 Samples über 0,5 V** (max. A dort ca. 0,131 V). Insgesamt überschritt A 0,5 V an **5.596 von 500.000 Messpunkten**, davon **5.536 Punkte, während B unter 0,2 V lag**. Der größte Ausschlag trat etwa 700 ms nach dem 5-V-Trigger auf, während B nahe 0 V lag. Das spricht gegen einen absichtlich getriebenen KNX_TX-HIGH-Pegel bei stabiler USB-Versorgung. **Einstreuung am unversorgten/schwebenden Signal** ist plausibel, aber nicht elektrisch bewiesen. Sehr kurze Transienten zwischen Abtastpunkten bleiben möglich.

**USB-Enumeration:** Windows hat den vorher erkannten ROM-Bootloader COM6 VID/PID 2E8A:0003 um **15:54:16 MESZ** verloren und um **15:54:34 MESZ** erneut erkannt. Der Hardware-Trigger beendete die Aufzeichnung um **15:54:25 MESZ**, also **vor** der abschließenden ROM-USB-Wiederanmeldung. Die Zeiten des Betriebssystems sind gepollte Sichtbarkeitsereignisse, keine präzisen Steckkontakt-Zeitstempel.

**Nach erfolgreichem Wiederanschluss:** Neue unabhängige Ruheaufnahme mit 500.000 Samples/Kanal: B min. **4,169 V**, Mittelwert **4,260 V**, max. **4,343 V**; A max. **0,131 V**, keine Messwerte über 0,5 V. Ist der gewählte Messpunkt tatsächlich der USB-VBUS-Eingang, sind 4,26 V niedriger als nominelle 5 V. **Mit Multimeter und geprüftem Bezugspunkt kontrollieren**, bevor daraus ein konkreter Hardwarefehler abgeleitet wird.

## Auswertung und Fehlerquellen

Das PicoScope lieferte für beide Kanäle je 1.000.000 Bytes little-endian signed-Int16-Rohdaten. Die SHA256-Werte, USB-Rohereignisse, Messbereiche und Korrelationen stehen im [JSON-Messprotokoll](KNX043_PICOSCOPE_DUAL_USB5V_RESULT_20261015.json). Es gab keinen RP2040-/KNX-/Motor-/Firmware-Schreibvorgang. Der bisherige Legacy-Zustandseintrag des Recorders mit "both x10" war irreführend; die **reale B-Einstellung war 1:1**, explizit in Aufruf und Ergebnis-JSON vermerkt. Das Skript wurde für neue Aufnahmen entsprechend korrigiert, die Original-Rohdaten und Metadaten bleiben unverändert.

**Sicherheitsstatus:** Alle 17 physischen KNX-Sicherheitsgates bleiben unbestätigt. Aus der Aufnahme folgt **keine Freigabe**, KNX TP oder reale Motorlasten zuzuschalten. U9/U11 nach Überhitzung, R17-Padtrennung, F1/D1/JMP1-Rückspeisung und das Verhalten unter KNX- bzw. Brownout-Versorgung sind separat zu messen.
