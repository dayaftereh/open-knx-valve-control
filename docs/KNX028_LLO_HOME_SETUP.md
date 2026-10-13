# KNX028 - LLO Home als Offline-Entwicklungsrechner

**13.10.2026.** Geraete werden erst angeschlossen, wenn die OpenKNXValveControl V1.2 Platine fertig aufgebaut und die Hardware-Freigaben KNX002-006 geklaert sind. Dieses Dokument beschreibt nur PC-Initialisierung, keine elektrische Funktionsabnahme.

## Root, Session, Git

- Primaerer Rechner: **LLO Home Agent 0.7.9**, Windows. `C:\_myspace\workspace\open-knx-valve-control`.
- Git baseline zu KNX028: `14795c6c7af6808bcff210d3a98bce814bac7461`, `main` synchron mit GitHub; vor Arbeit clean.
- Beim SYSTEM-Agent gehoert das Projekt `DESKTOP-FSU5FR0\ll`. Git kann deshalb `dubious ownership` melden. Nur gezielt `git -c safe.directory=C:/_myspace/workspace/open-knx-valve-control ...` nutzen, keine globale System-Ausnahme.
- Erst Agent-Session/Git-`status`/`docs/slices/_OPEN_*.md` pruefen, maximal ein Write-Slice. Desktop nicht parallel fuer dieselben Dateien beschreiben.

## Bereits lokal gefunden

| Werkzeug | Pfad | Befund |
| --- | --- | --- |
| Python 3.11.7 | `C:\Users\ll\.platformio\penv\Scripts\python.exe` | Python vorhanden |
| PlatformIO Core 6.1.18 | `C:\Users\ll\.platformio\penv\Scripts\pio.exe` | PIO vorhanden |
| PIO Benutzerdaten | `C:\Users\ll\.platformio` | Verwenden mit `PLATFORMIO_CORE_DIR` fuer SYSTEM Jobs |
| Git | `C:\_myspace\Tools\Git\cmd\git.exe` | Vorhanden; Eigentuemervertrauen nur pro Kommando |
| Raspberry Pi Platform | `git+https://github.com/maxgerhardt/platform-raspberrypi` | Erfordert erstmalige Installation, Status jeweils live pruefen |
| Arduino-Pico | Firmware-Pin `5.5.0` | PlatformIO laedt das gepinnte Release |
| OpenKNXproducer | GitHub-Release `v3.12.2` | Nicht vorinstalliert; Archiv `OpenKNXproducer-3.12.2.zip` ist ca. 165 MB |
| Native C++-Hostcompiler | unbekannt | Kein `g++.exe` im initialen Toolverzeichnis nachgewiesen |

**Keine globale Python-/PIO-Installation erzwungen.** Ggf. den Python-PIO-Pfad als `PYTHON_EXECUTABLE` in lokalen Befehlen referenzieren und `PIO_EXECUTABLE`/ `OPENKNXPRODUCER_EXECUTABLE` fuer den KNX027-CLI setzen.

## Sofort nutzbare Offlinechecks

In Powershell, vom Repository-Root aus:

```powershell
$env:PLATFORMIO_CORE_DIR = 'C:\Users\ll\.platformio'
$python = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'
$pio = 'C:\Users\ll\.platformio\penv\Scripts\pio.exe'
& $python tools/test_usb_flash_controller.py
& $python tools/audit_ash_workflow.py
& $python tools/audit_design.py
& $pio --version
```

**Vorliegende Ergebnisse am 13.10.2026:** KNX027 Mock-Upload-Tests 8/8 PASS, ASH-Audit 30/30 PASS mit 472 Links, Design-Static-Audit 0 Invariantfehler (bekannte Hardware-Warnungen bleiben). Diese Tests nutzen keinen angeschlossenen Controller.

## Isolation des Buildvorgangs

`src/controller/controller.ini` legt `upload_protocol=picotool` fest, aber ein `pio run -e controller` ist **Build**, kein `-t upload`. Der Produktgenerator schreibt beim normalen Build in `include/knxprod.hpp`; deswegen nur die isolierten Builder in `tools/usb_flash_controller.py build` oder `tools/build_controller_isolated.py` nutzen. KNX027 erwartet OpenKNXproducer.exe via `OPENKNXPRODUCER_EXECUTABLE` bzw. PATH und PlatformIO via `PIO_EXECUTABLE`.

