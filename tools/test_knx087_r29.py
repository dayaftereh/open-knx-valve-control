#!/usr/bin/env python3
"""KNX087 user-confirmed R29 0.200-ohm/1W math and read-only INA test."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx085_motor_diag"))
import knx086_live_connected as mod

def main():
    m="KNX085 INA read_ok=1 bus_mv=3148 current_ma_assuming_R29_200mohm=463 overflow=0 idle_ok=0 SHUNT_AND_SUPPLY_AS_BUILT_NOT_YET_MEASURED"
    z=mod.summarize_r29_ina([m])
    assert z["r29_ohms"]==0.2 and z["r29_rated_w"]==1
    assert z["shunt_drop_mv_inferred"]==92.6
    assert z["shared_supply_ma_reported"]==463
    assert z["r29_dissipated_w_inferred"]==0.04287
    assert z["measurement_valid"] and z["m_vcc_idle_over_25ma_gate"]
    assert z["measures"]=="shared M_VCC rail, not M1 exclusively"
    assert not z["physical_movement_observed"]
    print("PASS 463 mA with confirmed R29 200mohm: 92.6mV, 0.04287W")
    bad=mod.summarize_r29_ina([m.replace("overflow=0","overflow=1")])
    assert not bad["measurement_valid"] and "shunt_drop_mv_inferred" not in bad
    print("PASS refused invalid INA overflow")
    no=mod.summarize_r29_ina([])
    assert not no["measurement_valid"]
    print("PASS absent INA reading")
    idle=mod.summarize_r29_ina([m.replace("=463 ", "=0 ").replace("idle_ok=0", "idle_ok=1")])
    assert idle["measurement_valid"] and not idle["m_vcc_idle_over_25ma_gate"]
    print("PASS 0 mA readout under motor idle threshold")
    print("KNX087 R29 user-confirmed shared M_VCC math 4/4 PASS")
if __name__=="__main__":
    main()
