# KNX089 Nachtrag / 19.10.2026 – entscheidende DMM-Gegenmessung

Der Nutzer hat **0,00 mV DC direkt ueber dem bestueckten R29** gemessen. Die fruehere favorisierte Hypothese einer echten 463-mA-Last auf M_VCC ist dadurch **stark entkraeftet**. Der motor-gesperrte KNX089-Firmwaretest las den INA219 direkt: CONFIG0x399F, SHUNT0x01 rund 92,6mV, CAL0x05=0, Bus3148mV, nach gezieltem INA-ADC-Reset praktisch unveraendert. Beide I2C-Lesewege funktionierten. Naechster DMM-Test: 0-mV-Wert ueber R33 Pad2/U23 IN+ zu R34 Pad2/U23 IN- mit der direkten R29-Messung vergleichen. [KNX089 Registerdiagnose](KNX089_INA219_R29_ZERO_MV_REGISTER_DIAG_20261019.md). Der Rest dieses Dokuments dokumentiert den frueheren Stand **vor** der DMM-Gegenmessung.

---

# KNX088 – INA219 / M_VCC 463 mA im Stillstand

**19.10.2026, Live- und PCB-Audit über LLO Home.**

## Zusammenfassung

Der RP2040 läuft mit KNX085. Alle acht Motorenable-GPIOs und die beiden
Richtungssignale sind LOW, Motorzustand IDLE. Trotzdem meldet der INA219
am gemeinsamen Motorrail-Shunt R29 kontinuierlich rund **463 mA**.

**PCB-Verdrahtung und Firmware-Stromfaktor sind KORREKT.** Offen ist,
ob ein tatsächlicher ungewollter Strom über M_VCC fließt oder
die reale INA219-Analogmessung fehlerhaft ist. Die vorhandenen
USB-Daten ohne unabhängigen Spannungsmesser trennen diese zwei
Hypothesen noch nicht endgültig. M1 wurde nicht aktiviert.

## Reale, rein lesende 45-Sekunden-Messung

Werkzeug: tools/knx088_ina_idle_monitor.py --seconds 45.
Benutzt nur STATUS, MSTATUS, INA, TEMPS und RXSTATS.
USB-Ziel: VID 2E8A PID 000A, Serial E464401787522D33, COM8.

- 41 von 41 INA219-Messungen gültig.
- Gemeinsamer Motorrail-Strom min/median/max: **462/463/463 mA**.
- M_VCC/Busspannung min/median/max: **3148/3148/3152 mV**.
- R29 vom Nutzer als real bestückt bestätigt: **0,200 Ω / 1 W**.
- Shuntspannungsabfall aus gemeldetem Wert: ca. **92,6 mV**.
- Verbrauch am Shunt: ca. **0,04287 W**.
- VIN+ / 3,3-V-Schiene aus Bus + Shunt ABGELEITET:
  **3240,6 mV** (kein unabhängig gemessener Wert).
- Wenn echte 463 mA fließen, Lastleistung auf M_VCC:
  3,148V * 0,463A = ca. **1,46 W**; Ersatzlast ca. **6,8 Ω**.
- Passive KNX-RX-Kanten: +2844 während 45 Sekunden.
- Vier Temperatursensoren gültig, UART Timeout 0, Reject 0.
- Motor-GPIO/KNX_TX LOW. Keine ARM/PULSE/STOP-Kommandos.

Private Daten unter:
C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX088_INA_IDLE\
- KNX088_PASSIVE_INA_20261019_090753.json
- KNX088_PASSIVE_INA_20261019_090753.csv

## PCB V1.2: 183 Bauteile statisch geprüft

Werkzeug: tools/knx088_ina_net_audit.py
PCB: schematic/pcb_knx-valve-control_v1.2.json
Ergebnis: PASS, 23 Pins unmittelbar an M_VCC.

R29.1 = 3.3V, R29.2 = M_VCC.

R33 (10 Ω) führt 3.3V an INA219 SOIC Pin8 (IN+).
R34 (10 Ω) führt M_VCC an INA219 SOIC Pin7 (IN-).
C31 (100nF) liegt parallel zu R29.
Die Polarität ist korrekt (TI INA219 Datenblatt, SOIC-Pinout).

M_VCC versorgt nach PCB-Netzliste ausschließlich:
- Vier Doppel-H-Brückentreiber TB6612FNG U34, U35, U36, U37,
  jeweils ihre VM-Pins 13/14/24.
- C36..C43, vier 100nF und vier 10uF nach GND.
- R34.1 als INA219-Senseleitung und C31.1 sowie R29.2.

Kein RP2040, ATtiny, KNX-Transceiver oder andere Logik bekommt
direkt Leistung von M_VCC. U34–U37 Pin19/STBY und Pin20/VCC
liegen jeweils an 3.3V; STBY ist fest HIGH und kann nicht per
Firmware abgeschaltet werden.

