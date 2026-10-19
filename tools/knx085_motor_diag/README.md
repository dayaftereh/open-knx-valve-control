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
