# KNX030 – Passive Erstkontakt-Inventur auf LLO Home

**Stand: 13.10.2026.** Die OpenKNXValveControl-Platine ist noch nicht vollständig bestückt. Diese rein lesende Inventur hilft, ein später angeschlossenes RP2040- oder USB/UPDI-Gerät anhand **neuer Windows-Einträge** gegenüber dem vorherigen Zustand zu unterscheiden. **Keine elektrische Freigabe, kein Flash, kein KNX-Buszugriff.**

## 1. Bereits erfasster Ausgangszustand

Der erste echte, passiv erhobene Snapshot liegt **außerhalb des Git-Repositories** unter:

    C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-before-board-20261013.json

| OS-Datenquelle | Beobachtung bei der Baseline | Bedeutung |
| --- | ---: | --- |
| Vorhandene USB-/Port-PnP-Kandidaten | 15 | Bestehende PC-Peripherie; keine Zuordnung zur neuen Platine |
| Laufwerk mit Label RPI-RP2 | 0 | Kein Bootloaderlaufwerk über diesen OS-Check sichtbar |
| Lokale Netzwerkadapter-Einträge | 21 | Aktive/inaktive und virtuelle Adapter; kein KNX/IP-Nachweis |

Der Vorher-/Nachher-Vergleich der Baseline mit sich selbst ergab erwartungsgemäß **0 neue USB-/COM-Kandidaten, 0 neue RPI-RP2-Laufwerke und 0 Linkwechsel**. Die Baseline speichert **keine Roh-PnP-Instanz-IDs oder USB-Seriennummern**; nur deren SHA256-Hashes für den lokalen Vergleich. Keine IP- oder MAC-Adressen, keine Kommunikationsinhalte.

## 2. Befehle

Im PowerShell-Fenster auf LLO Home, bei vorhandenem Projekt:

    Set-Location 'C:\_myspace\workspace\open-knx-valve-control'
    $py = 'C:\Users\ll\.platformio\penv\Scripts\python.exe'
    $before = 'C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-before-board-20261013.json'
    $after = 'C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX030-home-after-usb-01.json'

    # Ohne Betriebssystem- oder Gerätezugriff: unterstützte Aktionen anzeigen
    & $py tools/knx030_passive_inventory.py plan

    # Erst NACH physischer Spannungs-/USB-Freigabe und mit abgeklemmten Motoren:
    # Nur Windows-Metadaten lesen; keinerlei COM-Port öffnen!
    & $py tools/knx030_passive_inventory.py capture --label after_usb --output $after

    # Zwei gespeicherte JSON-Dateien vergleichen, ohne OS-/Hardware-Abfrage:
    & $py tools/knx030_passive_inventory.py compare --before $before --after $after

**Wichtig:** capture überschreibt keine existierende Datei. Für jede Wiederholung einen neuen Dateinamen verwenden. Dateien sind bewusst nicht im Repository gespeichert. compare arbeitet vollständig offline mit den beiden JSON-Dateien.

## 3. Was die Erkennung erkennt – und was nicht

- **USB / COM:** Windows Get-PnpDevice -PresentOnly liefert registrierte Ports, USB-Geräte und bestimmte USB-Speichereinträge. Ein neuer COM5-Eintrag kann z. B. ein USB/UPDI-Adapter sein; der Gerätevergleich kann die physische Leitung oder 3,3-V-Pegel **nicht** nachweisen.
- **RP2040:** Eine neue Vendor-ID 2E8A oder ein Laufwerklabel RPI-RP2 wird nur als **RP2040-/BOOTSEL-Kandidat** gemeldet. Sie beweist weder die korrekte V1.2-Platine noch bestückte Flashgröße, USB-Stabilität, KNX-Konfiguration oder sicheres Flashen.
- **ATtiny:** Das Programm öffnet **keinen** UPDI-Port und liest **keine** Chip-Signatur. U25 ist in der Software als ATtiny3216 konfiguriert; die PCB-Teilemetadaten enthalten aber ATtiny1616. Der reale Chipaufdruck und später eine freigegebene read-only UPDI-Signatur sind entscheidend.
- **KNX:** Get-NetAdapter liest ausschließlich lokale Netzwerklink-Metadaten. Adapterstatus Up bedeutet **nicht**, dass ein KNX/IP-Gateway erreichbar ist. Kein Multicast-Suchtelegramm, keine KNX-Adresse, kein UDP/TCP-Verbindungsversuch und kein ETS6-Download werden durchgeführt.
- **Motoren:** Keine GPIOs oder Aktoren werden angesprochen. Die auf V1.2 fest an 3,3 V liegenden TB6612-STBY-Pins und die offenen KNX022-Sicherheitsblocker bleiben unverändert.

