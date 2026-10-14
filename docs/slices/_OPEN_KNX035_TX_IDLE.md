# KNX035 – STKNX TX-Startpegel / R17 Pull-up-Hazard

**State:** open
**Profile:** software/static safety review, no physical actions
**Opened:** 2026-10-14
**Owner:** ChatGPT-OpenKNXValveControl-KNX035-STKNX-TX-20261014
**Session:** ses-20261014T062618-0631fe85bcbf
**Base HEAD:** 374dbc4f837169057b2000b0f19a3b91f240784e
**Git initial:** main CLEAN, 17 commits ahead origin/main, no other active writer.

## Gate 1 – Evidence/checkup

- User connected KNX and separate 5 V; U11 became very hot and KNX bus appears heavily loaded; all physical power disconnected after incident. User says the installed resistor is genuinely **68 ohms**, and the wrong 3.5-milliohm PCB Manufacturer Part was deliberately selected for the footprint. Do NOT mistake metadata for installed device.
- V1.2 schematic R17 = **10 kOhm pull-up**, PCB pad 1 = `KNX_TX`, pad 2 = `3.3V`. U9 STKNXTR pad24 = `KNX_TX`, connected to U18 via JMP3. U11 schematic **68 Ohm 2 W** (PCB metadata `HoJLR2512-3W-3.5mR-1%` wrong).
- Official ST DS12399 Rev3, sections 4.3 and 5.1.1: STKNX KNX_TX **LOW idle**, **HIGH only 35-us active pulse**, followed by 69-us LOW. Built-in KNX_TX weak pull-down typical 6 uA. A 10k resistor to 3.3V defeats this bias with MCU pin high-Z.
- Existing prepared firmware `setupKnx` uses `TPUart::Interface::ArduinoSerial(Serial1)`; library starts 19200/38400 baud 8E1 normal UART **idle HIGH**, which is incompatible with STKNX active-HIGH pulse input. The user's current *blink program* was not inspected; do not claim it actually enabled UART.
- This is a strong **design-level causal hypothesis**, NOT a measured high level at U9 KNX_TX and NOT verified exclusion of U9 damage, KNX wiring faults or another cause.

## Gate 2 – Decision

- Document remove R17 **only unpowered**, then separately measure the inactive KNX_TX voltage before reconnecting KNX. STKNX internal weak pulldown might restore idle LOW with high-Z MCU but cannot override a HIGH output or UART HIGH idle.
- For future revision, delete pull-up and provide **4.7k–10k external pull-down to GND**, directly on the `KNX_TX` input net, **NOT by placing a resistor on current R17 pads** (other R17 pad is 3.3 V). Consider independent hardware TX-enable/low-safe gate and reset/brownout behavior. Review proper STKNX pulse-level driver/PIO and KNX timing before bus tests.
- U11 actual value tracked as USER REPORTED 68Ω, while erroneous PCB MPN noted for later BOM cleanup. No production schematic/PCB/firmware changes in this slice; don't assert root cause proven.
- Keep KNX, USB/UPDI, motors and power disconnected until original KNX002–006, KNX034 power gates and post-overheat U9 checks addressed. Any real bus retest needs its own risk-controlled acceptance plan.
- Create docs, immutable source safety audit and negative tests, include in offline runner, commit locally without push.

## Gate 3
Pending.

## Gate 4
Pending.

## Gate 3 – evidence / plan implementation

- [x] Current schematic/PCB source proof: R17 10k up 3V3 on U9 KNX_TX, U11 expected 68ohm 2W between STKNX R68 and KNX_A; user confirms physical 68ohm rather than wrong BOM MPN; JMP3 and RP2040 physical pin2 link located.
- [x] ST official DS12399 Rev3 sections 4.3 and 5.1.1: LOW idle, HIGH 35us (KNX logic0) then LOW 69us, weak 6uA internal pulldown at KNX_TX. Externally 10k pull-up defeats idle-low in high-Z MCU state, plausibly causes continuous KNX load/overheating when 3.3V appears.
- [x] Separate software hazard: source setupKnx uses TPUart ArduinoSerial(Serial1) and third-party library normal 8E1/19200/38400 baud, idle HIGH; direct STKNX pulse input incompatible. User blink firmware is uninspected; do not claim actual MCU pin drove high.
- [x] docs/KNX035_STKNX_TX_IDLE_HAZARD.md and docs/KNX035_STKNX_TX_HAZARD.json, no fabricated hardware values. V1.2 unpowered R17 removal recommended as first fix, but not safe automatic bus reconnect. V1.3 ECO: remove 3.3V pull-up, add external 4.7-10k KNX_TX to GND on new footprint, investigate fail-LOW gated transmitter and correct RP2040 STKNX pulse PHY; correct U11 wrong MPN/BOM without altering actual 68ohm user report.
- [x] tools/audit_knx035_stknx_tx.py source/net/frozen prior firmware/PCB verifier PASS; tools/test_knx035_tx_hazard.py 12/12 fail-closed cases PASS.
- [x] README/ROADMAP/KNX022 and Home offline runner extended. Existing KNX002..006 and KNX034 power F1/D1 gate all remain BLOCKED.

## Gate 4 – validation/close

- [ ] Whole LLO Home offline smoke (job-000270) result.
- [ ] ASH audit 30/30 (first run 546 links), staged diff --check.
- [ ] Local implementation commit, HISTORY closing commit and marker remove, final clean Git/checkpoint; NO PUSH.

**Root cause only PROBABLE:** No U9 Pin24 measurement, no thermal/bus current measurement, and U9 post-overheat fault not excluded. No real power, USB, KNX, firmware flashing or motor actions in KNX035.
