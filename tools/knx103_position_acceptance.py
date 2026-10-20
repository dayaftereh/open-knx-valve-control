#!/usr/bin/env python3
"""KNX103: read-only INA219 source verification and immutable 5-step bench record.

No serial, no GPIO, no USB, no motor commands. Only original completed KNX101
JSON + 8ms CSV traces on LLO Desktop. Freeze the reviewed evidence once
into config/knx103_m1_position_bench.json; subsequent runs require exact match.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(r"C:\ASH\Workspace\Runtime\KNX101")
FROZEN=ROOT/"config"/"knx103_m1_position_bench.json"
STEPS=[
    ("R",1000,12951,1619,"ENDSTOP_CANDIDATE","CURRENT_ENDSTOP_CANDIDATE",None),
    ("F",500,11383,1423,"TIMED_TARGET","TIMED_ESTIMATE",11376),
    ("F",250,5694,712,"TIMED_TARGET","TIMED_ESTIMATE",5688),
    ("R",750,12199,1525,"TIMED_TARGET","TIMED_ESTIMATE",12194),
    ("F",0,16599,2075,"ENDSTOP_CANDIDATE","CURRENT_ENDSTOP_CANDIDATE",None),
]
class Invalid(ValueError):pass
def need(cond,message):
    if not cond:raise Invalid(message)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def first_streak(records,pred,from_ms=450,consecutive=6):
    run=0
    for ms,value in records:
        if ms<from_ms:continue
        run=run+1 if pred(value) else 0
        if run==consecutive:return ms
    return None
def inspect(data_dir,i):
    direction,target,stop_ms,count,kind,evidence,planned=STEPS[i-1]
    stem=f"KNX101_STEP_{i:02d}_{direction}"
    p=Path(data_dir)/stem
    jp=p.with_suffix(".json");cp=p.with_suffix(".csv")
    need(jp.is_file() and cp.is_file(),f"missing original {stem} .json/.csv")
    report=json.loads(jp.read_text(encoding="utf8"))
    step=report.get("step",{})
    need(report.get("complete") is True and report.get("started") is True,
         f"{stem}: incomplete or unacknowledged original motor test")
    need((step.get("step"),step.get("direction"),step.get("target")) ==
         (i,direction,target),f"{stem}: sequence/position mismatch")
    stop=report.get("motor_cutoff",{})
    need((stop.get("reason"),stop.get("ms"))==(kind,stop_ms),
         f"{stem}: unknown firmware cutoff reason/time")
    post=report.get("postflight",{})
    need((post.get("phase"),post.get("evidence"),post.get("position"),
          post.get("issued"),post.get("completed"),post.get("driver"),
          post.get("gpio_low"),post.get("idle_ma")) ==
         ("IDLE",evidence,target,i,i,"IDLE",True,0),
         f"{stem}: wrong position evidence or GPIO/INA not verified off")
    need(report.get("end_ack")=="KNX101 POSACKOFF_COMPLETE",
         f"{stem}: no confirmed independent STOP/INA handshake")
    need(report.get("raw_sample_count")==count,
         f"{stem}: wrong MCU sampled record count")
    diag=[x for x in report.get("rx_excerpt",[]) if "KNX101 START_DIAG_" in x]
    need(diag==["KNX101 START_DIAG_OK pin_latch=1 pin_settled=1 model_ack=1"],
         f"{stem}: no correct GPIO latch/pad/ACK")
    with cp.open("r",newline="",encoding="utf8") as file:
        reader=csv.DictReader(file)
        need(reader.fieldnames==["ms","shunt_raw","shunt_uV","bus_mv","valid","ma"],
             f"{stem}: wrong raw columns")
        rows=list(reader)
    need(len(rows)==count,f"{stem}: raw INA records missing")
    times=[];milliamps=[];bus=[];current_int=[]
    for row in rows:
        ms=int(row["ms"]); raw=int(row["shunt_raw"]);uV=int(row["shunt_uV"])
        volts=int(row["bus_mv"]); val=row["valid"]; current=float(row["ma"])
        need(val=="True" and uV==raw*10 and abs(current-uV/200)<1e-8,
             f"{stem}: invalid INA conversion at {ms}ms")
        need(3100<=volts<=3450 and -5<=current<=120,
             f"{stem}: INA supply/current outside tested guard")
        if times:
            need(ms-times[-1]==8,f"{stem}: lost INA sample before {ms}")
        times.append(ms);milliamps.append(current);bus.append(volts)
        current_int.append((ms,int(raw/20)))
    need(times[0] in (6,7) and times[-1]==stop_ms,
         f"{stem}: trace does not exactly end at MCU cutoff")
    need(int(milliamps[-1])==stop.get("ma") and bus[-1]==stop.get("bus_mv"),
         f"{stem}: raw final current/bus differs from firmware report")
    rise=first_streak(current_int,lambda x:x>=45)
    cut=first_streak(current_int,lambda x:0<=x<=5)
    if kind=="ENDSTOP_CANDIDATE":
        need(rise==stop_ms and cut is None,
             f"{stem}: electrical endstop cutoff not first continuous current rise")
    else:
        need(rise is None and cut is None,
             f"{stem}: timed move had an earlier endstop/current-cut signal")
        need(planned is not None and 0<=stop_ms-planned<=8,
             f"{stem}: timed cutoff did not follow directional 8ms timer")
    return {
      "step":i,"direction":direction,"target_internal_r_permille":target,
      "cutoff_ms":stop_ms,"cutoff_reason":kind,"current_at_stop_ma":stop["ma"],
      "samples":count,"position_evidence":evidence,
      "planned_timed_ms":planned,"timer_overrun_ms":stop_ms-planned if planned is not None else None,
      "raw_current_peak_ma":round(max(milliamps),3),
      "running_current_median_ma":round(statistics.median(
              [current for ms,current in zip(times,milliamps)
               if 1000<=ms<=stop_ms-500] or milliamps),3),
      "bus_mv_min":min(bus),"bus_mv_max":max(bus),
      "start_latch":1,"start_pad_after_1300us":1,"model_start_ack":1,
      "source_trace_csv_sha256":sha(cp),
      "source_result_json_sha256":sha(jp),
      "all_8ms_samples_complete":True,
      "stop_and_idle_acknowledged":True}
def evaluate(data_dir):
    trials=[inspect(data_dir,i) for i in range(1,6)]
    total=sum(x["samples"] for x in trials)
    need(total==7354,"wrong aggregate INA raw sample count")
    expected750=int(round(22751*.75)) # KNX098 mean F full stroke
    return {
      "schema_version":1,"record":"KNX103_M1_USB_POSITION_ACCEPTANCE",
      "date":"2026-10-20","hardware":"OpenKNXValveControl V1.2",
      "serial_number":"E464401787522D33",
      "firmware":"KNX101", "boot_from_fault_latched":"KNX100",
      "source":"original_private_LLO_Desktop_KNX101_csv_json",
      "model_direction":"F_end_is_internal_0_R_end_is_internal_1000",
      "mechanical_valve_open_close_mapped":False,
      "absolute_mid_position_encoder_verified":False,
      "complete_8ms_ina_samples":total,
      "full_5_step_sequence_complete":True,
      "trials":trials,
      "timed_cutoff_jitter_ms":[x["timer_overrun_ms"] for x in trials if x["timer_overrun_ms"] is not None],
      "final_F_reference":{"internal_r_permille":0,"current_endstop_candidate":True},
      "F_reference_from_internal_750":{
         "expected_ms_by_KNX098":expected750,
         "actual_ms":trials[-1]["cutoff_ms"],
         "difference_actual_minus_expected_ms":trials[-1]["cutoff_ms"]-expected750,
         "not_measured_absolute_position_accuracy":True
      },
      "release_status":"USB_testbench_only_no_KNX_ETS_release_no_physical_midstroke_metrology"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=DATA)
    ap.add_argument("--profile",type=Path,default=FROZEN)
    ap.add_argument("--freeze",action="store_true")
    args=ap.parse_args()
    accepted=evaluate(args.data)
    if args.freeze:
        need(not args.profile.exists(),"Freeze already exists, no overwrite")
        args.profile.parent.mkdir(parents=True,exist_ok=True)
        args.profile.write_text(json.dumps(accepted,ensure_ascii=False,indent=2)+"\n",
                                encoding="utf8",newline="\n")
        print("KNX103_FROZEN",args.profile)
    else:
        need(args.profile.is_file(),"Frozen record does not exist")
        prior=json.loads(args.profile.read_text(encoding="utf8"))
        need(prior==accepted,"Changed data or threshold from SHA-pinned KNX103 record")
        print("KNX103_ORIGINAL_EVIDENCE_VERIFIED",args.profile)
    print("KNX103_ALL_FIVE_PASS",json.dumps({
        "steps":[(x["step"],x["cutoff_ms"],x["cutoff_reason"],x["samples"]) for x in accepted["trials"]],
        "samples":accepted["complete_8ms_ina_samples"],
        "timer_jitter_ms":accepted["timed_cutoff_jitter_ms"],
        "F_homing_residual_ms":accepted["F_reference_from_internal_750"]["difference_actual_minus_expected_ms"]
    }))
if __name__=="__main__":
    main()
