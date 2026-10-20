# KNX093 – M1 R 800ms, One-shot-Hoertest (Desktop)

**Aktuell auf echter Platine COM7:** KNX093 mit freigegebenem,
aber auf genau ein Befehlsformat begrenztem Motorkanal M1 R800ms.

Der Benutzer vermutete beim frueheren KNX092 F150ms-Puls
einen Endanschlag. Deshalb wurde am 20.10.2026 einmal R800ms
als laengerer Hoertest durchgefuehrt. Kein Homing/Anschlag-Test.

- Verifizierte Board-ID: USB 2E8A:000A, COM7,
  RP2040 E464401787522D33.
- Physisch nur USB-C und Ventilmotor M1 angeschlossen.
- INA219 nach Reparatur R33/R34 je10Ohm plausibel:
  0,12..0,16mV Shunt ohne Motor; M_VCC ~3,29V.
- Firmware-Build PlatformIO Core6.1.16:
  env knx093_m1_reverse_800 PASS.
- UF2 SHA256:
  f10743ac5b5e33e0969a04e34c53d353ec832ffb2009a29fcdfd90417447d619.
- Motor-Gate1, nur PULSE M1 R 800, alle anderen
  Motorbefehle fuer M2/F/andere Zeiten abgelehnt.
- Software-Notstopp bei >120mA, Spannung ausserhalb
  3,10..3,45V, fehlenden INA-Werten/USB, Zeit>800ms.
- Zusaetzlicher Stall-Guard: ab100ms fuer vier gueltige
  aufeinanderfolgende Samples >=90mA => FAULT.
- Software-Stop ist keine unabhaengige STO;
  eine analoge Abschaltung ist nicht auf dem Board vorhanden.
- Keine selbsttaetige Motorbewegung nach Flash/Boot.

Host-Skript: tools/knx093_m1_long/knx093_host.py
- preflight: alter KNX085-Stand, nur USB-Diagnose
- flash: KNX093 genau einmal mit identifiziertem
  ROM-Bootloader und Image-SHA
- verify: aktueller KNX093-Stand, nur USB-Diagnose
- pulse: genau ein ARM + M1 R800 + Trace/STOP,
  keine Auto-Wiederholung

ACHTUNG: Flash und Pulse wurden bereits durchgefuehrt;
die Runtime-One-Shot-Flags verhindern automatische
Wiederholungen. Keinesfalls Flag loeschen, um ohne neuen
Testauftrag erneut loszufahren.

Realtest: 100/100 gueltige INA-Samples t7..799ms,
Peak108,90mA, Median29,625mA, Ende29,95mA.
Firmware Ende IDLE, kein FAULT; STOP quittiert,
Motor-Ausgaenge LOW, INA nachher nominal0mA.

Der Benutzer muss die physische Motorbewegung/Hoerbarkeit
noch bestaetigen.

Vollstaendiger Bericht:
docs/KNX093_DESKTOP_M1_R800_LIVE_20261020.md

Trace auf LLO Desktop:
C:\ASH\Workspace\Runtime\KNX093\
KNX093_M1_R800_20261020_080931.csv und .json

Kein Git-Push ohne explizite Freigabe.
