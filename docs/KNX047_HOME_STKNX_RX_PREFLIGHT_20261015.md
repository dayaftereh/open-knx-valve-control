# KNX047 - LLO Home STKNX V1.2 RX-Bench: Livecheck und elektrische Vorpruefung

**Stand:** 15.10.2026, ca. 22:39 MESZ. **Entscheidung:** `USB_READY / KNX_TP_NO_GO`.
**Hardware:** PCB V1.2, RP2040 U18, STKNX U9. **Ziel:** spaeter ausschliesslich passiven KNX_RX-Empfang am separaten Testbus nachweisen, keine KNX-Sendung / Motorbefehle.

## 1. Live auf LLO Home verifiziert (KNX047)

- Agent `ok`, Windows, Version `0.7.9`, zuletzt 2026-10-15T20:38:50Z.
- Neue eigene Write-Session `ses-20261015T203914-5a3850a88729`. KNX046-Session `ses-20261015T193010-d5b032b55fb7` CLOSED/completed, keine laufenden dortigen Jobs. Keine fremde Write-Session uebernommen.
- Repository `C:\\_myspace\\workspace\\open-knx-valve-control`: `main` und `origin/main` **beide** `f647cec87ceb018329015eaf9b04fb87dceba765`; vor diesen KNX047-Dokumentationsaenderungen CLEAN. Kein Pull/Push erforderlich.
- USB-Port eindeutig `COM8`, VID/PID `2E8A:000A`, Seriennummer `E464401787522D33`; Port kann nach Neustart wechseln.
- Read-only-Abfrage `tools/knx043_rx_capture.py status --port COM8 --expect-serial E464401787522D33` erfolgreich: `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0`.
- Vorliegende KNX043 RX-only-UF2 noch vorhanden, 146432 Bytes, SHA-256 `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f`. **Nicht erneut geflasht.** USB-Status bestaetigt laufendes Diagnoseprogramm, kein unabhaengiger Flash-Readback.
- Original-PDF `schematic/sch_knx-valve-control_v1.2.pdf` SHA-256 `e7e452f1b517dabe077e9ac3987d3c1565464005b7a744beb8b53b3181c52789`, EasyEDA-Schaltplan-JSON `3c36ba0775ec04b5798b3084b04206ac4e7e4b07a125af9c1239a3e8c7deb367`; stimmen mit der dokumentierten V1.2-Revision ueberein. Bestehende verifizierte Schaltplan-/PCB-Audits: [Schaltplan](SCHEMATIC_V1_2_REVIEW.md), [PCB](PCB_V1_2_AUDIT.md). Keine neue ERC-/DRC-/As-built-Zertifizierung.
- `docs/KNX043_HOME_KNX_GATE.json`: **17 von 17 Beobachtungen noch `null`**, Auswertung `BLOCKED_AWAIT_HARDWARE_EVIDENCE`. Softwarebeweise ersetzen keine physische Beurteilung. Es wurde keine KNX-Leitung, kein Motor und keine aktive RX-Capture durch den Agenten angeschlossen oder gestartet.

## 2. Kritischer Signal- und Strompfad

| Punkt | V1.2-Quelle / Konsequenz |
| --- | --- |
| U9 STKNX Pin 24 / JMP3 Pad 2 `KNX_TX` | LOW = Ruhe, HIGH fuer ca. 35 us = aktiver Sendepuls; U9 besitzt nur schwachen internen Pull-down (typ. 6 uA). |
| RP2040 GPIO0 / JMP3 Pad 3 `KNX_TX'` | Verbindung / Brueckenlage physisch noch zu pruefen. KNX043 setzt GPIO0 **erst nach Firmware-Start** LOW; Reset, BOOTSEL und Brownout sind nicht hardwareseitig garantiert. |
| R17 | Historischer 10-kOhm-Pull-up `KNX_TX -> 3.3V`; laut Nutzer ausgelötet, **Pads weder optisch noch ohmisch freigegeben**. Keinen Pulldown ueber die alten R17-Pads einbauen, weil ein Pad 3.3V fuehrt. |
| U9 Pin 3 `R68` -> U11 -> `KNX_A` | U11 laut Design 68 Ohm / 2 W; frueheres starkes Erhitzen. ST gibt fuer typischen 68-Ohm-Sendewiderstand **mindestens 1 W** an. Reale Bauform/Belastbarkeit und thermische Unversehrtheit pruefen, nicht nur Widerstandswert. |
| U9 Pin 23 `KNX_RX` / JMP2 Pad 2 -> Pad 1 / RP2040 GPIO1 | KNX_RX LOW in Ruhe, HIGH waehrend aktivem Busimpuls. VCCCORE/KNX_RX-HIGH darf den RP2040-GPIO **nicht mit 5 V** beaufschlagen: U9 VCC_SEL/VCCCORE Pin 20 und Pegelkompatibilitaet pruefen. |
| JMP1 / Q1 / D6 / F1 / D1 / U6 | KNX_VCC/USB_VCC-Versorgungsauswahl und gemeinsame 3.3V-Versorgung. D1 laut Nutzer ueberbrueckt, F1 physisch T2.5A statt Schaltplan 630 mA; USB+KNX-Gemeinschaftsbetrieb ohne Rueckspeisepruefung **nicht freigegeben**. `KNX_B` ist im V1.2-Schema mit Board-GND verbunden (keine automatische galvanische Trennung gegen USB-PC). |
| U11 / U9 nach thermischem Vorfall | Beschädigung oder Fehlbestueckung nicht ausgeschlossen. Normale USB-Firmwareantwort beweist U9-Funktion nicht. |

