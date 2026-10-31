#!/usr/bin/env python3
"""The plugin's own naming gate (semantic naming spec §8.5): the deterministic naming rules on the plugin's Python
code (N1), its CLI flags and environment variables (N5) and its contract vocabulary (N16).

Every surface is extracted in memory by skills/hep-computing/scripts/extract_names.py and judged by
contracts/naming_check.py in gate mode: deterministic rules only, every name reported (not only changed ones), every
violated rule an error and every unverified or unsupported result a failure. Findings that existed when the gate came
in are listed in tools/naming_known_gaps.json, keyed by rule and entity id without its line ("<rule_id>|<surface>:
<file>#<container>/<name>", with a count for a name declared more than once); the file only shrinks. A finding not in
it fails the gate (an unverified or unsupported result is never baselined); an entry nothing matches any more is
reported as stale (delete it), never an error. A waiver is an
explicit exception, visible in the PR, in the same file's "waivers" list (rule_id, entity_ids, reason, recorded_by).

Usage: python3 tools/check_naming.py [--known-gaps FILE] [--root PLUGIN_ROOT] [--write-known-gaps] [--base REV]
--write-known-gaps rewrites the file from the current findings (only to record the baseline when a rule comes in, or
after fixing gaps; review its diff). The baseline only shrinks: an entry that grew since --base (default
origin/main) for a rule the base registry already had fails the gate; a rule new since then may bring entries. Without
the base revision (a shallow clone) the comparison is skipped and baseline_note says so. Exit 0 no new finding, 1 a
new finding or a grown baseline, 2 unusable input. Output: one JSON object with a status key. Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[1])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

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
        if f["severity"] == "unresolved":
            unlisted.append(f)  # unverified and unsupported results are never baselined: they always fail (§8.5)
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


def baseline_growth(root: Path, known_gaps: Path, gaps: dict, base: str) -> tuple[list[str], str | None]:
    """Keys of the baseline that grew since the base revision for a rule the base registry already had (a rule that
    is new may bring its own entries). (grown keys, note): the note says why nothing could be compared."""
    import subprocess

    def show(path: Path):
        try:
            top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True,
                                 text=True, timeout=60).stdout.strip()
            relp = path.resolve().relative_to(Path(top).resolve()).as_posix()
            p = subprocess.run(["git", "-C", str(root), "show", f"{base}:{relp}"], capture_output=True, text=True,
                               timeout=60)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None
        return json.loads(p.stdout) if p.returncode == 0 else None
    old_gaps, old_rules = show(known_gaps), show(root / "contracts" / "naming" / "rules.json")
    if old_gaps is None or old_rules is None:
        return [], f"baseline not compared: {base} or its files are not available (a shallow clone)"
    known_rules = {r["rule_id"] for r in old_rules.get("rules", [])}
    grown = sorted(k for k, n in gaps.items() if n > old_gaps.get("gaps", {}).get(k, 0) and k.split("|", 1)[0] in known_rules)
    return grown, None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--known-gaps", type=Path, default=KNOWN_GAPS)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--write-known-gaps", action="store_true")
    ap.add_argument("--base", default="origin/main",
                    help="git revision the baseline may only shrink against (default origin/main; skipped when absent)")
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
    grown, base_note = ([], None) if args.write_known_gaps else baseline_growth(
        args.root.resolve(), args.known_gaps, known.get("gaps", {}), args.base)
    status = "pass" if (not out["new"] and not grown) or args.write_known_gaps else "fail"
    by_rule = Counter(f["rule_id"] for f in out["new"])
    print(json.dumps({"status": status, "entities": out["entities"], "counts": rep["naming"]["counts"],
                      "known_gaps_applied": out["applied"], "known_gaps_stale": out["stale"][:50],
                      "stale_count": len(out["stale"]), "new_by_rule": dict(by_rule),
                      "new_findings": [{k: f.get(k) for k in ("rule_id", "location", "current", "state", "message", "action")}
                                       for f in out["new"][:50]],
                      "baseline_grown": grown[:50], "baseline_note": base_note,
                      "written": str(args.known_gaps) if args.write_known_gaps else None}, indent=1))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
