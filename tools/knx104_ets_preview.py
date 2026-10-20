#!/usr/bin/env python3
"""KNX104: Generate/verify an ETS V3 *proposal* manifest without KNX access.

This does NOT alter ETS AppVersion2, .knxprod, group addresses or firmware
motor IO. Source is the checked-in KNX008 AppVersion3 proposal. KNX104
adds unallocated mapping/verification parameter ideas (40-56), not deployable
ETS ParameterRefs or production memory offsets.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"assets"/"knx008_zone_ets_proposal.json"
XML=ROOT/"assets"/"open-knx-valve-control.xml"
FROZEN=ROOT/"assets"/"knx104_motor_ets_preview.json"

class ContractError(ValueError): pass

def require(condition, message):
    if not condition: raise ContractError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    proposal=json.loads(SOURCE.read_text("utf8"))
    existing=ET.parse(XML).getroot()
    actual_app=[e for e in existing.iter()
                if e.tag.rsplit("}",1)[-1]=="ApplicationProgram"]
    actual_objects=[e for e in existing.iter()
                    if e.tag.rsplit("}",1)[-1]=="ComObject"]
    require(len(actual_app)==1,"Unknown ETS existing application count")
    require(actual_app[0].get("ApplicationVersion")=="2","ETS XML version unexpectedly changed")
    require(len(actual_objects)==35,"Current ETS XML KO baseline changed; audit required")
    require(proposal.get("status")=="PROPOSAL_ONLY__NOT_IN_ETS_XML_OR_FIRMWARE",
            "KNX008 source is no longer proposal-only")
    legacy=proposal["baseline"]
    require(legacy["existingApplicationVersion"]==2 and
            legacy["proposedApplicationVersion"]==3 and
            legacy["existingCommunicationObjects"]==35 and
            legacy["existingParameters"]==21,"Unexpected KNX008 object/param baseline")
    objects={x["number"]:x for x in proposal["proposedComObjects"]}
    require(set(objects)==set(range(36,101)),"KNX008 KO36..100 missing/duplicated")
    params={x["number"]:x for x in proposal["proposedParameters"]}
    require(set(params)==set(range(22,40)),"KNX008 params22..39 changed")
    zone_objects=[]
    motor_objects=[]
    for z in range(1,9):
        obj=38+4*(z-1)
        require(objects[obj]["dpt"]=="5.001" and
                objects[obj]["direction"]=="rx" and
                objects[obj]["zone"]==z,
                f"Zone {z} DPT5.001 KO contract mismatch")
        zone_objects.append({
            "zone":z,"directDemandRxKo":obj,
            "dpt":"5.001","applicationPayloadBytes":1,
            "frameKind":"GroupValueWrite","notLegacyKo17to24":True,
            "modeRequired":"DirectPercent","gaBindingMustBeVerified":True,
        })
    for m in range(1,9):
        ko={
            "estimatedPositionTxKo":67+m,
            "faultTxKo":75+m,
            "referencedTxKo":83+m,
            "movingTxKo":91+m,
            "deviceBusyTxKo":100,
        }
        expected_dpts=["5.001","1.005","1.002","1.001","1.002"]
        for (key,num),dpt in zip(ko.items(),expected_dpts):
            require(objects[num]["dpt"]==dpt and objects[num]["direction"]=="tx",
                    f"Motor{m} wrong {key} DPT or transport direction")
        motor_objects.append({
            "motor":m,**ko,"positionIsOnlyTimeEstimate":True,
            "defaultPhysicalDirectionConfirmed":False,
            "defaultPositionTxAvailable":False,
        })

    # These are new IDS for future ETS application proposal only; existing
    # KNX008 has not assigned physical memory offsets for these parameters.
    proposed_new_parameters=[]
    for i in range(1,9):
        proposed_new_parameters.append({
            "number":39+i,"name":f"Motor{i}PhysicalDirection",
            "type":"enum",
            "values":{"0":"Unconfirmed","1":"F_End_Closed","2":"R_End_Closed"},
            "default":0,"memoryOffset":"UNALLOCATED",
            "requiresPhysicalCommissioningEvidence":True})
    for i in range(1,9):
        proposed_new_parameters.append({
            "number":47+i,"name":f"Motor{i}PhysicalMappingVerified",
            "type":"boolean","default":False,
            "memoryOffset":"UNALLOCATED",
            "requiresIndependentActualMotorDirectionCheck":True})
    proposed_new_parameters.append({
        "number":56,"name":"ETS_V3_ValveDirectionCommissioningGate",
        "type":"boolean","default":False,
        "memoryOffset":"UNALLOCATED",
        "mustRemainFalseUntilEtsApp3AndPhysicalDirectionValidated":True})

    new_ids={p["number"] for p in proposed_new_parameters}
    require(new_ids==set(range(40,57)),"KNX104 future parameter IDs overlap")
    return {
        "schema":"openknxvalve.knx104.motor-ets-contract-preview.v1",
        "status":"OFFLINE_PROPOSAL_NOT_IN_ETS_XML_NOT_DEPLOYED",
        "sourceKnx008Sha256":sha(SOURCE),
        "existingEtsXmlSha256":sha(XML),
        "existingXmlApplicationVersion":2,
        "futureProposalApplicationVersion":3,
        "existingXmlComObjects":35,
        "preserveLegacyKoRange":[1,35],
        "preserveLegacyDpt5004KoRange":[17,24],
        "existingKnx008ProposalKoRange":[36,100],
        "existingKnx008ProposalParameterRange":[22,39],
        "safeDefaults":{
            "mode":"Disabled","mapping":"Unconfirmed",
            "physicallyVerified":False,
            "etsV3Commissioned":False,
            "allowMotorCommands":False,
            "allowEstimatedPhysicalOpenFeedback":False,
            "directDemandTimeoutSeconds":300,
        },
        "proposedZoneDirectDemandDescriptors":zone_objects,
        "proposedMotorTelemetryDescriptors":motor_objects,
        "knx104AdditionalUNALLOCATEDParameterIDs":proposed_new_parameters,
        "requirements":[
            "Telegram DPT supplied by trusted ETS GA association, never on-wire inferred.",
            "Do not read legacy 5.004 KO17..24 as scaling 5.001.",
            "No motor movement or physical position output while R/F direction unknown.",
            "KNX099 position and motor INA/GPIO safety remain separate, not a KNX command.",
            "No production .knxprod or KNX interface exists for this V3 extension.",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--freeze",action="store_true")
    opt=p.parse_args()
    manifest=build()
    if opt.freeze:
        require(not FROZEN.exists(),"Already frozen. Do not overwrite without review.")
        FROZEN.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",
                          encoding="utf8",newline="\n")
        print("KNX104_ETS_PROPOSAL_FROZEN",FROZEN)
    else:
        require(FROZEN.exists(),"Proposal manifest not found")
        require(manifest==json.loads(FROZEN.read_text("utf8")),
                "ETS proposal changed / source no longer consistent")
        print("KNX104_ETS_PROPOSAL_VERIFIED",FROZEN)
    print("KNX104_ETS_SAFETY_CONTRACT_PASS 8 zones 8 motors legacy35 preserved no motor IO")
if __name__=="__main__":
    main()
