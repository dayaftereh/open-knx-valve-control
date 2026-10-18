# KNX082 – Hardware-Umbau und Wiederaufnahme nach KNX081

**Stand: 18.10.2026.** **Umbau vom Nutzer angekündigt, noch nicht live verifiziert.**
Arbeitsrechner: LLO Home. Diese Dokumentation ändert keine ETS-Parameter,
Firmware, KNX-Ausgänge oder Motoren. Die geplante Hardware-Verkabelung
wird erst bei der nächsten Rückmeldung neu überprüft.

## 1. Abgenommener letzter Zustand

**KNX081: physikalischer TP1-Sendepfad bis zur MDT KNX/IP-Schnittstelle PASS.**
Testplatine ist am Ende der Kellerlinie **1.3** hinter dem Lichtschalter
im Lager. Im Original-ETS-Projekt vom 12.10.2026 ist **1.3.250** auf
dieser Linie nicht belegt. Linienkoppler **1.3.0** ist für
Gruppentelegramme in beide Richtungen auf Durchleiten gestellt.

- Genau ein GroupValueWrite (1 Bit = 0), Quelle 1.3.250,
  Ziel/Test-GA 29/7/241; TP1-Nachricht: BC 13 FA EF F1 D1 00 80 E5.
- PicoScope B an KNX_TX/JMP3: **48/48 HIGH-Impulse à 35 µs**;
  Bitpositionen innerhalb 1 µs, 0 verlorene Messdaten.
- PicoScope A an KNX+ gegen gemeinsame KNX-/GND-Referenz:
  gleichzeitige Spannungseinbrüche von **7,44–7,88 V**.
- Unabhängiger A-Kanal-Decoder: alle neun Bytes, Parität,
  Start-/Stopbits, XOR-FF-Prüfsumme und Bus-ACK 0xCC gültig.
- MDT KNX/IP-Tunnel: exakt **ein passendes Telegramm empfangen**,
  18.10.2026 21:19:05 MESZ, 1.3.250 -> 29/7/241, Write 0.
- Gegenrichtung IP -> Platinen-RX wurde separat in KNX071 nachgewiesen.
- Kein wiederholtes Telegramm, keine ETS-Änderung, kein Motorbefehl.
- KNX078 wurde mit der linienfremden Quelle 1.0.250 nicht durch
  den IP-Monitor gesehen; 1.3.250 löste das Sichtbarkeitsproblem im Test.
  Die interne Kopplerentscheidung des alten Versuchs wurde nicht gemessen.

Vollbeleg: [KNX081 Abnahme](KNX081_KELLER_TP1_TX_KNXIP_ACCEPTANCE_20261018.md).
Original-PicoScope-ADCs, IP-JSONL, Event-CSV und zwei Kurven
(full.svg und zoom.svg) bleiben **privat in Downloads auf LLO Home**,
nicht als Rohdaten im Git-Repository.

## 2. Aktuell installierte Software

Der RP2040 U18 führt **KNX081 PIO Einzeltelegramm-Diagnosefirmware** aus,
nicht die integrierte ETS-/Ventilreglerfirmware.
Zuletzt bestätigte USB-CDC-Antwort am LLO Home (bisher COM8):
KNX081 STATUS tx_low=1 pio_ready=1 armed=0 attempted=1 collision=0.
Die Software sendet nichts automatisch. Ein weiterer Sendeversuch
ist bis zu einem RP2040-Neustart gesperrt; auch nach einem Neustart
ist explizites ARM FRAME + FIRE FRAME erforderlich.

**BOOTSEL:** Der Nutzer möchte beim nächsten Aufbau den RP2040 in BOOTSEL
setzen. Dann erscheint normalerweise RPI-RP2/USB-ID 2E8A:0003 statt
der Firmware-CDC-Schnittstelle 2E8A:000A. Ein BOOTSEL-Neustart setzt
flüchtige One-Shot-Statusdaten zurück. Ein sicherer KNX_TX-Pegel
während Reset/Boot-ROM ist ohne erneute Messung nicht garantiert.
Nicht automatisch UF2 kopieren, flashen oder KNX-Nachrichten auslösen.

Die isolierte KNX081-Firmware steuert **weder reale Motoren noch liest sie
T0/T1-Temperaturen**. Vor einem kombinierten Test brauchen wir eine
für STKNX und Mehrquellenbetrieb geprüfte Firmware. Ältere
KNX042-LED-Diagnosen verlangen abgezogenen KNX-Bus, und die alte
Produktfirmware besitzt eine ungeeignete UART-TX-Ruhestellung.

## 3. Angesagter physischer Umbau (alles PENDING bis live geprüft)

