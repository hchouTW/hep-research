#!/usr/bin/env python3
"""Insert the shared context-resolution stanza into every core SKILL.md (between markers),
or check that each copy matches the template.

Usage: python3 tools/build_stanzas.py [--check]     exit 0 ok, 1 drift/missing markers
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "contracts" / "stanzas" / "context-resolution.md"
BEGIN = "<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->"
END = "<!-- END context-resolution -->"
BLOCK = re.compile(re.escape(BEGIN.split(":")[0]) + r".*?" + re.escape(END), re.S)


def render() -> str:
    return f"{BEGIN}\n{TEMPLATE.read_text(encoding='utf-8').strip()}\n{END}"


def main(argv=None) -> int:
    check = "--check" in (sys.argv[1:] if argv is None else argv)
    want, problems = render(), []
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        blocks = BLOCK.findall(text)
        if len(blocks) != 1:
            problems.append(f"{skill.relative_to(ROOT)}: expected exactly one stanza block, found {len(blocks)}")
            continue
        if blocks[0] != want:
            if check:
                problems.append(f"{skill.relative_to(ROOT)}: stanza differs from template")
            else:
                skill.write_text(text.replace(blocks[0], want), encoding="utf-8")
    print(json.dumps({"ok": not problems, "problems": problems}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
