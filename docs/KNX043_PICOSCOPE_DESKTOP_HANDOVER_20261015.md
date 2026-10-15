# KNX043 – PicoScope-Handover LLO Desktop (15.10.2026)

**Erstellt am:** 14.10.2026. **Nächster Prüfstand:** LLO Desktop, `C:\ASH\Workspace\Projects\open-knx-valve-control`. **Priorität:** KNX-TX-Ruhepegel/Reset ohne KNX-Bus. **Status:** Vorbereitung; **kein Oszilloskop angeschlossen, keine Pegelmessung durchgeführt, keine KNX-Busfreigabe**.

## 1. Ausgangsstand

- LLO Home und LLO Desktop am 14.10.2026 vor diesem Handover: identisch `main`, Git `cc6eb38`, beide CLEAN (47 Commits vor `origin/main`; nicht gepusht).
- Board heute auf **LLO Home** erfolgreich mit separatem **KNX043 STKNX RX-only**-Image per USB-BOOTSEL/UF2 geflasht; Firmware antwortete dort auf **COM8**, USB-Seriennummer `E464401787522D33`, mit `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0`. **COM8 ist nicht automatisch der spätere Desktop-Port.**
- Nutzer bestätigt **R17 ausgelötet**, **U11 neu verlötet und mit 68 Ω gemessen**, **U9 richtiger Chip-Typ**. Ein vorheriges U11-Überhitzungsereignis ist damit noch nicht vollständig elektrisch geklärt; keine Messung zu U9 und Reset-/Brownout-Pegeln.
- Desktop-Agent v0.8.2 erreichbar. **PicoScope 6** installiert: `C:\Program Files (x86)\Pico Technology\PicoScope6\PicoScope.exe`. Scope-Hardware derzeit nicht nachgewiesen/noch nicht zur Verfügung. PicoScope nicht automatisch starten oder mit der Platine verbinden.
- KNX/IP-Schnittstelle auf Home zuvor netzwerkseitig unter **192.168.178.5:3671** (SCN-IP000.03, eigene Adresse 1.0.1) gefunden; kein Beweis für einen **isolierten Testbus**. **Kein Busanschluss und keine ETS-Programmierung** bis Hardware-Gates erfüllt sind.

## 2. Exakte Jumper-Pad-Netze aus V1.2-PCB-JSON

Quellbasis: `schematic/pcb_knx-valve-control_v1.2.json` (nicht aus einer Fotoannahme). Die drei Pads eines Jumpers sind **nicht** elektrisch gleichbedeutend; keine Brücken setzen, bis die tatsächlich bestückte Lage geprüft wurde.

| Bauteil / Pad | PCB-Netz | Warum |
| --- | --- | --- |
| **JMP3 Pad 2** | `KNX_TX` | **U9 Pin 24 (STKNX-Seite)** – vorrangiger PicoScope-Messpunkt |
| **JMP3 Pad 3** | `KNX_TX'` | **RP2040 GPIO0-Seite** – Vergleich mit Pad 2, sofern Jumperlage es zulässt |
| JMP3 Pad 1 | `KNX_RX'` | **Nicht KNX_TX!** Nicht versehentlich als TX messen oder auf 2/3 brücken |
| **JMP2 Pad 2** | `KNX_RX` | U9 Pin 23, erst später Empfangssignal |
| **JMP2 Pad 1** | `KNX_RX'` | RP2040 GPIO1, erst später Empfangssignal |
| JMP2 Pad 3 | `KNX_TX'` | **Nicht KNX_RX!** Nicht versehentlich mit Pad 1/2 kurzschließen |
| R17 Pad 1 | `KNX_TX` | Ursprünglicher 10-kΩ-Pull-up, laut Nutzer ausgelötet |
| R17 Pad 2 | `3.3V` | Nächster netzseitiger Vergleich zur stromlosen Brücken-/Widerstandsprüfung |

