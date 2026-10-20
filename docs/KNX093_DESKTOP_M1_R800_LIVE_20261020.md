# KNX093 – LLO Desktop M1 R 800 ms, Live-Test

Stand: 20.10.2026, OpenKNXValveControl V1.2, LLO Desktop v0.8.2.

## Aufbau und Ausgangslage

Der Nutzer vermutete nach dem KNX092 M1 F 150ms Versuch, dass
der Motor schon in F-Richtung am Anschlag sein koennte, und
beauftragte einen laengeren akustisch beobachtbaren Motortest.
Deshalb wurde ausdruecklich die Gegenrichtung R gewaehlt.

Platine: Nur USB-C am RP2040 und ein Motor M1, kein KNX,
kein UPDI, keine DS18B20, kein M2. R33/R34 seit KNX092
jeweils mit 10 Ohm repariert. INA219-Leerlauf nahe null,
M_VCC um3,29V, R29 real200mOhm/1W.

USB: COM7, RP2040 VID:PID 2E8A:000A, Seriennr.
E464401787522D33. Andere CH340 COM8/9/10 auf Desktop
gehoeren nicht zu diesem Board und wurden nicht verwendet.

## Firmware KNX093 - fuer laengeren Einzeltest

Separater Fork, Original-KNX085 bleibt im Repository erhalten.

Quellen:
- tools/knx093_m1_long/src/main.cpp
- tools/knx093_m1_long/src/motor_gate.hpp
- tools/knx093_m1_long/platformio.ini
- tools/knx093_m1_long/knx093_host.py
- tools/test_knx093_m1_long.py

Motorfirmware akzeptiert ausschliesslich PULSE M1 R 800;
F-Richtung, M2, abweichende Zeit werden gesperrt.
Motor-Gate=1 nur in diesem Bench-Image. Kein automatischer
Motorbefehl nach Reset. KNX TX staendig LOW.

Feste Schutzbedingungen:
- ARM nur nach >5 gueltigen INA-Leerlaufproben, 5s Fenster.
- INA219 M_VCC 3,10 bis 3,45V, Ruhegrenze25mA,
  Fahrtgrenze120mA, Abtastung rund8ms.
- Maximaldauer800ms.
- Zusaetzlicher Software-Blockierschutz: nach ersten100ms
  bei mindestens90mA ueber vier unmittelbar aufeinanderfolgende
  gueltige Laufproben wird ein FAULT verriegelt und Ausgang
  im selben Polling-Zyklus abgeschaltet.
- Stromtrace-Puffer 160 Eintraege, fuer ~100 Proben bei800ms.
- Zusaetzlich STOP und STATUS/INA-Readback nach dem Impuls.
- Nur eine Ausfuehrung durch One-Shot-Flag pro Testserie.

Diese Abschaltungen sind Softwaremechanismen, KEINE
unabhaengige Hardware-STO. Ein kurzzeitiger Strompeak
unter8ms kann unentdeckt bleiben. Eine Blockierung
unterhalb90mA ist durch die neue Schwelle nicht erkennbar.

Build PlatformIO Core6.1.16, env knx093_m1_reverse_800: PASS
RAM17,0%, Flash5,2%. UF2 243200 Bytes, SHA256:
f10743ac5b5e33e0969a04e34c53d353ec832ffb2009a29fcdfd90417447d619

USB vor Flash genau identifiziert, sicherer RP2040-ROM-Loader
via picotool und Flash-Identitaet. Upload einmalig, erfolgreich
verifiziert; COM7 kam wieder. KNX093-Firmware-Fingerprint
erfolgreich live gelesen, INA stabil, Motor/KNX_TX LOW.

KNX093-Fingerprint:
M1_R_ONLY duration_ms=800 motor_gate=1 limit_ma=120
stall_ma=90 after_ms=100 consecutive=4 latched=0.

Sechs gezielte Offline-Kontraktpruefungen PASS.

## Durchgefuehrter zweiter Motorversuch

Ein einziges ARM und anschliessend M1 R 800ms.
USB meldete PULSE_STARTED; das automatische Ende war IDLE,
kein FAULT. Redundanter STOP wurde quittiert, Ausgaenge
LOW, KNX TX LOW; INA idle_ok=1, nominal0mA nach Ende.
Nachpruefung ueber COM7 ebenfalls bestanden.

| Messgroesse | Live-Daten |
| --- | --- |
| Motor M1, Richtung | R |
| Impulslaenge (angefordert) | 800ms |
| INA219 Strommesspunkte | 100/100 gueltig |
| Zeitfenster | 7 bis799ms |
| Erfasster Spitzenstrom | 108,90mA bei7ms |
| Strom bei15ms | 91,75mA |
| Strom bei23ms | 80,85mA |
| Strom bei79ms | 33,40mA |
| Minimum/Mittelmedian | 20,55mA / 29,625mA |
| Strom bei799ms | 29,95mA |
| Motor-Spannung min/max | 3260..3284mV |
| Stromwerte >=90mA nach t100ms | 0 |
| Blockierschutz ausgelöst? | Nein, latched=0 |
| Motorstate nach Ende | IDLE |
| Nachher Strom nominal | 0mA |

Die Stromaufnahme fällt nach dem Anlauf deutlich ab
und bleibt bis800ms auf rund25..35mA ohne Anstieg am
vermuteten Anschlag. Das ist mit einem frei drehenden
Motor vereinbar, aber KEIN visuell oder akustisch
bestaetigter Bewegungstest. Auf Nutzerfeedback warten.

Messbelege/UF2 auf LLO Desktop (nicht im Git):
C:\ASH\Workspace\Runtime\KNX093\
- KNX093_FLASH_20261020_080903.json
- KNX093_M1_R800_20261020_080931.json
- KNX093_M1_R800_20261020_080931.csv
- KNX093_FLASH_STARTED.flag
- KNX093_M1_R800_STARTED.flag

Keine automatische weitere Motorbewegung, keine
Endanschlagfahrt und keine Kalibrierung vorgenommen.
Die Platine laeuft jetzt auf KNX093 (nicht mehr KNX085).
Weitere Langlauf-/Stalltests erst nach Nutzerfeedback.

Git lokal committen, KEIN Push ohne ausdruecklichen Auftrag.
