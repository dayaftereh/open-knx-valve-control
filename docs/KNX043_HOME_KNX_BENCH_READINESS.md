# KNX043 – LLO Home: KNX-TP-Erstprüfung nach Geräteumzug

**Stand: 14.10.2026.**

**Arbeitsrechner: LLO Home.**

**Freigabestatus: VORBEREITET, KNX_BUS_ANSCHLUSS_GESPERRT.**

**Hardware derzeit nicht vor Ort angeschlossen; keine elektrische KNX-Freigabe, kein ETS-Download.**

## 1. Verifizierter Transfer- und Rechnerstand

Am 14.10.2026 live geprüft:

- LLO Desktop: C:\ASH\Workspace\Projects\open-knx-valve-control, main, Git HEAD 9d77dbe, CLEAN.
- LLO Home: C:\_myspace\workspace\open-knx-valve-control, main, **derselbe** Git HEAD 9d77dbe, CLEAN; deshalb kein erneuter Git-Download erforderlich. Die weiteren KNX043-Änderungen werden nur in der Home-Write-Session erstellt, dann lokal committed.
- LLO Home: ETS6.exe unter C:\Program Files (x86)\ETS6\ETS6.exe vorhanden. **ETS-Lizenz, tatsächliche Sitzung und KNX-Verbindung nicht geprüft.**
- Python/PlatformIO unter C:\Users\ll\.platformio\penv\Scripts vorhanden, OpenKNXproducer v3.12.2 unter C:\_myspace\Tools\OpenKNXproducer-3.12.2\tools\Windows\OpenKNXproducer-x64.exe vorhanden.
- Nur Bluetooth-COM3/COM4 festgestellt. **Der RP2040 ist noch nicht auf Home.** Kein KNX/IP- oder KNX/USB-Adapter am Rechner verifiziert.
- SHA256-geprüfte bisherige KNX042-LED-Sequenz-UF2 und KNX042-M1-Rollback-UF2 lagen bereits auf Home.
- Älteres KNX029-Paket (Controller-UF2 und ATtiny3216 HEX) unter C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX029-b016a16-v1 vorhanden, aber der Controller benutzt derzeit eine für direkten STKNX ungeeignete TPUart-UART-Ansteuerung. **Dieses Image nicht an einen KNX-Bus flashen.**

## 2. Warum der KNX-Bus noch NICHT angeschlossen werden darf

Original V1.2 EasyEDA-PCB JSON und STKNX-Datenblatt (DS12399 Rev. 3, Kapitel 5.1) geprüft:

| As-built-Teil | PCB-Verbindung / Eigenschaft | Konsequenz |
| --- | --- | --- |
| RP2040 U18 GPIO0 | U18 Pad 2 = KNX_TX', über JMP3 (Pad 2–3) nach KNX_TX / U9 Pin 24 | Sendepin: LOW in Busruhe, HIGH bedeutet aktive KNX-Stromsenke |
| R17 | 10 kΩ von 3.3V nach KNX_TX | Externer Pull-up ist **falsch für STKNX**, kann Bus dauerhaft belasten |
| U9 STKNX | KNX_TX Pin 24, KNX_RX Pin 23, KNX_A Pin 11, R68 Pin 3 | Transceiver nach früherem Hitzeereignis potenziell beschädigt |
| U11 | 68 Ω / 2 W zwischen R68 und KNX_A (Soll) | Bereits real heiß geworden; echter Widerstand/Schaden unklar |
| RP2040 U18 GPIO1 | U18 Pad 3 = KNX_RX', via JMP2 Pad 1–2 zu KNX_RX / U9 Pin 23 | RX LOW in Ruhe; bei aktivem Busimpuls für ~35 µs HIGH |
| JMP1 | KNX_VCC ↔ R9_2/Quellenwahl | Öffnung trennt Versorgungszweig, **nicht TX** |
| D1 (as-built Draht) | Wegfall des ursprünglichen Sperrelements | USB/KNX-Quellen dürfen ohne Rückspeisemessung nicht gemeinsam betrieben werden |
| F1 | Fotoaufschrift vermutlich T2.5A vs. vorgesehen 630 mA | Schutzwert und Strompfad erneut prüfen |
| TB6612 STBY | Vier Treiber mit STBY hart HIGH | Keine hardwareseitige Motor-Ausgangssperre; alle Motoren abgesteckt lassen |

