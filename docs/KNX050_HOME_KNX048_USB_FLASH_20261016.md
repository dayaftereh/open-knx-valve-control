# KNX050 – KNX048 RX-only mit 16K-Ring auf LLO Home installiert

**Stand:** 16.10.2026, 00:15 MESZ (15.10.2026, 22:15 UTC).
**Status:** USB-only Firmwareinstallation **ERFOLGREICH**, reale KNX-TP-Empfangsmessung **noch nicht durchgeführt**.

## 1. Anlass / physischer Zustand

Der Nutzer bestätigte im Chat nach ausdrücklicher Nachfrage, dass die KNX-Leitung von der Platine abgetrennt sei, und gab die Freigabe für das Firmwareupdate. Diese physische Trennung kann der Agent **nicht** elektrisch oder optisch überprüfen. Motor-, Sensor- und weitere Leitungen wurden während KNX050 nicht unabhängig inspiziert. Aufgrund der früheren U11-Erhitzung bleibt der Anschluss an den produktiven KNX-Hausbus gesperrt.

Verwendetes Zielgerät: OpenKNXValveControl PCB V1.2 / RP2040, USB VID/PID `2E8A:000A`, Seriennummer `E464401787522D33`, anfänglich und anschließend `COM8`.

## 2. Vorprüfung auf LLO Home

- Agent: online / Version `0.7.9`, vorherige Sessions vollständig geschlossen, keine laufenden Jobs bei Eröffnung.
- Root: `C:\_myspace\workspace\open-knx-valve-control`.
- Baseline: Git `main` **`7cae6bc0c6ee4700b72e06c0128b6e259925b686`**, CLEAN, `origin/main=f647cec87ceb018329015eaf9b04fb87dceba765`, lokal 3 Commits voraus; kein Pull/Push erforderlich.
- Alte Firmware vor Update über USB bestätigt: `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0` (noch ohne `capacity`).
- KNX048 Imagepfad: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX048_RX_BUFFER_20261015\knx048-passive-rx-16k-NOT-FLASHED.uf2` (historischer Name `NOT-FLASHED` gilt nach KNX050 **nicht mehr**).
- KNX048 SHA-256: `af6aa0f228bb6b294bd31f35a3c68b8758afe2e3213da7344a7fffa5f236e70a`, 166.400 Byte, **325 korrekte UF2-Blöcke**, Zieladresse ab `0x10000000`; Quellcode-/Host-Hashes gegen Buildmanifest PASS.
- KNX043-Rollback nach UUID/SHA überprüft: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014\knx043-passive-rx-only-NOT-FLASHED.uf2` 146.432 Byte, 286 Blöcke, SHA-256 `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f`.
- Hardware-Gate-Datei `KNX043_HOME_KNX_GATE.json`: weiterhin **0/17 verifizierte physische Prüfpunkte**, nach Softwarestatus `BLOCKED_AWAIT_HARDWARE_EVIDENCE`. Das USB-only-Update stellt keine elektrische Bus-Freigabe dar.

## 3. Tatsächlicher Flash-Vorgang

1. USB-Überwachung `tools/knx043_usb_bootsel_watch.py` auf LLO Home gestartet; initiale COM8-Enumeration und Seriennummer beobachtet.
2. Arduino-Pico unterstützt Bootloaderwechsel bei 1200 bps / DTR LOW. USB-Port zuvor auf VID/PID und Seriennummer verifiziert. Beim seriellen 1200-bps-Öffnen meldete Windows einen Konfigurationsfehler, **weil USB dabei bereits verschwand**. Dieser Prozess endete mit Exit 1; den Bootloaderzustand haben wir deshalb unabhängig geprüft und **keinen unkontrollierten zweiten Reset** versucht.
3. USB-Monitor: COM8 verschwand **2026-10-15T22:13:34.607Z**; `RPI-RP2`-Laufwerk erschien auf `D:` **2026-10-15T22:13:34.962Z**. Das offizielle Laufwerkslabel und `D:\INFO_UF2.TXT` (`Board-ID: RPI-RP2`) wurden überprüft. Ein separater USB-ROM-COM-Port VID/PID `2E8A:0003` wurde unter Windows **nicht** beobachtet; die ROM-Massenspeicherschnittstelle war jedoch eindeutig erreichbar.
4. KNX048-Hash, alle 325 UF2-Blöcke, eindeutiges `D:`-Bootvolume und Abwesenheit der Anwendung **unmittelbar vor dem Kopieren erneut geprüft**.
5. Offizieller RP2040-UF2-Massenspeicherweg: `Copy-Item` der geprüften KNX048-UF2 nach `D:\KNX048_RX_ONLY.uf2`; **Exit 0**, `UF2_COPY_FINISHED` am **2026-10-15T22:14:19.112Z**.
6. USB-Monitor: `RPI-RP2` verschwand **2026-10-15T22:14:19.545Z**; RP2040 CDC mit Seriennummer `E464401787522D33` erschien auf `COM8` **2026-10-15T22:14:20.076Z**.
7. Vier unabhängige `tools/knx043_rx_capture.py status`-Abfragen auf COM8 jeweils erfolgreich:

    ```text
    KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0 capacity=16383 high_water=0 observed=0
    ```

