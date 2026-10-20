# KNX098 / 20.10.2026 – M1-Motortest als Bench-Gate abgeschlossen

**M1-Bench-Abnahme GREEN:** Drei komplette KNX097-Umkehrzyklen R/F mit 6/6 INA219-LOAD_RISE-Abschaltungen, 17.678/17.678 gueltigen 8-ms-Strommessungen und stabilen Richtungszeiten. R-Mittelwert **24,388 s**, F-Mittelwert **22,751 s**, Standardabweichung 91,5 / 59,9 ms. KNX098 hat die Originalkurven zusaetzlich vollstaendig gegen die sechsfach bestaetigte 45-mA-Stromschwelle offline nachgeprueft und SHA256-gebunden eingefroren: config/knx098_m1_bench_calibration.json. **Zwischenpositionen, mechanische 0/100%-Zuordnung und KNX-/ETS-Freigabe sind noch nicht validiert.** Kein weiterer Motorlauf erforderlich; Board derzeit KNX097 IDLE, legs_done=6. Abnahmebericht: docs/KNX098_M1_MOTOR_BENCH_ABNAHME_20261020.md.

---

# KNX097 / 20.10.2026 – Drei M1-R/F-Reversierzyklen

Auf LLO Desktop COM7 wurden drei vollstaendige R/F-Zyklen mit Stromabschaltung am LOAD_RISE-Kandidaten ausgefuehrt. R: 24,423 / 24,479 / 24,263s, Mittelwert 24,388s; F: 22,767 / 22,815 / 22,671s, Mittelwert 22,751s. Die Spannweiten liegen bei nur 216ms (R) und 144ms (F). Alle 17.678 INA219-Samples bei 8ms sind gueltig und lueckenlos. Nach dem letzten STOP ist M1 IDLE, GPIO LOW, 0mA. Keine ETS-0/100%-Position gesetzt. Details: docs/KNX097_M1_REVERSAL_REPEATABILITY_20261020.md.

---

# KNX096 / 20.10.2026 – M1-F-Gegenfahrt komplett aufgezeichnet

**LLO Desktop, COM7:** Die stromueberwachte Fahrt vom zuvor erkannten R-LOAD_RISE-Kandidaten in Richtung F endete bei **22,695 Sekunden** durch einen zweiten LOAD_RISE-Kandidaten. Der Rohstrom stieg am Ende auf 56,45mA (maximal nahe Ende59,65mA), zuvor betrug der laufende Median20,15mA. Danach STOP ACK, Motorausgaenge LOW, IDLE, INA nominal0mA. Die vollstaendige Firmware-RAM-Aufzeichnung **2837/2837 Rohsamples, 8ms-Abstand ohne Luecken** wurde rein lesend ausgelesen; CSV/JSON auf LLO Desktop Runtime KNX096. Es sind zwei elektrische Endlagen-Kandidaten, noch keine mechanisch bestaetigte 0/100-Prozent-Kalibrierung. [KNX096-Bericht](docs/KNX096_F_OPPOSITE_FULLSTROKE_20261020.md).

---

# KNX095 / 20.10.2026 – erster M1-Referenzanschlag-Kandidat

LLO Desktop COM7: M1 bewegt sich laut Nutzer mechanisch. Beim ersten abgesicherten Referenz-Suchlauf KNX095 in Richtung R wurde nach **7,735s** ein anhaltender INA219-Lastanstieg von ~28mA Normalstrom auf **46mA** erkannt. Das MCU stoppte den Motor bei sechs aufeinanderfolgenden Proben >=45mA (LOAD_RISE-Kandidat), vor dem 15s-Limit. 967/967 gueltige Rohmessungen, STOP danach quittiert, GPIO LOW, Motor IDLE, INA nominal0mA. Die Funktion hat **noch keinen permanenten 0%-Referenzpunkt** gesetzt, weil ein Lastanstieg auch von Reibung kommen kann. Kein automatischer Folgeversuch. [KNX095-Messbericht](docs/KNX095_M1_INA_REF_LOADRISE_20261020.md).

---

# KNX094 / 20.10.2026 – M1 Rueckwaertsfahrt 10 Sekunden

