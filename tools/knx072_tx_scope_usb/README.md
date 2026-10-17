# KNX072 USB-only GPIO0 TX oscilloscope bench

**Hard physical gate:** detach BOTH KNX+ and KNX- conductors before power.
This diagnostic firmware deliberately drives GPIO0 HIGH for eight 35-us
pulses separated by 69-us LOW, only after the USB commands
\`ARM USB_ONLY\` followed within 8 seconds by \`PULSE8\`. No pulses at boot.
USB \`STATUS\`, \`DISARM\`, \`STOP\` keep TX LOW.

GPIO0 is wired to JMP3 pad 3 and (if bridged) JMP3 pad 2 -> U9 KNX_TX
pin 24; JMP3 pad 1 is RX-related. Scope Channel B with true 10:1 probe:
set ±500mV RAW range, interpreted ±5V at probe tip for 3.3V HIGH.

This test is not a KNX TP1 packet or physical-device send authorization.
One pulse train is only ~0.83ms; permanent high current or short pulses
must never occur. If anything heats, disconnect USB immediately.
Board RUN reset/BOOTSEL idle safety and D1/U11 risks are independent
and still need verification before KNX+/- can be attached.

\`upload_command\` stays deliberately blocked. BOOTSEL UF2 copy is
permitted ONLY after physically confirming BOTH KNX power wires removed.

**KNOWN LIVE OBSERVATION (KNX072):** Scope saw all eight timed pulses but measured only 1.94 V maximum HIGH. Manufacturer guarantees digital HIGH only >=2.2 V at 3.3-V VCCCORE. STOP further use until U9 VCCCORE/power-domain verified. Known-good RX-only firmware was restored after this test. See docs/KNX072_USB_ONLY_TX_JMP3_PICOSCOPE_20261017.md.
