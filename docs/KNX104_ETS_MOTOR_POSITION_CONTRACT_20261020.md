# KNX104 – ETS V3 Stellwert-/Motorpositionsvertrag ohne KNX-Bus

Stand 20.10.2026. OpenKNXValveControl V1.2 / LLO Desktop Agent.
**Status:** Portable ETS-Schnittstelle implementiert; AppVersion3 weiterhin nur Entwurf. Keine reale KNX-Kommunikation oder Motorbewegung durch diesen Slice.

## Bestehende ETS-Basis

Die aktuelle Produkt-XML assets/open-knx-valve-control.xml hat **AppVersion2 und 35 Kommunikationsobjekte**. Die vorhandene KNX008-Planung assets/knx008_zone_ets_proposal.json reserviert KO36–100 und Parameter22–39 für eine geplante AppVersion3, die **noch nicht** in der Produkt-XML existiert. Diese Bereiche werden von KNX104 nicht überschrieben.

Wichtig: KO17–24 verwendet Legacy DPT **5.004**, nicht DPT **5.001**. Eine stille Umdeutung ist verboten. Der aktuelle Motor-Testaufbau hat keine unabhängig gemessenen Öffnungsprozente und keine bestätigte Zuordnung R/F = Öffnen/Schließen.

## Umsetzung

- lib/common/knx104_m1_ets_contract.hpp: Portable C++17-Brücke zwischen DPT5.001-Aufträgen, KNX099-Positions-Snapshot und vorgeschlagenen Statusobjekten. Ohne KNX-, Serial-, Arduino-, GPIO- oder Motor-Treiberzugriff.
- assets/knx104_motor_ets_preview.json: Aus KNX008 und aktueller AppV2-XML SHA256-gebundene, wiederholbar generierbare Vorschau für acht Zonen, acht Motoren und 17 neue Parameterideen.
- tools/knx104_ets_preview.py: Verifiziert AppVersion2/35 KOs, KNX008 Vorschlags-KO36–100 und Parameter22–39 sowie keine Kollisionen; Original-XML wird nicht editiert.
- tests/native/test_knx104_m1_ets_contract.cpp: 14 native C++17-Testgruppen mit MSVC /W4 /WX.
- tools/test_knx104_ets_preview.py: 11 Python-Unit-/Negativtests inklusive beschädigter KO-/Parameterliste und falscher ETS-Version.
- tools/knx104_verify.py: Vollständig offline wiederholbarer MSVC- und Python-Gesamttest. Build-Artefakte nur in C:\ASH\Workspace\Runtime\KNX104.
- src/controller/main.cpp: Header eingebunden, reine Compile-Time-Assertion. Keine Instanz des KNX104-Vertrags, keine Abonnements, keine Änderung am Motor-Hardlock, keine neue KNX-Aktion.

## Kommunikationsobjekte – bestehender AppV3-Entwurf

| Funktion | Motor/Zone 1 | Motor/Zone 8 | DPT | Richtung |
|---|---:|---:|---|---|
| Zone DirectDemand | KO38 | KO66 | 5.001 Scaling | RX |
| Motor EstimatedPosition | KO68 | KO75 | 5.001 **geschätzt** | TX |
| Motor Fault | KO76 | KO83 | 1.005 Alarm | TX |
| Motor Referenced | KO84 | KO91 | 1.002 Boolean | TX |
| Motor Moving | KO92 | KO99 | 1.001 Switch | TX |
| Device Motion Busy | KO100 | KO100 | 1.002 Boolean | TX |

Die Objektkennungen sind **keine Gruppenadressen**. Die Motor-Zonen-Zuordnung ist separat konfigurierbar und folgt nicht automatisch aus gleichem Index. Spätere Bus-Integrationen müssen die echte ETS-Gruppenadressbindung, Telegrammtyp GroupValueWrite und deklarierte DPT-Bindung prüfen; DPT selbst steht nicht als Typcode im Bus-Telegramm.

## Sicherheits-/Mapping-Vertrag

Die KNX099-Motorkoordinate ist F-Ende = interne 0 Promille und R-Ende = interne 1000 Promille. Es ist nicht bekannt, welcher Endpunkt das Ventil schließt. Der KNX104-Vertrag unterstützt deshalb zwei erst nach mechanischer Bestätigung verwendbare Settings: F_End_Closed und R_End_Closed. Default bleibt **Unconfirmed**.

Weitere Defaults: Modus Disabled, physicallyVerified=False, etsV3Commissioned=False und DirectDemand-TTL 300 Sekunden (Einstellbereich 10–3600 Sekunden).

Ein empfangener DPT5.001-Rohwert 0..255 darf nur als rein **softwareseitiger Zielvorschlag** in 0..1000 Promille übersetzt werden, wenn alle Gates erfüllt sind: korrekte ETS-Parametrierung und bestätigte reale Öffnungsrichtung, authentisch geprüfte GA/DPT-Zuordnung, GroupValueWrite mit 1-Byte-Payload, frischer Befehl, referenzierte KNX099-Motorposition, gültige unabhängige Output-Off-Rückmeldung und verfügbare Verbindung. Dieser Vertrag ruft nie eine reale Motor- oder KNX-API auf.

Ein falscher DPT5.004, schlechte Payload, ungültige GA-Zuordnung, Referenzverlust, Ablauf der TTL oder Konfigurationswechsel verwirft die Zielvalidität. Statusobjekte Fault/Moving/Referenced bleiben reine Vorschläge; eine 5.001-Öffnungsposition wird ohne bestätigte Zuordnung oder bei laufendem Motor/Fehler nie ausgegeben. Jede veröffentlichbare Zwischenposition bleibt als **TimedEstimate** markiert, niemals als unabhängig gemessener Encoder-Wert.

## Neue Parameterideen – ausdrücklich noch nicht importierbar

Der KNX104-Ausblick schlägt 40–47 (R/F physische Zuordnung pro Motor), 48–55 (acht Bestätigungsgates) sowie 56 (globale ETS-V3-Freigabe) vor. Alle Defaultwerte sind deaktiviert. **Alle ETS-Speicheroffsets bleiben UNALLOCATED**; die Werte dürfen nicht blind als fertige ParameterRefs oder .knxprod exportiert werden. Die bisherige echte XML und produktive .knxprod wurden nicht verändert.

## Prüf- und Hardwarestand

- C++17 Software-Kontrakt: **14/14 Testgruppen PASS**.
- ETS-Vorschau und Negativtests: **11/11 PASS**.
- Original-AppV2 und KNX008-AppV3-Entwurf passen zu den erwarteten Objektbereichen.
- KNX101 bleibt auf RP2040 COM7 installiert, KNX103 5/5 M1-USB-Fahrten abgeschlossen, Motor IDLE, GPIOs LOW, INA219 im letzten Check 0mA. Ohne neuen separaten Testauftrag keine zusätzlichen Motorfahrten.

Reproduzierbar auf dem LLO Desktop:

    python tools/knx104_verify.py

Die fehlenden Validierungsschritte sind: physische Bedeutung R/F am tatsächlichen Ventil, unabhängig vermessene Zwischenpositionen, realer ETS-AppV3-Export und KNX-Gruppenadress-End-to-End-Test. Solange das fehlt, darf keine produktive KNX-Ventilregelung behauptet oder aktiviert werden.

KNX104 ist für lokalen Commit und – auf ausdrücklichen Nutzerauftrag – Git-Push gemeinsam mit den noch ausstehenden zehn früheren Commits vorgesehen; kein Force-Push.
