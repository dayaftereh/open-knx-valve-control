"""Normalize OpenKNXproducer duplicate KO numeric and accessor macros.

OpenKNXproducer emits a numeric macro and a second macro with the same name
referencing knx.getGroupObject. Keep the numeric macro and rename only the
second accessor macro to NameObject. Do not change object IDs or numbering.
"""
from __future__ import annotations
from pathlib import Path
import re

DEFINE = re.compile(r"^(\s*#define\s+)(\S+)(\s+)(.*?)(\r?\n?)$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
FUNCTION_MACRO = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*\([^)]*\)$")
NUMBER = re.compile(r"^\d+(?:\s*//.*)?$")
ACCESSOR = re.compile(r"^\(knx\.getGroupObject\(([A-Za-z_][A-Za-z_0-9]*)\)\)(?:\s*//.*)?$")


def normalized_text(src: str) -> str:
    parsed = []
    numeric = {}
    for line in src.splitlines(keepends=True):
        match = DEFINE.match(line)
        if match:
            _, name, _, body, _ = match.groups()
            if not IDENT.fullmatch(name) and not FUNCTION_MACRO.fullmatch(name):
                raise ValueError("Invalid generated C++ macro identifier: " + name)
            if name.startswith("Ko") and NUMBER.fullmatch(body):
                if name in numeric:
                    raise ValueError("Duplicate numeric KO identifier: " + name)
                numeric[name] = body.split()[0]
        parsed.append((line, match))

    if not numeric:
        raise ValueError("Generated header contains no numeric KO identifiers")

    normalized = []
    aliases = set()
    for line, match in parsed:
        if not match:
            normalized.append(line)
            continue
        prefix, name, spaces, body, newline = match.groups()
        accessor = ACCESSOR.fullmatch(body)
        if accessor and name == accessor.group(1) and name in numeric:
            if name in aliases:
                raise ValueError("Duplicate KO accessor: " + name)
            aliases.add(name)
            normalized.append(prefix + name + "Object" + spaces + body + newline)
        else:
            normalized.append(line)

    if set(numeric) != aliases:
        raise ValueError("Missing KO accessors: " +
                         ", ".join(sorted(set(numeric) - aliases)))
    if len(numeric) != 35:
        raise ValueError("KNX015 requires exactly 35 stable KO definitions")

    result = "".join(normalized)
    seen = set()
    for line in result.splitlines():
        match = DEFINE.match(line)
        if match:
            name = match.group(2)
            if name in seen:
                raise ValueError("Duplicate macro after normalization: " + name)
            seen.add(name)

    for idx in range(9):
        name = "KoT" + str(idx)
        if numeric.get(name) != str(25 + idx):
            raise ValueError("Temperature KO index changed: " + name)

    if numeric.get("KoTemperatureBridgeOnline") != "34" or \
       numeric.get("KoTemperatureValidMask") != "35":
        raise ValueError("Diagnostic KO indexes changed")

    return result


def normalize_header(path: str | Path) -> int:
    path = Path(path)
    raw = path.read_bytes()
    normalized = normalized_text(raw.decode("utf-8"))
    if normalized.encode("utf-8") != raw:
        path.write_bytes(normalized.encode("utf-8"))
    return 35


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: knxprod_header_fix.py <generated-header-path>")
    print("Normalized KO declarations:", normalize_header(sys.argv[1]))
