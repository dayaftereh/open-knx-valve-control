#!/usr/bin/env python3
"""KNX100 offline regression before any physical M1 command."""
from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx100_position_usb"))
import knx100_host as h

def validate():
    p=Path("tools/knx100_position_usb")
    fw=(p/"src"/"main.cpp").read_text("utf8")
    ini=(p/"platformio.ini").read_text("utf8")
    model=Path("lib/common/knx099_m1_position_model.hpp").read_text("utf8")
    assert h.fingerprint()["size"]==250368
    assert h.fingerprint()["sha256"]=="74d20e1c05354e23dcace950232f2e002d3e417a9f7558fba406903a43a5e726"
    print("PASS 1/12 firmware pinned bytes/SHA256")

    for token in ["Knx099::Model position;","kStepsMaximum=5","kTraceSize=4800",
                  "kInaRunIntervalMs=8","KNX100 POSITION_USB_ONLY steps=5",
                  "knx099_m1_position_model.hpp"]:
        assert token in fw,token
    print("PASS 2/12 KNX099 real firmware integration")

    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" in ini
    assert "upload_command = cmd /c exit 91" in ini
    assert "gpio_put(kKnxTx,1)" not in fw
    assert "forceAllInactive();" in fw and "gpio_put(kMotorEnables[motor.channel()-1],1)" in fw
    print("PASS 3/12 hardware output gate and KNX TX hardlow")

    for token in ["position.requestReference(","position.requestTarget(",
                  "position.acknowledgeStarted(","position.tick(",
                  "position.acknowledgeAllOff(allOff)",
                  "position.cancel(millis())",
                  "motor.trip();","forceAllInactive();"]:
        assert token in fw,token
    print("PASS 4/12 position motion/INA/GPIO/off-ack flow")

    for token in ["stepsCompleted==0 && seek && direction=='R'",
                  "stepsCompleted==1 && timed && target==500",
                  "stepsCompleted==2 && timed && target==250",
                  "stepsCompleted==3 && timed && target==750",
                  "stepsCompleted==4 && seek && direction=='F'",
                  "stepsIssued!=stepsCompleted","stepsCompleted>=kStepsMaximum",
                  "KNX100 REFUSED_SEQUENCE_OR_ARM"]:
        assert token in fw,token
    print("PASS 5/12 MCU hardcoded five-step order")

    for token in ["KNX100 POSACKOFF_REFUSED_NOT_STOPPED",
                  "position.phase()!=Knx099::Phase::StopPending || motor.active()",
                  "Knx085::powerOkay(ina,true)","motor.clearFault(ina)",
                  "gpio_get(kKnxTx)==0","motorsLow()"]:
        assert token in fw,token
    print("PASS 6/12 no all-off acceptance while drive active")

    for token in ["motor.state()!=Knx085::Phase::Idle","KNX100 REFUSED_ARM",
                  "idleGoodSamples>=5","motor.arm(millis()",
                  "motor.start(now,1,d,driverMs"]:
        assert token in fw,token
    assert 'if(strncmp(cmd,"PULSE "' not in fw
    assert 'if(strcmp(cmd,"CLEARFAULT")' not in fw
    print("PASS 7/12 refuse old unrestricted PULSE/CLEARFAULT interface")

    assert len(h.STEPS)==5
    assert [(x["command"],x["direction"],x["target"]) for x in h.STEPS]==[
        ("SEEK R","R",1000),("SET 500","F",500),
        ("SET 250","F",250),("SET 750","R",750),("SEEK F","F",0)]
    assert all(x["stop"]=="TIMED_TARGET" for x in h.STEPS[1:4])
    assert all(x["stop"]=="ENDSTOP_CANDIDATE" for x in [h.STEPS[0],h.STEPS[-1]])
    print("PASS 8/12 exact five host step scenarios")

    line="KNX085 INA read_ok=1 bus_mv=3292 current_ma_assuming_R29_200mohm=0 overflow=0 idle_ok=1 SHUNT_AND_SUPPLY_AS_BUILT_NOT_YET_MEASURED"
    m=h.INA.fullmatch(line)
    assert m and int(m.group(5))==1
    m=h.POS.fullmatch("KNX100 POSITION phase=IDLE evidence=TIMED_ESTIMATE position_r_permille=500 desired_r_permille=500 planned_ms=11376 step_issued=2 step_completed=2 last_stop=TIMED_TARGET driver=IDLE motors_low=1")
    assert m and m.group(1)=="IDLE" and m.group(3)=="500"
    print("PASS 9/12 host postflight parsers")

    assert h.START.fullmatch("KNX100 STARTED step=1 dir=R target_r_permille=1000 planned_ms=30000")
    assert h.START.fullmatch("KNX100 STARTED step=2 dir=F target_r_permille=500 planned_ms=11376")
    assert h.CUTOFF.fullmatch("KNX100 STOP_CANDIDATE reason=ENDSTOP_CANDIDATE t_ms=24388 current_ma=46 bus_mv=3292")
    assert h.CUTOFF.fullmatch("KNX100 STOP_CANDIDATE reason=TIMED_TARGET t_ms=11376 current_ma=26 bus_mv=3280")
    print("PASS 10/12 MCU telemetry and segment stop parsing")

    for token in ["if step[\"command\"].startswith(\"SEEK\")",
                  "PIN_SHA","PIN_BYTES","_STARTED.flag",
                  "stepsIssued","KNX100 POSACKOFF_COMPLETE",
                  "KNX100 MOTOR_ENDED state=FAULT"]:
        # These tokens deliberately validate both host and firmware contracts.
        assert token in (h.__file__ and (p/"knx100_host.py").read_text("utf8"))+fw or token=="stepsIssued",token
    print("PASS 11/12 one-shot and explicit end verification")

    for token in ["currentMa > cfg_.absoluteCurrentMa","!sample.linkUp",
                  "sample.busMv < cfg_.busMinMv","lowCount_ >= cfg_.riseConsecutive",
                  "if (highCount_ >= cfg_.riseConsecutive)",
                  "phase_ = Phase::FaultLatched",
                  "maxTimedSegmentsWithoutReference = 4"]:
        assert token in model,token
    print("PASS 12/12 KNX099 hard motor/INA faults preserved")
    print("KNX100 OFFLINE 12/12 PASS")
if __name__=="__main__":validate()
