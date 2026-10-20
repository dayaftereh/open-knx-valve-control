# KNX095 – INA219-M1-Referenzsuche, erste Lastanstiegserkennung

Stand: 20.10.2026, LLO Desktop, COM7, Boardserial E464401787522D33.

**Live-Ergebnis:** Nutzer bestaetigte zuvor mechanische M1-Drehbewegung.
Nach KNX094-R10s bei normalem Laufstrom28mA wurde in derselben
Richtung eine einzelne kontrollierte KNX095-Referenzsuche gestartet.

Die Firmware trennte die Motoransteuerung **bei t=7735ms**
selbststaendig, weil der Strom fuer sechs aufeinanderfolgende
INA219-Abtastungen die 45mA-Schwelle erreicht hatte.
Rohsignal: ENDSTOP_CANDIDATE kind=LOAD_RISE, current_ma=46.

Die Stromkurve stieg von Median28,25mA (400..3000ms)
ueber34,15mA (5000..6000ms),40,15mA (6000..7000ms)
auf45,05mA (7500..7700ms). 967/967 Rohwerte gueltig.
Firmware-Endstatus FAULT (beabsichtigter Lastabbruch),
danach USB STOP ACK und IDLE, GPIO LOW, nominal0mA.

**Ein mechanischer Endanschlag-Kandidat, NOCH KEIN
als 0% bestaetigter Nullpunkt.** Ursache des Anstiegs kann
auch lastabhaengige Reibung oder Schwergang sein.
Keine zweite Motorfahrt, kein Backoff und keine automatische
ETS-/KNX-Positionsschreibung ausgefuehrt.

## Firmware

Separater Fork von tools/knx094_motor_10s.
- generate_from_knx094.py: Firmwarequellen.
- src/main.cpp, src/motor_gate.hpp, platformio.ini
- generate_host.py: pruefbare USB-Testskriptgenerierung.
- knx095_host.py: preflight, flash, verify und nur EINEN
  M1 R15000 Versuch, mit Live- und Rohtraceprotokoll.
- tests: ../test_knx095_reference.py (7/7 PASS).

Strict: Nur PULSE M1 R 15000, M1 in Gegenrichtung/F oder
M2 nicht freigegeben. Max15 Sekunden und 120mA Laufstrom,
M_VCC 3100..3450mV; USB/INA-Fehler -> FAULT.
Nach450ms Anlaufzeit:
  6 gueltige Samples >=45mA -> LOAD_RISE,
  6 gueltige Samples 0..5mA -> CURRENT_CUT.
Bei Kandidat sofort latched FAULT und Ausgang LOW;
USB gibt eindeutigen Stopgrund aus. Software ist keine
unabhaengige Hardware-Sicherheitsabschaltung.

Firmware UF2 Groesse 244224 Bytes; SHA256
11e6ee28a6620102426e2af96969861089a6d19fd47ecdf32535f0f9543130b0.
PlatformIO6.1.16 SUCCESS. Nur ein ROM picotool Flash auf
exakt identifizierte COM7 RP2040 Platine.

## Echtmessung und Bericht

docs/KNX095_M1_INA_REF_LOADRISE_20261020.md

Originalbelege auf LLO Desktop:
C:\ASH\Workspace\Runtime\KNX095\
- KNX095_FLASH_20261020_094725.json
- KNX095_M1_R15000_20261020_094805.json
- KNX095_M1_R15000_20261020_094805.csv

One-shot Flags verhindern automatisches Wiederholen.
KNX095 laeuft derzeit auf dem RP2040, Motor im Zustand IDLE.

Naechster Schritt: Benutzer bestaetigt, ob Mechanik in diesem
Versuch am konstruktiven Endpunkt angekommen ist.
Anschliessend separat abgesicherten Gegenrichtungs-Entlastungs-
und Wiederholungstest planen, bevor 0% als Position geschrieben
oder die automatische ETS-Regelung aktiviert wird.

Kein Git Push ohne neuen expliziten Auftrag.
