#!/usr/bin/env python3
"""KNX101 USB-only five guarded physical position moves / one-shot flashing.

No KNX bus. Connect only RP2040 USB-C/COM7 and a single M1 motor.
No autonomous run or automatic retries. Fresh user authorization required
for additional firmware variants, and each step is separately one-shot.
"""
from __future__ import annotations

import argparse,csv,hashlib,json,re,shutil,subprocess,sys,time
from datetime import datetime
from pathlib import Path
import serial
from serial.tools import list_ports

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"knx097_repeatability"))
import knx097_flash as prior
import knx092_office_usb_m1 as old

OUT=Path(r"C:\ASH\Workspace\Runtime\KNX101")
IMAGE=HERE/".pio"/"build"/"knx101_m1_position_diag_5step"/"firmware.uf2"
PIN_SHA="9900c58675f09e9c7bcd832a3eb224af480e1725046e957898bcc78e8b296a76"
PIN_BYTES=250880
BOARD_SERIAL="E464401787522D33"
SIGNATURE="KNX101 POSITION_USB_ONLY steps=5 order=R,500,250,750,F full_r_ms=24388 full_f_ms=22751 limit_ma=120 rise_ma=45 after_ms=450 consecutive=6 motor_gate=1"
POS=re.compile(r"KNX101 POSITION phase=([A-Z_]+) evidence=([A-Z_]+) position_r_permille=(\d+) desired_r_permille=(\d+) planned_ms=(\d+) step_issued=(\d+) step_completed=(\d+) last_stop=([A-Z_]+) driver=([A-Z]+) motors_low=(\d)")
INA=re.compile(r"KNX085 INA read_ok=(\d) bus_mv=(\d+) current_ma_assuming_R29_200mohm=(-?\d+) overflow=(\d) idle_ok=(\d)(?:\s+.*)?")
START=re.compile(r"KNX101 STARTED step=(\d) dir=([RF]) target_r_permille=(\d+) planned_ms=(\d+)")
CUTOFF=re.compile(r"KNX101 STOP_CANDIDATE reason=([A-Z_]+) t_ms=(\d+) current_ma=(-?\d+) bus_mv=(\d+)")
ENDED=re.compile(r"KNX101 MOTOR_ENDED state=([A-Z]+) reason=([A-Z_]+)")
LIVE=re.compile(r"KNX101 LIVE t_ms=(\d+) current_ma=(-?\d+) shunt_raw=(-?\d+) bus_mv=(\d+)")
HDR=re.compile(r"KNX085 TRACE_BEGIN count=(\d+)")
TRACE=re.compile(r"KNX085 TRACE t_ms=(\d+) shunt_raw=(-?\d+) shunt_uv=(-?\d+) bus_mv=(\d+) valid=(\d)")
STEPS=[
    {"step":1,"command":"SEEK R","direction":"R","target":1000,
     "stop":"ENDSTOP_CANDIDATE","expected_ms":12200,"range_ms":[6000,30000],
     "evidence":"CURRENT_ENDSTOP_CANDIDATE"},
    {"step":2,"command":"SET 500","direction":"F","target":500,
     "stop":"TIMED_TARGET","expected_ms":11376,"range_ms":[10900,11850],
     "evidence":"TIMED_ESTIMATE"},
    {"step":3,"command":"SET 250","direction":"F","target":250,
     "stop":"TIMED_TARGET","expected_ms":5688,"range_ms":[5400,6000],
     "evidence":"TIMED_ESTIMATE"},
    {"step":4,"command":"SET 750","direction":"R","target":750,
     "stop":"TIMED_TARGET","expected_ms":12194,"range_ms":[11800,12600],
     "evidence":"TIMED_ESTIMATE"},
    {"step":5,"command":"SEEK F","direction":"F","target":0,
     "stop":"ENDSTOP_CANDIDATE","expected_ms":17063,"range_ms":[12000,30000],
     "evidence":"CURRENT_ENDSTOP_CANDIDATE"},
]
class Refused(RuntimeError):pass