Nach vorherigem gleichzeitigen KNX-/5-V-Anschluss wurde U11 heiß und KNX brach offenbar zusammen. **Kein zweiter Versuch, bis Ursache und beschädigte Bauteile geprüft sind.** R17 darf stromlos ausgelötet werden, aber alte R17-Pads verbinden TX mit 3.3V, daher nicht versehentlich kurzschließen oder dort einen GND-Pulldown direkt bestücken. R17-Entfernung allein beweist keinen TX-LOW-Pegel bei ROM/BOOTSEL, Reset, UART-Idle-HIGH oder Brownout. Bestehende Controller-Firmware setzt normale TPUart::ArduinoSerial(Serial1) auf GPIO0 ein, **nicht** die direkten 35-µs-STKNX-TX-Pulse.

Herstellerreferenz: https://www.st.com/resource/en/datasheet/stknx.pdf

## 3. Test-Gates nach Ankunft der Platine

**Gate A – stromlos / visuell.** USB, KNX, externe 5 V, UPDI, alle Motoren komplett trennen. Vorhandenen Stand und U9/U11, R17, F1, D1, Q1, JMP1/2/3 sowie Lötstellen nach dem Transport fotografieren. R17-Status und U11-Wert/Schaden mit geeigneten Messmitteln/Bestückungsabgleich erfassen. Verwechslungs-/Kurzschlussgefahr mit benachbarten Pads verhindern. Kein Anschluss an Haus-KNX.

**Gate B – stromlos / Kontinuität.** R17-Pull-up tatsächlich entfernt und beide Pads nicht verbunden? GPIO0/JMP3/U9 KNX_TX und GPIO1/JMP2/U9 KNX_RX gegen V1.2-Netzliste prüfen. USB_VCC, 5V_, 5V, KNX_VCC, 3V3/GND gegen Kurzschluss/Rückspeisung prüfen. U11 nach Hitzebelastung separat beurteilen. STKNX U9 VCCCORE (Pin 20) bzw. KNX_RX-HIGH-Pegel auf sichere 3,3-V-Kompatibilitaet mit RP2040 pruefen, keine 5-V-RX-Pegel am GPIO1 zulassen. F1 und D1-Bypass fachlich freigeben.

**Gate C – nur USB, busfrei / softwareseitig.** Nur nach Gate A+B: USB-C angeschlossen, RP2040/COM und T0/T1-USB-Diagnose/3,3-V-Versorgung verifizieren. TX an U9 Pin24 muss im Ruhestand LOW sein, nicht nur nach erfolgreichem Sketch-Start, sondern auch **während Reset/BOOTSEL/Neustart/Brownout** (geeignete zeitaufgelöste Messung). Prüfen, dass U9/U11 nicht heiß werden; keine Motorspulen anschließen. **Spannungsmessung mit Multimeter allein beweist keine 35-µs-Impulse oder Glitches.**

**Gate D – Spannungsquellen / separate KNX-TP-Testumgebung.** Isoliertes KNX-TP-Testnetz mit geeigneter KNX-Busversorgung und überprüfter KNX/IP- oder KNX/USB-Schnittstelle. Niemals den produktiven Haus-Bus für den ersten Fehler-Retest verwenden. Auf der V1.2 Versorgungspfad Q1/JMP1/F1/D1 einschließlich Rückspeisung zuerst elektrisch qualifizieren, da USB für Protokolllogging und KNX-TP gleichzeitig nötig sein könnten. KNX erst nach dokumentierter fachlicher Freigabe anschließen. **Kein KNX plus USB nur aufgrund erfolgreichen USB-Tests.**

