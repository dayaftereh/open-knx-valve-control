# KNX035 – STKNX KNX_TX-Startpegel: R17 Pull-up und UART-Konflikt

**Stand: 14.10.2026. Status: bestätigter Designkonflikt, reale Fehlerursache noch nicht elektrisch nachgewiesen.** Diese Analyse folgt einem realen Busüberlastungsereignis. **Kein erneuter KNX-, 5-V-/USB- oder UPDI-Anschluss bis zur separaten Freigabe; keine Motoren.**

## 1. Aktuelle Evidenz

Der Nutzer berichtet, dass nach Anschluss von KNX und 5 V der Leistungswiderstand **U11 sehr heiß** wurde und der Bus offenbar zusammenbrach. Danach wurden beide Einspeisungen getrennt.

**U11 ist nach Nutzerangabe real mit 68 Ω bestückt**, passend zur V1.2-Schaltplanangabe **68 Ω / 2 W**. Die zur Footprint-Auswahl hinterlegte PCB-Herstellerteilenummer HoJLR2512-3W-3.5mR-1% meint allerdings einen 3,5-mΩ-Widerstand und ist ein **BOM-Metadatenfehler, kein nachgewiesener Bestückungsfehler**. U11 wurde noch nicht ohmisch nachgemessen. JMP1 ist laut jüngster Nutzeraussage ausgelötet/offen; es fehlen protokollierte Messwerte. JMP1 unterbricht nur den KNX-Versorgungszweig, **nicht** KNX_TX.

Das tatsächlich bestückte Blink-Programm wurde nicht ausgelesen. Nicht behaupten, dass es den UART aktiv betreibt. Auch U9 und U11 könnten nach der Überhitzung beschädigt sein.

## 2. Source-level-Netzprüfung

| Referenz | Schaltplanwert bzw. PCB-Padnetze | Erkenntnis |
| --- | --- | --- |
| **R17** | 10 kΩ, Pin 1 KNX_TX, Pin 2 3.3V | Externer Pull-**up** an aktiv-HIGH Sendepin |
| **U9 STKNXTR** | Pin 24 KNX_TX, Pin 3 R68, Pin 11 KNX_A | Direkter STKNX-Transceiver |
| **U11** | 68 Ω / 2 W Soll, PCB Pin 1 R68, Pin 2 KNX_A | Stromsenkpfad, 68 Ω real vom Nutzer gemeldet |
| **JMP3** | Pad 2 KNX_TX / Pad 3 KNX_TX' | Verbindung zum RP2040 (Brückenbelegung vor Ort prüfen) |
| **U18 RP2040** | Pad 2 KNX_TX' / GPIO0 | Dessen Boot-/GPIO-/UART-Betriebsart beeinflusst TX |

