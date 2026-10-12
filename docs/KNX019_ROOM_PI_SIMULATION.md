# KNX019 – Simulierter PI-Raumtemperaturregler für den späteren KNX010-Slice

**Stand:** 12.10.2026. **Status:** eigenständiger, offline getesteter C++-Reglerkern – **keine real angeschlossene KNX-Schnittstelle, kein ETS6-Import, keine Hardware-Motorbewegung, kein validierter realer Heizungsbetrieb**.

Dieser Slice setzt **nur die Rechen- und Validierungsseite** des späteren Raumtemperaturreglers um. Die produktive ETS-XML (ApplicationVersion 2), das generierte KNX-Headerfile, die bestehenden RP2040-/ATtiny-Firmwares und sämtliche H-Brücken-Ausgänge sind unverändert. Der große [KNX010-Integrationsslice](ROADMAP.md) bleibt geplant und braucht weiterhin KNX006/007/009; die ETS-/Bus-Slices KNX009/016 sind [auf Nutzerwunsch zurückgestellt](KNX_TESTBENCH_PLAN.md).

## 1. Datenfluss und Abgrenzung

Die physische V1.2-Platine hat acht motorisierte Ventile, aber nur einen gemeinsamen INA219-Strommesspfad und geteilte Richtungsleitungen. **Auch bei acht parallelen Raumreglern darf nur ein Motor physisch fahren**; diese Arbitrierung ist Aufgabe von KNX004–006, nicht KNX019.

Die neun lokalen ATtiny-Sensoren T0 (Vorlauf) sowie T1–T8 (Rücklauf) melden Rohr-/Verteilertemperaturen und sind **keine Raum-Isttemperatur**. Für jeden Raum werden externe KNX-Raum-Soll- und Raum-Istwerte benötigt. Ihre künftigen KOs sind als *Vorschlag* in [KNX008](KNX008_ZONE_CHANNEL_DESIGN.md) spezifiziert; sie sind **noch nicht** in der produktiven KNX-XML vorhanden.

    Raum-Soll (KNX DPT 9.001)     Raum-Ist (KNX DPT 9.001)
                \                     /
                 \                   /
                   KNX019 PI (8 Zonen)
                   -> 0..1000 Promille
                   -> KNX008 Zielwert-Router
                   -> 1..8 Motor-ZIELWERTE im RAM
                   -> später KNX004/005/006 Fahr-Scheduler
                         (ein Motor zur Zeit)

    Alternativ: KNX DPT 5.001 Direkt-Prozent
                   -> KNX008, unter Umgehung des PI-Reglers

**Wichtig:** Ein Regler-Sollwert von 50 % ist ein angenommener Stellhub, **kein** Beweis für 50 % hydraulischen Durchfluss. Die voneinander abhängigen Durchflüsse bei mehreren Ventilstellungen bleiben Gegenstand späterer Systemtests; schneller Sollwertwechsel kann sich sonst gegenseitig verstärken.

## 2. Implementierung

| Baustein | Datei | Rolle |
| --- | --- | --- |
| PI-Zustand und 8-Zonen-Bank | [room_pi_controller.hpp](../lib/common/room_pi_controller.hpp) | Reiner portabler C++-Header ohne Arduino, KNX-Library, Serial, GPIO oder PWM |
| Existierender Zonenrouter | [heating_zone_model.hpp](../lib/common/heating_zone_model.hpp) | Weitergabe nur gültiger Zonen-Stellziele auf 1..8 Motorzuordnungen |
| Native Unit-, Integration- und Toy-Plant-Tests | [test_room_pi_controller.cpp](../tests/native/test_room_pi_controller.cpp) | Fehlertests, Zeitverhalten, 8 Zonen, zwei gekoppelte Raumtemperaturen |
| Wiederholbarer Testlauf | [test_room_pi_controller.py](../tools/test_room_pi_controller.py) | Kompiliert C++17 mit -Wall/-Wextra/-Werror/-pedantic, führt native EXE aus |
| Nichtintegrations-/ABI-Audit | [audit_knx019_room_pi.py](../tools/audit_knx019_room_pi.py) | Git-Vergleich gegen festes KNX008-HEAD und Nachweis unveränderter ETS-/Firmwaredateien |

**PI-Struktur (heating-only):**

    error_K = (room_setpoint_centiC - room_actual_centiC) / 100.0
    if abs(error_centiC) <= deadband_centiC: error_K = 0
    P_permille = Kp_permille_per_K * error_K
    I_candidate = I_previous + P_permille * dt_seconds / Ti_seconds
    U_unlimited = P_permille + I_candidate
    U_limited = clamp(U_unlimited, 0, 1000)
    U_output = clamp(U_limited, last_output - max_slew*dt/60s,
                                 last_output + max_slew*dt/60s)

