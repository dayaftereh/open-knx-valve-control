# KNX008 – Zonen-, Heizkreis- und Regelmodusdesign (ETS-Proposal)

**Stand:** 12.10.2026. **Status:** ASH Design-/Offline-Software-Slice, **nicht in die produktive ETS XML, knxprod.hpp, RP2040-main oder die KNX/Antriebs-Hardware übernommen**.

**Maschinenlesbarer Entwurf:** [KNX008 ETS Proposal JSON](../assets/knx008_zone_ets_proposal.json). **Testbare, KNX-unabhängige Referenzlogik:** [heating_zone_model.hpp](../lib/common/heating_zone_model.hpp). **Tests:** [native C++](../tests/native/test_knx008_zone_model.cpp), [Produktkontrakt-Audit](../tools/audit_knx008_zone_contract.py).

## 1. Anforderungen und bewusst gewählte Grenzen

- **Bis zu 8 Zonen/Räume** Z1…Z8 und **genau 8 physische Motorkanäle** M1…M8. Ein Motor wird im ETS-Entwurf über **genau einen** Parameter auf **Zone 0 (keine Zuordnung)** oder **Zone 1…8** gesetzt. Jede Zone kann 0 bis 8 Motoren enthalten; ein und derselbe Motor darf nicht in mehreren Zonen stehen.
- **Kein Grund für starr eine Zone pro Motor.** Eine Zone mit 2, 3 oder 4 Kreisen bekommt eine einzige logische Stellanforderung. Die einzelnen Motoren bleiben physisch eigenständig (Laufzeit, Referenzstatus, geschätzte Istposition, Fehler).
- **Nicht angeschlossene oder deaktivierte Zonen** sowie ungültige ETS-Konfigurationen dürfen keine neuen Motor-Zielpositionen freigeben. Im späteren sicheren Motor-Scheduler ist weiterhin **exakt ein Motor gleichzeitig** erlaubt (vier TB6612FNG-Treiber mit gemeinsamer Richtung und einem INA219).
- **T0 ist Vorlauf, T1..T8 sind Rücklauf am Heizverteiler.** Keine dieser Temperaturen ersetzt die tatsächliche Raumtemperatur des Raums. Die 9 Messobjekte KO25..33 mit Status KO34/35 stammen aus KNX013–015 und bleiben unangetastet.
- **Keine tatsächliche Temperaturregelung oder Motorbewegung in KNX008.** Der Prototyp ist ausdrücklich nur ein Eingangsvalidierer und **Zielwert-Router**. Ein zukünftiger Regler (KNX010) berechnet erst den Stellwert; Motorschutz/-strom/-Endlagen und Ein-Motor-Fahrqueue folgen KNX004–006.
- **Kein ETS6-Import:** KNX016 und KNX009 bleiben gemäß [KNX017](KNX_TESTBENCH_PLAN.md) zurückgestellt. Der eigenständige Testplatz KNX018 wird erst später mit echter Hardware und KNX-Anbindung aufgebaut.

## 2. Signalkette und Zuständigkeiten

```text
Externe KNX-Raumgeräte (pro Zone Z1..Z8):
    Soll-Raumtemp     DPT9.001 ─┐
    Ist-Raumtemp      DPT9.001 ─┴──> KNX010 Raumregler (NOCH NICHT IMPLEMENTIERT)
                                           |
                                           v
                                       Stellziel 0..100%
    Direkter Stellwert DPT5.001 ────────────┐
                                             v
                              KNX008 Zonen-Gateway / Validierung
                             (Modus, Zeitstempel, Zuordnung, Grenzen)
                                            |
              +-----------------------------+------------------------+
              | M1            M2            M3                  M8  |
              | gleicher logischer Zonen-Zielwert, individuelle Endlage |
              +-----------------------------+------------------------+
                                            |
                        KNX004/005/006 sichere Einzelmotorfahrten
                         (gemeinsame Richtung + INA219: nur 1 aktiv)

ATtiny T0/Vorlauf, T1..T8/Rücklauf -> UART -> KNX015 Messdiagnose:
                          ausdrücklich KEIN Raum-Istwert
```

**Beispiel ohne behauptete reale Raumbelegung:** M1–M4 → Z1, M5–M7 → Z2, M8 → Z3; alle Zonen können unterschiedliche Betriebsarten verwenden. Sind M1–M4 in Z1, ist ihr logischer Zielprozentsatz identisch. Ihre reale Position oder der Durchfluss muss das deswegen **nicht** sein.

