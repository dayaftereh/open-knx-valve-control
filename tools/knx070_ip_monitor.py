#!/usr/bin/env python3
"""KNX070: passive KNXnet/IP tunnelling group monitor for cross-validation.

Needs xknx>=4 in an isolated Python environment. Sends KNXnet/IP control
handshake/keepalive/ack messages, but NEVER a KNX TP GroupValueRead/Write.
No KNX device objects, no state updater or outgoing telegrams are configured.
A KNX/IP routing listener is different; SCN-IP000.03 is a tunnelling interface.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def make_record(telegram: object) -> dict[str, object]:
    payload = getattr(telegram, "payload", None)
    value = getattr(payload, "value", None)
    nested_value = getattr(value, "value", None)
    if isinstance(nested_value, (list, tuple)):
        value_repr: object = list(nested_value)
    elif isinstance(nested_value, (bytes, bytearray)):
        value_repr = list(nested_value)
    elif isinstance(nested_value, (int, float, str, bool, type(None))):
        value_repr = nested_value
    else:
        value_repr = repr(nested_value)
    return {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "source": str(getattr(telegram, "source_address", "")),
        "destination": str(getattr(telegram, "destination_address", "")),
        "apci": type(payload).__name__,
        "value": value_repr,
        "telegram": str(telegram),
    }


async def monitor(args: argparse.Namespace) -> int:
    from xknx import XKNX
    from xknx.io import ConnectionConfig, ConnectionType

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8", buffering=1) as writer:
        def received(telegram: object) -> None:
            nonlocal count
            rec = make_record(telegram)
            writer.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
            if count <= 15 or count % 20 == 0:
                print("IP_RX", count, rec["time_utc"], rec["source"], "->",
                      rec["destination"], rec["apci"], rec["value"], flush=True)

        cfg = ConnectionConfig(
            connection_type=ConnectionType.TUNNELING,
            local_ip=args.local_ip,
            gateway_ip=args.gateway,
            gateway_port=args.port,
            auto_reconnect=False,
        )
        xknx = XKNX(connection_config=cfg, telegram_received_cb=received,
                    daemon_mode=False, state_updater=False)
        print("IP_MONITOR_CONNECT local="+args.local_ip+
              " gateway="+args.gateway+":"+str(args.port),
              "mode=TUNNELING PASSIVE_ONLY_NO_KNX_TELEGRAM_OUTPUT", flush=True)
        try:
            await asyncio.wait_for(xknx.start(), timeout=14.0)
            print("IP_MONITOR_CONNECTED", flush=True)
            await asyncio.sleep(args.seconds)
        finally:
            await xknx.stop()
            print("IP_MONITOR_STOPPED count="+str(count)+" log="+str(out), flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gateway", required=True, help="IP of KNX/IP interface")
    ap.add_argument("--local-ip", required=True, help="local adapter address")
    ap.add_argument("--port", type=int, default=3671)
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if not 1 <= args.seconds <= 180:
        ap.error("seconds must be between 1 and 180")
    return asyncio.run(monitor(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TimeoutError, RuntimeError, ValueError) as exc:
        print("IP_MONITOR_ERROR", type(exc).__name__, str(exc), file=sys.stderr)
        raise SystemExit(2)
