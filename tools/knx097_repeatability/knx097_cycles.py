#!/usr/bin/env python3
"""KNX097 M1 reversal repeatability: TWO verified phases, max 6 protected legs.

Phase 1: --start 0 --count 2, R then F.
Phase 2: --start 2 --count 4, R F R F, only after reviewing phase 1.
Exactly one ARM and one 30000ms max MCU-cutoff PULSE per leg.
No retries, autonomous motor actions, homing position writes, or Git pushes.
"""
from __future__ import annotations
import argparse,csv,json,re,sys,time,statistics
from datetime import datetime
from pathlib import Path
import serial

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent))
import knx097_flash as fw
import knx092_office_usb_m1 as old
OUT=fw.OUT
HDR=re.compile(r"KNX085 TRACE_BEGIN count=(\d+)")
TRACE=old.TRACE
CAND=re.compile(r"KNX097 ENDSTOP_CANDIDATE kind=(LOAD_RISE|CURRENT_CUT) t_ms=(\d+) current_ma=(-?\d+) bus_mv=(\d+)")
LIVE=re.compile(r"KNX097 LIVE t_ms=(\d+) current_ma=(-?\d+) shunt_raw=(-?\d+) bus_mv=(\d+)")
ENDED=re.compile(r"KNX085 MOTOR_ENDED state=(IDLE|FAULT)")

def require(v,msg):
    if not v:raise fw.Stop(msg)

def name_for(i):
    return f"KNX097_LEG_{i+1:02d}_{'R' if i%2==0 else 'F'}"

def cmd(ser,text):
    ser.write((text+"\n").encode("ascii"))
    ser.flush()

def lines_until(ser,predicate,seconds,all_lines):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        line=ser.readline().decode("ascii","replace").strip()
        if not line:continue
        all_lines.append(line)
        if predicate(line):return line
    return None

def samples_from_raw(ser):
    ser.reset_input_buffer()
    cmd(ser,"TRACE")
    data=bytearray()
    deadline=time.monotonic()+65
    while time.monotonic()<deadline:
        chunk=ser.read(8192)
        if chunk:
            data.extend(chunk)
            if b"KNX085 TRACE_END" in data:break
    else:raise fw.Stop("TRACE_END not received; refuse next leg")
    rows=data.decode("ascii","replace").splitlines()
    begins=[m for x in rows if (m:=HDR.fullmatch(x))]
    require(len(begins)==1 and "KNX085 TRACE_END" in rows,"TRACE lacks one BEGIN/END")
    announced=int(begins[0].group(1))
    out=[]
    for x in rows:
        m=TRACE.fullmatch(x)
        if not m:continue
        t,raw,uv,bus,valid=map(int,m.groups())
        require(raw*10==uv,"INA219 trace raw-to-voltage mismatch")
        out.append({"ms":t,"shunt_raw":raw,"shunt_uV":uv,"bus_mv":bus,
                    "valid":valid==1,"ma":round(uv/200,3)})
    require(announced==len(out) and 1000<=announced<=4200,
            f"TRACE incomplete: MCU={announced} host={len(out)}")
    require(all(x["valid"] for x in out),"At least one invalid INA trace sample")
    require(all(out[j+1]["ms"]-out[j]["ms"]==8 for j in range(len(out)-1)),
            "INA trace timestamps have gaps or duplicates")
    return out,announced,len(data)

def probe_idle(ser,expected_leg):
    ser.reset_input_buffer()
    lines=[]
    for j in range(5):
        cmd(ser,"STATUS")
        cmd(ser,"INA")
        cmd(ser,"KNX097")
        limit=time.monotonic()+.46
        while time.monotonic()<limit:
            x=ser.readline().decode("ascii","replace").strip()
            if x:lines.append(x)
        if j<4:time.sleep(.21)
    states=[old.STATUS.match(x) for x in lines if x.startswith("KNX085 STATUS")]
    sensors=[old.INA.match(x) for x in lines if x.startswith("KNX085 INA read_ok=")]
    require(len(states)>=4 and len(sensors)>=4,"Insufficient post-run idle checks")
    require(all(m and m.group(1)=="1" and m.group(2)=="1"
                and m.group(9)=="IDLE" for m in states[-4:]),
            "GPIOs are not LOW or motor state not IDLE")
    require(all(m and m.group(1)=="1" and m.group(4)=="0" and m.group(5)=="1"
                and -5<=int(m.group(3))<=3 and 3100<=int(m.group(2))<=3450
                for m in sensors[-4:]),
            "INA219 current/voltage idle not stable after STOP")
    version=fw.parse_version(lines)
    require(version["legs_done"]==expected_leg,"MCU leg counter unexpected after stop")
    return {"version":version,"bus_mv":int(sensors[-1].group(2)),
            "idle_ma":int(sensors[-1].group(3)),"gpio_low":True}