**Gate E – erste empfangsseitige Beobachtung.** Nach ALLEN vorherigen Hardwaregates und separater Freigabe darf ein unabhängiges STKNX-RX-Only-Sketch genutzt werden. GPIO0 wird nach Sketch-Start LOW gehalten, niemals HIGH geschaltet; GPIO1 wird als reiner Eingang auf RX-Flanken überwacht. Diese Datei wurde **nur offline kompiliert**, noch nicht geflasht. KNX-Impulse über USB protokollieren; noch keine Telegramme senden. Erst dann Empfängerpegel, Impulszeiten und Verluste beurteilen.

**Gate F – echter KNX-/ETS-Test (SPÄTER).** Ein STKNX-kompatibler physikalischer Transmitter mit 35-µs-HIGH/69-µs-LOW-Bitmuster samt Reset-/Brownout-Sicherheit ist noch NICHT implementiert/freigegeben. Die produktive TPUart-Software ist für diesen PHY nicht verwendbar. Erst nach einem gesonderten Offline-PHY- und Hardware-Sicherheitsnachweis können KNX-Telegramme/ETS-Individualadresse/KO25–35 sinnvoll geprüft werden. Ohne KNX/IP- oder USB-Interface ist ETS6 allein nicht ausreichend.

Messdaten niemals erfinden; alle Felder bleiben bis zur realen Messung offen. Datensatz: [KNX043 Hardware-Gate](KNX043_HOME_KNX_GATE.json). Automatischer Prüfer erteilt auch bei vollständig ausgefüllter Datei **keine** Freigabe zum Einschalten des KNX-Busses.

## 4. Bereits vorbereitet: RX-Only-Sketch und Offline-Infrastruktur auf Home

Neue Dateien (keine Motoraktivierung, keine KNX-Sende-Firmware):

- [RX-Only-Sketch](../tools/knx043_passive_rx/src/main.cpp) – GPIO0 fest LOW ab Setup, GPIO1-CHANGE-Interrupt mit Mikrosekunden-Zeitstempel, Ringbuffer und Dropped-Count, Aufnahme maximal 120 Sekunden, nur nach explizitem USB ARM LISTEN_ONLY und START LISTEN.
- [PlatformIO-Konfiguration](../tools/knx043_passive_rx/platformio.ini) – pinnt Arduino-Pico 5.5.0, Upload bewusst deaktiviert.
- [USB RX-Capture-Client](../tools/knx043_rx_capture.py) – probe/status/stop/capture, START nur bei ausgefülltem Gate plus expliziter manueller Prüffreigabe; STATUS ist read-only.
- [Home-Inventur ohne Gerätekontakt](../tools/knx043_home_knx_preflight.py) – ETS/PIO/OpenKNXproducer/Backups und fehlende Gate-Messungen prüfen.
- [Tests Preflight](../tools/test_knx043_home_knx_preflight.py) und [Tests RX-Only](../tools/test_knx043_rx_capture.py) – 16 Offline-Regressionstests PASS.

**LLO Home PlatformIO-Build:** PASS (RX-Only Sketch). UF2-Backup und Manifest im Verzeichnis:

C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014

| Datei | SHA256 | Bedeutung |
| --- | --- | --- |
| knx043-passive-rx-only-NOT-FLASHED.uf2 | 8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f | Empfangsdiagnose, **NOCH NICHT GEFLASHT** |
| rollback-knx042-led-diagnostic.uf2 | 7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d | Bewährter KNX042-USB-Diagnose-Rollback |
| KNX029-PRODUCT-TPUART-DO-NOT-FLASH-ON-KNX.uf2 | 6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805 | Historische Produktbuild-Referenz, **nicht auf KNX verwenden** |

