# Versorgungsarchitektur: KNX, USB und externes 5-V-Netzteil

**Stand:** 10.10.2026 (Entwurfs-/Entscheidungsdokument)

**Basis:** Hauptschaltplan und Leiterplattenexport V1.2; echte Bestueckung, Brueckenbelegung, Netzteil- und Lastmessungen **noch nicht verifiziert**.

## Anforderung aus der Projektplanung

Die acht Homematic-IP-Antriebe **HmIP-VDMOT** sollen einzeln angesteuert werden; jeweils maximal **ein** Motor darf laufen. Die Antriebe haben laut Hersteller **3,3 V DC** Versorgung und **120 mA maximale Stromaufnahme** (nicht einen garantierten Anschlagstrom). Ein zusaetzliches, kleines **externes 5-V-SELV-Netzteil** war als Loesung vorgesehen, falls die KNX-Busversorgung nicht fuer den Motor plus RP2040, Temperaturerfassung und HMI ausreicht.

**Es wurde bisher nicht nachgewiesen, dass KNX-only ausreicht oder nicht ausreicht.** Die beiden Varianten sind bewusst als Alternativen dokumentiert; Schaltplan und PCB bleiben unveraendert.

## 1. Bauteilgrenzen und Leistungsbilanz

| Bauteil / Groesse | Herstellerangabe oder Nachweis | Auswirkung |
| --- | --- | --- |
| U9 STKNX, Buck-DC/DC | maximal **150 mA am einstellbaren DC/DC-Ausgang**; V1.2 setzt ihn rechnerisch auf ca. 5,07 V | Obergrenze des Reglers, **nicht** identisch mit 150 mA vom KNX-Bus |
| STKNX KNX-Bus-Entnahme | bis zu **30 mA auf der KNX-Busseite**; Hersteller warnt, dass die 150 mA Buck-Ausgangsstrom je nach Buslastgrenze nicht voll nutzbar sind | Bus-Fan-in und Gesamtleistung begrenzen das reale Budget |
| U6 Traco TSR 1-2433 | Eingang **4,75–36 V DC**, Ausgang **3,3 V**, bis **1 A Ausgang** | Die 1-A-Angabe gilt nur bei ausreichender Leistung **vor** U6 |
| Antrieb HmIP-VDMOT | 3,3 V DC, **max. 120 mA** | Nenn-Leistungsobergrenze eines Motors: 3,3 V × 0,12 A = **0,396 W** |
| STKNX-Buck rechnerisch | 5,07 V × 0,15 A = **ca. 0,76 W** | Nur **ideales Reglerausgangsmaximum**; NICHT garantierte KNX-Leistung |
| Ausgangsreserve vor Wandlungsverlusten | 0,76 W minus 0,396 W = **ca. 0,36 W** | RP2040, STKNX, Anzeige, Sensorik, Verluste und Motoranlauf koennen die Reserve aufbrauchen |
| F1 | Auf dem Schaltplan **630 mA / 275 V**, im EasyEDA-MPN-Feld aber `S1032-F-60.0A` | Bestueckte Sicherung, ihre Kennlinie und relevante Nennwerte vor Einspeiseversuchen pruefen |

Damit ist die KNX-only-Stromversorgung **nicht automatisch unmoeglich**, aber fuer den Antrieb und die restliche Elektronik ohne Messung **nicht freigegeben**. 30 mA KNX-seitig bei typischerweise deutlich hoeherer Busspannung sind nicht mit 30 mA bei 5 V gleichzusetzen.

