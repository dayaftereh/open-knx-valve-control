# Eigenständige KNX-Testumgebung – zurückgestellter Integrationsnachweis

**Stand:** 2026-10-12
**Status:** Konzept / **nicht aufgebaut**, kein realer Bus-, ETS6- oder Platinenfunktionstest erfolgt.
**Bezug:** [KNX015](KNX015_TEMPERATURE_PUBLISH.md), [KNX016/018 in der Roadmap](ROADMAP.md), [Stromversorgungskonzept](POWER_SUPPLY_CONCEPT.md), [As-built- und Safety-Gates](ROADMAP.md).

## Entscheidung

Der ETS6-Produktimport KNX016 und alle physischen KNX-Bus- und UART-Tests werden **bewusst verschoben**. Der bisherige LLO Desktop Agent bleibt für Repositorypflege, Builds und simulierte Tests verfügbar, wird aber **nicht** zum endgültigen KNX-Hardwaretestplatz.

Die neue Testumgebung soll eine vom Desktop-Agent unabhängige Installation mit eigenem Zugang, lokaler KNX-Verbindung und der echten OpenKNXValveControl-Platine sein. Der Zeitpunkt des Aufbaus ist offen. Die Datei ist eine Anforderungsliste, keine vorhandene Installation oder Hardwarefreigabe.

## Zielbild

```text
Dedizierter ETS6-/Test-Rechner (Windows)
  |-- isoliertes ETS6-Testprojekt / versionierte .knxprod
  |-- reproduzierbare Testskripte, Logger, Git-Stand und Protokolle
  |-- KNX/IP-Interface oder KNX-USB-Interface
       |
       +-- eigener, fachgerecht versorgter KNX-TP-Testbus
            |
            +-- OpenKNXValveControl V1.2 Platine
                 |-- KNX-Transceiver / RP2040
                 |-- ATtiny3216 -- 1-Wire T0..T8
                 |-- Motortreiber: im Temperaturtest AUS / gesperrt
```

Ein dedizierter ETS6-/Testrechner ist eine **Planungsanforderung**, nicht die Behauptung, dass er eingerichtet wurde. Eine KNX/IP-Verbindung muss auf dem vorgesehenen lokalen Netz getestet werden; automatische IP-Discovery kann über VPN oder unterschiedliche Interfaces scheitern. KNX-USB ist als Alternative möglich.

## Voraussetzungen vor dem ersten echten Test

| Bereich | Voraussetzung | Status |
| --- | --- | --- |
| Test-Rechner | Gesonderte Windows-Testumgebung mit ETS6-Lizenz/Projekt, kontrollierten Zugriffsrechten und Logs | Offen |
| KNX | KNX-TP-Busversorgung und geeignete KNX/IP- oder KNX-USB-Schnittstelle, Testbus vom produktiven Haus getrennt | Offen |
| Platine | V1.2 physisch vorhanden, Stückliste/Bestückung U25 und Shunt R29 sowie Pin-/Versorgungspfad geprüft (KNX002) | Offen |
| Niederspannungsversorgung | KNX-Versorgung und gegebenenfalls 5-V-/3,3-V-Zweige elektrisch qualifiziert, ohne ungewollte Rückspeisung (KNX003) | Offen |
| Firmware | ATtiny/RP2040 mit dokumentierten Versionsständen, Flash-/Restore-Möglichkeit; zunächst nur Temperaturfunktion | Offline Builds bestanden; Flash offen |
| Sensoren | T0 zentraler Vorlauf, T1–T8 Rückläufe; mindestens ein bekannter Testfühler plus Fehlerszenarien | Reale Testmittel offen |
| Sicherheit | Alle acht Motoren unbestromt; keine Endlagenfahrt ohne KNX004/005/006-Abnahme | Pflicht |

**Nicht an den Haus-KNX-Bus oder an Antriebe gehen, bevor** die realen Versorgungs-/Strompfade und mögliche Rückspeisung geklärt sind. Eine bestehende ETS-Projekt-/Gruppenadresskonfiguration bleibt unangetastet.

