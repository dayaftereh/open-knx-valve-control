#!/usr/bin/env python3
"""KNX085 host parser/preflight tests. No serial access is permitted."""
from __future__ import annotations
import sys
from knx085_motor_diag import knx085_bench_host as h

BASE=[
 "KNX085 STATUS tx_low=1 motors_low=1 uart_ready=1 snapshots=12 timeout=0 rejected=0 rx_edges=12345 motor_gate=1 motor_state=IDLE NO_AUTOMATIC_MOTOR_OR_KNX_TX",
 "KNX085 INA addr=0x40 config=0x399f config_ok=1 good_idle_samples=6",
 "KNX085 INA read_ok=1 bus_mv=3296 current_ma_assuming_R29_200mohm=0 overflow=0 idle_ok=1 SHUNT_AND_SUPPLY_AS_BUILT_NOT_YET_MEASURED",
]+[
 f"KNX085 CH T{i} valid=1 temp_c=14.25 flags=3 fault=0 fault_name=None age_s=2"
 for i in range(4)
]
def refuses(f):
    try: f()
    except RuntimeError:return
    raise AssertionError("Unsafe input was accepted")

assert h.check_status(BASE,gate_required=True)["knx_rx_edges"]==12345
assert h.check_ina(BASE)["bus_mv"]==3296
assert h.TRACE.fullmatch("KNX085 TRACE t_ms=30 shunt_raw=300 shunt_uv=3000 bus_mv=3296 valid=1")
refuses(lambda:h.check_status([x.replace("tx_low=1","tx_low=0") for x in BASE],gate_required=True))
refuses(lambda:h.check_status([x.replace("motor_gate=1","motor_gate=0") for x in BASE],gate_required=True))
refuses(lambda:h.check_status([x.replace("T1 valid=1","T1 valid=0") for x in BASE],gate_required=True))
refuses(lambda:h.check_ina([x.replace("good_idle_samples=6","good_idle_samples=0") for x in BASE]))
refuses(lambda:h.check_ina([x.replace("bus_mv=3296","bus_mv=2800") for x in BASE]))
refuses(lambda:h.check_ina([x.replace("config_ok=1","config_ok=0") for x in BASE]))
refuses(lambda:h.check_ina([x.replace("idle_ok=1","idle_ok=0") for x in BASE]))
# Confirm no even read-only COM open can occur on unconfirmed pulse request
old_serial=h.serial.Serial
try:
    h.serial.Serial=lambda *a,**kw: (_ for _ in ()).throw(AssertionError("COM OPENED"))
    sys.argv=["knx085_bench_host","pulse"]
    refuses(h.main)
finally:
    h.serial.Serial=old_serial
print("KNX085_HOST offline parser + fail-closed preflight 11/11 PASS")
