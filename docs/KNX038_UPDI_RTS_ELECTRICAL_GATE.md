# KNX038 – Units V1.2 CH340 RTS/UPDI-Programmer am ValveControl ATtiny3216

**Stand 14.10.2026, LLO Desktop. Status: COM4 erkannt, Schaltung geprüft, ATtiny-HEX offline erfolgreich gebaut, Signatur/Flash weiterhin NICHT durchgeführt.**

## Live-Status und belegte Schaltung

Der Nutzer meldet, dass der sechspolige Programmer mit dem ValveControl-Board verbunden sein sollte. COM4 = USB CH340 **VID:PID 1A86:7523**, RP2040 aktuell COM7 = 2E8A:000A, USB-Heartbeat läuft. Keine KNX- oder Motorenanschlüsse laut Nutzer. Eine PC-Enumeration von COM4 beweist **nicht** den Anschluss, die Steckerausrichtung oder die elektrische UPDI-Pegelkompatibilität.

**Units-Programmer Originalquelle:** `C:\ASH\Workspace\Projects\Units\schematic\updi\sch_updi_programmer_v1.2.json` und `pcb_updi_programmer_v1.2.json`, außerdem `configurator/src/app/services/firmware/serial-updi-programmer.service.ts`.

- U1 CH340G, Pin 16 `VCC` = vom USB-Anschluss erzeugte Versorgungsnetze; U2 und U7 `SN74LVC1G3157DCKR` Pin 5 ebenfalls `VCC`. Es ist im Netzabgleich **keine automatische 3,3-V-Pegelwandlung über diese MUX-ICs** nachgewiesen.
- U2 Pin 6 und U7 Pin 6 hängen am Netz `RTS`, Umschaltung zwischen UART- und UPDI-Pfaden. USB-TXD → R21 → U2 Pin4, UPDI-TX U2 Pin3. UPDI-RX → U7 Pin3, über R18 nach Programmer CN1 Pin 3 `UPDI`; D3 verbindet TX_UPDI und RX_UPDI.
- Programmer-Stecker: **CN1.1 = CN1_1** über D1 SS34 nach DVCC (VCC-Netz/-MOSFET-Logik gesondert zu prüfen), **CN1.2 = TX**, **CN1.3 = UPDI**, **CN1.4 = RX**, **CN1.5/6 = GND**.
- Original Units-Programmer-Software setzt bei UPDI `port.setSignals({dataTerminalReady:true,requestToSend:true})` und beim Schließen beide false. `RTS=True` bezeichnet die **logische hostseitige API-Einstellung**; am CH340 existiert ein aktives LOW `RTS#`-Signal. Die reale MUX-Stellung und der UPDI-Spannungshub auf diesem Board wurden noch nicht mit DMM/PicoScope gemessen.
- `pymcuprog` auf LLO Desktop ist installiert. Dessen im Gerät vorliegende `pymcuprog/serialupdi/physical.py` initialisiert PySerial mit `serial.Serial(port, baud, parity=even, stopbits=two)`. Bei Standard-PySerial-Open werden RTS/DTR typischerweise als True gesetzt. Der Treiber sendet beim Initialisieren **sofort einen UPDI BREAK**, deshalb `pymcuprog ping` NICHT als nur passives COM-Probing ansehen.

**ValveControl V1.2 Quelle:** `schematic/pcb_knx-valve-control_v1.2.json`:

- `CN1.1 = 5V`, `CN1.2 = RXD`, `CN1.3 = UPDI`, `CN1.4 = TXD`, `CN1.5/6 = GND`; der Stecker kreuzt damit die jeweiligen UART-Signale zur Programmer-Seite passend. Pin-1-Orientierung am **realen** Kabel bleibt unbelegt.
- U25 ATtiny Pin 1 = **3.3V**, Pin16 = `UPDI`, Pin20 = GND. Schaltplan und aktuelle Firmware erwarten **ATtiny3216**, PCB-Herstellerteilenummer lautet dagegen **ATTINY1616-SN**, also keine reale Identifikation. Erwartete 3216-Signatur `1E 95 21`, ATtiny1616 `1E 94 21` laut vorhandenem Units-Service. Nur ein echter UPDI-Signatur-Read kann den bestückten Typ endgültig bestätigen.

