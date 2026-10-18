# KNX084 - passive KNX receive and ATtiny3216 temperature diagnostics

**Only KNX RX / temperature measurements. NEVER transmit KNX, move a motor or write ATtiny flash.** Separate isolated RP2040 application, not a complete ETS valve controller.

## PCB V1.2 pins

| Pin | Hardware | Diagnostic |
| --- | --- | --- |
| RP GPIO0 | STKNX KNX_TX active HIGH | output LOW permanently in application |
| RP GPIO1 | STKNX KNX_RX | input interrupt, no pullup |
| RP GPIO8 | UART1 TX -> ATtiny PA2 RX | ATtiny CRC snapshot requests only |
| RP GPIO9 | UART1 RX <- ATtiny PA1 TX | ATtiny CRC responses |
| RP GPIO10..17 | TB6612 eight enables M1..M8 | all outputs LOW |
| RP GPIO18/19 | TB6612 shared direction | both outputs LOW |
| ATtiny PA5/PA6/PA7/PB5 | DS18B20 T0/T1/T2/T3 | controlled by existing ATtiny firmware |

GPIO0 is **not** shared with the ATtiny UART. The diagnostic contains
no UART0/Serial1, KNX TX PIO, telegram output or motor PWM functions.
The firmware initializes GPIO0 and all motor GPIOs as LOW first, before
opening any serial interfaces, and reasserts LOW periodically.
It CANNOT guarantee their state in ROM BOOTSEL, reset or brownout.

## Read-only USB-CDC commands

- STATUS - motor and KNX_TX LOW status, UART status and counters
- TEMPS - cached CRC-validated T0..T3 (or NO_SNAPSHOT_YET)
- RXSTATS - KNX_RX rising/falling counts, buffer loss and input level
- RXDUMP - timestamped stored RX edges for offline decode
- HELP - permitted command names

All other commands are refused. The firmware requests one cached ATtiny
snapshot ~every 2.1s, with an initial 3.5s delay, on UART1 at115200.
It uses the existing KNX014 8-byte request/67-byte response, CRC16,
frame sequence and channel status validation. Response includes all nine
channels; print T0..T3 only. Invalid/stale/faulty readings yield
temp_c=NA, never a false 0C.

Passive bus RX ring: 4096 edges. RXSTATS includes total and lost counts.
For a long run, the host tool drains the ring approximately every 8s.
Overflow affects stored timestamps, not physical bus communication.

## Build and observation

PlatformIO Arduino-Pico 5.5.0 env knx084_rx_temp. Standard upload
command is intentionally disabled; flash only a SHA-checked UF2 after
verifying the target RP2040 BOOTSEL RPI-RP2 volume.

    platformio run -e knx084_rx_temp
    python tools/knx084_passive_rx_temp/knx084_live_monitor.py --seconds 43
    python -m tools.knx084_passive_rx_temp.knx084_decode_capture LOGFILE

Monitor discovers runtime RP2040 USB CDC via 2E8A:000A instead of COM8
assumptions, records raw serial and JSON summary privately to Downloads.
The offline decoder uses the existing KNX070 TP1 parser and never
touches hardware.

## Known hardware gates

KNX, RP USB-C, CN1/UPDI CH340 and real M1/M2 test valve loads are
present per user; actual rail voltages have NOT been DMM measured.
CN1 pin1=5V can create a backfeed path with three powered interfaces.
The RP USB BOOTSEL driver separate MI_01 lacks WinUSB (Windows Code28);
UF2 mass storage works and the new firmware reenumerates as USB CDC.

The TB6612 STBY pin is hardwired HIGH: software LOW outputs are not a
hardware interlock. Do not load older motor-LED firmware with live KNX.
Before motor control, separately qualify supply, current/INA219/R29,
travel, end positions, fail-safe STOP and power-loss behavior.

Open electrical concerns: earlier U11 thermal issue, D1 bridge, F1
rating mismatch, STKNX VCCCORE under live bus, GPIO0 reset/BOOTSEL
fail-LOW safety, and previously measured brief 4.014V TX overshoot.

Live evidence and handover:
../../docs/KNX084_PASSIVE_BUS_ATTINY_T0_T3_LIVE_20261018.md