Die PCB-Pinzuordnungen sind plausibel:
- RP2040 GPIO10..17 => M1_EN..M8_EN (Pads13..18,27,28).
- RP2040 GPIO18/19 => gemeinsame Richtungen IN_1 / IN_2.
- Motor-PWM-Eingänge und IN1/IN2 an allen vier TB6612 stimmen mit
  diesen Netzen überein.

Der statische PCB-Netzabgleich kann keine tatsächlichen
Lötfehler, Kurzschlüsse, falsch bestückten Bauteile oder
beschädigten H-Brücken nachweisen.

Netzbericht:
C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX088_INA_IDLE\KNX088_STATIC_NET_AUDIT.json

## INA219 und Treiber-Datenblattprüfung

TI INA219 (https://www.ti.com/lit/ds/symlink/ina219.pdf):
- Pin8 ist IN+, Pin7 IN-; Busspannung referenziert IN- gegen GND.
- CONFIG=0x399F ist Werksdefault; PGA /8 hat ±320mV Range.
- Offset INA219A bei /8 maximal ±200uV = ±0,2mV.
- Shunt-Spannung zählt je 10uV/LSB; BUS je 4mV/LSB.
- 92,6mV sind etwa 463-mal der zulässige Offset eines
  unbeschädigten INA219A. Eine normale Offsetungenauigkeit
  erklärt den Wert somit nicht.

Toshiba TB6612FNG:
https://toshiba.semicon-storage.com/info/docget.jsp?did=10660&prodName=TB6612FNG
- Vier Dual-Bridge-ICs arbeiten an M_VCC; STBY ist fest HIGH.
- Normaler dokumentierter Versorgungsschaltkreis braucht
  typischerweise nur wenige mA pro Chip aus VCC, nicht
  463mA über VM bei abgeschalteten Motoren.
- Datenblatt definiert Stop/Hi-Z für IN1=IN2=LOW bei PWM=HIGH;
  für PWM=LOW bei IN1/IN2 LOW keine eigene Tabellenzeile.
  Die exakte physische Ausgänge-Hi-Z-Lage kann durch
  GPIO-STATUS allein nicht endgültig bewiesen werden.

Die Firmware liest INA219 Register 0x01 und 0x02, castet
Shunt zweierkomplementgerecht nach int16 und rechnet
signedRaw*10/200 mA. Das passt zu 200mΩ. Kein
Software-Kalibrierfehler nachweisbar.

## Plausibelste Fehlerursachen (noch Hypothesen)

1. **Echte ungewollte Motorrail-Last (wahrscheinlich, nicht
   unabhängig elektrisch bestätigt)**: partieller Kurzschluss
   auf M_VCC, beschädigte U34..U37, defekter C36..C43
   oder ein real nicht ausgeschalteter H-Brückenausgang.
   Bei 463mA wird ca. 1,46W auf M_VCC abgegeben.
2. **Reale INA219-/Sense-Strecken-Anomalie**: PCB-Lötfehler
   an R33/R34/U23 oder beschädigter INA219. Ein normaler
   ADC-Offset ist dagegen um Größenordnungen kleiner.
3. **Software-/Netlist-Irrtum**: nach Audit wenig wahrscheinlich.
   C31 kann nur AC-Signale überbrücken, keinen DC-Ruhestrom
   von 463mA erklären.

## Eine entscheidende physische Prüfung (später am Board)

Kein erneutes Flashen nötig. Bei stabilem, eingeschaltetem
Board und AUSgeschalteten Motoren:

1. DMM DC-mV: ROTE Spitze an **R29 Pad1/3.3V** und SCHWARZE
   an **R29 Pad2/M_VCC**.
2. Falls etwa **+92,6mV** messbar: echter Motorrail-Strom ~463mA;
   U34..U37, C36..C43 und M_VCC-GND-Bereiche thermisch/elektrisch
   untersuchen und tatsächliche GPIO-Pegel physisch kontrollieren.
3. Falls etwa **0..5mV**: echter Strom höchstens ~25mA;
   dann INA219 U23, R33, R34 bzw. deren Lötstellen prüfen.
4. Zur Gegenprobe R29.1 und R29.2 jeweils gegen PCB-GND
   messen: 3,241V und 3,148V sind nur INFERENZEN.
5. Keine Bauteile oder Motorstecker unter Spannung ziehen.

**Die Motorfreigabe bleibt bis zur Klärung der tatsächlichen
Shuntspannung gesperrt.** KNX085 bleibt installiert; M1 hat sich
bei dieser Diagnose nicht bewegt.

Das Audit findet keine Begründung, den bestätigten 200mΩ-
Widerstand umzudimensionieren oder die softwareseitige
Leerlaufgrenze von 25mA blind anzuheben.