**Vor der Messung** auf der physischen Platine die Padnummerierung anhand Layout/Fotos verifizieren. Ein versehentliches Verbinden von JMP3-Pad 1 mit 2/3 oder JMP2-Pad 3 mit 1/2 kann RX/TX zusammenschalten. Für die gesamte geplante erste Messreihe bleibt die KNX-TP-Klemme komplett **abgeklemmt**.

## 3. Messfolge mit PicoScope 6 (nur USB, keine Motoren)

1. Platine, USB und alle übrigen Spannungsquellen vor Anschluss der Messleitung **stromlos** lassen. **Kein KNX-TP, keine Antriebe, keine externe 5-V- oder KNX-Versorgung, kein UPDI.** Den Schutzleiter-/Massebezug des am PC angeschlossenen PicoScope berücksichtigen.
2. Sichtkontrolle R17-Lötpads (kein Zinnsteg zu 3,3 V); U11 und U9 auf Verfärbung/Hitzeschäden prüfen. JMP3-Konfiguration und Board-GND mit Schaltplan/Multimeter **stromlos** identifizieren. U11=68 Ω stammt bisher aus Nutzerangabe. Keine Widerstandsmessung an eingeschalteter Platine.
3. **Oszilloskop-Masse nur an verifizierten Platinen-GND anschließen**, keinesfalls an KNX_A, KNX_B oder den USB-/KNX-Versorgungszweig. CH A als **10:1-Tastkopf** an **JMP3 Pad 2** (`KNX_TX` / U9). Falls zweiter Kanal sicher erreichbar, CH B an **JMP3 Pad 3** (`KNX_TX'` / RP2040 GPIO0). Keine benachbarten Pads mit der Tastkopfspitze kurzschließen. CH B kann später nach Umstecken für JMP2 dienen.
4. PicoScope 6 mit **DC-Kopplung**, Tastkopf-Einstellung **10:1**, konservativem vertikalen Bereich um 3,3-V-Logik und zunächst **1–10 ms/Div** einstellen. Zusätzlich kurzer Zeitbereich **etwa 50–200 µs/Div** zur Glitchsuche. Für schnelles Umschalten/Trigger ein Single-Shot mit positiver Flanke nahe **0,5–1 V** als Suchhilfe verwenden; das ist noch **kein** fachlicher STKNX-Grenzwert.
5. Erst bei sicherem Masse- und Tastkopfanschluss die Platine **nur über USB** versorgen. USB-Seriennummer und den neuen Desktop-COM-Port **live** identifizieren; KNX043-READY-Banner und lesendes `STATUS` auf `listen=0` prüfen. Im aktuellen RX-only-Image soll GPIO0 **nach Setup** LOW sein. JMP3 Pad 2 **separat beurteilen**, weil die U9-Versorgungsdomäne im USB-only-Betrieb nicht automatisch als aktiv belegt gilt.
6. **Aufzeichnen:** (A) stabiler USB-/Firmware-Normalbetrieb; (B) kontrollierter Reset/Neustart über vorgesehenen Reset/RUN (Lage erst prüfen); (C) USB abstecken und wieder verbinden, sofern sicher vorbereitet, um Einschalt-/Ausschalttransienten zu sehen; (D) wenn möglich kurz ROM-BOOTSEL **ohne KNX**, damit der Firmware-unabhängige GPIO-Zustand sichtbar wird. Keine absichtlich herbeigeführten Kurzschlüsse/Brownout-Experimente. Ein normales USB-Aus-/Einstecken ersetzt keine vollständige Brownout-Qualifizierung.
7. **Pegel protokollieren:** JMP3 Pad 2 und ggf. Pad 3 – DC-Low-Pegel, beobachtetes High/Peak, Impulsdauern und Zeitbezug zu Reset/Boot. PicoScope-Rohaufzeichnung/Screenshot in den Projekt-Arbeitsbereich ablegen; im Messprotokoll auf die Datei verweisen. **Ein dauerhaft HIGH, relevante Glitches oder unplausible Spannungen ⇒ KNX-Busanschluss weiterhin gesperrt.**
8. Optional für **RX** erst nach TX-Baseline: CH A an **JMP2 Pad 2**, CH B an **JMP2 Pad 1**. Das passive Empfangssignal bleibt ohne angeschlossenen KNX-Bus möglicherweise statisch; daraus **keine KNX-Kommunikationsfähigkeit** folgern. Der RX-Eingang am RP2040 muss mit 3,3-V-Logik kompatibel sein.

