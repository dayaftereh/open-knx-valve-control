#!/usr/bin/env python3
"""KNX088 static PCB netlist audit for the INA219+R29+TB6612 M_VCC chain.

No serial, no hardware I/O. EasyEDA source board V1.2 is authoritative
for DESIGN NETS only; it cannot prove as-built shorts or component damage.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PCB=ROOT/"schematic"/"pcb_knx-valve-control_v1.2.json"
OUT=Path(r"C:\_myspace\workspace\Builds\OpenKNXValveControl\KNX088_INA_IDLE")
def demand(flag,msg):
    if not flag:raise ValueError(msg)
def build_pads():
    data=json.loads(PCB.read_text(encoding="utf8"))
    by_ref={}
    for s in data["shape"]:
        if not s.startswith("LIB~"):continue
        children=s.split("#@$")
        refparts=[x.split("~") for x in children if x.startswith("TEXT~P~")]
        if not refparts:continue
        ref=refparts[0][10]
        pads={}
        for c in children:
            if not c.startswith("PAD~"):continue
            items=c.split("~")
            pads[items[8]]=items[7]
        if pads:by_ref[ref]=pads
    return by_ref
def audit():
    refs=build_pads()
    demand(len(refs)>=180,"Incomplete EasyEDA PCB footprint parse")
    def net(ref,pin,expected):
        got=refs[ref][str(pin)]
        demand(got==expected,f"{ref}.{pin} net {got} != {expected}")
    net("R29",1,"3.3V")
    net("R29",2,"M_VCC")
    net("R33",1,"3.3V")
    net("R33",2,"U23_8")
    net("R34",1,"M_VCC")
    net("R34",2,"U23_7")
    net("U23",8,"U23_8") # INA219 SOIC IN+ per TI
    net("U23",7,"U23_7") # INA219 SOIC IN- per TI / Vbus sense
    net("U23",5,"3.3V")
    net("U23",6,"GND")
    net("C31",1,"M_VCC")
    net("C31",2,"3.3V")
    caps=[f"C{i}" for i in range(36,44)]
    for c in caps:
        net(c,1,"GND");net(c,2,"M_VCC")
    enables={}
    vm=[]
    for drv in ("U34","U35","U36","U37"):
        for pin in (13,14,24):
            net(drv,pin,"M_VCC")
            vm.append(f"{drv}.{pin}")
        net(drv,19,"3.3V") # STBY always high
        net(drv,20,"3.3V") # VCC
        net(drv,18,"GND")
        for pin in (16,22):net(drv,pin,"IN_2")
        for pin in (17,21):net(drv,pin,"IN_1")
        for pin in (15,23):
            ena=refs[drv][str(pin)]
            demand(ena.endswith("_EN"),f"{drv}.{pin} unexpected PWM net {ena}")
            enables[ena]=f"{drv}.{pin}"
    demand(len(enables)==8 and
           set(enables)=={f"M{i}_EN" for i in range(1,9)},
           "Missing M1..M8 motor output")
    pinset=[13,14,15,16,17,18,27,28]
    for idx,pin in enumerate(pinset,start=1):net("U18",pin,f"M{idx}_EN")
    net("U18",29,"IN_1");net("U18",30,"IN_2")
    m_vcc=sorted(f"{ref}.{pin}" for ref,pins in refs.items()
                 for pin,connection in pins.items() if connection=="M_VCC")
    expected=sorted(["R29.2","R34.1","C31.1"]+
                    [f"{c}.2" for c in caps]+vm)
    demand(m_vcc==expected,
           "M_VCC load list changed: "+str(sorted(set(m_vcc)^set(expected))))
    return {
     "schema":"knx088-v1_2-ina219-motor-rail-net-audit/v1",
     "pcb_file":str(PCB),"components_parsed":len(refs),
     "verified_net_map":{
      "source":"3.3V",
      "r29":"R29.1 3.3V -> R29.2 M_VCC, 0.200 ohm/1W user-confirmed",
      "ina219_in_plus":"U23.8 <- U23_8 <- R33.2 <- R33.1 3.3V",
      "ina219_in_minus":"U23.7 <- U23_7 <- R34.2 <- R34.1 M_VCC",
      "ina219_vbus_reference":"SOIC pin7 IN- = M_VCC (TI datasheet)",
      "ac_filter":"C31 100nF directly across R29",
      "bulk_decupling":"C36..C43 4x100nF + 4x10uF M_VCC to GND",
      "motor_driver_vm_pads":vm,
      "driver_stby":"U34/U35/U36/U37 pin19 tied to 3.3V (not controllable)",
      "driver_logic_enables":enables,
      "rp2040_pwm_pins":"GPIO10..17 -> M1..M8, GPIO18/19 -> IN_1/IN_2, verified PCB padnet",
     },
     "m_vcc_all_pcb_footprint_pads":m_vcc,
     "passive_vs_active_load_note":
       "Only four dual motor drivers U34..U37 plus eight bypass capacitors and "
       "the INA219 sense input load M_VCC after the shunt. No display/ATtiny/"
       "RP2040 or KNX interface loads directly on M_VCC in source PCB.",
     "limits":"Static PCB netlist cannot detect actual assembly short, damage, or direct measured shunt voltage",
     "r29_ohm_user_confirmed":0.2,
     "reported_motor_off_ma":463,
     "reported_shunt_mv_inferred":92.6,
     "reported_in_minus_v_mv":3148,
     "implied_in_plus_v_mv":3240.6,
     "implied_m_vcc_load_power_w":round(3.148*.463,4),
     "implied_m_vcc_equivalent_resistance_ohm":round(3.148/.463,3),
     "ina219_shunt_offset_max_mv_at_pga_div8":0.2,
     "shunt_signal_offset_multiple":463,
    }

if __name__=="__main__":
    obj=audit()
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"KNX088_STATIC_NET_AUDIT.json"
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("KNX088 NET AUDIT PASS",
          json.dumps({"components":obj["components_parsed"],
              "m_vcc_pad_count":len(obj["m_vcc_all_pcb_footprint_pads"]),
              "m_vcc_unique_drivers":["U34","U35","U36","U37"],
              "r29_ohms":0.2,"ina_polarity":"CORRECT",
              "driver_stby":"3.3V HIGH",
              "inferred_vin_plus_mv":obj["implied_in_plus_v_mv"],
              "inferred_motor_rail_power_w":obj["implied_m_vcc_load_power_w"]}))
    print("NET_AUDIT_JSON",path)
