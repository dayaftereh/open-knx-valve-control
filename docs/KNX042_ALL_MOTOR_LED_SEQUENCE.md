# KNX042 – RP2040-LED-Sequenz für acht Motor-Kanäle

Stand: 14.10.2026. Arduino-Pico-Testsketch erfolgreich gebaut, gesichert und geprüft. **Noch NICHT geflasht; die neue Sequenz wurde noch NICHT an echter Hardware ausgeführt.** Das vorherige KNX042-M1-Diagnoseimage läuft weiterhin.

## Zweck und Hardwarevoraussetzungen

Nur Sichtprüfung der 8 Motorfreigabe- und OPEN/CLOSE-LEDs, **ohne angeschlossenen KNX-Bus oder Ventilmotoren, nur mit USB-Strom**. TB6612 STBY ist V1.2-fest HIGH; es gibt kein unabhängiges Hardware-STO. KNX_TX/GPIO0 ist während Reset und BOOTSEL nicht garantiert LOW (bekanntes KNX/R17/U9/U11-Problem). KNX daher während des gesamten Tests physisch abgezogen lassen.

Dies ist kein produktiver Ventilregler. Das minimale Sequenz-Sketch enthält nicht die alte ATtiny-Temperatur-UART-Diagnose. Für deren Wiederherstellung ist das gesicherte frühere UF2 vorgesehen.

## Testablauf

Reihenfolge pro Runde:

M1 CLOSE → M1 OPEN → M2 CLOSE → M2 OPEN → M3 CLOSE → M3 OPEN → M4 CLOSE → M4 OPEN → M5 CLOSE → M5 OPEN → M6 CLOSE → M6 OPEN → M7 CLOSE → M7 OPEN → M8 CLOSE → M8 OPEN

- Jeder Schritt: **1 Sekunde EIN, danach 1 Sekunde alles AUS** (auch beide gemeinsame Richtungsleitungen).
- Insgesamt **5 komplette Runden** mit nominal 160 Sekunden; ein zweites Software-Limit liegt bei 180 Sekunden.
- **Nie mehr als ein** Motorkanal freigegeben. CLOSE = GPIO18 LOW/GPIO19 HIGH, OPEN = GPIO18 HIGH/GPIO19 LOW.
- Alle Ausgänge sind bei Start/Reset LOW. Die Sequenz startet **niemals automatisch nach Boot**, sondern nur nach den expliziten USB-Kommandos ARM LEDS_ONLY und START ALL 5.
- Das USB-Kommando STOP schaltet sämtliche GPIO sofort LOW. STATUS ist ausschließlich lesend.
- Nach fünf Runden endet der Ablauf automatisch; für eine Wiederholung erneut starten.

| Motor | Enable GPIO | Anzeige-LED / Vorwiderstand |
| --- | --- | --- |
| M1 | GPIO10 | LED12 / R48 |
| M2 | GPIO11 | LED16 / R54 |
| M3 | GPIO12 | LED11 / R47 |
| M4 | GPIO13 | LED15 / R53 |
| M5 | GPIO14 | LED9 / R45 |
| M6 | GPIO15 | LED13 / R51 |
| M7 | GPIO16 | LED10 / R46 |
| M8 | GPIO17 | LED14 / R52 |

OPEN hängt an IN_1 GPIO18 über R41; CLOSE an IN_2 GPIO19 über R43.

## Projektdateien

- [Arduino-Pico Sketch](../tools/knx042_led_sequence/src/main.cpp)
- [PlatformIO-Konfiguration](../tools/knx042_led_sequence/platformio.ini): Flash-Upload absichtlich deaktiviert
- [USB-Start/Status/Stop-Client](../tools/knx042_led_sequence_control.py)
- [Offline-Regression](../tools/test_knx042_led_sequence.py)

PlatformIO-Build auf dem LLO Desktop Agent: C:\Users\LLO\.platformio\penv\Scripts\python.exe -m platformio run -d tools/knx042_led_sequence -e knx042_led_sequence

**Build PASS**, KNX042-Testgruppe **22/22 PASS**, UF2-Struktur und Checksummen geprüft.

## Gebaute UF2-Datei und Backup

**Verzeichnis:** C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX042-ALL-MOTOR-LED-SEQUENCE-20261014

| Datei | SHA-256 | Verwendung |
| --- | --- | --- |
| knx042-all-motor-led-sequence-5rounds.uf2 | 959cde9090d8ddc1258971fed548aa01c823254105ae1ac3f292fb01790c2875 | Neues Bild, NICHT installiert |
| rollback-knx042-m1-180s.uf2 | 7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d | Vorheriges verifiziertes M1-Testimage |

Manifest mit Gerätedaten und Dateiprüfsummen: manifest.json im selben Build-Verzeichnis. Die Rollback-Kopie stammt aus der vorhandenen KNX042-Original-UF2, nicht aus einem neuen Auslesen des Flash-Speichers.

## Noch ausstehendes Flash-Gate

1. **Physisch sicherstellen:** KNX-Bus getrennt, alle Ventilmotoren abgeklemmt, keine weitere Versorgung, ausschließlich USB-Strom. Nicht bei eingeschalteter Platine löten.
2. Der automatische Versuch picotool reboot -f -u meldete: Unable to locate reset interface on the device. Der RP2040 war dabei USB-CDC, nicht BOOTSEL.
3. Manuell in BOOTSEL: USB-Kabel abziehen, Taste USB_BOOT gedrückt halten, USB wieder anschließen, Taste loslassen.
4. Mit picotool info -a prüfen, dass RP2040 Rev B2 mit 16-MB-Flash im ROM-BOOTSEL erkannt wird.
5. Nur das oben genannte SHA-verifizierte neue UF2 mit picotool load -v -x und genau diesem Dateipfad flashen/verifizieren/neustarten.
6. Anschließend neue USB-Kennung KNX042 LED SEQUENCE READY und STATUS seq=0 active=0 prüfen.

Start nach ausdrücklicher Bestätigung aller Sicherheitsbedingungen:

    C:\Users\LLO\.platformio\penv\Scripts\python.exe tools/knx042_led_sequence_control.py start --port COM7 --expect-serial E464401787522D33 --knx-disconnected --motors-unplugged --usb-only --leds-current-limited

Status (read-only):

    C:\Users\LLO\.platformio\penv\Scripts\python.exe tools/knx042_led_sequence_control.py status --port COM7 --expect-serial E464401787522D33

Manueller Stopp:

    C:\Users\LLO\.platformio\penv\Scripts\python.exe tools/knx042_led_sequence_control.py stop --port COM7 --expect-serial E464401787522D33

Die LED-Sichtprüfung muss der Benutzer vornehmen; USB-ACK oder GPIO-Befehle ersetzen keine reale Spannungs- oder Lastmessung. KNX und Motorlasttests bleiben gesperrt. Kein Git-Push ohne Freigabe.
