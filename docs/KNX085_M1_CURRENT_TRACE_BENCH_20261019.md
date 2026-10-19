# KNX087 – R29-Nachtrag vom 19.10.2026

Nach Nutzerbestätigung ist R29 auf der realen V1.2-Platine mit **200 mΩ / 1 W** bestückt. Die bisherige Sollwert-/MPN-Unklarheit bezieht sich auf eine widersprüchliche EasyEDA-Bauteilmetadatenangabe und die frühere Fotoablesung; sie gilt nicht mehr als ungeklärter Bestückungswert. Die echte KNX085-Firmware ist bereits für **0,200 Ω** konfiguriert (0,05 mA pro INA219-Shunt-LSB von 10 µV). Bei ausgeschalteten Motoren bleibt aber ein **ungewöhnlicher INA219-M_VCC-Gesamtstrom von ca. 463 mA**. Daraus ergeben sich ~92,6 mV Shuntspannung und nur ~0,043 W Verlust an R29. Ursache der unerwarteten Ruhelast bzw. der Messpfadabweichung offen. Siehe [KNX087-R29-Nachweis](KNX087_R29_200MOHM_1W_CONFIRMED_20261019.md). Die folgende historische Dokumentation ist als damaliger Prüfstand zu lesen.

---

# NACHTRAG KNX086 / 19.10.2026

**Aktueller Live-Stand:** Die KNX085-Firmware wurde am 19.10.2026 auf der realen V1.2-Platine MIT KNX und UPDI erfolgreich geflasht. Die bisherige pauschale Flash-Sperre wegen der frueheren U11-Erwaermung war fuer diesen bereits bei KNX076/081/084 geprueften Aufbau falsch; urspruenglich ging es um den entfernten R17-Pull-up. KNX085 antwortet auf COM8 mit TX LOW, Motoren LOW und aktiven Temperatur- und KNX-RX-Daten. **M1 fuhr noch nicht**, da INA219 im motorischen Stillstand eine nicht plausible Roh-Shuntspannung (~92.6mV) liefert; der R29-Wert ist unbekannt. Die nachfolgenden KNX085-Aussagen sind historische Zwischenstaende. Aktuelle Fakten: [KNX086-Live-Bericht](KNX086_R17_LIVE_FLASH_INA219_20261019.md).

---

# KNX085 M1 current profile – dry-bench test preparation

Date: 2026-10-19. LLO Home 0.7.9 session ses-20261019T050929-60cfb2d7ce79.
Initial Git 5879cb7 (clean). No hardware actuation, UF2 flash, KNX TX, UPDI write or Git push during this phase.

## User request
User authorizes physical test motion of two actual HmIP-VDMOT actuators on waterless sample valves. Desired sequence: log free-running current, drive M1 to an end-stop, identify a reliable current-based stall signature, stop immediately, establish zero, then back-drive. The estimated 15–30 mA free run and ~120 mA at stall are HYPOTHESES; there is no new measured motor-current data yet.

Manufacturer maximum: 3.3 V DC and 120 mA. This is NOT a prescribed end-stop current. Manufacturer reference: https://www.eq-3.com/downloads/download/homematic_ip/pdb/en/HmIP-VDMOT_153309A0_datasheet_V2.0.pdf

## Live 15-second passive baseline
- Firmware KNX084 still on RP2040; motor outputs cannot be commanded.
- COM8 RP2040 2E8A:000A, USB serial E464401787522D33.
- COM5 CH340 UPDI still connected; prototype KNX TP 1.3 live.
- Live host evidence C:\Users\ll\Downloads\KNX084_LIVE_20261019_071158_summary.json.
- Nine valid CRC snapshots, UART timeout 0, rejected 0.
- T0 14.69C, T1 14.44C, T2 14.25C, T3 14.25C VALID.
- GPIO0 KNX TX LOW, all motor outputs LOW, passive RX count rising.
- No INA219 data can be sampled by current KNX084 firmware.

## Current instrumentation
U23 INA219 I2C GPIO4 SDA, GPIO5 SCL, presumed address 0x40 pending live proof.
Shunt is common R29 between 3.3V and M_VCC, nominal design 0.200 ohm, physical as-built resistance UNVERIFIED. INA219 shunt voltage LSB 10uV, bus voltage LSB 4mV.
Provisional conversion ONLY if R29=0.200 ohm:
I_mA = shunt_uV / 200. E.g. 15mA->3mV, 30mA->6mV, 120mA->24mV.
Save RAW shunt voltage even if milliamp calibration proves wrong.

## Prepared offline firmware and host workflow
- tools/knx085_motor_diag/generate_from_knx084.py chains enhance_trace.py to reproduce source.
- source retains KNX RX input, KNX TX LOW, ATtiny UART temperature T0–T3.
- INA219 config/readout with five valid consecutive idle samples required before ARM.
- 96-sample bounded waveform of shunt_raw, shunt_uV, bus_mV, time_ms, validity. Export after motor OFF.
- M1/M2 exclusive motor logic, arm expires 5 seconds, pulses 50–250ms, USB-loss auto-stop, current/voltage fault and explicit STOP, no auto-drive on boot.
- Two firmware builds OFFLINE only. Both have auto upload DISABLED.
  - locked UF2 242176B SHA256 DF6BDECEBA8C97A42071A5B11CEE3F2327646439D28229000AB3465D8A862839
  - bench unlocked UF2 242688B SHA256 86CBF6942FD12EBA07402C52842BA7543CABD2C2A557A329607C954388A54750
- Both PlatformIO builds exit0. Native 25+ state-machine checks PASS.
- tools/knx085_motor_diag/knx085_bench_host.py verifies COM identity, read-only status, T0–T3, INA config/voltage, CH340 absent, and requires explicit physical isolation before a single M1 pulse. Preflight refused without confirmations, exit5, before opening COM.
- Synthetic host parser/gate checks and Python syntax checks PASS.

## Real test BLOCKED on physical disconnection
The prototype is still connected to the live KNX line. A firmware flash requires RP2040 BOOTSEL/reset when KNX_TX GPIO0 LOW is NOT guaranteed. There is previous STKNX/U11 and TX/reset hazard evidence; do not knowingly flash while KNX live. Also UPDI CH340 is physically connected via CN1, with an unverified 5V backfeed path.

For the NEXT real step the user must:
1. Physically unplug only prototype KNX TP branch.
2. Physically unplug CH340/UPDI from CN1 and its USB supply.
3. Keep USB-C on RP2040 and M1/M2 test motors attached.
4. Ensure local ability to disconnect USB power promptly.

Then on a fresh work session verify port, boot identity and safe 3.3V/INA idle values, flash the tested UF2 with guarded procedure, perform read-only INA/TEMPS baseline, then a single 150ms M1 pulse; inspect raw current waveform, supply and all-off before any further pulse. Only after characterization and additional assessment consider a bounded homing-to-block run and a robust current-rise detector using several successive samples. A 120mA manufacturer max must never be assumed equal to verified zero.

No physical motor current, peak, travel time, end stop or zero position is claimed in this phase.
No Git push authorized.
