# KNX036 – LLO Desktop: erste USB-/COM-Prüfung ohne KNX-Bus

**Stand: 14.10.2026.** LLO Desktop Agent 0.8.2, Projekt `C:\ASH\Workspace\Projects\open-knx-valve-control`. Der neuere Home-Stand KNX035 wurde per lokalem SHA256-geprüften Git-Bundle übertragen und ohne Push als Fast-Forward übernommen (19 Commits). **Kein Target angeschlossen/geflasht, keine COM-Schnittstelle geöffnet, kein KNX- oder Motorbetrieb.**

## 1. Der echte Desktop-Ausgangszustand

| Quelle | Ergebnis vor Anschluss |
| --- | --- |
| Windows-Seriell | `COM1`: ACPI PNP0501 (PC-interner Kommunikationsanschluss) |
| Windows-Seriell | `COM3`: Intel Active Management Technology SOL (PC-interner Port) |
| KNX030 OS-Snapshot | 11 vorhandene USB-/Port-PnP-Kandidaten |
| KNX030 Bootloader | 0 Laufwerke mit Label `RPI-RP2` |
| KNX030 Netzwerkschnittstellen | 5 lokale Adapter, **kein KNX/IP-Nachweis** |

Die reproduzierbare, rein lesende OS-Baseline liegt **außerhalb Git** in:

`C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-before-board-20261014.json`

`COM1` und `COM3` sind **keine** momentan identifizierten RP2040-/CH340-UPDI-Geräte; daher diese Ports nicht testweise öffnen. Ein RP2040 ohne laufende USB-CDC-Firmware kann auch statt COM nur `RPI-RP2` als ROM-Bootloader-Volume erscheinen, während ein separater CH340G-Programmer einen weiteren neuen USB-Serial-Port liefert. Beide Geräte getrennt identifizieren, nicht Ports aus älteren Chats raten.

## 2. Unmittelbare elektrische Sperren vor einem Kabel

Nach dem KNX-Ereignis wurde **U11 (68 Ω nach Nutzerangabe) sehr heiß**. Das V1.2-Design besitzt einen 10-kΩ-**R17-Pull-up** an U9/STKNX `KNX_TX` nach 3,3 V, der dem aktiven-HIGH-Sendepuls (LOW idle) widerspricht. Die aktuelle vorbereitetet Produktivfirmware nutzt zudem `TPUart::ArduinoSerial(Serial1)` mit UART-Ruhepegel HIGH, **nicht** die richtige STKNX-Sendeform. Die Integrität von U9 nach Überhitzung ist unbekannt.

**Bevor der RP2040 erstmals mit USB bestromt wird, separat bestätigen und dokumentieren:**

- **KNX komplett abgeklemmt**, **alle acht Motoren** und externe 5-V-/Motorversorgungen getrennt; JMP1 wurde laut Nutzer geöffnet. **R17 wurde bisher nur zur Entfernung vorgeschlagen, nicht als tatsächlich entfernt bestätigt.**
- F1-Bestückung auf Foto `T 2.5 A` statt Schematic `630 mA`: Schutz-/Leiterbahn-/USB-Überstrombudget neu prüfen; bei Schutzunklarheit nicht direkt den Desktop-USB-Port verwenden.
- D1 ist durch Draht überbrückt; vorher stromlose Kurzschlussprüfung zu benachbarten Pads/GND, Versorgungssicherheit und Rückspeisung bewerten.
- TRACO U6 ist rückseitig physisch sichtbar; tatsächliche Typmarkierung / Spannung **noch nicht gemessen**. USB über D6, F1, Draht-D1, U6 VIN; Herstellerbedarf mindestens `4,75 V` am VIN-Pin. USB 5 V nominal genügt als Nachweis unter Last nicht.
- CN1 Programmer: ValveControl **Pin 1 = 5 V**, Pin 3 = UPDI ATtiny3216 an **3,3-V-Logik**, Pin 5/6 GND. Units-CH340G besitzt RTS-gesteuerte Umschaltung und USB-bezogene Pegel. **Nicht beide USB-Leitungen und das 2x3-Kabel gleichzeitig einstecken, solange Pin-1-/3,3-V-/5-V-Rückspeisung und Massebezug ungeprüft sind.** Kein UPDI-Port-Betrieb vor Signatur- und Pegel-Gate.

Der vorliegende Chat enthält **keine Messfreigabe**. Erst nachdem diese Punkte fachlich geklärt und eine geschützte/strombegrenzte erste Versorgung abgesichert sind, dürfen reale Geräte angeschlossen werden.

