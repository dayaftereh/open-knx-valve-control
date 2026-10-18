# KNX076 RP2040 PIO single-pulse diagnostic (35 us)

Purpose: prepare a reproducible short STKNX KNX_TX waveform for a separate
two-channel PicoScope test. This is NOT a KNX frame, KNX group write, or
production controller firmware.

Safety and protocol:
- At startup GPIO0 output latch and direction are set LOW before PIO takeover.
- PIO program sits on blocking PULL with side-set 0, holding TX inactive.
- NO pulses at boot or from STATUS, STOP or DISARM.
- USB commands ARM ONE and then FIRE ONE within 4 seconds enable ONE pulse.
  After it, the software locks until next reboot.
- The 1-MHz PIO state machine is independent of the application CPU.
  16+16+3 = 35 cycles HIGH, then 1 cycle LOW, then indefinitely idle LOW.
- PlatformIO automatic upload is intentionally disabled. No automatic flash.
- The previously documented R17 pull-up is removed, but historic U11 heating
  and D1 bypass remain separate risks. The earlier USB-only VCCCORE measurement
  was 0.3 V; do not assume that value applies with bus power connected.
- During any later powered-bus pulse test use simultaneously sampled
  PicoScope A=KNX+ (proper input range for about 31 V through 10x probe)
  and B=KNX_TX (10x probe), with a common verified ground.
- This diagnostic firmware does not receive or decode KNX telegrams.
- Flashing a correctly built UF2 is not itself proof that transmission is safe.
- Do not trigger even one pulse until U9 VCCCORE under actual KNX supply,
  absence of shorted/damaged U11, and the GPIO reset/idle state have been
  checked on the bench.

Implementation:
  platformio run --project-dir tools/knx076_tx_single_pio

Host-side STATUS query after any flash is non-actuating. The next test should
use its own explicitly gated command sender and synchronized PicoScope capture.

No Git push without explicit instruction.
