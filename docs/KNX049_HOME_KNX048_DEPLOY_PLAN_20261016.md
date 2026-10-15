# KNX049 – KNX048-Firmwareupdate und passiver KNX-RX-Nachweis (LLO Home)

**Datum:** 16.10.2026 (MESZ). **Status:** Update-Image verifiziert, *Hardware-Flash gesperrt solange KNX-TP laut Nutzer angeschlossen ist*. Keine neue Write-Slice-Datei: `docs/slices/_OPEN_KNX042_MOTOR_LED_BRINGUP.md` bleibt einziger offener ASH-Slice.

## 1. Livezustand und verifizierter Softwarestand

- Agent LLO Home Windows, Version `0.7.9`, online. Neue KNX049-Write-Session, keine fremde aktive Session oder laufende Agent-Jobs bei Eröffnung.
- Repository `C:\_myspace\workspace\open-knx-valve-control`, `main` vor KNX049 auf `a32c654573d2d9be58b2ab155103bf4e1af7a074`, CLEAN; `origin/main=f647cec87ceb018329015eaf9b04fb87dceba765`. Zwei lokale Commits ahead, **kein Git-Push**.
- RP2040 über USB als `COM8`, VID/PID `2E8A:000A`, Seriennummer `E464401787522D33`; USB-Read-only-Status: `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0`.
- **Es läuft weiterhin KNX043 (alter 255-Einträge-Ring), nicht KNX048.** Die fehlenden neuen `capacity`, `observed`, `high_water`-Felder bestätigen, dass das neue Programm noch nicht installiert ist.
- KNX048-Image: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX048_RX_BUFFER_20261015\knx048-passive-rx-16k-NOT-FLASHED.uf2`, 166.400 Byte, 325 UF2-Blöcke, SHA-256 `af6aa0f228bb6b294bd31f35a3c68b8758afe2e3213da7344a7fffa5f236e70a`. Header/Blocknummern und Flash-Zieladressen unabhängig mit lokalem UF2-Prüfer PASS. Quellenhash und Host-Hash stimmen mit Bildmanifest überein.
- KNX043-Rollback-Image vorhanden: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX043_HOME_KNX_BENCH_20261014\knx043-passive-rx-only-NOT-FLASHED.uf2`, 146.432 Byte, 286 UF2-Blöcke, SHA-256 `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f`, Integritätsprüfung PASS.
- Regression KNX043/KNX048: **62/62 PASS**. ASH-Audit: **30/30 PASS**, 725 Markdown-Links. Die neue KNX048-Firmware war zuvor mit PlatformIO erfolgreich gebaut (RAM 140.160 von 262.144 Byte = 53,5 %). Das sind Offline-Ergebnisse, **kein echter KNX-RX-Test**.
- `docs/KNX043_HOME_KNX_GATE.json`: **0 von 17 physischen KNX-Sicherheitsgates verifiziert**; `BLOCKED_AWAIT_HARDWARE_EVIDENCE`.

## 2. Warum der KNX048-Flash jetzt ausgesetzt ist

Der Nutzer meldete zuletzt die **KNX-TP-Leitung angeschlossen**; ein späteres explizites Abklemmen ist **nicht** dokumentiert. Weitere KNX-Teilnehmer auf dem Strang funktionierten und am Line Gateway wurden Blinkimpulse beobachtet. Das ist ein Hinweis auf *Busaktivität*, kein Beweis für die Funktion von U9 Pin23 / GPIO1.

**Keinen Firmware-Reset oder BOOTSEL durchführen, solange KNX-TP angeschlossen ist**: KNX043/048 erzwingt GPIO0/KNX_TX LOW nur nach Start der Anwendung, nicht hardwareseitig bei Reset, ROM-BOOTSEL oder Brownout. Auf V1.2 sind zudem frühere U11-Überhitzung, mögliche Schäden an U9, R17-Padisolation, D1-Bypass, F1-Wert und USB/KNX-Rückspeisung ungeklärt. Ein weiter funktionierender Hausbus schließt lokale Risiken nicht aus.

Keine KNX-TX-Telegramme, keine `ARM LISTEN_ONLY`/`START LISTEN`-Kommandos, keine Motorsignale, kein Flash, kein Git-Push. Die Gate-Sperre des Host-Capture-Tools bleibt unangetastet.

## 3. Vorbereiteter Ablauf: USB-only-Upgrade nach physischer Trennung

