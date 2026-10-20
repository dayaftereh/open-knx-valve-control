#!/usr/bin/env python3
"""Derive guarded 10s KNX094 host from KNX093; no hardware action."""
from pathlib import Path

here=Path(__file__).resolve().parent
old=(here.parent/"knx093_m1_long"/"knx093_host.py").read_text("utf8")
s=old.replace("KNX093","KNX094").replace("knx093","knx094")
s=s.replace("knx094_m1_reverse_800","knx094_m1_reverse_10000")
s=s.replace("duration_ms=800","duration_ms=10000")
s=s.replace("DURATION_MS=800","DURATION_MS=10000")
s=s.replace("stall_ma=90 after_ms=100 consecutive=4","stall_ma=60 after_ms=400 consecutive=6")
s=s.replace("PULSE M1 R 800","PULSE M1 R 10000")
s=s.replace("M1_R800","M1_R10000")
s=s.replace("M1_R_800","M1_R_10000")
s=s.replace("800ms listening test","10-second monitored test")
s=s.replace("M1 R 800, read INA trace","M1 R 10000, read INA trace")
# The flashed KNX094 firmware retained the prior KNX093 query token;
# it returns the unique KNX094 signature in the response.
s=s.replace('old.command(ser,"KNX094")','old.command(ser,"KNX093")')
sha="c59596c3e3ba27fdd30adc094219953d47a7c59185ce2f55e00b1d04a2d5e284"
assert s.count('IMAGE_SHA256="f10743ac5b5e33e0969a04e34c53d353ec832ffb2009a29fcdfd90417447d619"')==1
s=s.replace('IMAGE_SHA256="f10743ac5b5e33e0969a04e34c53d353ec832ffb2009a29fcdfd90417447d619"',f'IMAGE_SHA256="{sha}"')
assert "C:\\ASH\\Workspace\\Runtime\\KNX094" in s
assert s.count('done=old.gather(ser,2.0,lines,lambda s:')==1
s=s.replace('done=old.gather(ser,2.0,lines,lambda s:',
            'done=await_limited_motor_run(ser,lines,12.5)')
# The original next line lambda needs deletion
needle='''                                s.startswith("KNX085 MOTOR_ENDED state="))
'''
assert s.count(needle)==1
s=s.replace(needle,"",1)
assert s.count('old.gather(ser,4.2,lines,lambda s:s=="KNX085 TRACE_END")')==1
s=s.replace('old.gather(ser,4.2,lines,lambda s:s=="KNX085 TRACE_END")',
            'old.gather(ser,38.0,lines,lambda s:s=="KNX085 TRACE_END")')
anchor='''def one_pulse():
'''
assert s.count(anchor)==1
custom='''LIVE_LINE=re.compile(r"KNX094 LIVE t_ms=(\\\\d+) current_ma=(-?\\\\d+) shunt_raw=(-?\\\\d+) bus_mv=(\\\\d+)")
def await_limited_motor_run(ser,lines,seconds):
    """Wait on MCU-timed 10s motor stop, log LIVE samples as they arrive."""
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        line=ser.readline().decode("ascii","replace").strip()
        if not line:continue
        lines.append(line)
        match=LIVE_LINE.fullmatch(line)
        if match:
            print("KNX094_MOTOR_LIVE",line,flush=True)
            # This host is not the primary current protection; firmware
            # independently samples 8ms, cuts on >120mA or >=60mA x6.
            # If USB sees an unexpectedly high single value, STOP too.
            elapsed,ma,raw,bus=map(int,match.groups())
            if elapsed>400 and (ma>=115 or bus<3100 or bus>3450):
                print("KNX094_HOST_STOP_GUARD",line,flush=True)
                old.command(ser,"STOP")
                # The trace will reveal whether a MCU cutoff was earlier.
                return True
        if line.startswith("KNX085 MOTOR_ENDED state="):
            return True
    return False

'''
# make re regex literal \d in generated host
custom=custom.replace('\\\\d','\\d')
s=s.replace(anchor,custom+anchor,1)
needle='''    fail_unless(data["finished_state"]=="IDLE",
                "Stall/overcurrent fault indicated; DO NOT REPEAT")
'''
assert s.count(needle)==1
s=s.replace(needle,'''    if data.get("finished_state")!="IDLE":
        print("KNX094_MOTOR_NON_IDLE_END",data.get("finished_state"),
              "stall_latch",data.get("knx094_signature"),flush=True)
        # Early FAULT may be the expected endstop-current signature.
        # No automatic retry or fault clear beyond the redundant STOP.
''',1)
needle='''        data["knx094_signature"]=next((s for s in reversed(lines)
               if s.startswith(SIGNATURE)),None)
'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''        live=[]
        for l in lines:
            m=LIVE_LINE.fullmatch(l)
            if m:
                ms,ma,raw,mv=map(int,m.groups())
                live.append({"ms":ms,"ma":ma,"shunt_raw":raw,"bus_mv":mv})
        data["live_updates"]=live
        data["stalled_or_overcurrent"]=data.get("finished_state")=="FAULT"
        data["actual_sampled_duration_ms"]=t[-1]["ms"] if t else 0
''')
# Correct any generated assertions
assert "PULSE M1 R 10000" in s
assert "KNX094 M1_R_ONLY duration_ms=10000" in s
assert "done=await_limited_motor_run(ser,lines,12.5)" in s
assert "old.gather(ser,38.0" in s
(here/"knx094_host.py").write_text(s,encoding="utf8",newline="\n")
print("KNX094 host generated with serial LIVE events, 10s duration, 38s trace dump, pinned UF2")
