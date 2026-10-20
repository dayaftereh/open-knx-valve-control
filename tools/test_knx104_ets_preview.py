#!/usr/bin/env python3
"""KNX104 zero-KNX-bus ETS preview schema and guard regression tests."""
from __future__ import annotations
import json,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import knx104_ets_preview as m

class KNX104(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=json.loads(m.FROZEN.read_text("utf8"))

    def test_01_immutable_ets_manifest(self):
        self.assertEqual(m.build(),self.output)

    def test_02_appversion2_xml_still_untouched(self):
        self.assertEqual(self.output["existingXmlApplicationVersion"],2)
        self.assertEqual(self.output["existingXmlComObjects"],35)
        self.assertEqual(self.output["existingEtsXmlSha256"],m.sha(m.XML))
        self.assertEqual(self.output["sourceKnx008Sha256"],m.sha(m.SOURCE))
        self.assertIn("NOT_DEPLOYED",self.output["status"])

    def test_03_old_knx_ko_numbers_preserved(self):
        self.assertEqual(self.output["preserveLegacyKoRange"],[1,35])
        self.assertEqual(self.output["preserveLegacyDpt5004KoRange"],[17,24])
        self.assertEqual(self.output["existingKnx008ProposalKoRange"],[36,100])
        self.assertEqual(self.output["existingKnx008ProposalParameterRange"],[22,39])

    def test_04_eight_zone_receivers_exact_5_001(self):
        a=self.output["proposedZoneDirectDemandDescriptors"]
        self.assertEqual(len(a),8)
        self.assertEqual([x["directDemandRxKo"] for x in a],
                         [38,42,46,50,54,58,62,66])
        self.assertTrue(all(x["dpt"]=="5.001" and x["gaBindingMustBeVerified"]
                            and x["frameKind"]=="GroupValueWrite" for x in a))

    def test_05_eight_motor_transmitters_no_alias(self):
        a=self.output["proposedMotorTelemetryDescriptors"]
        self.assertEqual(len(a),8)
        for i,row in enumerate(a,1):
            self.assertEqual(row["estimatedPositionTxKo"],67+i)
            self.assertEqual(row["faultTxKo"],75+i)
            self.assertEqual(row["referencedTxKo"],83+i)
            self.assertEqual(row["movingTxKo"],91+i)
            self.assertEqual(row["deviceBusyTxKo"],100)
            self.assertTrue(row["positionIsOnlyTimeEstimate"])
            self.assertFalse(row["defaultPositionTxAvailable"])

    def test_06_proposed_parameter_ids_unused(self):
        a=self.output["knx104AdditionalUNALLOCATEDParameterIDs"]
        self.assertEqual([v["number"] for v in a],list(range(40,57)))
        self.assertTrue(all(x["memoryOffset"]=="UNALLOCATED" for x in a))
        self.assertTrue(all(not (x["default"] is True) for x in a))
        self.assertEqual(a[-1]["default"],False)

    def test_07_commissioning_default_is_safe(self):
        d=self.output["safeDefaults"]
        self.assertEqual(d["mode"],"Disabled")
        self.assertEqual(d["mapping"],"Unconfirmed")
        for item in ("physicallyVerified","etsV3Commissioned",
                     "allowMotorCommands","allowEstimatedPhysicalOpenFeedback"):
            self.assertIs(d[item],False)
        self.assertEqual(d["directDemandTimeoutSeconds"],300)

    def test_08_wrong_source_KO_rejected(self):
        original=json.loads(m.SOURCE.read_text("utf8"))
        original["proposedComObjects"][0]["number"]=104
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.json"
            path.write_text(json.dumps(original),encoding="utf8")
            with patch.object(m,"SOURCE",path):
                with self.assertRaises(m.ContractError):m.build()

    def test_09_wrong_source_param_rejected(self):
        original=json.loads(m.SOURCE.read_text("utf8"))
        original["proposedParameters"][0]["number"]=1
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.json"
            path.write_text(json.dumps(original),encoding="utf8")
            with patch.object(m,"SOURCE",path):
                with self.assertRaises(m.ContractError):m.build()

    def test_10_current_product_xml_ver_changed_rejected(self):
        source=m.XML.read_text("utf8")
        self.assertIn('ApplicationVersion="2"',source)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.xml"
            path.write_text(source.replace('ApplicationVersion="2"',
                                           'ApplicationVersion="3"',1),encoding="utf8")
            with patch.object(m,"XML",path):
                with self.assertRaises(m.ContractError):m.build()

    def test_11_cpp_and_controller_no_runtime_binding(self):
        header=(m.ROOT/"lib/common/knx104_m1_ets_contract.hpp").read_text("utf8")
        main=(m.ROOT/"src/controller/main.cpp").read_text("utf8")
        self.assertIn("valveSemanticsUnlocked",header)
        self.assertIn("heating_zone_model.hpp",header)
        self.assertNotIn("gpio_put(",header)
        self.assertNotIn("digitalWrite(",header)
        self.assertNotIn("knx.getGroupObject(",header)
        self.assertIn('#include "knx104_m1_ets_contract.hpp"',main)
        self.assertIn('static_assert(sizeof(Knx104::Contract)',main)
        self.assertNotIn("Knx104::Contract motor",main)

if __name__=="__main__":
    unittest.main(verbosity=2)
