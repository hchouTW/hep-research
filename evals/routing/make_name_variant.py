#!/usr/bin/env python3
"""Make a scratch copy of the plugin with the two halves of the communication split renamed (plan 10.2, G14).

The live routing eval compares candidate names (for example hep-sources / hep-manuscript) with the working names
hep-citations / hep-authoring. This script copies the plugin to --out, renames the two skill folders and their test
folders, rewrites every maintained text file (SKILL.md names and descriptions, references, the routing table and
cases, the skill-name contract, docs, profiles, fixtures), runs the static routing check on the copy, and writes the
ids of the cases that involve either skill to <out>/name-variant-ids.txt. The repository is never modified; history
files (CHANGELOG.md, VALIDATION.md, release-manifests/) are copied unchanged.

Usage: python3 evals/routing/make_name_variant.py --literature hep-sources --writing hep-manuscript --out DIR
                                                  [--plugin PLUGIN_ROOT]
Then:  python3 evals/routing/run_routing_eval.py run --model M --plugin-dir DIR --cases DIR/tests/routing/cases.json \\
           --ids "$(cat DIR/name-variant-ids.txt)" --budget-usd 5
Exit codes: 0 copy made and its static routing check passes; 1 the check fails on the copy; 2 bad input.
Output: one JSON object with status. Standard library only; no model calls.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins" / "hep-research"
OLD = ("hep-citations", "hep-authoring")
NAME_RE = re.compile(r"^hep-[a-z]+$")
HISTORY = ("CHANGELOG.md", "VALIDATION.md", "release-manifests/")
TEXT = {".md", ".py", ".json", ".txt", ".toml", ".tex", ".sh", ".bib", ".yml", ".yaml", ".csv", ".cfg"}


def rename_text(text: str, mapping: dict) -> str:
    for old, new in mapping.items():
        text = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", new, text)
        text = re.sub(rf"(?<![\w]){re.escape(old.replace('-', '_'))}(?![\w])", new.replace("-", "_"), text)
    return text


def involved_ids(cases: list, names: set) -> list[str]:
    """Ids of the cases whose expected skill, 'not', chain, turns or also_accept names one of the skills."""
    out = []
    for c in cases:
        named = {c.get("expected_primary"), c.get("not")} | set(c.get("chain") or []) | set(c.get("also_accept") or [])
        named |= {t.get("expected") for t in c.get("turns") or []}
        if named & names:
            out.append(c["id"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--literature", required=True, help="new name of hep-citations")
    ap.add_argument("--writing", required=True, help="new name of hep-authoring")
    ap.add_argument("--out", type=Path, required=True, help="new folder for the copy (must not exist)")
    ap.add_argument("--plugin", type=Path, default=PLUGIN)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def fail(msg: str) -> int:
        print(json.dumps({"status": "error", "error": msg}, indent=1))
        return 2
    lit, wr = args.literature, args.writing
    existing = {p.parent.name for p in (args.plugin / "skills").glob("*/SKILL.md")}
    if not all((args.plugin / "skills" / o / "SKILL.md").is_file() for o in OLD):
        return fail(f"{args.plugin} has no {OLD[0]} and {OLD[1]} skills")
    for n in (lit, wr):
        if not NAME_RE.match(n):
            return fail(f"{n!r} is not a skill name (hep-<lowercase letters>)")
        if n in existing - set(OLD):
            return fail(f"{n!r} is already a skill of the plugin")
    if lit == wr:
        return fail("the two names must differ")
    if args.out.exists():
        return fail(f"--out {args.out} exists; give a new folder")
    mapping = {OLD[0]: lit, OLD[1]: wr}
    shutil.copytree(args.plugin, args.out, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    changed = 0
    for p in sorted(args.out.rglob("*")):
        rel = p.relative_to(args.out).as_posix()
        if not p.is_file() or p.suffix not in TEXT or rel.startswith(HISTORY):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = rename_text(text, mapping)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed += 1
    for parent, fmt in (("skills", "{}"), ("tests/skills", "{}")):
        for old, new in mapping.items():
            src = args.out / parent / (fmt.format(old) if parent == "skills" else old.replace("-", "_"))
            if src.exists():
                src.rename(args.out / parent / (new if parent == "skills" else new.replace("-", "_")))
    check = subprocess.run([sys.executable, str(args.out / "tools" / "check_routing_static.py")],
                           capture_output=True, text=True, timeout=600)
    try:
        static = json.loads(check.stdout)
    except ValueError:
        static = {"ok": False, "raw": (check.stdout + check.stderr)[-2000:]}
    cases = json.loads((args.out / "tests" / "routing" / "cases.json").read_text(encoding="utf-8"))["cases"]
    ids = involved_ids(cases, {lit, wr})
    (args.out / "name-variant-ids.txt").write_text(",".join(ids) + "\n", encoding="utf-8")
    ok = bool(static.get("ok"))
    print(json.dumps({"status": "ok" if ok else "static-check-failed", "out": str(args.out), "names": mapping,
                      "files_rewritten": changed, "cases_involving_the_skills": len(ids),
                      "ids_file": str(args.out / "name-variant-ids.txt"),
                      "static_check": {k: static.get(k) for k in ("ok", "cases", "failed", "coverage_errors", "topic_errors")}},
                     indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
