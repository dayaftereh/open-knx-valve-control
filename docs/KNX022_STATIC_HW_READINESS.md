# KNX022 – Statischer Hardware-Readiness-Check der V1.2-Platine

**Stand:** 12.10.2026. **Ergebnis:** Die vorliegenden EasyEDA-/Firmware-Quellen wurden reproduzierbar geprüft; die **bestückte Platine ist NICHT für motorische Inbetriebnahme freigegeben**.

Die eigentliche [KNX002 As-built Hardware-/BOM-Abnahme](ROADMAP.md) bleibt **geplant**. Dieser KNX022-Slice ist ein abgegrenzter Quellen- und Risikocheck, kein Ersatz für Fotos, bestückte Bauteile, Messungen oder native EasyEDA ERC/DRC.

**Automatisierte Quelle:** [audit_knx022_hw_preflight.py](../tools/audit_knx022_hw_preflight.py) und [Negative-Tests](../tests/test_knx022_hw_preflight.py). Die deterministische [maschinenlesbare Risiko-/Netzliste](KNX022_STATIC_HW_PREFLIGHT.json) enthält Quell-Hashes, bestätigte Netzzuordnungen, Kennzeichnungen der drei MPN-Konflikte und die noch offenen Nachweise. Keine Hardware wurde für diesen Bericht elektrisch kontaktiert oder aktiviert.

## 1. Konkret verifizierte Quelllage

Der Auditor liest **live aus den Repository-Dateien**:

- [PCB EasyEDA V1.2 JSON](../schematic/pcb_knx-valve-control_v1.2.json): Pads, Netze und Manufacturer-Part-Metadaten.
- [Schaltplan EasyEDA V1.2 JSON](../schematic/sch_knx-valve-control_v1.2.json): sichtbar annotierte Werte von R29, U25, F1.
- [RP2040 Pinbelegung](../src/controller/config.hpp) und [aktuelles Main](../src/controller/main.cpp).
- [ATtiny PlatformIO Target](../src/temperature/temperature.ini).

**35 statische Invarianten PASS**. Wesentliche Ergebnisse:

| Elektrischer Teil | Beobachtung aus V1.2, nicht von der realen Platine |
| --- | --- |
| Acht Antriebe | U34 = M1/M2, U36 = M3/M4, U37 = M5/M6, U35 = M7/M8; je zwei separate PWM-Netze und gemeinsame Richtungsnetze IN_1 / IN_2 |
| RP2040 | Firmware D10…D17 = M1_EN…M8_EN, D18/D19 = IN_1/IN_2; passende Netze auf U18 vorhanden; die Firmware-Mainloop enthält noch **keine motorische GPIO-Steuerung** |
| TB6612FNG Standby | Pin **19 von U34/U35/U36/U37 liegt fest an 3.3V**. Dies ist keine durch RP2040 schaltbare gemeinsame Motor-Notabschaltung |
| Stromüberwachung | **R29 3.3V ↔ M_VCC**, R33/R34 verbinden die beiden Messseiten mit **einem** INA219 U23; Messkanal gilt für die gesamte gemeinsame Motorversorgung, nicht für acht getrennte Stromsensoren |
| Spannungswandler | USB_VCC → D6 → 5V_ → F1 → 5V → D1 → D1_1 → U6 VIN → 3.3V; aus Layoutnetz-Namen folgt **keine** ausreichende Eingangsspannung unter Last |
| KNX-/USB-Umschaltung | JMP1 verbindet KNX_VCC mit R9_2 im Q1-Auswahlpfad; **kein** externer 5-V-Eingangsstecker |
| ATtiny-Sensoren | U25 hat 20 PCB-Pads und T0…T8; das Firmware-Projekt erwartet einen **ATtiny3216**, tatsächlich bestückte Kennzeichnung bisher unbekannt |