Der Controller-Build braucht die exakte gepinnte Platform `https://github.com/maxgerhardt/platform-raspberrypi`, Framework Arduino-Pico `5.5.0`, OpenKNX-Bibliotheken und einen verfuegbaren Producer. ATtiny verwendet `atmelmegaavr`, `ATtiny3216`, MilesBurton DallasTemperature/SpenceKonde OneWire, ebenfalls nur Builds. Bei noch fehlendem Producer/Compiler gilt **BLOCKED**, nicht PASS.

### Isolierte Build-Beispielbefehle (erst nach Toolinstallation)

```powershell
$env:PLATFORMIO_CORE_DIR = 'C:\Users\ll\.platformio'
$env:PIO_EXECUTABLE = 'C:\Users\ll\.platformio\penv\Scripts\pio.exe'
$env:OPENKNXPRODUCER_EXECUTABLE = 'C:\_myspace\Tools\OpenKNXproducer-3.12.2\OpenKNXproducer.exe' # realen exe-Pfad pruefen
& 'C:\Users\ll\.platformio\penv\Scripts\python.exe' tools/usb_flash_controller.py build
```

## Strikt verboten ohne spaetere Hardwarefreigabe

- Kein `-t upload`, `usb_flash_controller.py upload --execute`, USB CDC 1200 Baud Reset, ROM BOOTSEL oder UPDI, kein SPI/UART/KNX-Buszugriff.
- Kein Motor/INA219-Endlagenversuch, keine scheinbaren Sicherheitstests mit softwareseitigen AllOff ACKs.
- RP2040-UART und ATtiny-UART sind eigene Leitungen; T0..8 Vor-/Ruecklauf ist niemals externer Raum-Isttemperatursensor.
- PCB V1.2 hat Hardware-Blocker: TB6612 STBY high, Spannungs-/Rueckspeisepfade, U25-Bauteilidentitaet, R29/INA219, reale Motor-Stromkurven nicht abgenommen.
- Kein Git-Push ohne separate Absprache; Home-`main`-Arbeit nur nach ASH Checkpoint und auf diesem Host dokumentieren.

## Noch zu verifizieren

Den tatsaechlichen Installations-/Buildstatus und fehlende Paketquellen in der Session festhalten. Ein erfolgreich kompilierender Host ersetzt niemals ETS6-, USB-, KNX-, Versorgungs- oder Motorpruefungen am fertigen Aufbau.

## Live-Update der Home-Initialisierung

- **RP2040-Toolchain installiert:** PlatformIO hat `raspberrypi@1.20.0+sha.5d4561a`, `framework-arduinopico@1.50500.0` (Projektpin 5.5.0), ARM GCC, picotool und pioasm sowie OpenKNX knx 2.4.0 / TPUart 1.1.0 geladen.
- **ATtiny3216-Offlinebuild PASS** aus einem temporaren Kopie-Workspace am 13.10.2026. OneWire und DallasTemperature inklusive der SpenceKonde-Source vorhanden; kein Upload.
- **OpenKNXproducer v3.12.2**: Das offizielle OpenKNX ZIP `C:\_myspace\Tools\OpenKNXproducer-3.12.2.zip` hat 164848021 Bytes und enthaelt **nicht** die Datei `OpenKNXproducer.exe`, sondern das lauffaehige Programm `C:\_myspace\Tools\OpenKNXproducer-3.12.2\tools\Windows\OpenKNXproducer-x64.exe`. `--help` meldet OpenKNXproducer 3.12.2; der Producer muss nicht durch ein globales Installationsskript nach SYSTEMPROFILE kopiert werden. Die zuvor als Beispiel bezeichnete `OPENKNXPRODUCER_EXECUTABLE` muss auf diesen realen x64-Pfad zeigen. Fuer den SCons Prebuild muss `OPENKNX_PRODUCER` ebenfalls diesen Pfad erhalten.
- **Host-C++-Regression KNX025:** nicht gestartet, da kein nativer `g++.exe` verfuegbar; keine faelschliche PASS-Meldung. ARM- und AVR-Crosscompiler ersetzen den Host-g++ nicht.
- **Git:** User-Kontext SYSTEM gegenueber Besitzer `ll` weiterhin nur `-c safe.directory=C:/_myspace/workspace/open-knx-valve-control` pro Git-Aufruf, falls erforderlich.
- `tools/home_offline_check.ps1` wurde in dieser Home-Initialisierung 0 Exitcode geprueft (nur Simulation/Audits, keine Schnittstellenaktion).