**ST-Datenblatt:** [DS12399 Rev.3, S. 13 und S. 16](https://www.st.com/resource/en/datasheet/stknx.pdf), Abschnitt 5.1.1 und IKNX_TX in Tabelle der Kennwerte:

- **LOW** am KNX_TX = **inaktiv**, KNX-Logik 1, Busruhe.
- **HIGH für 35 µs**, dann **LOW für 69 µs** = aktiver KNX-Logik-0-Busimpuls.
- KNX_TX besitzt einen **schwachen internen Pull-down (typisch 6 µA)**.
- Während aktivem Impuls zieht U9 Busstrom durch den Pfad R68 und U11.

R17 speist bei 3,3 V rechnerisch ungefähr **330 µA**, deutlich mehr als 6 µA interner Pull-down. Wenn RP2040 GPIO0 hochohmig bleibt, ist **HIGH** am U9 KNX_TX sehr wahrscheinlich. Das passt zum heißen U11, ist aber noch nicht direkt an Pin 24 gemessen.

## 3. Zwei getrennte Fehler, beide vor KNX-Betrieb lösen

**A. Fehler im Reset-/Ruhestrom-Hardwarebias:** Den **R17-Pull-up stromlos entfernen**. Danach kann der STKNX-eigene Pull-down mit hochohmigem RP2040-Pin für LOW sorgen. **Das garantiert KEIN LOW**, wenn der RP2040-Pin aktiv HIGH oder UART-Idle-HIGH ausgibt. Kein Busanschluss allein wegen ausgelötetem R17.

**B. Derzeitige, nur offline getestete KNX-Firmware ist keine STKNX-Phy:** In src/controller/main.cpp wird die Schnittstelle folgendermaßen aufgebaut:

    platform.interface(new TPUart::Interface::ArduinoSerial(Serial1));

Die lokale TPUart-Bibliothek verwendet SERIAL_8E1 und probiert 19200/38400 Baud. Eine normale UART-TX-Leitung hat im Leerlauf **HIGH**. STKNX erwartet dagegen LOW und direkte 35-µs-Sendepulse. Die vorbereitete Firmware gehört damit **nicht ungeprüft an die reale KNX-Leitung**. Der Nutzer hat derzeit ein gesondertes Blink-Programm; dessen Pinzustände sind nicht belegt.

## 4. V1.2 – stromlose Korrektur und Prüfgrenze

1. **KNX, USB, Laborversorgung, UPDI, alle Motoren trennen und Kondensatoren entladen lassen.** Nach U11-Überhitzung U9/U11 und den KNX-Eingangsbereich auf sichtbare Schäden prüfen.
2. **R17 stromlos entfernen**; Lötpads und benachbarte Kontakte sorgfältig kontrollieren, kein Lötzinnkurzschluss. Die **bisherigen beiden R17-Pads NICHT mit einem Pull-down bestücken**: eines ist direkt mit 3.3V verbunden.
3. Nur **spannungsfreie** DMM-Kontinuität und V1.2-Netze prüfen; tatsächliches KNX_TX-Ruheniveau ist erst nach einer gesonderten sicheren, motorlosen Spannungsprüfung messbar.
4. **Kein sofortiger KNX-Retest.** Erst definierte TX-LOW-Ruhelage bei Reset, laufendem Programm, Brownout und unabhängigem KNX-/5-V-Anlauf; U9/U11 nach thermischer Belastung separat bewerten. Der frühere F1-Wert T2.5A gegen 630mA und D1-Bypass-/Backfeed-Gates sind weiterhin offen.

## 5. ECO-Vorschlag für V1.3 (noch nicht im Schematic/PCB umgesetzt)

- R17 **Pull-up entfernen**; stattdessen an **KNX_TX gegen GND** nahe U9 Pin 24 einen externen **4,7-kΩ- bis 10-kΩ-Pull-down** vorsehen. Alte R17-Landepads verbinden KNX_TX mit 3.3V und können nicht unverändert dafür verwendet werden.
- Echte **fail-LOW TX-Freigabe** erwägen: Hardwaregatter oder Treiber mit definierter Inaktivität beim Reset/Brownout; hoher GPIO-Pegel darf den STKNX nicht versehentlich dauerhaft einschalten. Pull-down allein überstimmt kein aktiv HIGH treibendes GPIO.
- Firmware-KNX-Transport für **STKNX direkte Puls-Ansteuerung** neu entwerfen (z. B. RP2040 PIO/Timer) und die korrekten 35-µs/69-µs-Pegel, Empfang, KNX-Timing, Wake-/Reset- und Fehlerzustände zunächst **offline** verifizieren. Normale TPUart/SERIAL_8E1-TX-Dauer-HIGH ist inkompatibel.
- U11-Herstellerteilenummer in einer **separaten** neuen BOM-/PCB-Revision auf einen **realen 68-Ω-Leistungswiderstand** korrigieren; passenden Footprint und ≥2 W unabhängig verifizieren.
- U9-U11-Übertemperatur, F1 2,5A vs. 630mA und D1-Bypass-/USB-KNX-Rückspeisung als eigenständige sicherheitskritische Freigabepunkte beibehalten.

**Ergebnis: ELECTRICAL_TX_IDLE_HAZARD_OPEN.** R17 wurde bislang **nicht** als vom Nutzer ausgelötet bestätigt; tatsächlicher LOW-Pegel am STKNX nicht gemessen. Der überhitzte U11 und U9 sind noch nicht erneut geprüft. Keine Power-, Bus-, Flash- oder Motorfreigabe aus diesem Dokument ableiten.

## Nachtrag 14.10.2026: R17 laut Nutzer ausgelötet

Der Nutzer hat am 14.10.2026 berichtet, dass er R17 ausgelötet hat. Die PCB-V1.2-Designdaten enthalten den urspruenglichen 10k Pull-up weiterhin als historische Design-Referenz. **Tatsaechliche Widerstands-/Kontinuitaetsmessung U9 KNX_TX zu 3.3V, freies R17-Pad, U11-Zustand und TX LOW bei RESET/BOOTSEL/Brownout stehen aus.** Das alleinige Ablöten R17 erteilt keine KNX-Busfreigabe. [Home KNX043 R17-Plan](KNX043_R17_REWORK_TO_RX_FLASH.md).
