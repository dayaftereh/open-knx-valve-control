# KNX092 – LLO Desktop: INA219 repariert und erster M1-Stromtest

Stand: 20.10.2026, Büroprüfstand OpenKNXValveControl V1.2.

## Aktueller Hardwarestand

Laut Nutzer wurden R33 und R34 durch je 10 Ohm ersetzt. Direkt an den
INA219-Sense-Eingängen wurden 0,00 mV DC gemessen. Angeschlossen waren
ausschließlich USB-C am RP2040 und ein Motor M1. Kein KNX, UPDI,
zweiter Motor oder DS18B20 an der Testplatine.

Die echte Platine wurde am LLO Desktop eindeutig erkannt: COM7,
VID:PID 2E8A:000A, USB-Seriennummer E464401787522D33. Weitere
COM8/9/10 CH340-Adapter gehören zum Arbeitsplatz, nicht zur Platine.

Git-Startstatus: main bei 8600aff, sauber und synchronisiert.

## INA219 nach dem Austausch: PASS

KNX089 mit hardwareseitig gesperrten Motorausgängen lieferte bei
zwölf wiederholten USB-Lesezyklen:

- I2C-Adresse INA219 0x40; Konfigurationsregister 0x399F.
- Shunt-Rohwert ca. 0x000C bis 0x0010, entsprechend ca. 0,12–0,16 mV.
- Bus-/Motorversorgung 3288–3292 mV.
- R29 200 mOhm: ruhender Schienenstrom etwa 0,6–0,8 mA.
- USB meldet 0 mA, weil die Firmware nur ganze mA ausgibt.
- Motorausgänge LOW, KNX TX LOW, Motor IDLE, KNX_RX 0 Kanten.
- T0–T3 fehlen planmäßig; das wurde nicht als Fehler interpretiert.

Der alte falsche Ruhestrom von ca. 463 mA/92,6 mV ist nach dem
Austausch der Sense-Widerstände R33/R34 verschwunden. Somit war
der Messpfad, nicht die INA219-I2C-Konfiguration, die Ursache.

## Firmwarewechsel: geprüftes KNX085 auf dem Büro-PC

Die KNX085-Testfirmware wurde von LLO Home als gepinntes UF2-Binärbild
übertragen und auf LLO Desktop geprüft:

  C:\ASH\Workspace\Runtime\KNX092\knx085_bench_unlocked.uf2

UF2: 242688 Byte.
SHA256: 86CBF6942FD12EBA07402C52842BA7543CABD2C2A557A329607C954388A54750.

Der Desktop-PlatformIO-Start war zunächst nicht funktionsfähig
(platformio.exe vorhanden, Python-Modul fehlte). Es wurde deshalb
die bereits geprüfte identische KNX085-Firmware verwendet.

Nach erfolgreicher KNX089-Motor-LOCKED-Vorprüfung wurde per
1200-Baud-CDC der ROM-Bootloader betreten. Windows meldete den
RP2040 als RP2 Boot auf COM6, aber NICHT als RPI-RP2-Laufwerk.
Das vorbereitete Massenspeicher-Uploadverfahren verweigerte
daraufhin ohne Firmwarekopie und ohne automatischen zweiten Reset.

Das vorhandene picotool v2.0.0 identifizierte den einzigen ROM-Chip:
RP2040 Revision B2, Flash-ID 0xE464401787522D33,
also genau die Hardware der vorherigen COM7-Platine.

Einmaliges picotool LOAD mit -v (verifizieren) und -x (starten)
übertrug das gepinnte UF2. Verifikation 100% OK.
Danach erschien der Controller auf COM7 mit KNX085 motor_gate=1,
Motor IDLE, alle Motoren und KNX TX LOW. Der INA219 blieb
plausibel mit 3,292 V und nominal 0 mA im Leerlauf,
mindestens 119 gültigen Idle-Messungen.

## Erster echter M1-Puls

Einziges Motorsignal: M1 Richtung F, genau 150 ms angefordert.
Vorher: einmalig ARM MOTORS mit 5-Sekunden-Freigabefenster.
Die Firmware bestätigte PULSE_STARTED, dann MOTOR_ENDED state=IDLE.
Redundanter STOP wurde mit STOPPED_ALL_OFF quittiert.
Nach Abschluss waren TX/Motor-GPIOs LOW, IDLE und
der INA219 zeigte wieder 0 mA an.

18 von 18 INA219-Tracepunkte waren gültig, Zeitraum
7 bis 143 ms, nominelles Abtastintervall ca. 8 ms.