Das ist eine konzeptionell diskretisierte **PI-Heizregelung** mit Integrationszeit Ti und Proportionalfaktor Kp. Die tatsächliche Implementierung begrenzt den I-Term explizit auf 0..1000 Promille und **stoppt die weitere Integration, wenn das Regelsignal in dieselbe Richtung bereits an 0/100 % gesättigt oder an der Slew-Grenze begrenzt ist** (conditional-integration Anti-Windup). Bei negativer Regeldifferenz kann der I-Term wieder abgebaut werden. Der Regler treibt keine Hardware; diese Berechnung ist kein sicherheitstechnisches Überhitzungsschutzorgan.

## 3. Parameter und frei gewählte Simulationsdefaults

Die folgenden Werte sind **feste Testprofil-Defaults im C++-Quellcode, nicht ETS-Parameter und nicht an einer echten Fußbodenheizung abgestimmt**.

| Parameter | Modell-Default | Im Prototyp erlaubter Bereich |
| --- | ---: | ---: |
| Kp | 250 Promille je K = 25 Prozentpunkte/K | 1..1500 Promille/K |
| Integrationszeit Ti | 3600 s = 60 min | 300..21600 s |
| Deadband | ±0,10 K | 0..1,00 K |
| maximale Stellwertänderung | 30 Promille/min = 3 Prozentpunkte/min | 1..300 Promille/min |
| Rechenintervall | 60 s | 30..600 s |
| externe Raum-Soll-/Ist-Gültigkeit | 900 s aus KNX008-Konfiguration | 30..3600 s |
| direkter DPT5.001-Stellwert | KNX008-Timeout 300 s | 30..3600 s |

Plausibilitätsgrenzen aus KNX008: Raum-Soll 5..35 °C, Raum-Ist −40..80 °C. Einstellbar pro Zone im RAM, ohne persistierten ETS-Produktparameter. Vor echtem Heizen sind Parametrierung, Raumreaktion und Komfort/Frostschutz zu bewerten.

### Verhalten bei Initialisierung, Änderungen und Fehlern

- **Neustart/erstmaliger Raum-Modus:** Beide externen Raumtelegramme müssen gültig und nach Eintritt in den Raumregelungsmodus empfangen worden sein; der Ausgang beginnt bewusst bei 0 Promille und folgt erst danach dem eingestellten Slew-Limit. Dies ist eine **neutral gestartete Software-Zielgröße**, kein Aufruf zum physisch sofortigen Ventilschließen.
- **Mode DirectPercent:** Der PI-Regler wird vollständig umgangen. Nur der direkte DPT5.001-Wert wird über KNX008 an die Motorziele verteilt. KO17..24 des V2-Produkts sind aktuell weiterhin **DPT5.004 und nicht kompatibel** ohne spätere Migration.
- **ETS-Zuordnungs-/Timeout-Änderung:** Konservative **globale Neuinitialisierung** aller Zonen und Invalidierung alter direkter Befehle. Dadurch kann z. B. ein neu zugeordneter Motor keinen vorherigen Raumauftrag aus einer alten Konfiguration erben.
- **Raum-Soll-/Istfehler, Werte außerhalb Plausibilität oder Telegrammtimeout:** Reglerstatus ungültig, kein neuer gültiger Zielwert, Integrator wird zurückgesetzt. Zum Reaktivieren müssen **beide** Eingänge seit Fehler-/Konfigurationsbarriere neu eingegangen sein. Nur einen neuen Raum-Istwert zu erhalten genügt nach Störung nicht.
- **Blockierter Regel-Loop:** Bei einer Rechenpause über **3 × konfiguriertes Rechenintervall** wird kein großer aufgestauter Integrationsschritt ausgeführt. Stattdessen Ausgang invalidieren, Integrator zurücksetzen und neue Raumtelegramme verlangen.
- **Kp-/Ti-/Deadband-/Slew-/Intervalländerung:** Reset nur der betroffenen Zonen-PI; der Zustand erbt keinen fremden I-Term.
- **Betrieb ohne Störung:** Zwischen geplanten PI-Rechenschritten bleibt ein innerhalb der Quellen-Gültigkeit liegender letzter Sollwert gültig; der Ausgangszeitstempel wird erst bei tatsächlichem PI-Rechenschritt erneuert, nicht bloß durch Update-Aufruf.

