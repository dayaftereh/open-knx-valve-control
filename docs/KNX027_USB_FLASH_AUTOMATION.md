# KNX027 - RP2040 USB Auto-Upload und Recovery

**Stand: 12.10.2026 - Software vorbereitet, kein physischer USB-Flash nachgewiesen.**

## Zweck und verifizierte Grundlage

Der RP2040-Controller verwendet Arduino-Pico 5.5.0, PlatformIO und den bestehenden USB-CDC-Anschluss Serial.begin(DefaultSerialBaud). Arduino-Pico verarbeitet bei funktionierendem USB CDC einen 1200-Baud-Port-Open/Close als Reset-to-Bootloader. PlatformIO mit **upload_protocol = picotool** kann den gewaehlten USB-COM-Port dafuer verwenden. KNX027 macht das Uploadprotokoll in src/controller/controller.ini explizit, ohne Motor-, ETS-, KNX- oder ATtiny-Code anzufassen.

Wichtig: USB-Serial (Serial) ist nicht der KNX-UART (Serial1) und auch nicht der ATtiny-UART (Serial2). Der 1200-Baud-Trick funktioniert nur, wenn der USB-Stack des bereits laufenden Programms antwortet. Bei Erstflash oder abgestuerzter Firmware weiterhin den RP2040-ROM-BOOTSEL-Modus verwenden.

Offizielle Quellen:
- https://arduino-pico.readthedocs.io/en/stable/serial.html
- https://arduino-pico.readthedocs.io/en/latest/usb.html
- https://github.com/earlephilhower/arduino-pico/blob/master/docs/install.rst
- https://docs.platformio.org/en/stable/boards/raspberrypi/pico.html

## Kommandos im Projekt-Root

Python, PlatformIO, OpenKNXproducer und Git muessen auf dem Rechner installiert sein. Der Desktop hat PlatformIO Core 6.1.19; das neue Tool sucht pio im PATH oder im PlatformIO-Standardpfad unter dem Windows-Benutzerprofil, alternativ per Umgebungsvariable PIO_EXECUTABLE. OpenKNXproducer kann per PATH, OPENKNXPRODUCER_EXECUTABLE oder Desktop-Toolpfad gefunden werden.

### 1. Passiv USB-Ports anzeigen

~~~powershell
python tools/usb_flash_controller.py probe
~~~

Das fragt PlatformIO nach seriellen COM-Ports, Beschreibungen und ggf. USB VID:PID ab. Keine Verbindung wird geoeffnet, kein Reset, kein Upload. Am 12.10.2026 zeigte der LLO Desktop nur COM1 (ACPI) und COM3 (Intel AMT), **keinen RP2040**. Auf dem spaeteren LLO Laptop muss die Zuordnung erneut bestimmt werden. Eine VID:PID allein beweist keine physische Identitaet: Geraet vor/nach USB-Anstecken und Deskriptor/Seriennummer bzw. bestueckte Platine vergleichen.

### 2. Offline-Plan (keine Hardwareaktion)

~~~powershell
python tools/usb_flash_controller.py plan --port COM5 --expect-vidpid 2E8A:00C0
~~~

COM5 und 2E8A:00C0 sind ausschliesslich Beispieldaten. Dieser Aufruf macht weder eine reale Portpruefung noch einen Firmwarebuild oder Upload.

### 3. Firmware ohne Upload isoliert bauen

~~~powershell
python tools/usb_flash_controller.py build --output-uf2 C:\ASH\Workspace\Builds\OpenKNXValveControl\controller-recovery.uf2
~~~

Die Ausgabedatei darf vorher nicht existieren (keine Ueberschreibung). Bei Bedarf das Argument --output-uf2 weglassen. Der Builder legt eine temporaere Kopie von Projekt-/Firmwarequellen samt OpenKNXproducer-Assets an und baut dort den Controller. Er verlangt firmware.elf und eine nichtleere firmware.uf2, meldet den UF2-SHA256 und prueft, dass der Hash der originalen Git-Datei include/knxprod.hpp unveraendert bleibt.

**Keine Build-/UF2-Dateien ungeprueft in das Repository committen.** Den Recovery-Build explizit ausserhalb des Git-Projektroots speichern.

### 4. Erst nach elektrischem KNX018-Teststand: bestaetigter USB-Upload

~~~powershell
git status --short --branch
git rev-parse HEAD
python tools/usb_flash_controller.py probe

# Beispiel-Port, Beispiel-USB-ID und BEISPIEL-Git-HEAD ersetzen:
python tools/usb_flash_controller.py upload --port COM5 --expect-vidpid 2E8A:00C0 --expected-head 0123456789abcdef0123456789abcdef01234567 --execute --confirm-safe-bench
~~~

Der Vollstaendigkeitscheck verweigert einen Upload, solange eine der folgenden Bedingungen nicht erfuellt ist:

