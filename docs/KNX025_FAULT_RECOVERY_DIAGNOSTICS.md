# KNX025 – Fehlerbehandlung, Wiederanlauf und Softwarediagnose

**Stand:** 12.10.2026. **Ausschließlich portable Software-/Firmwareintegration, NICHT elektrische Sicherheitsfreigabe.** Die KNX025-Überwachung benutzt keine echten H-Brücken-, KNX/IP-, UPDI- oder GPIO-Befehle. Ein getesteter Software-Fault oder eine simulierte All-off-Quittung beweist keine Schutzfunktion der realen V1.2-Leiterplatte.

## 1. Einordnung im KNX-Regelungsstack

KNX025 baut auf den abgeschlossenen Software-Schritten [KNX008](KNX008_ZONE_CHANNEL_DESIGN.md), [KNX019](KNX019_ROOM_PI_SIMULATION.md), [KNX020](KNX020_MOTOR_QUEUE_SIMULATION.md), [KNX021](KNX021_END_TO_END_SIMULATION.md), [KNX023](KNX023_FIRMWARE_SOFTWARE_RUNTIME.md) und [KNX024](KNX024_ETS_ROOM_INPUT_CONTRACT.md) auf:

    Vorgeschlagene V3 GroupValueWrite KOs36..67
              |   Raum-Soll/Raum-Ist DPT9.001 oder direkt DPT5.001
              v
       KNX024 typed Offline-Adapter
              |
              v
       KNX025 Fehler-/Frische-/Recovery-Vorprüfung
              |
              +--- bei Fault: Eingänge leeren, native Queue cancel,
              |               STOP wiederholen bis tokenized ACK
              |
              v
       KNX019 PI -> KNX008 Zone Targets -> KNX020 Queue
              |                              |
              |       ausschließlich NATIVER TEST-HOST
              +------------------------------v
                                  KNX021 VirtualMotor Mock
                                  (NICHT echte Hardware)

    RP2040-Produktiv-AppV2:
       KNX023 RAM-only Tick + KNX025 PASSIVER Beobachter,
       NO real V3 KO RX, NO motor actuators, ARDUINO compile-hardlock.

Der [portable Faultsupervisor](../lib/common/knx025_fault_supervisor.hpp) enthält die Fault-/Diagnose-/Wiederanlaufregelung. [src/controller/main.cpp](../src/controller/main.cpp) bindet den Header in die tatsächlich kompilierbare RP2040-Firmware ein, initialisiert nur RAM-Zustände und ruft im bisherigen 100-ms-Pfad **observeFirmware()** auf.

**Auf der echten Firmware wird absichtlich keine neue room-KNX-Busverbindung erzeugt.** Die bestehenden 35 Kommunikationsobjekte der ETS-Version 2 enthalten keine vorgeschlagenen V3-Raumeingänge. Erst nach neuer KNX018-Testbench/ETS-GA-Abnahme kann eine echte typisierte KO-Bindung in einem gesonderten Slice beginnen. Deshalb darf die aktuelle passive Beobachtung **nicht** als vollständig aktiver Motor-Faultschutz bezeichnet werden.

## 2. Klare Diagnosephasen und Fehlercodes

| Softwarezustand | Bedeutung | Neue Motorfreigabe |
| --- | --- | --- |
| Unconfigured | Nach Boot oder Softwarequittierung; keine V3-Modus-/Zonen-Konfiguration | Keine |
| WaitingForFreshInputs | Konfiguration gültig, aber mindestens einem zugeordneten aktiven Raum fehlt noch der vollständige frische Eingangssatz | Keine aus der fehlenden Zone |
| HealthySoftwareInputs | Alle zugeordneten aktiven Zonen haben derzeit gültige frische Eingangsdaten | Nur synthetischer Host-Test; auf Arduino weiterhin **permanent DISARMED** |
| FaultLatched | Erster kritischer Fehler dauerhaft mit Grund, Zeitpunkt und 1-basierter Zone gespeichert; spätere Telegramme reaktivieren nichts | Keine; native Mock-Queue fordert STOP und wartet auf Matching-Off-ACK |

**Kritische Fehler:** InvalidConfiguration, InvalidRoomTelegram, RoomSourceExpired, DirectDemandExpired, RoomTransportLost, SoftwareLoopStalled, SoftwareConfigurationChanged, MotorQueueFault, MockBackendProtocolFault und OperatorEmergencyStop. Das jeweils **erste** Fault-Ereignis bleibt bis zum ausdrücklichen erfolgreichen Wiederanlauf sichtbar.

