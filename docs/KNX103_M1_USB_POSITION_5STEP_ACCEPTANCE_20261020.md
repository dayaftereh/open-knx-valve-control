# KNX103 – M1-USB-Positionstest: 5 Fahrten erfolgreich

**Stand:** 20.10.2026, LLO Desktop Agent 0.8.2.
**Board:** OpenKNXValveControl V1.2, RP2040 COM7 / Seriennummer E464401787522D33.
**Testaufbau:** USB-C + Motor M1, ohne KNX-Bus, UPDI oder Temperatursensoren.

## Ablauf und Resultate

Die zuvor KNX100-fault-verriegelte Platine wurde bei Motor IDLE, GPIO LOW und INA219 0mA geprüft. Danach wurde das SHA256-gepinnte KNX101-Diagnoseimage einmalig geflasht, anhand der ROM-Geräteidentität verifiziert und nach Neustart ohne Motorbewegung als UNREFERENCED / IDLE bestätigt.

KNX101-Firmware: UF2 250880 Bytes, SHA256 9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76.
Flashbeleg: C:\ASH\Workspace\Runtime\KNX101\KNX101_FLASH_20261020_135652.json.

Fünf einzeln via ARM MOTORS freigegebene Echtfahrten:

| Schritt | Internes Ziel | Geplante Teilzeit | Tatsächlicher Stopp | Grund | Strom beim Stopp | INA219-Rohwerte |
|---:|---|---:|---:|---|---:|---:|
| 1 | Unbekannte Lage -> R-Endlage | Strombasiert, max 30 s | 12,951 s | ENDSTOP_CANDIDATE | 50 mA | 1.619 |
| 2 | R1000 -> F500 | 11,376 s | 11,383 s | TIMED_TARGET | 18 mA | 1.423 |
| 3 | F500 -> F250 | 5,688 s | 5,694 s | TIMED_TARGET | 20 mA | 712 |
| 4 | F250 -> R750 | 12,194 s | 12,199 s | TIMED_TARGET | 22 mA | 1.525 |
| 5 | R750 -> F-Endlage | Strombasiert, max 30 s | 16,599 s | ENDSTOP_CANDIDATE | 65 mA | 2.075 |

**5/5 Fahrten bestanden, 7.354/7.354 lückenlose INA219-Abtastungen mit 8-ms-Takt.** Jede Fahrt separat gestartet und nach Ende mit POSACKOFF, Motor-Gate IDLE, GPIOs LOW und INA219 0mA bestätigt. Keine unkontrollierte automatische Gegenfahrt.

Bei allen fünf Starts: KNX101 START_DIAG_OK pin_latch=1 pin_settled=1 model_ack=1. Deshalb ist der KNX100-Fehler FAILED_OUTPUT_OR_START_ACK bei den neuen Messungen nicht reproduziert. Ein initialer GPIO10-Pad-Lese-Transient ist plausibel, aber nicht bewiesen: KNX101 zeichnet den unmittelbar gelesenen Pad-Wert nur bei Fehler auf; bei erfolgreichen Starts nur den nach 1,3ms verzögerten Pad-Wert.

## Zeitstabilität und Genauigkeitsgrenzen

Die drei zeitgesteuerten Teilfahrten hatten nur **+7, +6 und +5 ms** Differenz zwischen Solltimer und realer Firmware-Abschaltung. Die gemessenen kurzen Stromspitzen lagen bei 105,60–109,75 mA, unter dem zusätzlichen Softwarelaufstromlimit von 120 mA.

Der reine Zeitansatz nach KNX098 rechnet für 75 % des F-Vollhubs mit 17,063 s; die abschließende echte F-Referenz aus der intern geschätzten 750-Promille-Position benötigte 16,599 s. **Residual = -464 ms**. Dieser Wert spricht dafür, die Zeit-zu-Weg-Umrechnung unter wechselnden Bewegungsrichtungen/Getriebespiel und Last zu kalibrieren. Er ist ohne externen Wegsensor **kein direkter Nachweis einer mechanischen Positionsabweichung**.

