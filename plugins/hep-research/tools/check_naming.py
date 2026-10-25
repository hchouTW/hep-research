#!/usr/bin/env python3
"""The plugin's own naming gate (semantic naming spec §8.5): the deterministic naming rules on the plugin's Python
code (N1), its CLI flags and environment variables (N5) and its contract vocabulary (N16).

Every surface is extracted in memory by skills/hep-computing/scripts/extract_names.py and judged by
contracts/naming_check.py in gate mode: deterministic rules only, every name reported (not only changed ones), every
violated rule an error and every unverified or unsupported result a failure. Findings that existed when the gate came
in are listed in tools/naming_known_gaps.json, keyed by rule and entity id without its line ("<rule_id>|<surface>:
<file>#<container>/<name>", with a count for a name declared more than once); the file only shrinks. A finding not in
it fails the gate; an entry nothing matches any more is reported as stale (delete it), never an error. A waiver is an
explicit exception, visible in the PR, in the same file's "waivers" list (rule_id, entity_ids, reason, recorded_by).

Usage: python3 tools/check_naming.py [--known-gaps FILE] [--root PLUGIN_ROOT] [--write-known-gaps]
--write-known-gaps rewrites the file from the current findings (only to record the baseline when a rule comes in, or
after fixing gaps; review its diff). Exit 0 no new finding, 1 a new finding, 2 unusable input. Output: one JSON object
with a status key. Standard library only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.naming_check import registries, run_check  # noqa: E402
from core.naming.model import stable_key  # noqa: E402

KNOWN_GAPS = ROOT / "tools" / "naming_known_gaps.json"
GATE_SURFACES = ("N1", "N5", "N16")


def extractor():
    spec = importlib.util.spec_from_file_location("extract_names", ROOT / "skills/hep-computing/scripts/extract_names.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gap_key(f: dict) -> str:
    where = stable_key(f["entity_id"]) if f.get("entity_id") else f"{f['surface']}:<surface>"
    return f"{f['rule_id']}|{where}"


def run(root: Path, known: dict) -> dict:
    x = extractor()
    inventories = [x.EXTRACT[s](root, ["."]) for s in GATE_SURFACES]
    rules, surfaces = registries()
    rep = run_check(inventories, rules=rules, surfaces=surfaces, waivers=known.get("waivers", []), report_all=True,
                    mode="gate", expect=GATE_SURFACES, scope={"gate": list(GATE_SURFACES)})
    rep.pop("_judged")
    allowed = Counter(known.get("gaps", {}))
    seen: Counter = Counter()
    unlisted, applied = [], 0
    for f in rep["findings"]:
        if f["severity"] not in ("error", "unresolved"):
            continue
        k = gap_key(f)
        seen[k] += 1
        if seen[k] <= allowed.get(k, 0):
            applied += 1
        else:
            unlisted.append(f)
    stale = sorted(k for k in allowed if seen.get(k, 0) < allowed[k])
    return {"report": rep, "new": unlisted, "applied": applied, "stale": stale, "seen": seen,
            "entities": {inv["surface"]: len(inv["entities"]) for inv in inventories}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--known-gaps", type=Path, default=KNOWN_GAPS)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--write-known-gaps", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        known = json.loads(args.known_gaps.read_text(encoding="utf-8")) if args.known_gaps.is_file() else {"gaps": {}}
    except ValueError as exc:
        print(json.dumps({"status": "rejected", "error": f"{args.known_gaps}: {exc}"}))
        return 2
    out = run(args.root.resolve(), {} if args.write_known_gaps else known)
    if args.write_known_gaps:
        doc = {"known_gaps_version": "1.0.0",
               "$comment": "Naming findings of the plugin's own code when the gate came in (tools/check_naming.py). "
                           "Only shrinks: delete an entry once its name is fixed; never add one by hand (a new name "
                           "follows the charter, or takes an explicit waiver below).",
               "waivers": known.get("waivers", []), "gaps": dict(sorted(out["seen"].items()))}
        args.known_gaps.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    rep = out["report"]
    status = "pass" if not out["new"] or args.write_known_gaps else "fail"
    by_rule = Counter(f["rule_id"] for f in out["new"])
    print(json.dumps({"status": status, "entities": out["entities"], "counts": rep["naming"]["counts"],
                      "known_gaps_applied": out["applied"], "known_gaps_stale": out["stale"][:50],
                      "stale_count": len(out["stale"]), "new_by_rule": dict(by_rule),
                      "new_findings": [{k: f.get(k) for k in ("rule_id", "location", "current", "state", "message", "action")}
                                       for f in out["new"][:50]],
                      "written": str(args.known_gaps) if args.write_known_gaps else None}, indent=1))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
