# OpenKNXValveControl – KNX085 / KNX086 Motor- und INA219-Diagnose

**Aktueller Stand: 19.10.2026, LLO Home.**

## Was auf dem RP2040 installiert ist

Die Firmware **KNX085 bench_unlocked** wurde mit dem verifizierten
RP2040-UF2-Bootloader auf der echten V1.2-Testplatine installiert:
- USB-C: COM8, VID:PID 2E8A:000A, Seriennr. E464401787522D33.
- KNX-TP Kellerlinie 1.3 und CH340/UPDI COM5 blieben verbunden.
- M1/M2 Testventilmotoren und T0..T3 waren angeschlossen.
- KNX_TX GPIO0 LOW und sämtliche Motor-GPIO LOW, Motorzustand IDLE.
- Passive KNX RX und vier gültige ATtiny-Temperaturkanäle laufen weiter.
- Firmware: tools/knx085_motor_diag/src/main.cpp,
  erzeugt aus KNX084 durch generate_from_knx084.py + enhance_trace.py.
- Exact UF2 SHA256:
  86CBF6942FD12EBA07402C52842BA7543CABD2C2A557A329607C954388A54750.

Die ehemals angesetzte **generelle Flash-Sperre bei angeschlossenem
KNX oder UPDI war für diesen nachgewiesen getesteten Prüfstand nicht
gerechtfertigt**. Der ursprüngliche U11-Hitzefehler war der
fehlerhaften R17-Pull-up-Bestückung zuzuordnen. R17 wurde entfernt;
KNX076/081/084 wurden zuvor mit angeschlossenem Bus erfolgreich
programmiert, und KNX043-Scopebeobachtungen zeigten keine gefährliche
HIGH-Ansteuerung im geprüften Resetfenster. Dies ist keine Garantie für
alle denkbaren Brownout- und Verdrahtungsfehler.

Die **alten historischen Offline-/isolierten Verfahren** bleiben
erhalten, sind aber nicht das aktuelle Live-Testverfahren.

## Aktuelle Motor-/INA219-Diagnose

INA219 auf 0x40 erkannt, CONFIG=0x399F, Leerlauf-M_VCC ca. 3,148 V.
24 reale INA219-Leerlaufmessungen (keine Motorbewegung):
- Bus 3144..3152 mV
- Roh-Shuntdifferenz etwa 92,6 mV
- rechnerisch mit Nutzer-bestätigtem R29=0,200 Ohm: 462..463 mA
- motor_gate=1, motor_state=IDLE, motors_low=1.

**R29-Bestückung bestätigt (19.10.2026): 200 mOhm / 1 W.** Die
EasyEDA-PCB-MPN SCR1206F1M1 / C3017245 ist lediglich noch ein
widersprüchlicher Datenbankeintrag, kein Nachweis falscher Bestückung.
Der INA219 meldet bei MOTOR AUS weiterhin ca. 92,6 mV Shuntspannung
bzw. 463 mA **Gesamt-M_VCC-Strom**; der Wert ist kein M1-Laufstrom.
Die gemeldete große Ruhelast / INA219-Messpfadabweichung bleibt zu
klären. Bei 463 mA verbrät R29 nur ca. 0,043 W (unterhalb von 1 W).

Der angeforderte M1-150-ms-Test wurde deshalb vor ARM/PULSE
abgelehnt, statt einen ungeklärten Motorversorgungskreis zu
übersteuern. **M1 wurde noch nicht bewegt.** Für den nächsten
Versuch muss die unerwartete M_VCC-Ruhelast bzw. INA219-Messstrecke
plausibilisiert werden; der R29-Bestückungswert selbst ist geklärt.

## Live-Skripte

