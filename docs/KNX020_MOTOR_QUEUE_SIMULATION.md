# KNX020 – Exklusive Motor-Fahrqueue als reine C++-Simulation

**Stand: 12.10.2026. Status: Software-Simulation, KEIN MOTORTEST.** Dieser Slice bereitet den Zustandsautomaten für den späteren [KNX004 Motor-Safety-Slice](ROADMAP.md) vor. Er implementiert weder PWM-/Motor-Treiber noch ein Hardware-Interlock. ETS-Dateien, RP2040-/ATtiny-Firmware und PCB bleiben unverändert.

## Warum die acht Antriebe nacheinander fahren müssen

Die V1.2-Platine besitzt vier TB6612FNG-Dualtreiber für acht Motoren, **gemeinsame IN_1/IN_2-Richtungssignale** und einen **gemeinsamen INA219-Strompfad**. Daraus folgt die Anforderung: **Maximal eine aktive Motorfahrt auf der gesamten Platine**. Mehrere KNX-Räume dürfen gleichzeitig verschiedene Sollwerte anfordern, aber nicht gleichzeitig Motoren bewegen.

[KNX019](KNX019_ROOM_PI_SIMULATION.md) erzeugt Raumtemperatur-Stellwerte; der [KNX008-Router](KNX008_ZONE_CHANNEL_DESIGN.md) ordnet sie den Motoren zu. KNX020 verarbeitet die acht Software-Zielwerte, simulierte Motorpositionen und simulierte Treiberquittungen. **Seine Start-/Stop-Ereignisse sind abstrakte Datenwerte und keine physische Freigabe.**

## Zustandsautomat

    BOOT --> DISARMED
                | explizit armieren + Mock-Safety-Gates
                | + extern bestätigtes All-off
                v
               IDLE --> START_PENDING --> RUNNING
                         | Start-ACK          |
                         +-- Fault/Timeout ---+
                                               |
                            Laufzeit erreicht / Ziel geändert / Fehler
                                               v
                                          STOP_PENDING
                                       (Lease bleibt reserviert)
                                               |
                               Stop-ACK mit passendem Token und All-off
                                               |
                                +--------------+--------------+
                                v              v              v
                               IDLE         DISARMED     FAULT_LATCHED
                             (Totzeit)      (Rearm)      (Reset nötig)

**Lease vor Start:** Ein Motorkanal wird bereits vor dem START-Ereignis exklusiv reserviert. Vor der passenden STOP-Quittung kann niemals ein zweiter START erteilt werden. Ein fehlender STOP-ACK blockiert jeden weiteren Motor und lässt das STOP-Ereignis mit **derselben Token-ID** wiederholen. Ein Timeout erzeugt zusätzlich einen verriegelten Fehlerzustand, aber keine Freigabe des Leases.

**Keine persistente FIFO mit alten Stellwerten:** Der Scheduler wertet im IDLE-Zustand immer die aktuellen [KNX008 MotorTargets](../lib/common/heating_zone_model.hpp) aus. Verlorene Berechtigung, geänderter Sollwert, Referenzverlust oder Operator-Cancel stoppen die aktuelle simulierte Bewegung. Nach Stopp wird vor erneuter Fahrt desselben Kanals eine neue Positionsevidenz-Revision verlangt. Die Reihenfolge der zu startenden Motoren ist Round-Robin.

**Wichtig:** Eine hypothetische Fahrzeit beweist nicht das tatsächliche Erreichen der Ventilstellung. Der Simulator berechnet aus Positionsdifferenz und übergebener fiktiver Vollhubzeit nur eine geplante Dauer; es gibt keinen Encoder. Der Herstellerwert 120 mA für HmIP-VDMOT ist kein nachgewiesener Endlagenschwellwert.

## Simulationseinstellungen

| Eigenschaft | Software-Default, NICHT physisch vermessen |
| --- | --- |
| Ausgangszustand | DISARMED, kein Fahrereignis |
| Freigabe | Fünf Mock-Sicherheits-Flags plus unabhängiges All-off erforderlich |
| Kanäle | Acht Indizes 0–7, keine GPIO-Pinreferenzen |
| Position | Nur bei valid, referenced und 0…1000 Promille |
| Vollhubzeit | Simulierter zulässiger Eingabebereich 5…180 s |
| Kleinbewegungsgrenze | 20 Promille (2 Prozentpunkte) |
| Maximaler Einzelauftrag | 120 s, längere Aufträge werden abgelehnt, nicht verkürzt |
| START-Quittungszeit | 1 s; Timeout führt zu STOP und Fehlersperre |
| STOP-Quittungszeit | 2 s; Timeout hält den Lease und wiederholt STOP |
| Pause zwischen Motoren | Mindestens 500 ms nach bestätigtem Stopp |
| Sicherheitsverlust / Not-Stopp / Fehler des aktiven Motors | STOP, latched Fault; niemals automatische Wiederaufnahme |

Alle Guard-Flags sind **synthetisch**. Sie heißen explicitTestPermit, boardAsBuiltQualified, supplyQualified, outputInterlockQualified, currentMonitoringQualified und emergencyStop. Das Testprogramm darf diese Booleans setzen; daraus folgt keinerlei reale Bestückungs-, Spannungs- oder Schutzfreigabe.

