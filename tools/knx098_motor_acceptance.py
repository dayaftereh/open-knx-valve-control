#!/usr/bin/env python3
"""KNX098: NO MOTOR/USB action. Freeze/verify KNX097 six-leg bench calibration.

Reads archived .json and .csv traces. Replays INA219 thresholds from raw
8-ms shunt records, measures repeatability, fingerprints original evidence.
The output is a BENCH profile, not a mechanical encoder calibration.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,statistics
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
DEFAULT_DATA=Path(r"C:\ASH\Workspace\Runtime\KNX097")
DEFAULT_PROFILE=REPO/"config"/"knx098_m1_bench_calibration.json"
DIRECTIONS=("R","F","R","F","R","F")
LIMITS={"shunt_milliohms":200,"ina_period_ms":8,"ina_threshold_ma":45,
        "ina_consecutive_samples":6,"ina_startup_ignore_ms":450,
        "current_cut_ma":5,"absolute_current_limit_ma":120,
        "min_full_stroke_ms":12000,"max_stroke_ms":30000,
        "motor_bus_min_mv":3100,"motor_bus_max_mv":3450,
        "idle_current_limit_ma":25}
class Rejected(ValueError):pass

def require(ok,reason):
    if not ok:raise Rejected(reason)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def first_streak(series,predicate,threshold_count=6,from_ms=450):
    streak=0
    for t,ma in series:
        if t<from_ms:continue
        streak=streak+1 if predicate(ma) else 0
        if streak==threshold_count:return t
    return None

def compute_stats(times):
    avg=statistics.mean(times)
    st=statistics.pstdev(times)
    return {"n":len(times),"mean_ms":round(avg,3),
            "stddev_ms":round(st,3),
            "spread_ms":max(times)-min(times),
            "cv_percent":round(100*st/avg,4),
            "min_ms":min(times),"max_ms":max(times)}

def inspect_leg(data_dir,i,direction):
    prefix=f"KNX097_LEG_{i:02d}_{direction}"
    jp=data_dir/(prefix+".json")
    cp=data_dir/(prefix+".csv")
    require(jp.is_file() and cp.is_file(),f"{prefix}: missing original files")
    doc=json.loads(jp.read_text(encoding="utf8"))
    with cp.open(encoding="utf8",newline="") as f:
        rows=list(csv.DictReader(f))
    require(len(rows)>1500 and len(rows)==doc["sample_count"],f"{prefix}: truncated CSV")
    require(doc.get("complete") and doc.get("stop_ack") and
            doc.get("motor_end")=="FAULT" and
            doc.get("start_requested") and doc.get("start_ack"),
            f"{prefix}: motor did not finish with acknowledged LOAD_RISE")
    require(doc["direction"]==direction and doc["leg"]==i and
            doc["candidate"]["type"]=="LOAD_RISE" and
            doc["candidate"]["ms"]>=LIMITS["min_full_stroke_ms"] and
            doc["candidate"]["ms"]<LIMITS["max_stroke_ms"],
            f"{prefix}: direction/endstop/elapsed outside bounds")
    post=doc["postflight"]
    require(post.get("gpio_low") and -5<=post.get("idle_ma",999)<=3
            and LIMITS["motor_bus_min_mv"]<=post.get("bus_mv",0)<=LIMITS["motor_bus_max_mv"]
            and post["version"]["legs_done"]==i and
            post["version"]["last_dir"]==direction and
            post["version"]["last_kind"]=="LOAD_RISE",
            f"{prefix}: postflight/MCU sequence mismatch")
    series=[];bus=[]
    for row in rows:
        t=int(row["ms"])
        raw=int(row["shunt_raw"])
        uv=int(row["shunt_uV"])
        ma=float(row["ma"])
        mv=int(row["bus_mv"])
        require(row["valid"]=="True" and uv==raw*10 and
                abs(ma-uv/LIMITS["shunt_milliohms"])<1e-6 and
                LIMITS["motor_bus_min_mv"]<=mv<=LIMITS["motor_bus_max_mv"] and
                -5<=ma<=LIMITS["absolute_current_limit_ma"],
                f"{prefix}: invalid INA raw shunt/current/voltage or overcurrent at {t}ms")
        series.append((t,ma))
        bus.append(mv)
    require(series[0][0]==7 and series[-1][0]==doc["candidate"]["ms"]
            and all(series[j+1][0]-series[j][0]==LIMITS["ina_period_ms"]
                    for j in range(len(series)-1)),
            f"{prefix}: missing/duplicate/shifted INA samples")
    threshold=LIMITS["ina_threshold_ma"]
    found=first_streak(series,lambda ma:ma>=threshold)
    cut=first_streak(series,lambda ma:0<=ma<=LIMITS["current_cut_ma"])
    require(found==doc["candidate"]["ms"] and cut is None,
            f"{prefix}: INΑ219 guard replay contradicts motor cutoff")
    require(int(series[-1][1])==doc["candidate"]["current_ma"],
            f"{prefix}: firmware integer cutoff not equal to last raw sample")
    cruise=[ma for t,ma in series if 1000<=t<series[-1][0]-500]
    require(cruise,"No stable running-current interval")
    baseline=statistics.median(cruise)
    require(abs(baseline-doc["current_cruise_median_ma"])<=0.05,
            f"{prefix}: recorded cruise current median mismatch")
    isolated_high=sum(ma>=threshold for t,ma in series if
                      t>=LIMITS["ina_startup_ignore_ms"] and
                      t<series[-1][0]-500)
    return {"leg":i,"cycle":(i+1)//2,"direction":direction,
            "cutoff_ms":doc["candidate"]["ms"],
            "cutoff_ma":doc["candidate"]["current_ma"],
            "sample_count":len(rows),
            "cruise_median_ma":round(baseline,3),
            "prior_isolated_over_threshold_samples":isolated_high,
            "current_peak_ma":max(ma for _,ma in series),
            "bus_min_mv":min(bus),"bus_max_mv":max(bus),
            "csv_sha256":digest(cp),"json_sha256":digest(jp),
            "stop_ack":True,"gpio_low":True,
            "full_trace_8ms":True,"first_sustained_rise_at_cutoff":True}

def evaluate(data_dir):
    data_dir=Path(data_dir)
    trials=[inspect_leg(data_dir,i,d) for i,d in enumerate(DIRECTIONS,1)]
    stats={d:compute_stats([x["cutoff_ms"] for x in trials
                            if x["direction"]==d]) for d in ("R","F")}
    require(all(v["n"]==3 and v["spread_ms"]<=500 and v["cv_percent"]<1.0
                for v in stats.values()),
            "KNX097 three-cycle full-stroke repeatability acceptance FAILED")
    require(sum(x["sample_count"] for x in trials)==17678,
            "Unexpected number of original INA records")
    return {"schema_version":1,"id":"KNX098_M1_BENCH",
            "status":"bench_accepted_current_endstop_candidates",
            "test_date":"2026-10-20","source_firmware":"KNX097",
            "hardware":{"board_rev":"V1.2","channel":"M1",
                        "supply":"USB-C_ONLY_OFFICE_BENCH",
                        "ina219_config":"0x399F",
                        "r33_ohms":10,"r34_ohms":10},
            "guards":LIMITS,
            "directional_stroke_ms":{"R":stats["R"]["mean_ms"],
                                     "F":stats["F"]["mean_ms"]},
            "repeatability":stats,
            "source_trials":trials,
            "all_trace_samples":sum(x["sample_count"] for x in trials),
            "acceptance":{"full_stroke_current_detection":True,
                          "six_full_strokes_repeated":True,
                          "all_fault_cutoffs_acknowledged":True,
                          "intermediate_positions_measured":False,
                          "absolute_mechanical_endstops_verified":False,
                          "open_closed_mapping_defined":False,
                          "knx_ets_product_firmware_released":False},
            "use_note":"Bench baseline only; direction F/R is not mapped to open/closed. Use INA stops during reference, never assume encoder-quality mid-stroke positioning."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,default=DEFAULT_DATA)
    p.add_argument("--profile",type=Path,default=DEFAULT_PROFILE)
    p.add_argument("--freeze",action="store_true")
    args=p.parse_args()
    calibration=evaluate(args.data)
    if args.freeze:
        require(not args.profile.exists(),"Calibration already frozen; refuse overwrite")
        args.profile.parent.mkdir(parents=True,exist_ok=True)
        args.profile.write_text(json.dumps(calibration,indent=2,ensure_ascii=False)+"\n",
                                encoding="utf8",newline="\n")
        print("CALIBRATION_FROZEN",args.profile,flush=True)
    else:
        require(args.profile.is_file(),"Calibration profile absent; use --freeze once")
        frozen=json.loads(args.profile.read_text(encoding="utf8"))
        require(frozen==calibration,"Original six traces/calibration differ from accepted snapshot")
        print("CALIBRATION_VERIFIED_IMMUTABLE",args.profile,flush=True)
    print("KNX098_ACCEPT_PASS",json.dumps({"R":calibration["repeatability"]["R"],
           "F":calibration["repeatability"]["F"],
           "raw_samples":calibration["all_trace_samples"]},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