1. **Nutzer vor Ort**: KNX-TP (+ und –) sicher von der V1.2-Platine abklemmen. Keine Motoren, keine Sensorleitungen/weitere Versorgung oder externes KNX-Netzteil an der Platine lassen; USB-C als alleinige Versorgungs- und Programmierschnittstelle. Bei sichtbarem Schaden oder Erwärmung zuerst spannungsfrei prüfen.
2. **Explizite Nutzerbestätigung** einholen: „KNX-TP vollständig getrennt, keine Motoren, keine externe Versorgung; ausschließlich USB-C“. Agent kann diese physische Trennung nicht aus COM8 erkennen.
3. Neue gültige Write-Session, Git-/USB-Gerätezustand, eindeutige RP2040-Identität, UF2- und Rollback-SHA erneut prüfen. **Kein automatischer Flash direkt aus der Chat-Übergabe**.
4. RP2040 **nur busfrei** unter Nutzeraufsicht in ROM-BOOTSEL bringen. BOOTSEL-USB VID/PID `2E8A:0003`, RP2040-Volume-Label `RPI-RP2` und `INFO_UF2.TXT` prüfen (historisch D:, Buchstabe neu feststellen).
5. Das **bereits verifizierte** KNX048-Image über offiziellen UF2-Massenspeicherweg kopieren. **Keine** KNX029-TPUART-Firmware verwenden. Nach ROM-Abmeldung Wiedererscheinen CDC VID/PID `2E8A:000A` und Seriennummer prüfen; bei Fehler nicht unkontrolliert wiederholen.
6. Auf neuem COM-Port `tools/knx043_rx_capture.py status --port <COM> --expect-serial E464401787522D33` ausführen. Neuer `STATUS` muss **`capacity=16383`** enthalten, mit `armed=0 listen=0`; damit wird die neue Firmware funktional erkannt. Keine KNX-Capture, kein Motorbetrieb.
7. USB-only-Ergebnis, Build-Hash, Flash-Transport, Port, Status und Rollback lokal protokollieren. **Keine Verbindung zum produktiven KNX-Bus** ohne separat geprüfte Hardwarefreigabe.

## 4. Danach: echter KNX-Empfang nur auf abgesichertem Teststrang

Erst nach R17/U9/U11-, TX-Reset-/Brownout-, F1/D1/JMP1-, VCCCORE/GPIO1-Pegel- und Versorgungsprüfung einen separaten, strombegrenzten KNX-TP-Teststrang mit geeignetem KNX-Netzteil/Drossel und unabhängigem KNX-Interface verwenden; USB-/GND-Gemeinschaftspfad qualifizieren. Die Hausbus-Schnittstelle `192.168.178.5:3671` ist kein isolierter Teststrang.

- Zunächst 30 s `tools/knx043_rx_capture.py capture` mit allen echten Host-Gate-Bestätigungen auf dem getrennten Teststrang. Während des Fensters am unabhängigen, sicheren Testbus gezielte bekannte Telegramme auslösen, z. B. von einem Testaktor/KNX-Testinterface; das RP2040-Programm bleibt **RX-only**.
- Erfolg nicht nur nach Anzahl „E“-Zeilen bewerten, sondern `capacity=16383`, `observed`, `dropped=0`, `high_water`, `buffered=0` nach Drain, vollständigem Host-Abgleich, ca. 35-µs-RX-Pulsbreiten und unabhängiger Busreferenz. Rohflanken alleine sind noch keine dekodierten KNX-Telegramme.
- Bei **0 Flanken trotz bewiesenem unabhängigem KNX-Verkehr**: V1.2 `JMP2`-Brücke und GPIO1-Kontinuität prüfen, U9 Pin23 / `KNX_RX` mit Oszilloskop gegen sicheren Board-GND messen, U9 VCCCORE/VCC_SEL und KNX-A/B-Buspegel prüfen (ohne 5-V-GPIO1), danach Firmware-Interrupt-Pin/ISR validieren. So trennen wir physisches U9-/Jumperproblem von Software-/USB-Problemen.
- Bei Flanken, aber `dropped > 0`/nicht vollständigem Abgleich: USB-Durchsatz, ISR-Latenz, Ringfüllstand, Windows-Treiber/CDC und Host-Reader getrennt untersuchen. 16K Ring ist ein Puffer, keine Garantie für Dauerverlustfreiheit.

**Freigabestatus:** `KNX048_IMAGE_READY, USB_FLASH_WAIT_PHYSICAL_DISCONNECT, KNX_TP_RX_NO_GO`. Keine Hardware-Prüffelder automatisch auf `true` setzen.
