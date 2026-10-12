# KNX008 – ETS-Zonen-/Heizkreismodell und Moduskontrakt

**Stand:** 2026-10-12
**Status:** OPEN, Gate 4/4 – Implementierung und Native-/ETS-/ASH-Qualitätsprüfungen bestanden, Commit ausstehend
**Owner:** ChatGPT-OpenKNXValveControl-KNX008-20261012
**Session:** ses-20261012T061346-f91558196616
**Root:** C:\ASH\Workspace\Projects\open-knx-valve-control
**Git baseline:** `c171d17`, `main` clean, 16 lokale Commits ahead origin/main
**Profile:** Software-/ETS-*Entwurf* (ohne ETS-Import, Hardware oder Firmwareflash)

## Gate 1 – Checkup (PASS)

- [x] LLO Desktop Agent online; alle vorangegangenen Sessions geschlossen, kein konkurrierender Write-Owner.
- [x] Git clean, kein `_OPEN_*.md`-Marker; KNX017 wurde formal geschlossen.
- [x] KNX015 XML ist ApplicationVersion 2: 35 KOs und 21 Parameter. KO25..33 liefern die Verteiler-Temperaturen T0..T8; KO34..35 sind UART-/Sensorqualitätsdiagnosen.
- [x] KO1..8 Solltemperatur, KO9..16 Isttemperatur pro *Antrieb*, KO17..24 Stellwert DPT **5.004**. Diese sind **kein** fertiger 8-Zonen-Regelungsvertrag.
- [x] KNX016/009 sind vom Nutzer zurückgestellt und benötigen später einen **eigenständigen KNX-/Controller-Testplatz** (KNX018).

## Gate 2 – Decision / Scope

- **Maximal acht logische Zonen (Räume)**, maximal acht physische Motoren M1..M8.
- **Je Motor genau eine Zuordnung:** Zone 0 = nicht zugeordnet, Zone 1..8; beliebig viele Motoren dürfen dieselbe Zone teilen. Ein Motor darf nie gleichzeitig zwei Zonen bedienen.
- **Zone-Modi:** 0 = deaktiviert, 1 = Raumregelung Soll-/Ist-Temperatur über **externe KNX-Raumfühler**, 2 = direkter KNX-DPT5.001-Stellwert von 0..100 %. Der lokale T0..T8-Fühlerpfad misst Vor-/Rücklauf, **keine** Raumtemperatur.
- Die noch **nicht implementierte** Regelung KNX010 erzeugt erst aus Soll-/Ist und Reglerzustand einen zonenweisen Positionswunsch; KNX008 darf keinen vermeintlichen PI-Regler vortäuschen.
- Ein reiner, hardwareunabhängiger Zonenrouter darf bereits den zonenweisen Zielwert auf alle zugehörigen Motoren auffächern, **nur** wenn Mode, Datenfrische und Aktivierung gültig sind. Keine Motor-PWM, kein KNX-Senden.
- **ETS-ABI nur vorschlagen:** KO1..35 und P1..21 bleiben unangetastet; Entwurf neuer Namen/DPTs/KOs ab 36 sowie Parameter ab P22, potenzielle ApplicationVersion 3 **nur für den späteren Implementierungsslice**. Kein produktives XML-/Header-Update in KNX008.
- Fail-safe: ungültige Konfigurationen, unzugewiesene/ausgeschaltete Zonen, fehlende/stale Eingaben führen zu **keiner neuen Fahranforderung**. Das ist **keine** bereits implementierte physische All-off-Schutzfunktion (KNX004).
- HmIP-VDMOT: kein Strom-/Endlagenschwellwert ohne Messung; nur eine Motorfahrt gleichzeitig wegen gemeinsamer Richtungssteuerung und INA219 (KNX004/005/006).
- **Keine** ETS6-Importversuche/Downloads, KNX-Bustests, Motorbewegung, Stromversorgungsänderung, physische Platinenaktionen, GitHub-Push.

## Gate 3 – Implementation

- [x] Dokumentation ETS-Nr./DPT/Parameter/Mode, Konflikt- und Migrationsregeln.
- [x] Maschinenlesbarer *Proposed-only*-ETS-Kontrakt, Referenzvergleich mit live XML.
- [x] Hardwareunabhängiger Zonenzuordnungs- und Zielwertrouter mit Native-C++-Tests.
- [x] README/Roadmap und genaue Übergabe an KNX009/010.

## Gate 4 – Validation / Close

- [x] Native-Zonen-Mocktests: 1/2/3/4-fach Gruppe, verschiedene Räume, disabled, stale, Mode/Prozent-Skalierung, Parametergültigkeit.
- [x] JSON-/ETS-Kontrakt-Audit gegen kanonische V2 XML, KO1..35/P1..21 unverändert und Vorschlags-IDs eindeutig.
- [x] ASH-Workflow, PCB/ETS static, Markdown-Links und `git diff --cached --check`.
- [ ] Implementierungscommit; HISTORY/Roadmap und Markerentfernung im separaten Closing-Commit.
- [ ] Git clean, Checkpoint, Session schließen; KNX009/016 weiter deferred; kein Push.

## Next exact action

Nur KNX008-Dateien stagen, gestagten Whitespace-Audit ausführen und den Implementierungscommit speichern. Danach HISTORY/ROADMAP aktualisieren, Slice-Marker in separatem Closing-Commit entfernen und Session-Checkpoint schließen. **Nächsten Slice nicht automatisch eröffnen.**
