# KNX099 – Ventilpositionierung ohne KNX-Bus

Stand: 20.10.2026. OpenKNXValveControl V1.2, LLO Desktop Agent.
Status: Portable Positionslogik implementiert und mit realen Strommessungen getestet. Physische Motorbindung, ETS-Kopplung und Zwischenpositionsvalidierung sind noch nicht freigegeben.

## 1. Basis und Richtungen

Quelle der Kalibrierwerte ist das eingefrorene KNX098-Bench-Profil in config/knx098_m1_bench_calibration.json. Es enthält drei R/F-Wiederholungszyklen mit insgesamt 17.678 validen INA219-Messpunkten (8-ms-Takt).

| Parameter | R | F |
|---|---:|---:|
| Mittlere Vollhub-Fahrzeit | 24.388,333 ms | 22.751,000 ms |
| Ganzzahliger C++-Parameter | 24.388 ms | 22.751 ms |
| Zeitliche Spannweite aus drei Zyklen | 216 ms | 144 ms |

**Wichtig:** Der neue Positionskern benutzt nur eine INTERNE technische Koordinate: F-Lastanstiegskandidat = 0 Promille und R-Lastanstiegskandidat = 1000 Promille. Ob R oder F das Ventil tatsächlich öffnet, ist noch ungeklärt; diese Koordinate ist deshalb NICHT der ETS-Öffnungsgrad. Es gibt auch noch keine Messung der absoluten mechanischen Ventilstellung oder von Zwischenpositionen.

## 2. Umgesetzte Software

- lib/common/knx099_m1_position_model.hpp: reiner portabler C++17-Positionskern, ohne Arduino-/GPIO-/KNX-/I2C- oder USB-Aufrufe.
- tests/native/test_knx099_position_model.cpp: 11 native Testgruppen für Referenzieren, Fahrzeiten, Zielplanung, Sicherheitsfehler und Bestätigung echter Motorstopps.
- tests/native/test_knx099_trace_replay.cpp: erneuter Durchlauf des C++-Endlagendetektors über alle sechs echten KNX097-CSV-Stromkurven.
- tools/knx099_native_verify.py: Windows-MSVC-Compile, native Tests, unveränderten KNX098-Kalibrierungsstand prüfen und sechs reale Stromtraces erneut validieren.
- src/controller/main.cpp: neuer C++-Header wird eingebunden und per static_assert mitkompiliert, aber keine Positionskern-Instanz erzeugt und keine Motoransteuerung freigegeben.

## 3. Zustands- und Schutzmodell

Zustände: Unreferenced, Idle, StartPending, Running, StopPending und FaultLatched.

- Neustart verwirft jede frühere Positionsschätzung. Eine Fahrt benötigt explizite Freigabe, bestätigte LOW-Ausgänge und einen gültigen INA-Ruhestrom.
- Die Referenzsuche nach R oder F stoppt bei sechs gültigen, aufeinanderfolgenden INA-Werten ab 45 mA. Die ersten 450 ms zählen wegen des Anlaufstroms nicht. Ein Stromabfall auf 0–5 mA wird als eigener, nicht bestätigter Endschalter-/Stromfehler behandelt.
- Jede Fahrt hat eine maximale 30-s-Dauer, 120-mA-Laufstromgrenze und zulässige Motorspannung 3100–3450 mV.
- INA-/Kommunikationsfehler, fehlendes erstes INA-Sample, Abtastlücken über 16 ms, falsche quittierte Fahrtrichtung, Überstrom, Spannungsausfall, Zeitüberschreitung oder ungeplante Blockierung liefern STOP/FAULT.
- Der Positionskern gibt nur typisierte StartR-, StartF- und Stop-Aufträge aus; er schaltet niemals GPIOs selbst. Eine Fahrzeit oder USB-STOP-Antwort ist für sich KEIN Beweis für einen tatsächlich stillstehenden Motor.
- Erst ein separat und unabhängig bestätigtes Abschalten sämtlicher Motorausgänge darf eine strombasierte Endlagen-Kandidatenposition oder eine zeitbasierte Zwischenpositionsschätzung übernehmen.
- Ein abgebrochener oder nicht quittierter Lauf verwirft die Position und verriegelt den Fehlerzustand. Ein falscher Motorstart-ACK erzeugt sofort einen STOP-Auftrag.
- Maximal vier zeitbasierte Teilfahrten ohne erneuten stromerkannten Endlagenbeleg; danach muss neu referenziert werden.
- Totband 15 Promille und kein rein zeitbasiertes Positionieren innerhalb der letzten 30 Promille vor den Endlagen; Endpositionen benötigen Stromreferenzierung.

