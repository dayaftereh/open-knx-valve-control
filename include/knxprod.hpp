#pragma once


#define paramDelay(time) (uint32_t)( \
            (time & 0xC000) == 0xC000 ? (time & 0x3FFF) * 100 : \
            (time & 0xC000) == 0x0000 ? (time & 0x3FFF) * 1000 : \
            (time & 0xC000) == 0x4000 ? (time & 0x3FFF) * 60000 : \
            (time & 0xC000) == 0x8000 ? ((time & 0x3FFF) > 1000 ? 3600000 : \
                                         (time & 0x3FFF) * 3600000 ) : 0 )
                                             
// Parameter with single occurrence
#define StartupDelay                         0      // uint16_t
#define StartupDelaySelection                2      // 16 Bits, Bit 15-0
#define Drive1Active                         4      // 1 Bit, Bit 7
#define     Drive1ActiveMask 0x80
#define     Drive1ActiveShift 7
#define Drive2Active                         4      // 1 Bit, Bit 6
#define     Drive2ActiveMask 0x40
#define     Drive2ActiveShift 6
#define Drive3Active                         4      // 1 Bit, Bit 5
#define     Drive3ActiveMask 0x20
#define     Drive3ActiveShift 5
#define Drive4Active                         4      // 1 Bit, Bit 4
#define     Drive4ActiveMask 0x10
#define     Drive4ActiveShift 4
#define Drive5Active                         4      // 1 Bit, Bit 3
#define     Drive5ActiveMask 0x08
#define     Drive5ActiveShift 3
#define Drive6Active                         4      // 1 Bit, Bit 2
#define     Drive6ActiveMask 0x04
#define     Drive6ActiveShift 2
#define Drive7Active                         4      // 1 Bit, Bit 1
#define     Drive7ActiveMask 0x02
#define     Drive7ActiveShift 1
#define Drive8Active                         4      // 1 Bit, Bit 0
#define     Drive8ActiveMask 0x01
#define     Drive8ActiveShift 0
#define Drive1ControlLoop                    5      // 1 Bit, Bit 7
#define     Drive1ControlLoopMask 0x80
#define     Drive1ControlLoopShift 7
#define Drive2ControlLoop                    5      // 1 Bit, Bit 6
#define     Drive2ControlLoopMask 0x40
#define     Drive2ControlLoopShift 6
#define Drive3ControlLoop                    5      // 1 Bit, Bit 5
#define     Drive3ControlLoopMask 0x20
#define     Drive3ControlLoopShift 5
#define Drive4ControlLoop                    5      // 1 Bit, Bit 4
#define     Drive4ControlLoopMask 0x10
#define     Drive4ControlLoopShift 4
#define Drive5ControlLoop                    5      // 1 Bit, Bit 3
#define     Drive5ControlLoopMask 0x08
#define     Drive5ControlLoopShift 3
#define Drive6ControlLoop                    5      // 1 Bit, Bit 2
#define     Drive6ControlLoopMask 0x04
#define     Drive6ControlLoopShift 2
#define Drive7ControlLoop                    5      // 1 Bit, Bit 1
#define     Drive7ControlLoopMask 0x02
#define     Drive7ControlLoopShift 1
#define Drive8ControlLoop                    5      // 1 Bit, Bit 0
#define     Drive8ControlLoopMask 0x01
#define     Drive8ControlLoopShift 0
#define PrePostTemperaturesOutput            6      // 1 Bit, Bit 7
#define     PrePostTemperaturesOutputMask 0x80
#define     PrePostTemperaturesOutputShift 7