## 3. Softwarebereit: rein passiver USB-OS-Vergleich

```powershell
Set-Location 'C:\ASH\Workspace\Projects\open-knx-valve-control'
$py = 'C:\Users\LLO\.platformio\penv\Scripts\python.exe'
$before = 'C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-before-board-20261014.json'
$after = 'C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-after-board-usb-01.json'

# Nur Host-OS-Metadaten, keine COM-Oeffnung; ERST nach separatem Hardware-Gate:
& $py tools/knx030_passive_inventory.py capture --label after_rp_usb --output $after
& $py tools/knx030_passive_inventory.py compare --before $before --after $after
```

Immer **ein** neues USB-Gerät auf einmal verbinden und Snapshot vergleichen. `capture` überschreibt keine vorhandene Datei. Der Vergleich nutzt nur JSON und kann keine elektrische Sicherheit, Bordidentität oder funktionierende USB-CDC-Protokolle beweisen. `RPI-RP2`-Massenspeicher nicht ohne gesonderte Freigabe beschreiben.

## 4. Neue separate, **noch nicht flashberechtigte** RP2040-USB-Diagnose

Unter [tools/knx036_usb_diag](../tools/knx036_usb_diag/platformio.ini) existiert ein **eigenständiges PlatformIO-Projekt**, das **nicht** `src/controller/main.cpp`, OpenKNX, TPUart, ETS, Motorbibliotheken oder ATtiny-UART verwendet.

Das C++-Programm hält **GPIO0/KNX_TX nach Setup aktiv LOW** und sendet ausschließlich auf **RP2040 USB-CDC** alle 2 Sekunden den Marker `KNX036 USB-ONLY RP2040 ALIVE` mit Uptime/Sequenz. **Keine** Aktionen auf GPIO8/9 (ATtiny-Link), GPIO10..19 (Motoren), KNX-TP, KNX-Empfang oder CN1. Es enthält keine Upload- oder Busbefehle.

```powershell
$pio = 'C:\Users\LLO\.platformio\penv\Scripts\pio.exe'
& $pio run --project-dir tools/knx036_usb_diag -e knx036_usb
```

Der **Build ist zulässig ohne Board**; das separate PlatformIO-Environment hat `upload_protocol = custom` und absichtlich `upload_command = cmd /c exit 91`: Ein unbeabsichtigtes `-t upload` soll fehlschlagen. Ein UF2-Artefakt ist **nicht automatisch eine Freigabe zu Flash/USB/KNX/Motoren**. KNX_TX kann **vor** `setup()` beim RP2040-Reset noch high-Z sein; während KNX verbunden ist, bietet diese Testfirmware **keine** hinreichende Sender-Hardwareverriegelung. Nur auf isoliertem strombegrenztem USB-Prüfstand ohne KNX-Bus/motorische Last einsetzen.

Bei positiver elektrischer Freigabe kann zunächst das **bestehende Blink-Programm** rein passiv erkannt werden. Für ein späteres Testfirmware-Flashen müssen RP2040-Identität, Flash-Bestückung, 3,3-V- und 5-V-Versorgung, USB-Pegel, COM-VID/PID und ein **separater expliziter Flashauftrag** dokumentiert sein. Kein automatischer 1200-Baud-Reset, kein picotool Upload, kein BOOTSEL-Datenschreiben erfolgt durch KNX036.

## 5. ATtiny-/UPDI-Schnittstelle getrennt

Als nächsten Schritt den **Units Programmer V1.2** zunächst **nur per USB am PC** identifizieren, ohne CN1 an die Platine anzuschließen. Der neue CH340G-Port ist ein Programmer-Kandidat, nicht automatisch ein lesefähiger Sensor-UART. Die aktive Temperaturschnittstelle läuft auf U25 PA1/PA2 ↔ RP2040 GPIO8/9; CN1-RXD/TXD auf U25.8/.9 ist eine andere UART-Zuordnung.

Eine spätere, ausdrücklich freigegebene UPDI-Signatur-Leseoperation benötigt zuerst bestätigten Mikrocontrolleraufdruck, 3,3-V-UPDI-Pegel, korrekte CN1-Pin-1-Orientierung und Quellentrennung. Keine Fuses, kein Erase, kein Program-Write, kein Default-RTS/DTR-Autotoggle auf unbekanntem COM. **Keine KNX-Busversorgung für USB-/UPDI-Tests.**

## 6. Beobachtungen und offene Fragen

