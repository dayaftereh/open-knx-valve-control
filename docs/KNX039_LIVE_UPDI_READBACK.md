# KNX039 – Echtabnahme ATtiny3216 über CH340 COM4 / UPDI: Signatur und Speicher-Readback

**Datum:** 14.10.2026. **Agent:** LLO Desktop 0.8.2. **Status:** ECHTE UPDI-LESUNGEN ERFOLGREICH, KEINE SCHREIB- ODER ERASE-AKTION.

## 1. Grundlage und Rückmeldung

Der Nutzer hat ausdrücklich freigegeben, den bereits verbundenen Units-/CH340-Programmer über COM4 in den UPDI-Modus zu schalten und den bestehenden ATtiny auszulesen. Er berichtete, dass der Programmer und das bereits vorhandene Programm an dieser Hardware früher erfolgreich getestet wurden. Die spontane Bezeichnung **„ATtiny2316“** wird nicht als belegte Typkennung übernommen: Die **tatsächlich per UPDI gemessene Signatur `1E 95 21` identifiziert den ATtiny3216**. Damit wurde die erwartete Bezeichnung aus der Temperatur-Firmware bestätigt; der alte PCB-Metadateneintrag `ATTINY1616-SN` ist für die tatsächlich geprüfte Platine falsch.

Vor der Aktion waren die echten Windows/PySerial-Geräte COM4 = CH340 `1A86:7523` und COM7 = RP2040 USB-CDC `2E8A:000A` vorhanden. Git `main` war CLEAN, HEAD `90dfc8e`, 25 lokale Commits vor `origin/main`, keine aktive Fremd-Session.

**Programmer-Schaltplan:** Units V1.2 U2/U7 SN74LVC1G3157 selektieren mit RTS zwischen UART und UPDI. Vorhandene Units-WebSerial-Implementierung setzt logisch `requestToSend:true` und `dataTerminalReady:true` für UPDI. Das verwendete `pymcuprog` öffnet PySerial mit Standard-RTS/DTR (True) und sendet einen Initial-BREAK auf UPDI. Mit dieser Verbindung wurde der ATtiny mehrfach erfolgreich angesprochen.

**Grenze:** Es wurde **keine separate Oszilloskop-/DMM-Pegelmessung** an CN1 Pin 3 gegenüber U25-VDD durchgeführt und kein CN1-Kabel entfernt. Die erfolgreiche Kommunikation beweist den funktionierenden UPDI-Weg, **nicht** die elektrische 5-V-/3,3-V-Toleranz aller Board-/Programmer-Leitungen oder die Sicherheit unter KNX- bzw. Motorlast. Der Nutzer bezeichnete den Aufbau als bereits erprobt.

## 2. Tatsächliche nur lesende Operationen

Alle Befehle liefen lokal auf LLO Desktop, jeweils über `C:\Users\LLO\.platformio\penv\Scripts\pymcuprog.exe` und `--device attiny3216 --tool uart --uart COM4`.

```powershell
pymcuprog --device attiny3216 --tool uart --uart COM4 ping
# Connecting to SerialUPDI
# Pinging device...
# Ping response: 1E9521
# Done.

# Danach ohne ERASE/WRITE/FUSE-Write ausschließlich:
pymcuprog --device attiny3216 --tool uart --uart COM4 --memory flash --filename <flash-backup>.hex read
pymcuprog --device attiny3216 --tool uart --uart COM4 --memory eeprom --filename <eeprom-backup>.hex read
pymcuprog --device attiny3216 --tool uart --uart COM4 --memory fuses --filename <fuses-backup>.hex read
pymcuprog --device attiny3216 --tool uart --uart COM4 --memory user_row --filename <user-row-backup>.hex read
```

Die vier Read-Operationen lieferten jeweils **Exitcode 0**, erneutes `Ping response: 1E9521`, Speicher-Readout und `Done.`. Kein `write`, `--erase`, Fuse-Change, Flash-Upload, Motor- oder KNX-Kommando. COM7 RP2040-Heartbeat-Firmware nicht verändert.

## 3. Sicherung des tatsächlichen Ist-Programms

Originaldateien **außerhalb Git** am LLO Desktop unter:

