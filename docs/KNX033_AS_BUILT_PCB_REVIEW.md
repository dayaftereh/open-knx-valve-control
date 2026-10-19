# KNX087-Bestueckungsnachtrag / 19.10.2026

R29 wurde vom Nutzer inzwischen ausdruecklich als **200 mOhm / 1 W tatsaechlich bestueckt** bestaetigt. Die aeltere fotobasierte Angabe unten (Wert nicht ablesbar) beschreibt nur den Pruefstand vom 13.10.2026; die widerspruechliche PCB-MPN SCR1206F1M1 ist daher nur noch ein Metadatenkonflikt. [Aktueller KNX087-Befund](KNX087_R29_200MOHM_1W_CONFIRMED_20261019.md).

---

# KNX033 – As-built-Sichtprüfung der bestückten V1.2-Platine (13.10.2026)

**Ergebnis:** Erste Fotodokumentation und Soll-/Ist-Netzabgleich verfügbar. **Kein elektrischer Freigabenachweis; bis zur Klärung der Versorgung und F1 ausdrücklich keine Bestromung, kein USB-/UPDI-Flash, keine KNX-Busspeisung und keine Motoren.** Dieser Eintrag ergänzt den statischen [KNX022-Preflight](KNX022_STATIC_HW_READINESS.md); er schließt keines seiner zehn realen Hardware-Gates.

## 1. Quellen, Fotos und Nachweisqualität

Die auf dieser Seite benannten originalen Nutzerbilder liegen als **Chat-Anhänge** vor, **nicht** als überprüfbar abgelegte Dateien im LLO-Home-Repository. Dateinamen und lokale SHA256-Hashes wurden zur späteren Reproduzierbarkeit im [maschinenlesbaren Istbericht](KNX033_AS_BUILT_PREFLIGHT.json) hinterlegt.

| Foto im Chat | Inhalt |
| --- | --- |
| `20261013_160055.jpg` | Detailbereich KNX-/USB-Eingang, F1, D1-Ersatzdraht, Q1, D3/D4/D6, JMP1/JMP2/JMP3, U23/INA219, R29 |
| `20261013_160046.jpg` | Bestückungsseite im Überblick, IC-Bestückung, Leiterplattenkennung V1.2 |
| `20261013_160042.jpg` | Zweite Aufnahme derselben Bestückungsseite |

**Unterschied strikt beachten:** Eine Benutzerangabe beschreibt eine eingebaute Brücke. Ein Foto zeigt eine Lötstelle. Eine Schaltplan-/PCB-Datei benennt das **beabsichtigte** Netz. Erst eine geeignete Durchgangsmessung zeigt, ob diese Netzverbindung tatsächlich sauber besteht und **keine ungewollten** Kurzschlüsse dazugekommen sind. Daher stehen alle Messfelder auf `null`.

## 2. Tatsächliche Bestückung versus V1.2

