# KNX042 - USB-only eight-channel motor LED first contact

**Status:** OPEN / M1 OPEN+CLOSE and M2 OPEN LEDs visually PASS; remaining channels and real 8-channel sequence flash pending. Do not claim Gate 4.

- **Gate 1:** V1.2 pinout and known KNX/power/STBY risks assessed.
- **Gate 2:** isolated KNX042 firmware and guarded USB pulse client implemented.
- **Gate 3:** offline source/host regressions, PlatformIO build and ASH audit.
- **Gate 4 (pending):** physical KNX bus isolation and actual LED/logic observation, no motor load. Only after user physically verifies isolation may any USB flash or pulse be attempted.

Evidence: [KNX042 runbook](../KNX042_MOTOR_LED_BRINGUP.md).

- **14.10.2026:** M1 F 180-s-HOLD-Testbild gebaut, sieben Offline-Tests PASS. Physische Bedingungen vom Nutzer gemeldet: KNX abgeklemmt, USB-only, keine Motoren. **USB-Flashing/LED-Output nicht erfolgt:** BOOTSEL-Transportaufruf sicherheitsseitig gesperrt, RP2040 weiterhin normale CDC-Anwendung. M1 noch AUS / nicht angesteuert. Gate 4 bleibt offen.

- First real USB test (2026-10-14): flash/verify and M1 F hold ACK successful. LED visual result remains pending.

- 2026-10-14 15:06:27 MESZ: M1 F 180s HOLD repeated at user's request using installed KNX042; USB ARM/HOLD ACK, later `armed=0 active=1`; actual LED observation remains pending. No reflash; leave slice open.

- Visual feedback after M1 F repeat #3: user confirmed **OPEN indicator illuminated** and reported M1 apparently energized. Original V1.2 PCB JSON ties OPEN via R41 to `IN_1` (GPIO18), CLOSE via R43 to `IN_2` (GPIO19). Remaining LED orientation possibly incorrect per user, not proven; no real motor current measured. Refer to [visual observation](../KNX042_OPEN_LED_OBSERVATION_20261014.json). Electrical LED checks and mechanical polarity mapping remain OPEN.

- 2026-10-14 16:56:40 MESZ: M1 F HOLD after user LED rework accepted; COM7 initial off, follow-up active=1 at 16:56:54, max 180s software auto-off. Visual LED result awaiting user; no flash/KNX/motor connection. [Evidence](../KNX042_M1_LED_AFTER_REWORK_20261014.json).

- **KNX042 Host-Fehler aufgedeckt, 14.10.2026:** Frühere `STATUS`-Abfragen sendeten im `finally` ein unbeabsichtigtes `STOP` (M1 HOLD 16:56:40, Status/STOP etwa 16:56:54). LED-Beobachtung nach Umlöten ist nicht schlüssig, keine elektrische GPIO-Verifikation. PC-Host korrigiert und mit Mock 3/3 plus bisheriger KNX042-Suite 10/10 getestet. **Keine** erneute Motoransteuerung/kein Flash während des Fixes. [Fehlernachweis](../KNX042_STATUS_SIDE_EFFECT_FIX_20261014.md).

- 2026-10-14 **17:13:01 MESZ after host STATUS fix:** new guarded M1 F 180s HOLD ACK; corrected STATUS read-only twice at 17:13:21 and 17:13:43, both `active=1`. Previous premature-stop bug did **not** recur. Physical LED observation still pending; timeout check pending. [Evidence](../KNX042_M1_AFTER_HOST_FIX_20261014.json).

- 2026-10-14 17:25:28–17:26:29 MESZ: User-requested M1 CLOSE / IN2 test without firmware flash, bounded 100 × 400ms `PULSE 1 R` with each AUTO-STOP acknowledged and 200ms nominal dark gap. Initial and final USB state `armed=0 active=0`, host exit0, 13/13 offline host tests PASS. **Physical CLOSE LED sighting pending**. [Live evidence](../KNX042_M1_CLOSE_BLINK_20261014.json).

