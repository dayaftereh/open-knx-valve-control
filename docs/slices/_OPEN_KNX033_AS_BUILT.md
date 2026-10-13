# KNX033 – V1.2 As-built-Fotos, D1-Bypass und Power-On-Sperren

**State:** open
**Gate:** 2/4 (Live-Check und Scope entschieden)
**Profil:** Hardware-Evidenzaufnahme, ausschließlich Offline-Analyse
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX033-AsBuiltPhoto-20261013 / `ses-20261013T141743-96548d3fafec`
**Projekt:** `C:\_myspace\workspace\open-knx-valve-control`
**Basis-Git:** `7d8f835`, `main` CLEAN, 13 lokale Commits vor `origin/main`, keine konkurrierenden Sessions.

## Gate 1 – Quell- und Fotoabgleich

- [x] Drei Benutzerfotos `20261013_160055.jpg`, `20261013_160046.jpg`, `20261013_160042.jpg` im Chat erhalten; **Originale NICHT im LLO-Home-Repository**. Fotozeitstempel sind Dateinamen, keine geräteseitig verifizierten Zeitdaten.
- [x] Auf Bestückungsseite sichtbar: V1.2-Silkscreen, USB1, U18 RP2040, U25 Atmel im 20-poligen Gehäuse, 4 TB6612 U34/U36/U37/U35, U23 INA219, R29 Shunt-Gehäuse, L1, F1, D1-Ersatzdraht sowie JMP1/JMP2/JMP3-Lötstellen. U6 TRACO im Foto dieser Seite **nicht zweifelsfrei als Baugruppe sichtbar**; Rückseite anfordern.
- [x] Nutzermeldung: JMP1 geschlossen, JMP2/JMP3 jeweils »nach oben« gebrückt, D1 entfernt und durch Drahtbrücke ersetzt. Diese Aussagen sind **as-built reports**, noch keine ohmschen Messungen.
- [x] Foto der F1-Aufschrift weist auf `T 2.5A ... AC250V` hin; V1.2-Schaltplan zeigt dagegen `630 mA / 275 V`. Hohe Abweichung, ist VOR ENERGIZING zu klären.
- [x] U25-Aufdruck sieht wie `TINY3216` aus, aber Foto allein ist noch keine zuverlässig protokollierte vollständige IC-Signatur. Die PCB-MPN `ATTINY1616-SN` ist nachweislich historisch widersprüchlich.
- [x] V1.2-Netzbeweis: D1 Pad2=5V, Pad1=D1_1 (U6 VIN); F1 5V_↔5V; JMP1 KNX_VCC↔R9_2; JMP2 Pad1=KNX_RX', Pad2=KNX_RX, Pad3=KNX_TX'; JMP3 Pad1=KNX_RX', Pad2=KNX_TX, Pad3=KNX_TX'; U6 1=D1_1, 2=GND, 3=3.3V. Alle anderen Quell-/Hardware-Freigabeprüfungen bleiben offen.

## Gate 2 – Entscheidung

- Einen **evidenzbehafteten dokumentierten Iststand** anlegen mit strenger Trennung Foto/User-Angabe/Schaltplan gegen **nicht vorgenommene Messung**.
- Stromloses Prüfprotokoll für D1-Jumper (5V↔D1_1, Fremd-Kurzschluss/Rückspeisung), JMP1/JMP2/JMP3 per tatsächlichen Pads, tatsächliche F1-Auslegung, U6 mechanisch (ggf. Rückseite) und U25/R29 präzisieren.
- `docs/KNX033_AS_BUILT_PCB_REVIEW.md` und maschinenlesbares `docs/KNX033_AS_BUILT_PREFLIGHT.json` sowie `tools/audit_knx033_asbuilt.py` + Negativtests anlegen.
- **Keine Bestromung/COM-/USB-/KNX-/UPDI-/ETS-/Motoraktion**, kein PCB-Firmware-Schaltplan-Source editieren, kein Git-Push.
- Bestehende KNX022-Blocker nicht zu PASS erklären. Wenn Rückseitenfoto oder Messwerte fehlen, KNX033 als *Sichtprüfungsabschluss mit offenem Hardware-Gate* kennzeichnen, nicht als elektrische Abnahme.