**Wichtige Einschränkung:** Selbst wenn das Oszilloskop in USB-only-Betrieb überall LOW zeigt, folgt daraus **noch keine Freigabe** für den KNX-Bus. Erst U9/U11-Elektro-/Thermikzustand, 3,3-V-/5-V-/KNX-Versorgung und `D1/F1/JMP1`-Rückspeisung sowie Reset-/ROM-/Brownout-Failsafe in der tatsächlichen Versorgungsumgebung nachweisen. Beim STKNX bedeutet **KNX_TX HIGH aktiv**, also potenziell Busstrom/U11-Erwärmung. Ein produktiver Haus-KNX ist **kein Ersttestbus**.

## 4. Prüfdatensatz – morgen mit Messwerten füllen

Vorbereitet: [KNX043 PicoScope Messwerte](KNX043_PICOSCOPE_MEASUREMENTS_20261015.json). **Alle Messwerte derzeit `null`**. Messung am Scope braucht eine neue legitime Desktop-Write-Session; keine fremde Session übernehmen.

**Nächster Chat:** Sobald die Platine am LLO Desktop angekommen ist, erst Agent/Session/Git und USB-Geräte/COM prüfen, danach PicoScope-Hardware finden und die oben vorbereitete **busfreie** Messung ausführen. **Keine neue Firmware, kein KNX-Busanschluss, kein ETS-Telegramm und kein GitHub-Push ohne neuen konkreten Auftrag.**

## 5. Quellen im Repository

- [KNX035 STKNX-TX-Hardwarekonflikt](KNX035_STKNX_TX_IDLE_HAZARD.md)
- [KNX043 Flash-Bestätigung](KNX043_RX_ONLY_FLASH_HOME_20261014.json)
- [KNX043 elektrische Sicherheits-Gates](KNX043_HOME_KNX_GATE.json)
- [KNX043 ausführlicher Bench-Plan](KNX043_HOME_KNX_BENCH_READINESS.md)

## Live-Erstprüfung PicoScope Kanal A – 15.10.2026

**Echte USB-only-Messung, keine KNX-Busfreigabe.** Am LLO Desktop meldete der RP2040 COM7, Seriennummer E464401787522D33, Firmware KNX043 mit read-only STATUS armed=0 listen=0 buffered=0 dropped=0. PicoSDK konnte **PicoScope 3205D MSO, Seriennummer GX118/0047** direkt öffnen.

Der Nutzer meldet: Tastkopf **1:1**, **Kanal A**, Messspitze am **KNX_TX**. Der tatsächliche Jumper-Pad und die Oszilloskop-Masseklemme wurden vom Agenten **nicht visuell überprüft**. Die Spannung ist daher zunächst ein **Kanal-A-Messwert nach Nutzerangabe**, kein bestätigtes JMP3-Pad-2-Gate.

- PicoSDK ps3000a.dll: Eingang A DC, ±5 V, 1:1, Trigger aus.
- Erste Kurzaufnahme: 16.000 Messpunkte / 31,744 ms: 0,04368–0,13118 V, Mittelwert 0,08419 V.
- Vier anschließende Blockaufzeichnungen mit je 100.000 Punkten / 498,4 ms, Abstand 4,984 µs, zusammen 400.000 Messpunkte und 1,9936 s reine Aufzeichnungszeit:

| Block | Min. | Max. | Mittelwert | > 0,5 V | Überlauf |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 0,000 V | 0,13118 V | 0,07911 V | 0 | 0 |
| 2 | 0,000 V | 0,13118 V | 0,07682 V | 0 | 0 |
| 3 | 0,000 V | 0,13118 V | 0,07801 V | 0 | 0 |
| 4 | 0,000 V | 0,13118 V | 0,07618 V | 0 | 0 |

