# KNX034 – Rueckseite V1.2 und geplanter USB-only-Erstkontakt (JMP1 offen)

**Stand:** 13.10.2026. **Status:** `PROPOSED_NOT_APPLIED` – das Öffnen von JMP1 wurde vom Nutzer vorgeschlagen, **nicht** als ausgeführt bestätigt. **Hardware-Freigabe:** `BLOCKED_NO_POWER_NO_FLASH_NO_MOTOR`.

## 1. Neues reales Foto / was wir sehen

Das vierte Nutzerfoto `20261013_164325.jpg` zeigt die zweite Platinenseite (Datei-SHA256 `932bfac8982d03ebee0e23087a8da03d7480d40fc89b5677eec800fb3d392e82`). Original liegt **nur im aktuellen Chat**; im Repository sind ausschließlich Quell-/Foto-Metadaten dokumentiert.

Auf der Seite sind folgende Elemente sichtbar:

- **U6 ist physisch bestückt.** Am Rand der Platine steht `U6`; neben dem schwarzen Block sind die `5V`- und `3.3V`-Markierungen erkennbar. Das beseitigt den offenen Punkt aus [KNX033](KNX033_AS_BUILT_PCB_REVIEW.md), ob überhaupt ein U6-Bauteilkörper auf der zweiten Seite zu sehen ist. **Die Aufschrift des Moduls ist nicht lesbar; TSR 1-2433, Pinbelegung, korrekte Lötung und 3,3-V-Ausgang bleiben elektrisch unbestätigt.**
- **CN1 2×3** auf dieser Seite bestückt; außerdem RUN, PROG und USB_BOOT-Taster. Die vorgesehene UPDI-/5-V-Pinbelegung wurde nicht elektrisch getestet; **kein UPDI-Kabel anschließen**.
- LCD-/HMI-Bereich und zahlreiche externe Anschlusspositionen wirken nicht vollständig bestückt; daraus weder durchgängige Funktion noch Fehlbestückung ohne Bauplan-Abgleich ableiten.

Das neue Foto macht den **körperlichen U6-Installationsnachweis plausibel**, ersetzt aber keine elektrischen Sicherheitsprüfungen.

## 2. Iststand, Vorschlag und reale Strompfade

**Letzte bestätigte Benutzerangabe:** `JMP1 geschlossen`, `JMP2/JMP3 jeweils nach oben gebrückt`, `D1 ausgelötet und durch Draht ersetzt`. **Neuer Vorschlag:** `JMP1 wieder öffnen`.

Aus dem originalen [V1.2 PCB JSON](../schematic/pcb_knx-valve-control_v1.2.json):

| Ref | Pins / Netze | Bedeutung für Test |
| --- | --- | --- |
| JMP1 | 1 = `KNX_VCC`, 2 = `R9_2` | Geöffnet unterbricht den gewollten KNX-Versorgungsanschluss an Q1-Drain/R9_2 |
| Q1 | 1 = `USB_VCC`, 2 = `5V_`, 3 = `R9_2` | MOSFET im Quellenwahlzweig; sein Verhalten nicht durch JMP1 allein abgenommen |
| R9 | 1 = GND, 2 = `R9_2` | 100-kΩ-Pulldown auf Seite Q1-Drain |
| D6 | 2 = `USB_VCC`, 1 = `5V_` | USB-Schottky bleibt, mit Forward-Drop |
| F1 | 1 = `5V_`, 2 = `5V` | Auf Foto **T 2,5 A** statt Soll **630 mA** |
| D1 (Draht) | 2 = `5V`, 1 = `D1_1` | Ursprüngliche Diode entfernt; bidirektionaler Leiter statt Richtungs-Sperre |
| U6 | 1 = `D1_1`, 2 = GND, 3 = `3.3V` | Soll: TRACO TSR 1-2433, mindestens 4,75 V an VIN |

Bei **JMP1 offen** und **KNX-Bus vollständig abgeklemmt** wäre die vorgesehene externe Energiequelle für den 3,3-V-Wandler USB, nicht KNX:

```text
USB-C VBUS -> USB_VCC -> D6 -> 5V_ -> F1 -> 5V
                                           |
                                 D1 durch Draht ersetzt
                                           |
                                   D1_1 / U6 VIN
                                           |
                                       U6 -> 3.3V

KNX-Versorgungszweig:
KNX-Bus -> STKNX/U9 Buck -> KNX_VCC  [JMP1 OFFEN]  R9_2 / Q1
                                         ^ Unterbrechung dieses Zweiges
```

**Wichtige Einschränkungen:**

