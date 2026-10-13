# KNX029 – Inbetriebnahme-Vorbereitung RP2040 / ATtiny / KNX

**State:** open
**Gate:** 2/4 (Checkup und Entscheidung angenommen)
**Profile:** software
**Opened:** 2026-10-13
**Owner/Session:** ChatGPT-OpenKNXValveControl-KNX029-Home-Readiness-20261013 / `ses-20261013T101642-e0e1a1f3f57b`
**Project root:** `C:\_myspace\workspace\open-knx-valve-control`
**Baseline:** `a35d6be` (KNX028 geschlossen; Home main CLEAN, 4 lokale Commits vor origin/main)

## Ziel

Ein reproduzierbares **stromloses Offline-Bring-up-Kit** zur spaeteren ersten Platinen-Inbetriebnahme auf LLO Home erzeugen: getrennte RP2040/ATtiny3216-Binaries, dateibasierte Integritaetsnachweise, sichere Testabfolge fuer USB, UPDI, KNX und Software-Telemetrie, ohne angeschlossene Hardware zu behaupten.

## Gate 1 – Livecheck / Quellen

**Accepted:**
- Agent 0.7.9 online, keine laufenden anderen Write-Sessions, Git main sauber, keine anderen _OPEN_-Marker, HEAD a35d6be. Arbeitsstand lokal vier Commits vor GitHub und darf nicht verloren gehen.
- KNX028 Toolchain/Hosttests fertig; RP2040 Arduino-Pico 5.5.0 / GCC14.3.0, PlatformIO und OpenKNXproducer3.12.2 vorbereitet; nativer WinLibs C++ QA.
- Realer Motorbootzustand und TB6612 STBY **nicht elektrisch sicher nachgewiesen**. KNX022 mit zehn Hardware-Blockern; keinerlei Ventil erlaubt.
- U25 Bestueckung kann ATtiny1616 statt konfiguriertem ATtiny3216 sein. **Keine UPDI-Erase-/Programmiersuche**, erst physische Markierung und lesende Signatur nach Pegel-/CN1-Freigabe.
- KNX018 beschreibt CN1 Pin1 mit potentiellem USB-5V-Konflikt. RP2040 USB ist NICHT derselbe ATtiny-Programmer-UART; KNX TP ueber Serial1, ATtiny Temperatur UART1 ueber Serial2, kein echter KNX-Bustest bisher.

## Gate 2 – Entscheid / Scope

**Accepted:**
- Neuen Python-Host-Workflow `tools/knx029_prepare_bringup.py`: default `plan` liefert nur strukturierte Voraussetzungen; `build` akzeptiert ausschliesslich einen EXPLIZITEN vollen Git-SHA, sauberen Repo-Tree und neuen Ausgabepfad **ausserhalb** des Git-Roots. Zwei echte PlatformIO-Umgebungen `controller` und `temperature` ausschliesslich in temp-kopierter Quelle; keine upload-/device-/erase-/COM-/KNX-Befehle, keine USB-Erkennung.
- Bundle bestehend aus controller UF2/ELF, ATtiny HEX/ELF, maschinenlesbarem Manifest (SHA256, Commit, Targets und unverifizierte reale Hardware-Gates). Den ATtiny3216-Hex nie als kompatibel zu physisch bestuecktem ATtiny1616 ausgeben.
- Host-Tests: Negativpfade unsauberer Tree, falscher HEAD, existierender Pfad, fehlende Artefakte/Tools, nicht-physische Plan-Ausgabe, SHA; simulierte Builds mit Kommandowatch; statischer Source-Scope-Audit.
- Dokumentation mit klarer Reihenfolge: stromlose Fotos/BOM/Versorgungs-/UPDI-Logik; USB-Erkennung ohne Flash; RP-Flash erst motorlos nach KNX002/003/018; ATtiny-ID zuerst read-only; KNX/IP isoliert; anschliessend Sensor T0..T8, ohne Motor.
- Keine Produktschemata, ETS XML/KO, Pinbelegung, Firmware-Motorlogik, ATtiny-Firmware, Release-Upload-CLI, Bibliotheken oder Sicherheitsgrenzen veraendern. Kein Flash, kein Netzwerkbuszugriff, kein Git-Push.