def need(cond,msg):
    if not cond:raise Refused(msg)

def fingerprint():
    data=IMAGE.read_bytes()
    sha=hashlib.sha256(data).hexdigest()
    need(sha==PIN_SHA and len(data)==PIN_BYTES and data[:4]==bytes.fromhex("5546320a"),
         f"KNX101 image pin mismatch {len(data)}B {sha}")
    return {"path":str(IMAGE),"size":len(data),"sha256":sha}

def board():
    return old.board()

def store(name,report):
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/(name+".json")
    need(not path.exists(),f"refusing to overwrite existing report {path}")
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("EVIDENCE",path,flush=True)
    return path

def command(ser,cmd):
    ser.write((cmd+"\n").encode("ascii"))
    ser.flush()

def consume(ser,seconds,lines,predicate):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        raw=ser.readline()
        if not raw:continue
        line=raw.decode("ascii","replace").strip()
        if not line:continue
        lines.append(line)
        if predicate(line):return line
    return None

def parsed_latest(lines,pattern,msg):
    m=[m for line in lines if (m:=pattern.fullmatch(line))]
    need(bool(m),f"No {msg}: {lines[-8:]}")
    return m[-1]

def identify_and_idle(ser,step=None):
    ser.reset_input_buffer()
    lines=[]
    for _ in range(3):
        command(ser,"KNX101")
        command(ser,"POSSTATUS")
        command(ser,"STATUS")
        command(ser,"INA")
        consume(ser,.8,lines,lambda x:False)
    need(SIGNATURE in lines,"Wrong USB firmware fingerprint (not KNX101)")
    pos=parsed_latest(lines,POS,"KNX101 POSSTATUS")
    ina=parsed_latest(lines,INA,"INA219 idle")
    sta=[x for x in lines if x.startswith("KNX085 STATUS")]
    need(sta and "tx_low=1 motors_low=1" in sta[-1] and
         "motor_state=IDLE" in sta[-1],"Motor GPIO/KNX_TX not LOW+IDLE")
    need(int(ina.group(1))==1 and int(ina.group(4))==0 and int(ina.group(5))==1
         and 3100<=int(ina.group(2))<=3450
         and -5<=int(ina.group(3))<=3,"INA219 invalid idle/current/rail")
    info={"phase":pos.group(1),"evidence":pos.group(2),
          "position":int(pos.group(3)),"desired":int(pos.group(4)),
          "planned_ms":int(pos.group(5)),"issued":int(pos.group(6)),
          "completed":int(pos.group(7)),"last_stop":pos.group(8),
          "driver":pos.group(9),"gpio_low":pos.group(10)=="1",
          "bus_mv":int(ina.group(2)),"idle_ma":int(ina.group(3)),
          "status":sta[-1]}
    need(info["driver"]=="IDLE" and info["gpio_low"],"Motor not IDLE/GPIO_LOW")
    if step is not None:
        need(info["issued"]==step-1 and info["completed"]==step-1,
             f"Step sequence mismatch for {step}: {info}")
        if step==1:
            need(info["phase"]=="UNREFERENCED" and info["evidence"]=="NONE",
                 "Must start unreferenced firmware for first R SEEK")
        else:
            prior_step=STEPS[step-2]
            need(info["phase"]=="IDLE" and info["evidence"]==prior_step["evidence"]
                 and info["position"]==prior_step["target"],
                 f"Incorrect existing reference/position for step {step}: {info}")
    return info

def verify(need_fresh=False):
    port=board()
    with serial.Serial(port,115200,timeout=.12,write_timeout=.8,
                       rtscts=False,dsrdtr=False) as ser:
        info=identify_and_idle(ser,1 if need_fresh else None)
    print("KNX101_VERIFIED",json.dumps(info),flush=True)
    return info

