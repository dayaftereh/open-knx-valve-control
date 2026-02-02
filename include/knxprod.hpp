#pragma once


#define paramDelay(time) (uint32_t)( \
            (time & 0xC000) == 0xC000 ? (time & 0x3FFF) * 100 : \
            (time & 0xC000) == 0x0000 ? (time & 0x3FFF) * 1000 : \
            (time & 0xC000) == 0x4000 ? (time & 0x3FFF) * 60000 : \
            (time & 0xC000) == 0x8000 ? ((time & 0x3FFF) > 1000 ? 3600000 : \
                                         (time & 0x3FFF) * 3600000 ) : 0 )
                                             
// Parameter with single occurrence
#define StartupDelay                         0      // int32_t
#define StartupDelaySelection                4      // 16 Bits, Bit 15-0
#define Heartbeat                            6      // int32_t
#define TemperatureSensor                   10      // 1 Bit, Bit 7
#define     TemperatureSensorMask 0x80
#define     TemperatureSensorShift 7
#define HumiditySensor                      10      // 1 Bit, Bit 6
#define     HumiditySensorMask 0x40
#define     HumiditySensorShift 6
#define TemperatureAlign                    11      // float
#define HumidityAlign                       13      // float
#define HumiditySend                        15      // 8 Bits, Bit 7-0

//         Zeit (Sekundengenau)
#define ParamStartupDelay                        ((int32_t)knx.paramInt(StartupDelay))
// Zeit bis das Gerät nach einem Neustart aktiv wird
#define ParamStartupDelaySelection               (knx.paramWord(StartupDelaySelection))
// 'In Betrieb'-Telegramm senden alle
#define ParamHeartbeat                           ((int32_t)knx.paramInt(Heartbeat))
// Temperatursensor
#define ParamTemperatureSensor                   ((bool)(knx.paramByte(TemperatureSensor) & TemperatureSensorMask))
// Luftfeuchtesensor
#define ParamHumiditySensor                      ((bool)(knx.paramByte(HumiditySensor) & HumiditySensorMask))
// Temperaturwert anpassen
#define ParamTemperatureAlign                    (knx.paramFloat(TemperatureAlign, Float_Enc_IEEE754Single))
// Luftfeuchte anpassen
#define ParamHumidityAlign                       (knx.paramFloat(HumidityAlign, Float_Enc_IEEE754Single))
// Wert senden als
#define ParamHumiditySend                        (knx.paramByte(HumiditySend))

// Communication objects with single occurrence
#define KoHeartbeat 1
#define KoTemperature 2
#define KoHumidity 3
#define KoRequest 4

// In Betieb
#define KoHeartbeat                           (knx.getGroupObject(KoHeartbeat))
// Temperaturmesswert
#define KoTemperature                         (knx.getGroupObject(KoTemperature))
// Luftfeuchtemesswert
#define KoHumidity                            (knx.getGroupObject(KoHumidity))
// Alle Messwerte anfordern
#define KoRequest                             (knx.getGroupObject(KoRequest))

#ifdef MAIN_FirmwareRevision
#ifndef FIRMWARE_REVISION
#define FIRMWARE_REVISION MAIN_FirmwareRevision
#endif
#endif
#ifdef MAIN_FirmwareName
#ifndef FIRMWARE_NAME
#define FIRMWARE_NAME MAIN_FirmwareName
#endif
#endif
