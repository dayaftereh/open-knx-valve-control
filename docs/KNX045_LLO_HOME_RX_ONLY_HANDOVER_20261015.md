# KNX045 – LLO Home: Git-/Firmware-Übergabe für STKNX-Empfang

**Stand:** 15.10.2026, beide Rechner live geprüft.

## Ziel und Status

LLO Desktop → GitHub `main` → LLO Home wurde per Commit `0a610d8` synchronisiert. Alle KNX043-PicoScope- und KNX044-USB-Flash-Reports sowie die USB-Monitor-/PicoScope-Skripte und ihre Tests sind im Git-Repository. Die umfangreichen **binären Rohaufzeichnungen** liegen aus Platzgründen weiterhin als SHA-verifizierte ZIP-Archive außerhalb von Git in den jeweiligen Build-Verzeichnissen.

| Bereich | Ergebnis |
| --- | --- |
| Git LLO Desktop und LLO Home | `main`, gleicher Stand, sauber nach Abgleich |
| Home Python/PlatformIO/Picotool | Installiert |
| Home ETS6 und OpenKNXproducer | Auf dem Rechner vorhanden; kein ETS-Produktgerät in Betrieb genommen |
| KNX043 Firmware-Image | Vorhanden, SHA256 bestätigt |
| Firmware zuletzt am V1.2-Board | **KNX043 passive RX-only**, auf Desktop per Picotool geladen/verifiziert, App über COM7 bestätigt |
| KNX_TX USB-only | 60 Sekunden Hardware-Trigger >0,35 V ohne Ereignis; keine aktive KNX-TX-Ansteuerung in KNX043 |
| Platine aktuell an LLO Home | **Nein** – kein RP2040 via USB erkannt; deshalb kein Home-Flash erfolgt |
| KNX-Busanschluss | **NICHT FREIGEGEBEN**: 17 physische Gates unbestätigt |

## Pfade auf LLO Home

Projekt: `C:\_myspace\workspace\open-knx-valve-control`

**Aktuelle geeignete Firmware:** `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014\knx043-passive-rx-only-NOT-FLASHED.uf2`

Der historische Teil `NOT-FLASHED` im Dateinamen ist inzwischen **falsch** – dieses Image wurde tatsächlich am Board geflasht und erneut bytegenau verifiziert. SHA-256: `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f`, 146.432 Bytes, 286 UF2-Blöcke.

Werkzeuge:
- Python: `C:\Users\ll\.platformio\penv\Scripts\python.exe`
- PlatformIO: `C:\Users\ll\.platformio\penv\Scripts\platformio.exe`
- Picotool: `C:\Users\ll\.platformio\packages\tool-picotool-rp2040-earlephilhower\picotool.exe`
- Bootloader-Preflight: `tools\knx043_bootsel_firmware_preflight.py`
- Empfang/USB-STATUS: `tools\knx043_rx_capture.py`
- Passives Hardware-Gate: `tools\knx043_home_knx_preflight.py` und `docs\KNX043_HOME_KNX_GATE.json`