def flash():
    image=fingerprint()
    port=board()
    sys.path.insert(0,str(HERE.parent/"knx100_position_usb"))
    import knx100_host as prev
    prior_state=prev.verify()
    need(prior_state["phase"]=="FAULT_LATCHED" and
         prior_state["issued"]==2 and prior_state["completed"]==2 and
         prior_state["last_stop"]=="CANCELLED" and
         prior_state["gpio_low"] and prior_state["driver"]=="IDLE" and
         prior_state["idle_ma"]==0,
         "Before reflashing require the documented stopped KNX100 step3 fault")
    OUT.mkdir(parents=True,exist_ok=True)
    flag=OUT/"KNX101_FLASH_STARTED.flag"
    need(not flag.exists(),"No automatic repeated firmware flashing")
    flag.write_text("KNX101 first bootloader flash initiated\n",encoding="utf8")
    report={"image":image,"previous_state":prior_state,"complete":False,
            "motor_commands":0,"bootloader_reset":False}
    try:
        try:
            old.enter_rom(port)
            report["bootloader_reset"]=True
        except Exception as exc:
            # On Windows COM7 may disappear DURING CDC-1200 port config:
            # continue ONLY if exact device is independently in ROM.
            report["cdc_serial_exception"]=repr(exc)
        deadline=time.monotonic()+12
        boots=[]
        while time.monotonic()<deadline:
            boots=[p for p in list_ports.comports()
                   if (p.vid,p.pid)==(0x2E8A,0x0003)]
            if len(boots)==1:break
            time.sleep(.2)
        need(len(boots)==1,"No single RP2040 ROM device, refusing flash")
        info=subprocess.run([str(old.PICOTOOL),"info","-a"],
                            capture_output=True,text=True,errors="replace",
                            timeout=17)
        match=re.search(r"flash id:\s*0x([0-9A-Fa-f]+)",info.stdout)
        need(info.returncode==0 and match and
             match.group(1).upper()==BOARD_SERIAL and
             re.search(r"type:\s+RP2040",info.stdout),
             "Bootloader ID not exactly board previously seen on COM7")
        report["flash_id"]=match.group(1).upper()
        run=subprocess.run([str(old.PICOTOOL),"load","-v","-x",str(IMAGE)],
                           capture_output=True,text=True,errors="replace",
                           timeout=50)
        need(run.returncode==0 and "OK" in run.stdout and
             "rebooted to start the application" in run.stdout,
             "Single picotool verified flash failed; no automatic retry")
        report["picotool_last_lines"]=run.stdout.splitlines()[-6:]
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            try:
                port=board()
                break
            except Exception:time.sleep(.2)
        else:raise Refused("No exact COM7 board after verified flash")
        # Repeat at most a few checks while waiting for INA idle samples.
        checked=None
        for _ in range(6):
            try:
                checked=verify(need_fresh=True)
                break
            except Refused:time.sleep(.5)
        need(checked is not None,"KNX101 fresh IDLE verification not established")
        report["postflight"]=checked
        report["complete"]=True
        print("KNX101_FLASH_SUCCESS_NO_MOTOR",flush=True)
    except Exception as exc:
        report["error"]=repr(exc)
        raise
    finally:
        store("KNX101_FLASH_"+datetime.now().strftime("%Y%m%d_%H%M%S"),report)