Das Diagnoseobjekt enthält unter anderem firstFaultZone (0 global oder 1..8), firstFaultAtMs, Zähler der Fault-Epochen/erfolgreichen und verweigerten Recoveries, Softwaretickzahl und letztes Tickdatum, erwartete/ehemals gültige/aktuell frische Zonemasken, beobachteten virtuellen Queue-Zustand, Queue-Fault und Lease-Maske. Das Feld physicalOutputsVerifiedOff ist bewusst **immer false**.

**Sekundäre Warnung:** manifoldTelemetryWarning wird gesetzt, wenn ein bereits erkannter T0..T8-Datentransport auf dem ATtiny-/RP2040-UART nicht erreichbar ist. Die Messwerte T0 Vorlauf und T1..T8 Rücklauf sind **KEINE Raumluft-Isttemperaturen**. Diese Warnung sperrt deshalb eine ansonsten valide externe Raumregelung **nicht automatisch**; sie taugt nur zur Diagnose der Verteiler-Temperaturmessung.

## 3. Sicherheitsverhalten bei Fehlern

1. **Boot:** Ohne ETS-V3-Konfiguration ist Unconfigured ein normaler Zustand, kein Fehlalarm. Die reale Controller-Firmware bleibt ohnehin ARDUINO-DISARMED. Alle vorherigen Eingangs- und synthetischen Positionsdaten sind beim Software-Reboot ungültig.
2. **Eingangsfrische:** In einer aktiv zugeordneten Zone muss DirectPercent einen frischen DPT5.001-Wert besitzen, oder RoomTemperature braucht **beide** gültigen DPT9.001-Raum-Kanäle. Vor dem allerersten gültigen Satz ist WaitingForFreshInputs normal; geht nach erfolgter Gültigkeit eine Quelle verloren, folgt ein **sticky** Zone-Fault. Für ungültige bekannte Telegramme erfolgt die Sperre sofort vor dem nächsten Motorqueue-Tick.
3. **KNX-Quellenverlust:** Der simulierte/vertrauenswürdige roomTransportMonitored-Status ist **nicht** dasselbe wie knx.configured(), der TemperatureBridge-online-Status oder das bloße Vorhandensein einer IP-Adresse. Sobald ein als überwacht markierter KNX-Raumeingang explizit offline ist, wird **vor einem möglichen neuen Start** gesperrt – auch beim ersten Steuerungstick. Bei nicht vorhandener, bislang ungeprüfter KNX-Raumüberwachung wird kein Verbindungsstatus erfunden.
4. **Verpasster Software-Tick:** Überschreitet der zeitliche Abstand zweier beobachteter Tickaufrufe 2.000 ms, setzt KNX025 SoftwareLoopStalled. Die Rechnung funktioniert über uint32-millis-Rollover. **Das ist KEIN aktiver RP2040-Hardware-Watchdog:** Wenn der Loop hängt, stellt dieser C++-Code weder Hardwareausgänge ab noch startet er unabhängig einen Watchdog. Er kann den Zeitfehler erst nach Wiederaufnahme der Ausführung erkennen.
5. **Queue-Störung:** Ein virtueller ACK-Timeout, FaultLatched oder Protokollfehler bleibt sperrend. KNX025 leert die bisherigen Software-Intents, setzt in nativen Tests die KNX020-Cancel-Anforderung und lässt die Queue ihre tokenisierte STOP/AllOff-Antwort selbst verarbeiten. **Niemals eine aktive Lease durch Reset freigeben.**
6. **Weitere Fehler:** Externe Konfiguration, die nachträglich ohne kontrollierte Re-Konfiguration verändert wird, erzeugt SoftwareConfigurationChanged, auch wenn nur ein Zeitparameter geändert wurde. Das Altdaten-Übernehmen über einen Modus- oder Motor-Zonen-Wechsel ist verboten. Ein explizites manuelles Stop-Signal sperrt ebenfalls.

## 4. Wiederanlaufregelung

Nach einem Fault wird eine neue synthetische Room-KNXTabelle **nicht einfach wieder akzeptiert**. Es gelten alle folgenden softwareseitigen Bedingungen:

