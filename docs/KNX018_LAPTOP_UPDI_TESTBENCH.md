# KNX018 – Geplanter Laptop-Teststand mit KNX/IP, RP2040 und RTS-UPDI-Programmer

**Stand: 12.10.2026.** **NICHT aufgebaut und NICHT elektrisch freigegeben.** Diese Planung ist für den späteren Laptop-Umzug verbindlich, keine Anschluss- oder Flashfreigabe.

## 1. Zielbild

    ChatGPT -> dedizierter ASH-Laptop-Agent
                     |
               Windows-Laptop
                  |        |                 |
              Ethernet   USB RP2040      USB CH340G (Units Programmer V1.2)
                  |        |                 | RTS: UPDI/UART
              KNX/IP      |                 +-- 2x3 CN1 -> ATtiny UPDI
                  |        |                                    |
            separater    OpenKNX ValveControl V1.2 <- UART ALT1  DS18B20 T0..8
             KNX-TP                   |
              Testbus              spaeter M1+/M1- (nur nach KNX002-006)

**Nutzer-Ziel:** Den Laptop in das Netz der vorhandenen KNX/IP-Schnittstelle stellen. Die echte Platine einmal per USB mit dem RP2040 und einmal per USB über den RTS-umschaltbaren UPDI-Programmer mit dem ATtiny verbinden. Sensor T0 (Vorlauf) und bis zu T1–T8 (8 Rückläufe) mit Dallas/1-Wire DS18B20 oder kompatiblen Fühlern ausrüsten. Dann Ende-zu-Ende bis ETS6/KNX prüfen; einen einzigen realen Ventilantrieb erst zuletzt und erst nach Sicherheitsfreigabe an M1.

## 2. Nachgewiesene Dateiquellen und Hostzustände

| Teil | Nachweis bzw. offener Punkt |
| --- | --- |
| OpenKNX-Projekt | Desktop C:\ASH\Workspace\Projects\open-knx-valve-control, main. Bei Abschluss KNX022 HEAD 3b47fa7, **26 lokale Commits vor origin/main**. Der Laptop darf nicht bloß veraltetes origin/main übernehmen |
| Desktop-Agent | ASH Local Agent 0.8.1, Entwicklung und Offline-Simulation |
| Laptop-Agent | ASH Local Agent 0.7.9 erreichbar, Windows; C:\ASH\Workspace\Projects vorhanden. OpenKNX-Projekt **noch nicht** auf Laptop. Ethernet 2 aktiv, aber KNX/IP-Verbindung **nicht** getestet |
| Laptop USB/COM | Zuvor nur COM3 Intel AMT SOL nachgewiesen; RP2040/CH340G/USB-UPDI **noch nicht als real angeschlossene Geräte erkannt** |
| Programmer Layout | Desktop C:\ASH\Workspace\Projects\Units\schematic\updi\pcb_updi_programmer_v1.2.json und sch_updi_programmer_v1.2.json |
| Programmer Software | Desktop Units: assets/init_updi.py, assets/autodetect_port.py, src/updi/platformio.ini, configurator/src/app/services/firmware/serial-updi-programmer.service.ts |
| Laptop Units | C:\ASH\Workspace\Projects\Units ist **älter** als Desktop Units; neuer V1.2-TypeScript-Service/Schaltungsstand dort nicht nachgewiesen |
| Zielcontroller | Schaltplan und src/temperature/temperature.ini verlangen ATtiny3216, PCB-Herstellerteilenummer U25 nennt aber ATTINY1616-SN; die **physische Chipkennung fehlt** |
| Firmware-Funktion | RP2040 Serial1 = KNX TP, Serial2 UART1 = T_TX/T_RX. ATtiny firmware Serial.swap(1) USART0 ALT1 PA1/PA2 für RP2040-Snapshots (115200 Baud, 8N1, CRC) |

## 3. RTS-Umschaltung des Units V1.2 Programmers

PCB V1.2: U1 CH340G, U2 und U7 SN74LVC1G3157 (Schalter), RTS-Netz jeweils an Pin 6 des Schalters; serielle TXD/RXD-Zweige werden auf UPDI bzw. UART umgeschaltet.

