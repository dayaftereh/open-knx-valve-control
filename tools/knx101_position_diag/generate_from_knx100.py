#!/usr/bin/env python3
"""KNX101: corrected KNX100 USB M1 positional bench with start-pin diagnostics.

Root cause of KNX100 step3 failed output-or-start-ACK was unresolved:
expose both hardware pad / SIO output-latch and model ACK; no override
of safety checks. Start from UNREFERENCED after flash, seek R first.
"""
from pathlib import Path
import shutil
old=Path(__file__).resolve().parents[1]/"knx100_position_usb"
new=Path(__file__).resolve().parent
(new/"src").mkdir(parents=True,exist_ok=True)
shutil.copyfile(old/"src"/"motor_gate.hpp",new/"src"/"motor_gate.hpp")
s=(old/"src"/"main.cpp").read_text("utf8")
s=s.replace("KNX100","KNX101")
oldcode='''        const bool gpioActive=gpio_get(kMotorEnables[0])==1;
        const Knx099::Action ack=position.acknowledgeStarted(
                                  motor.started(),d=='R'
                                  ? Knx099::Direction::R
                                  : Knx099::Direction::F);
        if(ack.type!=Knx099::ActionType::None || !gpioActive) {
            forceAllInactive();
            motor.trip();
            position.cancel(millis());
            if(Serial)Serial.println(F("KNX101 FAILED_OUTPUT_OR_START_ACK"));
            return;
        }
'''
newcode='''        // Observe BOTH the RP2040 SIO output latch and actual pad.
        // A transient pad low after driving a loaded pin is suspicious.
        const bool gpioOut=gpio_get_out_level(kMotorEnables[0])==1;
        const bool gpioPadInitial=gpio_get(kMotorEnables[0])==1;
        delayMicroseconds(1300);
        const bool gpioPadSettled=gpio_get(kMotorEnables[0])==1;
        const Knx099::Action ack=position.acknowledgeStarted(
                                  motor.started(),d=='R'
                                  ? Knx099::Direction::R
                                  : Knx099::Direction::F);
        // Do NOT bypass the motor driver GPIO or position ACK guard.
        if(ack.type!=Knx099::ActionType::None || !gpioOut || !gpioPadSettled) {
            forceAllInactive();
            motor.trip();
            position.cancel(millis());
            if(Serial) {
                Serial.print(F("KNX101 START_DIAG_FAILED pin_latch="));
                Serial.print(gpioOut?1:0);
                Serial.print(F(" pin_input_initial="));
                Serial.print(gpioPadInitial?1:0);
                Serial.print(F(" pin_input_settled="));
                Serial.print(gpioPadSettled?1:0);
                Serial.print(F(" model_action="));
                Serial.print(static_cast<unsigned>(ack.type));
                Serial.print(F(" model_phase="));
                Serial.println(positionPhaseName(position.phase()));
                Serial.println(F("KNX101 FAILED_OUTPUT_OR_START_ACK"));
            }
            return;
        }
        if(Serial) {
            Serial.print(F("KNX101 START_DIAG_OK pin_latch=1 pin_settled=1 model_ack=1"));
            Serial.println();
        }
'''
assert s.count(oldcode)==1,("KNX101 source start guard pattern",s.count(oldcode))
s=s.replace(oldcode,newcode)
s="// KNX101: Start pad/latch probe after KNX100 step3 output/ACK refusal; fail-closed.\n"+s
ini=(old/"platformio.ini").read_text("utf8")
ini=ini.replace("KNX100","KNX101")
ini=ini.replace("knx100_m1_position_5step","knx101_m1_position_diag_5step")
(new/"src"/"main.cpp").write_text(s,encoding="utf8",newline="\n")
(new/"platformio.ini").write_text(ini,encoding="utf8",newline="\n")
print("KNX101 fail-closed start GPIO diagnostics generated, no loosened guards")