(Beim UF2-Ergebnis gilt nur die Software-/Dateiintegrität, nicht die Sicherheit zum Flashen.)

**Read-only Vorprüfung**, auf Home im Projektverzeichnis:

    & "C:\Users\ll\.platformio\penv\Scripts\python.exe" tools/knx043_home_knx_preflight.py

Nach Anstecken des RP2040 mit USB an Home lautet der COM-Port möglicherweise anders als auf Desktop. Deshalb zuerst per Geräte-Manager/Host erkennen, nicht COM7 annehmen. KNX043-Host kann, sofern das RX-Only-Bild wirklich geladen wurde, erst nach Gate-Freigabe verwendet werden:

    & "C:\Users\ll\.platformio\penv\Scripts\python.exe" tools/knx043_rx_capture.py probe --port COMx --expect-serial E464401787522D33

Das Capture-Programm wird vor erfüllten Gates und separater Hardwarefreigabe **nicht** gestartet. Es bietet keine KNX-Telegramm-Decodierung und ersetzt weder ETS6 noch die physische Messung am Transceiver.

## 5. Nächste Eingaben vom Nutzer

Bitte nach Ankunft bei LLO Home:

1. Platine stromlos ablegen und mitteilen, ob R17 tatsächlich entfernt wurde; Foto/Status von U9 und U11 (vorher überhitzt).
2. Sagen, ob ein eigener KNX-TP-Testbus samt KNX-Stromversorgung und KNX/IP- oder KNX/USB-Interface verfügbar ist.
3. Gegebenenfalls Messwerte aus Gate A/B liefern. Diese gemeinsam auswerten, bevor irgendwelche 5-V-/USB-/KNX-Versorgungen verbunden werden.

**Keine automatische Wiederaufnahme oder Live-KNX-Test ohne diese Prüfschritte. Kein GitHub-Push ohne ausdrückliche Freigabe.**

## 6. Hinweis zu Motoren

M1 OPEN/CLOSE und M2 OPEN wurden mit LEDs tatsächlich beobachtet, was den GPIO-/Anzeigenpfad für diese Kanäle positiv bestätigt. M3–M8 sind **nicht** unabhängig elektrisch gemessen und reale Motorantriebe/Endlagen/INA219 sind weiter ungeprüft. Die Motoren haben derzeit keine Priorität und bleiben physisch abgeklemmt.

## Live-Nachtrag 14.10.2026 – BOOTSEL und KNX/IP entdeckt

Der RP2040 wird auf LLO Home als USB 2E8A:0003 im **ROM-BOOTSEL** erkannt. Das Laufwerk D: hat Label RPI-RP2 und INFO_UF2.TXT meldet UF2 Bootloader v3.0. Das USB-Massenspeicherinterface funktioniert. Das zusätzliche Interface RP2 Boot (MI_01) zeigt jedoch Windows Problemcode **28: Treiber fehlt**; deshalb meldet Picotool zwar das Geraet, kann es aber nicht oeffnen. Keine UF2 kopiert, keine Firmware geflasht. Die USB-ROM-Seriennummer E0C9125B0D9B weicht von der frueheren Anwendungsseriennummer E464401787522D33 ab, was unterschiedliche Identitaetsquellen sein koennen.

KNXnet/IP im WLAN 192.168.178.21/24: eine Multicast-Suche an 224.0.23.12:3671 lieferte SearchResponse und eine direkte DescriptionRequest lieferte DescriptionResponse vom IP-Interface **192.168.178.5:3671**. Das 30-Byte-Namensfeld beginnt mit SCN-IP000.03 IP Interface mit. Die eigene physikalische KNX-Adresse des **IP-Interfaces** ist **1.0.1** (nicht die Adresse des Ventilcontrollers); DIB-Servicefamilie 4 Version 2 meldet KNXnet/IP-Tunneling-Unterstuetzung. ETS6.exe ist installiert, zum Untersuchungszeitpunkt aber nicht gestartet. Keine ETS6-Sitzung, kein Tunneling-Aufbau und keine KNX-TP-Telegramme.