Die Richtung bedeutet ausschließlich LogicalOpen oder LogicalClose, **keine behauptete Motorpolung oder Ansteuerspannung**. Ein bestätigter Timeout oder bestätigtes Ausgehen einer fiktiven Motorbewegung ersetzt weder INA219-Stromprüfung noch Hardware-Rückmeldung.

## Fehlerreaktionen

- **Start-ACK fehlt oder hat falschen Token:** Keine Annahme einer gestarteten Fahrt; nach Deadline STOP und Fault.
- **Stop-ACK fehlt oder ist ungültig:** Motor-Lease bleibt reserviert und STOP wird wiederholt; kein zweiter Motor erhält Freigabe, auch nach dem Timeout.
- **Verlust Power-Good, Motorkanal-Fehler oder Not-Halt:** Abstraktes STOP-Ereignis und verriegelte Fehlersperre bis nach bestätigtem All-off, manuellem Fault-Reset und erneutem Arm.
- **Stale KNX-Input oder geänderter Sollwert:** STOP; danach DISARMED bis erneuter expliziter Freigabe. Kein alter Fahrjob wird danach automatisch fortgesetzt.
- **Nicht referenzierter Antrieb / fehlende Positionsrevision:** Keine neue Fahrt; Referenzverlust während eines Leases stoppt.
- **Reboot:** Zurück nach DISARMED. Ein unabhängiger physischer All-off-Nachweis wäre im späteren KNX004-Backend zusätzlich nötig. Software-Tokens bleiben innerhalb derselben Testinstanz monoton, aber reale bootübergreifende Epoch-IDs sind noch ungelöst.

**Sicherheitsgrenze:** Ein STOP-Ereignis im Simulator schaltet physisch nichts aus. Reale Verriegelung, GPIO-Ausgänge-low, Energieabtrennung, Watchdog und aktuelle Stromabschaltung sind **ausdrücklich nicht implementiert**.

## Software-Artefakte und Tests

| Artefakt | Inhalt |
| --- | --- |
| [motor_queue_simulator.hpp](../lib/common/motor_queue_simulator.hpp) | Reiner C++-Zustandsautomat mit acht Motoren, global exklusivem Lease, Quittungen, Timeouts und Mock-Guards |
| [test_motor_queue_simulator.cpp](../tests/native/test_motor_queue_simulator.cpp) | Start-/Stop-Ack, Round-Robin acht Motoren, Stale, Cancel, Fault, Hardwareevidenz-Sperren, 32-Bit-Zeitüberlauf, Integration mit echtem KNX008-Router |
| [test_motor_queue_stress.cpp](../tests/native/test_motor_queue_stress.cpp) | 20.000 deterministische Simulations-Ticks mit wechselnden Zielwerten, Guard-Störungen und Quittungen |
| [test_motor_queue_simulator.py](../tools/test_motor_queue_simulator.py) | Wiederholbare native Builds (C++17, -Wall, -Wextra, -Werror, -pedantic) |
| [audit_knx020_motion_offline.py](../tools/audit_knx020_motion_offline.py) | Prüft produktive ETS/Firmware/PCB-Quellen gegen Git-Baseline und verbietet Hardware-/KNX-API-Aufrufe im Simulator |

Im Repo-Root ausführen:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_motor_queue_simulator.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx020_motion_offline.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx008_zones.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_room_pi_controller.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py

**Bisheriger Test:** Zwei native KNX020-C++-Suites PASS. Der Stresslauf umfasste **20.000 Schritte**, **703 abstrakte Starts** und **702 bestätigte Stopps** bei **maximal einem simultan belegten simulierten Motorplatz**. Die letzte Testfahrt konnte beim Ende des Zeitfensters noch aktiv sein. Das sind KEINE echten Motorbewegungen.

## Voraussetzungen vor produktiver Integration

1. **KNX002:** As-built V1.2 prüfen (U25-Bestückung, R29-Shunt, TB6612-Ausgänge, STBY/Richtung, Leiterbahn- und Pinbelegung).
2. **KNX003:** Externe 5-V-/3,3-V- und KNX-Versorgung sicher spezifizieren und mit Stromreserve und Rückspeiseschutz aufbauen.
3. **KNX004:** Echten, unabhängigen Hardware-All-off- und Exklusiv-Interlock inklusive Reset- und Watchdog-Verhalten sowie realem Stop-ACK implementieren und prüfen.
4. **KNX005/006:** HmIP-VDMOT-Polung, Stromkurven, Blockade-/Endlagenreaktion, tatsächliche Hubzeiten, Referenz und Positionsunsicherheit messen. Keine willkürlichen Vollhubzeiten aus diesem Simulator übernehmen.
5. **KNX018:** Eigenständige KNX- und Controller-Testumgebung errichten. ETS-/KNX-Importtests KNX009 und KNX016 bleiben bis dahin zurückgestellt.

**ASH-Scope:** KNX020 darf als Offline-Simulator abgeschlossen werden. KNX004, KNX005, KNX006 und KNX010 bleiben geplante, nicht durch KNX020 hardwareseitig freigegebene Slices. Es gab keinen ETS6-Import, keine KNX-Bustelegramme, keine GPIO-Aktionen, keinen Motorlauf und keinen Firmwareflash.