| Ref | Schematic / V1.2 | Beobachtung / Nutzerangabe | Bewertung |
| --- | --- | --- | --- |
| Platine | V1.2 | Silkscreen V1.2 und USB-C gut sichtbar | Fotos bestätigen Designgeneration, **keine elektrische DRC** |
| **D1** | 1N5819HW, Pad 2=`5V`, Pad 1=`D1_1` (U6 VIN) | **User:** Diode entfernt, Draht-/Lötbrücke installiert; sichtbare kurze blanke Kupferspitze | **P0:** Spannungsabfall reduziert, aber bisherige Rückwärtssperre aufgehoben. Freigabe erst nach Kurzschluss-/Quellentrenntest |
| **F1** | Schematicsoll 630 mA, Pad 1=`5V_`, Pad 2=`5V` | Aufschrift wirkt klar `T 2.5A ... AC250V` | **P0:** 2,5 A ist eine andere Nennstärke als 630 mA. Bestückungs-/Schutzkonzept und korrekte Sicherungscharakteristik zuerst klären |
| **JMP1** | `KNX_VCC` ↔ `R9_2`, KNX/Q1-Versorgungszweig | **User:** geschlossen; sichtbare Lötbrücke | **Stromlos messen.** Geöffnet/geschlossen entscheidet über Quellumschaltung – kein 5-V-Einspeisepunkt |
| **JMP2** | Pad 1 `KNX_RX'`, Pad 2 `KNX_RX`, Pad 3 `KNX_TX'` | **User:** »nach oben« gebrückt; zwei Pads sichtbar verbunden | Zu bestätigende Option: Pad 1–2 = RX gerade. Optische »oben«-Orientierung ist keine Pinprüfung |
| **JMP3** | Pad 1 `KNX_RX'`, Pad 2 `KNX_TX`, Pad 3 `KNX_TX'` | **User:** »nach oben« gebrückt; zwei Pads sichtbar verbunden | Zu bestätigende Option: Pad 2–3 = TX gerade. Gehäuse/Fotoorientierung kann anders aussehen als die Nummerierung |
| **U6** | TRACO TSR 1-2433, Pin 1 `D1_1`, 2 GND, 3 `3.3V` | Reglerkörper von dieser fotografierten Seite aus **nicht sicher identifizierbar** | Rückseite fotografieren und Bauteilbestückung mechanisch nachweisen, sonst **kein Power-On** |
| **U25** | Schematic/Firmware `ATtiny3216`, PCB-MPN historisch `ATTINY1616-SN` | Atmel 20-Pin-IC; Fotoaufschrift **scheint** `TINY3216` zu enthalten | Gute Vorinformation, vollständige Markierung/lesende UPDI-Signatur noch offen; **kein Blindflash** |
| **R29** | Soll 0,200 Ω zwischen `3.3V` und `M_VCC`, PCB-MPN `SCR1206F1M1` widersprüchlich | 2-Pad-Bauteil sitzt auf R29, Wert nicht ablesbar | Vierleitermessung bzw. verlässliche Bestückungs-BOM nötig; normale DMM-Beep-Funktion kann 0,200 Ω nicht beweisen |
| **U18/U16/U23** | RP2040, externer QSPI-Flash, INA219 | Bestückt sichtbar | Bauteilbeschriftung/Flashkapazität und I²C noch nicht elektrisch verifiziert |
| **U34/U36/U37/U35** | Vier TB6612FNG mit je 2 Motoren, STBY hart auf 3,3 V | Alle vier Gehäuse sichtbar | Keine unabhängige globale Motor-Abschaltung durch RP2040 in V1.2 – **keine Motorfreigabe** |

Die auf der Bestückungsseite sichtbaren Kontaktlöcher für Motoren, Temperaturfühler und UPDI sind **keine** nachgewiesenen angeschlossenen Anschlüsse. Rückseitenbestückung, solder voids, Kurzschlüsse unter IC-Gehäusen und Leckströme können aus den Frontfotos nicht bewertet werden.

## 3. D1-Brücke: Wirkung im Versorgungsweg

```text
USB-C VBUS / USB_VCC
  → D6 (Schottky, weiterhin im Strompfad)
  → 5V_ → F1 (auf Foto vermutlich T 2.5A)
  → 5V → [D1 entfernt: Drahtbrücke]
  → D1_1 = U6 Pin 1 (VIN)
  → U6 TSR 1-2433 → 3.3V → RP2040 / ATtiny / HMI
                            ↘ R29 → M_VCC → vier TB6612
KNX_VCC → JMP1 → R9_2 ↔ Q1-Auswahlpfad ↔ 5V_
```

Dadurch entfällt **der Vorwärtsspannungsabfall von D1**. Dies kann die früher kritische Reserve am U6-TSR-Eingang verbessern (U6 braucht laut Hersteller **mindestens 4,75 V VIN**). Allerdings wird `5V` nun **bidirektional mit `D1_1` verbunden**. Der D1-Schutz gegen umgekehrten Stromfluss existiert nicht mehr, während der Q1-/JMP1-/D6-Quellenpfad weiter separat geprüft werden muss.

**Nicht daraus schließen**, dass nun KNX und USB gleichzeitig gefahrlos verbunden oder eine externe 5-V-Versorgung einfach an ein vorhandenes Pad angeschlossen werden darf. Besonders wegen des geschlossenen JMP1 muss Rückspeisung zwischen KNX_VCC, USB_VCC, 5V_ und VIN qualifiziert werden. Der kurze blanke Drahtabschnitt an D1 darf bei Bewegung/Erwärmung kein benachbartes Pad/Leiterbahn berühren; optisch ausreichender Abstand ist noch keine Messung.

## 4. Unmittelbar möglicher Prüfabschnitt: stromlos

**Vor Beginn:** Alle Versorgungen, KNX-Bus, USB, UPDI-Adapter und alle acht Motoren/Temperaturfühler abgetrennt lassen; noch keine Spannung anlegen.