Dieses IP-Interface ist **nicht** als isolierter KNX-Testbus qualifiziert. R17 am STKNX-KNX_TX, das fruehere Hitzeereignis an U11 und der Zustand von U9 sowie D1/F1/JMP1-Rueckspeisung bleiben kritisch. Besonders im BOOTSEL/Reset ist ein inaktives LOW auf GPIO0 nicht durch Firmware garantiert. **Keine KNX-Busleitung an der Platine anschliessen**, bis die stromlosen und spannungsgefuehrten Gates separat geklaert sind.

[Maschinenlesbarer Live-Bericht](KNX043_HOME_LIVE_DISCOVERY_20261014.json).

**Naechster Schritt:** Platine fuer R17/U9/U11/F1/D1/JMP1-3-Kontrolle erst stromlos machen und Messungen dokumentieren. Fuer die ETS6-Konfiguration kann spaeter das gefundene IP-Interface 192.168.178.5 als KNX/IP-Verbindung ausgewaehlt werden, ohne den nicht freigegebenen Ventilcontroller an den Bus zu haengen.

## Nachtrag R17-Entfernung und RX-UF2-Pruefung (14.10.2026)

Der Nutzer bestaetigt, dass er **R17 physisch ausgelötet** hat. Dies wurde dokumentiert als **Nutzerbericht, kein gemessener Widerstand oder Nachweis fuer TX LOW im Reset/BOOTSEL**. Das kombinierte KNX-TX-Hardware-Gate bleibt unverifiziert, ebenso U11 nach vorheriger Ueberhitzung, U9, D1-Bypass, F1 und die Spannungs-/Rueckspeisungspfade.

Der RP2040 wird auf Home weiterhin im USB-ROM-BOOTSEL mit Laufwerk D: RPI-RP2 erkannt. Die passende, neueste isolierte KNX043-RX-only-UF2 und die KNX042-Rollback-UF2 haben auf Home und im automatisierten READ-ONLY-Preflight korrekte SHA256-Werte und UF2-Adressen (14.10.2026). **Kein Flash erfolgt.** Die weiteren Schritte inklusive sicherer manueller UF2-Option und notwendigen stromlosen Messungen stehen unter [R17-Rework und RX-Only-Flashplan](KNX043_R17_REWORK_TO_RX_FLASH.md). Windows blockiert lokale .ps1-Dateien per Execution Policy, die nicht veraendert wird; der Pruefer ist Python und ist read-only.

## KNX043 USB-only Flash successfully completed on Home (2026-10-14)

The user reports R17 desoldered, U11 resoldered and measured 68 ohms, and U9 is the expected chip. These are user-reported observations, not independent board-voltage or heat-damage clearance.

The isolated KNX043 passive receive-only image (pre-copy SHA256 8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f) was written through the verified RP2040 RPI-RP2 D: ROM BOOTSEL USB-mass-storage volume. USB copy process EXIT 0. The board subsequently enumerated on LLO Home as COM8 (VIDPID 2E8A:000A, serial E464401787522D33). The KNX043-specific READY banner was recognized and read-only USB STATUS returned exactly: KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0. The program is running. Firmware contents were not directly read back from flash.

**KNX BUS STILL BLOCKED:** No physical proof of U9/U11 electrical/thermal health after the previous overheating, KNX_TX LOW under ROM/reset/brownout, R17-pad continuity, D1/F1/JMP1 rail power/backfeed, or independent testbus isolation. This firmware only captures receive edges, does not implement ETS KNX telegram transmission. Do NOT connect the board to KNX on firmware success alone.

[Live USB flash report](KNX043_RX_ONLY_FLASH_HOME_20261014.json).