//         Zeit (Sekundengenau)
#define ParamStartupDelay                        (knx.paramWord(StartupDelay))
// Zeit bis das Gerät nach einem Neustart aktiv wird
#define ParamStartupDelaySelection               (knx.paramWord(StartupDelaySelection))
// Stellmotor 1 aktiviert
#define ParamDrive1Active                        ((bool)(knx.paramByte(Drive1Active) & Drive1ActiveMask))
// Stellmotor 2 aktiviert
#define ParamDrive2Active                        ((bool)(knx.paramByte(Drive2Active) & Drive2ActiveMask))
// Stellmotor 3 aktiviert
#define ParamDrive3Active                        ((bool)(knx.paramByte(Drive3Active) & Drive3ActiveMask))
// Stellmotor 4 aktiviert
#define ParamDrive4Active                        ((bool)(knx.paramByte(Drive4Active) & Drive4ActiveMask))
// Stellmotor 5 aktiviert
#define ParamDrive5Active                        ((bool)(knx.paramByte(Drive5Active) & Drive5ActiveMask))
// Stellmotor 6 aktiviert
#define ParamDrive6Active                        ((bool)(knx.paramByte(Drive6Active) & Drive6ActiveMask))
// Stellmotor 7 aktiviert
#define ParamDrive7Active                        ((bool)(knx.paramByte(Drive7Active) & Drive7ActiveMask))
// Stellmotor 8 aktiviert
#define ParamDrive8Active                        ((bool)(knx.paramByte(Drive8Active) & Drive8ActiveMask))
// Stellmotor 1 Control-Loop
#define ParamDrive1ControlLoop                   ((bool)(knx.paramByte(Drive1ControlLoop) & Drive1ControlLoopMask))
// Stellmotor 2 Control-Loop
#define ParamDrive2ControlLoop                   ((bool)(knx.paramByte(Drive2ControlLoop) & Drive2ControlLoopMask))
// Stellmotor 3 Control-Loop
#define ParamDrive3ControlLoop                   ((bool)(knx.paramByte(Drive3ControlLoop) & Drive3ControlLoopMask))
// Stellmotor 4 Control-Loop
#define ParamDrive4ControlLoop                   ((bool)(knx.paramByte(Drive4ControlLoop) & Drive4ControlLoopMask))
// Stellmotor 5 Control-Loop
#define ParamDrive5ControlLoop                   ((bool)(knx.paramByte(Drive5ControlLoop) & Drive5ControlLoopMask))
// Stellmotor 6 Control-Loop
#define ParamDrive6ControlLoop                   ((bool)(knx.paramByte(Drive6ControlLoop) & Drive6ControlLoopMask))
// Stellmotor 7 Control-Loop
#define ParamDrive7ControlLoop                   ((bool)(knx.paramByte(Drive7ControlLoop) & Drive7ControlLoopMask))
// Stellmotor 8 Control-Loop
#define ParamDrive8ControlLoop                   ((bool)(knx.paramByte(Drive8ControlLoop) & Drive8ControlLoopMask))
// Vor- und Rücklauf-Temperaturen Ausgeben
#define ParamPrePostTemperaturesOutput           ((bool)(knx.paramByte(PrePostTemperaturesOutput) & PrePostTemperaturesOutputMask))

// Communication objects with single occurrence
#define KoSoll-Temperatur_1 
#define KoSoll-Temperatur_2 
#define KoSoll-Temperatur_3 
#define KoSoll-Temperatur_4 
#define KoSoll-Temperatur_5 
#define KoSoll-Temperatur_6 
#define KoSoll-Temperatur_7 
#define KoSoll-Temperatur_8 
#define KoIst-Temperatur_1 
#define KoIst-Temperatur_2 
#define KoIst-Temperatur_3 
#define KoIst-Temperatur_4 
#define KoIst-Temperatur_5 
#define KoIst-Temperatur_6 
#define KoIst-Temperatur_7 
#define KoIst-Temperatur_8 
#define KoStell-Wert_1 
#define KoStell-Wert_2 
#define KoStell-Wert_3 
#define KoStell-Wert_4 
#define KoStell-Wert_5 
#define KoStell-Wert_6 
#define KoStell-Wert_7 
#define KoStell-Wert_8 
#define KoT0 
#define KoT1 
#define KoT2 
#define KoT3 
#define KoT4 
#define KoT5 
#define KoT6 
#define KoT7 
#define KoT8 

