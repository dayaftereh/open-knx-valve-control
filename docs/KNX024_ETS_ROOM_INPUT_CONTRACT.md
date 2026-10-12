# KNX024 – ETS-Raumdatenvertrag und sicherer Offline-KO-Adapter

**Stand:** 12.10.2026. **Abnahmetyp:** nur Software-/Schema-Tests plus isolierter RP2040-Firmware-Build. Keine produktive ETS-AppVersion3, keine echten KNX-Telegramme, keine Motor-GPIO, kein Flash.

**KNX025 Weiterfuehrung:** [Fault-/Recovery-Supervisor](KNX025_FAULT_RECOVERY_DIAGNOSTICS.md) prueft im portablen Simulator KNX024-Telegrammfehler, Stale-Quellen, softwareseitige ACK-Leases und manuell quittierten Wiederanlauf. Keine ETS6-/KNX- oder Motorfreigabe.

Die [KNX008-Zonenplanung](KNX008_ZONE_CHANNEL_DESIGN.md) wird in einen portablen, strikt typisierten KNX-Eingangsadapter umgesetzt und mit dem [KNX023-Regler](KNX023_FIRMWARE_SOFTWARE_RUNTIME.md) offline verbunden.

## 1. ETS-KO- und Parametervorschlag

Maschinenlesbarer Vertrag: [KNX008 ETS-V3 Proposal JSON](../assets/knx008_zone_ets_proposal.json). Gilt ausdrücklich nur als **PROPOSAL**, kein tatsächlich importiertes ETS-Produkt.

| Zone | Raum-Soll RX DPT9.001 | Raum-Ist RX DPT9.001 | Direkt RX DPT5.001 | Stellanforderung TX DPT5.001 |
| --- | ---: | ---: | ---: | ---: |
| Z1 | 36 | 37 | 38 | 39 |
| Z2 | 40 | 41 | 42 | 43 |
| Z3 | 44 | 45 | 46 | 47 |
| Z4 | 48 | 49 | 50 | 51 |
| Z5 | 52 | 53 | 54 | 55 |
| Z6 | 56 | 57 | 58 | 59 |
| Z7 | 60 | 61 | 62 | 63 |
| Z8 | 64 | 65 | 66 | 67 |

KOs36–67 sind **32** geplante Zonen-Objekte; davon **24 RX** und **8 nur TX**. Weitere 33 geplante KOs68–100 für Motor/Diagnose werden in diesem Slice weder gelesen noch interpretiert. P22–P29 sind die acht Zonenmodi, P30–P37 die acht Motor-Zonen-Zuordnungen, P38/P39 die vorgeschlagenen Eingangstimeouts für Raum-Soll/Ist (900 s) und direkte Prozentwerte (300 s), jeweils 30–3600 s.

**Strikte Kompatibilität:** Das produktive ETS-V2-XML bleibt mit **KO1–35 und P1–21 unverändert**. Insbesondere sind **KO17–24 weiterhin DPT 5.004**. Das neue DPT 5.001 darf diesen alten Objekten weder zugewiesen noch stillschweigend durch eine Bytekonvertierung unterstellt werden.

## 2. Bytekodierung gemäß KNX-Standard

| DPT | Format | Beispiel |
| --- | --- | --- |
| 9.001 Temperatur | 2 Bytes, big-endian: Bit15 Vorzeichen, Bits14–11 Exponent, Bits10–0 Mantisse. Centigrad = signierte Mantisse × 2^Exponent. Der Sonderwert **0x7FFF bedeutet ungültig** | 0x07D0 = 20,00 °C; 0x0C7E = 23,00 °C; 0x879C = −1,00 °C |
| 5.001 Scaling | 1 Byte, 0–255 entspricht 0–100 %. Software-Umrechnung auf Permille gerundet | 0 = 0 %, 128 ≈ 50,2 %, 255 = 100 % |
| 5.004 Percent_U8 | 1 Byte, 0–255 bedeutet 0–255 Prozentpunkte, **nicht** Scaling | 0x32 = 50 %, bei 5.001 nur ca. 19,6 % |