**Besonders wichtig für KNX020/KNX021:** Dort ist ein All-off-ACK nur ein *simuliertes Ereignis*. Da die V1.2-STBY-Leitung fest high ist, **kann eine echte Firmware nicht einfach ein globales STBY-Low per GPIO ausgeben**. Vor jeder echten Fahrt benötigt KNX004 ein auf der tatsächlichen Platine realisierbares Ausgangs-Aus-Konzept, zum Beispiel verifizierte PWM-Aus-Zustände plus geeignete unabhängige Hardwareverriegelung/Versorgungstrennung in einer überarbeiteten Platine. Ob V1.2 auf anderem Weg ausreichend sicher abgeschaltet werden kann, muss fachlich und elektrisch geprüft werden.

## 2. Konkrete Blocker vor der ersten Motorbewegung

Die Prioritäten sind interne **Inbetriebnahme-Sperren**, keine behaupteten offiziellen Norm-Einstufungen.

| Priorität | Kennung | Evidenz und notwendige Klärung |
| --- | --- | --- |
| P0 | **R29_PART_METADATA** | Schaltplan: **200 mΩ / 1 W**. EasyEDA-Herstellerteilenummer: **SCR1206F1M1** (LCSC C3017245). Teilenummer widerspricht dem Sollshunt. Bestücktes Bauteil/BOM und niederohmige Messung prüfen; INA219 danach passend kalibrieren |
| P0 | **U25_PART_METADATA** | Schaltplan/PlatformIO: **ATtiny3216**. PCB-MPN: **ATTINY1616-SN** (C614136). Physische IC-Aufschrift und UPDI-Gerätesignatur vor Flash prüfen |
| P0 | **F1_PART_METADATA** | Schaltplan: **630 mA / 275 V**. PCB-MPN: **S1032-F-60.0A** (C553920). Tatsächliche Sicherung, Kennlinie und Nominalstrom identifizieren; die Angabe 275 V bedeutet nicht, dass die Platine einen 230-V-Anschluss hat |
| P0 | **TB6612_STBY_TIED_HIGH** | Alle vier TB6612-STBY-Pins (19) an 3,3 V; kein unabhängiger MCU-gesteuerter Kill. Reset, Brownout, Fehlerpfad, Ausgangszustände und ggf. Hardware-Neudesign klären |
| P0 | **U6_TWO_DIODE_HEADROOM** | Zwei Schottky-Dioden im USB-Zweig, während U6 TSR 1-2433 mindestens **4,75 V VIN** benötigt. Reale VIN und 3,3-V-Stabilität unter definierter **motorloser** Last messen |
| P0 | **KNX_USB_SOURCE_BACKFEED** | Q1-/JMP1-Netze sind keine geprüfte externe Quelle. Rückspeisung USB ↔ KNX, Masse-/Trennkonzept und geschützte externe Versorgung vor Umbau qualifizieren |
| P0 | **STKNX_POWER_BUDGET** | Herstellerbegrenzungen und Gesamtsystemlast müssen für KNX-Bus, RP2040, ATtiny, LCD und maximal **einen** HmIP-VDMOT rechnerisch und messtechnisch zusammengeführt werden |
| P0 | **MOTOR_OUTPUT_BOOT_UNKNOWN** | Die vorhandene RP2040-Mainloop initialisiert noch keine Motor-Pins mit nachgewiesen sicherem Default; alle PWM-/Richtungspfade im Boot-/Reset-/Brownout-Fall prüfen |
| P1 | **SHARED_INA219_AND_DIRECTION** | Nur ein Stromsensor und gemeinsame Richtung: **immer genau ein** aktiver Motor; keine Hall-/Encoder-Positionsrückmeldung. Stromkurve/Hubzeit und Referenzierung fehlen |
| P0 | **EASYEDA_MANUFACTURING_GATE** | Native ERC/DRC, Netlist-/Ratsnest-Vollständigkeit, bestätigte Bestückungs-BOM und Abgleich gegen die echte Platine fehlen. JSON-Tracks/Vias allein beweisen keine Fertigungsfreigabe |

Die Blocker stehen zusätzlich als strukturiertes Array im [JSON-Report](KNX022_STATIC_HW_PREFLIGHT.json). Er enthält bewusst für **alle realen Mess-/Bestückungsnachweise null-Werte** – ein korrigiertes MPN-Feld allein kann diese nicht auf "PASS" ändern.