| Hostmodus | Aus dem vorhandenen Units-Quellcode | Nutzung |
| --- | --- | --- |
| UPDI | WebSerial-Service setzt requestToSend: true und dataTerminalReady: true, 115200 Baud, 8E2; prüft Device-ID vor Erase/Write | UPDI-Programmiermodus per RTS-Auswahl |
| CLI-Upload | PlatformIO nutzt pymcuprog --tool uart und --uart COM-Port, Datei über upload_command | Erst nach verifiziertem Chiptyp und sicherer Versorgung |
| UART | PlatformIO monitor_rts = 0 mit Kommentar RTS high for TX/RX | Umschaltung auf seriellen TX/RX-Monitor |
| USB/Port schließen | Service deaktiviert RTS/DTR bei Close | Elektrische Reset-/Power-Zustände müssen separat verifiziert werden |

**Wichtig:** USB-Treiber/APIs nutzen logische RTS-Assertion, der CH340G-Pin ist RTS# aktiv-low bezeichnet. Elektrische Pegel und Schalterposition vor dem Anschluss **messen**, nicht einen API-Boolean direkt als High/Low am Pin interpretieren.

## 4. CN1-Pinvergleich: Units Programmer vs. ValveControl V1.2

Die Zuordnung stammt aus **beiden PCB-JSON-Padnetzen**. Sie beweist keine reale Kabellage, Schlüsselung oder Bestückung.

| 2x3 CN1-Pin | Programmer V1.2 | ValveControl V1.2 | Prüffrage |
| --- | --- | --- | --- |
| 1 | CN1_1; Diode D1 (SS34) Richtung DVCC/USB-Versorgungspfad | **5V** | **KRITISCH:** USB-Versorgung/Rückspeisung möglich. Pin 1 nicht blind verbinden |
| 2 | TX | RXD am U25 Pin 8 | Debug-UART-Zweig, **nicht** aktueller RP2040-Datenlink |
| 3 | UPDI | UPDI am U25 Pin 16 | Signatur nur lesen, keine Erase/Write vor Chipnachweis |
| 4 | RX | TXD am U25 Pin 9 | Debug-UART-Zweig, aktuelle Firmware nutzt Serial.swap(1) |
| 5 | GND | GND | Masseverbindung/Isolation qualifizieren |
| 6 | GND | GND | Zweiter Masseanschluss |

**Stopp vor Anschluss:** ValveControl U25 VCC an **3.3V** (U25 Pin 1). Programmer CH340G/MUX-VCC aus USB-Versorgung. Weder sichere UPDI-Signalpegel noch Rückspeisefreiheit des 6-poligen Kabels sind belegt. **Die 5-V-Verbindung von CN1.1 nicht stecken**, bevor geeignete Versorgungstrennung und ggf. Pegelwandler sowie mechanische Pin-1-Ausrichtung anhand echter Fotos/Messungen geprüft wurden. Niemals 5V an 3.3V-UPDI oder M_VCC anschließen. [KNX022 Readiness](KNX022_STATIC_HW_READINESS.md) bleibt BLOCKED.

## 5. Laufender Temperaturdatenpfad und PIN-Unterscheidung

Der ATtiny sendet nach Serial.swap(1) über **PA1 (U25.17) -> T_RX -> RP2040 GPIO9 RX** und empfängt über **PA2 (U25.18) <- T_TX <- RP2040 GPIO8 TX**. Das ist die aktive 115200/8N1-UART1-Verbindung des [KNX014 Frames](KNX014_UART_BRIDGE.md). Die CN1-RXD/TXD-Pins (U25.8/.9) sind **andere Pins** und dienen im aktuellen Firmware-Stand nicht als laufender Temperatur-Snapshot-Kanal. Ein UART-Monitor am Programmer allein kann den internen Temperatur-Link daher nicht sehen; RP2040-USB-Diagnose/Bus-Tests sind die richtige Beobachtungsebene.

Sensoren T0 (Vorlauf) sowie T1..T8 (8 Rückläufe), DS18B20/1-Wire mit geeigneter Stromversorgung und Pull-ups. Erst einzelne Sensoren, später neun und Fehlerfälle; dann KNX KO25..35 und Diagnosen in isoliertem ETS6-Testprojekt prüfen.

