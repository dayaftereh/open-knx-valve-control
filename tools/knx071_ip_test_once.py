#!/usr/bin/env python3
"""KNX071: single guarded KNXnet/IP group write to ETS-unassigned test address.

Defaults to DRY RUN. Only --execute permits ONE GroupValueWrite (1 bit).
The sender is the existing KNX/IP interface, NOT the OpenKNX PCB's TX pin.
Run in parallel with receiver's RX-only USB COM monitor for bus proof.
This does not make a KNX address private: undisclosed devices may still react.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def verify_fresh_ets_map(mapped: dict, test_group: str) -> tuple[str, int]:
    path = Path(mapped["source"])
    if not path.is_file():
        raise RuntimeError("ETSPROJ_MISSING source file from map")
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha != mapped["source_sha256"]:
        raise RuntimeError("ETS_SOURCE_CHANGED, refuse send until regenerated")
    used = {r["group_address"] for r in mapped["groups"]}
    if test_group in used:
        raise RuntimeError("TEST_GA_IN_ETS_PROJECT, REFUSE: " + test_group)
    if len(used) != mapped["total_groups"] or not used:
        raise RuntimeError("ETS_INVENTORY_UNEXPECTED, REFUSE")
    main = int(test_group.split("/")[0])
    used_mains = {int(row["group_address"].split("/")[0]) for row in mapped["groups"]}
    if main in used_mains:
        raise RuntimeError("TEST_MAIN_GROUP_ALREADY_IN_USE_IN_ETS, REFUSE")
    return actual_sha, len(used)


async def issue_once(args: argparse.Namespace, out: Path) -> dict:
    from xknx import XKNX
    from xknx.io import ConnectionConfig, ConnectionType
    from xknx.telegram import Telegram, GroupAddress
    from xknx.telegram.apci import GroupValueWrite
    from xknx.dpt import DPTBinary

    inbound = []
    def on_receive(t) -> None:
        p = getattr(t, "payload", None)
        rec = {
            "t_utc": stamp(), "kind": "IP_RECEIVE",
            "source": str(getattr(t, "source_address", "")),
            "destination": str(getattr(t, "destination_address", "")),
            "apci": type(p).__name__,
            "payload": str(p) if p else "",
        }
        inbound.append(rec)
        if len(inbound) <= 10 or rec["destination"] == args.group:
            print("IP_RX", rec["t_utc"], rec["source"], rec["destination"], rec["apci"],flush=True)

    cfg = ConnectionConfig(
        connection_type=ConnectionType.TUNNELING,
        local_ip=args.local_ip, gateway_ip=args.gateway,
        gateway_port=args.port, auto_reconnect=False)
    client = XKNX(
        connection_config=cfg, telegram_received_cb=on_receive,
        daemon_mode=False, state_updater=False)
    connected = False
    tx = {}
    try:
        print("KNX071_CONNECT",args.gateway,args.port,"LOCAL",args.local_ip,flush=True)
        await asyncio.wait_for(client.start(),timeout=14)
        connected = True
        print("KNX071_IP_CONNECTED",stamp(),flush=True)
        # A short preflight receive window, no telegram from custom board.
        await asyncio.sleep(2.0)
        msg = Telegram(
            destination_address=GroupAddress(args.group),
            payload=GroupValueWrite(DPTBinary(args.value)))
        tx = {"t_utc": stamp(), "kind": "SINGLE_REQUESTED_GROUP_WRITE",
              "destination": args.group, "bit_value": args.value, "telegram": str(msg)}
        print("KNX071_SEND_ONCE",json.dumps(tx,ensure_ascii=True),flush=True)
        await asyncio.wait_for(client.telegrams.put(msg),timeout=3)
        print("KNX071_ENQUEUED",stamp(),flush=True)
        # Wait for the tunnel to dispatch and observe only.
        await asyncio.sleep(5.0)
    finally:
        if connected:
            await client.stop()
            print("KNX071_IP_DISCONNECTED",stamp(),flush=True)
    result = {"t_utc": stamp(), "source": "KNX071", "gateway": args.gateway,
              "local_ip": args.local_ip, "tx": tx,
              "ip_received": inbound}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KNX071_RESULT",str(out),"rx_count",len(inbound),flush=True)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map",type=Path,required=True)
    ap.add_argument("--gateway",required=True)
    ap.add_argument("--local-ip",required=True)
    ap.add_argument("--port",type=int,default=3671)
    ap.add_argument("--group",required=True)
    ap.add_argument("--value",type=int,choices=(0,1),default=1)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--execute",action="store_true")
    args = ap.parse_args()
    if not re.fullmatch(r"(?:[0-9]|[12][0-9]|3[01])/[0-7]/(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])",args.group):
        raise RuntimeError("INVALID_3LEVEL_GROUP_ADDRESS")
    mapping=json.loads(args.map.read_text(encoding="utf-8"))
    sha,n=verify_fresh_ets_map(mapping,args.group)
    print("ETS_SAFE_GUARD_OK",n,"declared GAs, test group",args.group,
          "NOT DECLARED, ETS SHA",sha,flush=True)
    if not args.execute:
        print("KNX071_DRY_RUN_ONLY_NO_BUS_TELEGRAM_SENT",flush=True)
        return 0
    args.output.parent.mkdir(parents=True,exist_ok=True)
    asyncio.run(issue_once(args,args.output))
    return 0


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print("KNX071_ABORT",type(exc).__name__,str(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