1. Bereits **ohne KNX-Busanschluss** ist USB die einzige angeschlossene externe Quelle – unabhängig davon, ob JMP1 noch geschlossen ist. JMP1 zu öffnen verhindert zusätzlich den vorgesehenen KNX-Versorgungseinspeisepfad über diesen Zweig; es ist daher für einen separaten Laborversuch zweckmäßig, aber nicht die einzige Voraussetzung.
2. **Keine galvanische Trennung.** `KNX_B`, GND sowie Bus-/Logiksignale sind im V1.2-Schema anderweitig miteinander verbunden. Eine später angeschlossene KNX-TP-Leitung kann deshalb trotz offenem JMP1 Potential- und Rückspeise-/Masseprobleme verursachen. Eine tatsächliche USB/KNX-Gemeinschaftsversorgung benötigt einen eigenen Nachweis.
3. Die D1-Brücke beseitigt den zweiten Vorwärtsspannungsabfall, **D6 bleibt aber noch vorgeschaltet**. Bei niedrigem USB-Eingang oder Lastabfall kann U6 VIN weiterhin **unter 4,75 V** sinken. Netzteil-/Portnennspannung 5,0 V ist kein gemessener VIN-Wert.
4. Die sichtbare **F1 T 2,5 A statt 630 mA** ist **nicht durch Öffnen von JMP1 behoben**. Eine falsch dimensionierte Schutzsicherung kann Leiterbahnen und USB-Leitungen unzureichend schützen; vor Energieeinspeisung den tatsächlich vorgesehenen Fuse-Wert, Trägheit, Abschalt-/I²t-Charakteristik und zulässige Energiequelle anhand Strombudget und BOM prüfen.
5. U25-Identität, M_VCC-Shunt R29, UPDI 3,3-V-Pegel/CN1.1 (5 V) und alle motorischen STBY-/Reset-Gates bleiben offen.

## 3. Konkreter stromloser JMP1-Änderungs- und Messplan

**Voraussetzung:** Keine USB-, KNX-, UPDI-, Laborstromversorgungs- oder Motorverbindung; Kondensatoren entladen lassen. Bei Verwendung eines Lötkolbens ESD- und Platinenschutz beachten.

| Reihenfolge | Prüfumfang | Erwartung / dokumentierbarer Nachweis |
| --- | --- | --- |
| 1 | Vor dem Trennen: Ist JMP1 tatsächlich noch leitend? | V1.2 Pad1 `KNX_VCC` ↔ Pad2 `R9_2` mit DMM messen; protokollieren |
| 2 | JMP1 bei ausgeschalteter Hardware öffnen (Lötbrücke entfernen) | Kein Pad angehoben, keine Nachbarbahn beschädigt |
| 3 | Nachher JMP1 Pad1 ↔ Pad2 erneut stromlos messen | **Keine niederohmige Brücke** zwischen `KNX_VCC` und `R9_2`; DMM-Ohmwert/OL dokumentieren; Bauteile können Parallelpfade verursachen, also kein automatischer Unendlichkeitsnachweis |
| 4 | `KNX_VCC` ↔ `5V_` und `5V` bei getrennten Quellen prüfen | Kein unerwarteter niederohmiger Durchgang; Verhalten der Halbleiter beeinflusst DMM-Messwerte; im Zweifel Schaltplan-/Diodenmodus gegenprüfen |
| 5 | D1-Ersatzdraht: `5V` ↔ `D1_1`, nahe D5/R7/GND | Nur gewollte Brücke niederohmig; kein benachbarter Kurzschluss, keine blanke Spitze frei beweglich |
| 6 | F1 | Endgültige Sicherungsidentität und Schutzkoordination zur beabsichtigten Strombegrenzung **vor** erster Spannung klären |
| 7 | Stromlose Kurzschluss-/Sichtprüfung 5V-GND, D1_1-GND, 3.3V-GND, M_VCC-GND | DMM-Werte mit Betriebsart protokollieren; Kondensatorladung und Halbleiterpfade beachten; keine willkürliche Ohm-Grenze als Freigabe verwenden |

**Noch nicht durchführen:** USB-C anschließen, KNX-TP verbinden, ATtiny-UPDI-Programmer anstecken, Motoren aktivieren oder Firmware flashen. Der nächste **separat freizugebende KNX003-Erstspannungstest** erfolgt erst nach abgeschlossener F1-/D1-/U6-/Quellenprüfung, mit geeigneter Strombegrenzung und ausdrücklich ohne Motoren. Dann U6 VIN (mindestens 4,75 V laut Datenblatt) und 3,3-V-Ausgang unter definierter Logiklast nachmessen sowie das Fehlen von Rückspeisung überprüfen.

## 4. Status

- **KNX034 Dokumentation:** Rückseitenfoto und vorgeschlagener USB-only-Pfad bewertet.
- **JMP1 offen:** **Noch NICHT bestätigt oder gemessen.**
- **U6 Bauteilgehäuse auf Rückseite:** **Sichtbar**; Typ, Versorgung, Lötstellen und Ausgang nicht geprüft.
- **F1 2,5 A gegen 630 mA:** **P0 offen.**
- **USB-only Power-On, KNX, UPDI/USB-Flash und Motor:** **NICHT freigegeben.**

Der historische [KNX033-Fotobericht](KNX033_AS_BUILT_PCB_REVIEW.md) bleibt als damaliger Drei-Foto-/JMP1-geschlossen-Iststand unverändert. Sobald JMP1 tatsächlich entfernt und stromlos gemessen wurde, werden die **neuen realen DMM-Werte** als separater Nachtrag erfasst – nicht aus einer Sollverbindung abgeleitet.