Home-Prüflog: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX045_LLO_HOME_RX_PREP_20261015\preflight.json` (read-only; Hardwarestatus `BLOCKED_AWAIT_HARDWARE_EVIDENCE`, 0 von 17 physischen Beobachtungen bestätigt).

Zusätzliche SHA-geprüfte Desktop-Messarchive befinden sich auf Home in `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043-PicoScope-20261015` und `...\KNX044_USB_ONLY_FLASH_20261015`.

## Wenn die Platine zu LLO Home gebracht wird: nur USB-Prüfung

1. **KNX-TP-Leitungen und alle Motoren getrennt lassen.** Platine zunächst nur an USB anschließen; nicht gleichzeitig über den KNX-Bus speisen.
2. USB-Gerät tatsächlich identifizieren: Anwendung = RP2040 `VID 2E8A / PID 000A` mit eigener COM-Nummer (nicht pauschal COM8); BOOTSEL-ROM = `PID 0003`. Die zuletzt auf Desktop bestätigte Flash-/App-Seriennummer lautet `E464401787522D33`.
3. Wenn bereits die KNX043-Anwendung startet, **nicht unnötig neu flashen**. Ausschließlich `STATUS` über die auf LLO Home erkannte COM-Nummer prüfen, z. B. im Projekt:

   `C:\Users\ll\.platformio\penv\Scripts\python.exe tools\knx043_rx_capture.py status --port COMx --expect-serial E464401787522D33`

   Erwartet: `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0`.
4. Sollte ausschließlich der ROM-Bootloader erscheinen und nach unabhängiger Geräteidentifikation ein erneuter Flash nötig sein: SHA256 der oben genannten UF2 prüfen; **nur ohne KNX-TP und Motorlast**, per Picotool **mit Update und Verify** laden, anschließend in die Anwendung booten. Das hat am Desktop mit `picotool load -u -v` und `picotool reboot -a` bereits funktioniert. Niemals das alte `KNX029-PRODUCT-TPUART-DO-NOT-FLASH-ON-KNX.uf2` verwenden.

## Was vor echtem KNX-RX zu erledigen ist

- R17 wurde laut Nutzer entfernt, muss aber **stromlos an den Lötpads** gegen 3,3 V und KNX_TX auf Lötbrücke/Isolation überprüft werden.
- **U11 68 Ω / U9 STKNX** nach früherer starker Erwärmung prüfen; U11-Temperatur-/Busstromproblem beim früheren Busversuch ist nicht als behoben nachgewiesen.
- USB-/KNX-Strompfade mit F1, D1-Bypass, Q1 und JMP1 sowie Einschalt-/Reset-/Brownout-Fail-LOW am STKNX KNX_TX absichern.
- Jumper JMP2 KNX_RX U9 Pin23 → RP2040 GPIO1 und JMP3 KNX_TX U9 Pin24 ← RP2040 GPIO0 physisch bestätigen.
- **Nur ein separater, kontrollierter und abgesicherter KNX-TP-Testaufbau**, nicht der produktive Hausbus. Erst nach bestätigten Hardwaregates den gesicherten RX-only-Host-Workflow `knx043_rx_capture.py capture` mit seiner unabhängigen Prüf- und Isolationsfreigabe ausführen. Das Tool erfasst Pegelflanken; es sendet keine KNX-Frames und übernimmt noch keine ETS-Parametrierung.
- **Keine KNX-TX-Freigabe:** Das bestehende Produktprogramm nutzt TPUart `Serial1` (UART idle HIGH) und ist nicht direkt mit STKNX vereinbar. Die neue STKNX-spezifische KNX-Phy-Sendeimplementierung und ETS-Parametrierung sind nach dem RX-Bench separat zu entwickeln und zu validieren.

## Prüfquellen

- [KNX043 USB-PicoScope mit BOOTSEL](KNX043_PICOSCOPE_BOOTSEL_20261015.json)
- [KNX043 gemeinsame KNX_TX/Versorgungs-Messung](KNX043_PICOSCOPE_DUAL_USB5V_RESULT_20261015.md)
- [KNX044 erneut verifizierte Firmware](KNX044_USB_STKNX_FLASH_VERIFY_20261015.md)
- [Hardware-Gate und fehlende Freigaben](KNX043_HOME_KNX_GATE.json)
- [RX-Only Source](../tools/knx043_passive_rx/src/main.cpp)

**Ergebnis:** LLO Home ist softwareseitig bereit, die vorhandene KNX043-Firmware per USB zu erkennen und bei Bedarf erneut zu installieren. **Nicht** bereit zur gefahrlosen Verbindung mit dem KNX-TP-Bus, bis die physischen Sicherheitsprüfungen bestanden sind.


## Nachtrag 15.10.2026 – KNX046 auf LLO Home tatsächlich ausgeführt

Der Nutzer bestätigte nur USB ohne KNX-TP, Motor und Temperatursensor. Das zuvor beschriebene KNX043 RX-only-Image wurde über das RPI-RP2-Laufwerk D: installiert; Windows hat danach COM8 (2E8A:000A) erkannt. 3/3 KNX043-USB-Statusabfragen waren erfolgreich. [Flash-Ergebnis](KNX046_HOME_RX_ONLY_FLASH_20261015.md). Der physische KNX-Bus darf daraus nicht freigegeben werden; die 17 Sicherheitsgates sind weiterhin offen.
