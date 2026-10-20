# KNX097 – M1-Reversier- und Laufzeitkonstanztest

**Abgeschlossen am 20.10.2026, auf LLO Desktop COM7.**

- Drei volle R/F-Zyklen (6 Motorfahrten), jeweils bis zu einem INA219-LOAD_RISE-Kandidaten.
- R: 24,423 / 24,479 / 24,263 s, Mittel 24,388 s.
- F: 22,767 / 22,815 / 22,671 s, Mittel 22,751 s.
- Spannweite R 216 ms; F 144 ms.
- Alle **17.678** INA219-Abtastungen mit exakt 8-ms-Intervall aus den sechs RAM-Puffern vollständig gespeichert.
- 6/6 Firmware-Abschaltungen mit LOAD_RISE, danach STOP-ACK, alle Motorausgänge LOW.
- Keine 0-/100-%-Position festgelegt.

## Dateien im Repository

- generate_from_knx096.py: reproduzierbare KNX097-Quellen aus KNX096.
- src/main.cpp, src/motor_gate.hpp, platformio.ini: Controller-Firmware.
- knx097_flash.py: ROM-Image-Prüfung, Identitätsbindung, einmaliger Flash, read-only Verify.
- knx097_cycles.py: kontrollierter Test in zwei Etappen (zuerst 2 Fahrten, danach 4), unabhängig scharf geschaltete Motorfahrt, Strom-/Timeout-/USB-Gates, Rohdaten- und Postflight-Prüfung.
- tools/test_knx097_repeatability.py: neun Offline-Regressionsprüfungen.
- docs/KNX097_M1_REVERSAL_REPEATABILITY_20261020.md: vollständiger Bericht.

Firmware UF2 SHA256: d54632979a63dd6895f898f8923b6e9c94b72b93c6f874b9469dfe8dd792a2eb.

## Belege und Sicherheitsgrenzen

LLO Desktop Runtime: C:\ASH\Workspace\Runtime\KNX097.

Die Dateien KNX097_LEG_01_R bis KNX097_LEG_06_F enthalten pro Fahrt JSON sowie CSV mit lückenlosem INA-Stromprofil. KNX097_REPEATABILITY_SUMMARY.json/.csv fasst die Laufzeiten zusammen. Die originalen Einmalmarker bleiben erhalten, um **keine Fahrten versehentlich zu wiederholen**.

Neue Bewegungen sind mit KNX097 nach leg_done=6 durch den MCU-Fahrtenzähler gesperrt. Keine autonome Bewegung; kein KNX-/UPDI-Betrieb beim USB-Prüfstand. TB6612 STBY ist hart HIGH – Softwareüberwachung ist kein unabhängiger Hardware-Not-Aus. Vor produktiver KNX-/ETS-Referenzierung müssen mechanische Endlage und Lastsignaturen separat validiert werden.