Quellen: [STKNX Hersteller und Datenblatt](https://www.st.com/resource/en/datasheet/stknx.pdf), [TSR 1 Datenblatt](https://www.tracopower.com/tsr1-datasheet), [HmIP-VDMOT Herstellerangaben](https://homematic-ip.com/de/produkt/stellantrieb-motorisch).

## 2. Tatsächlich im PCB V1.2 vorhandene Netze, Pads und Jumper

Die folgenden Verbindungen sind direkt aus `schematic/pcb_knx-valve-control_v1.2.json` ausgelesen, **keine geratenen Loetpunkte**:

| Bestandteil | PCB-Pad-/Netzzuordnung | Funktion |
| --- | --- | --- |
| L1 | 1: `DCDC_LX`; 2: `KNX_VCC` | STKNX-Wandlerausgang |
| **JMP1** | 1: `KNX_VCC`; 2: `R9_2` | **Zweipadiger, normalerweise offener Loetjumper** (`JMP-2-NO-0603`) im KNX-Versorgungspfad; **kein externer 5-V-Anschluss** |
| R9 | 1: `GND`; 2: `R9_2` | 100-kOhm-Widerstand zur Jumper-/MOSFET-Seite |
| Q1 AO3401A | 1: `USB_VCC` (Gate); 2: `5V_` (Source); 3: `R9_2` (Drain) | P-MOSFET in der Stromquellenumschaltung; sein tatsaechliches Durchschalt-/Rueckspeiseverhalten unter allen Quellen testen |
| USB1 | VBUS: `USB_VCC`; Ground: `GND` | USB-C-Speisung |
| D6 1N5819HW | 2: `USB_VCC`; 1: `5V_` | Schottky im USB-5-V-Pfad |
| F1 | 1: `5V_`; 2: `5V` | Auf Schaltplan mit 630 mA bezeichnet; reale Bestueckung offen |
| D1 1N5819HW | 2: `5V`; 1: `D1_1` | Weitere Schottky-Diode vor U6 |
| **U6 TSR 1-2433** | **Pin 1: `D1_1`**, Pin 2: `GND`, Pin 3: `3.3V` | Wandelt eine hinreichend hohe DC-Eingangsspannung in die gemeinsame 3,3-V-Schiene |
| **R29** | 1: `3.3V`; 2: `M_VCC` | Gemeinsamer Motor-Versorgungsshunt, laut Schaltplan 200 mOhm; MPN-Metadaten **widerspruechlich** |
| JMP2 / JMP3 | `KNX_RX`, `KNX_TX` und gekreuzte Varianten | **Kommunikationsjumper**, keine Versorgungsauswahl |

Beobachteter Strompfad (schematisch, nicht vollstaendige Baugruppe):

```text
KNX-Bus -> STKNX -> L1 -> KNX_VCC -> JMP1 -> Q1 -----.
                                                        |
USB-C -> USB_VCC -> D6 -------------------------------+-> 5V_
                                                        -> F1 -> 5V -> D1
                                                        -> D1_1 -> U6 (5V->3.3V)
                                                        -> 3.3V -> RP2040 + Sensorik
                                                        -> R29 -> M_VCC -> Motortreiber M1..M8
```

**Wichtige Besonderheit:** Der bestehende Anschluss `JMP1` trennt/aktiviert einen Zweig der KNX-Versorgung; er ist **keine** dreipolige KNX/USB/Extern-Umschaltung. Ein normales DuPont-Jumperkabel ist zudem etwas anderes als dieser winzige Loetjumper. Die as-built Stellung von JMP1 muss nachgemessen werden.

## 3. Warum 5 V nicht beliebig eingespeist werden duerfen

- **Nicht `M_VCC` mit 5 V versorgen:** Das wuerde direkt die fuer **3,3 V** ausgelegten Motortreiber/Motoren ueberversorgen und die Messarchitektur aendern.
- **5 V an `USB_VCC` sind nicht gleich 5 V an U6:** Der dokumentierte USB-Pfad enthaelt **D6 und D1 in Reihe**. Schon bei typischen Schottky-Spannungsabfaellen kann die U6-Eingangsspannung unter **4,75 V** liegen; unbedingt am **U6-Pin 1** unter Last messen.
- **5 V an `5V_` sind kein sicherer allgemeiner Einstieg:** D1 bleibt im Pfad. Q1 hat sein Gate an `USB_VCC`; bei Einspeisung direkt auf `5V_` (ohne USB-VBUS) kann die MOSFET-Vorspannung einen **Rueckspeisepfad Richtung `KNX_VCC` ueber JMP1** erzeugen. Ohne durchgemessene Quellentrennung **nicht verbinden**.
- **5 V an `5V`** umgehen F1, behalten aber den Abfall an D1. Diese Einspeisung ist **ohne eigenen Schutz und Nachweis** nicht freigegeben.
- **`D1_1` / U6-Pin 1 ist der direkte Eingang des 3,3-V-Wandlers**, der den D1-Abfall umgehen wuerde. Er ist jedoch **kein fertig geschuetzter, vorgesehener externer Versorgungseingang**. Erst mit definierter Einspeiseschaltung, Rueckspeisesperre/Power-ORing, eigener Sicherung, Verpolschutz und Messungen ein moeglicher Design-Eingriff.
- Externes Netzteil **isoliert und fuer SELV geeignet**; KNX-Bus, USB/GND und externer GND duerfen erst nach Pruefung der Topologie zusammengebracht werden. Eine externe Quelle nicht unbesehen parallel zu KNX/USB schalten.
- Der HmIP-VDMOT **bleibt an 3,3 V**. 5 V sollen *vor* einer geeigneten 3,3-V-Regelung liegen, nie direkt am Motor.

## 4. Zwei technische Varianten fuer die naechste Hardwareversion

### Variante A – Externes 5-V-Netzteil speist die gesamte 3,3-V-Platine (fuer Prototyp empfohlen)

```text
externes isoliertes 5-V-SELV-Netzteil
  -> neuer geschuetzter 5-V-Eingang + GND
  -> definierte Quellen-Umschaltung / niederohmiges Power-ORing
  -> VIN U6 (Netz D1_1), verifizierte Spannung >= 4,75 V
  -> 3,3 V -> R29/INA219 -> EIN ausgewahlter Motor
KNX-Bus versorgt/uebertraegt weiterhin STKNX-Kommunikation.
```

**Vorteile:** Keine Unterbrechung des gemeinsamen Shunts, alle acht Bruecken weiterhin gleich angeschlossen; ext. Versorgung versorgt auch RP2040/HMI. Die vorhandene U6-Regelung kann bei nachgewiesen ausreichender VIN verwendet werden. **Konzeptioneller Richtwert** fuer die Quelle: geregelte 5 V, etwa 1 A Reservierung, aber exakte Dimensionierung und Leitungsschutz erst nach Lastmessung. **Kein Anspruch**, damit eine schon vorhandene Steck-/Loetstelle ohne weitere Schaltung nutzen zu koennen.

**Zu klaeren:** Automatisches Zurueckfallen auf KNX-Versorgung waere fuer Motorfahrten gefaehrlich, falls die KNX-Versorgung zu schwach ist. Ein Eingang `ExternalPowerPresent` / `MotorPowerOK` und ein **Motor-Freigabesperre** bei Versorgungsausfall sollten im V1.3-Entwurf vorgesehen werden. Es ist noch keine solche eigene Quelle in der V1.2-Firmware abgebildet.

### Variante B – KNX betreibt Elektronik, externes Netzteil ausschliesslich Motoren

```text
KNX-Versorgung -> vorhandene 3,3-V-Logikschiene -> RP2040 + Sensoren + I2C
extern 5 V -> eigener 3,3-V-Regler -> neue MOTOR_3V3 -> R29 -> M_VCC
beide Pfade mit bewusst validierter gemeinsamer Bezugsmasse.
```

**Vorteile:** Starke Entkopplung von Motoranlauf und Logik; die Strommessung bleibt grundsaetzlich moeglich. **Nachteil:** Dazu muss die bestehende Leiterbahn `3.3V -> R29` gezielt aufgetrennt bzw. das PCB neu entworfen werden; noetige Quell-/Masse-, INA219-Common-Mode- und Resetchecks sind offen. Ausserdem muesste **KNX allein** die gesamte Logik sicher versorgen koennen – bislang unbewiesen.

**Entscheidung:** Fuer einen isolierten Prototypentest **Variante A priorisieren**. Variante B als Alternative zur PCB-Revision vorsehen, wenn ausdruecklich ein KNX-only-Logikbetrieb trotz fehlender externer Motorversorgung gewuenscht ist.

## 5. Mess- und Sicherheits-Gates (vor einer Bestromung durch Jumperkabel)

1. **Platine stromlos, fotografieren/identifizieren:** JMP1 bestueckt/offen? R29 tatsaechlich 200 mOhm? U25 tatsaechlich ATtiny3216? Wert/Typ F1? Positionen Q1, D1, D6, U6?
2. **Durchgang und Polaritaet stromlos pruefen:** Vorhandene Pad-Netz-Verbindungen anhand PCB vs. echter Platine abgleichen. Bei Loetjumper nicht annehmen, dass er bereits geschlossen ist.
3. **KNX-only & USB-only OHNE Motor:** Eingangs- und Railspannungen `KNX_VCC`, `USB_VCC`, `5V_`, `5V`, `D1_1` (VIN U6), `3.3V`, `M_VCC`, sowie KNX-Busstrom messen. Speziell Diodenabfall und Regler-Headroom bei Last beobachten.
4. **Externe Quelle zuerst ohne Motor:** Mit geschuetzter/abgesicherter SELV-Einspeisung, geregeltem Labornetzteil und passender Strombegrenzung den **geplanten, getrennten Eingang** qualifizieren. Spannung am U6-Pin 1, 3,3-V-Regelung und Stromfluss **in Richtung** KNX_VCC und USB_VCC pruefen.
5. **Nur bei stabiler Einspeisung:** Einen Motor anschliessen und mit konservativen Zeit-/Stromschutzgrenzen ausschliesslich EINEN Kanal testen; INA219-Messung mit unabhaengiger Strommessung vergleichen. Der 120-mA-Herstellerwert ist **keine** freigegebene Stall-Erkennung.
6. **Ausfallverhalten:** Extern 5 V weg bei KNX vorhanden, KNX weg bei extern 5 V vorhanden, USB an/ab, Neustart bei Motorlauf – immer Motor AUS, Status korrekt, keine Rueckspeisung.
7. Erst nach bestandenen Tests das **PCB V1.3** (externer 5-V-Klemmenanschluss, Power-Mux/Verpol- und Rueckspeiseschutz, Sicherung, Motor-Power-Good-Erfassung) festlegen.

**Hinweis zu Jumper-Wires:** Steck-/Jumperleitungen eignen sich fuer strombegrenzte Laborversuche mit gegen Kurzschluss gesicherten Testanschluessen. Die vorhandenen 0603-Loetjumper sind **keine DuPont-Buchsen**, und eine dauerhafte Versorgung benoetigt geeignete Klemmen, Zugentlastung und Schutzbauteile.

## 6. Offene Entwurfsentscheidung

- Soll der Controller **ganz** ueber externe 5 V versorgt werden (KNX weiterhin als Kommunikation), oder sollen **nur Motoren** eine getrennte Versorgung erhalten?
- Soll bei fehlendem externen 5 V noch KNX-Kommunikation moeglich sein, aber ohne Motorbewegungen? Falls ja, Variante B bzw. passende getrennte Backup-Architektur pruefen.
- Soll ein automatisches Umschalten der 5-V-Quellen vorgesehen werden, oder ein absichtlich **mechanisch/jumperbasiert exklusiver** Betriebsmodus?

Fuer die V1.2-Platine wurden **keine Loet-, Netz-/PCB-, Software- oder Stromversorgungs-Aenderungen durchgefuehrt**. Dieses Dokument ist ausschliesslich ein belastbarer Auslegungs- und Messplan.

## KNX033 reale D1- und F1-Aenderung (13.10.2026)

Die vorangehende Beschreibung behandelt die urspruenglich **eingezeichnete D1-Diode**. Die neue fotografierte V1.2-Platine hat an `D1` stattdessen eine Drahtbruecke von `5V` nach `D1_1/U6 VIN`: Der Vorwaertsabfall an D1 entfaellt, **aber auch die D1-Rueckwaertssperre**. Q1/JMP1, D6, F1 bleiben als separate, nicht auf Rueckspeisungsfreiheit gepruefte Elemente bestehen. **Foto F1 `T 2,5 A / AC250V`**, Schematicsoll `630 mA / 275 V`: Schutzfunktion vor jedem Power-On neu koordinieren, nicht aus der Zeichnung eine passende Sicherung ableiten. U6 (TSR 1-2433) und Anschlussseite sind auf Frontfotos nicht sicher erkennbar. Die PCB-Herstellerteilenummer fuer die entfernte D1 ist `1N5819HW-7-F`; der Schematic-JSON-D1-Kommentar nennt dagegen `SL1MDIO` (BOM-Labeldifferenz, nicht Netzzuordnung). Mess- und Bildnachweis steht in [KNX033](KNX033_AS_BUILT_PCB_REVIEW.md).
