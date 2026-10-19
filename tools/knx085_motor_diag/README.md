# KNX085 offline-only gated M1/M2 diagnostic

This is a development candidate forked from KNX084 using
`generate_from_knx084.py`. It is **not flashed** to the real board.

Build offline only:
`pio run -d tools/knx085_motor_diag -e knx085_locked`

All motor output assertion code is compiled out under
`KNX085_HARDWARE_GATE_APPROVED=0` and every ARM is refused.
The isolated firmware preserves passive KNX RX, all T0..T3 ATtiny
snapshots, GPIO0 KNX_TX LOW, and implements provisional INA219 readout.
I2C address, R29 calibration, rail supply, reset/brownout outputs and
hardwired TB6612 standby require physical qualification first.

NOTE: No hardware emergency stop exists on V1.2. Do not flip the
compile gate or flash the image without independent electrical proof,
especially while live KNX/USB/UPDI are connected. Current 3.10..3.45V,
25/120mA and 50..250ms software parameters are NOT field-qualified.

See [KNX085 Gate 1 report](../../docs/KNX085_MOTOR_GATE1_OFFLINE_20261019.md).


## KNX085 bench-only measurement update (2026-10-19)

The user authorized real movement of M1 on a **dry, waterless test valve**.
This is not permission to ignore the real prototype's KNX/USB/UPDI
power-path and reset issues. The RP2040 is still running KNX084 and
the prototype's KNX bus and CH340 UPDI are still connected; **no motor
movement or firmware flash was performed** in the current work session.

Run the read-only preparation tool first:
- python tools/knx085_motor_diag/knx085_bench_host.py plan

Two offline firmware images have passed PlatformIO builds:
- knx085_locked (compile-time motor outputs disabled, default)
- knx085_bench_unlocked (M1/M2 50..250ms pulses only after USB arming,
  five safe INA219 idle readings and explicit operator bench release)

The unlocked image is **NOT uploaded**. Physical KNX and CN1 UPDI
disconnection is required before a guarded flash/motor trial. The
host insists on USB-only supply, no CH340 enumerated, physical power
off available, exact RP2040 USB identity, valid T0..T3, acceptable
INA219 register/bus readback, and all-off verification. Current in
mA assumes a nominal 0.200-ohm R29 and is not calibrated yet. The
TRACE command retains raw shunt voltage for later calibration.

See docs/KNX085_M1_CURRENT_TRACE_BENCH_20261019.md.
No automatic homing-to-block is attempted before current tracing.