Die interne Koordinate heißt ausschließlich F-Endlage=0, R-Endlage=1000 Promille. Welche Fahrtrichtung das Ventil tatsächlich öffnet, ist noch nicht belegt. Die 25/50/75-Werte sind weiterhin TIMED_ESTIMATE, keine mechanisch gemessenen Ventilprozentwerte. Die Position an Stromlast-Enden bleibt CURRENT_ENDSTOP_CANDIDATE.

## Schutzkonzept

- Kein KNX aktiv, KNX-TX bleibt LOW.
- INA219 auf 0x40, 200-mOhm-Shunt, Motorstrom im 8-ms-Takt, max 120 mA.
- Versorgung zulässig 3100–3450 mV, Ruhegrenze 25 mA.
- Elektrische Endlage durch mindestens sechs fortlaufende Messungen >=45 mA nach 450 ms.
- Maximal 30 s Referenzsuchdauer, INA-/USB-/Strom-/Spannungsfehler und unvorhergesehene Last führen zu STOP und Verlust der Positionsgültigkeit.
- Nach jedem Stopp explizite Prüfung der Ausgänge und INA vor neuer Freigabe.
- TB6612 STBY ist fest HIGH. Der Software-Stromschutz ist keine unabhängige Hardware-STO.
- KNX101 kann nach step_completed=5 keine weitere Fahrt starten; kein Flash/Neustart für eine Wiederholung erfolgt.

## Unabhängige Nachprüfungen

1. Native C++17 Replay: tests/native/test_knx103_live_trace_replay.cpp. Mit MSVC /W4 /WX gebaut. Die **fünf echten Stromkurven** wurden durch dieselbe KNX099-Zustandsmaschine erneut verarbeitet; jeder einzelne Stopp wurde exakt an seinem ursprünglichen Firmware-Timestamp erkannt: **5/5 PASS, 7.354/7.354 Samples**.
2. Einmalig eingefrorene Nachweise: config/knx103_m1_position_bench.json. Enthält die SHA256-Fingerprints der fünf originalen CSV-Dateien und fünf JSON-Fahrberichte sowie Richtungen, Stopparten, Zeiten, Stromprofile und OFF-Quittungen.
3. Reproduzierbarer Offline-Validator: tools/knx103_position_acceptance.py. Normaler Aufruf prüft alle Dateien gegen den eingefrorenen Snapshot, ohne COM-Zugriff oder Motorsteuerung.
4. Manipulations-/Fehlernegativtests tools/test_knx103_position_acceptance.py: **12/12 PASS** (fehlende Proben, Abtastlücke, vorzeitige 6-fach-Stromschwelle, Versorgung, Position, GPIO-ACK).
5. KNX101 Release-Tests tools/test_knx103_knx101_release.py: **12/12 PASS**; KNX102 Regression 6/6; KNX100 Regression 12/12.

Originaldaten liegen ausschließlich auf LLO Desktop unter C:\ASH\Workspace\Runtime\KNX101: KNX101_STEP_01_R bis KNX101_STEP_05_F jeweils JSON + vollständige INA219-CSV. Große Rohaufzeichnungen wurden **nicht nach Git kopiert**.

## Abschlusszustand

Letzter echter COM7-Read-only-Check:
- KNX101, phase=IDLE, step_issued=5, step_completed=5;
- pos_r_permille=0, evidence=CURRENT_ENDSTOP_CANDIDATE, last_stop=ENDSTOP_CANDIDATE;
- Motor IDLE, alle GPIO-Ausgänge LOW, INA219 Ruhe 0 mA, Bus 3292 mV.

**Funktional bestanden:** USB-M1-Positionsansteuerung, 25/50/75-Probe mit stetiger INA219-Messung, Rückreferenzierung auf beide elektrischen Lastanstiegskandidaten.

**Noch nicht freigegeben:** Mechanisch verifizierte Zwischenpositionen in mm/%, Zuordnung R/F zu Ventil Öffnen/Schließen, geregelter KNX-/ETS-Betrieb, unbeaufsichtigter Produktivbetrieb. Die KNX098-Vollhubzeiten bleiben vorerst unverändert, weil die aktuelle Teilhubmessung allein keine bessere Lastkalibrierung begründet.

Kein Git-Push ohne ausdrücklichen Auftrag.
