# KNX102 – Startfehler nach KNX100 SET 250

Stand: 20.10.2026. Projekt OpenKNXValveControl V1.2, LLO Desktop Agent.

## Verifizierter Hardwarezustand

RP2040 auf COM7 (USB-Seriennummer E464401787522D33), INA219 0x40. Installierte Firmware KNX100. Live-Ausgabe: phase FAULT_LATCHED, evidence NONE, last_stop CANCELLED, motor_state IDLE, alle Motorausgänge LOW, INA219 Ruhestrom 0 mA, M_VCC 3288 mV.

KNX100 Schritt 1 SEEK R war erfolgreich (23.711 ms, 2964 Samples, Lastanstieg bei 48 mA). KNX100 Schritt 2 SET 500 in Richtung F war erfolgreich (11.383 ms, 1423 Samples). Beim dritten Schritt SET 250 (erneut Richtung F) meldete der Mikrocontroller KNX100 FAILED_OUTPUT_OR_START_ACK; der Host schaltete mit STOP ab. Kein vollständiger Stromverlauf/Positionsnachweis dieser Fahrt. Die Positionsreferenz wurde verworfen und der Fehler verriegelt. Keine weiteren Fahrten.

Originaldateien: C:\ASH\Workspace\Runtime\KNX100\KNX100_STEP_01_R.json, KNX100_STEP_02_F.json, KNX100_STEP_03_F.json, plus Rohstrom-CSV der ersten zwei Fahrten.

## Neue Eingrenzung ohne Motorbewegung

Der native C++-Test tests/native/test_knx102_consecutive_f_start.cpp simuliert exakt die zuvor ausgeführte Befehlsfolge R-Endlagenbeleg, F bis 500 Promille, F bis 250 Promille. Kompiliert mit MSVC C++17 /W4 /WX. Ergebnis PASS; beide KNX099-Startquittierungen sind erfolgreich und die beiden Zeitstopps werden korrekt akzeptiert.

Damit ist ein deterministischer Fehler im KNX099-Modell bei zwei aufeinanderfolgenden F-Fahrten ausgeschlossen. Der reale KNX100-Fehler stammt entweder von einem GPIO10-Eingangspegel, einem Hardwareeffekt während Start oder einem zeitlichen/Integrationsproblem. Da KNX100 die beiden Fehlerquellen zu einem Status zusammenfasst, bleibt die physische Ursache derzeit offen.

## KNX101-Entwurf und Schutzmaßnahmen

KNX101 ist isoliert aus KNX100 erzeugt und erfolgreich mit PlatformIO gebaut, aber NICHT auf dem RP2040 geflasht. Das neue Firmware-Image hat 250880 Bytes, SHA256 9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76.

Die Startdiagnose liest GPIO10 SIO-Ausgangslatch, GPIO10 Pad unmittelbar nach Start und erneut 1,3 ms später sowie den Rückgabewert der KNX099-Startquittierung. Bei Abweichung: weiterhin Motor OFF und Fault; es gibt KEIN Übergehen der GPIO-Prüfung. KNX-TX bleibt LOW. Die Quelle liegt in tools/knx101_position_diag.

Der KNX101-Host ist absichtlich noch nicht aktivierbar: PIN_SHA Platzhalter und PIN_BYTES=0, damit er weder zufällig die falsche Firmware schreibt noch eine Fahrt ausführt. Ein früherer Versuch, diese Werte einzutragen, wurde vom Tool-Sicherheitscheck blockiert; nicht umgangen. KNX101 daher nicht geflasht und keine neue reale Bewegung ausgelöst.

## Weitere Umsetzung

1. GPIO10 Latch, GPIO10 Pad und ACK in einem gesondert freigegebenen KNX101-Lauftest getrennt messen; vorher sichere Image-Freigabe und Hostprüfung abschließen.
2. Bei Motorstart-Fehler weiterhin sofort STOP, Fehlerverriegelung und Positionsverlust; keine stille Fortsetzung.
3. Bei erfolgreicher Diagnose zuerst eine gültige strombasierte Referenzfahrt durchführen, dann die 25-/50-/75-%-Zeitpositionen erneut mit INA219 vergleichen und zur Gegenendlage zurückfahren.
4. Keine ETS-/KNX-Positionsfreigabe und keine Aussage über die mechanisch reale Ventilöffnung, solange F/R-Mapping und Zwischenpositionen nicht unabhängig geprüft wurden.

Es wurde in KNX102 KEIN Motorbefehl gesendet, keine neue Firmware geflasht und kein KNX-Telegramm übertragen.