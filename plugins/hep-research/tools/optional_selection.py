#!/usr/bin/env python3
"""Which test modules each optional CI extra needs, from check-run records (tools/run_all_checks.py --out).

Usage: python3 tools/optional_selection.py generate --required DIR [DIR ...] --optional NAME=DIR [NAME=DIR ...]
                                                    [--out FILE] [--source TEXT]
       python3 tools/optional_selection.py verify --required DIR [DIR ...] --optional NAME=DIR [NAME=DIR ...]
                                                  [--selection FILE]

A test is unlocked by an extra when the required units runs (all shards, without the extra) skip it and the full
optional run with the extra installed does not. generate writes, per extra, the modules that hold unlocked tests
(the format of tools/optional_modules.json, read by run_all_checks.py --extra); verify fails when an unlocked test sits
in a module the selection does not list for that extra, so a pull request running only the selected modules would
miss it. Both need a full optional run (no --extra, no --shard): a selective run cannot show what it did not run.
What this cannot see: a test that runs in both environments but behaves differently with the extra installed. That is
why pushes to main and the weekly run keep the full optional suites.
Exit 0 ok, 1 verify found an unlisted module, 2 bad input. Prints a JSON report.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "tools" / "optional_modules.json"
NOTE = ("Test modules each optional CI extra needs (tests that the required jobs skip and the extra unlocks); "
        "run_all_checks.py --extra NAME runs only these on pull requests. Regenerate with tools/optional_selection.py "
        "generate from a full CI run; pushes to main check it with optional_selection.py verify.")


class InputError(ValueError):
    """Bad usage or unreadable records (exit 2)."""


def unit_records(folder: Path) -> list[dict]:
    """The unittest check of every check-run-*.json under folder."""
    out = []
    for f in sorted(folder.rglob("check-run-*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        out += [c for c in doc.get("checks", []) if c.get("name") == "unittest"]
    if not out:
        raise InputError(f"{folder}: no check-run record with a unittest check")
    return out


def test_id(entry: str) -> str:
    """'name (module.Class.name): reason' -> 'name (module.Class.name)'."""
    head, sep, _ = entry.partition("): ")
    return head + ")" if sep else entry.split(": ", 1)[0]


def module_of(tid: str) -> str:
    m = re.search(r"\(([^()]*)\)$", tid)
    if not m:
        raise InputError(f"cannot read the module of skipped test {tid!r}")
    parts = m.group(1).split(".")
    return ".".join(parts[:-2]) if len(parts) > 2 and parts[-1] == tid.split(" ", 1)[0] else ".".join(parts[:-1])


def unlocked(required: list[dict], optional: list[dict]) -> dict[str, list[str]]:
    """{module: [test ids]} skipped in the required runs and not skipped in the full optional run."""
    if len(optional) != 1:
        raise InputError(f"expected one optional units run, found {len(optional)}")
    plan = optional[0].get("plan") or {}
    if plan.get("extra") or plan.get("shard", "1/1") != "1/1":
        raise InputError("the optional run must be a full run (no --extra, no --shard)")
    ran = {r["module"] for r in optional[0]["modules"]}
    req_skip = {test_id(s) for u in required for s in u.get("skipped", [])}
    opt_skip = {test_id(s) for s in optional[0].get("skipped", [])}
    out: dict[str, list[str]] = {}
    for tid in sorted(req_skip - opt_skip):
        mod = module_of(tid)
        if mod in ran:
            out.setdefault(mod, []).append(tid)
    return out


def parse_optional(items: list[str]) -> dict[str, Path]:
    out = {}
    for it in items:
        name, sep, path = it.partition("=")
        if not sep or not name or not path:
            raise InputError(f"--optional wants NAME=DIR, got {it!r}")
        out[name] = Path(path)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("generate", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--required", nargs="+", type=Path, required=True, metavar="DIR")
        p.add_argument("--optional", nargs="+", required=True, metavar="NAME=DIR")
        if name == "generate":
            p.add_argument("--out", type=Path, metavar="FILE")
            p.add_argument("--source", default="", metavar="TEXT")
        else:
            p.add_argument("--selection", type=Path, default=SELECTION, metavar="FILE")
    args = ap.parse_args(argv)
    try:
        required = [u for d in args.required for u in unit_records(d)]
        if any((u.get("plan") or {}).get("extra") for u in required):
            raise InputError("a --required record was run with --extra")
        found = {name: unlocked(required, unit_records(d)) for name, d in parse_optional(args.optional).items()}
        if args.cmd == "generate":
            doc = {"note": NOTE, "source": args.source,
                   "extras": {name: sorted(mods) for name, mods in sorted(found.items())}}
            text = json.dumps(doc, indent=1) + "\n"
            if args.out:
                args.out.write_text(text, encoding="utf-8")
            print(json.dumps({"status": "ok", "extras": {k: len(v) for k, v in doc["extras"].items()}}, indent=1))
            return 0
        listed = json.loads(args.selection.read_text(encoding="utf-8")).get("extras", {})
    except (InputError, OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, indent=1))
        return 2
    missing = {name: {m: tests for m, tests in mods.items() if m not in listed.get(name, [])}
               for name, mods in found.items()}
    missing = {k: v for k, v in missing.items() if v}
    print(json.dumps({"status": "failed" if missing else "ok", "unlisted": missing,
                      "unlocked_modules": {k: sorted(v) for k, v in found.items()}}, indent=1))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
