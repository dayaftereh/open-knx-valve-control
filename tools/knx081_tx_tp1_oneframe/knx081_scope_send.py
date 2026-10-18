#!/usr/bin/env python3
"""KNX081: one explicitly authorized 9-byte TP1 GroupValueWrite, PicoScope A+B and IP correlation.

NO autonomous pulses. Never repeat FIRE FRAME if any result is uncertain.
Requires KNX081 firmware, explicit --execute --confirm-lab-setup,
strict idle voltage/USB STATUS gates, scopes A=KNX+ B=KNX_TX physical 10x.
Result is a complete fixed TP1 group frame, not a production KNX stack.
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
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

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
    print(f"KNX081_BEFORE_FRAME_A_BASELINE={base_a:.3f}V B={base_b:.3f}V B_MAX={max_b:.3f}V",flush=True)
    if not 27.0<=base_a<=35.0:
        raise RuntimeError("KNX+ idle outside safe test envelope")
    if not -0.30<=base_b<=0.30 or max_b>0.6:
        raise RuntimeError("KNX_TX not reliably LOW in preflight")
    return base_a,base_b



from tools.knx081_scope_analyze import analyze

def run_test(args):
    if not args.execute or not args.confirm_lab_setup:
        raise RuntimeError("Explicit --execute AND --confirm-lab-setup required")
    args.outdir.mkdir(parents=True,exist_ok=True)
    stem="KNX081_SCOPE_AB_TP1_"+datetime.now().strftime("%Y%m%d_%H%M%S")
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
                print("KNX081_COM8",line,flush=True)
    def usb_send(message):
        print("KNX081_COMMAND",message,flush=True)
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
                x.startswith("KNX081 STATUS") for x in firmware_lines):
            usb_read()
            time.sleep(.01)
        match=[x for x in firmware_lines if x.startswith("KNX081 STATUS")]
        if len(match)!=1 or not all(item in match[-1] for item in (
                "tx_low=1","pio_ready=1","armed=0","attempted=0")):
            raise RuntimeError("KNX081 firmware identity/one-shot status guard FAILED")
        print("KNX081_STRICT_FIRMWARE_PREFLIGHT_PASS",flush=True)
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
            print("KNX081_SCOPE_AB_RECORDING_STARTED",
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
                    replies=[x for x in firmware_lines if x.startswith("KNX081 STATUS")]
                    if len(replies)<2 or not all(q in replies[-1] for q in (
                            "tx_low=1","pio_ready=1","armed=0","attempted=0")):
                        raise RuntimeError("Secondary no-stimulus STATUS guard failed")
                    usb_send("ARM FRAME")
                    stage=2
                if stage==2 and samples>=preflight_samples+90000:
                    if not any(x.startswith("KNX081 ARMED_4S_ONE_FIXED_FRAME") for x in firmware_lines):
                        raise RuntimeError("Firmware failed to ACK ARM; refusing FIRE")
                    # Set local one-shot latch BEFORE sending: even on serial error,
                    # never send this command a second time.
                    fire_one_sent=True
                    stage=3
                    usb_send("FIRE FRAME")
                time.sleep(.002)
            usb_read()
            print("KNX081_SCOPE_END",
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
    result.update({"source":"KNX081 LLO Home",
                   "timestamp_local":datetime.now().isoformat(),
                   "path_a":str(file_a),"path_b":str(file_b),
                   "knx_bus_test_requested":True})
    file_json.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KNX081_RESULT_SAVED",str(file_json),flush=True)
    if result["detected_tx_pulses"]:
        first=result["first_tx_sample"]
        a=array.array("h");a.frombytes(file_a.read_bytes())
        b=array.array("h");b.frombytes(file_b.read_bytes())
        lo=max(0,first-250)
        hi=min(len(a),first+14000)
        with file_csv.open("w",encoding="ascii") as fd:
            fd.write("time_from_TX_rise_us,A_KNXPLUS_V,B_KNX_TX_V\n")
            for i in range(lo,hi):
                fd.write("%s,%.4f,%.4f\n"%(
                    (i-first)*actual_interval.value,
                    a[i]*(PICO_RAW_RANGE_A_V*PHYSICAL_PROBE_ATTENUATION/max_count.value),
                    b[i]*(PICO_RAW_RANGE_B_V*PHYSICAL_PROBE_ATTENUATION/max_count.value)))
        print("KNX081_EVENT_CSV",str(file_csv),flush=True)
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
