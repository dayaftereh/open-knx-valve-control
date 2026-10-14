# KNX041 - Temperature Bridge UART Write-Readiness Fix

## Scope and evidence
KNX040 isolated real-hardware UART diagnostics confirmed that the installed Arduino-Pico
`SerialUART::availableForWrite()` implementation returns **0 or 1** for readiness,
not a free-byte count. In the product bridge, a request frame is 8 bytes, but
`availableForWrite() < 8` always evaluated true and prevented any request.

KNX041 changes the product firmware source guard to
`availableForWrite() <= 0`. The request stays blocked when the port
is not writable; it proceeds when writable. Request generation, protocol,
CRC, receive parsing and motor/KNX interfaces are unchanged.

## Regression and historical scope
`tools/test_knx041_temperature_bridge_write_ready.py` checks the guard,
its ordering before `prepareRequest`, the transmit call, and exact
source equality with the previous Git HEAD after applying only the approved
three-line guard/comment replacement. This is a source-level regression;
there is **no product firmware flash** and no new target hardware test.

The older KNX031 historical immutability audit intentionally compares
`src/controller/temperature_bridge.cpp` byte-for-byte to its historical
baseline; it necessarily fails after this explicitly authorized KNX041
source change. Keep that historical evidence and record this expected
scope conflict rather than silently relaxing immutable historical audits.

## Hardware restrictions
The real KNX040 UART link was previously verified with no DS18B20 fitted;
there are not yet any real Celsius measurements. The production RP2040
firmware must **not** be flashed, KNX bus must remain disconnected, and
motors must not be moved. STKNX TX idle, U9/U11 overheating and supply
safety are still open. Physical sensor connection requires V1.2 pinout
verification and power OFF.

No GitHub push without approval.
