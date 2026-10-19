# NACHTRAG KNX086 / 19.10.2026

**Aktueller Live-Stand:** Die KNX085-Firmware wurde am 19.10.2026 auf der realen V1.2-Platine MIT KNX und UPDI erfolgreich geflasht. Die bisherige pauschale Flash-Sperre wegen der frueheren U11-Erwaermung war fuer diesen bereits bei KNX076/081/084 geprueften Aufbau falsch; urspruenglich ging es um den entfernten R17-Pull-up. KNX085 antwortet auf COM8 mit TX LOW, Motoren LOW und aktiven Temperatur- und KNX-RX-Daten. **M1 fuhr noch nicht**, da INA219 im motorischen Stillstand eine nicht plausible Roh-Shuntspannung (~92.6mV) liefert; der R29-Wert ist unbekannt. Die nachfolgenden KNX085-Aussagen sind historische Zwischenstaende. Aktuelle Fakten: [KNX086-Live-Bericht](KNX086_R17_LIVE_FLASH_INA219_20261019.md).

---

# KNX085 – Gate 1 PASS, Gate 2 blocked, offline motor diagnosis candidate

Date: 2026-10-19 (Europe/Berlin), Agent LLO Home v0.7.9.
Repo main initial HEAD c16c967, clean, ahead 1 before these KNX085 changes.
ASH write session ses-20261019T045138-4c1e6020227a.

## Gate 1 / real USB live verification
- COM8 RP2040 VID 2E8A:000A; COM5 CH340 UPDI present.
- Current flashed RP application stays KNX084 – **KNX085 NOT FLASHED**.
- 15-second read-only host monitor from tools/knx084_passive_rx_temp:
  C:\Users\ll\Downloads\KNX084_LIVE_20261019_065308_summary.json
  - 9 snapshots observed, UART timeouts 0, rejected 0; T0 14.69C,
    T1 14.44C, T2 14.25C, T3 14.19C; all VALID.
  - STATUS KNX_TX low=1, motors low=1, uart_ready=1.
  - Passive KNX_RX increments, 1,811,920 edges at last check.
  - Ring timestamp loss (1,797,747 cumulative) from unattended
    logging is not evidence of 1.8M lost telegrams. Host monitor drains live.
- No GPIO motor pulse, KNX_TX, flash, UPDI write or Git push performed.

## Gate 2 / motor hardware cannot yet be released
- User identifies 2 real eQ-3 HmIP-VDMOT motors, manufacturer rated 3.3V,
  max 120mA, stroke 4.3 +/-0.3mm. Published 120mA is NOT a stall threshold.
- One shared R29 shunt between 3.3V and M_VCC. Schematic calls it
  0.200 ohm; PCB MPN metadata conflicts. Actual assembled resistance unknown.
- U23 INA219 shared high-side rail on SDA=GPIO4/SCL=GPIO5.
  I2C address 0x40 is a *candidate*, needs proof from real A0/A1 and readback.
  Differential V/I output is not yet calibrated/verified.
- User-reported D1 jumper, F1 2.5A vs schematic 630mA, earlier U11 heat,
  STKNX power budget and USB+KNX+UPDI backfeed risks remain.
- All TB6612 STBY pins are hard HIGH, no independent hardwired emergency
  motor kill. Reset/BOOTSEL/brownout motor outputs are not qualified.
- KNX-connected + USB-powered live board cannot be considered motor-safe
  from software assertions alone; isolated supply voltage/current measurement
  with appropriate meter/current limiting and verified motor supply is required.
- NOT APPROVED to run M1/M2 yet. No automatic permission is given by this file.

## Gate 3 / guarded offline-only candidate
- tools/knx085_motor_diag/ isolated fork of KNX084 (not production controller).
- Existing passive GPIO1 KNX receive, GPIO0 KNX TX always LOW, ATtiny
  T0..T3 CRC UART snapshots retained.
- New INA219 diagnostics register reads using Wire on GPIO4/5. Bus address,
  calibration and voltage/current readings unproven on hardware. Shunt current
  reported only as **assuming 0.200 ohm**.
- USB commands: STATUS, TEMPS, RXSTATS, RXDUMP, INA, MSTATUS,
  STOP, CLEARFAULT, ARM MOTORS, PULSE M1|M2 F|R duration_ms.
- Compile-time KNX085_HARDWARE_GATE_APPROVED=0 in committed
  platformio.ini means ARM is always refused and GPIO motor drive block is
  compiled out. This is the ONLY built variant. Never edit to 1 or flash
  without separate documented electrical qualification and independent review.
- The motor state model enforces idle INA proof, max one channel M1/M2,
  arm lease 5s, 50..250ms pulse, auto-stop, USB-loss and bad-sample fault.
  Thresholds (idle <=25mA, during <=120mA, M_VCC 3.10..3.45V)
  are illustrative firmware limits, NOT characterized motor limits.
- Firmware-side stop is NOT an independent hardware safety mechanism.
  Software timer can fail if MCU halts; INA219 raw shunt register limits
  depend on sensor settings and valid calibration. Do not claim real
  overcurrent/end-stop response from native unit tests.
- tools/knx085_motor_diag/generate_from_knx084.py reproducibly forks KNX084,
  and tests/native/test_knx085_motor_gate.cpp exercises state rules offline.
  No UF2 is auto-uploaded (upload_command exits 91).

## Next release gates before M1 test
1. Identify actual R29 resistance / INA219 board I2C address and verify
   differential shunt polarity against calibrated instrument.
2. Measure actual 5V, U6 VIN, 3.3V, M_VCC and motor rail behavior with
   safe sources; resolve D1/F1, STKNX budget, and CN1/UPDI backfeed.
3. Prove fail-off motor outputs during MCU reset, BOOTSEL, brownout and
   host-disconnect or implement an independent power cut.
4. Obtain explicit physical-gate acceptance for a short individual M1 pulse,
   observe differential output, current, motor direction and all-off.
5. Only after M1 passes, repeat on M2. Continue passive KNX RX + T0..T3.

**Git policy:** local commits allowed; no git push without explicit request.
