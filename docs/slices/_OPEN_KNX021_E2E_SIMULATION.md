# KNX021 – Virtuelle End-to-End-Integration PI -> Zonen -> Motorqueue

**Stand:** 2026-10-12
**Status:** OPEN, Gate 4/4 – Native Integration/Regression, Source/ASH/PCB QA PASS; Commits ausstehend
**Session:** ses-20261012T071430-429c2fad940b
**Owner:** ChatGPT-OpenKNXValveControl-KNX021-20261012
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Baseline:** 8dc7577 / main CLEAN, 22 lokale Commits vor origin/main

## Gate 1 – Checkup

- [x] LLO Desktop Agent online; vorheriger KNX020-Slice geschlossen, keine konkurrierende Write-Session.
- [x] Git main sauber, HEAD 8dc7577, keine _OPEN_-Marker.
- [x] KNX008-Zonenzuordnung, KNX019-PI und KNX020-Exklusivfahrqueue separat in nativen C++-Tests bestanden.
- [x] KNX002/003 As-built/Versorgung, KNX004–006 echte Motorfreigaben und KNX018 KNX-Testbench **nicht** durchgeführt; KNX009/016 ETS/Bustest deferred.

## Gate 2 – Decision

- Reiner OFFLINE-KNX021: zusammenhängender Referenz-Testpfad aus **realen KNX008/019/020-C++-Klassen** plus virtueller Motor-Backend-Simulation.
- Virtuelles Backend hält maximal eine belegt simulierte Motor-Ausgangsmaske, bestätigt START/STOP nur über nachvollziehbare tokenisierte ACKs und aktualisiert virtuelle Positions-Evidenz erst beim All-off.
- Wichtig: Ein vorzeitig gestoppter Antrieb verliert im Modell seine Positions-Referenz; bloßer Neustart oder veraltete Sollwerte dürfen keine Weiterfahrt erlauben, bis ein gesondert simulierter Re-Home-Evidenznachweis vorliegt.
- Auch bei Stop-Ack-Ausfall / nicht abgeschaltetem Backend blockiert die Queue alle anderen Motoren. Keine alten oder falsch getaggten ACKs akzeptieren.
- Eingangsfehler/Regler-Telegrammtimeouts aus KNX019/008 müssen beim aktiven Motor in ein STOP münden; keine neue Bewegung ohne explizite Re-Arm- und valide Quellen.
- Deterministischer, reproduzierbarer End-to-End-Test über mehrere Heizkreise/Räume mit mindestens einem Fault-Szenario, 32-Bit-Zeitüberlauf und Sicherheitseigenschaft **maximal ein belegter Motor**.
- Simulationswerte für Motorhub/Zeiten/virtuelle Temperaturführung sind Modellannahmen, keine realen Messdaten.
- **Kein** ETS XML/Header/KNX-Produkt-Update, kein GPIO, keine Motorbewegung, kein Firmwareflash, kein KNX-Live-Test, kein Push. KNX004 bleibt geplant.

## Gate 3 – Deliverables

- [x] Separate, portable virtuelle Motor-Feedback-Backend-Klasse (ausschließlich abstrahierte Ereignisse), keine GPIO-Anbindung.
- [x] End-to-End-native-C++-Tests mit KNX019 -> KNX008 -> KNX020 -> Mock-Backend einschließlich definierter Ausfall- und Wiederanläufe.
- [x] Test-Runner und unveränderte ETS-/Firmware-/PCB-Produktionsquellenprüfung.
- [x] Technische Dokumentation, Roadmap/README und KNX020-Querverweis.

## Gate 4 – QA / ASH-Abschluss

- [x] KNX021 native suites PASS; bestehende KNX008/019/020/013–015 Regression PASS.
- [x] Strikter Source-/ASH-/Markdownlink-/PCB-/ETS-Audit PASS.
- [ ] Scope/Whitespace prüfen und eigenen Implementierungscommit erstellen.
- [ ] HISTORY, Roadmap, Markerentfernung in separatem Closing-Commit; Git sauber.
- [ ] Session-Checkpoint und Close; keine automatische nächste Slice-Eröffnung.

## Next exact action

Implementierung des rein virtuellen Backends, vollständige Tests, Fail-Closed-Handling; anschließend Offline-QA und zwei lokale Commits. **Produktive GPIO-/KNX-Software unverändert lassen.**
