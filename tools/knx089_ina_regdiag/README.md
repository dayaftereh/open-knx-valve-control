# KNX089 – INA219 Registerdiagnose

Dieses Projekt ist ein bewusst **motor-gesperrter** Fork der
KNX085-Firmware für OpenKNXValveControl V1.2.

Die Firmware ist auf dem realen RP2040 auf LLO Home (USB COM8)
installiert. KNX_TX und Motor-PWM bleiben LOW, motor_gate=0.

## Warum

Der Nutzer maß am 19.10.2026 **0,00 mV DC an R29**.
INA219 0x40 behauptete zuvor rund +92,6 mV bzw. 463 mA.
Mit R29=0,200 Ohm können nicht beide Messungen richtig sein.

## Firmwarekommandos

- STATUS, TEMPS, RXSTATS: unveränderte passive KNX085-Diagnose
- INA: gecachter KONFIG-Wert, laufend aktualisierte INA-Werte
- INA_REGS: liest 0x00..0x05 direkt, jeweils per Repeated-START
  sowie STOP/START; gibt KNX089 REG-Zeilen aus
- INA_ADC_RESET: setzt ausschließlich den INA219-ADC per
  CONFIG Reset-Bit zurück, liest Konfiguration neu und
  startet die ADC-Messung erneut

Die vorhandenen KNX085-Motor-USB-Kommandos sind durch den festen
Kompilierungswert KNX085_HARDWARE_GATE_APPROVED=0 **inaktiv**,
auch bei einer irrtümlichen ARM-Anforderung. Zum Motorversuch
muss später bewusst die separate KNX085-Variante eingesetzt werden,
aber erst nach Behebung der INA219-Messabweichung.

## Verifizierte Ergebnisse

- CONFIG 0x399F Standard, auch nach INA_ADC_RESET.
- SHUNT 0x01: 92,59 mV vor und 92,63 mV nach Reset.
- BUS: 3,148 V.
- CAL 0x05 = 0x0000; deswegen sind 0x03 POWER und
  0x04 CURRENT 0, aber die Shuntspannung 0x01 muss
  trotzdem korrekt sein.
- Repeated-START und STOP-Lesungen liefern konsistente
  Konfigurationsregister; kleine Veränderungen bei laufendem
  ADC sind erwartbar.
- Alle vier Temperaturen, KNX-RX, UART und Ausgangs-Idle PASS.
- **Keine Motoransteuerung, kein KNX-TX-Befehl**.

## Aufzeichnung

Host auf LLO Home:

    & 'C:\Users\ll\.platformio\penv\Scripts\python.exe' 'C:\_myspace\workspace\open-knx-valve-control\tools\knx089_ina_regdiag\knx089_host.py'

Optional kann mit \`--reset-adc\` ausschließlich der INA219-ADC
zurückgesetzt werden. Dies wurde bereits einmal durchgeführt.
Ein erneuter MCU-Flash ist nicht nötig.

Build offline:

    C:\Users\ll\.platformio\penv\Scripts\pio.exe run -d tools\knx089_ina_regdiag

UF2 243200 Bytes, SHA256:
4715C992FC1BA61D90720A3B463AC172CD6499660A3D13ED3678793DB916BAEF

Details: docs/KNX089_INA219_R29_ZERO_MV_REGISTER_DIAG_20261019.md

## Nächster DMM-Test

Spannungsdifferenz am U23-seitigen Ende von
R33 Pin2 (IN+) gegen R34 Pin2 (IN−) auf DC-mV messen
und mit R29 (0,00 mV) vergleichen. Bei 0 mV dort
Analogfrontend/INA219 prüfen; bei 92,6 mV die
realen Sense-Leitungen und Lötstellen.


## KNX090 – Schlüsselfund aus der Reinigung (19.10.2026)

Der Nutzer entfernte Schmutz/Rückstände an U23, misst zwischen
R33 Pad2/IN+ und R34 Pad2/IN- noch etwa **82mV** und einen
ohmschen Wert um **20kOhm**. Nach Reinigung zeigt der
Live-INA219 weiterhin **92,59mV** im Shuntregister (CONFIG0x399F,
VBUS3148mV). Kein Reflash und kein Motor-Test.

**Neue Hauptverdachtsursache**: R33/R34 sind im PCB symbolisch
mit **10Ohm** ausgezeichnet, aber beide mit EDA
Hersteller-MPN **0402WGF1002TCE / LCSC C25744 = real
10kOhm (0402)** verknüpft. Zwei bestückte 10kOhm ergeben
zusammen über R29 nahezu genau 20kOhm, die der Nutzer nennt.
Vorsicht: Im EasyEDA-Design wird diese 10kOhm-MPN auch als
Platzhalter für 37 unterschiedliche Widerstandswerte benutzt;
die MPN ALLEIN beweist keine tatsächliche Bestückung.

**Nächste Messung**: Nur bei vollständig spannungsloser
Platine (USB/KNX/UPDI ab) R33 und R34 EINZELN jeweils
zwischen Pad1 und Pad2 auf Ohm prüfen. Soll jeweils 10Ohm.
Falls je etwa 10kOhm, Widerstände ersetzen und erneut
INA-/R29-Differenz plausibilisieren. INA219 nicht blind
ersetzen, bevor R33/R34 geprüft sind.

Dokumentiert:
docs/KNX090_INA219_CLEANED_R33_R34_MPN_20K_20261019.md