## KNX028 – Offenes Controller-Buildproblem (verifiziert 13.10.2026)

Beim ersten **echten isolierten RP2040-Build auf LLO Home** erzeugte OpenKNXproducer 3.12.2 erfolgreich das temporare `knxprod.hpp` mit 35 KO sowie den temporaren knxprod-Kandidaten, ohne die Projektdateien zu veraendern. Die gepinnte `framework-arduinopico 5.5.0` wurde kompiliert, scheiterte aber nach ca. 170 s **in Fremdcode**, nicht in OpenKNX-Firmware:
```text
C:\Users\ll\.platformio\packages\framework-arduinopico\cores\rp2040\malloc-lock.cpp:122:19:
error: '__getreent' was not declared in this scope; did you mean '_reent'?
*** [.pio\build\controller\FrameworkArduino\malloc-lock.cpp.o] Error 1
controller FAILED (00:02:49.792)
```
Erfasst im ASH Job `job-000035` der Home-Session `ses-20261013T091101-f5813049ea1d`. **Kein Controller-Firmware-Build PASS, kein UF2-Artefakt als Erfolg gemeldet, kein Upload.** Die Ursache (Version/Kompatibilitaet zwischen vom PlatformIO-Platform-Fork aktuell geladenem ARM-Toolchain-Quickrelease und Arduino-Pico 5.5.0) ist zu untersuchen; Fremdtoolchain nicht blind modifizieren. Desktop hat vor der Migration mit einer anderen Toolchain ein isoliertes Build bestanden. Naechster Schritt: Paketversionen und `-D`-Compileflags Desktop vs Home vergleichen und danach nur kontrolliert kompatible Toolchain-Version einsetzen oder gezielte Anpassung dokumentieren. Keine Aenderung der Hardware-Firmware-Safety-Fence.

**Gesicherte Erfolge:** KNX027-Mocktests 8/8 PASS, ASH 30/30 PASS, statischer Design-Audit 0 Invariantfehler, ATtiny3216-Offlinebuild PASS, RP2040-Dependencies und Producer vorhanden; nativer g++-Hosttest weiterhin BLOCKED.

### Konkreter Unterschied gegen letzten erfolgreichen Desktop-Build

Live am 13.10.2026 geprueft: Bei gleichem `framework-arduinopico` **1.50500.0 (Arduino-Pico 5.5.0)** hat der frueher erfolgreiche LLO Desktop die ARM-Paketversion `toolchain-rp2040-earlephilhower 5.140200.250530`, Home hingegen `5.160100.260719`. Das ist eine nachgewiesene **Toolchain-Differenz**, die den `__getreent`-Fehler erklaeren koennte, aber noch kein kausaler Beweis. Keine Fremdbibliothek modifizieren. Erst eine kontrollierte isolierte Regression mit explizit gepinnter aelterer, auf Desktop bewaehrter Compiler-Version pruefen und danach PIO-Paketversion projektweit dokumentieren; keine System-/USB-/Motoraktion.

## KNX028 – Buildblocker geloest: reproduzierbarer RP2040-Stand

Am 13.10.2026 wurde der vorherige `__getreent`-Fehler durch eine **gezielte Projekt-Paketbindung** behoben, ohne Quellcode oder fremde Framework-Dateien zu patchen:

