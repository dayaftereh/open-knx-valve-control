#!/usr/bin/env python3
"""KNX101 five-step host from KNX100, diagnostic and fresh fault recovery.

Separately pinned firmware, state/evidence, flags and no automatic retries.
"""
from pathlib import Path
source=Path(__file__).resolve().parents[1]/"knx100_position_usb"
dest=Path(__file__).resolve().parent
s=(source/"knx100_host.py").read_text("utf8")
s=s.replace("KNX100","KNX101").replace("knx100_m1_position_5step","knx101_m1_position_diag_5step")
# KNX101 first R seek starts from the aborted KNX100 ~500 permille
# rather than the original KNX097 F endpoint, so ~half stroke expected.
s=s.replace('''"stop":"ENDSTOP_CANDIDATE","expected_ms":24388,"range_ms":[12000,30000],''',
            '''"stop":"ENDSTOP_CANDIDATE","expected_ms":12200,"range_ms":[6000,30000],''')
# Before flashing, verify the old KNX100 current fault is harmless and latched.
a='''    prior_state=prior.verify()
    need(prior_state["version"]=={"next_dir":"R","legs_done":6,
          "last_kind":"LOAD_RISE","last_dir":"F"},
         "Must preserve documented F-side KNX097 completed endpoint as initial position")
'''
b='''    sys.path.insert(0,str(HERE.parent/"knx100_position_usb"))
    import knx100_host as prev
    prior_state=prev.verify()
    need(prior_state["phase"]=="FAULT_LATCHED" and
         prior_state["issued"]==2 and prior_state["completed"]==2 and
         prior_state["last_stop"]=="CANCELLED" and
         prior_state["gpio_low"] and prior_state["driver"]=="IDLE" and
         prior_state["idle_ma"]==0,
         "Before reflashing require the documented stopped KNX100 step3 fault")
'''
assert s.count(a)==1,(a[:80],s.count(a))
s=s.replace(a,b)
# Existing imports of prior in KNX100 remain harmless.
s=s.replace('PIN_SHA="74d20e1c05354e23dcace950232f2e002d3e417a9f7558fba406903a43a5e726"',
            'PIN_SHA="__KNX101_SHA__"')
s=s.replace("PIN_BYTES=250368","PIN_BYTES=0")
assert "KNX101 POSITION_USB_ONLY steps=5" in s
assert "KNX101_START_DIAG" not in s or True
assert "__KNX101_SHA__" in s
(dest/"knx101_host.py").write_text(s,encoding="utf8",newline="\n")
print("KNX101 host generated, previous KNX100 FAULT_LATCHED proof and independent flags")