def trace_download(ser):
    ser.reset_input_buffer()
    command(ser,"TRACE")
    raw=bytearray()
    end=time.monotonic()+75
    while time.monotonic()<end:
        ch=ser.read(8192)
        if ch:
            raw.extend(ch)
            if b"KNX085 TRACE_END" in raw:break
    else:raise Refused("Entire INA trace was not downloaded")
    lines=raw.decode("ascii","replace").splitlines()
    header=[m for x in lines if (m:=HDR.fullmatch(x))]
    need(len(header)==1 and "KNX085 TRACE_END" in lines,"TRACE header/end missing")
    announced=int(header[0].group(1))
    values=[]
    for line in lines:
        m=TRACE.fullmatch(line)
        if not m:continue
        t,shunt,uv,bus,valid=map(int,m.groups())
        need(uv==shunt*10 and valid==1 and 3100<=bus<=3450,
             f"Invalid shunt/current/voltage {line}")
        values.append({"ms":t,"shunt_raw":shunt,"shunt_uV":uv,
                       "bus_mv":bus,"valid":True,"ma":round(uv/200,3)})
    need(announced==len(values) and 200<=announced<=4800,
         f"Incomplete INA trace: firmware {announced} host {len(values)}")
    need(all(values[i+1]["ms"]-values[i]["ms"]==8 for i in range(len(values)-1)),
         "Noncontinuous 8ms sampling in INA trace")
    return values,len(raw)

