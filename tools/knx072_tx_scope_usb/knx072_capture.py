#!/usr/bin/env python3
"""USB-only RP2040 GPIO0 pulse/oscilloscope B proof. NEVER with KNX bus connected."""
from __future__ import annotations
import argparse
import array
import ctypes as c
import json
import os
from pathlib import Path
import statistics
import time
from datetime import datetime
import serial


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port",required=True)
    ap.add_argument("--sdk",type=Path,required=True)
    ap.add_argument("--outdir",type=Path,required=True)
    ap.add_argument("--confirm-knx-both-disconnected",action="store_true")
    a=ap.parse_args()
    if not a.confirm_knx_both_disconnected:
        ap.error("Both KNX+ and KNX- MUST be physically disconnected")
    a.outdir.mkdir(parents=True,exist_ok=True)
    stem="KNX072_SCOPE_TX_"+datetime.now().strftime("%Y%m%d_%H%M%S")
    raw=a.outdir/(stem+".s16le")
    summary=a.outdir/(stem+".json")
    csv=a.outdir/(stem+"_waveform.csv")
    os.add_dll_directory(str(a.sdk))
    d=c.WinDLL(str(a.sdk/"ps3000a.dll"))
    def fn(name,types):
        f=getattr(d,name);f.argtypes=types;f.restype=c.c_uint32
        return f
    def ok(name,ret):
        if ret:raise RuntimeError(name+" pico_status="+hex(ret))
    open_=fn("ps3000aOpenUnit",[c.POINTER(c.c_int16),c.c_char_p])
    close=fn("ps3000aCloseUnit",[c.c_int16])
    stop=fn("ps3000aStop",[c.c_int16])
    channel=fn("ps3000aSetChannel",[c.c_int16,c.c_int32,c.c_int16,c.c_int32,c.c_int32,c.c_float])
    maxv=fn("ps3000aMaximumValue",[c.c_int16,c.POINTER(c.c_int16)])
    buf=fn("ps3000aSetDataBuffer",[c.c_int16,c.c_int32,c.POINTER(c.c_int16),c.c_int32,c.c_uint32,c.c_int32])
    run=fn("ps3000aRunStreaming",[c.c_int16,c.POINTER(c.c_uint32),c.c_int32,c.c_uint32,c.c_uint32,c.c_int16,c.c_uint32,c.c_int32,c.c_uint32])
    CB=c.WINFUNCTYPE(None,c.c_int16,c.c_int32,c.c_uint32,c.c_int16,c.c_uint32,c.c_int16,c.c_int16,c.c_void_p)
    latest=fn("ps3000aGetStreamingLatestValues",[c.c_int16,CB,c.c_void_p])
    port=None; h=c.c_int16(); opened=False
    lines=[];rx=""
    def read_serial():
        nonlocal rx
        if port is not None and port.is_open:
            n=port.in_waiting
            if n:rx+=port.read(n).decode("ascii",errors="replace")
            while "\n" in rx:
                line,rx=rx.split("\n",1)
                line=line.strip()
                if line:
                    lines.append(line)
                    print("SERIAL",line,flush=True)
    def send(txt):
        print("USB_COMMAND",txt,flush=True)
        port.write((txt+"\n").encode("ascii"))
        port.flush()
    done=False;armed=False;sent=False
    count=0;callbacks=0;overflows=0
    bufsize=30000
    nmax=2000000
    buff=(c.c_int16*bufsize)()
    interval=c.c_uint32(1)
    max_adc=c.c_int16()
    try:
        port=serial.Serial(a.port,115200,timeout=0,write_timeout=1,
                           rtscts=False,dsrdtr=False)
        port.dtr=True;port.rts=False
        time.sleep(.3);read_serial()
        send("STATUS")
        deadline=time.monotonic()+2.5
        ready=False
        while time.monotonic()<deadline and not ready:
            read_serial()
            ready=any("KNX072 STATUS mode=USB_ONLY" in l and "tx_low=1" in l for l in lines)
            time.sleep(.01)
        if not ready:raise RuntimeError("KNX072 GPIO0 TX_LOW preflight not confirmed")
        print("USB_PREFLIGHT_GPIO0_LOW_VERIFIED",flush=True)
        ok("SCOPE_OPEN",open_(c.byref(h),None));opened=True
        ok("A_DISABLE",channel(h,0,0,1,5,0.0))
        # Scope range: raw +/-500mV; actual voltage = raw * physical probe 10x.
        ok("B_DC_500mV",channel(h,1,1,1,5,0.0))
        ok("MAX_ADC",maxv(h,c.byref(max_adc)))
        ok("BUFFER_B",buf(h,1,buff,bufsize,0,0))
        if max_adc.value<30000:raise RuntimeError("Unexpected scope ADC max")
        with raw.open("wb") as f:
            def callback(_h,n,start,overflow,*rest):
                nonlocal count,callbacks,overflows
                if n<=0:return
                v=min(n,nmax-count)
                if v<=0:return
                f.write(c.string_at(c.addressof(buff)+2*start,2*v))
                count+=v;callbacks+=1
                if overflow&2:overflows+=1
            cb=CB(callback)
            ok("SCOPE_STREAM_START",run(h,c.byref(interval),3,0,nmax,1,1,0,bufsize))
            t0=time.monotonic()
            print("SCOPE_STREAM_STARTED",interval.value,"us/sample; target",nmax,flush=True)
            while count<nmax and time.monotonic()-t0<6:
                status=latest(h,cb,None)
                if status not in (0, 0x25, 0x27):
                    ok("SCOPE_POLL",status)
                read_serial()
                elapsed=time.monotonic()-t0
                if elapsed>.23 and count>=50000 and not armed:
                    send("ARM USB_ONLY");armed=True
                if elapsed>.55 and count>=80000 and armed and not sent:
                    if not any("KNX072 ARMED USB_ONLY" in l for l in lines):
                        raise RuntimeError("Firmware did not ACK ARM; no pulse command")
                    send("PULSE8");sent=True
                time.sleep(.002)
            done=any("KNX072 TX_BENCH_COMPLETE" in l for l in lines)
        print("SCOPE_FINISHED",count,"CALLBACKS",callbacks,"OVERFLOWS",overflows,flush=True)
        send("DISARM");time.sleep(.1);read_serial()
        send("STATUS");time.sleep(.15);read_serial()
    finally:
        if opened:
            print("SCOPE_STOP",stop(h),"SCOPE_CLOSE",close(h),flush=True)
        if port is not None and port.is_open:
            try:port.write(b"DISARM\n")
            except Exception:pass
            port.close()
    data=array.array("h");data.frombytes(raw.read_bytes())
    scale=5/max_adc.value
    base=statistics.median(data[:min(len(data),20000)])*scale if data else None
    pulse=[];start=None
    threshold=1.5/scale
    for i,v in enumerate(data):
        if v>threshold and start is None:start=i
        elif v<=threshold and start is not None:
            if i-start>=5:pulse.append((start,i))
            start=None
    if start is not None:pulse.append((start,len(data)))
    widths=[(e-s)*interval.value for s,e in pulse]
    gaps=[(pulse[i+1][0]-pulse[i][1])*interval.value for i in range(len(pulse)-1)]
    low=min(data)*scale if data else None
    high=max(data)*scale if data else None
    pass_=len(pulse)==8 and all(28<=x<=48 for x in widths) and all(60<=x<=100 for x in gaps) and (base is not None and base<.5) and high>2.5 and overflows==0 and done
    if pulse:
        lo=max(0,pulse[0][0]-80);hi=min(len(data),pulse[-1][1]+100)
        with csv.open("w",encoding="ascii") as out:
            out.write("time_from_first_rise_us,knx_tx_gpio0_V\n")
            for i in range(lo,hi):
                out.write("%.1f,%.4f\n"%((i-pulse[0][0])*interval.value,data[i]*scale))
    result={"sample_count":len(data),"interval_us":interval.value,"probe_assumed":10,
            "scope_raw_range_V":.5,"channel":"B JMP3 2/3","baseline_V":base,
            "min_V":low,"max_V":high,"pulses":len(pulse),"widths_us":widths,
            "low_gaps_us":gaps,"overflows":overflows,"firmware_done":done,
            "pass":pass_,"serial_log":lines,"file_raw":str(raw),
            "file_csv":str(csv) if pulse else None}
    summary.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("SCOPE_B_BASELINE_V",round(base,3),"MAX_V",round(high,3),flush=True)
    print("SCOPE_B_PULSES",len(pulse),"HIGH_US",widths,"LOW_GAP_US",gaps,flush=True)
    print("SCOPE_PULSE_TEST_PASS",pass_,"RESULT",str(summary),flush=True)
    return 0 if pass_ else 3

if __name__=="__main__":
    raise SystemExit(main())
