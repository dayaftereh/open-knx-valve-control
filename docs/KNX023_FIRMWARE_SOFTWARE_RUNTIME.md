# KNX023 – Fail-closed RP2040-Regelpfad ohne Motor-Ausgänge

**Stand:** 12.10.2026. **Abnahmetyp: nur Software auf Host und isolierter RP2040-Firmware-Build. Keine neue KNX/ETS-Motorsteuerung, keine Motor-GPIO.**

## 1. Was tatsächlich eingebunden wurde

Der RP2040-Controller ruft nun – zusätzlich zu seiner seit KNX014/015 vorhandenen, separat unverändert bleibenden KNX-TP-/Temperatur-Telemetrie – die neue portable [RoomControlRuntime::Pipeline](../lib/common/room_control_runtime.hpp) auf. Sie verknüpft:

    KNX019 RoomPi::Bank
            |
            v
    KNX008 HeatingZone::resolve
            |
            v
    KNX020 MotorQueueSim::Queue
            |
            | Nur nativer Hosttest (NICHT ARDUINO)
            v
    KNX021 VirtualMotor::Backend (synthetische ACKs/Positionen)

Die Software-Pipeline läuft in der RP2040-Hauptschleife etwa alle **100 ms** und berechnet ausschließlich Zustände im RAM. Im tatsächlichen Controller-Build gilt eine **kompilierte harte Sperre**:

- Die Compiler-Definition ARDUINO verhindert das Einbinden des virtuellen Motor-Backends.
- armNativeSimulation gibt im ARDUINO-Build **immer false** zurück, unabhängig von scheinbar qualifizierten Bool-Sicherheitsflags.
- injectNativePosition gibt im ARDUINO-Build **immer false** zurück; der KNX020-Motorqueuezustand startet DISARMED und erhält in diesem Pfad niemals einen Arm-Aufruf.
- tick berechnet in der Firmware ausschließlich KNX019/KNX008 Stellintents, erzeugt aber keinerlei Start-/Stop-Event und schreibt keine GPIO-/PWM-/H-Brücken-Ausgänge.
- Die Firmware verarbeitet weiterhin die bestehenden Temperatursnapshots über Serial2, KNX über Serial1 und KNX015-Diagnose-/Temperaturtelegramme; diese Kommunikation wurde nicht umgedeutet.

**Defaultkonfiguration:** Alle acht Raumregler sind Disabled, alle Motor-Zuordnungen sind null, alle externen Raum-/Direktwerte invalid. Kein ETS-Adapter füttert diese Pipeline mit Daten, bis die KNX-KO-/DPT-Verträge in separaten Folge-Slices sauber entwickelt und mit echten ETS-Daten geprüft sind. Insbesondere ist KO17..24 aktuell DPT5.004 und DARF **NICHT** als bereits kompatibles DPT5.001-Sollwertsignal verstanden werden.

Die KNX023-Runtime liefert Diagnosen, berechnet virtuelle Stellwert-Intents und kompiliert im Controller. Sie ist **nicht** die endgültige KNX010-Regelung und keine implementierte physische KNX004-Motorsteuerung.

## 2. Was der native, synthetische Test zusätzlich darf

Nur in einem **C++-Hostprogramm ohne ARDUINO** kann man der Pipeline simulierte Motorpositionen/Vollhubzeiten, echte Software-PI- und KNX008-Zoneninputs sowie explizite Mock-Safety-Flags übergeben. Dann verifiziert der Testscheduler die KNX020-Exklusivitätsregel gegen den KNX021-in-memory Motorbackend-Simulator. Dieses Test-Backend ist weder mit einem realen GPIO noch mit der KNX-Telemetrie verbunden.

**Testszenarien:**

| Szenario | Erwartetes Ergebnis |
| --- | --- |
| RP2040-/Runtime-Reset | DISARMED, keine Sensor-/Positionshistorie und keine Motorfreigabe |
| Zwei Heizkreise in Raum 1 per synthetischem Direkt-DPT5.001 | Jeweils 502 Promille Sollwert, Starts ausschließlich nacheinander |
| Ein Heizkreis in Raum 2 per KNX019 PI | Synthetischer 2300/1900-CentiC-Raumregler liefert zuerst 30 Promille |
| Drei Testmotoren mit ACK-Protokoll | 3 synthetische Starts, 3 bestätigte All-off-ACKs, M1/M2/M3 virtuell 502/502/30 Promille |
| Ausfall einer Direktdatenquelle während der simulierten Fahrt | STOP-Anforderung, kein zweiter Start ohne Stop-Off-ACK; Fehlreferenzierung führt zu manueller Re-Home-Pflicht |
| ACK-Ausfall nach STOP | Verriegelter StopAckTimeout; Lease bleibt blockiert; Fehler löst nicht automatisch einen neuen Start aus |
| Synthetisch verlorenes Power-Good vor Arm | Arm verweigert, obwohl gültige Sollwerte vorhanden sind |
| Zweiter Build mit Compilerflag ARDUINO | 100.000 ms virtuelle Tick-Tests, Arm dauerhaft false, Positionsinjektion false, keine Motor-Start-/Stop-Events |