- Das Fault-Latch ist aktiv und eine **ausdrückliche** operatorAcknowledgement wurde übergeben; ein nackter neuer Raumtelegrammempfang ist nicht ausreichend.
- Ein optional überwachter Raum-Transport muss wieder als online beobachtet worden sein; eine noch aktive manuelle Not-Stopp-Anforderung verhindert Quittierung.
- Im nativen Motor-Simulator existiert **keine ausstehende Motor-Lease** und kein aktiver Start-/Running-/StopPending-Zustand. Der virtuelle Backend meldet null belegte Kanäle und keine Protokollverletzungen. Solange ein STOP-AllOff-ACK fehlt, bleibt die Lease gesperrt, auch wenn der Fehler seit Sekunden besteht.
- Erst dann setzt KNX025 **nur Software-RAM** zurück, invalidiert PI/Targets/Positionsevidenz und die alte V3-Konfiguration. Danach sind **eine neue ausdrücklich geprüfte P22..39-Konfiguration** und **frische Telegramme** erforderlich. Ein Motor kann dadurch nicht automatisch wieder anlaufen.
- KNX023s ARDUINO-Compile-Gate lehnt armNativeSimulation() und injectNativePosition() unverändert ab, unabhängig von einem erfolgreichen Supervisor-Softwareack.

**Keine dieser Softwarebedingungen ersetzt den erforderlichen unabhängigen Hardware-AllOff-Nachweis.** An V1.2 hängen die TB6612-Standby-Pins weiterhin permanent an 3,3 V. Die Sicherheit echter Motoren hängt von KNX002/003/004/005/006, einer qualifizierten Stromversorgung und eigener messtechnischer Freigabe ab.

## 5. Testumfang und Nachweise

| Dateipfad | Prüfung |
| --- | --- |
| [knx025_fault_supervisor.hpp](../lib/common/knx025_fault_supervisor.hpp) | Faultcodes, Zustände, sticky first-fault, Zeit-/Quellen-/Konfigurations-Guard, Softwaretick, Diagnose-Masken, Quarantäne/ACK-Recovery, ARDUINO-Passivbeobachter |
| [test_knx025_fault_supervisor.cpp](../tests/native/test_knx025_fault_supervisor.cpp) | Normaler Boot ohne ETS, beide Steuerarten, PI-Raumdatenverlust und falsches 0x7FFF, DPT5.004-Mismatch, 30s Direkt-/Raumtimeout, KNX-Transport bei erstmaligem OFFLINE, Manifold-Warnung separat, 32-bit-Wrap und 2s-Softwaredeadline, simulierte Start-/Stop-ACK-Verluste mit Lease-Sperre, ETS-Konfigurationswechsel bei aktiver virtueller Lease, manueller Stop und Recovery |
| [test_knx025_firmware_hardlock.cpp](../tests/native/test_knx025_firmware_hardlock.cpp) | Kompiliert mit ARDUINO-Definition und beweist, dass eine gültige synthetische Stellanforderung plus fünf scheinbar qualifizierte Simulation-Flags keinen Motorstart aktivieren können |
| [test_knx025_fault_supervisor.py](../tools/test_knx025_fault_supervisor.py) | Strenge C++17-Host-Builds -Wall -Wextra -Werror -pedantic in temporärem Verzeichnis |
| [audit_knx025_fault_scope.py](../tools/audit_knx025_fault_scope.py) | Produkt-/ATtiny-/PCB-/KNX008…024-Quellschutz, nur additive Main-Änderung, keine GPIO-/KNX-KO-/echte Hardware-Watchdog-Funktion |

Testbefehle im Repository-Root auf dem Desktop-Agent:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx025_fault_supervisor.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx025_fault_scope.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx024_room_dpt_adapter.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx023_room_control_runtime.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\build_controller_isolated.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py

Ein isolierter PlatformIO-RP2040-Firmware-Build erzeugt lediglich eine UF2-Datei unter dem temporären Build-Root, **flasht diese aber nicht**. Die ETS-V2-Produktdaten KO1..35/P1..21 einschließlich DPT5.004-KO17..24 werden nicht verändert; die zusätzlichen V3-KOs36..100 bleiben weiterhin lediglich die ursprüngliche KNX008-Offline-Proposal.

## 6. Nächster physischer Gate-Schritt

[KNX018 Laptop KNX-/RTS-UPDI-Teststand](KNX018_LAPTOP_UPDI_TESTBENCH.md) enthält den späteren Plan des Nutzers: USB-RP2040, USB/RTS-Programmer zur ATtiny-UPDI/UART-Umschaltung, einzelne DS18B20-T0..8-Sensoren, KNX/IP in einem getrennten Busnetz und erst nach Spannungs-/Pegel-/AllOff-Freigaben ein einzelner Motor an M1. Der Laptop ist noch nicht aufgebaut und die Desktop-Commits sind noch nicht dorthin migriert. KNX009/016 ETS6-/Busabnahmen sind bewusst deferred.

**KNX025 ist bis zur realen elektrischen Prüfung eine vertrags- und diagnosesichere Offline-Softwareweiterentwicklung, kein Sicherheitssteuergerät.**
