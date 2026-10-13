# KNX029 – RP2040 / ATtiny / KNX: Erstkontakt und Offline-Firmwarepaket

**Stand 13.10.2026.** Dies ist ein Ablauf- und Artefaktnachweis für die spätere Inbetriebnahme der OpenKNXValveControl V1.2. **Die Platine ist noch nicht angeschlossen; elektrische Freigabe, USB-Flash, UPDI-Flash und KNX-/ETS6-Funktion sind nicht nachgewiesen.**

## 1. Entwicklung auf LLO Home

Repository: `C:\_myspace\workspace\open-knx-valve-control`. LLO Home ist der führende Software-Rechner; Desktop und GitHub können bis zu einem expliziten Push/Pull abweichen. Vor jedem Build Git-Status, Session und HEAD live prüfen. Niemals einen Stand aus dem veralteten Origin-Branch als neueren lokalen Stand behandeln.

- RP2040: Arduino-Pico 5.5.0, GCC ARM 14.3.0, PlatformIO und OpenKNXproducer 3.12.2; der Controller-Build ist auf dem LLO Home softwareseitig erfolgreich getestet.
- ATtiny: PlatformIO `env:temperature` ist **ATtiny3216** mit 20 MHz. PCB-Part-Metadaten zeigen möglicherweise ATtiny1616; diese beiden Typen dürfen nicht verwechselt werden.
- `pymcuprog` 3.19.4.61 ist im PlatformIO-Python installiert, wird **von KNX029 nicht aufgerufen**.
- Zuletzt festgestellt: LLO Home WLAN verbunden, Ethernet getrennt. Daraus folgt **keine** erreichbare KNX/IP-Schnittstelle.

## 2. KNX029-Kommandos – alle ohne Zielhardware

```powershell
Set-Location 'C:\_myspace\workspace\open-knx-valve-control'
$env:PLATFORMIO_CORE_DIR = 'C:\Users\ll\.platformio'
$env:PIO_EXECUTABLE = 'C:\Users\ll\.platformio\penv\Scripts\pio.exe'
$env:OPENKNXPRODUCER_EXECUTABLE = 'C:\_myspace\Tools\OpenKNXproducer-3.12.2\tools\Windows\OpenKNXproducer-x64.exe'
$env:OPENKNX_PRODUCER = $env:OPENKNXPRODUCER_EXECUTABLE
$python = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'
$gitSafe = 'safe.directory=C:/_myspace/workspace/open-knx-valve-control'
& $python tools/knx029_prepare_bringup.py plan
& $python tools/test_knx029_bringup_kit.py
$sha = (& git -c $gitSafe rev-parse HEAD).Trim()
& git -c $gitSafe status --short
# NUR bei CLEAN Repository; den Ausgabepfad neu und außerhalb des Git-Roots wählen.
$out = 'C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX029-' + $sha.Substring(0, 8)
& $python tools/knx029_prepare_bringup.py build --expected-head $sha --output-dir $out
& $python tools/knx029_prepare_bringup.py verify --kit $out
```

**`plan`** startet keinerlei externe Kommandos. **`build`** verweigert nicht-40-stellige/falsche Git-HEAD, einen verschmutzten Arbeitsbaum, existierende oder innerhalb des Repos liegende Ausgabeverzeichnisse. Der Build verwendet eine temporäre Kopie, die ATtiny-Konfiguration ohne Programmer-Actions und ausschließlich `pio run -e controller` sowie `pio run -e temperature`. **`verify`** kontrolliert Hashes/Größen/Gates ohne Hardwarekontakt. Keine Aktion öffnet COM-Ports, sendet einen 1200-baud Reset oder führt einen Upload aus.

Das Paket enthält:

| Datei | Bedeutung |
| --- | --- |
| `controller-rp2040.uf2` | RP2040 Firmwarekandidat für einen später gesondert freigegebenen Flash |
| `controller-rp2040.elf` | Controller-Buildsymbolik/Analyse |
| `temperature-attiny3216.hex` | **Nur für einen tatsächlich identifizierten ATtiny3216** |
| `temperature-attiny3216.elf` | ATtiny-Buildsymbolik/Analyse |
| `bringup-manifest.json` | Git-HEAD, Buildbeschreibung, Firmware-SHA256, **alle echten Freigaben false** |
| `SHA256SUMS.txt` | Integritätsliste der vier Firmwaredateien und des Manifests |

**Ein erfolgreiches Paket ist ausdrücklich keine Programmier- oder Motorfreigabe.** Die reale RP2040-Flashgröße und ATtiny-Gerätesignatur sind bis zur Prüfung unbekannt. Ein manuell kopiertes HEX/UF2 umgeht die Firmware-Upload-Sicherheitsbedingungen nicht.

## 3. Hardware-Testabfolge mit STOP-Gates