- Alter, auf Desktop bewaehrter `toolchain-rp2040-earlephilhower`: **5.140200.250530 (ARM GCC 14.3.0)** statt Home-Fehlschlag mit **5.160100.260719 (ARM GCC 16.1.0)**.
- In `src/controller/controller.ini` ist die offizielle Producer-unabhaengige Compiler-Release-URL `pico-quick-toolchain/releases/download/4.1.0/x86_64-w64-mingw32.arm-none-eabi-1aec55e.250530.zip` explizit unter `platform_packages` fixiert.
- Die maxgerhardt Raspberry-Pi-PlatformIO-Plattform ist zusaetzlich auf den am Home erfolgreich getesteten Git-Commit `5d4561a05e3b212660ac6fdd3fbfb328d1988aa1` fixiert.
- **Kontrollbuild 1 PASS** vor Plattform-SHA-Pin und **Kontrollbuild 2 PASS** nach beiden Pins. Der isolierte `usb_flash_controller.py build` erzeugte `firmware.elf` und `firmware.uf2`, **ohne USB/KNX oder Flash**.
- Beide Builds produzierten dieselbe Firmware-UF2-SHA256 `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805`; Controller RAM 54.108/262.144 B (20,6 %), Flash 198.340/1.048.576 B (18,9 %). Das in der Config eingetragene 16-MiB-Flash-Layout ist **noch nicht am realen Chip geprueft**.
- Die bisherige Knx027-Scope-Pruefung ist explizit um die **zwei erlaubten, genau verifizierten KNX028-Toolchain-Pins** erweitert, ohne unkontrollierte Firmware-/ETS-/Upload-Aenderungen zu tolerieren; `tools/audit_knx027_usb_flash_scope.py` wieder PASS.
- Die Geraete-/USB-/KNX-/Motor-Safety-Gates bleiben unveraendert blockiert. Die Hersteller-Warnungen zu ETS Channel-Number-Prefix und fehlendem XSD-Schema beim Producer sind dokumentierte Software-Warnungen; kein ETS6-Importnachweis.

### Native C++-Tests

Ein separater, opt-in portabler Windows-g++ wird aus dem originalen WinLibs-Release **16.2.0posix-14.0.0-ucrt-r2** mit offiziellem SHA256-Sidecar (keine globalen PATH/Registry-Aenderungen) mittels `tools/install_home_host_compiler.ps1` nach `C:\_myspace\Tools\winlibs-gcc-16.2.0-ucrt\mingw64\bin\g++.exe` installiert. `tools/home_offline_check.ps1 -Native` kann danach alle elf native-Test-Skriptgruppen ausfuehren. `-ControllerBuild` baut zusaetzlich nur einen temporaeren RP2040-Snapshot (kein Upload).

### Verifizierte nativen Hosttests (Home, 13.10.2026)

Das WinLibs-7z-Archiv (109762824 Bytes) wurde gegen das offizielle Release-SHA256-Sidecar verifiziert: `53fb6773fbdf87cdf22b69a6b2a07ee33d3ada413b42d83044bc7cc6481400d2`. `g++.exe --version` ergab **16.2.0 (MinGW-w64 x86_64 UCRT)**. Keine globale Installation oder PATH-Aenderung; die Tests erhalten den Pfad per `CXX` im lokalen PowerShell-Prozess.

`tools/home_offline_check.ps1 -Native` **exit 0 / PASS**: 11/11 native Testskriptgruppen mit erfolgreich gebauten und ausgefuehrten Host-C++-Binaries fuer KNX008, KNX013, KNX014, KNX015, KNX019, KNX020, KNX021, KNX023, KNX024, KNX025, KNX026 einschliesslich Arduino-Hardlock-Mocks. Ebenfalls PASS: KNX027 mock USB-Uploadtests 8/8, KNX026/KNX027 frozen-firmware-Scope, statisches Design-Audit und ASH workflow. `audit_knx022_hw_preflight.py` meldet 35/35 **statische** Invarianten PASS, aber weiterhin **10 reale Hardware-Blocker** mit `BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR`.

Der eingeschlossene KNX027 Scope-Audit ist fuer die genau zwei bekannten `controller.ini`-Pins erweitert: fremde Firmware-/ETS-/PCB-Aenderungen und geaenderte USB-Upload-Freigaben bleiben weiterhin verboten. Native Simulation, Software-Queue-ACK und `ARDUINO` Compile-Hardlock sind kein Nachweis einer elektrisch abgesicherten H-Bruecke.

**Letzter End-to-End-Check:** `tools/home_offline_check.ps1 -ControllerBuild` lief als LLO-Home-ASH-Job `job-000072` **exit 0**, wieder mit derselben UF2-SHA256 `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805`. Damit ist nicht nur der isolierte Python-Builder, sondern auch das reproduzierbare PowerShell-Runbook praktisch geprueft. Weder USB-Reset noch Upload.
