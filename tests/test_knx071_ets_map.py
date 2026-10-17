#!/usr/bin/env python3
"""KNX071 offline parser, ETS guards and DPT9 regression tests. No bus I/O."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.knx071_ets_group_map import read_ets, addr_text
from tools.knx071_annotate_tp import dpt9, annotate
from tools.knx071_ip_test_once import verify_fresh_ets_map


class TestETSGAInventory(unittest.TestCase):
    def test_three_level_address_conversion(self):
        self.assertEqual(addr_text(0), "0/0/0")
        self.assertEqual(addr_text((4 << 11) | (2 << 8) | 1), "4/2/1")
        self.assertEqual(addr_text(0xEFF1), "29/7/241")
        self.assertEqual(addr_text(65535), "31/7/255")

    def test_group_and_comobject_link_resolution(self):
        xml = """<?xml version="1.0"?>
<KNX xmlns="http://knx.org/xml/project/23"><Project>
  <Installations><Installation><Topology>
    <Area Address="1"><Line Address="2"><Segment>
      <DeviceInstance Id="P-0001-0_DI-4" Address="10" Description="Synthetic test sensor">
        <ComObjectInstanceRefs>
          <ComObjectInstanceRef RefId="R-1" Links="GA-1 GA-3"/>
        </ComObjectInstanceRefs>
      </DeviceInstance>
    </Segment></Line></Area>
  </Topology></Installation></Installations>
  <GroupAddresses><GroupRanges>
    <GroupRange Name="Heizung"><GroupRange Name="Keller">
      <GroupAddress Id="P-0001-0_GA-1" Address="8705"
        Name="Synthetic Value A" DatapointType="DPST-9-7"/>
      <GroupAddress Id="P-0001-0_GA-3" Address="8706"
        Name="Synthetic Value B" DatapointType="DPST-9-7"/>
    </GroupRange></GroupRange>
  </GroupRanges></GroupAddresses>
</Project></KNX>"""
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"sample.knxproj"
            with ZipFile(p,"w") as fp:
                fp.writestr("P-0001/0.xml",xml)
            data=read_ets(p)
            self.assertEqual(data["total_groups"],2)
            self.assertEqual(data["total_devices"],1)
            self.assertEqual(data["assigned_com_links"],2)
            target=data["groups"][0]
            self.assertEqual(target["group_address"],"4/2/1")
            self.assertEqual(target["main"],"Heizung")
            self.assertEqual(target["middle"],"Keller")
            self.assertEqual(target["dpt"],"DPT 9.7")
            self.assertEqual(target["device_count"],1)
            self.assertIn("1.2.10",target["linked_devices"])

    def test_guard_refuses_declared_ga_and_stale_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"original.knxproj"
            source.write_bytes(b"fixed ets zip placeholder")
            sha=hashlib.sha256(source.read_bytes()).hexdigest()
            mapping={"source":str(source),"source_sha256":sha,
                "total_groups":1,"groups":[{"group_address":"4/2/1"}]}
            checksum,count=verify_fresh_ets_map(mapping,"29/7/241")
            self.assertEqual(checksum,sha)
            self.assertEqual(count,1)
            with self.assertRaisesRegex(RuntimeError,"TEST_GA_IN_ETS_PROJECT"):
                verify_fresh_ets_map(mapping,"4/2/1")
            mapping["source_sha256"]="bad"
            with self.assertRaisesRegex(RuntimeError,"ETS_SOURCE_CHANGED"):
                verify_fresh_ets_map(mapping,"29/7/241")


class TestDPTAnnotation(unittest.TestCase):
    def test_knx_dpt9_temperature_and_humidity(self):
        self.assertAlmostEqual(dpt9("1925"),23.44)
        self.assertAlmostEqual(dpt9("1A4F"),47.28)
        self.assertAlmostEqual(dpt9("05C8"),14.8)
        with self.assertRaises(ValueError):
            dpt9("1")

    def test_annotation_with_explicit_unassigned_test_telegram(self):
        meta={"groups":[{"group_address":"4/2/1","main":"Heizung",
            "middle":"Keller","name":"Synthetic Value A","dpt":"DPT 9.7",
            "linked_devices":"1.3.43 Synthetic test sensor"}]}
        quality=dict(checksum_ok=True,even_parity_ok=True,
                     start_stop_ok=True,ack_valid=True,ack_code="CC")
        decoded={"frames":[
            {"host_time":"19:13:06.214","source":"1.3.43","destination":"4/2/1",
             "service":"GroupValueWrite","payload_hex":"1A4F",
             "short_value":None,"frame_hex":"TEST","quality":quality},
            {"host_time":"19:13:27.418","source":"1.0.3","destination":"29/7/241",
             "service":"GroupValueWrite","payload_hex":"","short_value":1,
             "frame_hex":"BC 10 03 EF F1 D1 00 81 1E","quality":quality}]}
        rows=annotate(decoded,meta)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["decoded_value"],"47.28 %RH")
        self.assertTrue(rows[0]["valid"])
        self.assertEqual(rows[1]["name"],"ETS UNASSIGNED")
        self.assertEqual(rows[1]["decoded_value"],"1")
        self.assertTrue(rows[1]["valid"])


if __name__=="__main__":
    unittest.main()
