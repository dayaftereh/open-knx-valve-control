#!/usr/bin/env python3
"""KNX077: one operator-authorized KNX_TX GPIO0 pulse, PicoScope A+B correlation.

NO autonomous pulses. Never repeat FIRE ONE if any result is uncertain.
Requires KNX076 firmware, explicit --execute --confirm-lab-setup,
strict idle voltage/USB STATUS gates, scopes A=KNX+ B=KNX_TX physical 10x.
Result is a bare 35us GPIO pulse, NOT a KNX group telegram.
"""
from __future__ import annotations
import argparse
import array
import ctypes as ct
from datetime import datetime
import json
import os
from pathlib import Path
import statistics
import time
import serial

PICO_TRANSIENT_STATUSES=(0,0x25,0x27)
SAMPLES_TARGET=1800000
SAMPLES_PER_CALLBACK=30000
INTERVAL_REQUEST_US=1
PICO_RAW_RANGE_A_V=5.0
PICO_RAW_RANGE_B_V=0.5
PHYSICAL_PROBE_ATTENUATION=10.0
BAUD=115200


def get_api(dll, name, signature):
    f=getattr(dll,name)
    f.argtypes=signature
    f.restype=ct.c_uint32
    return f


def check(name,status):
    if status:
        raise RuntimeError(f"{name}: PicoSDK status 0x{status:04X}")


def verify_idle_samples(pre_a,pre_b,max_adc):
    if len(pre_a)<25000 or len(pre_b)<25000:
        raise RuntimeError("insufficient idle scope samples; refusing pulse")
    a_scale=PICO_RAW_RANGE_A_V*PHYSICAL_PROBE_ATTENUATION/max_adc
    b_scale=PICO_RAW_RANGE_B_V*PHYSICAL_PROBE_ATTENUATION/max_adc
    base_a=statistics.median(pre_a)*a_scale
    base_b=statistics.median(pre_b)*b_scale
    max_b=max(pre_b)*b_scale
    print(f"KNX077_BEFORE_PULSE_A_BASELINE={base_a:.3f}V B={base_b:.3f}V B_MAX={max_b:.3f}V",flush=True)
    if not 27.0<=base_a<=35.0:
        raise RuntimeError("KNX+ idle outside safe test envelope")
    if not -0.30<=base_b<=0.30 or max_b>0.6:
        raise RuntimeError("KNX_TX not reliably LOW in preflight")
    return base_a,base_b