def drive(ser,i):
    direction="R" if i%2==0 else "F"
    label=name_for(i)
    flag=OUT/(label+"_STARTED.flag")
    report_path=OUT/(label+".json")
    require(not flag.exists() and not report_path.exists(),
            f"Motor leg {label} already attempted. No retry")
    report={"leg":i+1,"direction":direction,"timestamp":datetime.now().isoformat(),
            "start_requested":False,"start_ack":False,
            "motor_end":None,"candidate":None,
            "stop_ack":False,"sample_count":0,
            "source":"live COM7 RP2040 exact ID",
            "position_reference_committed":False}
    flag.write_text(f"{label}: one-shot motor test started\n","utf8")
    print("KNX097_START",label,flush=True)
    lines=[]
    try:
        cmd(ser,"ARM MOTORS")
        armed=lines_until(ser,lambda x:x=="KNX085 ARMED_5S" or "REFUSED_ARM" in x,2,lines)
        require(armed=="KNX085 ARMED_5S","M1 ARM failed; no PULSE")
        cmd(ser,f"PULSE M1 {direction} 30000")
        report["start_requested"]=True
        expected=f"KNX085 PULSE_STARTED M1 {direction} duration_ms=30000"
        ack=lines_until(ser,lambda x:x.startswith("KNX085 PULSE_STARTED")
                         or "REFUSED_" in x,2,lines)
        require(ack==expected,f"Wrong M1 {direction} 30s ACK: {ack!r}")
        report["start_ack"]=True
        end=time.monotonic()+34
        last_live=time.monotonic()
        last_user_log=0
        while time.monotonic()<end:
            x=ser.readline().decode("ascii","replace").strip()
            if x:
                if (m:=LIVE.fullmatch(x)):
                    last_live=time.monotonic()
                    ms,ma,raw,bus=map(int,m.groups())
                    if ms-last_user_log>=3000:
                        print("KNX097_LIVE",f"{label} t={ms/1000:.1f}s I={ma}mA U={bus}mV",flush=True)
                        last_user_log=ms
                    if ma>=115 or bus<3100 or bus>3450:
                        raise fw.Stop(f"Host sees dangerous current/voltage: {x}")
                if (m:=CAND.fullmatch(x)):
                    report["candidate"]={"type":m.group(1),"ms":int(m.group(2)),
                                         "current_ma":int(m.group(3)),
                                         "bus_mv":int(m.group(4))}
                if (m:=ENDED.fullmatch(x)):
                    report["motor_end"]=m.group(1)
                    break
                lines.append(x)
            if time.monotonic()-last_live>3:
                raise fw.Stop("USB live telemetry silent >3s during motor: STOP")
        require(report["motor_end"]=="FAULT" and report["candidate"],
                "Motor ran to timer/no threshold or no verified ENDSTOP")
        c=report["candidate"]
        require(c["type"]=="LOAD_RISE" and 12000<=c["ms"]<=29999,
                "Short/ambiguous endpoint or CURRENT_CUT: abort series")
    except Exception as e:
        report["error"]=str(e)
    finally:
        try:
            cmd(ser,"STOP")
            stopped=lines_until(ser,lambda x:x=="KNX085 STOPPED_ALL_OFF",2,lines)
            report["stop_ack"]=stopped=="KNX085 STOPPED_ALL_OFF"
        except Exception as e:
            report["stop_error"]=repr(e)
    if not report["stop_ack"]:
        report_path.write_text(json.dumps(report,indent=2)+"\n","utf8")
        raise fw.Stop(f"STOP unconfirmed after {label}; do NOT continue")
    if report.get("error"):
        report_path.write_text(json.dumps(report,indent=2)+"\n","utf8")
        raise fw.Stop(f"{label} stopped, aborted: {report['error']}")
    try:
        # The MCU keeps the entire trace until next PULSE. A buffered read avoids
        # the dropped 413-line gap seen during KNX096 line-by-line trace dump.
        trace,announced,received_bytes=samples_from_raw(ser)
        report["sample_count"]=len(trace)
        report["trace_bytes"]=received_bytes
        report["trace_first_ms"]=trace[0]["ms"]
        report["trace_last_ms"]=trace[-1]["ms"]
        report["current_start_max_ma"]=max(x["ma"] for x in trace if x["ms"]<450)
        cruise=[x["ma"] for x in trace if 1000<=x["ms"]<trace[-1]["ms"]-500]
        report["current_cruise_median_ma"]=round(statistics.median(cruise),3) if cruise else None
        report["current_peak_ma"]=max(x["ma"] for x in trace)
        report["last_raw_ma"]=trace[-1]["ma"]
        report["bus_mv_min"]=min(x["bus_mv"] for x in trace)
        report["bus_mv_max"]=max(x["bus_mv"] for x in trace)
        require(abs(trace[-1]["ms"]-report["candidate"]["ms"])<=8,
                "Motor cutoff time vs trace last timestamp differs")
        report["postflight"]=probe_idle(ser,expected_leg=i+1)
        v=report["postflight"]["version"]
        next_dir="F" if direction=="R" else "R"
        require(v["next_dir"]==next_dir and v["last_dir"]==direction
                and v["last_kind"]=="LOAD_RISE",
                "MCU did not advance confirmed leg in expected direction")
        # Physical stop is a CANDIDATE, not automatically 0/100% position.
        report["complete"]=True
        with (OUT/(label+".csv")).open("w",encoding="utf8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(trace[0]))
            writer.writeheader();writer.writerows(trace)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf8")
        print("KNX097_LEG_OK",json.dumps({"leg":i+1,"dir":direction,"travel_s":c["ms"]/1000,
            "end_ma":c["current_ma"],"samples":len(trace),"running_median_ma":report["current_cruise_median_ma"]}),flush=True)
        return report
    except Exception as e:
        report["recovery_error"]=str(e)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf8")
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--count",type=int,required=True)
    args=p.parse_args()
    require((args.start,args.count) in {(0,2),(2,4)},
            "Only explicit reviewed 2-leg then 4-leg phases supported")
    OUT.mkdir(parents=True,exist_ok=True)
    validated=fw.verify(require_start=args.start==0)
    require(validated["version"]["legs_done"]==args.start,
            "MCU leg count different from reviewed phase")
    if args.start==2:
        for i in range(2):
            f=OUT/(name_for(i)+".json")
            require(f.is_file(),f"Previous phase evidence missing {f}")
            d=json.loads(f.read_text("utf8"))
            require(d.get("complete") and d["postflight"]["version"]["legs_done"]==i+1,
                    "Prior phase not validated; refuse continuation")
        require(validated["version"]["next_dir"]=="R" and
                validated["version"]["last_kind"]=="LOAD_RISE",
                "Firmware not ready for R on phase2")
    path=OUT/(f"KNX097_PHASE_{args.start+1}_TO_{args.start+args.count}_STARTED.flag")
    require(not path.exists(),"Phase already attempted; no automatic rerun")
    path.write_text(datetime.now().isoformat()+"\n","utf8")
    successes=[]
    try:
        with serial.Serial(old.board(),115200,timeout=.13,write_timeout=.5) as ser:
            for i in range(args.start,args.start+args.count):
                # Maintain idle in both directions, 3+ seconds between stops.
                state=probe_idle(ser,expected_leg=i)
                if i>0:
                    time.sleep(3)
                    state=probe_idle(ser,expected_leg=i)
                require(state["version"]["next_dir"]==("R" if i%2==0 else "F"),
                        "MCU direction mismatch immediately before ARM")
                result=drive(ser,i)
                prior=next((x for x in successes if x["direction"]==result["direction"]),None)
                if args.start==2 and prior is None:
                    index=0 if result["direction"]=="R" else 1
                    prior=json.loads((OUT/(name_for(index)+".json")).read_text("utf8"))
                if prior:
                    ref=prior["candidate"]["ms"];ms=result["candidate"]["ms"]
                    require(abs(ms-ref)<=max(4000,.2*ref),
                            f"Timing drift >20%/4s in {result['direction']}: {ms} vs {ref}ms")
                successes.append(result)
            print("KNX097_PHASE_OK",args.start+1,args.start+args.count,flush=True)
    except Exception as e:
        print("KNX097_PHASE_ABORT",str(e),file=sys.stderr,flush=True)
        raise SystemExit(5)
    for r in successes:print("TIMING",r["leg"],r["direction"],r["candidate"]["ms"],flush=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("KNX097_ABORT",repr(exc),file=sys.stderr,flush=True)
        raise SystemExit(5)