**Herstellerbasis:** STMicroelectronics STKNX DS12399 Rev.3, Abschnitte Pins/5.1.1/5.1.2/Tabelle externer Bauteile: <https://www.st.com/resource/en/datasheet/stknx.pdf>. 21-32 V DC ist der spezifizierte KNX-Busspannungsbereich, **keine Freigabe fuer eine improvisierte Busversorgung**.

## 3. Realer Pruefplan, derzeit ohne Freigabe

### Stufe A - vollstaendig stromlos (zuerst gemeinsam mit Nutzer)

USB-C, KNX-TP, externe Spannungen, UPDI sowie alle Motorklemmen **trennen**; Kondensatoren entladen lassen, keine Ohmmessung an bestromter Platine.

1. Scharfe Fotos Vorder-/Rueckseite sowie Nahaufnahmen **R17, U9, U11, JMP1, JMP2, JMP3, D1, F1, Q1**. Sichtpruefung auf Lötbruecken, verkohlte Stellen, verrutschte Pads / Beschaedigung von U11/U9.
2. Multimeter (stromlos): R17 tatsaechlich offen/entfernt, **keine niederohmige Kurzschlussbruecke KNX_TX zu 3.3V**; Signalweg am U9 Pin24 / JMP3 Pad2 identifizieren. Andere Halbleiter-/Parallelpfade koennen Widerstandsmessungen beeinflussen; keinen festen Ohmwert fuer den internen Pull-down annehmen.
3. U11 zwischen R68 und KNX_A: Sollbestueckung 68 Ohm und mindestens passende Leistungs-/Temperaturklasse bestaetigen. In-Circuit-Abweichung kann Parallelpfade haben; bei Unklarheit Fachpruefung statt einschalten. Nach frueherem Hitzeereignis ist ein gemessener 68-Ohm-Wert **allein kein Integritaetsbeweis**.
4. JMP2 U9 Pin23 ↔ GPIO1 und JMP3 U9 Pin24 ↔ GPIO0 mittels V1.2-Padbezeichnung/echter Brueckenlage nachvollziehen. Fuer den **ersten RX-only-Busversuch physische TX-Entkopplung / fail-LOW-Sperre** technisch bewerten; JMP3 nur nach Schaltplan-/PCB- und Bestueckungspruefung aendern.
5. Versorgungspfad USB_VCC, 5V_, 5V, D1_1, 3.3V, KNX_VCC, KNX_A, KNX_B/GND auf Kurzschluss-/Rueckspeiserisiken pruefen; D1-Bypass, F1 T2.5A und JMP1-Stellung erfassen. **Kein** Einschalten zweier Quellen zum Experimentieren.
6. Falls ein Kurzschluss, beschädigtes U9/U11, falscher Widerstand, undefinierte TX-Bruecke oder ungeklaerter Schutzpfad vorliegt: **STOP / NO-GO**.

### Stufe B - weiterhin ohne KNX-Bus, nur nach bestandener Stufe A