- Start-KNX086-LiveM1.ps1
  - ohne Parameter: INA219/Temperaturen lesen (keine Motorbewegung)
  - -Run: genau ein zeitbegrenzter M1-Impuls mit Stromspur,
    nur nach bestandenem INA-/Versorgungscheck
  - -Flash: nur wenn alte KNX084-Baseline erkannt und exakte USB-
    Identität und UF2-Hash erfolgreich geprüft werden
  - Bei bereits installierter KNX085 ist kein erneuter Flash nötig.
- Start-KNX085-M1.ps1: Kompatibilitätsaufruf auf die neue Live-Variante.
- knx086_live_connected.py: explizites Schrittmodell preflight,
  flash, read_ina, m1, zugeschnitten auf den dokumentierten Live-Aufbau.
- Start-KNX085-Isolated.ps1 und knx085_one_shot.py: historischer
  USB-only-Modus mit physischer KNX-/UPDI-Abtrennforderung.

Der Motor-Steuercode verfügt über:
- KNX_TX bleibt LOW, keine unaufgeforderte Busnachricht
- exklusiver M1/M2-Motor (nicht gleichzeitig), keine Autoboot-Fahrt
- explizite USB-Arming-Freigabe mit 5s Zeitfenster
- Strom-/Spannungs-Plausibilität, Fehlerabbruch
- einzelne Pulse nur zwischen 50 und 250 ms
- redundantes STOP und Roh-Shuntverlauf/CSV im erfolgreichen Versuch
- M1-One-Shot-Wiederholungssperre im Live-Host.

Die V1.2 TB6612-STBY-Leitung ist dauerhaft HIGH, weshalb ein
Software-STOP keine unabhängige Hardware-Sicherheitsabschaltung ist.
Der Hersteller-Maximalstrom 120mA beim HmIP-VDMOT darf nicht
automatisch mit dem Endanschlag verwechselt werden.

## Evidenz

Aktueller Bericht:
../../docs/KNX086_R17_LIVE_FLASH_INA219_20261019.md

Originalbelege:
../../docs/KNX043_PICOSCOPE_RUN_RESET_20261015.json
../../docs/KNX076_ONE_PULSE_FIRMWARE_FLASH_20261018.md
../../docs/KNX081_KELLER_TP1_TX_KNXIP_ACCEPTANCE_20261018.md
../../docs/KNX084_PASSIVE_BUS_ATTINY_T0_T3_LIVE_20261018.md

Messungen auf LLO Home unter:
C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX086_LIVE_M1

Kein automatischer Reflash, kein unbeabsichtigter Motorstart und
kein Git-Push.


## KNX088 – INA219/M_VCC Diagnose vom 19.10.2026

Die user-bestaetigte R29-Bestueckung (0,200 Ohm/1 W) ist in
Firmware und Auswertung korrekt konfiguriert. Ein neuer rein
lesender 45-s-USB-Test ergab 41/41 gueltige Werte mit
462..463 mA auf der M_VCC-Schiene, obwohl alle Motoren IDLE sind.
Die PCB-Netzlistenpruefung zeigt 23 M_VCC-Pads: R29, R34,
C31/C36..C43 und nur die vier H-Brueckentreiber U34..U37.
INA219 IN+/IN- und Formel sind korrekt. Der Eingangsoffset
des ICs erklaert 92,6mV nicht. Entweder liegt eine echte
ungewoehnliche Last/Teilkurzschluss auf M_VCC vor, oder ein
physischer INA219/Sense-Frontendfehler. Ohne separate direkte
R29-mV-Messung ist die Ursache nicht eindeutig.

**Nichts flashen oder M1 starten, bevor die Ruhestromursache
bestimmt ist.** Die Motorstrom-Idle-Sperre bleibt unveraendert.

Dokumentation:
[KNX088 INA219 Root-Cause-Audit](../../docs/KNX088_INA219_MVCC_IDLE_ROOT_CAUSE_20261019.md)

Offline-PCB-Pruefung:
tools/knx088_ina_net_audit.py

Read-only Live-Zeitreihe:
tools/knx088_ina_idle_monitor.py --seconds 45

Messbelege:
C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX088_INA_IDLE
