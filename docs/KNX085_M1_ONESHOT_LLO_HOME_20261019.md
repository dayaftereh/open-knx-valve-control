# NACHTRAG KNX086 / 19.10.2026

**Aktueller Live-Stand:** Die KNX085-Firmware wurde am 19.10.2026 auf der realen V1.2-Platine MIT KNX und UPDI erfolgreich geflasht. Die bisherige pauschale Flash-Sperre wegen der frueheren U11-Erwaermung war fuer diesen bereits bei KNX076/081/084 geprueften Aufbau falsch; urspruenglich ging es um den entfernten R17-Pull-up. KNX085 antwortet auf COM8 mit TX LOW, Motoren LOW und aktiven Temperatur- und KNX-RX-Daten. **M1 fuhr noch nicht**, da INA219 im motorischen Stillstand eine nicht plausible Roh-Shuntspannung (~92.6mV) liefert; der R29-Wert ist unbekannt. Die nachfolgenden KNX085-Aussagen sind historische Zwischenstaende. Aktuelle Fakten: [KNX086-Live-Bericht](KNX086_R17_LIVE_FLASH_INA219_20261019.md).

---

# KNX085 – Ausführbares M1-One-Shot-Skript für LLO Home

Stand 19.10.2026. User request: Der Nutzer möchte die KNX085-Firmware
vorbereitet bekommen, um den **ersten** M1-Test selbst per PowerShell
auszuführen. Dieses Paket wurde OFFLINE gebaut und getestet, **nicht**
auf die reale Platine geflasht.

## 1. Das fertige Paket

- Windows-Startskript:
  C:\_myspace\workspace\open-knx-valve-control\tools\knx085_motor_diag\Start-KNX085-M1.ps1
- Python-Orchestrator:
  tools/knx085_motor_diag/knx085_one_shot.py
- Motor-/INA219-USB-Host:
  tools/knx085_motor_diag/knx085_bench_host.py
- Firmware, isolierter Build:
  C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX085-M1-20261019\knx085_bench_unlocked.uf2
- UF2 SHA-256:
  86cbf6942fd12eba07402c52842ba7543cabd2c2a557a329607c954388a54750
- Firmwaregröße: 242688 Byte.
- Manifest liegt neben dem UF2; niemals unkontrolliert andere Firmware hochladen.

## 2. Sichere Anzeige ohne Hardwarebewegung (funktioniert jetzt)

In PowerShell:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\_myspace\workspace\open-knx-valve-control\tools\knx085_motor_diag\Start-KNX085-M1.ps1"

OHNE -Run zeigt das Skript **nur den Plan** und berührt weder
COM/USB noch Motor/Flash. Dieser Aufruf wurde live auf LLO Home
mit Exit 0 erfolgreich getestet.

## 3. M1-Ausführung NUR NACH physischer Trennung von KNX und UPDI

Bedingungen auf dem Prüfstand:
- KNX-TP-Bus der Platine PHYSISCH abgezogen (die übrige Hauslinie bleibt
  in Betrieb). Ein bloßes Bus-Software-Aus reicht nicht.
- CH340/UPDI-Programmer an CN1 PHYSISCH abgezogen und kein COM5-CH340
  mehr vorhanden. Noch angeschlossener CN1 kann Strom zurückspeisen.
- Einzige Elektronikversorgung ist USB-C am RP2040.
- Vor Ort existiert eine Möglichkeit zur direkten Versorgungstrennung.
- Echte Testantriebe an M1 und M2 dürfen angeschlossen bleiben,
  wasserlose Testventile.

ERST WENN DIESE TATSACHEN ZUTREFFEN, den folgenden Befehl benutzen:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\_myspace\workspace\open-knx-valve-control\tools\knx085_motor_diag\Start-KNX085-M1.ps1" -Run -ConfirmKnxPhysicallyDisconnected -ConfirmUpdiPhysicallyDisconnected -ConfirmUsbOnlyPower -ConfirmPhysicalPowerCutAvailable -Direction F -DurationMs 150

WICHTIG: Die vier Confirm-Schalter sind tatsächliche
Hardware-Bestätigungen, KEIN akzeptierter Software-Sicherheits-Bypass.
Nicht angeben, solange KNX/UPDI angeschlossen sind. Der Befehl
bricht andernfalls vorsorglich ab.

## 4. Ablauf beim wirklichen, freigegebenen Start

1. Verifiziert exakt ein RP2040 USB VID/PID 2E8A:000A, Seriennummer
   E464401787522D33. Prüft CH340/UPDI VID:PID 1A86:7523 ABSENT.
2. Prüft die feste SHA-256 und Größe des KNX085-UF2-Images.
3. Liest die aktuelle KNX084-USB-Statusmeldung, vier gültige Sensoren
   und KNX-RX-Zähler. Bei einem einzigen neuen RX-Ereignis zwischen
   den Prüfungen wird abgebrochen. Unveränderte Zähler sind aber
   KEIN Ersatz für die physische Bus-Trennung!