| Messgröße | Live-Ergebnis |
| --- | --- |
| Maximaler aufgezeichneter Strom (t=7 ms) | 108,15 mA |
| Median Motorstrom | 46,875 mA |
| Minimum innerhalb des Motorimpulses | 31,05 mA |
| Strom am letzten Tracepunkt (t=143 ms) | 31,65 mA |
| Motorspannung während des Impulses | 3260–3280 mV |
| Strom im Leerlauf nach STOP (Firmware ganze mA) | 0 mA |
| Automatisches Ende | IDLE |
| Fehlermeldung / FAULT | keine |
| Motor physisch sichtbar gedreht | noch nicht vom Nutzer bestätigt |

Anlaufstrom: t7ms 108,15mA, t15ms 98,80mA,
t23ms 83,25mA, t31ms 75,15mA, dann abfallend
auf ca. 31–34mA am Ende. Typisch für beschleunigenden DC-Motor,
aber kein eigenständiger Beweis für mechanische Bewegung.

Grenze der Aussage: Sehr schnelle Einschaltspitzen vor der
ersten 8-ms-Abtastung wurden NICHT erfasst. Der Softwarestromschutz
mit 120 mA Grenzwert ist kein echter Hardware-Strombegrenzer;
STBY der TB6612 liegt auf PCB V1.2 dauerhaft HIGH.

Privater Mess- und Firmwareordner auf LLO Desktop:

  C:\ASH\Workspace\Runtime\KNX092

Dateien:
- KNX092_M1_20261020_073811.json
- KNX092_M1_20261020_073811.csv
- knx085_bench_unlocked.uf2
- KNX092_FLASH_STARTED.flag
- KNX092_M1_PULSE_STARTED.flag

Die Flag-Dateien verhindern ein automatisches Wiederholen
eines bereits ausgelösten Flash- oder Motorversuchs.

## Desktop-Skript und weitere Entwicklung

Das neue Tool tools/knx092_office_usb_m1.py ist auf das
echte Office-USB-Setup zugeschnitten. Es akzeptiert nur COM7
mit genau der RP2040-Seriennummer und ignoriert die anderen
CH340-Geräte auf dem Büro-PC. Keine KNX-/UPDI- oder
Temperatursensorpflicht an der isolierten Platine.

Stufen: preflight (KNX089), flash (KNX085, fester SHA256),
verify (KNX085), pulse (einmal M1 F 150ms).
ROM-Bootloader-Fallback: picotool mit RP2040-Flash-ID-Prüfung,
wenn Windows kein Laufwerk einbindet, ohne erneuten CDC-Reset.
Einzelpulse haben STOP-Readback und JSON-/CSV-Protokoll;
keine verdeckten Wiederholungen oder Endanschlagfahrten.

Regression tools/test_knx092_office_usb_m1.py: 5/5 PASS.
Python-Syntaxprüfung: PASS.
Firmware nach dem Motorversuch nochmals read-only überprüft:
KNX085 gate1, M1/M2 LOW, IDLE, INA idle_ok=1.

Nächster Schritt: Mechanische M1-Bewegung durch den Nutzer
visuell bestätigen lassen. Danach bewusst Folgeversuch, z.B.
kurz rückwärts oder längeres Zeitprofil, mit Blick auf
Stromkurve, Getriebe, Endanschlag und Positionserkennung planen.

Keine automatische weitere Motorfahrt. Kein Git-Push ohne
ausdrücklichen neuen Auftrag.

## Desktop-Entwicklungsumgebung wiederhergestellt

PlatformIO-CLI hatte auf Desktop eine defekte/missing Python-Distribution (platformio.exe war vorhanden, Modul nicht). Version **6.1.16** wurde aus dem lokal zwischengespeicherten Wheel wieder in die Desktop-venv installiert (ohne Internet/Download). PlatformIO Core --version 6.1.16 PASS; anschliessend echter Build env knx085_bench_unlocked **SUCCESS** in 33,36s (RAM 16,7%, Flash 5,2%). Kein Upload beim Build.

**Wichtige Reproduzierbarkeitsabweichung:** Die auf Desktop frisch gebaute UF2 hat zwar ebenfalls 242688 Byte, aber SHA256 7A71FE13A4D489FA69B588FB479F6723F30940B2318A8AF98A93218999D0094D. Das ist NICHT byte-identisch mit dem oben dokumentierten, auf COM7 wirklich installierten und zuvor gepinnten Home-Image (SHA256 86CBF694...). Ursache der Build-Hash-Differenz noch nicht aufgeloest; es wurde dadurch **kein** weiterer Firmwarewechsel ausgeloest. Vor neuen Releases Buildversionen/Artefakte gezielt vergleichen und erneut identifizieren.
