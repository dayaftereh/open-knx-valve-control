#!/usr/bin/env python3
"""KNX024 negative in-memory ETS schema drift checks; never edits source JSON."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_knx024_room_ets_contract as contract


def must_block(base: dict, what: str, mutate) -> None:
    sample = deepcopy(base)
    mutate(sample)
    try:
        with redirect_stdout(StringIO()):
            contract.check_proposal(sample)
    except contract.ContractError:
        print("PASS BLOCKED:", what)
        return
    raise AssertionError("FAIL: changed ETS contract was accepted: " + what)


def main() -> int:
    base = json.loads((ROOT / contract.PROPOSAL).read_text(encoding="utf8"))
    with redirect_stdout(StringIO()):
        contract.check_proposal(base)
    print("PASS baseline 65 KO / 18 parameters")

    def edit(index, key, value):
        return lambda p: p["proposedComObjects"][index].__setitem__(
            key, value)

    must_block(base, "Legacy DPT5.004 incorrectly used as new direct 5.001",
               edit(2, "dpt", "5.004"))
    must_block(base, "Room temperature mislabeled as direct scaling",
               edit(0, "dpt", "5.001"))
    must_block(base, "KO39 mistakenly becomes receive-only",
               edit(3, "direction", "rx"))
    must_block(base, "KO67 becomes 2 byte",
               edit(31, "sizeBytes", 2))
    must_block(base, "Incorrect zone 8 room object number",
               edit(28, "number", 65))
    must_block(base, "Incorrect temperature object zone binding",
               edit(17, "zone", 8))
    must_block(base, "Changed first room object name",
               edit(0, "name", "LegacyMotorDemand"))
    must_block(base, "Frozen KO1..35 protection changed",
               lambda p: p["baseline"].__setitem__("preserveKoRange", [1, 34]))
    must_block(base, "Existing KO count changed to 67",
               lambda p: p["baseline"].__setitem__(
                   "existingCommunicationObjects", 67))
    must_block(base, "Old KO17..24 erroneously marked DPT5.001",
               lambda p: p["percentage"].__setitem__(
                   "legacyDptToPreserve", "5.001"))
    must_block(base, "P38 room timeout moved",
               lambda p: p["proposedParameters"][16].__setitem__(
                   "number", 40))
    must_block(base, "P39 direct timeout renamed",
               lambda p: p["proposedParameters"][17].__setitem__(
                   "name", "OldStaleTimer"))
    must_block(base, "Proposed product incorrectly claims ETS promotion",
               lambda p: p.__setitem__("status", "IN_PRODUCTION_ETS_XML"))
    print("RESULT: 13 KNX024 contract-negative cases PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