Die **neuen** Statusfelder, insbesondere `capacity=16383`, bestätigen den Start des KNX048-Images. Das Kommando-Präfix `KNX043 STATUS` bleibt in KNX048 aus Kompatibilitätsgründen erhalten.

**Nachweisgrenze:** Es erfolgte keine unabhängige binäre Rückleseprüfung des RP2040-Flashs; bestätigte UF2-Quelle, Kopierexit, ROM→CDC-USB-Übergang und 4/4 neue Firmware-Statusantworten belegen den erfolgreichen Funktionstest.

## 4. Puffer und Empfang

- Ringspeicher: **16.384 Plätze / 16.383 nutzbare Flanken**, 128 KiB statischer RAM für den Puffer. Theoretische Reservierung ca. 0,85 s bei hypothetischen 19.200 Flanken/s ohne Datenabholung; **kein Garantieversprechen** für verlustfreien Liveverkehr.
- KNX048 überträgt kompakte RX-Flanken `E <time_us> <0|1>`, dazu `observed`, `dropped`, `high_water` und `capacity`. PC-Host kann per JSONL streamen, am Ende Restdaten drainen und die Anzahl verifizieren.
- **Keine** `ARM LISTEN_ONLY`, `START LISTEN`, KNX-TX-Pulse, Motorbefehle, ETS-Schreibvorgänge oder Netzwerk-Telegramme im Rahmen dieses Updates. `listen=0` und `observed=0` bedeuten, dass noch keine tatsächliche Empfangsaufzeichnung stattgefunden hat.
- Für den ersten tatsächlichen STKNX U9 Pin23 → JMP2 → RP2040 GPIO1 Empfangstest muss vor dem KNX-TP-Anschluss weiterhin die Hardware inkl. R17-Pads, U11/U9 nach Überhitzung, F1/D1/JMP1-Rückspeisung, GPIO1-Spannungspegel, KNX_TX Reset/BOOTSEL/Brownout und Bus-/USB-Versorgungsführung elektrisch freigegeben werden. **Nur eine separate, abgesicherte KNX-Teststrecke**, nicht der produktive Hausbus.
- Die Blinks am Line Gateway zeigen höchstens Aktivität des vorhandenen KNX-Strangs; sie belegen nicht, dass die eigene Platine KNX_RX empfängt. Beim separaten Test muss eine bekannte Telegrammquelle parallel mit einer unabhängigen KNX-Schnittstelle mitgeschnitten werden.

## 5. Evidenz / Fortsetzung

- USB-Rohereignisse: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX050_HOME_RX_ONLY_FLASH_20261016\usb_rom_app_watch\usb_events.jsonl`
- Wachstatus: `...\usb_rom_app_watch\usb_watch_state.json`; abgeschlossen mit `STOP_REQUESTED` nach ordentlichem Stopfile, fünf Zustandsänderungen, CDC-Detach/ROM-Laufwerk/CDC-Reconnect.
- Frühere Softwaretests: KNX043+KNX048 **62/62 PASS**, Offline-PlatformIO-Build RAM ca. 53,5 %, Flash ca. 3,4 %; kein realer KNX-Busdurchsatztest.
- Projektreferenzen: [KNX048 Pufferänderung](KNX048_RX_BUFFER_20261015.md), [KNX049 sichere Flashplanung](KNX049_HOME_KNX048_DEPLOY_PLAN_20261016.md), [elektrische Gates](KNX043_HOME_KNX_GATE.json).
- **Nächste konkrete Aktion:** USB-only Zustand belassen, Stromversorgung/Schaltplan- und Messgates mit dem Nutzer prüfen; nach qualifizierter Hardwarefreigabe passiven 30-s-USB-RX-Capture auf isolierter KNX-TP-Teststrecke durchführen, `observed`, `dropped`, `high_water` sowie Flankenzeiten gegen unabhängigen Busmitschnitt abgleichen.
- Bestehender einziger offener ASH-Slice `docs/slices/_OPEN_KNX042_MOTOR_LED_BRINGUP.md` wird nicht verändert oder abgeschlossen. Kein Git-Push ohne ausdrückliche Freigabe.