**Elektrische Einordnung:** Texas Instruments [SN74LVC1G3157](https://www.ti.com/product/SN74LVC1G3157) schaltet analoge Signale bis zum jeweiligen `VCC`, reguliert diese Pegel aber nicht auf Target-VDD herunter. Microchip [ATtiny3216/3217 Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny3216-17-DataSheet-DS40002205A.pdf), Tabelle 36-1 nennt Pin-Spannungsgrenze `VDD+0,5 V` für normale I/O und eine gesonderte RESET-Spannungsgrenze. Ein 12-V-UPDI-Wiederherstellungsimpuls bzw. die RESET-Ausnahme sind **kein allgemeiner Nachweis**, dass alle am sechspoligen Programmer anliegenden UART-/Versorgungssignale bei 3,3-V-ATtiny-VDD sicher sind. Deshalb keine Grenzwertfreigabe aus dem Schaltplan ableiten.

## Bereits real erledigt – Software

1. LLO Desktop `pio run -e temperature` auf aktuellem `main` HEAD `1b7b649`: **SUCCESS** in 8,63 s, Firmware für `ATtiny3216`, 8.655 B Flash / 983 B RAM (26,4% / 48,0%). Bestehendes CRC-Framing und USART0 ALT1 PA1/PA2, neun Temperatursensoren, keine Änderung an Firmware-Logik.
2. HEX + ELF unveränderlich nach `C:\ASH\Workspace\Builds\OpenKNXValveControl\KNX038-ATtiny3216-offline-20261014` kopiert und SHA256-Manifest erstellt. HEX 24.356 Bytes; SHA256 `f3d118db90d8776de1b661a206f4bdcd025066bf1b27425335edd439dba95c6a`. Im Manifest ausdrücklich `flash_authorized=false`, `signature_read=false`.
3. [Tools KNX038](../tools/knx038_updi_readiness.py) mit `plan` ohne Hardware, `probe` nur PnP-Enumeration und `verify-build` SHA-Check. Die spätere Aktion `ping` enthält **nur** read-only `pymcuprog -d attiny3216 -t uart -u COM4 ping`, **keine** `write`/`erase`/Fuses. Sie verweigert Ausführung, solange nicht explizit alle elektrischen Gates als vor Ort gemessen bestätigt sind. **Dieses Tool wurde in KNX038 bisher nur im gesperrten Zustand getestet; COM4 blieb geschlossen, RTS/DTR unverändert.** Status der bereits real bestehenden RP2040-COM7-USB-Firmware bleibt unverändert.

## Nächster kurzer physischer Messschritt

Mit **ValveControl und Programmer zunächst physisch getrennt**, möglichst ohne andere Bordnetzquellen und ohne KNX/Motoren:

1. **Sechspoliges CN1-Kabel vom ValveControl abziehen**, Programmer weiterhin über USB am Desktop. Exakte Lage Pin 1 am Programmer fotografieren/kennzeichnen.
2. **Programmer-Pegelmessung** zwischen CN1 Pin 3 (UPDI) und Pin 5/6 (GND) sowie Pin 1 (Versorgung) im UART- und UPDI-Modus durchführen. Für den Moduswechsel kann danach der Agent **nur am elektrisch nicht mit ValveControl verbundenen COM4** RTS False/True ausgeben. Diese Ansteuerung nur nach expliziter Bestätigung der Trennung.
3. Am ValveControl separat U25 VDD 3,3 V, CN1 Pin 1 5 V, UPDI Pin 3 gegen GND stromlos/unter bekannter begrenzter Versorgung erfassen; Quellen- und RÜCKSPEISE-Schutz F1/D1 müssen weiterhin geprüft werden.
4. Sicherstellen, dass Programmer beim Wiederanschluss das 3,3-V-Ziel nicht über einen 5-V-Steuer-/UART-Pfad unzulässig belastet, sowie dass CN1.1 nicht zwei 5-V-Quellen gegeneinander treibt. Bei Bedarf geeignete, nachweislich kompatible UPDI-3,3-V-Pegelwandler-/Versorgungstrennung einsetzen.
5. Erst nach positiver Messung Pin-1-Ausrichtung, U25-VDD und UPDI-Leerlaufpegel erneut prüfen und **read-only** `pymcuprog ping` mit RTS=True. Erwartung: ATtiny3216 `1E 95 21`. Keine automatische Chip-Erase-, Fuse- oder Write-Aktion, **insbesondere nicht blind** via `pio run -e temperature -t upload`; dessen Skripte enthalten bereits `write --erase --verify`.
6. **Erst bei verifizierter Signatur und elektrischem Gate** eigenes ATtiny-Flashverfahren festlegen (eine HEX, gesonderte Freigabe, Verify, ohne Fuse-Änderungen), dann Temperatursensor-/RP2040-Link prüfen. KNX und Motoren bleiben weiterhin getrennt.

**KNX038 STOP-Gate:** `UPDI_RTS_ELECTRICAL_LEVEL_NOT_VERIFIED`; das ist kein Softwareproblem des RTS-MUX, sondern eine bisher fehlende tatsächliche Steck-/Pegel-/Backfeed-Bestätigung. **Nicht behaupten, dass das HEX auf dem ATtiny läuft.**

## KNX039 Live-Nachtrag: Nutzerfreigabe und erfolgreicher UPDI-Lesezugriff (14.10.2026)

Nach der frueheren KNX038-Planungs-Sperre hat der Nutzer ausdruecklich bestaetigt, dass der verbundene Programmer schon erprobt ist und das ATtiny-Programm bereits vorhanden ist. Er hat COM4-UPDI-Auslesen freigegeben, ohne das 2x3-Kabel abziehen zu wollen. Daraufhin wurde unter **KNX039** das echte `pymcuprog ping` samt Flash-/EEPROM-/Fuse-/USERROW-Read erfolgreich ueber COM4 mit `Ping response: 1E9521` ausgefuehrt. Das beweist die **reale UPDI-Funktion und ATtiny3216-Geraetekennung**, nicht separat den Ausgangsspannungshub der MUX bei RTS oder CN1.1-Versorgungsisolation. [Live-Ergebnis und Backups](KNX039_LIVE_UPDI_READBACK.md), [maschinenlesbare Evidenz](KNX039_UPDI_READBACK_EVIDENCE.json). KNX038 JSON bleibt **historischer Vorzustand**, wurde nicht stillschweigend als Messung umgedeutet. Keine ATtiny-Firmware geschrieben und keine Fuse aenderung.