def analyze(a_path,b_path,max_adc,dt,firmware_log,driver_overflows,
            commanded_fire,live_idle):
    a=array.array("h");a.frombytes(a_path.read_bytes())
    b=array.array("h");b.frombytes(b_path.read_bytes())
    if len(a)!=len(b):
        raise RuntimeError("scope data alignment broken")
    av=PICO_RAW_RANGE_A_V*PHYSICAL_PROBE_ATTENUATION/max_adc
    bv=PICO_RAW_RANGE_B_V*PHYSICAL_PROBE_ATTENUATION/max_adc
    threshold_count=1.35/bv
    events=[]
    rising=None
    for i,v in enumerate(b):
        if v>threshold_count and rising is None:
            rising=i
        elif v<=threshold_count and rising is not None:
            if i-rising>=4:
                events.append((rising,i))
            rising=None
    if rising is not None:
        events.append((rising,len(b)))
    measurements=[]
    for first,last in events:
        begin=max(0,first-int(750/dt))
        until=max(begin,first-int(50/dt))
        trailing_end=min(len(a),last+int(250/dt))
        before=a[begin:until]
        window=a[max(0,first-int(12/dt)):trailing_end]
        before_v=statistics.median(before)*av if before else None
        low_v=min(window)*av if window else None
        max_v=max(b[first:last])*bv
        a_drop=(before_v-low_v) if before_v is not None and low_v is not None else None
        during=a[first:last]
        during_min=min(during)*av if during else None
        measurements.append({
            "sample_start":first,
            "first_rise_t_s":round(first*dt/1e6,6),
            "width_us":(last-first)*dt,
            "TX_B_maxV":round(max_v,4),
            "A_KNXPLUS_beforeV":round(before_v,4) if before_v is not None else None,
            "A_KNXPLUS_min_duringV":round(during_min,4) if during_min is not None else None,
            "A_KNXPLUS_min_to_plus250usV":round(low_v,4) if low_v is not None else None,
            "A_KNXPLUS_max_dropV":round(a_drop,4) if a_drop is not None else None,
        })
    result={
        "sample_count_A":len(a),"sample_count_B":len(b),
        "dt_us":dt,"scope_adc_max":max_adc,"probe_attenuation_assumed":10,
        "A_channel":"KNX+","B_channel":"STKNX KNX_TX JMP3",
        "A_raw_rangeV":PICO_RAW_RANGE_A_V,"B_raw_rangeV":PICO_RAW_RANGE_B_V,
        "samples_dropped_or_driver_overflow":driver_overflows,
        "fire_one_command_sent":commanded_fire,
        "firmware_messages":firmware_log,
        "preflight_baselineV":{"A":live_idle[0],"B":live_idle[1]},
        "pulses_above_1_35V":len(events),"events":measurements,
        "one_shot_scope_success":len(events)==1 and
           27.0<=measurements[0]["width_us"]<=48.0 and
           measurements[0]["TX_B_maxV"]>=2.2 and
           driver_overflows==0 if measurements else False,
    }
    print("KNX077_SCOPE_RESULT",json.dumps(
        {"samples":len(a),"overflow":driver_overflows,
         "pulse_events":len(events),"events":measurements,
         "scope_success":result["one_shot_scope_success"]},
        ensure_ascii=True),flush=True)
    return result