4. Löst NUR dann den RP2040-USB-1200-Baud-BOOTSEL-Neustart aus.
   Der gefährdete KNX-TX-Pegel während ROM/Reset ist gerade der Grund,
   warum der KNX-Bus getrennt sein muss.
5. Wartet auf genau ein verifiziertes RPI-RP2-UF2-Laufwerk und kopiert
   die feste KNX085-Firmware genau EINMAL. Bei unsicherem
   Kopierergebnis KEINE automatische Wiederholung.
6. Prüft COM-Wiederanmeldung derselben USB-Seriennummer sowie KNX085
   all-off GPIO/ATtiny-Temperatur und INA219-Register/Spannung.
7. Prüft mindestens fünf gültige INA219-Leerlaufwerte bei 3.10–3.45 V,
   aktiviert M1 nur nach USB ARM, und führt EINEN Impuls Richtung F
   von 150 ms aus. Firmware limitiert grundsätzlich auf 50–250 ms.
8. Protokolliert Shunt-Rohspannung, angenommene Motorstromstärke und
   Motorspannung über die Zeit. All-off/STOP wird überprüft. Jeder
   beobachtete Fehler bricht ab. USB-Host sendet STOP redundant.
9. Speichert Berichte und Rohverlauf unter:
   C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX085-M1-20261019\logs
   inklusive CSV (ms, shunt_uV, bus_mV, nominal_mA) und JSON.
10. Setzt vor dem ersten M1-Puls eine lokale Einmal-Ausführungssperre.
    Weitere Fahrten erfordern die bewusste Prüfung und Freigabe der
    Messwerte; ein zweiter Aufruf bewegt M1 nicht erneut automatisch.

## 5. Grenzen und unbekannte elektrische Größen

- Der INA219 misst den gemeinsamen Shunt R29. Der tatsächliche
  Widerstandswert von R29 ist NICHT nachgemessen: nominell 0,200 Ohm
  laut Schaltplan, PCB-MPN widersprüchlich.
- Rohspannung des Shunts hat 10 uV/LSB; mA aus R29=0,200 Ohm ist
  eine **vorläufige Kalibrierannahme**, keine verifizierte Eichung.
- eQ-3 HmIP-VDMOT ist 3,3 V, maximal 120 mA nach Hersteller.
  Dieser Wert ist NICHT automatisch eine zulässige Stall-Abschaltschwelle.
- Keine automatische Blockfahrt, Homing/Nullpunkt-Erkennung oder
  Rückwärts-Freifahrt. Wir charakterisieren zunächst kurz das
  reale Laufstromprofil. Blockfahrt erst nach Durchsicht und
  Qualifikation der Stromkurve.
- TB6612-STBY ist auf PCB V1.2 fest HIGH. Software-STOP ist kein
  unabhängiges Hardware-STO und schützt nicht bei MCU-Absturz.
- Software kann **keine** mechanische Motorbewegung beweisen, nur
  Motor-ENABLE, Zeitgrenze und INA219-Messwerte protokollieren.

## 6. Tests und Git

- Vorhandener KNX085-motor_gate Native-Test: 25+ Checks PASS.
- KNX085 Hostparser-Test: 11/11 PASS.
- Neue KNX085-One-Shot Offline-Tests simulieren exaktes USB-Gerät,
  abwesendes UPDI, aktive/schweigende KNX-RX, korrekte UF2-Hashes,
  BOOTSEL, eine einzelne UF2-Kopie und eine einzelne M1-Probe.
- PowerShell-Plan ohne -Run: live Exit 0, KEIN Hardwarezugriff.
- PowerShell -Run ohne Freigabeschalter: verweigert sicher, kein
  Motor/BOOTSEL.
- KNX084 bleibt im Moment die tatsächlich geflashte Firmware.
- Kein Git-Push ohne gesonderte Benutzerfreigabe.

Der dokumentierte SCRIPT-Pfad ist für einen LLO-Home-Benutzer im
Windows-Projektroot verfügbar. Die UF2 liegt auf LLO Home unter
Workspace/Builds außerhalb des Git-Repos und wird separat gehasht.


### Ergänzung zur projektweiten Offline-QA

Die neuen KNX085-Tests sind erfolgreich (One-Shot 8/8, Host 11/11,
simulierte USB-Sequenzen 2/2, Python-Syntax und PowerShell-Plan/Refusal).
Ein darüber hinaus gestarteter projektweiter
tools/home_offline_check.ps1-Durchlauf bricht jedoch beim älteren
KNX026-Freeze-Audit für src/controller/temperature_bridge.cpp ab.
Diese Datei ist im aktuellen Git-Arbeitsverzeichnis unverändert.
Die KNX085-Änderungen liegen ausschließlich in den neuen
Testskripten/README/Dokumenten; kein Controller-Kernquelltext wurde
hier angepasst. Daher ist die projektweite QA in dieser Session
NICHT vollständig grün; dieser unabhängige Alt-Audit muss
separat mit seinem gespeicherten Quell-Hash abgeglichen werden.