**Physische Fail-safe-Einschränkung:** Die Invalidierung verhindert **nur neue Stellziele im KNX008-Router**. Sie beendet **keine bereits angestoßene/queued Motorfahrt**. Die Freigabeverriegelung, Ausgänge-all-off, Motorreferenzierung und sichere Behandlung von Busausfällen müssen unabhängig durch KNX004/005/006/010 implementiert und später an Hardware geprüft werden. Ein Sicherheitsthermostat/Heizquellenschutz darf nicht durch den PI-Prototyp ersetzt werden.

## 4. Native Simulationsnachweise

Native Tests verwenden **die reale C++-Klasse** und den echten KNX008-C++-Router, aber **nur simulierte** Raumtemperaturen und Motor-Intent-Ausgaben:

- Kp/Ti/Deadband/Slew-/Sampling-Grenzen (ungültige Konfiguration gibt keinen gültigen Ausgang).
- Erstfreigabe ohne Zielwertsprung, maximale Stellwertänderung pro Minute.
- Gemeinsame Raumzone mit mehreren Heizkreisen; acht unabhängige Zonen und isolierter Fehler einer Zone.
- DirectPercent-Modus vs. RoomTemperature-Modus; frischer Eingang nach Moduswechsel erforderlich.
- Sensor-/Raumsollausfall, Sensorausreißer, Zeitstempelalter, explizites Recovery-Gate.
- ETS-Topologieänderung sowie Änderung von Kp/Ti oder RoomTimeout invalidieren alte Stellanforderungen.
- Sättigung bei 0/100 %, Anti-Windup und negative Rückführabweichung.
- Sensorrauschen innerhalb Deadband ohne Stellwertjagd; 32-Bit-millis-Überlauf.
- Deterministische Zwei-Raum-Toy-Plant (siehe unten).

### Künstliche 48-Stunden-Wärmemodellsimulation

**Modell-Annahmen – nicht gemessen:** Zwei Räume mit thermischer Zeitkonstante von 240 min, 17 °C fiktiver Außentemperatur, maximal 7,2 K Heizwirkung und 15 % gemeinsamem Durchfluss-/Wärmeabnahmeeinfluss. Je Minute ein simulierter externer Raum-Istwert. Für diesen Lauf Kp=200 Promille/K, Ti=7200 s, Slew-Limit=20 Promille/min. Z1 hat zwei Heizkreise (M1 und M2), Z2 einen (M3). Die Heizkreis- und Motor-Laufzeiten sind **nicht** modelliert.

| Kennzahl | Zone 1 | Zone 2 |
| --- | ---: | ---: |
| Starttemperatur | 18,0 °C | 18,5 °C |
| Raum-Soll | 21,5 °C | 20,0 °C |
| Raumtemperatur nach 48 h | **21,60 °C** | **20,10 °C** |
| Höchste berechnete Temperatur | 21,68 °C | 20,11 °C |
| Max. Stellwertsprung | 20 Promille/min | 20 Promille/min |

Die Simulation meldet **PASS** für Begrenzungen, gültige Zielwerte, Kopplung der M1-/M2-Zonenanforderung sowie plausible Grenzen dieses **einzelnen künstlichen** Szenarios. Das gilt ausdrücklich **nicht** als Beweis für Konvergenz in allen Fällen, hydraulischen Abgleich, stabile echte Temperaturregelung oder Heizungs-Sicherheitsfreigabe.

## 5. Wiederholbare Tests und offene Folgearbeit

Auf dem LLO Desktop Agent, aus dem Repo-Root:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_room_pi_controller.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx019_room_pi.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx008_zones.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx008_zone_contract.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py
    git diff --check

**Nicht in KNX019:** Produktgenerierung Version 3, ETS-Zonenparametrierung, busseitiges Raum-Soll-/Ist-Empfangen und Stellwerttelegramme, persistenter PI-Zustand, KNX-/Busschnittstellen-Recovery, hydraulische Modellkalibrierung, Frostschutzfunktionen und Motor-Steuer-/Homing-Safety.

**Wiederanlauf:** Full [KNX010](ROADMAP.md) erst nach gesonderter Scope-/ASH-Entscheidung und Hardware-/ETS-Gates. KNX016/009 bleiben deferred bis zur [eigenständigen KNX018-Testbench](KNX_TESTBENCH_PLAN.md). Ein weiterer Software-Only-Slice könnte einen deterministischen Motor-Queue-Simulator ohne GPIO vorbereiten, darf jedoch **nicht** die KNX004-Hardwarefreigabe vorwegnehmen.