Der Nutzer möchte das **PicoScope (A und B) abziehen**, die Platine weiter
auf dem KNX-Bus der Kellerlinie 1.3 und über **USB-C** betreiben,
den **Units V1.2/CH340G-UPDI-Programmer** wieder mit dem ATtiny verbinden,
**zwei Motoren** an M1/M2 und **zwei DS18B20** an T0/T1 anschließen.
Nach dem Umstecken meldet er sich zurück und setzt BOOTSEL.

| Anschluss | Elektrische / logische Zuordnung | Status |
| --- | --- | --- |
| KNX TP | Kellerlinie 1.3, über Linienkoppler 1.3.0 | bisher live PASS, nach Umbau erneut prüfen |
| USB-C | RP2040 U18, Runtime 2E8A:000A / BOOTSEL 2E8A:0003 | neu zu prüfen |
| Units Programmer V1.2 | CH340G USB 1A86:7523, 2x3 CN1 -> ATtiny U25 UPDI | noch nicht wieder angesteckt / nicht geprüft |
| T0 DS18B20 | ATtiny3216 PA5, zentraler Vorlauf | Nutzer will anschließen |
| T1 DS18B20 | ATtiny3216 PA6, Rücklauf zu M1 | Nutzer will anschließen |
| M1 | M1+/M1-, TB6612 U34, Enable RP2040 GPIO10 | Nutzer will anschließen, Fahrt NICHT freigegeben |
| M2 | M2+/M2-, TB6612 U34, Enable RP2040 GPIO11 | Nutzer will anschließen, Fahrt NICHT freigegeben |

**Wichtige Anschlussdetails:**

- T0/T1 sind unabhängige **3-Draht-1-Wire**-Ports mit
  Datenleitung, GND und 3,3-V-Versorgung. Pinreihenfolge, Polarität
  und Pull-ups vor dem Einschalten mit V1.2-Schaltplan abgleichen;
  keine DS18B20-/Motor-Stecker unter Spannung umstecken.
- Der ATtiny3216 wurde am 14.10.2026 bereits per UPDI mit
  Signatur **1E 95 21** identifiziert; der ATtiny-Temperatur-UART
  zum RP2040 wurde damals **ohne angeschlossene Sensoren** real geprüft.
  [KNX039](KNX039_LIVE_UPDI_READBACK.md),
  [KNX040](KNX040_REAL_TEMPERATURE_UART.md).
- Der interne Temperaturdatenlink ist RP2040 **GPIO8 TX -> ATtiny PA2 RX**
  und **GPIO9 RX <- ATtiny PA1 TX**, 115200 Baud, 8N1,
  sequenz- und CRC16-geprüft. Die CN1-TXD/RXD-Pins des Programmers
  sind **nicht** diese UART-Snapshot-Leitung.
- CN1 ValveControl 2x3: **Pin 1 = 5V**, Pin 2 = RXD, Pin 3 = UPDI,
  Pin 4 = TXD, Pins 5/6 = GND. ATtiny U25 VDD ist **3,3 V**.
  Bei gleichzeitigem KNX, USB-C und CH340-Programmer besteht ein
  **Rückspeise-/Pegelrisiko am CN1-Pin 1**. Kabelrichtung/Pin1,
  GND, 5-V-Verbindung, Versorgungstrennung und UPDI-Pegel prüfen,
  bevor alle Quellen gleichzeitig verbunden werden.
- Der Programmer ist für den **ATtiny**, nicht für RP2040-SWD.
  Den USB-COM-Port des CH340G neu erkennen; bisherige Desktop-COM4-
  oder Home-COM8-Zuordnungen NICHT blind weiterverwenden.
- M1/M2 haben **gemeinsame Richtung GPIO18 (IN_1)/GPIO19 (IN_2)**,
  gemeinsames INA219-/R29-Strommesskonzept und M_VCC; **nie beide
  gleichzeitig bewegen**. Auf V1.2 ist TB6612-STBY fest auf 3,3 V
  und bietet keine unabhängige globale Motor-Ausgangssperre.
  Eine blinkende LED oder simulierte Motor-Queue beweist noch
  keine sichere Ventilfahrt.

## 4. Wiederaufnahme nach der Nutzer-Rückmeldung

**A. Zuerst nur Zustand aufnehmen.**
Agent-Ping, neue Session, Git/HEAD und COM-Enumerierung prüfen.
Auf dem RP2040 unterscheiden: BOOTSEL-Laufwerk RPI-RP2
gegen aktive CDC-Testfirmware. CH340G/UPDI getrennt identifizieren,
KNX/IP-Linienbezug 1.3 beibehalten. Keine stillen
Flash-/KNX-/ETS-Kommandos oder Motorbewegungen.