## Gate 3 – Implementierung

**Pending**: Host-Bundle-Tool, Mocktests, Runbook und Verweise.

## Gate 4 – Pruefung/Close

**Pending**: Mocktests, echte offline Builds mit SHA-Mapping, bestehende QA/ASH, git staged diff --check, Umsetzung- und Abschlusscommit, _OPEN_-Marker entfernen.

## Next exact action

Implementiere das stromlose, fail-closed KNX029 Bundle mit reproduzierbarem Software-Nachweis und Tests; keine angeschlossene Platine notwendig.

## Resume and Gate 3 proof (2026-10-13)

- Former session `ses-20261013T101642-e0e1a1f3f57b` lease became **stale** but had **0 running jobs**, state ready; last four jobs exited 0. Controlled stale takeover used for KNX029, no conflicting session/changes discarded.
- `tools/knx029_prepare_bringup.py` now provides **plan / build / verify** with exact clean Git HEAD, new output outside Git, two actual target builds in a temporary source copy, and SHA256SUMS/manifest. The temporary ATtiny config strips every UPDI/COM/upload hook before invoking PlatformIO.
- Fail-closed offline verifications: full tool tests **13/13 PASS**, including changed SHA, dirty Git, invalid source HEAD, missing HEX, malformed programmer config, checksum tampering and forbidden physical "GO" flags. Default and verify commands are software-only.
- `tools/audit_knx029_bringup_scope.py` **PASS**: original RP/ATtiny/ETS/PCB/driver/USB-upload tool files frozen vs `a35d6be`.
- Runbook `docs/KNX029_FIRST_CONTACT_RUNBOOK.md` details the real future bench sequence and physical KNX022/018 gates. `tools/home_offline_check.ps1`, README and ROADMAP reference new checks. ASH audit 30 checks / 484 Markdown links PASS. No hardware or bus access.
- Host inventory: `pymcuprog` 3.19.4.61 installed (not used), WLAN up, Ethernet disconnected (KNX/IP **not** proven).

**Gate 3 status:** implementation and negative tests PASS.

**Gate 4 next:** stage reviewed files, Git diff --check; commit implementation to establish a clean full Git SHA; generate real dual-firmware bundle in a fresh external directory on Home, verify all hashes and target artifacts; close marker/HISTORY in a separate commit. No push, motor, USB flash, UPDI or KNX send.

### Offline-Build-Regressionsprüfung nach Implementierungscommit

- Implementierungscommit `0dfb518`: Doppel-Target-build `job-000112` **beide Firmwarekompilationen PASS** (RP2040 und ATtiny3216), aber Verpackung BLOCKED: PlatformIO bereinigte beim Environmentwechsel die Controller-UF2/-ELF aus dem temporaeren `.pio/build/controller`. Der Packaging-Workflow hat deshalb zu Recht **kein unvollstaendiges Paket** freigegeben.
- Fix: RP2040-UF2 und -ELF unmittelbar nach dem ersten erfolgreichen Build mit SHA-Abgleich in einen separaten Temp-Bereich kopieren. Erst danach den ATtiny-Environment-Build starten; bei KIT-Build werden ausschliesslich verifizierte gesicherte Dateien verwendet.
- Neuer adversarial FakeRunner-Test simuliert das reale Loeschen des Controller-Buildordners bei ATtiny-Start. KNX029 **14/14 Tests PASS** einschliesslich des neuen Falles.
- No GitHub-Push, kein Motor, kein Bus, kein Flash. Der real erneut laufende Doppel-Build wird erst nach einem weiteren sauberen Fix-Commit gestartet.