Die Zahlen sind **fiktive Test-Sollwerte**, keine Messwerte einer realen Wohnung oder der HmIP-VDMOT-Antriebe. Ein synthetisch beendeter Motorlauf beweist keine Endlage und keine unabhängige elektrische Abschaltung.

## 3. Reproduzierbare Tests und Quellen

| Datei | Zweck |
| --- | --- |
| [room_control_runtime.hpp](../lib/common/room_control_runtime.hpp) | Portable Software-Koordinierung mit compile-time ARDUINO-Hardlock |
| [Firmware-Main](../src/controller/main.cpp) | Inert initialisieren und alle 100 ms RAM-Pipeline ticken lassen; keine KNX-/Motor-GPIO-Aktionen |
| [Host-Integration](../tests/native/test_knx023_room_control_runtime.cpp) | KNX019/008/020/021 zusammengesetzt mit Mock-Positionen, ACK/Fault und Reboot |
| [Arduino-Hardlock-Test](../tests/native/test_knx023_firmware_hardlock.cpp) | Compiliert ARDUINO-Pfad ohne Geräteheaders und versucht erfolglos Simulation zu armieren |
| [Nativer Runner](../tools/test_knx023_room_control_runtime.py) | Beide Tests mit C++17, -Wall -Wextra -Werror -pedantic |
| [Produkt-Audit](../tools/audit_knx023_firmware_offline.py) | Schützt KNX-/ETS-Produkt/PCB/ATtiny und verbietet zusätzliche Motor-API-Aufrufe |

Vom Projektroot aus:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx023_room_control_runtime.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx023_firmware_offline.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\build_controller_isolated.py --keep
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py

Der isolierte Firmware-Build findet **nicht** im kanonischen Repository statt, weil der OpenKNXproducer-Pre-Script sonst generierte knxprod.hpp-Dateien überschreibt; Tests und Build laufen in einem temporären Duplikat ohne Boardzugriff.

## 4. Laptop-Teststand als separater KNX018-Aufbau

Der beabsichtigte USB-/LAN-/UPDI-/1-Wire-/Motoranschluss ist erstmals in einer eigenen [KNX018 Laptop-/UPDI-Testbench-Verkabelungsdatei](KNX018_LAPTOP_UPDI_TESTBENCH.md) mitsamt den Unit-Programmer-V1.2-Quellen und der CN1.1-USB-5-V-Rückspeisegefahr dokumentiert.

Der tatsächliche Laptop wurde noch **nicht** auf die 26 lokalen Desktop-Commits migriert, es wurde kein Programmer elektrisch verbunden und kein UPDI-Chip erkannt. KNX018 Aufbau, KNX002/003 elektrische Qualifikation, KNX004–006 Motor-Safety/Homing, KNX009/016 echte KNX-/ETS-Tests bleiben unabgenommen.

**Schlussfolgerung:** KNX023 ist ein Software-Integrationsschritt, **keine** Freigabe für einen realen Motortreiber oder eine Migration der ETS-Hauptanlage.


## 5. KNX023-Abnahme vom 12.10.2026 (nur Firmware-Build und Offline-Tests)

- **RP2040 PlatformIO isolated controller build: PASS**. Der OpenKNXproducer lief im separaten Build-Root C:\Users\LLO\AppData\Local\Temp\openknx-controller-isolated-bi62ip4j. Eine firmware.uf2 wurde generiert. Kein Board angeschlossen/geflasht, Originaldatei include/knxprod.hpp per SHA256 unveraendert.
- **RAM 53.452 / 262.144 Bytes = 20,4 %**, **Flash 192.708 / 1.048.576 Bytes = 18,4 %**. Werte nur fuer diesen isolierten Build.
- **KNX023 native 2/2 PASS**: synthetische PI/Zonen/Queue/Stop-ACK-Kette; Arduino-Preprocessor-Hardlock verhindert Arm/Positions-Injektion und jedes Motor-Event.
- **Vorherige 12 native C++ Testsuites PASS**: KNX008 1, KNX019 1, KNX020 2, KNX021 1, KNX013 2, KNX014 4 und KNX015 2: Summe **13** vor KNX023, **15** inklusive der 2 neuen KNX023-Suites. (Die 13 umfasst die zwei KNX020-Suites.)
- **KNX023 strikt keine neuen I/O-Ansteuerungen PASS**, ETS-Produkt-KO/Parameter und PCB/ATtiny-Master unveraendert; KNX008 vorgeschlagener ETS-Contract PASS; KNX015 Produktversion2 ABI PASS, Design-Audit 0 Invariant-Fails.
- **KNX022 erneut als LIVE-Quellenaudit ausgefuehrt:** 35 statische Invarianten PASS und weiterhin BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR mit 10 offenen Risiken. Das historische KNX022-JSON enthaelt Quell-Hashes vor diesem KNX023-Main-Update und ist als **Snapshot** zu verstehen; --check-report gegen den neuen Main-Hash ist deshalb nicht die richtige Neuabnahme. Keine physische Freigabe.
- ASH 30 Checks mit 396 Markdown-Links vor dem Closing PASS, keine unkontrollierten Hardware-/ETC-Operationen.

Die erstellte UF2 ist ausschliesslich ein nachgewiesenes Buildartefakt in einem temporaeren Verzeichnis, **keine geflashte/abgenommene Firmwareversion**.
