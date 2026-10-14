# KNX043 – R17 ausgelötet: Vorbereitung für RX-Only-Firmware und KNX-Bench

**Stand: 14.10.2026.** Arbeitsrechner: **LLO Home**. Status: **USB-BOOTSEL und Firmware geprüft; noch nicht geflasht; KNX-TP-Bus gesperrt**.

## 1. Neue Hardware-Rückmeldung

Der Nutzer bestätigt: **R17 wurde physisch ausgelötet.** R17 war im PCB V1.2 der 10-kΩ-Widerstand zwischen 3,3 V und `KNX_TX` des STKNX U9 (Pin 24). Damit ist die als falsch erkannte externe HIGH-Vorspannung nominell entfernt.

Das ist eine **Benutzeraussage, kein Stromlos-Durchgangs- oder Oszilloskop-Nachweis**. Wir dürfen noch nicht behaupten, dass die U9-Pin-24-Verbindung zum 3,3-V-Netz sicher unterbrochen ist, dass R17-Lötpads nicht kurzgeschlossen sind oder dass KNX_TX auf jedem Reset-/BOOTSEL-/Brownout-Pfad LOW bleibt. Die kombinierten Hardware-Gates in [KNX043_HOME_KNX_GATE.json](KNX043_HOME_KNX_GATE.json) bleiben deshalb bis zur realen Messung unverändert `null`.

## 2. Verifizierter Firmware-Stand auf Home

`C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014`

| UF2 | SHA-256 | Status |
| --- | --- | --- |
| `knx043-passive-rx-only-NOT-FLASHED.uf2` | `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f` | **Neuster geeigneter USB-/RX-Only-Diagnosestand**, nicht geflasht |
| `rollback-knx042-led-diagnostic.uf2` | `7e3dc4fe5cb92544558d3d42c71fbb54afb61c3bb29e21d9bb1676fb4961cb6d` | Backup des früher getesteten USB-LED-Programms |
| `KNX029-PRODUCT-TPUART-DO-NOT-FLASH-ON-KNX.uf2` | `6b3e82f30e71d9e6bffd56d5418379e18a998f73fc8befddd68478e18975d805` | Alte Produktfirmware, **nicht** für direkten STKNX KNX_TX sicher |

Die RX-Only-Firmware ist eine separate Diagnose-Firmware: Sie setzt GPIO0 nach Programmstart auf LOW, lässt Motor-GPIOs LOW und kann STKNX-`KNX_RX` an GPIO1 überwachen. Sie implementiert **keine** KNX-Telegrammübertragung, keine neue ETS-Anwendung und keinen vollständigen KNX-PHY. Im RP2040-ROM-BOOTSEL/Reset garantiert sie **keinen** GPIO0-Pegel. Keine Verbindung zum KNX-TP-Bus allein wegen dieser Firmware.

Am 14.10.2026 auf Home live bestätigt: RP2040 USB `VID 2E8A / PID 0003`, Laufwerk `D:` mit Label `RPI-RP2`, `INFO_UF2.TXT` meldet Bootloader v3.0. Das zweite USB-Interface `RP2 Boot` hat Treiberfehler Code 28, weshalb Picotool nicht direkt zugreifen kann; das USB-Massenspeicherlaufwerk funktioniert. **Keine Firmware wurde aufgespielt.**

Der reine Prüfer `tools/knx043_bootsel_firmware_preflight.py` hat auf Home **PASS** geliefert: Gerätedaten, Volume-Label, UF2-Blockheader, Zieladressen und beide SHA-256-Werte stimmen. Der Prüfer führt keinerlei Schreiboperation am Gerät aus.

## 3. Nächste tatsächliche Hardware-Aufgabe (stromlos)

Vor einem KNX-Bustest:

1. **USB abziehen** und alle übrigen Versorgungen und KNX-Drähte abgeklemmt lassen. Nach früherer U11-Erwärmung sichtbare Verfärbungen/Schmelzspuren an **U9 und U11** prüfen; Fotos sind hilfreich.
2. Die ehemaligen R17-Lötpads prüfen: kein Lötbrücke von 3,3 V zu `KNX_TX`; mit Multimeter stromlos Widerstand bzw. Durchgang zwischen den R17-Pads messen. Hier soll nicht mehr der ehemalige 10-kΩ-Pull-up als bestückter R17 vorhanden sein. In-Circuit-Messungen können durch andere Pfade verfälscht werden: Messung dokumentieren, nicht automatisch als bestanden werten.
3. U11 nach dem vorherigen Hitzeereignis als **68 Ω / 2 W-Sollbauteil** visuell und elektrisch kontrollieren; beschädigte Teile erst qualifiziert ersetzen. D1-Drahtbrücke/USB-KNX-Rückspeisung, F1-Nennwert und JMP1-Versorgungswahl ebenfalls klären.
4. KNX_TX-Pegel an U9 Pin 24 muss nach Prüfung der Versorgungsdomänen bei USB-only, Reset/BOOTSEL und Brownout sicher LOW sein. Das ist ein gesonderter zeitaufgelöster Nachweis; der Firmware-Start beweist ihn nicht. Nur mit geeigneter, sicherer Messtechnik durchführen.

