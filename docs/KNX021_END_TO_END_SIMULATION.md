# KNX021 – Durchgängige Offline-Simulation von Raum-PI bis Motorfeedback

**Stand: 12.10.2026.** Ausschließlich native C++-Simulation. **Keine** ETS6-, KNX-Bus-, RP2040-, ATtiny-, GPIO-, Motor- oder Platinenaktion.

## Zusammenspiel

Vor KNX021 waren die Bausteine getrennt validiert: [KNX019 PI-Regler](KNX019_ROOM_PI_SIMULATION.md), [KNX008 Zonenrouter](KNX008_ZONE_CHANNEL_DESIGN.md) und [KNX020 exklusive Fahrqueue](KNX020_MOTOR_QUEUE_SIMULATION.md). KNX021 testet erstmals deren **kombinierten Pfad**, ohne vorhandenen Produktivcode zu verändern.

    Externe synthetische Raumtemperatur / direkter Prozentwert
                  |
             KNX019 Raum-PI
                  |
             KNX008 Zonenrouter
                  |
             KNX020 exklusiver Motor-Lease
                  |               ^
            Start / Stop          | tokenisierte Quittungen
                  v               |
             Virtuelles Motorfeedback
                  |
        Fiktive Ausgangsbelegung / Positionsrevision

Die virtuelle Motorschicht hat keine Bibliotheken für Arduino, GPIO, PWM, KNX oder Serial. Sie konsumiert lediglich abstrakte Start-/Stop-Events.

## Feedback-Vertrag und Sicherheitsgrenze

- **START:** Ein virtuelles Motor-Ausgangsbit darf nur aktiviert werden, wenn vorher keines belegt ist. Ein Start erhält nach einer einstellbaren Verzögerung eine tokenisierte Quittung.
- **STOP:** Die abstrakte Belegung kann auf null gehen, doch die KNX020-Queue gibt den exklusiven Lease **erst nach passendem All-off-ACK** frei. Wiederholte STOP-Events sind idempotent; sie verlängern nicht die Backend-ACK-Deadline.
- **Geplantes Fahrende:** Erst wenn die simulierte Laufzeit vollständig verstrichen und die All-off-Quittung ausgegeben ist, wird der gewünschte Sollwert als **rein virtuelle Positionsschätzung** übernommen. Die Schätzungsrevision steigt.
- **Abbruch/Fehler:** Nach vorzeitigem STOP werden die Flags für valide Position und Referenz **gelöscht**. Die Zwischenposition ist unbekannt; eine bloße erneute Armierung darf diesen Motor nicht wieder bewegen. Erst eine separat eingespeiste, **simulierte** Referenz-Evidenz ermöglicht dies.
- **Stop-ACK fehlt:** Der Lease wird auch bei scheinbar abgeschaltetem Backend nicht freigegeben; nach Timeout verriegelt KNX020 den Fehler.
- **Blockierte Abschaltung:** Bleibt das abstrakte Ausgangsbit belegt, startet auch nach Timeout kein anderer Motor. Eine spätere Test-Recovery muss weiterhin Token und All-off bestätigen.

Eine hypothetische Positionsschätzung ist **keine physische Messung**. Das Verhalten beweist kein Hardware-Interlock und keinen HmIP-VDMOT-Strom- oder Endlagenschwellwert. Physisches All-off, STBY-Ausgänge, Power-Good und Referenzfahrten sind erst in KNX002–006 zu prüfen.

## Szenarien im Integrationstest

| Szenario | Software-Nachweis |
| --- | --- |
| Zone 1 mit zwei Direkt-Stellwert-Heizkreisen | DPT5.001-Skalierung auf M1 und M2; beide erhalten 502 Promille (50,2 %), fahren aber nacheinander |
| Zone 2 mit PI-geregeltem Heizkreis | Externer Raum-Soll/Istwert geht über den vorhandenen KNX019-Regler auf M3 mit erstem Stellziel 30 Promille (3,0 %) |
| Gesamte Abnahme dieser Testsequenz | **3 virtuelle Starts, 3 bestätigte Off-ACKs**, Positionen M1/M2/M3 = 502/502/30 Promille |
| Eingangsverlust während Fahrt | Abbruch, Position nicht mehr vertrauenswürdig, neue Referenzevidenz erforderlich |
| Fehlende oder zu späte Stoppquittung | Alle anderen Motoren bleiben gesperrt, Fehler wird verriegelt |
| Simuliert blockierte Off-Schaltung | Ausgangsbelegungsbit bleibt gesetzt, kein zweiter Start |
| 32-Bit-Zeitüberlauf | Start, Stop, ACK und Positions-Update über die Millisekundenzählergrenze getestet |

Bei jedem Simulationsschritt wird überprüft, dass die virtuelle Ausgangsmaske und die Queue-Maske **höchstens je ein Bit** enthalten und dass jede belegte Motorposition ihrem reservierten Lease entspricht.

Die 502/502/30 Promille sind **künstliche Sollwerte**, keine vermessenen Ventilstellungen. Sie entstehen aus DPT5.001 (Byte 128) und dem KNX019-Slew-Limit. Eine reale hydraulische Kopplung ist in dieser Sequenz nicht simuliert.

## Dateien und reproduzierbare Prüfungen

| Artefakt | Funktion |
| --- | --- |
| [virtual_motor_feedback.hpp](../lib/common/virtual_motor_feedback.hpp) | Neuer isolierter C++-Motorfeedback-Mock mit Positionsrevision und Off-ACKs |
| [test_knx021_end_to_end.cpp](../tests/native/test_knx021_end_to_end.cpp) | Tatsächliche KNX019-/KNX008-/KNX020-Klassen integriert; Normalfall, Sensorfehler, ACK-Verlust, blockierter STOP und Zeitüberlauf |
| [test_knx021_end_to_end.py](../tools/test_knx021_end_to_end.py) | Reproduzierbarer nativer C++17-Build (-Wall, -Wextra, -Werror, -pedantic) |
| [audit_knx021_e2e.py](../tools/audit_knx021_e2e.py) | Festes Baseline-Git 8dc7577; Vergleich aller produktiven Firmware-/KNX-/PCB- und früheren Modellquellen, Hardware-API-Ausschluss |

Befehle aus dem Repository-Root:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx021_end_to_end.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx021_e2e.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_motor_queue_simulator.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_room_pi_controller.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx008_zones.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py

**Noch offen für reale Hardware:** KNX002 As-built, KNX003 KNX-/5-V-/3,3-V-Stromversorgung, KNX004 Hardware-All-off und Ein-Motor-Interlock, KNX005/006 reale Lauf-/Strom-/Referenzmessungen, KNX018 eigenständiger KNX-Testplatz. KNX009/016 sind bis dahin vom Nutzer bewusst zurückgestellt. KNX010 produktive Raum-/Motorregelung ist nicht abgeschlossen.

KNX021 ist nur die sichere *Software-Schichtübergreifende Mock-Abnahme* und darf nicht als Freigabe zum Flashen oder Ansteuern echter Motoren interpretiert werden.
