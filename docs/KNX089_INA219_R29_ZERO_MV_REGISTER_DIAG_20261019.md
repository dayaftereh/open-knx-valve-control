# KNX089 – INA219 Registerdiagnose nach R29-Messung 0,00 mV

Stand: 19.10.2026, LLO Home, OpenKNXValveControl V1.2.

Der Nutzer hat **0,00 mV DC direkt über R29** gemessen und bestätigt die
Bestückung 200 mΩ / 1 W. Der zuvor berichtete Motorrail-Strom von ca.
463 mA ist damit nicht als tatsächliche Stromaufnahme anzusehen:
0,463 A würde an 0,200 Ω einen Abfall von 92,6 mV erzeugen.

## Software und echte I²C-Messung

Die ursprüngliche KNX085-Firmware liest INA219 0x00 beim Start, zeigt
dessen Wert später aus einer Cachevariablen, liest 0x01 (Shunt-Rohwert)
und 0x02 (Busspannung). Sie schreibt vor der Diagnose keinen eigenen
Calibration-Wert. 0x399F ist laut TI INA219 die Default-Konfiguration;
für die manuelle Umrechnung aus 0x01 ist Calibration 0x05 nicht nötig.

Zwölf KNX085-Liveabfragen zeigten CONFIG 0x399F, read_ok=1,
bus_mv ca. 3148, rechnerisch 463 mA, alle Motor-GPIO LOW.

## Motor-gesperrte Firmware KNX089 installiert

- Quellen: tools/knx089_ina_regdiag
- Compile-Time Motor-Gate: 0; keine Motor- oder KNX-Sendeaktion.
- Built image size: 243200 Bytes.
- UF2 SHA256: 4715C992FC1BA61D90720A3B463AC172CD6499660A3D13ED3678793DB916BAEF.
- Einmal per kontrolliertem UF2-Bootloader auf den RP2040 geflasht,
  USB COM8 und bekannte Seriennummer verifiziert, PIN LOW,
  Motor-Gate=0, State IDLE.
- Der erste Versuch des Flash-Hostprogramms scheiterte an einem zu
  strengen STATUS-Regex noch VOR dem BOOTSEL-Wechsel; danach korrigiert.
- Die bereits installierte KNX085-Motor-Testfirmware wurde für diese
  Diagnose durch KNX089 (MOTOR LOCKED) ersetzt.

Live-Registerdump mit zwei I²C-Ausleseverfahren:
- Register 0x00 CONFIG: 0x399F
- Register 0x01 SHUNT: 92,59 mV vor INA-ADC-Reset;
  92,63 mV danach. Ein erster Dump ergab 92,62 mV.
- Register 0x02 BUS: 3148 mV.
- Register 0x03 POWER: 0x0000.
- Register 0x04 CURRENT: 0x0000.
- Register 0x05 CALIBRATION: 0x0000 (normal ohne Kalibrierung).
- Konfiguration und Kalibrierung sind in STOP- und
  Repeated-START-I²C-Lesungen identisch. Bei den kontinuierlichen
  ADC-Registern sind wenige LSB Unterschied zwischen zwei
  zeitlich versetzten Abfragen normal.
- Über I²C veranlasster INA219-ADC-Reset (nicht MCU-Reset)
  quittiert mit Code 0, anschließendes CONFIG 0x399F,
  Shuntwert weiterhin ca. 92,6 mV.
- Danach KNX-RX, T0..T3, USB und Motor-Idle erneut live bestätigt.

Damit ist die digitale Registerkommunikation funktionsfähig und die
Konfiguration plausibel. Die **physische analoge Shunt-Spannung
unterscheidet sich von der vom INA219 als 92,6 mV gemeldeten**.

## Nächster gezielter physischer Test

Zwischen den Eingängen des INA219 messen, vorzugsweise an den
Messanschlüssen hinter den beiden 10-Ω-Serienwiderständen:
rote Prüfspitze an R33 Pad2 (U23 Pin8 IN+), schwarze an
R34 Pad2 (U23 Pin7 IN−), Messgerät DC mV. Nur mit geeigneten
feinen isolierten Prüfspitzen; keine benachbarten Pads verbinden.

- Nahe 0 mV an R33/R34 wie an R29: U23 INA219 selbst oder
  dessen Analogfrontend verdächtig.
- Ca. 92,6 mV an R33/R34 trotz 0 mV an R29:
  R33/R34/Sense-Leiterbahnen, Lötverbindungen und Leckpfad
  untersuchen.

Kein Motorversuch mit unplausibler Stromschutz-Messung.
Für spätere Motorversuche KNX085-unlocked erst nach Abschluss
der INA219-Reparatur kontrolliert wieder installieren.

Belege im LLO-Home-Ordner:
C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX089_R29_0MV

Dateien:
- KNX089_INA_READ_ONLY_20261019_171744.json
- KNX089_FLASH_20261019_172543.json
- KNX089_REGISTER_DIAG_20261019_172552.json
- KNX089_REGISTER_DIAG_20261019_172728.json

TI INA219: https://www.ti.com/lit/ds/symlink/ina219.pdf
(Abschnitte 8.5 und 8.6).