def pulse_step(index):
    need(1<=index<=5,"Only five fixed operations are supported")
    step=STEPS[index-1]
    need(fingerprint()["sha256"]==PIN_SHA,"Image pin failure")
    OUT.mkdir(parents=True,exist_ok=True)
    basename=f"KNX101_STEP_{index:02d}_{step['direction']}"
    flag=OUT/(basename+"_STARTED.flag")
    file=OUT/(basename+".json")
    need(not flag.exists() and not file.exists(),"One-shot step already used; no retry")
    # Prior completed step report must be both on disk and on MCU.
    if index>1:
        prev=OUT/(f"KNX101_STEP_{index-1:02d}_{STEPS[index-2]['direction']}.json")
        need(prev.is_file(),"Previous step report missing")
        doc=json.loads(prev.read_text("utf8"))
        need(doc.get("complete") and doc.get("postflight",{}).get("completed")==index-1,
             "Prior physical step did not complete successfully")
    port=board()
    log=[]
    report={"step":step,"time":datetime.now().isoformat(),
            "started":False,"complete":False,"motor_cutoff":None,
            "end_ack":None,"postflight":None,"raw_sample_count":0}
    with serial.Serial(port,115200,timeout=.13,write_timeout=.8,
                       rtscts=False,dsrdtr=False) as ser:
        before=identify_and_idle(ser,index)
        report["preflight"]=before
        flag.write_text(datetime.now().isoformat()+" user-authorized physical step "+step["command"]+"\n",
                        encoding="utf8")
        print("KNX101_STEP_ARMING",index,step["command"],flush=True)
        try:
            command(ser,"ARM MOTORS")
            ack=consume(ser,2,log,lambda x:x=="KNX101 ARMED_5S" or x.startswith("KNX101 REFUSED_"))
            need(ack=="KNX101 ARMED_5S",f"ARM refused: {ack}")
            command(ser,step["command"])
            ack=consume(ser,2,log,lambda x:x.startswith("KNX101 STARTED") or
                        x.startswith("KNX101 REFUSED_") or
                        x.startswith("KNX101 FAILED_"))
            m=START.fullmatch(ack or "")
            need(m and int(m.group(1))==index and m.group(2)==step["direction"]
                 and int(m.group(3))==step["target"] and
                 (int(m.group(4))==30000 if step["command"].startswith("SEEK")
                  else abs(int(m.group(4))-step["expected_ms"])<=32),
                 f"Wrong output/motor start ack {ack!r}")
            report["started"]=True
            report["ack"]=ack
            deadline=time.monotonic()+33
            last_live=time.monotonic()
            last_logged_ms=0
            while time.monotonic()<deadline:
                line=ser.readline().decode("ascii","replace").strip()
                if line:
                    log.append(line)
                    live=LIVE.fullmatch(line)
                    if live:
                        last_live=time.monotonic()
                        ms,ma,_,bus=map(int,live.groups())
                        if ms-last_logged_ms>=4000:
                            print(f"KNX101_LIVE step={index} t={ms/1000:.2f}s I={ma}mA U={bus}mV",flush=True)
                            last_logged_ms=ms
                        need(ma<115 and 3100<=bus<=3450,
                             f"Host warning motor overcurrent/supply {line}")
                    stop=CUTOFF.fullmatch(line)
                    if stop:
                        report["motor_cutoff"]={"reason":stop.group(1),
                                "ms":int(stop.group(2)),
                                "ma":int(stop.group(3)),
                                "bus_mv":int(stop.group(4))}
                    if ENDED.fullmatch(line):
                        report["motor_ended"]=line
                        break
                need(time.monotonic()-last_live<=3,
                     "Motor telemetry stopped >3s; STOP needed")
            need(report.get("motor_cutoff") is not None,
                 "Missing KNX101 MCU reason and current timestamp")
            c=report["motor_cutoff"]
            need(c["reason"]==step["stop"] and
                 step["range_ms"][0]<=c["ms"]<=step["range_ms"][1],
                 f"Abnormal motor cutoff {c}, stop step series")
            need(report.get("motor_ended","").startswith("KNX101 MOTOR_ENDED state=FAULT"),
                 "Motor did not report force-off FAULT state")
            print("KNX101_MCU_OFF",index,c,flush=True)
            # Required: settle after motor current removed before INA idle sample.
            time.sleep(.3)
            command(ser,"POSACKOFF")
            got=consume(ser,3,log,lambda x:x.startswith("KNX101 POSACKOFF_"))
            need(got=="KNX101 POSACKOFF_COMPLETE",
                 f"INA/GPIO off proof or position acceptance missing: {got}")
            report["end_ack"]=got
            after=identify_and_idle(ser)
            need(after["completed"]==index and after["issued"]==index and
                 after["phase"]=="IDLE" and after["evidence"]==step["evidence"] and
                 after["position"]==step["target"],
                 f"Wrong M1 position snapshot after stop {after}")
            report["postflight"]=after
            vals,rawbytes=trace_download(ser)
            need(abs(vals[-1]["ms"]-c["ms"])<=8,
                 "Last INA raw time differs from firmware cutoff")
            report["raw_sample_count"]=len(vals)
            report["trace_received_bytes"]=rawbytes
            report["first_last_ms"]=[vals[0]["ms"],vals[-1]["ms"]]
            report["max_raw_current_ma"]=max(v["ma"] for v in vals)
            report["running_median_ma"]=(sorted(v["ma"] for v in vals)[len(vals)//2])
            csvp=OUT/(basename+".csv")
            need(not csvp.exists(),"Refuse overwrite prior current log")
            with csvp.open("w",newline="",encoding="utf8") as file:
                writer=csv.DictWriter(file,fieldnames=list(vals[0]))
                writer.writeheader()
                writer.writerows(vals)
            report["complete"]=True
            print("KNX101_STEP_PASS",index,c["reason"],c["ms"],"ms",len(vals),"raw samples",flush=True)
        except Exception as exc:
            report["error"]=repr(exc)
            try:
                command(ser,"STOP")
                consume(ser,2,log,lambda x:x=="KNX101 STOPPED_ALL_OFF")
            except Exception as stop_exc:
                report["emergency_stop_error"]=repr(stop_exc)
            raise
        finally:
            report["rx_excerpt"]=log[-100:]
            store(basename,report)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["pin","flash","verify","step"])
    parser.add_argument("--step",type=int)
    opt=parser.parse_args()
    try:
        if opt.command=="pin":
            print("KNX101_PIN",json.dumps(fingerprint()))
        elif opt.command=="flash":flash()
        elif opt.command=="verify":verify()
        else:
            need(opt.step is not None,"--step needed")
            pulse_step(opt.step)
    except Exception as exc:
        print("KNX101_REFUSED_OR_ABORTED",repr(exc),file=sys.stderr,flush=True)
        raise SystemExit(5)

if __name__=="__main__":
    main()
