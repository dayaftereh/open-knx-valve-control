# KNX037 – Reale RP2040-Programmierung auf LLO Desktop und COM4-UPDI-Sicherheitsgate

**Stand:** 14.10.2026. **Echter RP2040-Flash und USB-Diagnose PASS.** CH340 erkannt, aber **keine UPDI-Kommunikation und kein ATtiny-Flash**. Kein KNX-Bus oder Motorbetrieb.

## 1. Live zugeordnete USB-Geräte

| Zustand | USB-Kennung | Windows COM |
| --- | --- | --- |
| Vorherige Blink-Firmware des RP2040 | `2E8A:00C0` | **COM5** |
| CH340 Units Programmer V1.2 | `1A86:7523` | **COM4** |
| RP2040 ROM Bootloader | `2E8A:0003` | temporär **COM6** |
| Isolierte KNX036-Diagnosefirmware | `2E8A:000A` | jetzt **COM7** |

COM1 (ACPI-Kommunikationsanschluss) und COM3 (Intel AMT SOL) sind PC-interne Schnittstellen und wurden nicht angesprochen. Windows-Snapshots mit gehashten PnP-IDs liegen ausschließlich außerhalb Git in `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX037-20261014-two-ports.json` und `KNX037-20261014-after-diag.json`. Nach dem realen Upload dokumentiert der Vergleich COM5/VID:PID 2E8A:00C0 entfernt, COM7/2E8A:000A hinzugefügt.

## 2. Tatsächlich durchgeführter erster RP2040-Flash

1. USB-Identität COM5 2E8A:00C0 und COM4 1A86:7523 live durch Windows und PySerial bestätigt. Die bestehende Blink-Software war auf COM5 115200 Baud erreichbar, gab bei rein lesendem Test aber **0 Bytes** aus.
2. Ausschließlich das isolierte [KNX036-USB-Diagnoseimage](../tools/knx036_usb_diag/platformio.ini) verwendet, **nicht** die bekannte fehlerhafte KNX-Produktivfirmware. UF2: **141.312 Bytes**, SHA256 `ad8df9ba4426102fb240f2ebfbb9526071b91e563fab897ab04034ed766866de`. Sie liegt mit Manifest außerhalb Git in `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX036-desktop-usb-diagnostic-20261014`.
3. Ein erstes direktes `picotool load -f` konnte die laufende Anwendung nicht unmittelbar in den Bootloader überführen (keine Flashaktion). Danach gezielt **COM5 mit 1200 Baud, DTR True→False und RTS False** kurz geöffnet, ohne serielle Nutzdaten zu senden. Das löste den **automatischen RP2040-BOOTSEL-/ROM-Einstieg** aus, ohne die Taste drücken zu müssen.
4. `picotool info -a` am echten ROM-Gerät: **RP2040 Revision B2, externer Flash 16.384 KiB (16 MiB)**. Damit ist die Flashgröße real bestätigt.
5. `picotool load -v -x <KNX036-UF2>`: Flash Schreiben **100 %**, Verify **100 %**, `OK`, automatischer Neustart. Auf dem Gerät läuft nun das KNX036-USB-Heartbeat-Programm, das GPIO0/KNX_TX **nach setup()** LOW setzt und sonst keine KNX-/ATtiny-/Motoransteuerung enthält.
6. Nach Neustart enumeriert die Anwendung auf **COM7 / 2E8A:000A**. Bei 115200 Baud, RTS False, DTR True (USB-CDC host-ready) wurden **3/3**, später **4/4 gültige Heartbeats** empfangen:

       KNX036 USB-ONLY RP2040 ALIVE uptime_ms=66002 seq=1
       KNX036 USB-ONLY RP2040 ALIVE uptime_ms=68002 seq=2
       KNX036 USB-ONLY RP2040 ALIVE uptime_ms=70002 seq=3

Diese echte Beobachtung beweist **RP2040 USB/Flash/ROM-Reset/USB-CDC**. Sie beweist weder sichere KNX-Telegramme noch einen fail-LOW-Startzustand bei RP2040-Reset noch reale ATtiny-Sensoren.

## 3. Reproduzierbarer, zusätzlich abgesicherter RP2040-Workflow

[KNX037 Kommandozeilenwerkzeug](../tools/knx037_rp_usb_workflow.py): Standardaktion `plan` ohne Hardwarezugriff, `probe` nur Windows/PySerial-Geräte-Metadaten, `listen` öffnet ausschließlich ein explizit nach VID/PID **und voller USB-Serienkennung** verifiziertes RP2040-CDC-Gerät und liest mindestens zwei Heartbeats. COM4/CH340 wird vom Werkzeug **niemals geöffnet**.

    Set-Location 'C:\ASH\Workspace\Projects\open-knx-valve-control'
    $py = 'C:\Users\LLO\.platformio\penv\Scripts\python.exe'
    & $py tools/knx037_rp_usb_workflow.py plan
    & $py tools/knx037_rp_usb_workflow.py probe
    $usbSerial = (& $py -c 'from serial.tools import list_ports; print(next(p.serial_number for p in list_ports.comports() if p.device.upper()=="COM7"))').Trim()
    & $py tools/knx037_rp_usb_workflow.py listen --port COM7 --expect-vidpid 2E8A:000A --expect-serial $usbSerial