## 3. Benötigte reale Nachweise für KNX002/003

**Vor Anschluss eines echten Motors, zunächst spannungsfrei:** Fotos der Vorder- und Rückseite der konkreten V1.2-Platine mit erkennbarer Revisionskennung und gut lesbaren Details von U25, R29, F1, JMP1, Q1, U6 und den vier TB6612. Mit tatsächlicher Einkaufs-/Bestückungs-BOM abgleichen; für R29 und F1 reichen aus der Quelle allein keine sicheren Werte.

**Spätere Labor-Gates in fachgerechtem, strombegrenztem Aufbau:** Separat die Leiterbahn-/Brückenbelegung mit stromloser Durchgangsmessung prüfen. Erst nach sicherer Quellenfreigabe und ohne Motor KNX-only/USB-only untersuchen: KNX_VCC, USB_VCC, 5V_, 5V, **D1_1/U6 VIN**, 3.3V, M_VCC, Bus-Entnahmestrom und unerwartete Rückspeisung. Den 3,3-V-Antrieb **niemals an 5 V** anschließen und keine 5-V-Quelle direkt an M_VCC/JMP1 anlegen.

**Vor motorischem Lauf:** Bei sicherem Versorgungsaufbau Reset-/Watchdog-All-off durch unabhängige Hardwarebeobachtung nachweisen; reale Motorpolung, Stromkurve, Spannung, Laufzeit und Endlagenverhalten eines einzelnen Antriebs unter begrenzten Bedingungen erfassen. Der Herstellerwert 120 mA ist die **maximale Stromaufnahme**, keine bestätigte Blockier- oder Endlagenschwelle. KNX005/006 dürfen die Daten erst dann in Motorparameter übertragen.

**ETS-/KNX-Gate:** Separater Testplatz KNX018 mit angeschlossener Platine; KNX009/016 bleiben gemäß [Testbench-Konzept](KNX_TESTBENCH_PLAN.md) zurückgestellt. Der bisherige Desktop Agent ist kein physisch freigegebener KNX-Laborprüfstand.

## 4. Wiederholbarkeit und Test-Negativfälle

Vom Repository-Root auf dem Desktop Agent:

    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx022_hw_preflight.py --check-report docs\KNX022_STATIC_HW_PREFLIGHT.json
    C:\ASH\Tools\python-3.13.15\python.exe tests\test_knx022_hw_preflight.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_design.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py

Der Audit bricht mit einem **Fehler** ab, wenn sich kritische Netze, STBY, RP2040-Zuordnungen, 200-mΩ-/630-mA-Annotationen oder ATtiny-Target ohne neue Überprüfung ändern. Die Tests simulieren **15 unterschiedliche Driftfälle nur im Arbeitsspeicher** und bestätigen, dass eine MPN-Textkorrektur keine physische Sicherheitsfreigabe liefert.

**Interpretation:** Python Exitcode 0 bedeutet ausschließlich: Die **statische Quelle stimmt mit dem geprüften V1.2-Risikoregister überein**. Der gesonderte Status bleibt **BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR**. Kein Software-Audit kann die spätere Hardwaremessung ersetzen.

## KNX033 As-built-Foto-Nachtrag vom 13.10.2026

Inzwischen liegen reale Fotos der **Bestueckungsseite** der V1.2-Platine vor: [Foto-/Netzabgleich](KNX033_AS_BUILT_PCB_REVIEW.md). Der Nutzer meldet JMP1 geschlossen, JMP2/JMP3 jeweils nach oben und D1 als Drahtbruecke statt Diode. **Sichtbare F1 `T 2,5 A` statt Schemabeschriftung `630 mA`** ist ein neuer P0-Abweichungsnachweis. Die D1-Bruecke verbindet `5V` und `D1_1/U6 VIN` jetzt in beide Richtungen. U6-Bestueckung auf Rueckseite, R29-Istwert, U25-Signatur und Quellentrennung sind nicht gemessen. **Alle zehn elektrischen KNX022-Hardwareblocker bleiben offen, keine Power-On- oder Motorfreigabe.**
