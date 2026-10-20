#!/usr/bin/env python3
"""Generate KNX096 guarded one-shot USB host from KNX095 tested host."""
from pathlib import Path
here=Path(__file__).resolve().parent
parent=here.parent/"knx095_m1_reference"
s=(parent/"knx095_host.py").read_text("utf8")
s=s.replace("KNX095","KNX096").replace("knx095","knx096")
s=s.replace("knx096_m1_reference_15000","knx096_m1_fullstroke_30000")
s=s.replace("M1_R_SEARCH","M1_F_SEARCH")
s=s.replace("M1 R 15000","M1 F 30000")
s=s.replace("M1_R15000","M1_F30000")
s=s.replace("M1_R_15000","M1_F_30000")
s=s.replace("duration_ms=15000","duration_ms=30000")
s=s.replace("DURATION_MS=15000","DURATION_MS=30000")
s=s.replace("M1 R 800ms","M1 F 30000ms")
s=s.replace("M1 R 800","M1 F 30000")
s=s.replace("first bounded 15s endstop search","bounded 30s opposite end full stroke")
s=s.replace("M1 first bounded 15s endstop search","M1 opposite F stroke bounded to 30 seconds")
s=s.replace('done=await_limited_motor_run(ser,lines,18.0)',
            'done=await_limited_motor_run(ser,lines,33.0)')
s=s.replace('old.gather(ser,70.0,lines,lambda s:s=="KNX085 TRACE_END")',
            'old.gather(ser,140.0,lines,lambda s:s=="KNX085 TRACE_END")')
s=s.replace('IMAGE_SHA256="11e6ee28a6620102426e2af96969861089a6d19fd47ecdf32535f0f9543130b0"',
            'IMAGE_SHA256="4ac733f5a8ad72c4ab3685042f1f390546d66b1b3bb306a0bf8e14db41ffa45c"')
# Distinguish the destination reference endpoint from previous R-side 0% candidate;
# neither is a validated reference until physical/check repeat.
s=s.replace('data["position_zero_committed"]=False',
            'data["position_zero_committed"]=False\n        data["position_fullstroke_committed"]=False')
s=s.replace('\"position_zero_committed\",\"peak_ma\",',
            '\"position_zero_committed\",\"position_fullstroke_committed\",\"peak_ma\",')
# KNX096B: the first F attempt was physically STOPped before the first
# 8ms INA sample by an incorrect R acknowledgement match in the USB host.
# Preserve the first immutable report and marker, and create a DISTINCT
# reviewed test series with its own one-shot marker.
s=s.replace('KNX085 PULSE_STARTED M1 R duration_ms=30000',
            'KNX085 PULSE_STARTED M1 F duration_ms=30000')
s=s.replace('KNX096_M1_F30000_STARTED.flag',
            'KNX096B_M1_F30000_STARTED.flag')
s=s.replace('output_report("KNX096_M1_F30000",data)',
            'output_report("KNX096B_M1_F30000",data)')
prehook='''    lines=data["raw_lines"]
'''
assert s.count(prehook)==1
review='''    first=OUT/"KNX096_M1_F30000_20261020_101611.json"
    prior_marker=OUT/"KNX096_M1_F30000_STARTED.flag"
    fail_unless(first.is_file() and prior_marker.is_file(),
                "Missing preserved evidence of first stopped test")
    failure=json.loads(first.read_text(encoding="utf8"))
    fail_unless(failure.get("command_sent") is True and
                failure.get("start_acknowledged") is False and
                failure.get("stop_ack") is True and
                len(failure.get("motor_trace",[]))==0 and
                "motors_low=1" in str(failure.get("after_gpio","")),
                "First failed F attempt is not a verified safe pre-sample STOP")
    data["review_of_first_aborted_attempt"]=str(first)
    lines=data["raw_lines"]
'''
assert s.count(prehook)==1
s=s.replace(prehook,review,1)
# Important: ensure only permitted USB actions are one F pulse, no retries.
for term in ('PULSE M1 F 30000','KNX096 M1_F_SEARCH duration_ms=30000','KNX096 ENDSTOP_CANDIDATE',
             'KNX096 LIVE','KNX096B_M1_F30000_STARTED.flag','old.command(ser,"KNX096")',
             'endstop_statuses[0] in ("NONE","LOAD_RISE","CURRENT_CUT")',
             'before=verify_new(port,require_fresh=True)'):
    assert term in s,term
assert "PULSE M1 R 15000" not in s
assert "PULSE_STARTED M1 R duration_ms=30000" not in s
assert "PULSE_STARTED M1 F duration_ms=30000" in s
assert "KNX095" not in s
(here/"knx096_host.py").write_text(s,encoding="utf8",newline="\n")
print("KNX096 one-shot host generator PASS, full F stroke, trace140s receive cap, 30s MCU deadline, reference not assigned")
