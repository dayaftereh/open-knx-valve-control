#!/usr/bin/env python3
"""KNX089 motor-lock and INA register-dump offline regressions."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"knx089_ina_regdiag"))
import knx089_host as host

BASE=Path(__file__).resolve().parent/"knx089_ina_regdiag"
def main():
    ini=(BASE/"platformio.ini").read_text("utf8")
    cpp=(BASE/"src"/"main.cpp").read_text("utf8")
    assert "-DKNX085_HARDWARE_GATE_APPROVED=0" in ini
    assert "-DKNX085_HARDWARE_GATE_APPROVED=1" not in ini
    assert "upload_command = cmd /c exit 91" in ini
    assert cpp.count("#error \"KNX089")>=2
    assert "gpio_put(kKnxTx,0)" in cpp
    assert "gpio_put(kKnxTx,1)" not in cpp
    assert "KNX089 REGDUMP_END" in cpp and "INA_REGS" in cpp
    assert "INA_ADC_RESET" in cpp and "Wire.endTransmission(true)" in cpp
    assert "PULSE M" in cpp # inherited but can never physically drive
    assert "KNX085_HARDWARE_GATE_APPROVED == 1" in cpp
    print("PASS KNX089 locked output gates and diagnostic command paths")
    line="KNX089 REG addr=0x40 reg=0x1 restart_ok=1 restart_hex=0x242C stop_ok=1 stop_hex=0x242C"
    m=host.REG.fullmatch(line)
    assert m and m.groups()==("1","1","242C","1","242C")
    lines=[
      "KNX085 STATUS tx_low=1 motors_low=1 uart_ready=1 snapshots=100 timeout=0 rejected=0 rx_edges=900 motor_gate=0 motor_state=IDLE",
      "KNX085 INA read_ok=1 bus_mv=3148 current_ma_assuming_R29_200mohm=463 overflow=0 idle_ok=0"
    ]
    data=[0x399F,0x242C,((3148//4)<<3)|2,0x0000,0x0000,0x0000]
    for i,v in enumerate(data):
      lines.append(f"KNX089 REG addr=0x40 reg=0x{i:X} restart_ok=1 restart_hex=0x{v:X} stop_ok=1 stop_hex=0x{v:X}")
    result=host.validate(lines)
    assert result["motor_gate"]==0
    assert result["shunt_mv"]==92.6 and result["ma_at_200mohm"]==463.0
    assert result["bus_mv"]==3148
    assert result["reg_calibration"]=="0x0000"
    print("PASS raw register fingerprint matches 92.6 mV")
    bad=[x.replace("motor_gate=0","motor_gate=1") for x in lines]
    try:host.validate(bad)
    except host.DiagnosticError:print("PASS refuses unlocked motor firmware")
    else:raise AssertionError("missing gate0 refuse")
    corrupt=[x.replace("stop_hex=0x242C","stop_hex=0x1111") for x in lines]
    try:host.validate(corrupt)
    except host.DiagnosticError:print("PASS mismatched STOP vs repeated-start I2C refused")
    else:raise AssertionError("missing comparison guard")
    print("KNX089 OFFLINE TEST 4/4 PASS")
if __name__=="__main__":main()