| Schritt | Erwartete Zuordnung gemäß V1.2 | Tatsächlicher Wert |
| --- | --- | --- |
| A. Rückseite fotografieren | U6 TSR 1-2433 auf tatsächlicher Lötseite identifizieren; vollständige U25-/U16-/F1-Markierung bestätigen | **offen** |
| B. F1-Bestückung/BOM | Originalplan 630 mA; Foto zeigt T 2,5 A. Sicherungstyp, Kennlinie, Nennstrom und Schutzfunktion vor Power-On klären | **offen, P0** |
| C. D1-Draht, stromlos | Nur Pad 1 `D1_1` ↔ Pad 2 `5V` niederohmig; keine neue Verbindung zu GND/D5/R7 oder anderen fremden Netzen | **offen, P0** |
| D. JMP1 | Pad 1 `KNX_VCC` ↔ Pad 2 `R9_2` leitend, kein Zinnkurzschluss zu Nachbarpads | **offen** |
| E. JMP2 | Für nicht gekreuzte RX-Variante Pad 1↔2 geschlossen, Pad 2↔3 offen; physische Padnummerierung mit PCB-Daten kontrollieren | **offen** |
| F. JMP3 | Für nicht gekreuzte TX-Variante Pad 2↔3 geschlossen, Pad 1↔2 offen; physische Padnummerierung mit PCB-Daten kontrollieren | **offen** |
| G. Versorgungsnetze | Grobe Kurzschlussprüfung `5V`–GND, `3.3V`–GND, `D1_1`–GND und `M_VCC`–GND; Messwert und DMM-Modus aufschreiben, keine pauschale Ohm-Freigabeschwelle | **offen** |
| H. R29 | Istwert / Teilecode zum geplanten 0,200-Ω-Shunt prüfen; 4-Leiter-Milliohmmessung oder belastbare Teileherkunft erforderlich | **offen** |

**Erst nach dokumentiertem Abschluss** dieser Punkte und unabhängiger Bewertung der Eingangsschutz-/Leistungsarchitektur folgt ein **separater KNX003-Power-Gate** mit geeigneter strombegrenzter, isolierter Laborversorgung **ohne Motoren**. Dann nacheinander und getrennt `USB_VCC`, `5V_`, `5V`, `D1_1/U6 VIN`, `3.3V`, `M_VCC` messen, Versorgungseinbrüche und Rückspeisung dokumentieren. Es gibt hier **keine pauschale Freigabe zum Einstecken des USB-Kabels**.

## 5. Offene Foto-/Messanforderungen an den Teststand

Bitte für den nächsten Abgleich ein **scharfes Foto der Platinenrückseite** (besonders U6/TSR-1-2433-Lötseite) sowie, falls möglich, Großaufnahmen von U25, F1 und R29 bereithalten. Am hilfreichsten sind später drei **spannungsfreie** DMM-Durchgangsergebnisse: D1 Pad 1↔2, JMP2 Wahlpad↔Mittelpad und JMP3 Wahlpad↔Mittelpad – zuzüglich Nachbarpad-Prüfung.

**Status:** `BLOCKED_NO_POWER_NO_FLASH_NO_MOTOR`. Hardware- und Firmwaretests [KNX018](KNX018_LAPTOP_UPDI_TESTBENCH.md), [KNX029](KNX029_FIRST_CONTACT_RUNBOOK.md), [KNX030](KNX030_PASSIVE_FIRST_CONTACT.md) bleiben bis zu echten Versorgungs-/UPDI-Messungen gesperrt; [KNX032](KNX032_UART_TO_KNX_OFFLINE.md) ist weiterhin nur ein Mock-Test.

## KNX034-Nachtrag – Rueckseite und vorgesehener JMP1-Umbau (13.10.2026)

Nach der ersten dreiseitigen Frontfoto-Aufnahme wurde ein **separates viertes Rueckseitenfoto** bereitgestellt. Das U6-Gehaeuse ist darin physisch vorhanden. Wichtig: Der Nutzer **schlaegt vor**, JMP1 zum USB-only-Betrieb zu oeffnen; das ist **noch nicht als Aenderung bestaetigt** und aendert den oben dokumentierten as-built-JMP1-geschlossen-Stand nicht rueckwirkend. [Aktueller KNX034-Entscheidungs-/Pruefplan](KNX034_USB_ONLY_PREPOWER_GATE.md) beschreibt DMM-Messungen und offene F1-/D6-/RUECKSPEISE-Gates. KNX033-JSON bleibt als historische 3-Foto-Evidenz unveraendert.