## Gate 3

**Pending:** konkreter Foto-/Netzabgleich, Report, Metriken, QS.

## Gate 4

**Pending:** Quellschutz, negative Gates, Repo-Audit, Implementierungs- und Abschlusscommit, ASH-Checkpoint, kein Push.

## Gate 3 – Umsetzung/Ergebnisse

- [x] `docs/KNX033_AS_BUILT_PCB_REVIEW.md` dokumentiert drei neue Nutzerbilder (Chat-Anhaenge, **nicht auf LLO Home gespeichert**), ihre SHA256-Werte/Dateinamen, sichtbare Komponenten und Bruecken sowie sicheren stromlosen Testplan.
- [x] `docs/KNX033_AS_BUILT_PREFLIGHT.json` hat alle Original-Foto-SHA256, V1.2-Padnetze und aussagegetrennte Userberichte vs. Fotoindiz vs. ungemessene elektrische Istwerte.
- [x] F1-Fotoaufschrift `T 2.5A / AC250V` gegen Schaltplan `630mA 275V` **P0 dokumentiert**. D1 Userbericht "entfernt/gebueckt" zwischen `5V` und `D1_1/U6 VIN`, fuer Rueckstrom jetzt nicht richtungsabhaengig; JMP1/JMP2/JMP3 Positionen offen messbar. U25-Aufdruck sieht wie TINY3216 aus; U6 von gezeigter Seite nicht eindeutig, R29-Wert unmessbar.
- [x] PCB-Netzbelege direkt aus `schematic/pcb_knx-valve-control_v1.2.json` verifiziert: JMP1 KNX_VCC/R9_2; JMP2 Pad1 KNX_RX', Pad2 KNX_RX, Pad3 KNX_TX'; JMP3 Pad1 KNX_RX', Pad2 KNX_TX, Pad3 KNX_TX'; D1 5V/D1_1; F1 5V_/5V; U6 1 D1_1/2 GND/3 3.3V.
- [x] `tools/audit_knx033_asbuilt.py` Source/Fotogates **PASS**, `tools/test_knx033_asbuilt_gate.py` **15/15 PASS**. Negative cases blockieren erfundene DMM-Messungen, Power/Motor GO, umgedeutete D1, F1-Nennstromvertuschung, angeblich bestaetigte U25-Signatur/R29/U6 usw. Produktionsfirmware, KNX-ETS und PCB gegen `7d8f835` unangetastet.
- [x] README, Roadmap, KNX022-Preflight, Power-Konzept und KNX029-Runbook mit reellem As-built-Status verlinkt; vorhandene KNX022-Blocker **nicht** geschlossen.
- [x] Home offline smoke `tools/home_offline_check.ps1 -Native` Job `job-000219` **exit 0**, 12 native Testskriptgruppen und alle bisherigen USB-Upload-Mocks/KNX029–032 Audits weiter PASS; keine physischen Befehle.
- [x] ASH 30/30 Checks und 529 Markdown Links **PASS**; neue _OPEN-KNX033-Dokumentation als einziger aktiver Marker akzeptiert.

## Gate 4 – Abschluss

- [ ] Gestagter Dateiscope, Git diff --check, lokaler Implementierungscommit.
- [ ] Separater HISTORY-Abschluss und Entfernung des offenen KNX033-Slice-Markers; erneut ASH pruefen.
- [ ] Clean Git (kein Push) und abgeschlossene Session mit Checkpoint.

**Erst bei Rueckseitenfoto und stromlosen Messwerten kann ein neuer KNX002/003-Real-Gate gestartet werden.** Bis dahin `BLOCKED_NO_POWER_NO_FLASH_NO_MOTOR`.