Auf LLO Desktop (COM7, exakte RP2040-ID) wurde die KNX094-Firmware eingespielt und **ein einzelner M1-R-Impuls von 10000ms** durchgefuehrt. 1250/1250 INA219-Stromproben gueltig, Peak beim Start **112,05mA**, Laufstrom-Median **28mA**, ab400ms maximal **34,5mA**. **Kein Stromanstieg eines Hard-End-Anschlags**, kein FAULT; Ende zeitbedingt IDLE, STOP bestaetigt, Motor-/KNX-TX-Ausgaenge LOW. Mechanische Drehung/Endlage nicht unabhaengig bestaetigt. Nur USB-C und M1 am Board; INA nach R33/R34-Reparatur plausibel. Aktuelle Firmware KNX094 nimmt nur M1 R10000 nach ARM an, kein automatischer Test. CSV+JSON auf Desktop Runtime; Details in docs/KNX094_M1_R_10S_LIVE_20261020.md.

---

# KNX093 / 20.10.2026 – laengerer M1-Hoertest auf LLO Desktop

Am Arbeitsplatz ist aktuell **KNX093** auf dem RP2040 COM7 (Seriennummer E464401787522D33) installiert. Nur USB-C und ein Motor an M1, **kein KNX, UPDI oder Temperatursensor**. Nach Reparatur von R33/R34 (je10Ohm) ist der INA219-Ruhestrom plausibel. Ein einzelner, stromueberwachter **M1 R 800ms** Rueckwaertsimpuls wurde ausgefuehrt: 100/100 INA-Samples gueltig (t7..799ms), Peak **108,9mA**, Strom am Ende **29,95mA**; Firmware-IDLE und redundanter STOP bestaetigt, alle Motor-GPIO LOW, kein Stall-FAULT. Mechanische Bewegung noch vom Benutzer zu bestaetigen. Firmware nimmt nur M1 R800 an, keine automatische Motorfahrt, keine Wiederholung. [KNX093-Testbericht](docs/KNX093_DESKTOP_M1_R800_LIVE_20261020.md).

---

# KNX092 Live-Test – LLO Desktop, 20.10.2026

**Aktueller Hardwarestand:** Testplatine ausschliesslich mit USB-C an RP2040 (COM7, USB-ID E464401787522D33) und einem M1-Motor, ohne KNX/UPDI/Temperatursensoren. Nach Einloeten von je 10 Ohm an R33/R34 ist der INA219-Shunt wieder nahe 0mV (0,12..0,16mV), Bus 3,288V und Ruhestrom ca. 0,6..0,8mA. KNX085-Testfirmware SHA-geprueft per picotool-ROM hochgeladen; der **erste M1-F-Impuls von 150ms** wurde durchgefuehrt. 18 gueltige Strommessungen zwischen 7..143ms, aufgezeichneter Anlaufstrom maximal **108,15mA**, am Ende ca. 31,65mA. Motor automatisch IDLE, redundant STOP bestaetigt, alle Motor-GPIO LOW; Leerlauf danach nominal 0mA. Mechanische Bewegung bisher nicht unabhaengig bestaetigt. Kein automatisches Homing/zweiter Fahrbefehl. [Vollstaendiger KNX092-Live-Bericht](docs/KNX092_DESKTOP_USB_INA_M1_FIRST_TRACE_20261020.md).

---

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

## KNX089 – aktuelle Firmware nach DMM 0,00 mV (19.10.2026)

Beim Benutzer wurden direkt ueber R29 0,00mV DC gemessen. Die bisherige KNX085-Ausgabe von 92,6mV am INA219 ist damit eine fehlerhafte oder anders verschaltete ANALOGMESSUNG, nicht ein gesicherter echter Motorstrom. Die Konfiguration 0x399F wurde jetzt durch KNX089 direkt aus Register 0x00 gelesen; ADC-Reset aenderte Shuntregister 0x01 nicht (92,59 -> 92,63mV). Es wurde motor-gesperrte KNX089-Diagnosefirmware auf den echten RP2040 geflasht (COM8, KNX_TX LOW, motor_gate=0), KEINE M1-Bewegung. Die KNX085-Motor-USB-Kommandos sind damit auf dem BOARD aktuell NICHT freigegeben. Erst Sensor-/Sensepfad reparieren, dann fuer eine Motorstrommessung den KNX085-unlocked Build erneut bewusst deployen. Siehe docs/KNX089_INA219_R29_ZERO_MV_REGISTER_DIAG_20261019.md.
