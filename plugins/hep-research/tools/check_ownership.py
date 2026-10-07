#!/usr/bin/env python3
"""Ownership check: one owner per topic in the ownership table of docs/routing-contract.md.

The table sits between `<!-- ownership-table -->` markers and has the columns Topic | Owner | Claim terms |
Capability-matrix row. For every topic:
1. the owner's "**Owns:**" line claims at least one of the topic's terms;
2. no other skill claims a term in its "**Owns:**" line, in the "Use when" part of its description (before "Not for")
   or in its row of the README skill table;
3. the named capability-matrix row (if not "—") lists the owner first in its Owner column.
Terms are matched case-insensitively, with hyphens read as spaces and on word boundaries.

Usage: python3 tools/check_ownership.py [--root DIR]   Exit 0 ok, 1 problems. Output: JSON. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("-", " ").replace("/", " ")).lower()


def claims(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(norm(term)) + r"(?![a-z])", norm(text)) is not None


def table_rows(md: str, start: str, end: str | None = None) -> list[list[str]]:
    block = md.split(start, 1)[1] if start in md else ""
    if end:
        block = block.split(end, 1)[0]
    rows = []
    for line in block.splitlines():
        if not line.startswith("|"):
            if rows and end is None:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:]  # drop the header


def ownership_table(root: Path) -> list[dict]:
    md = (root / "docs" / "routing-contract.md").read_text(encoding="utf-8")
    rows = table_rows(md, "<!-- ownership-table", "<!-- /ownership-table -->")
    return [{"topic": r[0], "owner": r[1], "terms": re.findall(r"`([^`]+)`", r[2]), "matrix_row": r[3]} for r in rows]


def skill_texts(root: Path) -> dict:
    out = {}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        owns = re.search(r"^\*\*Owns:\*\*(.*)$", text, re.M)
        desc = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
        out[path.parent.name] = {"owns": owns.group(1) if owns else "",
                                 "use_when": (desc.group(1) if desc else "").partition("Not for")[0]}
    readme = (root / "README.md").read_text(encoding="utf-8")
    for cells in table_rows(readme, "| Skill | Use it when the deliverable is |"):
        name = cells[0].strip("`")
        if name in out:
            out[name]["readme"] = cells[1]
    return out


def check(root: Path = ROOT) -> list[str]:
    topics, skills = ownership_table(root), skill_texts(root)
    problems = [] if topics else ["no ownership table found in docs/routing-contract.md"]
    matrix = {r[0]: r[1] for r in table_rows((root / "docs" / "capability-matrix.md").read_text(encoding="utf-8"),
                                             "| Capability | Owner | Status |")}
    for t in topics:
        if t["owner"] not in skills:
            problems.append(f"{t['topic']}: owner {t['owner']} is not a skill")
            continue
        if not t["terms"]:
            problems.append(f"{t['topic']}: no claim terms")
        if not any(claims(skills[t["owner"]]["owns"], term) for term in t["terms"]):
            problems.append(f"{t['topic']}: owner {t['owner']} does not claim it in its Owns line")
        for name, s in skills.items():
            if name == t["owner"]:
                continue
            for where in ("owns", "use_when", "readme"):
                hit = [term for term in t["terms"] if claims(s.get(where, ""), term)]
                if hit:
                    problems.append(f"{t['topic']}: owned by {t['owner']} but {name} claims {hit} in its {where}")
        row = t["matrix_row"]
        if row and row not in ("—", "-"):
            if row not in matrix:
                problems.append(f"{t['topic']}: capability-matrix row '{row}' not found")
            elif matrix[row].split(",")[0].strip() != t["owner"]:
                problems.append(f"{t['topic']}: capability-matrix row '{row}' lists owner '{matrix[row]}', not {t['owner']}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this plugin)")
    opts = ap.parse_args(argv)
    problems = check(opts.root)
    print(json.dumps({"status": "fail" if problems else "pass", "topics": len(ownership_table(opts.root)),
                      "problems": problems}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