**B. Neue Mehrquellenversorgung und UPDI beurteilen.**
Bei abgeklemmter Versorgung Sicht-/Durchgangstest von CN1-Pin1,
GND/Pin1-Ausrichtung, R29, U6, D1 und F1; danach Spannung,
Stromaufnahme und 3,3-V-Pegel unter kontrollierten Bedingungen.
Der frühere Programmer-Readback war erfolgreich, ist aber keine
Freigabe für gleichzeitig angeschlossenes KNX+USB+CH340.
Anschließend höchstens **read-only UPDI Signatur/Status**,
kein ungefragtes erase/write/fuse oder EEPROM-Reset.

**C. Temperatur zuerst, motorlos.**
Aktuelle ATtiny-Firmware und RP2040-UART-Snapshotweg mit
geeigneter KNX-bussicherer Diagnose prüfen; echte Sensorwerte
T0 und T1 erst melden, wenn OneWire-Erkennung, CRC,
Validitäts-/Fehlerflags und Alter stimmen.
NoSensor, PowerOn85 und ungültige Werte nicht als 0,00 °C melden.
Dazu [KNX013](KNX013_ATTINY_SAMPLER.md),
[KNX014](KNX014_UART_BRIDGE.md) und
[KNX041](KNX041_TEMPERATURE_BRIDGE_READY_FIX.md) beachten.

**D. Motor-Test nach gesondertem elektrischen GO.**
Nennspannung und Strom der beiden physischen Antriebe,
M_VCC/R29/INA219, tatsächliche Treiber-/Motorpolung,
Laufrichtung, Endanschlag, unabhängige Stop-Möglichkeit
und Reset-/Brownout-Verhalten bestätigen. Danach jeweils
**nur M1**, definierte kurze Fahrt, All-off / STOP / Stromdaten;
**erst danach M2**, nie gleichzeitig. Voriger
[KNX042 LED-Test](KNX042_MOTOR_LED_BRINGUP.md) ist keine
Qualifikation für echte Motorventile.

## 5. Weiterhin offene Hardware-Gates

- R17 Pull-up an STKNX KNX_TX **entfernt lassen**:
  TX-Ruhepegel LOW, aktive HIGH-Pulse nur ca. 35 µs.
- U11 68 Ohm/2W wurde früher heiß; reale Dauerlast und
  thermische Unversehrtheit sind nicht unabhängig geprüft.
- D1 ist auf dem As-built-V1.2-Board überbrückt, F1 hat
  einen vom Sollwert abweichenden Aufdruck (T2,5 A versus
  nominell 630 mA). USB-/KNX-/Programmer-Rückspeisung offen.
- U9 VCCCORE unter tatsächlich versorgtem KNX wurde bislang
  nicht separat per DMM bestätigt (USB-only C1 zuvor 0,30 V).
- KNX081 PicoScope B zeigte einen kurzen **4,014-V-Peak**
  beim 47. Impuls, der normale HIGH-Pegel lag um 3,32 V.
  Möglicher kurzer Überschwinger: vor Produktfreigabe beurteilen.
- STKNX TX / Motortreiber müssen auch in Reset, BOOTSEL und
  Versorgungsausfall sicher bleiben. Eine Software-STOP-Routine
  ersetzt keine unabhängige Hardwaresperre.
- Der experimentelle KNX081-TP1-Test bestätigt die physikalische
  und IP-seitige Kommunikation, NICHT schon eine parametrierbare
  ETS-Produktapplikation oder eine motorische Dauerfreigabe.

## 6. Git-Übergabe

Vor diesem KNX082-Handover war das lokale Git-Repository
auf **main**, HEAD **34c3927** und CLEAN, mit sieben lokalen
Commits gegenüber dem damaligen origin/main (KNX070, 071,
072, 076, 077, 078, 081). Am 18.10.2026 wurde origin/main
frisch gefetcht, ohne Remote-Änderungen gegenüber dem vorigen
Stand. Mit dem Nutzerauftrag ist ein **normaler Fast-Forward-Push
nach origin/main** jetzt ausdrücklich genehmigt; kein Force-Push
und keine Änderung fremder Commits. Den tatsächlichen
Remote-HEAD nach dem Push separat live verifizieren.

**Handover-Satz für den Folgetermin:**
KNX082: Keller-TP1 1.3, KNX081 TX->KNX/IP PASS,
Test-IA 1.3.250, Test-GA 29/7/241. PicoScope entfernt;
Nutzer wird Units-UPDI/CH340, DS18B20 T0/T1 und Motoren
M1/M2 anschließen und den RP2040 in BOOTSEL setzen.
Zuerst tatsächliche USB-/Programmer-/Versorgungszustände
und Sensoreingänge prüfen, keine unaufgeforderte Fahrt,
kein unaufgeforderter KNX-Sendebefehl.