| Gate | Notwendiger Nachweis vor dem nächsten Schritt | Verbot, solange offen |
| --- | --- | --- |
| **A – Sichtprüfung, stromlos** | Fotos V1.2 Vorder-/Rückseite, U25 Aufdruck und BOM, R29 Shunt, F1, Q1/JMP1, U6 VIN, CN1 Stecker-/Pin1-Lage, RP-Flash-Baustein | Keine Spannung, kein Programmer |
| **B – Power/Schutzkonzept** | KNX002/003 Laborfreigabe: U6 Zweidioden-Spannungsreserve, 3,3-V-Stabilität, externe Quellen, USB↔KNX-Rückspeisung, Masseführung, Strombegrenzung; **alle M1…M8 abgeklemmt** | Kein USB-/UPDI-/KNX-Anschluss bei unsicherer Versorgung |
| **C – RP2040 passiv** | USB VID:PID/COM oder RPI-RP2 eindeutig beim Ein-/Ausstecken identifizieren; echter Flash-Chip bestätigt; GND/3,3 V stabil | Kein blindes BOOTSEL/UF2, kein Upload ohne separate Freigabe |
| **D – ATtiny über UPDI** | Physische U25 Markierung **und** lesende Signatur passen zum Build; reale 3,3-V-Pegel, CN1 Pin1/5-V-Abtrennung, RTS/RTS#-Schalterstellung gemessen | Kein `pymcuprog write/erase` vor Freigabe, keine ungeprüfte 5-V-Verbindung |
| **E – KNX/TP** | Getrennter KNX/IP-Testanschluss und KNX-TP-Testbus identifiziert, richtige Netztopologie und Stromversorgung geprüft; niemals Produktivtelegramme in der Ersterkennung | Kein ETS6-Download, keine fremde Gruppenadresse beschreiben |
| **F – Temperaturlink** | RP2040 Serial2(GPIO8/9) ↔ ATtiny ALT1 PA2/PA1, 115200/8N1, 9-Kanal-Frame-CRC; zunächst T0, dann T1…T8 sowie Offline-/Stale-Fälle | Keine Temperatur-Kanäle als Raum-Istwert ausgeben |
| **G – Ventilmotoren** | KNX004–006 echte unabhängige Ausgangssperre, sichere Reset-/Brownout-Zustände und INA219 Shunt/Motorstrom-/Referenztests fachlich freigegeben | **Bis dahin kein einziger echter Motor fahren** |

Besonders wichtig: Die V1.2-TB6612-STBY-Pins sind laut Schaltung fest auf 3,3 V. Die KNX020/023-Software-Queue und All-off-ACKs können **keine elektrisch geprüfte Abschaltung beweisen**. Alle realen KNX022-Hardware-Blocker bleiben offen, auch wenn RP2040 und ATtiny erfolgreich kompilieren.

## 4. Kommunikation und Revisionsgrenzen

- **RP2040 USB CDC** ist die spätere PC-Flash-/Diagnoseschnittstelle. Der 1200-baud Bootloaderwechsel aus KNX027 funktioniert nur bei funktionierender Firmware; bei Erstprogrammierung ggf. BOOTSEL/ROM-UF2 oder später SWD.
- **RP2040 Serial1** ist KNX TP über TPUart. Ein Windows-Ethernet/WLAN-Link allein weist keine KNX/IP/TP-Verbindung nach.
- **RP2040 Serial2** ist der getrennte Temperaturlink: GPIO8 TX ↔ ATtiny PA2 RX und GPIO9 RX ↔ ATtiny PA1 TX; **nicht** CN1 TXD/RXD-Pins der Units-Programmierplatine.
- **ATtiny-Programmer V1.2 CN1** ist 2x3: Pin 1 möglicherweise 5-V-/USB-Versorgungspfad! Die UPDI-Pegel/Rückspeisung sind vor jeder Verbindung zu messen. Der Programmer wird über einen getrennten USB-CH340G-Port erkannt.
- **ETS6**: Bisher nur AppVersion2 mit den vorhandenen KOs freigegeben. Die vorgesehenen AppVersion3-Zonen/KO36..67 sind reine Softwareentwürfe, keine importierte KNX-Konfiguration. Erst ein isoliertes Testprojekt anlegen und geordnet freigeben.

## 5. Testprotokoll für den fertiggestellten Aufbau

Fotos und gemessene Werte nach Gate A/B protokollieren, inklusive Zeit/Boardrevision/BOM/U25-Markierung/RP-Flash-Chip, beteiligter USB-Port-IDs und Netzteilgrenzen. An jedem Gateway genau **GO**, **BLOCKED** oder **NOT TESTED** dokumentieren, keine Werte annehmen. Gerätetests bleiben bis zum tatsächlichen Aufbau offen.

Siehe [KNX018 Teststand](KNX018_LAPTOP_UPDI_TESTBENCH.md), [KNX022 statische Hardware-Gates](KNX022_STATIC_HW_READINESS.md), [KNX027 USB Recovery](KNX027_USB_FLASH_AUTOMATION.md) und [KNX028 LLO Home Toolchain](KNX028_LLO_HOME_SETUP.md).