**Erst nach dieser Sicht- und Versorgungsprüfung** wird das Aufspielen der RX-Only-Firmware als USB-only-Aktion sinnvoll. Das ist weiterhin **kein Freigabesignal, den KNX-Bus zu verbinden**.

## 4. Vorbereitung des manuellen USB-Only-Flashes

Auf Home im Projektverzeichnis **rein lesend**:

```powershell
& "C:\Users\ll\.platformio\penv\Scripts\python.exe" tools/knx043_bootsel_firmware_preflight.py
```

Bei bestätigtem physisch **abgezogenem KNX-Bus**, keinen Motorantrieben, USB-only und unauffälliger Sicht-/Versorgungsprüfung kann der Bediener den geprüften RX-Only-UF2 über das Windows-BOOTSEL-Laufwerk installieren. Das muss eine **bewusste, separat freigegebene Bedienerhandlung** bleiben. Beispiel für eine manuelle Aktion in einer interaktiven PowerShell nach Prüfung:

```powershell
$uf2 = "C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014\knx043-passive-rx-only-NOT-FLASHED.uf2"
Get-FileHash -LiteralPath $uf2 -Algorithm SHA256
Copy-Item -LiteralPath $uf2 -Destination "D:\"
```

**Die Copy-Item-Zeile ist ein Flashvorgang und wurde vom Agenten nicht ausgeführt.** Sie ist kein automatischer Schritt. Sie ersetzt nicht die elektrische Prüfung von U9/U11/D1/F1. Nach erfolgreichem UF2-Kopieren trennt sich das `RPI-RP2`-Laufwerk normalerweise und die neue Firmware bootet. Der Agent verifiziert dann erneut Geräteidentität, COM-Port (nicht COM7 annehmen), `KNX043 PASSIVE RX READY` und `STATUS ... listen=0`, weiterhin ohne KNX-Leitung.

Die Windows-Ausführung lokaler `.ps1`-Skriptdateien ist auf LLO Home deaktiviert; diese Systemrichtlinie wird **nicht** verändert.

## 5. KNX-IP-Test und ETS6 separat

Am LLO Home wurde das KNX/IP-Interface bereits **netzwerkseitig** identifiziert: **192.168.178.5:3671**; Gerätename beginnt mit `SCN-IP000.03`, eigene physikalische Schnittstellenadresse **1.0.1**, KNXnet/IP-Tunneling angeboten. ETS6 ist installiert. Das erlaubt nach separater Zustimmung die ETS-Schnittstelle zu konfigurieren, ist aber **kein Beweis** für einen isolierten KNX-Prüfbus. Ein existierender Haus-KNX darf nicht zur Erstprüfung eines früher überhitzten U9/U11 verwendet werden.

Für einen späteren physischen KNX-TP-Test sind trotz entfernten R17 weiterhin erforderlich: intakter STKNX-Transceiver, elektrisch geprüfter Sendepin in ALLEN Reset-/Stromzuständen, KNX-Versorgung und USB-/KNX-Rückspeiseschutz, sicherer isolierter KNX-Prüfbus und geeignete Schnittstelle. Erst RX-Empfang beobachten; tatsächliches Senden und ETS-Parametrierung benötigen eine neu zu entwickelnde und validierte STKNX-TX-Schicht.

Referenzen: [KNX043 ausführlicher Prüfplan](KNX043_HOME_KNX_BENCH_READINESS.md), [Live-Geräteprüfung](KNX043_HOME_LIVE_DISCOVERY_20261014.json), [Hardware-Gate](KNX043_HOME_KNX_GATE.json).

**Git:** Der Home-Rechner ist die führende Entwicklungsinstanz. Nach Änderungen verifizieren und per SHA-geprüftem Offline-Bundle fast-forward auf LLO Desktop spiegeln. Kein GitHub-Push ohne explizite Freigabe.
