# KNX046 – KNX043 Read-only-Firmware auf LLO Home

Stand: 15.10.2026, USB-only-Test auf der OpenKNXValveControl V1.2.

Der Nutzer bestätigte ausdrücklich: nur USB-C angeschlossen, kein KNX-TP-Bus, kein Motor und kein Temperatursensor. Die physischen Anschlüsse konnten durch den Agenten nicht optisch geprüft werden.

## Flash- und USB-Ergebnis

- Der RP2040 war im ROM-BOOTSEL-Modus, USB VID/PID `2E8A:0003`, Laufwerk `D:` mit Volume `RPI-RP2`.
- Das unveränderte KNX043 STKNX RX-only UF2-Image wurde vorab geprüft: 146.432 Bytes, 286 Blöcke, SHA-256 `8b2a3d92c567bf38596d0afff9f1c7d527e5ef3be81ca798609b31a1e7f82e5f`.
- Picotool meldete einen fehlenden kompatiblen Windows-USB-Bootloader-Treiber; daher erfolgte das Flashen über den offiziellen UF2-Massenspeicherweg (Copy-Item an `D:\KNX043_RX_ONLY.uf2`). Kopierbefehl erfolgreich abgeschlossen am `2026-10-15T19:31:55.970Z`.
- USB-Beobachtung: `RPI-RP2` verschwand `2026-10-15T19:31:56.587Z`; RP2040 CDC erschien `2026-10-15T19:31:56.929Z` als `COM8`, VID/PID `2E8A:000A`, USB-Seriennummer `E464401787522D33`.
- Drei separate KNX043-STATUS-Abfragen auf COM8 waren erfolgreich: `KNX043 STATUS armed=0 listen=0 buffered=0 dropped=0`.
- Der Betrieb der KNX043-Firmware ist damit über USB bestätigt. Es erfolgte keine unabhängige binäre Flash-Rückleseprüfung mit Picotool.
- Original-USB-Ereignislog: `C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX046_HOME_USB_RXONLY_20261015\usb_bootsel_to_app_watch01\usb_events.jsonl`.

## Sicherheits- und Entwicklungsstatus

KNX043 stellt GPIO0 / KNX_TX nach Programmstart auf LOW und verfügt ausschließlich über eine passive STKNX-RX-Flankenerfassung. Die Empfangsaufzeichnung ist noch NICHT aktiviert. Keine KNX-Telegramme gesendet, keine motorischen Ausgangsbefehle, kein KNX-TP-Empfangstest durchgeführt. Es handelt sich nicht um eine funktionierende ETS-Produktfirmware.

**Kein KNX-Busanschluss freigegeben.** Alle 17 Hardware-Gate-Beobachtungen sind offen, darunter die frühere U11-Überhitzung, die R17-Pullup-Entfernung/Padisolation, U9-Schäden, F1/D1/JMP1-Rückspeisung sowie KNX_TX-Schutz während BOOTSEL/Reset/Brownout. Ein USB-Erfolg beweist nicht, dass der KNX-Transceiver am angeschlossenen Bus elektrisch sicher ist. Nächste reale Empfangsprüfung ausschließlich nach elektrischer Freigabe auf einer getrennten und abgesicherten KNX-Teststrecke.

Siehe [KNX045 Home-Handover](KNX045_LLO_HOME_RX_ONLY_HANDOVER_20261015.md) und [KNX043 Hardware-Gates](KNX043_HOME_KNX_GATE.json).
