#!/usr/bin/env python3
"""Offline TP1 KNX081 transmit golden vector: one fixed harmless 1-bit group write.

No network or device I/O. For RP2040 STKNX GPIO0 where HIGH for 35us transmits
a logical 0, LOW for the entire 104us transmits a logical 1. 13 bit cells per
character: 1 start0, 8 LSB data, even parity, 1 stop1, 2 idle1.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.knx070_tp1_decode import parse_l_data, read_char

SOURCE = "1.3.250"
DESTINATION = "29/7/241"
VALUE = 0
BYTE_TIME_US = 13 * 104
BIT_TIME_US = 104
PULSE_HIGH_US = 35


def build_frame() -> bytes:
    src=(1 << 12) | (3 << 8) | 250
    dest=(29 << 11) | (7 << 8) | 241
    # BC=standard data, normal priority. D1=group, hop=5, length=1 (2 APDU octets).
    # APDU 00 80 = TPCI 00, APCI GroupValueWrite, 1-bit data 0.
    raw=[0xBC, src >> 8, src & 255, dest >> 8, dest & 255,
         0xD1, 0x00, 0x80]
    check=0xFF
    for v in raw:
        check ^= v
    raw.append(check)
    return bytes(raw)


def byte_bits(byte: int) -> list[int]:
    data=[(byte >> i) & 1 for i in range(8)]
    even_parity=sum(data)&1
    return [0]+data+[even_parity,1,1,1]


def active_bits() -> list[int]:
    return [1-logical for b in build_frame() for logical in byte_bits(b)]


def packed_words() -> list[int]:
    bits=active_bits()
    bits.extend([0]*((-len(bits))%32))   # padded idle time never makes HIGH
    return [sum(bit << j for j,bit in enumerate(bits[i:i+32]))
            for i in range(0,len(bits),32)]


def validate() -> dict:
    data=build_frame()
    bits=active_bits()
    words=packed_words()
    assert len(data)==9 and len(bits)==117 and len(words)==4
    assert all(0<=w<=0xFFFFFFFF for w in words)
    assert data==bytes.fromhex("BC 13 FA EF F1 D1 00 80 E5"),data.hex(" ")
    assert 0xFF==__import__("functools").reduce(lambda x,y:x^y,data,0)
    decoded=parse_l_data(list(data))
    assert decoded["source"]==SOURCE and decoded["destination"]==DESTINATION,decoded
    assert decoded["service"]=="GroupValueWrite" and decoded["short_value"]==VALUE,decoded
    rises=[i*BIT_TIME_US for i,bit in enumerate(bits) if bit]
    chars=[]
    for n in range(len(data)):
        dec=read_char(rises,n*BYTE_TIME_US,BIT_TIME_US)
        assert dec["valid"] and dec["byte"]==data[n],(n,dec)
        chars.append(dec)
    return {
        "frame_hex":data.hex(" ").upper(),
        "source":SOURCE, "destination":DESTINATION,"value":VALUE,
        "characters":len(data),"bits":len(bits),"pulses":sum(bits),
        "duration_us":len(bits)*BIT_TIME_US,
        "gpio_high_us_per_logical_zero":PULSE_HIGH_US,
        "gpio_low_us_per_logical_zero":BIT_TIME_US-PULSE_HIGH_US,
        "packed_words":[f"0x{x:08X}" for x in words],
        "knx070_offline_decode_ok":True,
        "characters_start_stop_even_parity_ok":len(chars),
        "checksum_xor_FF":True,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    report=validate()
    print("KNX081_FRAME_GOLDEN_PASS",json.dumps(report))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