**Gesamtmittel 0,07753 V.** In diesen vier Messfenstern war der an Kanal A angeschlossene Pegel stets unter 0,5 V. **Zwischen den Messfenstern, bei Reset/BOOTSEL/Brownout sowie mit KNX-TP wurde NICHT gemessen.**

Rohdaten/Summary auf LLO Desktop: C:/ASH/Workspace/Builds/OpenKNXValveControl/KNX043-PicoScope-20261015 mit knx043_picoscope_chA_summary.json und vier .i16le-Dateien (je 100.000 Int16-ADC-Werte little-endian). Die vier SHA256-Werte stehen im [Messprotokoll](KNX043_PICOSCOPE_MEASUREMENTS_20261015.json). Wiederverwendbarer [PicoSDK-Kanal-A-Recorder](../tools/knx043_picoscope_usb_tx_capture.ps1) unterstützt 1x und 10x, x86 PowerShell wegen PicoScope6-DLL.

**WICHTIGE EINSCHRÄNKUNG:** Ein 1:1-Tastkopf kann eine schwach vorgespannte Leitung belasten und eventuell LOW vortäuschen. **Messung mit korrekt geschaltetem 10:1-Tastkopf wiederholen**, sowohl Tastkopfschalter als auch Recorderparameter ProbeRatio 10; Masseklemme muss an geprüftem Platinen-GND liegen. JMP3 Pad 2 ist U9 KNX_TX, Pad 3 die RP2040-GPIO0-Seite. Erst danach gezielt Reset-/Boot-Transienten aufzeichnen. **KNX-Bus bleibt physisch getrennt und alle Motoren abgesteckt.** Keine Busfreigabe ohne U9/U11-, D1/F1/JMP1-, Reset-/Brownout- und Versorgungsgates.

## Live 10:1-Prüfung mit zwei Messbereichen – 15.10.2026

Nach Nutzerbestätigung **10:1 bereit** wurden acht weitere **passive** Kanal-A-Blöcke mit jeweils 100.000 Messpunkten (498,4 ms) auf dem LLO Desktop erfasst. KNX043 RP2040 an USB COM7, keine KNX- oder Motoraktivierung, **kein Reset**.

| PicoScope-Eingangsbereich | Tastkopf-Skalierung | Mittelwert an der Spitze (rechnerisch) | Maximum (rechnerisch) | Beobachtung |
| --- | --- | ---: | ---: | --- |
| ±5 V | 10:1 | 0,76413 V | 1,31182 V | Grober Bereich; etwa 2 ADC-Stufen |
| **±0,5 V** | **10:1** | **0,08526 V** | **0,13087 V** | Empfindlicher Bereich, 0 Samples über 0,5 V |

Je Reihe 400.000 Messpunkte und 1,9936 s reine Aufzeichnungszeit, alle PicoSDK-Aufrufe erfolgreich, kein ADC-Überlauf. Die Rohdaten sind in den beiden Unterordnern **10x_steady_usb** und **10x_refined_500mV** des Messarchivs archiviert; SHA-256 und Messwerte stehen im [Messprotokoll](KNX043_PICOSCOPE_MEASUREMENTS_20261015.json).

**Die unterschiedlichen Messbereichswerte sind ein wichtiges Kalibrierungsproblem, kein belegter KNX-TX-HIGH-Impuls.** In beiden Messbereichen lagen die ADC-Rohwerte nahe zwei nativen 8-Bit-Stufen; die Skalierung dieses kleinen ADC-Offsets mit dem Bereich kann den rechnerischen Spannungswert von 0,764 V auf 0,085 V verändern. Daher dürfen wir aus dem groben Bereich weder einen realen TX-HIGH-Pegel ableiten noch den empfindlichen Wert als kalibrierte TX-Spannung behaupten.

