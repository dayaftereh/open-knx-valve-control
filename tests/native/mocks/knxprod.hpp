#ifndef OPENKNX_NATIVE_KNXPROD_MOCK_HPP
#define OPENKNX_NATIVE_KNXPROD_MOCK_HPP
// Test mirrors ETS generator ABI, not the product source of truth.
#define KoT0 25
#define KoTemperatureBridgeOnline 34
#define KoTemperatureValidMask 35
#define ParamPrePostTemperaturesOutput ((bool)(knx.paramByte(6) & 0x80))
#define ParamTemperatureSendIntervalSeconds (knx.paramWord(7))
#define ParamTemperatureChangeThresholdCenti (knx.paramWord(9))
#endif
