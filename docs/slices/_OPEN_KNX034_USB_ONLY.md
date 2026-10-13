# KNX034 – Rueckseitenfoto / USB-only Betriebsplanung durch offenen JMP1

**State:** open
**Scope:** nur fotografische und statische V1.2-Versorgungspruefung; keine elektrische Freigabe
**Date:** 2026-10-13
**Owner:** ChatGPT-OpenKNXValveControl-KNX034-UsbOnly-Backside-20261013
**Session:** ses-20261013T144950-46742678097e
**Baseline:** main HEAD e8033c7, working tree clean, 15 lokale Commits vor origin/main

## Gate 1 – Verify

- Der Nutzer zeigt ein viertes Bild der Platinenseite mit U6-Baukoerper: `20261013_164325.jpg`, SHA256 `932bfac8982d03ebee0e23087a8da03d7480d40fc89b5677eec800fb3d392e82` (Original im Chat, NICHT auf LLO Home archiviert). U6-Platz in der Rueckseitenansicht bestueckt, die schwarze Blockform und daneben 5V/3.3V/U6-Silkscreen sind erkennbar; Herstellerbezeichnung auf dem Bauteil im Bild nicht lesbar. CN1 (2x3) bestueckt, RUN/PROG/USB_BOOT-Schalter auf Rueckseite sichtbar. **Keine Messungen.**
- Nutzer **schlaegt vor**, JMP1 wieder aufzutrennen, damit fuer die erste Erprobung nur USB speist. Bisheriger KNX033-Istzustand meldet JMP1 geschlossen. Vorschlag nicht als bereits ausgefuehrte Aenderung protokollieren.
- PCB V1.2: JMP1 Pad1 KNX_VCC ↔ Pad2 R9_2; Q1 Drain=R9_2, Source=5V_, Gate=USB_VCC, R9 gegen GND. Oeffnen von JMP1 unterbricht diesen im Layout vorgesehenen KNX-Quellzweig zur 5V_-Auswahl, **aber garantiert keine galvanische Trennung oder fehlende parasitaere Rueckspeisung ueber GND/Signale**.
- Bestehender USB-Strompfad: USB_VCC → D6 → 5V_ → F1 → 5V → D1-Draht (statt Diode) → D1_1/U6 VIN → U6 3.3V. D6-Abfall bleibt; U6 min 4,75V VIN; selbst USB 5,0 V ist somit keine garantierte VIN-Reserve bei Last.
- KNX033-F1 Foto T2.5A vs Schaltplan 630mA ist weiter P0; D1-Draht und Q1-/KNX-GND-Rueckspeiseverhalten ungeprueft. Motor/STBY-Gates offen.

## Gate 2 – Decision

- Stromlosen, messbasierten Testplan fuer **JMP1 offen** entwerfen, mit getrenntem USB-only Labor-Gate erst nach F1/Leiterbahn-/Reglertyp-Abnahme.
- KNX-Bus, UPDI-Programmer und Motoren/externes Netzteil unverbunden lassen; kein USB-Stecken/KNX, solange F1 und D1-Freigabe offen.
- Fokussierte [KNX034-Checkliste](../KNX034_USB_ONLY_PREPOWER_GATE.md) erstellen, Status **proposed_not_applied** und alle Freigaben false. Aeltere KNX033-Evidenz nicht rueckwirkend umdeuten.
- Abschliessend QS, Git-commit und History, kein Push. Keine Source-/Firmware-/ETS-Aenderungen.

## Gate 3
Pending.

## Gate 4
Pending.

## Gate 3 – Completed (Dokumentation und sperrende Tests)

- [x] Rueckseitenbild mit SHA256 als **Chat-Evidenz** erfasst, U6-Modulkoerper an der U6-Aufdruckposition klar sichtbar, exakter Typ und VIN/VOUT noch nicht gemessen.
- [x] JMP1-Entscheidung als `PROPOSED_NOT_APPLIED` festgehalten, Vorzustand `JMP1 geschlossen` weder umgedeutet noch als geoeffnet beschrieben.
- [x] Verifiziertes PCB-Padnet: JMP1 KNX_VCC/R9_2, Q1 USB_VCC/5V_/R9_2, R9 GND/R9_2, D6 USB_VCC/5V_, F1 5V_/5V, D1 Draht 5V/D1_1, U6 VIN D1_1 und VOUT 3.3V.
- [x] USB-only-Plan verlangt **KNX-Bus vollstaendig getrennt**, keine Motoren/UPDI, **stromlose Ohmmessung** nach JMP1-Oeffnung und F1-Korrektur/Schutzkoordination vor Power. Keine Garantie auf galvanische Trennung, USB-Eingangsreserve >=4,75V an U6 oder Rueckspeisungsfreiheit.
- [x] `docs/KNX034_USB_ONLY_PREPOWER_GATE.md`, `docs/KNX034_USB_ONLY_PREFLIGHT.json`, `tools/audit_knx034_usb_only.py`, `tools/test_knx034_usb_only.py`, README/ROADMAP/KNX033-Nachtrag, Home-Offline-Smoke erweitert. Historischer KNX033-JSON und Produktions-Firmware-/ETS-/PCB-Dateien unveraendert.
- [x] Audit verifiziert echten source-level Pad-Netzvergleich und unberuehrte historische Quellen: PASS. **16/16 KNX034 Negativ-/Vertragspruefungen PASS**, keine physischen Freigaben.
- [x] Home `tools/home_offline_check.ps1 -Native` Job `job-000240` **exit 0** inkl. 12 native Regression-Gruppen, KNX027-033 u.a., kein Flash/Motor. ASH **30/30 PASS**, **540** lokale Markdownlinks, Markerstatus korrekt.

## Gate 4 – Next exact actions

- [ ] Stage reviewed KNX034 files; `git diff --cached --check`; local implementation commit.
- [ ] Close History entry and remove KNX034 marker in separate commit; final ASH audit and clean Git; no push.
- [ ] Preserve user-facing outstanding F1 and unpowered JMP1 confirmation request.

**No board USB/KNX/UPDI/bench power/measurement was carried out.**