Für eine **spätere erneute Flashaktion** verlangt der `flash`-Befehl zusätzlich den kompletten bekannten UF2-SHA256, einen passenden KNX036-Manifest-Eintrag und explizite Flags `--execute --confirm-no-knx --confirm-no-motors --confirm-safe-power --confirm-updi-cable-disconnected`. Nur dann öffnet er den gewählten RP2040-CDCPort bei 1200 Baud, verifiziert eindeutigen ROM-Bootloader und lässt exakt einen `picotool load -v -x` mit anschließendem Heartbeat-Lesetest laufen. Standardmäßig **keine Uploadautorität**.

**Wichtig:** Dieses Tool wurde erst **nach** dem obigen ersten realen, manuell gesteuerten Flash erstellt und ist eine Wiederholungsabsicherung; seine Schutzbestätigungen sind keine rückwirkend gemessenen Daten des ersten Versuchs. Der ehemalige COM5-Port ist für aktuelle Befehle falsch; Port- und USB-Kennung nach jedem Reboot prüfen.

## 4. COM4 CH340: RTS-Schaltlogik bekannt, 3,3-V-Pegel ungeprüft

Der real erkannte CH340 ist der vom Nutzer genannte **COM4 / VID:PID 1A86:7523**. Der existierende Units-V1.2-Programmer-Service setzt im **UPDI-Modus** die logischen Signale:

    port.setSignals({ dataTerminalReady: true, requestToSend: true })

Beim Schließen setzt der Service beide auf `false`. Das Programmer-PCB ist über die RTS-Leitung an zwei SN74LVC1G3157-Umschalter (U2/U7, Pin 6) verbunden; deren Versorgung `VCC` hängt an der USB-Versorgung des CH340. **CH340 RTS# ist aktiv-low**; logisches `true` ist nicht dasselbe wie ein gemessener HIGH-Pegel an einem Pin.

**Ungeklärte Sicherheitsgrenze:** Die ValveControl-V1.2 hat `CN1.1 = 5V`, `CN1.3 = UPDI`, `CN1.5/6 = GND`, und U25/ATtiny wird mit **3,3 V** betrieben. Auf Programmer-Seite liegen U1 CH340G VCC und U2/U7-MUX-VCC am USB-`VCC`. **Die UPDI-Ausgangsspannung und eine eventuelle 5-V-Einspeisung über CN1.1 sind noch nicht gemessen**. Ungeprüftes Setzen von RTS kann über die Programmerleitungen den 3,3-V-Eingang des ATtiny beanspruchen.

Darum bisher **kein COM4-Open, kein RTS-/DTR-Toggle auf COM4, kein `pymcuprog ping`, kein ATtiny-Erase/Write**. Ein späterer erster Test beginnt mit einem **vom Zielboard vollständig getrennten sechspoligen CN1-Kabel**: am allein mit PC-USB versorgten Programmer VCC/GND, CN1 Pin 1, CN1 Pin 3 (UPDI) und RTS=False/True Pegel mit geeigneter Messtechnik kontrollieren. Erst nach belegter 3,3-V-kompatibler Ansteuerung, Pin1-/Versorgungstrennung und gemeinsamer Masse kann ein **read-only** UPDI-Signaturtest stattfinden. U25 soll laut Firmware ATtiny3216 sein; historische PCB-BOM nennt ATTINY1616-SN, daher **kein Blindflash**.

## 5. Übrige offene Gates

Das USB-Testimage ist für **KNX Bus abgeklemmt und Motoren abgeklemmt**. Die bekannte V1.2-R17-Pull-up-Fehlbeschaltung auf aktiv-HIGH-STKNX-KNX_TX, Überhitzung U11 und möglicher U9-Schaden, F1-Foto T2,5 A versus Schaltplan 630 mA, D1-Draht-Bypass und USB/KNX-Rückspeisung sind nicht durch USB-CDC-Heartbeat erledigt. Die KNX-Produktivfirmware nutzt weiterhin **ungeeignetes TPUart::ArduinoSerial(Serial1)**, kein getesteter STKNX-Pulstreiber.

**Status:** `RP2040_FLASH_AND_HEARTBEAT_REAL_PASS`. `CH340_USB_ENUM_PASS`. `ATTINY_UPDI_BLOCKED_PENDING_CABLE_AND_VOLTAGE_VERIFICATION`. **Keine KNX-/Motorfreigabe.**

## KNX038 Nachtrag (14.10.2026)

Die Units-V1.2-UPDI-Schaltung und RTS-MUX-Netze wurden nochmals live geprueft; [aktueller KNX038-Runbook- und Sicherheitsstand](KNX038_UPDI_RTS_ELECTRICAL_GATE.md). Die Temperatur-ATtiny3216-Firmware kompiliert erfolgreich, HEX+ELF sind im Desktop-Builds-Ordner SHA256-dokumentiert; die **COM4-UPDI-Initialisierung wurde jedoch weiterhin nicht ausgefuehrt**, da am mit dem Board mutmasslich verbundenen 2x3-CN1-Kabel noch nicht gemessene Pegel/Pin1-Power-Gates bestehen. Dieser Nachtrag aendert keine der zuvor erfolgreichen realen RP2040-Flash-/Heartbeat-Ergebnisse.