- 2026-10-14 17:58:51–17:59:52 MESZ: user LED rework complete; guarded M2 OPEN `PULSE 2 F` 100x400ms real USB test PASS (100 ACK + 100 AUTO-STOP), initial/final inactive. 16/16 offline tests PASS. M2/OPEN visual LED confirmation pending; no motor/KNX connection or MCU flash. [Evidence](../KNX042_M2_OPEN_BLINK_20261014.json).

- 2026-10-14: New [8-channel 1s LED sequence](../KNX042_ALL_MOTOR_LED_SEQUENCE.md) (M1 CLOSE/OPEN through M8 CLOSE/OPEN, 1s ON + 1s OFF, 5 rounds/160s) built via Arduino-Pico, 22/22 KNX042 regressions PASS, UF2 checked/rollback saved. **Not flashed** because picotool reboot -f -u cannot reach ROM BOOTSEL over CDC; manual USB_BOOT required. [Build evidence](../KNX042_ALL_LED_SEQUENCE_BUILD_EVIDENCE.json).


## Prioritaetswechsel 2026-10-14: KNX043 Home-Bench vor M3–M8

Der Nutzer transportiert die Platine zu LLO Home und priorisiert KNX; M1 OPEN+CLOSE und M2 OPEN visuell positiv, die restlichen M3–M8-LED-Checks sind **bewusst zurueckgestellt**, nicht als bestanden markiert. KNX042 bleibt als **einziger** offener ASH-Slice-Marker erhalten; kein paralleler _OPEN_KNX043. Im selben kontrollierten Write-Slice wurden KNX043 Home-Inventur, Hardware-Sicherheits-Gates, RX-only-Sketch und Offline-Checks vorbereitet. [KNX043 Home-Bench](../KNX043_HOME_KNX_BENCH_READINESS.md).

**Physischer Blocker:** U11 wurde bei KNX + 5V heiss, R17 zieht STKNX-KNX_TX HIGH, produktive TPUart-Serial1-UART idle HIGH und unbekannte U9/U11-Schaeden. Keine Busbestromung vor stromlosem Hardwareabgleich, TX-LOW-Reset- und Brownout-Pruefung, sauberem USB-/KNX-Versorgungsnachweis und gesonderter Freigabe. Am LLO Home ist die Platine noch nicht angeschlossen. Kein Firmware-Flash/KNX-Versuch.

**Next exact action:** Bei Ankunft auf Home erst Foto/Status R17-U9-U11, Jumper und Rails stromlos, USB-C ohne Bus nur nach Power-Freigabe, COM/Geraete-ID erfassen und die [KNX043 Gate-Felder](../KNX043_HOME_KNX_GATE.json) mit realen Messungen aktualisieren. Dann elektrischen Buskontakt separat freigeben. Keinen alten TPUart-Controller am STKNX einsetzen.

- KNX043 Home live arrival 14.10.2026: RP2040 ROM BOOTSEL 2E8A:0003 mounted as D: RPI-RP2; RP2 Boot USB driver missing (Windows code28), picotool info refused, no flash. KNX/IP discovered at 192.168.178.5:3671 by multicast/unicast, own KNX IA 1.0.1 and tunneling advertised, ETS6 installed but not running. KNX hardware gate 0/17, R17/U9/U11/power still unresolved; no KNX TP bus or motors. [Evidence](../KNX043_HOME_LIVE_DISCOVERY_20261014.json).

- **R17 Benutzerbestaetigung 14.10.2026:** R17 ausgelötet laut Nutzer. Elektrische Kontinuität U9 KNX_TX zu 3V3 nicht gemessen; U11/U9 nach Temperaturereignis ungeprueft, reset-sicheres TX LOW und Backfeed offen. Auf Home ROM BOOTSEL D: RPI-RP2 mit read-only SHA256/UF2-Pruefer OK, 23/23 KNX043-Tests PASS. Kein Flash und kein KNX-Bus. [Firmware-Gate](../KNX043_R17_REWORK_TO_RX_FLASH.md).
