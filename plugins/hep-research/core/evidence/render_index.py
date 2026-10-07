#!/usr/bin/env python3
"""Render (or check) the source table and claim ledger in a profile's evidence index from its JSON ledger.

Paths are explicit arguments and profile-qualified IDs ('<ns>:S30') compress like bare ones.

Purpose: make data/sources.json and data/claims.json the single source of truth so the
human-readable index cannot drift from the machine-readable ledger.

What it does: builds the two markdown tables and either compares them with the blocks
between the GENERATED markers in references/source-index.md (default; exit 1 on any
difference) or rewrites those blocks (--write). Prose outside the markers is hand-written
and untouched. Nothing else in the file is modified.

Usage (from the plugin root):
  python3 core/evidence/render_index.py --sources S --claims C --index I            # check; prints a unified diff on mismatch
  python3 core/evidence/render_index.py --sources S --claims C --index I --write    # regenerate the marked blocks
  python3 core/evidence/render_index.py --sources S --claims C --index I --print    # print the rendered tables only
Exit codes: 0 in sync (or written/printed); 1 out of sync; 2 files unreadable or markers missing.
Standard library only. Importable: render_tables(sources, claims), check_index(text, sources, claims).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

BLOCK = re.compile(r"(<!-- BEGIN GENERATED: (?P<name>[\w-]+)[^>]*-->\n)(?P<body>.*?)(<!-- END GENERATED: (?P=name) -->)", re.S)


def _cell(text) -> str:
    return "" if text is None else str(text).replace("|", "\\|").replace("\n", " ")


def _level(source: dict) -> str:
    note = source.get("verification_note")
    return source["verification_level"] + (f" ({note})" if note else "")


def _compress(ids: list[str]) -> str:
    """Join IDs; runs of four or more consecutive ascending IDs collapse to 'S30-S37'."""
    parsed = [re.fullmatch(r"((?:[a-z][a-z0-9-]*:)?S)(\d+)", i) for i in ids]
    nums: list[Any] = [(m.group(1), int(m.group(2))) if m else None for m in parsed]
    parts, i = [], 0
    while i < len(ids):
        j = i
        while (j + 1 < len(ids) and nums[i] is not None and nums[j + 1] is not None
               and nums[j + 1][0] == nums[j][0] and nums[j + 1][1] == nums[j][1] + 1):
            j += 1
        if j - i >= 3:
            parts.append(f"{ids[i]}-{ids[j]}")
            i = j + 1
        else:
            parts.append(ids[i])
            i += 1
    return ", ".join(parts)


def _claim_type(claim: dict) -> str:
    text = " / ".join(claim["claim_types"])
    return f"{text} ({claim['claim_type_note']})" if claim.get("claim_type_note") else text


def render_tables(sources: list, claims: list) -> dict[str, str]:
    """Return {'source-table': markdown, 'claim-ledger': markdown}."""
    src = ["| ID | Title | Authors | Year | DOI / URL | Tier | Level |", "|---|---|---|---|---|---|---|"]
    for s in sources:
        src.append("| " + " | ".join(_cell(x) for x in (
            s["id"], s["title"], s["authors"], s.get("year_text", s.get("year")),
            s.get("locator_text") or " ; ".join(s.get("dois") or []) or s.get("url"),
            s.get("tier_text", s["tier"]), _level(s))) + " |")
    clm = ["| claim_id | claim (paraphrased) | type | source | location | supported scope | limitation |", "|---|---|---|---|---|---|---|"]
    for c in claims:
        row = "| " + " | ".join(_cell(x) for x in (
            c["id"], c["claim"], _claim_type(c), _compress(c["source_ids"]), c["location"],
            c["scope"]["text"], c.get("limitations"))) + " |"
        clm.append(re.sub(r"  \|$", " |", row))  # an empty last cell renders as '| |'
    return {"source-table": "\n".join(src) + "\n", "claim-ledger": "\n".join(clm) + "\n"}


def check_index(text: str, sources: list, claims: list) -> tuple[bool, str]:
    """Compare the generated blocks in `text` with a fresh render. Returns (in_sync, diff_or_error)."""
    rendered = render_tables(sources, claims)
    found = {m.group("name"): m.group("body") for m in BLOCK.finditer(text)}
    problems, diff = [], []
    for name, body in rendered.items():
        if name not in found:
            problems.append(f"missing GENERATED block '{name}'")
        elif found[name] != body:
            diff += list(difflib.unified_diff(found[name].splitlines(), body.splitlines(),
                                              f"index:{name}", f"rendered:{name}", lineterm="", n=0))
    if problems or diff:
        return False, "\n".join(problems + diff)
    return True, ""


def write_index(text: str, sources: list, claims: list) -> str:
    rendered = render_tables(sources, claims)
    if not all(m.group("name") in rendered for m in BLOCK.finditer(text)) or len(list(BLOCK.finditer(text))) != len(rendered):
        raise ValueError("source-index.md must contain exactly the GENERATED blocks: " + ", ".join(rendered))
    return BLOCK.sub(lambda m: m.group(1) + rendered[m.group("name")] + m.group(4), text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True, help="markdown file with GENERATED blocks")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite the GENERATED blocks in place")
    mode.add_argument("--print", action="store_true", help="print the rendered tables and exit")
    args = parser.parse_args(argv)
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        claims = json.loads(args.claims.read_text(encoding="utf-8"))
        text = args.index.read_text(encoding="utf-8") if not args.print else ""
    except (OSError, ValueError) as exc:
        print(f"unreadable: {exc}", file=sys.stderr)
        return 2
    if args.print:
        for name, body in render_tables(sources, claims).items():
            print(f"<!-- {name} -->\n{body}")
        return 0
    try:
        if args.write:
            args.index.write_text(write_index(text, sources, claims), encoding="utf-8")
            print(f"wrote {args.index}")
            return 0
        ok, detail = check_index(text, sources, claims)
    except ValueError as exc:
        print(f"unreadable: {exc}", file=sys.stderr)
        return 2
    if ok:
        print(f"{args.index.name} is in sync with the ledger")
        return 0
    print(f"{args.index.name} is OUT OF SYNC with the ledger:\n" + detail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
