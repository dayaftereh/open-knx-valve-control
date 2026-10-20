# KNX101 – GPIO10-Startdiagnose (Entwurf, nicht deployed)

**Stand: 20.10.2026.** Nur auf dem LLO Desktop Agent vorbereitet. Der laufende RP2040 auf COM7 hat weiterhin KNX100 im verriegelten Zustand `FAULT_LATCHED`; Motor M1 IDLE, Motorausgänge LOW, INA219 0 mA.

KNX100 hat die Fahrten R-Referenz (23.711 ms) und F nach 500 Promille (11.383 ms) erfolgreich abgeschlossen. Beim nächsten F-Start auf 250 Promille wurde `FAILED_OUTPUT_OR_START_ACK` gemeldet und der Motor unmittelbar gestoppt. Eine weitere physische Motorfahrt wird **nicht** aus dem ungeklärten Fehlerzustand gestartet.

## Ziel der Firmware

KNX101 ergänzt den Startpfad um getrennte Messungen von RP2040 GPIO10 Ausgangslatch, tatsächlichem GPIO10 Pinpegel unmittelbar und nach 1,3 ms sowie Rückgabewert der KNX099-Startquittierung. Bei Fehler bleiben alle bisherigen Stop-/Fault-Sperren erhalten. Es gibt keine KNX-TX-Übertragung, keinen automatischen Start und keinen alten PULSE-Befehl.

Der Build ist erfolgreich. UF2: 250880 Bytes, SHA256 `9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76`.

**Wichtig:** `knx101_host.py` besitzt absichtlich noch den ungültigen Image-Pin `__KNX101_SHA__` und `PIN_BYTES=0`. Es ist kein vollständig freigegebener Test-Launcher und darf nicht benutzt werden, um die Firmware zu flashen oder die Motortestfolge erneut zu starten. Ein vorheriger Versuch zur Aktivierung war durch eine Tool-Sicherheitsprüfung blockiert worden. Die Sperre wurde nicht umgangen.

## Prüfungen

- Native C++-Regression `tests/native/test_knx102_consecutive_f_start.cpp` bestätigt die beiden unmittelbar aufeinanderfolgenden F-Starts im reinen KNX099-Modell.
- `tools/test_knx102_start_guard.py` prüft Diagnoseflags, beibehaltene Schutzbedingungen, Build-Identität, absichtlich unvollständige Image-Freigabe sowie den archivierten realen Startabbruch.
- KNX100 Offline-Regression: 12/12 bestanden; KNX102 Diagnose-Regressionsprüfungen: 6/6 bestanden.

Vollständige Diagnose unter `docs/KNX102_START_GUARD_DIAG_20261020.md`.

Eine erneute Endlagenreferenz ist zwingend nötig, bevor der Positionsregler später reale Teilfahrten als gültige Positionen übernehmen darf. Git-Push erst nach ausdrücklichem Auftrag.
