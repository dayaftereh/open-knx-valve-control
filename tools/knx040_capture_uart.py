#!/usr/bin/env python3
"""KNX040: read-only USB CDC monitor for isolated RP2040 UART1 temperature diag.

No serial write, no RTS True, no target reset, no USB upload, no KNX/motors.
The USB firmware requests KNX014 CRC-protected frames from the ATtiny3216.
Without DS18B20 probes it should report T0..T8 as NoSensor; probe detection
can be rechecked later after an operator installs sensors with power OFF.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from pathlib import Path

VID=0x2E8A
PID=0x000A
SNAPSHOT=re.compile(r"^KNX040 SNAPSHOT seq=(\d+) up_ms=(\d+) valid=(\d+) no_sensor=(\d+) faults=(\d+) accepted=(\d+) timeout=(\d+) rejected=(\d+)$")
CHANNEL=re.compile(r"^KNX040 CH T([0-8]) flags=(\d+) fault=(\d+) age_s=(\d+) centiC=(-?\d+)$")

class ReadOnlyProbeError(RuntimeError):
    pass

def assert_port(candidates,port,expected_serial):
    devices=[p for p in candidates if getattr(p,"vid",None)==VID and
             getattr(p,"pid",None)==PID]
    if len(devices)!=1:
        raise ReadOnlyProbeError("expected exactly one 2E8A:000A RP2040 CDC")
    d=devices[0]
    if d.device.upper()!=port.upper() or not expected_serial or (
        d.serial_number or "").upper()!=expected_serial.upper():
        raise ReadOnlyProbeError("USB port/serial changed; no serial port opened")
    return d

def parse_capture(raw:bytes)->dict:
    lines=raw.decode("utf-8",errors="replace").splitlines()
    snapshots=[]
    channels=[]
    for line in lines:
        m=SNAPSHOT.fullmatch(line)
        if m:
            snapshots.append(dict(zip(("seq","up_ms","valid","no_sensor",
                "faults","accepted","timeout","rejected"),map(int,m.groups()))))
        m=CHANNEL.fullmatch(line)
        if m:
            idx,flags,fault,age,c=map(int,m.groups())
            channels.append({"channel":f"T{idx}","valid":bool(flags & 2),
                "flags":flags,"fault":fault,"age_s":age,
                "temperature_C":round(c/100,2) if flags & 2 else None})
    return {
        "USB_diagnostic_detected":any(line.startswith("KNX040 USB-CONTROL ") for line in lines),
        "snapshots":snapshots,"channel_records":channels,
        "snapshot_count":len(snapshots),
        "number_of_channel_lines":len(channels),
        "last_observed_channels":channels[-9:] if len(channels)>=9 else channels,
        "last_snapshot":snapshots[-1] if snapshots else None,
        "any_timeouts":any(line.startswith("KNX040 TIMEOUT ") for line in lines),
        "all_observed_nine_channels_NoSensor": bool(snapshots) and
              all(s["valid"]==0 and s["no_sensor"]==9 for s in snapshots),
    }

def serial_devices():
    from serial.tools import list_ports
    return list(list_ports.comports())

def capture(port,serial,seconds):
    import serial as uart
    assert_port(serial_devices(),port,serial)
    s=uart.Serial()
    s.port=port;s.baudrate=115200;s.timeout=0.25
    s.write_timeout=0.25;s.dtr=False;s.rts=False
    s.open()
    s.dtr=True
    data=bytearray()
    start=time.monotonic()
    try:
        while time.monotonic()-start<seconds and len(data)<100000:
            data+=s.read(256)
    finally:
        try:s.dtr=False
        except Exception: pass
        s.close()
    return bytes(data)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("plan","probe","capture"),nargs="?",default="plan")
    p.add_argument("--port")
    p.add_argument("--expect-serial")
    p.add_argument("--seconds",type=float,default=12.0)
    p.add_argument("--out",help="New plain-text capture path (never overwrite)")
    a=p.parse_args()
    try:
        if a.action=="plan":
            print(json.dumps({"mode":"READ_ONLY","RP_USB_VIDPID":"2E8A:000A",
                "baud":115200,"RTS":False,"CDC_DTR_for_host_ready":True,
                "CNX_KNX_motors_used":False,
                "expected_without_sensors":"T0..T8 fault=1/NoSensor flags=16 age_s=65535"},
                indent=2))
            return 0
        if a.action=="probe":
            matches=[{"port":p.device,"VIDPID":f"{p.vid:04X}:{p.pid:04X}",
                      "serial":p.serial_number}
                     for p in serial_devices() if p.vid==VID and p.pid==PID]
            print(json.dumps({"candidates":matches,"COM_opened":False},indent=2))
            return 0
        if not a.port or not a.expect_serial:
            raise ReadOnlyProbeError("capture requires exact COM and USB serial")
        if not 6<=a.seconds<=60:
            raise ReadOnlyProbeError("seconds must be 6..60")
        if a.out and Path(a.out).exists():
            raise ReadOnlyProbeError("capture target already exists; no overwrites")
        raw=capture(a.port,a.expect_serial,a.seconds)
        result=parse_capture(raw)
        result.update({"bytes_received":len(raw),"port":a.port,
                       "CDC_payload_bytes_written":0,"USB_RTS":False})
        if a.out:
            target=Path(a.out)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            result["saved_to"]=str(target)
        print(json.dumps(result,indent=2))
        return 0 if result["snapshot_count"]>=1 else 2
    except (ReadOnlyProbeError,OSError,ValueError) as exc:
        print("KNX040 BLOCKED:",str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