Das Ergebnis darf **niemals** den Status einer elektrischen Freigabe, Programmierfreigabe oder Motorfreigabe auf true setzen. Diese Entscheidung erfolgt ausschließlich in getrennten Hardware-Gates.

## 4. Empfohlene Reihenfolge beim späteren Aufbau

1. **Stromlos / ohne USB:** V1.2-Bestückung anhand Fotos und BOM prüfen: U25-Beschriftung, R29, F1, U6, Q1/JMP1, Flash-IC, CN1/Pin1 und Motorversorgungsverdrahtung. Keine Motoren anschließen.
2. **Labor-Power-Gate:** Erst nach Fachprüfung USB-/KNX-Versorgungswege, 5-V-/3,3-V-Spannungsniveau, CN1/UPDI-Pegel sowie Rückspeisung mit geeigneter strombegrenzter Versorgung messen. Bei Abweichung nicht weiter anschließen.
3. **RP2040 / USB:** Wenn USB elektrisch freigegeben ist, einen einzigen Kandidaten anstecken, capture erneut ausführen und gegen die Baseline vergleichen. Änderungen identifizieren einen **möglichen** Port, lösen aber keinen Reset aus.
4. **ATtiny / UPDI:** Für den getrennten Programmer denselben Vergleich wiederholen. Zuvor CN1-Pin1 und Pegel qualifizieren, U25 optisch prüfen; die UPDI-Gerätesignatur ist später separat nur lesend zu erfassen.
5. **KNX / ETS6:** Nach Bus- und Power-Gate den KNX/IP-Testanschluss und eigenen KNX-TP-Testbus separat prüfen. Eine lokale Netzwerkschnittstelle reicht nicht aus.
6. **Temperaturprüfung:** Erst nach bestätigtem RP2040-/ATtiny-Boot und sicheren Links T0 und dann T1..T8 über UART/CRC/DPT9.001 beobachten. Hardwaremotoren bleiben bis KNX004–006 gesperrt.

Die beiden bereits offline kompilierten Images und ihr Hash-Manifest liegen in [KNX029](KNX029_FIRST_CONTACT_RUNBOOK.md). Die physischen Voraussetzungen und zehn bestehenden Sicherheitsblocker stehen in [KNX022](KNX022_STATIC_HW_READINESS.md); der Testaufbau ist in [KNX018](KNX018_LAPTOP_UPDI_TESTBENCH.md) beschrieben.

## 5. Entwickler- und Prüfnachweise

tools/test_knx030_passive_inventory.py prüft künstliche Geräteschnappschüsse. Tests umfassen fehlende Windows-Daten, unbekannte Kandidaten, neue COM-Ports und BOOTSEL-Laufwerke, manipulierte Freigabefelder, gespeicherte Instanz-ID-Vertraulichkeit, vorhandene Ausgabepfade und den strikt subprocess-freien compare-Pfad. tools/audit_knx030_passive_scope.py prüft eingefrorene Firmware-/ETS-/PCB-Dateien und verbotene Befehle im OS-Erhebungsskript.

Jeder echte Windows-Snapshot ist lediglich ein Zeitpunkt. Während eines Systemupdates oder bei anderer USB-Peripherie können Änderungen nichts mit OpenKNXValveControl zu tun haben. Deshalb jeweils nur ein bekanntes Gerät ändern und die Differenz manuell bewerten.