M1+/M1- für **einen** späteren Antrieb bleiben bis KNX002–006 gesperrt. Acht Antriebe teilen 4 TB6612, IN_1/IN_2 und einen INA219-Shunt; TB6612-STBY auf V1.2 ist **an 3.3V festverdrahtet**, kein unabhängiger globaler Kill vorhanden. Software-simuliertes All-off ist keine elektrische Abschaltung.

## 6. Umzug des Repositories und Testreihenfolge

1. Desktop Gitstatus/HEAD/Session und lokale Commits neu verifizieren; die **26 unpublizierten Commits** (Stand KNX022, KNX023 wird dazukommen) vor dem Transfer per Git-Bundle mit Bundle-Verify und SHA256 schützen. Nicht auf dem Laptop das veraltete GitHub-origin als aktuellen Stand verwenden.
2. Einen **eigenen Laptop-KNX018-Agent/Projekt-Root** einrichten, getrennt vom älteren Units-Branch. Bundle kontrolliert übertragen und auf dem Laptop mit identischem HEAD/sauberem Gitstatus verifizieren. Noch keine Hardwarezugriffe.
3. Git/Python/PlatformIO/pymcuprog/USB-Treiber auf Laptop inventarisieren; UPDI-Programmer V1.2 aus Desktop-Units anhand Commit und Schematic-Version korrekt referenzieren. Ports zunächst nur passiv anhand VID/PID/COM zuordnen.
4. KNX/IP-Schnittstelle im vorgesehenen Netz lesen/testen, **separaten KNX-TP-Testbus** zuordnen, kein produktives KNX-Telegramm senden. ETS6-Import im isolierten Testprojekt erst nach KNX018 Aufbau.
5. Versorgung/Level/Pin1-Kabel/ATtiny-MPN und KNX002/003 reale Bestückung kontrollieren. Nach elektrischer Freigabe zuerst **read-only UPDI-Device-Signature**, Firmware/EEPROM gegebenenfalls sichern; erst später kontrolliertes Flash/Verify.
6. RP2040 per USB für Logs und Firmware; ATtiny mit einem DS18B20 zunächst an T0; CRC, Timing, Validität und DPT9.001-Temperaturen Ende-zu-Ende prüfen. Danach T1–T8 und Sensorfehler.
7. Physischer Ventilantrieb **erst nach KNX004/005/006 sicherem Interlock, Strom-, Hubzeit- und Referenznachweis**: genau ein Motor M1. Keine Motorfreigabe aus KNX020/021/023-Simulation übernehmen.

## 7. Offene Gates / keine stillschweigende Freigabe

**Nicht erledigt:** Hardware angeschlossen oder bestromt, UPDI Device ID gelesen, USB/KNX-IP live verifiziert, Firmware geflasht, DS18B20 am echten Board gelesen, KNX-ETS importiert oder Motor bewegt. KNX002/003/004/005/006 offen; KNX018 physisch geplant; KNX009 und KNX016 auf Nutzerwunsch deferred. Die aktuelle SOFTWARE-Arbeit kann unabhängig auf dem Desktop fortgesetzt werden, aber darf keine elektrische Freigabe simulieren.

**Datei dient als persistentes Handover für KNX018 auf dem Laptop** und ist in [KNX_TESTBENCH_PLAN.md](KNX_TESTBENCH_PLAN.md) sowie im README zu verlinken.


## KNX027-Nachtrag: RP2040 per USB ohne routinemaessige BOOTSEL-Taste

