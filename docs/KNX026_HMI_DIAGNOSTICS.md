# KNX026 – Read-only HMI und Softwarediagnose

**Stand:** 12.10.2026. **Status:** software-only. Kein Hardware-Release, kein freigeschalteter Motor, kein ETS6-/KNX-Bustest.

## Quellen und tatsaechliche HMI-Hardware

Die V1.2-PCB-Statik erkennt eine LCD-PCF8574-I2C-Schaltung an einem gemeinsamen I2C-Bus. Im Controller steht in `src/controller/config.hpp` HMI Button D2, Encoder A D6 und B D7. In der bisherigen Firmware fehlten aber ein verifizierter Displaytreiber und die Encoder-Auswertung. **KNX026 behauptet keine fertige physische LCD- oder Encoder-Ansteuerung.** Die konkrete LCD-Ausfuehrung, Adressierung, Pin/Bestueckung und Stromversorgung sind am Teststand vor spaeterer GPIO-Bindung zu pruefen.

## Datenquellen

- `lib/common/knx026_hmi_diagnostics.hpp`: fester portabler `Snapshot`, `capture()`, `Menu` mit sechs Seiten. Keine Arduino-, KNX-, GPIO- oder Displaytreiber-Abhaengigkeit.
- `lib/common/knx025_fault_supervisor.hpp`: **massgebliche** Fehlerphase, `firstFault`, 1-basierte Zone und erster Fehlerzeitpunkt, Warnung, Kommunikationszustand, synthetische Motorqueue. Keine zweite Fehlerlogik.
- `lib/common/room_control_runtime.hpp`: aktuelle Zonen-/Motorzuordnung, externe Raum-Soll-/Ist-Eingaenge, PI-Softwarestatus, angeforderte Stellwerte (nur Absicht). Ein Fault macht die angezeigte Anforderung ungueltig, selbst wenn alter Cache ueberbleibt.
- `TemperatureBridge` + `TemperatureProtocol`: **T0 = Vorlauf und T1..T8 = acht Ruecklaeufe**; Kanalgueltigkeit/Alter/Fehler und UART online/offline. **Keiner dieser Kanaele ist die Raum-Isttemperatur**.
- `src/controller/main.cpp`: passive `hmiSnapshot`-Aktualisierung im bestehenden 100-ms-RAM-Pfad. Es gibt keinen Aufruf eines Encoder-GPIO, KNX GroupObject, LCD-Treibers, Motor-GPIO oder Motorfreigabe.

## Ansichtsmodell und Navigation

| Seite | Angezeigte Informationen | Wichtige Einschraenkung |
| --- | --- | --- |
| Overview | Software-/Fehlerstatus, Hardwareblocker | Kein Sicher-Aus-Nachweis |
| Water | T0 und T1..T8, Temperatur/Alter/Gueltigkeit/Fehler | Offline-Werte niemals als frisch etikettieren |
| Zones | Z1..Z8, Zone-Motor-Masken, PI oder Direktmodus, externe Soll-/Isttemperatur, Stellanforderung | DPT5.001-Skalierung nur fuer den vorgeschlagenen Raumvertrag |
| Motors | M1..M8, zugeordnete Zone, Softwareziel, gegebenenfalls nativer virtueller Positionswert | **Reale Motorposition stets unbekannt**; fehlende Referenzierung |
| Links | KNX-Raumtransport und ATtiny-UART getrennt | KNX-V2-Raumtransport ohne Monitor ist *unknown*, nicht online |
| Faults | KNX025-Phase, latched Fehlercode/Zone/Zeit, Queue/Warnungen | Keine HMI-Quittierung oder Resetfunktion |

Der portable `Menu` verarbeitet nur simulierte Encoder-Detents (`rotate`) und Tastendruecke (`press`), ohne Aktionscode zum Quittieren, Schreiben oder Fahren.

## Gueltigkeit und Sicherheitsvertrag

- `Unknown` ohne Sample/Kommunikationsnachweis, `Fresh` nur bei nachweislich gueltiger aktiver Quelle, `Stale` bei abgelaufener Quelle oder offline Transport, `Invalid` bei Fehler/ungueltigem Inhalt.
- Timer fuer KNX-Raumdaten basieren auf den tatsaechlichen KNX008 `roomTimeoutSeconds` und `directTimeoutSeconds`; 32-Bit-Zeitumbruch wird durch unsigned-Differenzen beruecksichtigt.
- Native `virtualPositionPermille` ist **synthetische** KNX021-Bewegungsevidenz, kein realer Endanschlag/Referenzpunkt. Unter `ARDUINO` ist das virtuelle Backend entfernt und der Zustand bleibt unbekannt.
- `hardwareDriveBlocked=true`, `actualPhysicalAllOffProven=false` und `actualMotorReferenceProven=false` sind konservative unveraenderliche Aussagen des KNX026-Modells. Das bedeutet nicht, dass eine physische Abschaltung elektrisch hergestellt wurde.
- Die produktive ETS-Anwendung bleibt AppVersion2 mit KO1..35; die vorgeschlagenen Raum-KOs der AppVersion3 sind nicht auf den realen KNX-Bus geschaltet. KNX025 bleibt im realen Build nur passiver Beobachter.
- KI-/UI-Operationen duerfen weder den KNX023-ARDUINO-Hardlock noch KNX022-Hardwareblocker umgehen.

## Pruefungen

`C:\ASH\Tools\python-3.13.15\python.exe tools/test_knx026_hmi_diagnostics.py` kompiliert und startet zwei native C++17-Testsuites mit `-Wall -Wextra -Werror -pedantic`. Sie pruefen unbekannte/stale Quellen, Vorlauf-vs.-Raumtrennung, 8-Motor-/Zone-Maps, DPT5.001, Fault-Maskierung, Zeitumbruch, ausnahmslos unbekannte reale Position und read-only Navigation sowie die ARDUINO-Hardlock-Compilation.

Isolierter RP2040-Build: `tools/build_controller_isolated.py` (nur temporare Kopie, keine Platine geflasht, `include/knxprod.hpp` bleibt unveraendert). Aeltere Slices separat regressieren.

## Nicht erledigte Integration

LCD-PCF8574-Hardwareversion, echte Encoder-Debounce-/ISR-Implementierung, Anzeige-Rendering, lokale Bestueckung, reale KNX-Kommunikation, reale Motorposition/Endlagen, Unabhaengigkeit des sicheren Ausschaltens und physischer Hardwaretest bleiben eigenstaendige zukuenftige Gates; KNX011, KNX018 und KNX002..006 nicht implizit schliessen.