## Vorgeschlagene Abnahmereihenfolge

1. **ETS6 isoliert:** Produkt Version 2 aus [Produkt-XML](../assets/open-knx-valve-control.xml) / `.knxprod` in ein neues Testprojekt importieren. Vorheriges ETS-Produkt nicht überschreiben. P19 (Temperaturen), P20 (Intervall), P21 (Änderungsschwelle) prüfen, Kommunikationsobjekte 25–35 samt DPT und Sichtbarkeit prüfen. Importfehler/Versionierung protokollieren.
2. **Testbus passiv:** KNX-Schnittstelle erkennen und im ETS-Busmonitor testweise lesen; noch kein Download auf einen produktiven Teilnehmer. Telegramme/physikalische Adresse/Interface-Zuordnung nachvollziehbar protokollieren.
3. **Platine ohne Motorbetrieb:** Versorgung im sicheren Aufbau abnehmen, beide Controller identifizieren und funktionierende Programmier- sowie UART-Strecke bestätigen. Nur mit Hardwarefreigabe flashen.
4. **Temperatur-End-to-End:** Einen plausiblen Sensorwert sowie gültige 0 °C und negative Werte prüfen; Sollmeldung auf KO25–33 als DPT 9.001 im ETS-Busmonitor nachweisen. Nur als tatsächlich gemessen deklarieren, wenn die echte 1-Wire-/UART-Strecke beteiligt ist.
5. **Diagnose:** Sensor abziehen und wieder anschließen, CRC-/UART-Ausfall und Timeout getrennt prüfen. KO34 (Link online) sowie KO35 (T0..T8 Gültigkeitsmaske) kontrollieren; keine künstlichen 0-°C-Telegramme und keine ungültigen Werte als aktuelle Messung senden.
6. **ETS-Parameter:** P20=60 s und andere zulässige Intervalle, P21=0 und definierte Änderungsschwellen, P19 Ein/Aus sowie die minimale Telegrammpause prüfen. Laufzeiten und Busmonitor-Logs archivieren.
7. **Spätere Motor-Gates:** Erst nach KNX002–006 die Antriebskette und Endlagenerkennung am Motor untersuchen. Diese **nicht** als Bestandteil der Temperatur-ETS-Abnahme ausführen.

## Verbindliche Dokumentationsartefakte beim späteren Aufbau

- Aufbauplan mit Stromversorgung, Bus-Schnittstelle und konkreten Kabel-/Pinverbindungen.
- Konfigurationsdateien und Versionen von ETS6, Schnittstellentreiber, Boardfirmware, KNX-Produkt und Testprojekt.
- Eindeutige Test-Gruppenadressen (nicht die aus dem produktiven Hausprojekt).
- ETS-Busmonitor-Protokolle, Testergebnisse zu Sensoren/Timeouts und verwendeter Git-Commit.
- KNX-Flash/Download nur nach expliziter Laborfreigabe; kein automatischer Produktionsrollout.

## Was bis dahin sinnvoll weitergeht

**KNX008 – ETS-Zonen-/Heizkreis-Architektur ist softwareseitig abgeschlossen.** Die [Zonen-/Regelmodus-Spezifikation](KNX008_ZONE_CHANNEL_DESIGN.md) und der reine C++-Router sind getestet, mit vorgeschlagenen KNX-Objekten und Parametern. Zusätzlich ist [KNX019 – PI-Regler-Simulation](KNX019_ROOM_PI_SIMULATION.md) als offline Modell vorbereitet, ohne Änderung an der produktiven Motor-/KNX-Firmware. Das bedeutet ausdrücklich **keinen ETS6-Import oder reale KNX-/Motorintegration**.

Der bestehende Slice KNX016 bleibt **deferred** und ohne `_OPEN_`-Datei. Für den separaten Hardware-/ETS-Testplatz wird KNX018 als geplanter Aufbau geführt. KNX008 ist als ASH-Design-Slice abgeschlossen; spätere Umsetzung in produktive ETS-XML, Raumregler- und Motorfirmware erfordert separate ASH-Slices und Testfreigaben.