def run_test(args):
    if not args.execute or not args.confirm_lab_setup:
        raise RuntimeError("Explicit --execute AND --confirm-lab-setup required")
    args.outdir.mkdir(parents=True,exist_ok=True)
    stem="KNX077_SCOPE_AB_ONESHOT_"+datetime.now().strftime("%Y%m%d_%H%M%S")
    file_a=args.outdir/(stem+"_A_KNXPLUS.s16le")
    file_b=args.outdir/(stem+"_B_TX.s16le")
    file_json=args.outdir/(stem+"_result.json")
    file_csv=args.outdir/(stem+"_event.csv")
    if not (args.sdk/"ps3000a.dll").exists():
        raise RuntimeError("PicoSDK DLL missing")
    os.add_dll_directory(str(args.sdk))
    dll=ct.WinDLL(str(args.sdk/"ps3000a.dll"))
    op=get_api(dll,"ps3000aOpenUnit",[ct.POINTER(ct.c_int16),ct.c_char_p])
    stop=get_api(dll,"ps3000aStop",[ct.c_int16])
    close=get_api(dll,"ps3000aCloseUnit",[ct.c_int16])
    channel=get_api(dll,"ps3000aSetChannel",[
        ct.c_int16,ct.c_int32,ct.c_int16,ct.c_int32,ct.c_int32,ct.c_float])
    adc_max=get_api(dll,"ps3000aMaximumValue",[
        ct.c_int16,ct.POINTER(ct.c_int16)])
    setbuf=get_api(dll,"ps3000aSetDataBuffer",[
        ct.c_int16,ct.c_int32,ct.POINTER(ct.c_int16),ct.c_int32,ct.c_uint32,ct.c_int32])
    streaming=get_api(dll,"ps3000aRunStreaming",[
        ct.c_int16,ct.POINTER(ct.c_uint32),ct.c_int32,ct.c_uint32,ct.c_uint32,
        ct.c_int16,ct.c_uint32,ct.c_int32,ct.c_uint32])
    cbtype=ct.WINFUNCTYPE(None,ct.c_int16,ct.c_int32,ct.c_uint32,
                           ct.c_int16,ct.c_uint32,ct.c_int16,ct.c_int16,ct.c_void_p)
    latest=get_api(dll,"ps3000aGetStreamingLatestValues",[ct.c_int16,cbtype,ct.c_void_p])
    unit=ct.c_int16()
    opened=False
    ser=None
    samples=0
    callbacks=0
    overflows=0
    armed=False
    fire_one_sent=False
    firmware_lines=[]
    rxpartial=""
    pre_a=array.array("h")
    pre_b=array.array("h")
    driver_a=(ct.c_int16*SAMPLES_PER_CALLBACK)()
    driver_b=(ct.c_int16*SAMPLES_PER_CALLBACK)()
    max_count=ct.c_int16()
    actual_interval=ct.c_uint32(INTERVAL_REQUEST_US)
    scope_baseline=None

    def usb_read():
        nonlocal rxpartial
        if ser is None or not ser.is_open:return
        available=ser.in_waiting
        if available:
            rxpartial+=ser.read(available).decode("ascii",errors="replace")
        while "\n" in rxpartial:
            line,rxpartial=rxpartial.split("\n",1)
            line=line.strip()
            if line:
                firmware_lines.append(line)
                print("KNX077_COM8",line,flush=True)
    def usb_send(message):
        print("KNX077_COMMAND",message,flush=True)
        ser.write((message+"\n").encode("ascii"))
        ser.flush()

    try:
        ser=serial.Serial(port=args.port,baudrate=BAUD,timeout=0,write_timeout=1,
                          dsrdtr=False,rtscts=False)
        ser.dtr=True;ser.rts=False
        time.sleep(0.3)
        usb_read()
        usb_send("STATUS")
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and not any(
                x.startswith("KNX076 STATUS") for x in firmware_lines):
            usb_read()
            time.sleep(.01)
        match=[x for x in firmware_lines if x.startswith("KNX076 STATUS")]
        if len(match)!=1 or not all(item in match[-1] for item in (
                "gpio0_measured=LOW","pio_ready=1","armed=0","shots=0")):
            raise RuntimeError("KNX076 firmware identity/one-shot status guard FAILED")
        print("KNX077_STRICT_FIRMWARE_PREFLIGHT_PASS",flush=True)
        check("OpenUnit",op(ct.byref(unit),None));opened=True
        check("EnableChannelA_KNXPLUS_50V_physical",channel(unit,0,1,1,8,0.0))
        check("EnableChannelB_TX_5V_physical",channel(unit,1,1,1,5,0.0))
        check("MaximumValue",adc_max(unit,ct.byref(max_count)))
        if max_count.value<30000:raise RuntimeError("Unexpected PicoScope ADC resolution")
        check("BufferA",setbuf(unit,0,driver_a,SAMPLES_PER_CALLBACK,0,0))
        check("BufferB",setbuf(unit,1,driver_b,SAMPLES_PER_CALLBACK,0,0))
        with file_a.open("wb") as fa,file_b.open("wb") as fb:
            def callback(handle,n,start,overflow,*unused):
                nonlocal samples,callbacks,overflows
                count=min(n,SAMPLES_TARGET-samples)
                if count<=0:return
                bytes_a=ct.string_at(ct.addressof(driver_a)+start*2,count*2)
                bytes_b=ct.string_at(ct.addressof(driver_b)+start*2,count*2)
                fa.write(bytes_a);fb.write(bytes_b)
                if len(pre_a)<90000:
                    tmp=array.array("h");tmp.frombytes(bytes_a)
                    pre_a.extend(tmp[:max(0,90000-len(pre_a))])
                    tmp=array.array("h");tmp.frombytes(bytes_b)
                    pre_b.extend(tmp[:max(0,90000-len(pre_b))])
                samples+=count
                callbacks+=1
                if overflow:overflows+=1
            handler=cbtype(callback)
            check("RunStreaming",streaming(unit,ct.byref(actual_interval),3,0,
                                          SAMPLES_TARGET,1,1,0,SAMPLES_PER_CALLBACK))
            print("KNX077_SCOPE_AB_RECORDING_STARTED",
                  "DT_US",actual_interval.value,flush=True)
            started=time.monotonic()
            stage=0
            preflight_samples=160000
            while samples<SAMPLES_TARGET and time.monotonic()-started<9:
                status=latest(unit,handler,None)
                if status not in PICO_TRANSIENT_STATUSES:
                    check("Polling",status)
                usb_read()
                if stage==0 and samples>=preflight_samples:
                    if overflows:raise RuntimeError("PicoScope overflow before pulse")
                    scope_baseline=verify_idle_samples(pre_a,pre_b,max_count.value)
                    # Return to non-actuating status check before armed.
                    usb_send("STATUS")
                    stage=1
                if stage==1 and samples>=preflight_samples+25000:
                    replies=[x for x in firmware_lines if x.startswith("KNX076 STATUS")]
                    if len(replies)<2 or not all(q in replies[-1] for q in (
                            "gpio0_measured=LOW","pio_ready=1","armed=0","shots=0")):
                        raise RuntimeError("Secondary no-stimulus STATUS guard failed")
                    usb_send("ARM ONE")
                    stage=2
                if stage==2 and samples>=preflight_samples+90000:
                    if not any(x.startswith("KNX076 ARMED ONE_SHOT_4S_TTL") for x in firmware_lines):
                        raise RuntimeError("Firmware failed to ACK ARM; refusing FIRE")
                    # Set local one-shot latch BEFORE sending: even on serial error,
                    # never send this command a second time.
                    fire_one_sent=True
                    stage=3
                    usb_send("FIRE ONE")
                time.sleep(.002)
            usb_read()
            print("KNX077_SCOPE_END",
                  "samples",samples,"callbacks",callbacks,
                  "overflows",overflows,"fire_command_sent",fire_one_sent,flush=True)
        if ser.is_open:
            usb_send("DISARM")
            time.sleep(.13)
            usb_read()
            usb_send("STATUS")
            time.sleep(.13)
            usb_read()
    finally:
        if opened:
            print("PICOSCOPE_STOP",stop(unit),flush=True)
            print("PICOSCOPE_CLOSE",close(unit),flush=True)
        if ser is not None and ser.is_open:
            # No FIRE command here, disarm only.
            try:
                ser.write(b"DISARM\n")
                ser.flush()
            except (OSError,serial.SerialException):
                pass
            ser.close()
    if samples<50000:raise RuntimeError("Capture failed before useful samples")
    result=analyze(file_a,file_b,max_count.value,actual_interval.value,
                   firmware_lines,overflows,fire_one_sent,
                   scope_baseline if scope_baseline else (None,None))
    result.update({"source":"KNX077 LLO Home",
                   "timestamp_local":datetime.now().isoformat(),
                   "path_a":str(file_a),"path_b":str(file_b),
                   "knx_bus_test_requested":True})
    file_json.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KNX077_RESULT_SAVED",str(file_json),flush=True)
    if result["events"]:
        first=result["events"][0]["sample_start"]
        a=array.array("h");a.frombytes(file_a.read_bytes())
        b=array.array("h");b.frombytes(file_b.read_bytes())
        lo=max(0,first-250)
        hi=min(len(a),first+450)
        with file_csv.open("w",encoding="ascii") as fd:
            fd.write("time_from_TX_rise_us,A_KNXPLUS_V,B_KNX_TX_V\n")
            for i in range(lo,hi):
                fd.write("%s,%.4f,%.4f\n"%(
                    (i-first)*actual_interval.value,
                    a[i]*(PICO_RAW_RANGE_A_V*PHYSICAL_PROBE_ATTENUATION/max_count.value),
                    b[i]*(PICO_RAW_RANGE_B_V*PHYSICAL_PROBE_ATTENUATION/max_count.value)))
        print("KNX077_EVENT_CSV",str(file_csv),flush=True)
    # Return nonzero when no complete, passing scope result, without retrying.
    return 0 if result["one_shot_scope_success"] else 4


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute",action="store_true")
    ap.add_argument("--confirm-lab-setup",action="store_true")
    ap.add_argument("--port",default="COM8")
    ap.add_argument("--sdk",type=Path,required=True)
    ap.add_argument("--outdir",type=Path,required=True)
    args=ap.parse_args()
    return run_test(args)


if __name__=="__main__":
    raise SystemExit(main())