## 4. Zeitbasierte Teilpositionsplanung

Intern von F=0 Promille nach R=1000 Promille gerechnet:
- Fahrzeit R = Positionsdifferenz/1000 * 24.388 ms.
- Fahrzeit F = Positionsdifferenz/1000 * 22.751 ms.

Beispiele aus dem Test:
- F-Ende (0 Promille) bis interne 500 Promille: R-Laufzeit **12.194 ms**.
- Von internen 500 nach 250 Promille: F-Laufzeit **5.688 ms**.

**Diese Werte sind noch keine nachgewiesenen physikalischen 50-%- oder 25-%-Ventilpositionen.** Der Status lautet ausdrücklich TimedEstimate; er unterscheidet sich vom CurrentEndstopCandidate.

## 5. Testergebnisse

### Native C++-Tests

Microsoft Visual Studio 2022 MSVC, C++17, Warnungen als Fehler. Ergebnis: **11/11 Testgruppen PASS**. Geprüft werden u. a. Nullzustand nach Reset, fehlende Referenz, sicherer START-/STOP-ACK, falsche Fahrtrichtung, gültige/unplausible Sensordaten, USB-Verlust, Stromgrenzen, Unter-/Überspannung, Endlagenstörpeaks, zeitbasierte Zwischenfahrt, Überlauf von 32-Bit-millis, Timeout und Referenzverlust.

### Wiederholung aller echten Messungen mit dem neuen C++-Detektor

| Lauf | Richtung | Rohmessungen | Neuer Endlagen-Trigger |
|---:|:---:|---:|---:|
| 1 | R | 3053 | 24.423 ms |
| 2 | F | 2846 | 22.767 ms |
| 3 | R | 3060 | 24.479 ms |
| 4 | F | 2852 | 22.815 ms |
| 5 | R | 3033 | 24.263 ms |
| 6 | F | 2834 | 22.671 ms |

**Ergebnis: 6/6 genaue Übereinstimmungen** mit dem zuvor real gemessenen Firmware-Abschaltzeitpunkt; alle 17.678 INA219-Originalwerte verarbeitet. Das prüft den tatsächlich neuen C++-Kern und nicht nur die ältere Python-Analyse.

### RP2040 Controller-Build

Die produktive Firmware wurde vollständig neu mit PlatformIO Core 6.1.16 und dem vorhandenen Arduino-Pico-Toolchain-Pin gebaut. Für den ersten vollständigen Build musste der bereits vorhandene Arduino-Pico-Wire-Header in src/controller/main.cpp explizit eingebunden werden, damit die mitgelieferte Wire-Bibliothek auch von der PCF8574-/INA219-Abhängigkeit gefunden wird. Dabei wird Wire NICHT gestartet und kein Motor-GPIO gesetzt. Der produktive Motor-Hardlock des bisherigen RoomControlRuntime bleibt in Kraft.

Es wurde **keine neue Firmware auf den angeschlossenen RP2040 geflasht** und es gab **keinen neuen Motorimpuls**.

## 6. Noch offen / nächster Slice

KNX100: Zunächst einen separat abgesicherten USB-only-Motoradapter für M1 mit den bewährten INA219-Strom- und Motorspannungs-Gates an den KNX099-Positionskern anbinden. Danach können wenige explizit freigegebene physische Zwischenpositionsfahrten und Gegenreferenzen getestet werden, ohne KNX-Bus. Erst nach belegter Richtung Open/Close und Zwischenpositions-Prüfung ETS-Kommunikationsobjekte an das Positionsmodell koppeln.

Der V1.2-TB6612-Treiber hat STBY fest HIGH. INA219-Softwareüberwachung alle 8 ms ist keine unabhängige Hardware-Sicherheitsabschaltung. Aus diesem Software-Slice folgt ausdrücklich keine Freigabe für unbeaufsichtigte automatische Motorbewegungen oder KNX-Stellwertbetrieb.

Die angeschlossene Platine bleibt auf KNX097 (legs_done=6), COM7, INA219 CONFIG 0x399F, Motor IDLE und alle Treiberausgänge LOW. Kein Git-Push ohne ausdrückliche Freigabe.