Eine Bewegung an einem Heizkreis beeinflusst hydraulisch die anderen. Der Raumregler sollte deswegen **langsame**, begrenzte Änderungen zulassen und Durchfluss-/Rücklauftemperaturänderungen nicht mit einer schnellen, gegenseitig aufschaukelnden Pseudoregelung kompensieren. Hydraulischer Abgleich/ggf. Differenzdruckregelung bleiben separate Systemthemen; ein linearer 50-%-Stellantriebshub ist **nicht** zwingend 50 % Volumenstrom.

## 3. Zwei klar getrennte Betriebsarten pro Zone

| ETS-Modus | Quelle | Gültigkeitsbedingungen | Ergebnis |
| --- | --- | --- | --- |
| **0 – Disabled** | keine | immer gesperrt | Keine neue Zielposition für zugeordnete Motoren |
| **1 – RoomTemperature** | externes KNX-Soll **und** externes KNX-Raum-Ist, DPT 9.001 | beide gültig und frisch; außerdem gesondert gültiger **KNX010-Reglerausgang** 0..100 % erforderlich | Reglerausgang als identischer Motor-Zielwert an alle Zonenteilnehmer weiterreichen |
| **2 – DirectPercent** | KNX 1-Byte DPT **5.001** Scaling, 0..100 % | letzter direkter Befehl gültig und nicht veraltet | KNX-Demand auf alle zugeordneten Motoren auffächern, *ohne* internen Temperaturregler |

**Konfliktregel:** Der ETS-Zonenmodus ist die einzige Autorität. Direkte Stellwerte werden in Modus 1 ignoriert; Temperatur-Soll/Ist werden in Modus 2 nicht zu Motorzielen. Es gibt keinen automatischen Moduswechsel aufgrund eingehender Telegramme. Gleichzeitige Telegramme können sich so nicht widersprechen. Eine neue ETS-Konfiguration oder ein Moduswechsel muss die bisher zwischengespeicherten Eingangs-/Reglerwerte explizit invalidieren, bis neue passende Telegramme eintreffen.

**Zeitgrenzen (später P38/P39):** Externe Soll-/Ist-Raumtemperaturen: Standard **900 s**, direkter Prozentwert: Standard **300 s**; jeweils vorgeschlagen gültig von 30…3600 s. In Modus 1 ist zusätzlich ein neuer vom KNX010-Regler berechneter Stellwert erforderlich. Der [C++-Router](../lib/common/heating_zone_model.hpp) besitzt für jeden Eingang einen `valid`-Status und `receivedAtMs`; `millis()`-Überläufe werden behandelt. Bei Ablauf der Frische werden **keine neuen** Fahranforderungen erstellt. Bereits wartende Fahrjobs muss **KNX004/KNX010** gesondert entwerten, laufende Motorbewegungen durch sichere Abschaltung behandeln. Dies ist **noch keine Hardware-Fail-safe-Implementierung**.

**Plausibilitätsgrenzen des Prototyps:** Raumsoll 5…35 °C, Raum-Ist −40…80 °C; im ETS-Produkt später explizit bestätigen/parametrieren. Der Router führt **keine** 1-Wire-Abfrage aus und hat keinen Zugriff auf die Vor-/Rücklaufsensorik.

## 4. Prozentdarstellung und Legacy-Kompatibilität

Intern verwenden wir für logische Stellziele `uint16_t` **0…1000 Promille** (0,1-%-Schritte). DPT **5.001** kodiert **0…100 % als Rohwert 0…255**.

| Gewünschte Stellung | KNX 5.001 raw | Intern Promille | Legacy 5.004 raw |
| --- | ---: | ---: | ---: |
| 0 % | 0 | 0 | 0 |
| ca. 50 % | 128 | 502 | 50 |
| 100 % | 255 | 1000 | 100 |

Runden: `raw * 1000 / 255` auf den nächsten Promillewert; Rückwärtsrichtung `permille * 255 / 1000` auf das nächste Byte. Eine empfangene rohe **50** bedeutet mit **DPT 5.001 ca. 19,6 %**, aber mit DPT **5.004 50 %**. **KO17..24 bleiben im aktuellen V2-Produkt DPT5.004 und werden durch KNX008 nicht umgedeutet**. Eine spätere aktive Kompatibilitätslösung muss entweder DPT-gerecht konvertieren oder die alten Objekte gezielt aus dem dynamischen ETS-UI herausnehmen; keinen stillen Mischbetrieb.

