#!/usr/bin/env python3
"""Check local ASH Project Workflow v1 references, project links and Slice state.

Read-only stdlib validation; this does not validate ECU/PCB/ERC/ETS or runtime hardware.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "docs" / "reference" / "ash"
NAMES = (
    "README_PROJECT_WORKFLOW.md",
    "SLICE_PROTOCOL.md",
    "SLICE_TEMPLATE.md",
    "PROJECT_PROTOCOL.md",
    "PROJECT_PROFILES.md",
    "RECOVERY_HANDOFF.md",
    "EXAMPLES.md",
)

errors: list[str] = []
count = 0


def check(cond: bool, label: str) -> None:
    global count
    count += 1
    print(f"{'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        errors.append(label)


def normalized_hash(path: Path) -> str:
    # Compare contents independently of Git's configured Windows CRLF worktree policy.
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def validate_links() -> tuple[int, list[str]]:
    total = 0
    issues = []
    files = [ROOT / "README.md", ROOT / ".ash" / "WORKFLOW.md"]
    files.extend(sorted((ROOT / "docs").rglob("*.md")))
    for md in files:
        data = md.read_text(encoding="utf-8-sig")
        for match in re.finditer(r"\[[^\]\n]+\]\(([^)]+)\)", data):
            target = match.group(1).strip().split(None, 1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            total += 1
            if not (md.parent / target).exists():
                issues.append(f"{md.relative_to(ROOT)}: {target}")
    return total, issues


def main() -> int:
    config = ROOT / ".ash" / "project.yaml"
    check(config.is_file(), "ASH project.yaml present")
    if config.is_file():
        text = config.read_text(encoding="utf-8")
        for item in ("protocol: ash-project/v1", "profile: software",
                     "max_active_write: 1", "marker_dir: docs/slices",
                     "- checkup", "- decision", "- implementation", "- validation"):
            check(item in text, "Config includes " + item)
    for name in NAMES:
        check((REF / name).is_file(), "ASH source " + name)
    manifest = REF / "MANIFEST.sha256"
    check(manifest.is_file(), "ASH reference SHA256 manifest present")
    if manifest.is_file():
        actual = []
        for line in manifest.read_text(encoding="ascii").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            digest, filename = line.split(maxsplit=1)
            filename = filename.strip().lstrip("*")
            actual.append(filename)
            file = REF / filename
            check(filename in NAMES and file.is_file() and normalized_hash(file) == digest,
                  f"ASH SHA256 normalized {filename}")
        check(set(actual) == set(NAMES), "Manifest covers exactly 7 workflow source files")
    markers = sorted((ROOT / "docs" / "slices").glob("_OPEN_*.md"))
    check(len(markers) <= 1, "At most one active Write-Slice marker")
    print("INFO  Active markers:", ", ".join(p.name for p in markers) or "none")
    for path in ("docs/ROADMAP.md", "docs/slices/README.md", "docs/slices/HISTORY.md"):
        check((ROOT / path).is_file(), "Project slice documentation " + path)
    links, broken = validate_links()
    check(not broken, f"{links} local Markdown links resolve across project + all ASH sources")
    for item in broken[:50]:
        print("BROKEN", item)
    print(f"RESULT: {len(errors)} ASH workflow audit failures; {count} checks")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