`C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX039-ATtiny3216-readback-20261014\`

| Datei | Umfang | Inhalt |
| --- | ---: | --- |
| `attiny3216-existing-flash.hex` | 32.768 Flash-Bytes | Vollständiges bestehendes 32-KiB-Abbild, 1.888 Bytes ungleich `FF` |
| `attiny3216-existing-eeprom.hex` | 256 Bytes | Alle gelesenen Bytes `FF` |
| `attiny3216-existing-fuses.hex` | 9 Bytes | Gelesene Fusewerte, **nur gesichert, nie geändert** |
| `attiny3216-existing-user-row.hex` | 32 Bytes | Alle gelesenen Bytes `FF` |
| `readback_manifest.json` | Metadaten | SHA256, Speicherbereiche, Intel-HEX-Checksums und Vergleich zum neuen Build |

**Alle Intel-HEX-Prüfsummen sind korrekt.** Einzelne Fuse-Bytes sind im Manifest gespeichert, jedoch nicht ohne separaten Datenblattabgleich als Konfiguration interpretiert. Das EEPROM ist laut gelesenen Bytes leer/erased; dies belegt **nicht**, ob die ältere Firmware jemals EEPROM nutzt.

Flash-Backup SHA256: `048d09437f46cd7b6107fb7649ef1a7dcf469dab4ada59d125a7a6f1846bd5b7`. EEPROM SHA256: `7a0629b48f8b078188ed3e8272583181490dc4efe8f12716b8ef13a18f8b58b8`.

## 4. Ist-/Soll-Vergleich ohne Änderung am Chip

Der vorhandene Firmwarestand ist **nicht identisch** mit der in KNX038 frisch gebauten ATtiny3216-Temperatur-Firmware:

| Merkmal | Ist-Readback | Neuer lokaler Build |
| --- | --- | --- |
| Flashbereich | 32.768 Bytes gelesen | 8.655 definierte Programmdatenbytes |
| Bytes ungleich `FF` | 1.888 | 8.560 |
| Byte-Differenzen gegenüber neuem Image (definierte Build-Adressen) | – | **8.450** |
| Erste Differenz | – | Flashadresse `0x0002` |

Der neue, **bisher nicht geflashte** Build liegt unverändert unter:

`C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX038-ATtiny3216-offline-20261014\attiny3216-temperature.hex`

SHA256: `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`.

Die bestehenden 1.888 Nicht-FF-Bytes belegen ein **nicht leeres Flashabbild**, erlauben aber keine sichere Identifikation der ausgeführten Anwendung. Ein UPDI-Lesezugriff beweist auch **nicht**, dass eine bestehende Temperatur-UART-Verbindung RP2040↔ATtiny bereits funktioniert.

## 5. Nächste Engineering-Schritte

- Für die kommende Temperature-Firmware die echte `1E 95 21`-Signatur als erforderliche harte Gerätekennung verwenden, bevor geschrieben wird. Bei abweichender Signatur **kein Upload**.
- Alt-Flash, EEPROM, Fuses und USERROW einschließlich Prüfsummen erhalten, bevor ein bewusst freigegebenes **Flash-/Verify** durchgeführt wird. Fuseänderungen nicht automatisch vornehmen; der frühere PlatformIO-Upload enthält `write --erase --verify` und darf nicht blind benutzt werden.
- ATtiny USART0 ALT1 auf PA1/PA2 und RP2040 GPIO8/GPIO9 nach erfolgreichem Temperatur-Flash zunächst **ohne KNX-Bus und ohne angeschlossene Motoren** testen.
- Die PCB/BOM-Verwendung `ATTINY1616-SN` gesondert auf den **realen ATtiny3216** korrigieren (Footprint und Verfügbarkeit prüfen). Diese statische Bestandskorrektur ist noch **nicht** in die PCB-Datei geschrieben.
- KNX035: R17/STKNX-KNX_TX-HIGH-Hazard, möglicher U9-Hitzeschaden und TPUart-Firmwarekonflikt unverändert. KNX034: F1-/D1-/Versorgungsgates unverändert. Es gibt keine KNX- oder Motorfreigabe durch KNX039.

**Fazit:** `LIVE_UPDI_SIGNATURE_AND_FLASH_EEPROM_FUSES_USERROW_READBACK_PASS`; **UPDI-Verbindung funktioniert.** ATtiny-Flash-Write weiterhin **nicht durchgeführt**; die gesicherte bisherige Firmware ist noch installiert.