// Die Soll-Temperatur für die Steuerung von Stellmotor 1
#define KoSoll-Temperatur_1                   (knx.getGroupObject(KoSoll-Temperatur_1))
// Die Soll-Temperatur für die Steuerung von Stellmotor 2
#define KoSoll-Temperatur_2                   (knx.getGroupObject(KoSoll-Temperatur_2))
// Die Soll-Temperatur für die Steuerung von Stellmotor 3
#define KoSoll-Temperatur_3                   (knx.getGroupObject(KoSoll-Temperatur_3))
// Die Soll-Temperatur für die Steuerung von Stellmotor 4
#define KoSoll-Temperatur_4                   (knx.getGroupObject(KoSoll-Temperatur_4))
// Die Soll-Temperatur für die Steuerung von Stellmotor 5
#define KoSoll-Temperatur_5                   (knx.getGroupObject(KoSoll-Temperatur_5))
// Die Soll-Temperatur für die Steuerung von Stellmotor 6
#define KoSoll-Temperatur_6                   (knx.getGroupObject(KoSoll-Temperatur_6))
// Die Soll-Temperatur für die Steuerung von Stellmotor 7
#define KoSoll-Temperatur_7                   (knx.getGroupObject(KoSoll-Temperatur_7))
// Die Soll-Temperatur für die Steuerung von Stellmotor 8
#define KoSoll-Temperatur_8                   (knx.getGroupObject(KoSoll-Temperatur_8))
// Die Ist-Temperatur für die Steuerung von Stellmotor 1
#define KoIst-Temperatur_1                    (knx.getGroupObject(KoIst-Temperatur_1))
// Die Ist-Temperatur für die Steuerung von Stellmotor 2
#define KoIst-Temperatur_2                    (knx.getGroupObject(KoIst-Temperatur_2))
// Die Ist-Temperatur für die Steuerung von Stellmotor 3
#define KoIst-Temperatur_3                    (knx.getGroupObject(KoIst-Temperatur_3))
// Die Ist-Temperatur für die Steuerung von Stellmotor 4
#define KoIst-Temperatur_4                    (knx.getGroupObject(KoIst-Temperatur_4))
// Die Ist-Temperatur für die Steuerung von Stellmotor 5
#define KoIst-Temperatur_5                    (knx.getGroupObject(KoIst-Temperatur_5))
// Die Ist-Temperatur für die Steuerung von Stellmotor 6
#define KoIst-Temperatur_6                    (knx.getGroupObject(KoIst-Temperatur_6))
// Die Ist-Temperatur für die Steuerung von Stellmotor 7
#define KoIst-Temperatur_7                    (knx.getGroupObject(KoIst-Temperatur_7))
// Die Ist-Temperatur für die Steuerung von Stellmotor 8
#define KoIst-Temperatur_8                    (knx.getGroupObject(KoIst-Temperatur_8))
// Der prozentuale Stell-Wert für Stellmotor 1
#define KoStell-Wert_1                        (knx.getGroupObject(KoStell-Wert_1))
// Der prozentuale Stell-Wert für Stellmotor 2
#define KoStell-Wert_2                        (knx.getGroupObject(KoStell-Wert_2))
// Der prozentuale Stell-Wert für Stellmotor 3
#define KoStell-Wert_3                        (knx.getGroupObject(KoStell-Wert_3))
// Der prozentuale Stell-Wert für Stellmotor 4
#define KoStell-Wert_4                        (knx.getGroupObject(KoStell-Wert_4))
// Der prozentuale Stell-Wert für Stellmotor 5
#define KoStell-Wert_5                        (knx.getGroupObject(KoStell-Wert_5))
// Der prozentuale Stell-Wert für Stellmotor 6
#define KoStell-Wert_6                        (knx.getGroupObject(KoStell-Wert_6))
// Der prozentuale Stell-Wert für Stellmotor 7
#define KoStell-Wert_7                        (knx.getGroupObject(KoStell-Wert_7))
// Der prozentuale Stell-Wert für Stellmotor 8
#define KoStell-Wert_8                        (knx.getGroupObject(KoStell-Wert_8))
// Temperaturmesswert von T0
#define KoT0                                  (knx.getGroupObject(KoT0))
// Temperaturmesswert von T1
#define KoT1                                  (knx.getGroupObject(KoT1))
// Temperaturmesswert von T2
#define KoT2                                  (knx.getGroupObject(KoT2))
// Temperaturmesswert von T3
#define KoT3                                  (knx.getGroupObject(KoT3))
// Temperaturmesswert von T4
#define KoT4                                  (knx.getGroupObject(KoT4))
// Temperaturmesswert von T5
#define KoT5                                  (knx.getGroupObject(KoT5))
// Temperaturmesswert von T6
#define KoT6                                  (knx.getGroupObject(KoT6))
// Temperaturmesswert von T7
#define KoT7                                  (knx.getGroupObject(KoT7))
// Temperaturmesswert von T8
#define KoT8                                  (knx.getGroupObject(KoT8))

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