Die Position 0 % bedeutet bei der geplanten Kalibrierung **vollständig geschlossen**, 100 % vollständig offen; tatsächliche Motorpolung und Endlagen sind erst nach Messung KNX005/006 festzulegen. Der Stellwert ist **nicht** identisch mit dem hydraulischen Durchfluss.

## 5. ETS-KO-Vertrag: Vorgeschlagen, ausdrücklich nicht installiert

**Unveränderlicher IST-Vertrag:** ApplicationVersion **2**, **KO1..35** und **P1..21** in [assets/open-knx-valve-control.xml](../assets/open-knx-valve-control.xml), einschließlich DPT5.004 KO17..24 und DPT9.001 KO25..33. KNX008 reserviert im Entwurf nur zusätzliche Nummern und schlägt **ApplicationVersion 3** als spätere Migration vor. Keine XML-/Header-Datei wurde in diesem Slice geändert.

### Zonen-KOs, je vier ab 36

| Zone | Soll-Raumtemp (Rx) 9.001 | Ist-Raumtemp (Rx) 9.001 | Direkt % (Rx) 5.001 | Soll-Stellwert (Tx) 5.001 |
| --- | ---: | ---: | ---: | ---: |
| Z1 | 36 | 37 | 38 | 39 |
| Z2 | 40 | 41 | 42 | 43 |
| Z3 | 44 | 45 | 46 | 47 |
| Z4 | 48 | 49 | 50 | 51 |
| Z5 | 52 | 53 | 54 | 55 |
| Z6 | 56 | 57 | 58 | 59 |
| Z7 | 60 | 61 | 62 | 63 |
| Z8 | 64 | 65 | 66 | 67 |

Der vorgeschlagene C-Identifier ist `Zone{N}RoomSetpoint`, `Zone{N}RoomActual`, `Zone{N}DirectDemand`, `Zone{N}RequestedOutput`. `RequestedOutput` ist **der logische Zielwert**, weder tatsächlich gefahrene Motorkoordinate noch Durchfluss. ETS kann die jeweils irrelevanten Rx-KOs modusabhängig **ausblenden**; die Firmware darf sie unabhängig von Sichtbarkeit nicht auswerten. Dynamische KNX-Parameter-/KO-Blöcke brauchen später eine echte ETS6-Abnahme; derzeit existiert im Produkt nur ein dynamischer ETS-Kanal.

### Motor-/Geräte-Diagnosen: vorgeschlagene Zusatz-KOs

| KOs | Namen | DPT | Bedeutung |
| --- | --- | --- | --- |
| 68..75 | `Motor1EstimatedPosition` .. `Motor8EstimatedPosition` | 5.001 | Prozentuale, kalibrierabhängig **geschätzte** Position, kein Encoder |
| 76..83 | `Motor1Fault` .. `Motor8Fault` | 1.005 | Alarm pro Kanal, nicht als kontinuierliche Einzelstrommessung interpretieren |
| 84..91 | `Motor1Referenced` .. `Motor8Referenced` | 1.002 | Referenzfahrt erfolgreich und Position plausibel |
| 92..99 | `Motor1Moving` .. `Motor8Moving` | 1.001 | Bewegungsstatus des Kanals |
| 100 | `DeviceMotionBusy` | 1.002 | Gemeinsamer exklusiver Motor-Scheduler belegt |

**Ressourcen-Vorbehalt:** Die vorgeschlagenen 100 Gesamt-KOs sowie die neue Parameter-Speicherbelegung **wurden noch nicht von ETS6 oder dem konkreten MaskVersion-Limit bestätigt**. Abhängiger ETS-Migrations-/Importtest KNX009/016 bleibt deferred bis KNX018.

## 6. Parametervertrag: P22..39 nur vorgeschlagen

Die 21 bisherigen Parameter belegen Bytes **0 bis einschließlich 10** des ETS-Parameterbereichs. Ihre Bitadressen, Defaults und Bedeutungen bleiben erhalten. Die geplanten Parameter würden ohne Überlappung anschließend folgen:

| Parameter-IDs | Inhalt | Byte-Offsets | Typ / gültige Werte | Default |
| --- | --- | --- | --- | --- |
| P22..P29 | `Zone1Mode` .. `Zone8Mode` | 11..18 | uint8: 0 disabled, 1 room temp, 2 direct % | **0 (alle aus)** |
| P30..P37 | `Motor1Zone` .. `Motor8Zone` | 19..26 | uint8: 0 ohne Zone, 1..8 | **0 (unzugeordnet)** |
| P38 | `RoomTemperatureInputTimeoutSeconds` | 27..28 | uint16: 30..3600 s | 900 |
| P39 | `DirectDemandInputTimeoutSeconds` | 29..30 | uint16: 30..3600 s | 300 |