**Nächster notwendiger Messschritt:** Mit unverändert **10:1** und unveränderter PicoScope-Konfiguration **±0,5 V Scope-Eingang** die Messspitze vorsichtig auf einen vorher eindeutig identifizierten **Platinen-GND-Punkt** legen, Masseklemme an Platinen-GND belassen, und den Nullpunkt aufzeichnen. **Nicht KNX_A/KNX_B oder 3,3V versehentlich kurzschließen.** Danach Messspitze zurück auf **JMP3 Pad 2 / U9 KNX_TX**, gleiche Einstellung, zweiten Vergleich aufzeichnen. Ohne echten GND-Nullpunkt und genau identifiziertes Jumper-Pad bleibt die quantitative LOW-Aussage bedingt.

Reset-/BOOTSEL-/Brownout-Pegel und die U9/U11-, R17-, D1/F1/JMP1- und Rückspeisungsprüfungen stehen weiter aus. **Keine KNX-TP-Busfreigabe**.

## Live-Messung GND-Nullreferenz am 15.10.2026 (10:1)

Nach Nachricht **"GND bereit"** meldet der Nutzer, dass die Tastkopfspitze auf einen Platinen-GND-Punkt verlegt wurde. PicoScope 3205D MSO Kanal A blieb bei **10:1**, **DC**, **+/-0,5 V am Scope-Eingang** (+/-5 V an der Tastkopfspitze), 100.000 Samples pro Block, vier Bloecke, 498,4 ms je Block, **400.000 Abtastwerte**.

| Vergleich bei gleicher PicoScope-Einstellung | Unkorrigierter Mittelwert | Maximum | Bewertung |
| --- | ---: | ---: | --- |
| GND laut Nutzer, aktuelle Referenz | **0,07924 V** | 0,17455 V | Nullpunkt mit Offset/Quantisierung |
| KNX_TX laut Nutzer, davor gemessen | **0,08526 V** | 0,13087 V | Frühere USB-only-Messung |
| KNX_TX minus GND, zeitlich getrennte Fenster | **+0,00602 V** | – | Kleiner als typischer quantisierter Schritt |

Die realen ADC-Werte treten vor allem bei ca. 283, 567, 851 Codes auf (entspricht ungefähr **43,52 mV pro beobachtetem Code-Schritt** an der 10:1-Tastkopfspitze). **6,02 mV Mittelwertdifferenz sind deshalb kein verlässlicher Absolutnachweis** der KNX_TX-Spannung. Nicht simultane Aufzeichnung, Geräte-Offset/Drift, die unverifizierte konkrete GND-Klemme und Tastkopfkontakt sind weitere Unsicherheiten. Die GND-Aufzeichnung enthält vereinzelte Werte bis 0,17455 V: Rauschen/Quantisierung am vermeintlichen Nullpunkt.

Rohdaten der vier GND-Blöcke sowie die korrigierte Positionbezeichnung stehen im LLO-Desktop-Buildordner KNX043-PicoScope-20261015/10x_GND_zero_500mV; Prüfprotokoll in [KNX043-PicoScope-Messwerte](KNX043_PICOSCOPE_MEASUREMENTS_20261015.json). Der Recorder akzeptiert künftig die explizite Position ProbePoint=KNX_TX bzw. ProbePoint=GND, um eine fälschlich fest codierte Bezeichnung zu verhindern.

**Ergebnis:** Beide Messungen liegen messtechnisch nahe am GND-Offset; **keine belegte dauerhafte TX-HIGH-Spannung im bisherigen USB-only-Ruhebetrieb**. Das bedeutet **nicht**, dass GPIO0/U9 KNX_TX während Reset, BOOTSEL, Brownout oder mit KNX-Versorgung sicher LOW bleibt. R17-Pads/U11/U9/F1/D1/JMP1 und die übrigen Hardware-Nachweise stehen aus. **Der KNX-TP-Bus bleibt abgeklemmt.**

**Nächster Bedienerschritt:** Tastkopfspitze mit unverändertem 10:1-Tastkopf vom GND wieder auf **JMP3 Pad 2 = KNX_TX / U9 Pin 24** umsetzen, dabei keine benachbarten Pads kurzschließen. Auf Nutzerbestätigung ("TX bereit") mit identischen Parametern noch eine frische USB-only-Messung erfassen, um Drift einzugrenzen. Kein Reset-/Bus-Test automatisch auslösen.
