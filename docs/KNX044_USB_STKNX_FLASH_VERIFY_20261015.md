# KNX044 – STKNX USB-Firmwaretest und KNX_TX-Sicherheitsbefund

Stand: 15.10.2026, LLO Desktop, PCB V1.2. Die Platine war nur über USB-C angeschlossen; KNX TP und Motoren waren laut Nutzer abgeklemmt.

## Live-Ergebnis

- RP2040 BOOTSEL wurde als 2E8A:0003, COM6, Flash-ID E464401787522D33 erkannt.
- Die ersten 256 KiB des installierten Flash wurden vor der Installation gesichert (SHA-256: 3b1943cdc0780c3851d952bc00fd67396f0d4326ef114505b2c12a0de876c774).
- Alle 286 Datenblöcke der bekannten KNX043 RX-only UF2-Datei stimmten bereits vor dem Reflash bytegenau mit dem ausgelesenen Flash überein.
- Die KNX043 STKNX Receive-Only Firmware (SHA-256 8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f) wurde mit picotool load -u -v neu installiert bzw. verifiziert: Flash-Verify OK.
- picotool reboot -a startete die Anwendung: COM7, 2E8A:000A, USB-Seriennummer E464401787522D33.
- 12 von 12 gezielten USB-STATUS-Abfragen erfolgreich: KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0.
- Source-Audit: In tools/knx043_passive_rx/src/main.cpp wird GPIO0/KNX_TX ausschließlich LOW gesetzt, kein GPIO0 HIGH und kein Serial1/TPUART. Motorenable-Leitungen werden LOW gesetzt.
- PicoScope 3205DMSO Kanal A am benutzerseitig identifizierten JMP3 Pad2/KNX_TX, Tastkopf 10:1, 60s passiver Hardware-Trigger auf steigende Flanke größer 0,35 V: TIMEOUT_NO_TRIGGER. Kein Trigger über dem Grenzwert im geprüften Zeitraum. Ohne Trigger wurde keine analoge Wellenform gespeichert; kürzere oder kleinere Ereignisse sind nicht ausgeschlossen.
- Zusätzliche USB-only PicoScope-Freilaufmessung, 500.000 Samples: A max. ca. 0,175 V, keine Samples über 0,5 V. Der Zeitraum war NICHT eindeutig zum tatsächlichen ROM-zu-Anwendung-Reboot synchronisiert.
- Früherer RUN-Reset: COM7 trennte/wiederverbund sich unter scharfem Trigger, aber kein KNX_TX-Trigger über 0,35 V. Frühere USB-Kontaktstörungen: KNX_TX über 0,5 V nur bei eingebrochener Boardversorgung, nicht bei stabiler Versorgung über 3 V.

## Bedeutung für den KNX-Bus

Die USB-Diagnosefirmware läuft und treibt KNX_TX nach Programmstart nicht HIGH. Dies ist eine positive USB-only-Funktionsprüfung, aber KEINE KNX-TP- oder ETS-Produktabnahme.

KNX043 ist eine reine Empfangsdiagnose. Der bisherige KNX-Produktcontroller in src/controller/main.cpp benutzt TPUart ArduinoSerial(Serial1). Auf der echten V1.2-Hardware arbeitet U9 direkt als STKNX-Transceiver: KNX_TX LOW ist Ruhe, ein HIGH-Puls von 35 Mikrosekunden ist ein aktiver KNX-0-Busimpuls (STMicroelectronics DS12399). Die existierende TPUart-Produktfirmware darf nicht einfach auf dieses Gerät geflasht werden.

Vor Anschluss an eine isolierte, strombegrenzte KNX-Teststrecke sind insbesondere physische R17-Pull-up-Entfernung/Isolation, U11 68-Ohm-Sendewiderstand nach früherem thermischem Fehler, U9-Zustand, D1/F1/JMP1-Rückspeisung und das KNX-busversorgte Reset-/Brownout-Verhalten zu qualifizieren. Keine Freigabe für den produktiven KNX-Bus; keine KNX-Sendeimpulse erzeugt. Die bisher 17 Hardware-Gate-Beobachtungen bleiben offen.

Maschinenlesbare Nachweise und Bild-Hashes: docs/KNX044_USB_STKNX_FLASH_VERIFY_20261015.json. Backup, installierte UF2 und Oszilloskop-Messungen unter C:/ASH/Workspace/Builds/OpenKNXValveControl/KNX044_USB_ONLY_FLASH_20261015. Keine Git-Push- oder Motoraktion.