Dies reserviert theoretisch mindestens **31 Byte** ETS-Parameterraum; die Geräte-RAM/EEPROM-/KNX-Tabellenkapazität ist bei der späteren Produktintegration zu validieren. Ein **vollständig sicherer Auslieferungs-Default** hat alle Zonen deaktiviert und jeden Motor unzugeordnet. Bestehende Legacy-Parameter `DriveNActive` oder `DriveNControlLoop` werden nicht als Zonenkonfiguration ausgegeben und **nicht** automatisch migriert; dafür ist eine bewusste ETS-Migrationsstrategie erforderlich.

Jede Zoneneinstellung wäre im ETS-UI als Zone N mit Modi "Deaktiviert", "Soll-/Ist-Raumtemp", "Direkt-Stellwert" sichtbar. Jeder physische Kanal enthält ein Zone-Dropdown (0..8). Kompatibilität mit geänderten Kanaltypen, eindeutigen C-Identifiern und Read/Write/Transmit-Flags wird erst im KNX009-Produktumsetzungs-Gate festgelegt.

## 7. Status des testbaren C++-Modells

Die [heating_zone_model.hpp](../lib/common/heating_zone_model.hpp) setzt diese Abbildung bereits **rein im RAM** um:

1. Prüft jede der acht Zonen-Modusdefinitionen, jeden Motor-Zone-Eintrag und gültige Timeout-Parameter; schon ein ungültiger Eintrag führt zu **keiner** zulässigen Stellanforderung im gesamten Rückgabewert.
2. Wählt anhand des Modus exakt eine Eingangsquelle mit separatem `valid` und Zeitstempel. Bei Raumregelung sind externe Soll- und Ist-Temperatur **und** ein frischer, vom künftigen KNX010-Regler gelieferter Ausgang nötig.
3. Wandelt ausschließlich DPT5.001 Scaling, nicht DPT5.004, in 0..1000 Promille um.
4. Fächert pro Zone den fertigen Zielwert auf jedes zugehörige Motor-**Intent** auf. **Kein Motortreiber** und **kein** KNX-Objekt wird verwendet.

[Native-Tests](../tests/native/test_knx008_zone_model.cpp) decken Einzel- bis Vierfachbelegung, 4+3+1 Zuordnung aller acht Motoren, verschiedene Modi, 0-/100-%-Grenzen, echte 0-%-Befehle, DPT5.001 vs. 5.004, ungültige/stale Signale, ausgeschaltete/unzugeordnete Kanäle, fehlerhafte Konfiguration und `millis()`-Wraparound ab.

**Separater Software-Vorbereitungsslice KNX019:** Ein [portabler PI-Raumregelungskern](KNX019_ROOM_PI_SIMULATION.md) mit Deadband, Anti-Windup, Slew-Limit, Sensor-/Modus-Frische und Integration mit diesem Router wird offline simuliert. **Geplant für KNX010 (nicht Teil von KNX008/KNX019):** echte KNX-Eingangstelegramme, Firmware-Integration, Bus-Failover, Frostschutz, Motor-Queue-Entwertung, validierte reale Regelparametrierung und Hardwareabnahme. **Geplant für KNX004..006:** Ausgangs-Hardware-Interlock und exklusive Motor-Referenzfahrt. Die lokale Temperaturmessung bleibt Diagnose.

## 8. Nachweise, Freigaben und Wiederanlauf

Im Projekt-Root auf dem LLO Desktop Agent:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx008_zones.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx008_zone_contract.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py
    git diff --check

**Keine** ETS6-Produktdatei importiert oder heruntergeladen, keine physischen Telegramme oder Motorbewegungen. `KNX008` kann als Offline-Design-Slice geschlossen werden, **ohne** die späteren Implementierungs- oder Hardware-Gates zu umgehen. Vor echten Motorfahrten sind insbesondere [KNX002/003](POWER_SUPPLY_CONCEPT.md) und KNX004..006 offen. Der [Testbench-Plan](KNX_TESTBENCH_PLAN.md) bleibt maßgeblich für KNX018 und die wieder aufzunehmenden KNX009/016.
