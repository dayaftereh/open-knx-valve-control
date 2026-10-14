# KNX042 - USB-only eight-channel motor LED first contact

**Status:** OPEN / physical preflight pending. Do not claim Gate 4.

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