- Mit DMM definierte Punkte und Bezugs-GND messen: USB VBUS, `USB_VCC`, `5V_`, `5V`, U6 Pin1 `D1_1`, `3.3V`. U6 benoetigt gemaess dokumentierter Herstellergrenze min. 4.75 V Eingang. Bisheriger PicoScope-Wert ~4.26 V am *nicht unabhaengig identifizierten* +5V-Messpunkt ist **kein verifizierter Versorgungswert**; DMM-Vergleich erforderlich.
- U9 `VCCCORE` / VCC_SEL-Konfiguration und KNX_RX-Pegel gegen erlaubte RP2040-IO-Spannung fachlich pruefen; insbesondere einen moeglichen 5-V-Logikpegel am GPIO1 ausschliessen.
- Mit geeignetem **zeitaufloesendem Oszilloskop** U9 Pin24/JMP3 Pad2 (und GPIO0/JMP3 Pad3 getrennt) im USB-Only-Betrieb, Reset, BOOTSEL/USB-Replug und Brownout beurteilen. Ein einfaches DMM oder bisheriger No-Trigger >0.35 V genuegt nicht fuer eine Aussage zu allen transienten Bus-Power-Zustaenden. Die KNX-spezifische aktive TX-Ansteuerung muss auch bei Ausfall des MCU physisch gesperrt sein.
- Kein weiterer Flash, kein KNX-Senden, keine Motoren. Die dokumentierten PicoScope-Daten entstanden **ohne KNX-Bus** und ersetzen diese Freigabe nicht.

### Stufe C - isolierter KNX-RX-Test **erst nach Fachfreigabe**

- Separates, nicht mit dem Hausbus verbundenes KNX-TP-Labornetz mit geeignetem **strombegrenztem KNX-Netzteil inkl. vorgesehener Drossel**, eigener KNX-Testquelle/Schnittstelle und gepruefter Bus-/USB-GND- sowie Versorgungsentkopplung bereitstellen. **192.168.178.5:3671 ist keine Laborteststelle.**
- Stufenweise unter fachlicher Aufsicht einschalten, Spannung/Strom, U9/U11-Erwaermung, U9 TX (ruhig LOW in allen Betriebslagen), 3.3V, VCCCORE und RX-High sicher pruefen. Bei Erwärmung, Stromlimit/Buskollaps, unerwartetem TX-HIGH, Rueckspeisung oder unzulaessigem RX-Pegel **sofort trennen**.
- Erst bei dokumentierten 17/17 technischen Nachweisen **und separater Freigabe** wird die Host-RX-Erfassung zulässig. Das Host-Tool blockiert `capture` bei offenem Gate. Kein Schalter darf nur zum Testen des Clients auf `true` gesetzt werden.
- Vorgesehener Aufruf **nicht jetzt ausfuehren** (COM-Port erneut enumerieren, Ausgangspfad ausserhalb Repo):
  ```powershell
  C:\Users\ll\.platformio\penv\Scripts\python.exe tools\knx043_rx_capture.py capture --port COM8 --expect-serial E464401787522D33 --seconds 30 --output C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX047_RX_BENCH\rx_edges.jsonl --independent-electrical-review-complete --isolated-knx-testbus
  ```
- Primaerer Erfolg: reproduzierbare GPIO1-Flanken bei **nachweislicher Aktivitaet auf separatem Testbus**, plausible ca. 35-us-HIGH-Pulse und `dropped=0`, gegen unabhaengiges Bus-/Scope-Signal plausibilisiert. `0 edges` ohne sichergestellte Testbus-Telegramme beweist **keinen** U9-Defekt; Flanken alleine sind **keine** validierten KNX-Telegramme.

## 4. KNX047 Ergebnis, offene Abhaengigkeiten und ASH-Workflow

- **Software/USB:** GO. **Physische KNX-TP-Verbindung:** NO-GO, weiterhin 17/17 Gate-Felder offen. Keine manuellen Messungen aus Agent-Daten erfunden.
- Prioritaet fuer die naechste Nutzerrueckmeldung: **USB abziehen, R17/U11/U9-Nahaufnahme und DMM-Werte stromlos von U11 sowie KNX_TX gegen 3.3V** (plus fotografierte Jumperstellung). Danach erst konkrete Messpunkte fuer USB-Spannungen.
- `docs/slices/_OPEN_KNX042_MOTOR_LED_BRINGUP.md` ist noch vorhanden. **Keine zweite _OPEN_KNX047-Datei erzeugt**, um die im ASH-Workflow geforderte Ein-Slice-Regel nicht zu umgehen. KNX047 ist ein begrenzter Sicherheits- und Handover-Nachweis ohne Motor-/KNX-Aktivierung; KNX042 bleibt unveraendert und offen.
- Neues Ergebnis wird in README/ROADMAP referenziert. Kein Git-Push; lokale QA/Commit getrennt protokollieren. Diese Dokumentationsarbeit darf nicht als bestandene elektrische Hardwarefreigabe interpretiert werden.
