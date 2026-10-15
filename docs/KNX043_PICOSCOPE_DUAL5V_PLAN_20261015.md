# KNX043 – Zweikanal-PicoScope: KNX_TX gegen USB-5-V

**Stand:** 15. Oktober 2026 – Vorbereitung, noch **keine neue Einspeise-/Kontaktmessung**.

## Fragestellung

Beim vorangegangenen USB-BOOTSEL-Versuch berichtet der Nutzer mehrfaches An/Aus beim schwierigen USB-Einstecken. Die vorige Einzelkanalmessung erfasste bis +0,436 V an benutzerseitigem KNX_TX, aber ohne zeitgleiche Versorgungskurve. Der Trigger endete nach Trennung von COM7 und vor der erfassten ROM-Anmeldung. Kontaktprellen bei der USB-Verbindung und Einstreuung eines hochohmigen Knotens sind plausible, jedoch nicht nachgewiesene Erklärungen.

## Verdrahtung und Sicherheit

Vor Berührung der Messpunkte USB von der Platine entfernen, KNX-Bus und Motoren abgeklemmt lassen. PicoScope 3205D MSO besitzt **gemeinsame Masse der Analogkanäle**; beide Massereferenzen nur an **demselben Platinen-GND**, keinesfalls an KNX TP A/B, USB +5 V oder unterschiedliche Potenziale. Beide Tastköpfe physisch auf **10:1**. A bleibt an JMP3 Pad 2 / U9 KNX_TX. B wird mit der **Messspitze** an den positiv identifizierten **USB-VBUS-/5-V-Eingangspunkt der Platine** angeschlossen, nicht an eine KNX-seitige Versorgung oder einen unbekannten Anschluss. Nach Befestigung der Tastköpfe und ohne USB-Versorgung „Kanal B bereit“ melden. Kein Löten an angeschlossener Versorgung, keine benachbarten Pads kurzschließen.

**Kein KNX-TP-Busanschluss, keine Motorlast, kein UF2-Flash, keine automatische USB-/GPIO-Schaltaktion durch den Agenten.** Physischer Kontakt und korrekte VBUS-Stelle sind Nutzeraussagen; der Agent kann sie nicht selbst prüfen.

## Messkonfiguration

- PicoScope 3205DMSO Seriennr. GX118/0047; x86 PicoSDK ps3000a.dll.
- CH A: DC, SDK Range 5 = ±0,5 V Scope-Eingang, Tastkopf 10:1, ±5 V an der Messspitze.
- CH B: DC, SDK Range 6 = ±1 V Scope-Eingang, Tastkopf 10:1, ±10 V an der Messspitze; ausgelegt auf normale 5-V-USB-VBUS-Eingangsspannung.
- Hardware-Trigger **CH B positive Flanke bei 2,5 V an der Tastkopfspitze**, kein Autotrigger.
- Zwei PicoSDK-Datenpuffer, gleichzeitig abgetastet; Zeitbasis 1000, voraussichtlich ca. 7,984 µs/Sample; 100.000 Samples vor dem Trigger und 400.000 danach (gesamt ca. 4 Sekunden, tatsächliche Zeitbasis vom PicoSDK verifizieren).
- Rohformat: je 500.000 little-endian signed Int16 Samples für A/B, eigene SHA-256-Digests, JSON-Metadaten. Die B-Kurve wird mit Hysterese unter 2 V / über 3 V auf wiederholte USB-Kontakte ausgewertet.
- USB-Enumeration parallel über tools/knx043_usb_bootsel_watch.py: Firmware-CDC USB 2E8A:000A und ROM 2E8A:0003 werden getrennt protokolliert. Windows zeigt den Bootloader derzeit als COM6 statt Laufwerk RPI-RP2.
- Ein Durchlauf erfasst nur ein Triggerfenster von ca. vier Sekunden; spätere Steckerbewegungen könnten zusätzliche Läufe erfordern.

## Vorbereitende Funktionsprüfung

Das Skript tools/knx043_picoscope_dual_usb5v_capture.ps1 wurde in **Mode Test** mit zwei gleichzeitig aktiven SDK-Kanälen und deaktiviertem Hardware-Trigger erfolgreich geprüft. Je 500.000 ADC-Samples wurden gespeichert; ohne angeschlossenen B-Tastkopf zeigte B nur einen schwebenden Pegel und dieser Test ist **keine reale USB-5-V-Messung**. Für Mode Arm muss ein vom Nutzer bestätigter physischer Anschluss über -PhysicalProbesVerified angegeben werden.

## Noch offen

1. Nutzer steckt B im spannungsfreien Zustand an nachweislich USB-seitigen 5 V an; gemeinsames GND prüfen.
2. Agent überprüft beide PicoSDK-Kanäle ohne USB-Aktion und startet den passiven Hardware-Trigger sowie den USB-VID/PID-Monitor; **erst dann** wird eine konkrete Enduhrzeit angegeben.
3. Nutzer hält BOOTSEL, steckt USB einmal möglichst sauber ein und lässt den Stecker anschließend in Ruhe.
4. A und B Rohsignale um die erste 5-V-Flanke und eventuelle weitere B-Spannungseinbrüche quantitativ vergleichen. Eine 5-V-Rail-Kurve erklärt nicht automatisch die absolute U9-Versorgung; spätere U9/U11-, D1/F1/JMP1- und Brownout-Gates separat prüfen.

## Tatsächlich verwendeter Tastkopf und Ergebnis

Die ursprüngliche Vorbereitung ging für B von einem 10:1-Tastkopf aus. Der Nutzer stellte richtig, dass **Kanal B physisch 1:1** ist. Der daraus zunächst übersteuerte SDK-Messbereich wurde vor dem echten Versuch auf **±10 V Scope-Eingang bei 1:1** korrigiert und live validiert. A blieb 10:1.

Die echte Synchronaufnahme zeigt B-Einbruch/kurzen Wiederanstieg/erneuten Einbruch; KNX_TX-Ausschläge über 0,5 V treten praktisch ausschließlich bei eingebrochener B-Versorgung auf. [Ergebnis](KNX043_PICOSCOPE_DUAL_USB5V_RESULT_20261015.md).