Der RP2040-USB-Flash-Workflow ist im Desktop-Repo als [KNX027](KNX027_USB_FLASH_AUTOMATION.md) vorbereitet. Arduino-Pico 5.5.0 aktiviert USB-CDC mit Serial.begin; PlatformIO-Environment controller nutzt explizit picotool. Auf dem kuenftigen Laptop sollen passive USB-Erkennung (Port/VID:PID), isolierter Build, Git-HEAD-Bindung und erst nach Laborfreigabe ein einmaliger picotool-Upload ueber den ausgewaehlten COM-Port moeglich sein. Bei lauffaehigem USB-CDC kann der 1200-Baud-Reset den Bootloader automatisch starten. Erstflash, fehlender USB-Port oder Firmware-Haenger erfordern weiterhin BOOTSEL/ROM-UF2 oder spaeter SWD. Am LLO Desktop zeigte der Port-Scan nur COM1 und COM3 (kein RP2040); reale USB-Programmierung ist daher **nicht** verifiziert.

KNX018 muss vor physischem Upload: (1) Repo mit **allen** lokalen Git-Commits auf Laptop sichern/uebertragen, (2) korrekte Windows-Treiber sowie PlatformIO/Python/OpenKNXproducer und COM-Port nachweisen, (3) bestueckten Flashchip, 16-MiB-Konfigurationsannahme und KNX-/USB-/3,3-V-/5-V-Spannungspfad sicher beurteilen und (4) alle Motoren abgeklemmt belassen. Die separate UPDI-CN1-Pegel-/Rueckspeiserisiko-Pruefung bleibt zwingend.

## KNX030-Nachtrag (13.10.2026): LLO Home ist der führende Software-/Erstkontaktrechner

Der aktuelle Git-Stand und das fertig geprüfte KNX029-Offline-Firmwarepaket liegen auf **LLO Home**, nicht allein auf dem ursprünglich beschriebenen Laptop. Für den spätere Erstkontakt siehe [KNX030 passive Windows-Geräteinventur](KNX030_PASSIVE_FIRST_CONTACT.md): ein gespeicherter Basis-Snapshot vor dem Anschluss und ein neuer Snapshot nach dem **elektrisch freigegebenen** USB-Anschluss können nur neue PnP-/COM-Einträge anzeigen. Der Vorgang öffnet keinen Port und prüft noch nicht das Board oder die KNX/IP-Schnittstelle. Die in diesem Dokument beschriebenen CN1-/UPDI-, Bus-, Versorgungs- und Motor-Sicherheitsgates bleiben unverändert gültig.

## KNX031-Nachtrag – Rohdaten aus dem internen ATtiny-Temperatur-UART

Für einen späteren **separat freigegebenen** Rohmitschnitt der RP2040-Serial2 ↔ ATtiny ALT1 PA1/PA2-Leitung steht die rein dateibasierte [KNX031 UART-Analyse](KNX031_UART_TRACE_OFFLINE.md) bereit. Der LLO-Home-USB-CDC-Anschluss und die CH340G-Programmer-CN1-TXD/RXD-Pins liefern nicht automatisch diesen internen UART1-Verkehr. Keine Portöffnung in der Auswerte-CLI, keine Aufzeichnung ohne sicheren Spannungs-/GND-/Pegelcheck, keine elektrische oder motorische Freigabe durch einen guten CRC.

## KNX036 Desktop-Erstkontakt (14.10.2026; neue Anlaufstelle)

Nach dem KNX035-U11-Überhitzungsereignis wurde der aktuelle 19-Commit-Home-Fortschritt **ohne GitHub-Push** zum LLO Desktop zurücktransferiert. [KNX036](KNX036_DESKTOP_USB_FIRST_CONTACT.md) dokumentiert die inzwischen live geprüften Host-Ports `COM1` (lokal) und `COM3` (Intel-AMT-SOL), beide **nicht** als UPDI/RP2040-Kandidaten. Board-/Programmer-USB-Verbindungen haben noch **keine neuen PnP-Einträge** geliefert. Das eigene RP2040 USB-CDC-Build-Projekt enthält keine KNX-/Motorfunktionen und hat einen explizit gesperrten PlatformIO-Upload. **CN1.1 = 5 V** und **U25 = 3,3-V-Logik** bleiben inkompatibilitätsverdächtig, bis Pegel/isolierte Versorgung nachgewiesen sind; zunächst nur CH340G-Gerät PC-seitig **ohne 2×3-Kabel** enumerieren. R17-U9, F1, D1, U6 und KNX-/Motor-Gates bleiben separate reale STOP-Punkte.