1. Es wurden ausdruecklich --execute und --confirm-safe-bench uebergeben. Die zweite Option erklaert die MANUELLE Pruefung eines isolierten, elektrisch sicheren Teststands; das Skript kann elektrische Sicherheit nicht messen.
2. --port nennt genau einen aktuell vorhandenen COM-Port. Keine automatische Auswahl eines anderen COM-Ports, selbst bei Fehler.
3. --expect-vidpid stimmt mit dessen USB-Hardware-ID exakt ueberein. Nicht-USB-Ports, unklare Hardware-IDs und Duplikate werden abgewiesen.
4. --expected-head stimmt mit dem vollstaendigen 40-stelligen aktuellen Git-Commit ueberein; das Repository ist clean.
5. Der isolierte Build erzeugt firmware.elf und firmware.uf2, ohne den Git-Header zu veraendern. Kurz vor dem Upload wird die COM-/VID:PID-Identitaet erneut abgeglichen.

Erst dann wird **genau ein** PlatformIO-Upload im temporaeren Build-Verzeichnis ausgefuehrt:

~~~powershell
pio run -e controller -t upload --upload-port COM5
~~~

Das Programm wiederholt fehlgeschlagene Flashversuche nicht selbst und aendert die COM-Zuordnung nicht. Der Upload-Exitcode allein weist noch nicht nach, dass die Firmware auf der Hardware korrekt laeuft. Nach dem Neustart: USB-Neuerkennung, korrekte Firmwareversion sowie KNX-/UART-Diagnosen separat kontrollieren. Motoren bleiben gesperrt.

### 5. BOOTSEL-Erstflash oder Recovery bei nicht antwortendem USB

Wenn noch keine kompatible USB-CDC-Firmware laeuft, kein COM-Port vorhanden ist oder das Programm haengt:

1. **Nur** die elektrisch gepruefte, isolierte Controllerplatine **ohne angeschlossene Ventilmotoren** verwenden.
2. BOOTSEL beim Einstecken oder Reset gedrueckt halten, bis das ROM-Laufwerk RPI-RP2 erscheint.
3. Mit dem obigen Build-Kommando eine bekannte, verifizierte UF2 erzeugen; SHA256/Quelle pruefen.
4. UF2 manuell auf das eindeutig erkannte RPI-RP2-Laufwerk kopieren, Neustart abwarten.
5. Danach die USB-CDC-Portliste neu abfragen und zunaechst nur Diagnose testen. Erst mit einer laufenden USB-CDC-Firmware kommen automatische Updates ohne BOOTSEL in Betracht.

SWD mit separater Debug-Probe bleibt spaetere Recovery-Option. Das jetzige Skript schreibt **nie** automatisch auf beliebige Laufwerke.

## Verbindliche Hardware-Sperren

- KNX018 Laptop-Teststand ist noch nicht aufgebaut; automatischer Upload auf echter Platine nicht freigegeben oder getestet.
- KNX002/003: reale 3,3-V-/5-V-, USB-/KNX-Rueckspeisung und Bauteilbestueckung muessen geklaert sein; alle Motoren abgeklemmt.
- KNX022: vier TB6612FNG-STBY-Eingaenge sind auf V1.2 fest an 3,3 V verdrahtet; keine unabhaengig verifizierte Motorabschaltung. Software-Faults und erfolgreiche UF2-Uploads ersetzen sie nicht.
- Die aktuelle PlatformIO-Konfiguration nimmt 16 MiB Flash und ein bestimmtes Dateisystemlayout an. Den tatsaechlich bestueckten Flashchip und dessen Speichergroesse vor echtem Flashen pruefen.
- RP2040-USB-Upload ist unabhaengig vom ATtiny-Programmer: dessen CN1-USB/UPDI-Pegel- und 5-V-/3,3-V-Rueckspeiserisiko bleibt offen; keinen ungeprueften CN1-Verbinder aufstecken.
- ETS AppVersion2/KNX009/KNX016 und der echte KNX-Bus bleiben zurueckgestellt. Das Skript veraendert weder Motor- noch Bus-Logik.

## Softwaretests

~~~powershell
python tools/test_usb_flash_controller.py
python tools/usb_flash_controller.py probe
python tools/usb_flash_controller.py plan --port COM5 --expect-vidpid 2E8A:00C0
python tools/usb_flash_controller.py build
python tools/audit_knx027_usb_flash_scope.py
python tools/audit_ash_workflow.py
~~~

Acht lokale, simulierte Python-Tests pruefen positive/negative Port-Zuordnung, fehlende Freigabe, falsche Git-ID, Dirty-Tree, Generator-Isolation und einen einzigen autorisierten (gemockten) Upload. Es findet dabei KEIN physisches Flashen statt.

**Liefergrenze:** Host-Code und Build koennen jetzt vorbereitet und in Git versioniert werden. Der reale Test der 1200-Baud-USB-Reenumeration, des Windows-Treibers und des Flashvorgangs ist ausdruecklich ein spaeteres KNX018-Laborthema.
