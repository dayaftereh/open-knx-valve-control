#!/usr/bin/env python3
"""Generate KNX095 one-shot USB host from tested KNX094."""
from pathlib import Path

folder=Path(__file__).resolve().parent
source=(folder.parent/"knx094_motor_10s"/"knx094_host.py").read_text("utf8")
s=source.replace("KNX094","KNX095").replace("knx094","knx095")
s=s.replace("knx095_m1_reverse_10000","knx095_m1_reference_15000")
s=s.replace("duration_ms=10000","duration_ms=15000")
s=s.replace("DURATION_MS=10000","DURATION_MS=15000")
s=s.replace("M1_R10000","M1_R15000")
s=s.replace("M1_R_10000","M1_R_15000")
s=s.replace("PULSE M1 R 10000","PULSE M1 R 15000")
s=s.replace("M1 reverse 800ms listening test","M1 first bounded 15s endstop search")
s=s.replace("M1 R 800, read INA trace","M1 R 15000, record load-rise/cutoff candidate and trace")
s=s.replace('limit_ma=120 stall_ma=60 after_ms=400 consecutive=6 latched=',
            'limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 cut_ma=5 endstop=')
s=s.replace('old.command(ser,"KNX093")','old.command(ser,"KNX095")')
s=s.replace('all(x==SIGNATURE+"0" for x in good)',
            'all(x==SIGNATURE+"NONE" for x in good)')
s=s.replace('done=await_limited_motor_run(ser,lines,12.5)',
            'done=await_limited_motor_run(ser,lines,18.0)')
s=s.replace('old.gather(ser,38.0,lines,lambda s:s=="KNX085 TRACE_END")',
            'old.gather(ser,70.0,lines,lambda s:s=="KNX085 TRACE_END")')
sha="11e6ee28a6620102426e2af96969861089a6d19fd47ecdf32535f0f9543130b0"
oldsha='IMAGE_SHA256="c59596c3e3ba27fdd30adc094219953d47a7c59185ce2f55e00b1d04a2d5e284"'
assert s.count(oldsha)==1
s=s.replace(oldsha,f'IMAGE_SHA256="{sha}"',1)
marker='''LIVE_LINE=re.compile(r"KNX095 LIVE t_ms=(\\d+) current_ma=(-?\\d+) shunt_raw=(-?\\d+) bus_mv=(\\d+)")
'''
assert s.count(marker)==1
s=s.replace(marker,marker+'''ENDSTOP_CANDIDATE=re.compile(
    r"KNX095 ENDSTOP_CANDIDATE kind=(LOAD_RISE|CURRENT_CUT) t_ms=(\\d+) current_ma=(-?\\d+) bus_mv=(\\d+)")
''',1)
anchor='''        if line.startswith("KNX085 MOTOR_ENDED state="):
            return True
'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        stop=ENDSTOP_CANDIDATE.fullmatch(line)
        if stop:print("KNX095_ENDSTOP_CURRENT_CANDIDATE",line,flush=True)
'''+anchor,1)
needle='''        data["stalled_or_overcurrent"]=data.get("finished_state")=="FAULT"
'''
assert s.count(needle)==1
s=s.replace(needle,'''        candidates=[{"kind":m.group(1),"ms":int(m.group(2)),
                     "ma":int(m.group(3)),"bus_mv":int(m.group(4))}
                    for l in lines if (m:=ENDSTOP_CANDIDATE.fullmatch(l))]
        data["endstop_candidates"]=candidates
        data["search_result"]=(
            "ENDSTOP_CANDIDATE_"+candidates[0]["kind"]
            if candidates and data.get("finished_state")=="FAULT"
            else "TIME_LIMIT_NO_ENDSTOP"
            if data.get("finished_state")=="IDLE"
            else "UNCLASSIFIED_FAULT")
        data["position_zero_committed"]=False
        data["stalled_or_overcurrent"]=data.get("finished_state")=="FAULT"
''',1)
s=s.replace('''        print("M1_R15000_RESULT",json.dumps({k:v for k,v in data.items()
              if k in ("start_acknowledged","finished_state","peak_ma",
              "stop_ack","trace_complete","after_gpio","after_ina",
              "knx095_signature","error")},ensure_ascii=False))''',
'''        print("KNX095_REFERENCE_SEARCH_RESULT",json.dumps({k:v for k,v in data.items()
              if k in ("start_acknowledged","finished_state","search_result",
              "endstop_candidates","position_zero_committed","peak_ma",
              "stop_ack","trace_complete","after_gpio","after_ina",
              "knx095_signature","error")},ensure_ascii=False),flush=True)''')
s=s.replace('''    if data.get("finished_state")!="IDLE":
        print("KNX095_MOTOR_NON_IDLE_END",data.get("finished_state"),
              "stall_latch",data.get("knx095_signature"),flush=True)
        # Early FAULT may be the expected endstop-current signature.
        # No automatic retry or fault clear beyond the redundant STOP.
''',
'''    fail_unless(data.get("search_result")!="UNCLASSIFIED_FAULT",
                "Motor fault without endstop candidate: no homing declared")
    # Only a candidate! Zero position must be independently confirmed.
    # No automatic re-drive or fault-clear.
''')

# KNX095 postflight probe must accept a latched candidate but never permit
# new pulse attempts on a board already carrying homing history.
s=s.replace('def verify_new(port):','def verify_new(port,require_fresh=False):')
old_verify='''    fail_unless(len(good)>=2 and all(x==SIGNATURE+"NONE" for x in good),
                "Wrong KNX095 firmware build, stall guard or armed history")
'''
new_verify='''    endstop_statuses=[x[len(SIGNATURE):] for x in good]
    fail_unless(len(good)>=2 and len(set(endstop_statuses))==1 and
                endstop_statuses[0] in ("NONE","LOAD_RISE","CURRENT_CUT"),
                "Wrong KNX095 firmware build or unexpected endstop state")
    if require_fresh:
        fail_unless(endstop_statuses[0]=="NONE",
                    "M1 reference-search history exists; no automatic re-drive")
'''
assert s.count(old_verify)==1
s=s.replace(old_verify,new_verify)
s=s.replace('baseline["knx095_version_verified"]=good[-1]',
            'baseline["knx095_version_verified"]=good[-1]\n    baseline["endstop_status"]=endstop_statuses[0]')
s=s.replace('report["after"]=verify_new(port)',
            'report["after"]=verify_new(port,require_fresh=True)')
s=s.replace('before=verify_new(port)',
            'before=verify_new(port,require_fresh=True)')

# fixed label signature
assert "KNX095 M1_R_ONLY duration_ms=15000" in s
s=s.replace("KNX095 M1_R_ONLY duration_ms=15000",
            "KNX095 M1_R_SEARCH duration_ms=15000")
assert "PULSE M1 R 15000" in s
assert "old.command(ser,\"KNX095\")" in s
assert "ENDSTOP_CANDIDATE" in s
(folder/"knx095_host.py").write_text(s,encoding="utf8",newline="\n")
print("KNX095 one-shot host generated, 15s max, diagnostic current candidate, no automatic homing/second pulse")
