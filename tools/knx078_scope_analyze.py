#!/usr/bin/env python3
"""Offline analyze STKNX TP1 board TX waveform from paired PicoScope ADC files.

No hardware, serial or network actions; exact match to a single 9-byte
standard GroupValueWrite from 1.0.250 to ETS-unallocated 29/7/241, value0.
"""
from __future__ import annotations
import array
import json
from pathlib import Path
from tools.knx078_tp1_frame import active_bits, validate, BIT_TIME_US


def analyze(a_path:Path,b_path:Path,max_adc:int,dt:int,
            firmware_log:list[str],driver_overflows:int,
            commanded_fire:bool,live_idle:tuple[float,float]) -> dict:
    aa=array.array("h");aa.frombytes(a_path.read_bytes())
    bb=array.array("h");bb.frombytes(b_path.read_bytes())
    if len(aa)!=len(bb):
        raise ValueError("Scope channels are not aligned!")
    factor_a=50/max_adc
    factor_b=5/max_adc
    threshold=1.35/factor_b
    pulses=[]
    start=None
    for i,v in enumerate(bb):
        if v>threshold and start is None:start=i
        elif v<=threshold and start is not None:
            if i-start>=8:
                pulses.append((start,i))
            start=None
    if start is not None:pulses.append((start,len(bb)))
    expected=[i*BIT_TIME_US for i,b in enumerate(active_bits()) if b]
    obs=[(pulses[i][0]-pulses[0][0])*dt for i in range(len(pulses))] if pulses else []
    timings=[obs[i]-expected[i] for i in range(min(len(obs),len(expected)))]
    widths=[(e-s)*dt for s,e in pulses]
    peaks=[max(bb[s:e])*factor_b for s,e in pulses]
    dips=[]
    for s,e in pulses:
        # Real physical bus depression, not inferred from GPIO0.
        a_min=min(aa[s:e])*factor_a
        dips.append(live_idle[0]-a_min)
    frame=validate()
    result={
        "sample_count_each":len(aa),"dt_us":dt,"adc_max":max_adc,
        "A":"KNX+ x10 on PicoScope input range +/-5V",
        "B":"KNX_TX x10 on PicoScope input range +/-0.5V",
        "tx_command_sent":commanded_fire,
        "serial_log":firmware_log,
        "pico_overflow":driver_overflows,
        "A_bus_idle_baseline_V":live_idle[0],
        "B_gpio0_idle_baseline_V":live_idle[1],
        "expected_frame":frame,
        "expected_pulses":len(expected),
        "detected_tx_pulses":len(pulses),
        "first_tx_sample":pulses[0][0] if pulses else None,
        "pulse_width_us_range":[min(widths),max(widths)] if widths else [],
        "tx_peak_V_range":[round(min(peaks),3),round(max(peaks),3)] if peaks else [],
        "A_bus_droop_V_range":[round(min(dips),3),round(max(dips),3)] if dips else [],
        "max_bit_edge_error_us":round(max(abs(t) for t in timings),3) if timings else None,
        "bit_edge_errors_us":timings,
        "timings_match_104us_bits":len(timings)==len(expected)
            and all(abs(x)<=3 for x in timings),
        "rx_collision_or_abort":any("collision=1" in s or "PREFLIGHT_FAIL" in s
                                    or "ABORTED" in s for s in firmware_log),
        "tx_firmware_reported_completed":any(s.startswith("KNX078 FRAME_TX_COMPLETED_ONCE collision=0") for s in firmware_log),
    }
    result["scope_physical_tx_pass"]=bool(
        commanded_fire and len(pulses)==len(expected) and
        result["timings_match_104us_bits"] and
        all(30<=w<=39 for w in widths) and
        all(p>=2.2 for p in peaks) and
        sum(d>4 for d in dips)>=len(pulses)-4 and
        driver_overflows==0 and not result["rx_collision_or_abort"] and
        result["tx_firmware_reported_completed"]
    )
    result["one_shot_scope_success"]=result["scope_physical_tx_pass"]
    print("KNX078_ANALYZED",json.dumps({
        "TX_pulses":len(pulses),"expected_pulses":len(expected),
        "widths_us_minmax":result["pulse_width_us_range"],
        "TX_peak_V":result["tx_peak_V_range"],
        "A_drop_V":result["A_bus_droop_V_range"],
        "edge_error_us_max":result["max_bit_edge_error_us"],
        "collision":result["rx_collision_or_abort"],
        "scope_physical_tx_pass":result["scope_physical_tx_pass"]},
        ensure_ascii=True),flush=True)
    return result