- Die zwei aktuellen COM-Ports sind PC-intern; Board und Programmer wurden hier **noch nicht als neue USB-Geräte** nachgewiesen.
- Der Nutzer muss die **R17-Entfernung** und eine sichere versorgungstechnische Trennung/Limitierung vor jeglicher Boardbestromung bestätigen; das Hitzeereignis U11/U9 bleibt als P0 offen.
- Für das isolierte RP2040-Diagnoseimage stehen weiterhin Boot-, Brownout- und USB-CDCFunktionstests auf echter Hardware aus.
- KNX035 verlangt für das spätere KNX-Produktivprogramm einen **STKNX-spezifischen Puls-Treiber** und sicheren TX-LOW-Hardwarezustand, nicht nur Software. KNX002–006 und KNX034 sind nicht automatisch geschlossen.

**Status: DESKTOP_READY_FOR_OFFLINE_BUILD_AND_PASSIVE_PNP, PHYSICAL_CONNECTION_NOT_YET_AUTHORIZED.**

## 7. KNX036 erste tatsächliche Desktop-Ergebnisse (14.10.2026)

- Desktop-Bundle-Transfer: `65011e9` aus LLO Home übernommen, 19 lokal vor origin/main, ohne Push, Bundle-SHA256 auf beiden Rechnern identisch `2C3B7FE59AFAB9B6F1B919A7A9AF0C94D0969472B1BAC28089D0196C57B86DB8`.
- LLO Desktop: `C:\Users\LLO\.platformio\penv\Scripts\pio.exe` Version 6.1.19. Separates `knx036_usb_diag`-Projekt mit Arduino-Pico 5.5.0 wurde **nur auf dem Host kompiliert**: `SUCCESS` in 37,99 s, ca. 58.444 Bytes Programm-Flash, 8.740 Bytes RAM. Kein hochgeladener Code.
- UF2 + ELF samt SHA256/No-Release-Manifest **außerhalb Git**: `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-usb-diagnostic-20261014`. UF2: 141.312 Bytes, SHA256 `ad8df9ba4426102fb240f2ebfbb9526071b91e563fab897ab04034ed766866de`. Die UF2-Datei ist ein **ungeprüfter Firmwarekandidat, keine Flashfreigabe**.
- `tools/test_knx036_usb_diag.py --check-build`: **8/8 PASS** (isolierter Link, Upload gesperrt, GPIO0 LOW ab Setup, kein Arduino-KNX-/UART1-/Motor-Aufruf, UF2-Datei-/Magic-Prüfung).
- `tools/test_knx030_passive_inventory.py`: **11/11 PASS**. KNX035-Quell-Sicherheitsaudit PASS, Design-Audit 0 Invariantfehler, ASH 30/30 PASS.
- Zweite passive OS-Aufnahme `KNX036-desktop-current-01.json` und Offline-Diff zur Ausgangslage: **0 neue/entfernte USB-Geräte, 0 COM-Ports neu, 0 RPI-RP2-Volumes, 0 lokale Linkstatuswechsel**. Das Board ist demnach **noch nicht als neues Windows-Gerät nachgewiesen**. Keine COM-Schnittstelle wurde geöffnet.

**Nächster sichere reale Schritt:** Falls der Nutzer den Units-UPDI-Programmer verfügbar hat, darf zunächst **nur dieser USB-Programmer am PC ohne angeschlossenen ValveControl-CN1-Stecker** rein per Windows-Geräteerkennung aufgenommen werden; keine RTS/DTR-Änderung und keine UPDI-Transaktion. Das echte Board mit eigener USB-Versorgung weiterhin erst nach F1/D1/R17/Pegelprüfung und ohne KNX/UPDI/Motoren.

## KNX037 Nachtrag – tatsächlicher RP2040-Flash bestanden

Der damals nur als Build-Kandidat vorliegende KNX036-USB-Heartbeat wurde inzwischen unter gesondertem User-Auftrag **real auf den RP2040 geflasht**, inklusive 1200-Baud-Reset ohne BOOTSEL, ROM-Revisions-/16-MiB-Flash-Identifikation, 100%-Picotool-Verify und USB-CDC-Runtime-Heartbeats auf COM7 (vorher COM5). Siehe [KNX037 Live-Testprotokoll](KNX037_DESKTOP_LIVE_USB_AND_UPDI.md). Dies ändert **nicht** rückwirkend die KNX036-Offlineabnahme; keine Freigabe des normalen TPUart/KNX-Controllers oder der Motor-/UPDI-Funktionen.