Quelle: KNX Association, [System Specifications v02.02.01, Datapoint Types](https://support.knx.org/hc/zh-cn/article_attachments/15392631105682), Abschnitte 3.5 und 3.10.

Die bisherigen, konservativen [KNX008-Raum-Plausibilitätswerte](../lib/common/heating_zone_model.hpp) sind unabhängig vom DPT: Soll-Raumtemperatur **5,00…35,00 °C**, Raum-Ist **−40,00…80,00 °C**. Empfangene 0x7FFF, unplausible Temperaturen oder Größenüberläufe werden invalidiert und **nicht gekappt**.

**DPT-Grenze:** Ein reales KNX-GroupValueWrite-Telegramm trägt **keine DPT-Typ-ID**. Die übergebene DPT-Angabe ist daher eine **vertrauenswürdige Software-Metadateninformation aus der späteren ETS-/GA-Zuordnung**, nicht aus dem Bus dekodierte Evidenz. Eine reale, falsch als 5.004 konfigurierte GA kann bei identischer Bytezahl ohne externe Konfigurationsprüfung nicht zuverlässig erkannt werden. Die unabhängige ETS6-/GA-Prüfung bleibt erforderlich.

## 3. Implementierter rein portabler Adapter

[knx024_room_dpt_adapter.hpp](../lib/common/knx024_room_dpt_adapter.hpp) arbeitet vollständig im RAM. Der DPT-Dekoder erhält nur bereits extrahierte Applikationspayloads, also **keine** cEMI/APDU-Header und **keine** KNX-Gruppenadresse.

- **Start und Konfiguration:** Der Adapter beginnt unkonfiguriert. Eine valide, ausdrücklich per Software gesetzte KNX008-Modus-/Zuordnungs-Konfiguration startet eine neue Epoche und löscht alle alten Raum-/Direktinputs. Ohne Konfiguration keine akzeptierten Nachrichten. Ändert ein anderer Code die Laufzeitkonfiguration hinter dem Adapter, wird der Datenpfad fail-closed invalidiert.
- **Nur GroupValueWrite auf bekannten RX-KOs:** Empfang wird ausschließlich für die vorgeschlagenen Soll-/Ist- und direkten Prozent-KOs für Z1…Z8 akzeptiert. Antworten, Leseanfragen, die geplanten TX-KOs39/43/…/67, alle alten KO1–35 und alle geplanten Motor-KOs68–100 werden ignoriert.
- **Mode-Autorität:** RoomTemperature akzeptiert nur externen Raum-Soll-/Istwert, DirectPercent nur DPT5.001. Deaktivierte und zum aktuellen Modus unpassende Telegramme erzeugen niemals neue Ziele.
- **Fehlertoleranz:** Ein fehlerhafter, zum aktiven Modus gehörender RX-Kanal (falsche Typdeklaration, Payloadlänge, ungültige Zahlen, außerbereichige Temperatur) wird gelöscht; der nächste Software-Tick invalidiert die daraus resultierenden Regelziele. Unbekannte Objekte können den gültigen Zustand nicht überschreiben.
- **Zeitfenster:** Gültig/fresh sind nur passende Signale unter dem konfigurierten Raum- oder Direkttimeout. Die bestehenden KNX008-/KNX019-Algorithmen berücksichtigen den 32-bit-Millisekundenüberlauf. Kein automatisches Wiederaufleben nach Moduswechsel, Reboot oder Timeout.
- **Ausgangsobjekt nur simuliert:** Ein Ausgangs-Byte für KO39/43/…/67 wird ausschließlich bei gültigem aktuellem Software-Tick und fresh Inputs berechnet. Das ist eine **Sollwertanforderung**, weder gemessene Motorposition noch hydraulischer Durchfluss. Der Adapter ruft keine KNX- oder Hardwarefunktion auf.

Der [KNX023-Runtime-Header](../lib/common/room_control_runtime.hpp) erhält nur zwei unveränderliche C++-Accessor-Overloads. Der [RP2040-Einstiegspunkt](../src/controller/main.cpp) inkludiert den neuen Header und prüft per Compile-time-Assertion die vorgeschlagene KO36–67-Spanne. **Er registriert keinen Buscallback und benutzt keines dieser Objekte aus der produktiven ETS-V2-App**, weil sie dort noch nicht existieren. Die reale Firmware-DPT5.004-Altzuordnung bleibt unberührt.

## 4. Reproduzierbare Offline-QA

| Artefakt | Zweck |
| --- | --- |
| [Native KO-/DPT-Test](../tests/native/test_knx024_room_dpt_adapter.cpp) | 8×4-KO-Matrix, korrekte DPT9-Vorzeichen/Exponent/0x7FFF, falsche Größen und Typen, DPT5.001/5.004-Trennung, Modus-/Topologie-/Timeoutfälle, negative Temperatur und 32-bit-Wrap |
| [Arduino-Motor-Hardlock-Test](../tests/native/test_knx024_firmware_hardlock.cpp) | Gültiger, synthetischer DPT5-Eingang berechnet RAM-Target, darf aber keine Motorfreigabe oder GPIO-Aktivität erzeugen |
| [Native Runner](../tools/test_knx024_room_dpt_adapter.py) | Beide C++17-Suites mit strikten Compilerwarnungen |
| [ETS-/Produkt-Schema-Audit](../tools/audit_knx024_room_ets_contract.py) | Prüft präzise 65 vorgeschlagene KOs36–100 und 18 Parameter P22–39, bewahrt produktive V2-XML/PCB/ATtiny/Modelle und zeigt nur erlaubte additive Firmwareänderungen |
| [13 Schema-Negativtests](../tests/test_knx024_room_ets_contract.py) | Mutiert nur Speicher-Kopien, um falsche DPTs/KO-Nummern/Modi/Richtungen/Prozentwerte/Parameter-Promotion abzuweisen |
| [Isolierter RP2040-Build](../tools/build_controller_isolated.py) | OpenKNXproducer und PlatformIO nur im separaten temporären Arbeitsverzeichnis, Quellheader-Hash unverändert, UF2 wird nicht geflasht |

Testbefehle aus dem Repository-Root:

    C:\ASH\Tools\python-3.13.15\python.exe tools\test_knx024_room_dpt_adapter.py
    C:\ASH\Tools\python-3.13.15\python.exe tests\test_knx024_room_ets_contract.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx024_room_ets_contract.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_knx008_zone_contract.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\build_controller_isolated.py
    C:\ASH\Tools\python-3.13.15\python.exe tools\audit_ash_workflow.py

## 5. Noch gesperrte Schritte

Der echte ETS-V3-Produktimport, Gruppenadressierung, Parametermigration und Live-KNX-Eingänge sind für [KNX018 Laptop-/KNX-UPDI-Testbench](KNX018_LAPTOP_UPDI_TESTBENCH.md) und die bewusst zurückgestellten KNX009/016-Gates offen. KOs36+ sind **noch nicht** im realen Produkt.

KNX002/003/004/005/006 (Bestückung, Spannungsversorgung, unabhängige All-off-Abschaltung, Strom- und Hub-/Referenzmessungen) bleiben echte Hardware-Gates. Auf V1.2 liegt TB6612-STBY fest an 3,3 V. [KNX022 Hardware-Preflight](KNX022_STATIC_HW_READINESS.md) hat zehn ungelöste Befunde, der Status lautet weiterhin **BLOCKED_NOT_SAFE_TO_ENERGIZE_MOTOR**.

Der KNX023-ARDUINO-Hardlock bleibt aktiv. Kein Software-DPT-Test ist eine Freigabe, einen Motor zu bestromen.


## 6. Tatsächliches KNX024-Gate-4-Ergebnis (12.10.2026)

- **Zwei neue native C++-Suites PASS:** vollständiges KO36..67-/DPT9.001- und DPT5.001-Frame-Mapping, Fehler/Alter/Neu-Konfiguration, synthetische PI-Raum-Stellwerte sowie realer ARDUINO-Präprozessorpfad ohne Motorfreigabe.
- **15 bestehende native C++-Suites PASS:** KNX008 (1), KNX013 (2), KNX014 (4), KNX015 (2), KNX019 (1), KNX020 (2), KNX021 (1), KNX023 (2). **Insgesamt 17 Native-Suites bestanden.**
- **13 zusätzliche Python-Schema-Negativtests PASS**, etwa falscher DPT5.004 statt 5.001, falscher KO-Index, falsches P38/P39, ungültige ETS-Promotionsbehauptung.
- **KNX024 ETS-/Quell-Audit PASS**, auch vorheriger KNX023 Nichtansteuerungsaudit PASS. KNX008 ETS-Proposal und produktives KNX015-V2-ABI PASS. Das produktive ETS-XML, knxprod.hpp, Temperatur-ATtiny und PCB V1.2 blieben unverändert.
- **Isolierter RP2040 PlatformIO-Build PASS** nach Einbindung des neuen Headers; UF2 im temporären Build-Root C:\Users\LLO\AppData\Local\Temp\openknx-controller-isolated-jq6g6jji\.pio\build\controller\firmware.uf2. **Kein Flash.** RAM **53.452/262.144 = 20,4 %**, Flash **192.708/1.048.576 = 18,4 %**, kanonisches include/knxprod.hpp unverändert.
- **KNX022-Hardware-Quellenaudit weiterhin 35 PASS mit Readiness BLOCKED und 10 realen offenen Punkten**, u. a. STBY fest HIGH. PCB/ETS-Design-Static-Audit 0 Invariantfehler; Warnungen bleiben.
- **ASH 30 Checks, 427 dokumentierte lokale Markdownlinks vor Closing PASS**. Closing-Audit nach Markerentfernung wird wiederholt. Kein KNX-/ETS6-/USB-/Motor-/GPIO-Zugriff und kein GitHub-Push.

Alle Angaben beziehen sich ausschließlich auf Software- und Build-Verifikation. Es ist kein physisches Ventil und kein KNX-Gruppenadress-Test freigegeben.
