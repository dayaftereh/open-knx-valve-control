#!/usr/bin/env python3
"""KNX097 strictly offline protocol/safety tests, no actual serial or motion."""
from pathlib import Path
import tempfile
from unittest.mock import patch
import json,sys
sys.path.insert(0,"tools/knx097_repeatability")
import knx097_flash as fw
import knx097_cycles as c

def bad(f):
    try:f()
    except fw.Stop:return
    raise AssertionError("Expected a blocked operation")

def verify():
    home=Path("tools/knx097_repeatability")
    m=(home/"src"/"main.cpp").read_text("utf8")
    gate=(home/"src"/"motor_gate.hpp").read_text("utf8")
    pio=(home/"platformio.ini").read_text("utf8")
    assert fw.pin()["sha256"]==fw.SHA
    assert fw.pin()["size"]==244736
    print("PASS 1/9: exact new board firmware pin")

    assert "kMaxPulseMs=30000" in gate and "kRunningCurrentLimitMa=120" in gate
    assert "kIdleCurrentLimitMa=25" in gate and "kMinMotorBusMv=3100" in gate
    assert "kMaxMotorBusMv=3450" in gate and "kArmWindowMs=5000" in gate
    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" in pio
    print("PASS 2/9: max30s absolute overcurrent/power/ARM gates")

    for t in ("kTraceSize=4800","kInaRunIntervalMs=8",
              "kEndstopHighCurrentMa=45","kEndstopLowCurrentMa=5",
              "kEndstopConsecutive=6","kEndstopGuardStartMs=450",
              "motor.trip();","kShortestPlausibleLegMs=12000"):
        assert t in m,t
    print("PASS 3/9: INA 8ms, 4800 raw values, endpoint cutoff")

    for t in ("char expectedDirection='R';","uint8_t legsCompleted=0;",
              "kLegsMaximum=6","dir!=expectedDirection",
              "legsCompleted>=kLegsMaximum",
              "lastLegKind=\"LOAD_RISE\"","expectedDirection=(expectedDirection=='R')?'F':'R';",
              "KNX097 REFUSED_LEG_ORDER_OR_LIMIT"):
        assert t in m,t
    assert "gpio_put(kKnxTx,1)" not in m
    print("PASS 4/9: hardware enforces first R, then six R/F legs only")

    signature="KNX097 M1_ALTERNATE duration_ms=30000 motor_gate=1 limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 next_dir=R legs_done=0 last_kind=NONE last_dir=-"
    assert fw.parse_version([signature])=={"next_dir":"R","legs_done":0,"last_kind":"NONE","last_dir":"-"}
    bad(lambda:fw.parse_version(["KNX096 M1_F_SEARCH duration_ms=30000"]))
    print("PASS 5/9: unique KNX097 firmware signature and correct sequence parser")

    assert c.name_for(0)=="KNX097_LEG_01_R" and c.name_for(1)=="KNX097_LEG_02_F"
    assert [c.name_for(i).split("_")[-1] for i in range(6)]==list("RFRFRF")
    print("PASS 6/9: host explicit alternating positions")

    class FakeSerial:
        def __init__(self,lines):self.lines=list(lines);self.sent=[]
        def write(self,b):self.sent.append(b.decode().strip());return len(b)
        def flush(self):pass
        def readline(self):
            if self.lines:return (self.lines.pop(0)+"\n").encode()
            return b""
    fake=FakeSerial(["KNX085 ARMED_5S",
                     "KNX085 PULSE_STARTED M1 F duration_ms=30000",
                     "KNX085 STOPPED_ALL_OFF"])
    with tempfile.TemporaryDirectory() as td,patch.object(c,"OUT",Path(td)):
        bad(lambda:c.drive(fake,0))
        assert fake.sent==["ARM MOTORS","PULSE M1 R 30000","STOP"]
        r=json.loads((Path(td)/"KNX097_LEG_01_R.json").read_text("utf8"))
        assert r["start_requested"] and not r["start_ack"]
        assert r["stop_ack"] and not r.get("complete",False)
    print("PASS 7/9: wrong-direction ACK stops without retry")

    # 1000 valid trace entries in 8ms; serial chunk reader must preserve them.
    rows=["KNX085 TRACE_BEGIN count=1000"]
    for j in range(1000):
        t=7+j*8
        rows.append(f"KNX085 TRACE t_ms={t} shunt_raw=600 shunt_uv=6000 bus_mv=3280 valid=1")
    rows.append("KNX085 TRACE_END")
    blob=("\r\n".join(rows)+"\r\n").encode()
    class TraceSerial:
        def __init__(self,blob):self.blob=blob;self.calls=[]
        def reset_input_buffer(self):pass
        def write(self,b):self.calls.append(b.decode().strip())
        def flush(self):pass
        def read(self,size):
            out=self.blob[:size]
            self.blob=self.blob[size:]
            return out
    f=TraceSerial(blob)
    rec,count,total=c.samples_from_raw(f)
    assert len(rec)==1000 and count==1000 and f.calls==["TRACE"]
    assert rec[0]["ms"]==7 and rec[-1]["ms"]==7999 and rec[-1]["ma"]==30.0
    print("PASS 8/9: buffered complete 8ms raw trace parser")

    z=blob.replace(b"KNX085 TRACE t_ms=4007 shunt_raw=600 shunt_uv=6000 bus_mv=3280 valid=1\r\n",b"")
    if z==blob:z=blob.replace(b"KNX085 TRACE t_ms=3999 shunt_raw=600 shunt_uv=6000 bus_mv=3280 valid=1\r\n",b"")
    require_missing=TraceSerial(z)
    bad(lambda:c.samples_from_raw(require_missing))
    print("PASS 9/9: missing raw trace samples block further legs")
    print("KNX097 OFFLINE 9/9 PASS")

if __name__=="__main__":verify()
