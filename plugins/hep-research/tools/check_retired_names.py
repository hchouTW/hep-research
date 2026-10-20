#!/usr/bin/env python3
"""Fail on any maintained file that still spells a skill name retired in contracts 3.0.0 (hep-research 0.17.0).

The retired names are known only by their SHA-256 (contracts.skill_names.RETIRED_SHA256), so neither this tool nor
the contract spells them. Every hyphenated word of a maintained text file is hashed and compared. History keeps the
old names (restructuring plan 9.1) and is not scanned: CHANGELOG.md, VALIDATION.md, release-manifests/, docs/dev/,
and evidence ledgers (profiles/*/*/evidence/, dated records).

Usage: python3 tools/check_retired_names.py [--root PLUGIN_ROOT]
Exit 0 clean, 1 a retired name found, 2 bad input. Output: JSON with status and file, line per hit.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contracts import skill_names  # noqa: E402

HISTORY = ("CHANGELOG.md", "VALIDATION.md", "release-manifests/", "docs/dev/")
EVIDENCE = re.compile(r"^profiles/[^/]+/[^/]+/evidence/")
SUFFIXES = (".md", ".py", ".json", ".txt", ".tex", ".sh", ".toml", ".yml", ".yaml", ".cfg", ".C", ".cpp", ".h")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+")


def scanned(root: Path):
    """Maintained text files under root, as (relative path, path)."""
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if (not path.is_file() or "__pycache__" in path.parts or any(p.startswith(".") for p in path.parts[len(root.parts):])
                or rel.startswith(HISTORY) or EVIDENCE.match(rel) or path.suffix not in SUFFIXES):
            continue
        yield rel, path


def hits(root: Path) -> list[dict]:
    out = []
    for rel, path in scanned(root):
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(skill_names.is_retired(w) for w in WORD.findall(line)):
                out.append({"file": rel, "line": i})
    return out


def main(argv: list[str]) -> int:
    root = ROOT
    if argv[:1] == ["--root"] and len(argv) == 2:
        root = Path(argv[1]).resolve()
    elif argv:
        print(json.dumps({"status": "bad-input", "message": __doc__.strip().splitlines()[-2]}))
        return 2
    if not root.is_dir():
        print(json.dumps({"status": "bad-input", "message": f"no folder {root}"}))
        return 2
    found = hits(root)
    print(json.dumps({"status": "fail" if found else "ok", "hits": found}, indent=1))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
