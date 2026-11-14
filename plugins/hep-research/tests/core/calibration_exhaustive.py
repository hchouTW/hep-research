#!/usr/bin/env python3
"""Exhaustive Appendix C checks of core/calibration/use against the reference decision table (simulator calibration
phase 0 gate; simcal-tasks/phase-0.md, "Thresholds and test designs").

The scope of Appendix C is 31.6 million (own inputs, upstreams) cases: a full pass takes about two core-hours, the
mutant check about two per mutant, so the gate runs are split into shards (batch work, section 14.1) and the unit
suite (test_calibration_use.py) runs a fixed strided slice of the same functions. A shard k of n takes the cases with
index i, i mod n == k - 1, of the reference's own cases() order.

Checks (--check):
  agree       calib_use's assign, effective, allowed_uses, variation_upstream_admissible and derive_role equal the
              reference's on every case of the shard (outcome or rejection);
  invariants  the reference's check() with calib_use's functions in place of its own, on the shard: no violation;
  mutants     the reference's 24 mutants (its mutation_check list) each run on the shard with the reference
              functions; status ok only when every one is caught (a violation on a subset is a violation of the scope);
  lookup      the "outcome already determined" lookup against an independent enumeration, and mutant 25 (C.2 only),
              on the shard of the lookup scope.
Output: one JSON object with status ok (exit 0), failed (exit 1: a disagreement or violation; for mutants, never: a
mutant not caught in one shard is reported, not failed), or rejected (exit 2: bad arguments or the reference's hash).
Standard library only.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import itertools
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))


REFERENCE_SHA256 = "c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3"


def shard(iterable, k: int, n: int):
    return itertools.islice(iterable, k - 1, None, n)


def run_agree(ref, use, deps, k, n):
    from test_calibration_use import outcome
    bad, count = [], 0
    for c, ups in shard(ref.cases(), k, n):
        count += 1
        pairs = [("assign", outcome(use.assign, c), outcome(ref.assign, c)),
                 ("effective", outcome(use.effective, c, ups), outcome(ref.effective, c, ups))]
        eff = pairs[1][2]
        if eff[0] == "ok":
            pairs.append(("allowed_uses", use.allowed_uses(*eff[1]), ref.allowed_uses(*eff[1])))
        pairs.append(("inherited_flags", outcome(use.inherited_flags, c, ups), outcome(ref.inherited_flags, c, ups)))
        for u in ups:
            pairs.append(("variation_upstream_admissible", use.variation_upstream_admissible(u),
                          ref.variation_upstream_admissible(u)))
            pairs.append(("derive_role", deps.derive_role(u["usages"]), ref.derive_role(u["usages"])))
        for name, a, b in pairs:
            if a != b and len(bad) < 20:
                bad.append({"function": name, "case": repr(c), "upstreams": repr(ups), "calib_use": repr(a),
                            "reference": repr(b)})
    return {"cases": count, "disagreements": bad}, not bad


def _with_shard(ref, k, n, fn):
    orig = ref.cases
    ref.cases = lambda: shard(orig(), k, n)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            res = fn()
        return res, out.getvalue()
    finally:
        ref.cases = orig


def run_invariants(ref, use, deps, k, n):
    names = ("assign", "effective", "allowed_uses", "variation_upstream_admissible", "derive_role", "inherited_flags")
    saved = {x: getattr(ref, x) for x in names}
    try:
        ref.assign, ref.effective, ref.allowed_uses = use.assign, use.effective, use.allowed_uses
        ref.variation_upstream_admissible, ref.derive_role = use.variation_upstream_admissible, deps.derive_role
        ref.inherited_flags = use.inherited_flags
        errors, printed = _with_shard(ref, k, n, ref.check)
    finally:
        for x, v in saved.items():
            setattr(ref, x, v)
    return {"printed": printed.strip(), "violations": errors[:20]}, not errors


def run_mutants(ref, use, deps, k, n):
    argv = sys.argv
    sys.argv = argv[:1]            # the reference reads its own --part=k/n (a mutant subset) from sys.argv
    try:
        _, printed = _with_shard(ref, k, n, ref.mutation_check)
    finally:
        sys.argv = argv
    caught = {}
    for line in printed.splitlines():
        if line.startswith("mutant "):
            name, verdict = line[len("mutant "):].rsplit(": ", 1)
            caught[name] = verdict == "caught"
    # a mutant caught on a subset of the scope is caught by the scope (each case is judged on its own)
    return {"mutants": caught, "not_caught": sorted(m for m, c in caught.items() if not c)}, \
        len(caught) == REFERENCE_MUTANTS and all(caught.values())


def run_lookup(ref, use, deps, k, n):
    from test_calibration_use import independent_lookup, lookup_scope
    bad, count, c2_caught = [], 0, 0
    for c, ups, und in shard(lookup_scope(), k, n):
        count += 1
        got = use.outcome_determined(c, ups, und)
        det, seen = independent_lookup(c, ups, und)
        if (got["determined"], {(g, frozenset(u)) for g, u in got["outcomes"]}) != (det, seen) and len(bad) < 20:
            bad.append({"case": repr(c), "upstreams": repr(ups), "undecided": list(und)})
        if ups and independent_lookup(c, ups, und, c2_only=True)[0] != got["determined"]:
            c2_caught += 1
    return {"cases": count, "disagreements": bad, "mutant_c2_only_caught_in": c2_caught}, not bad


REFERENCE_MUTANTS = 24          # the reference's mutation_check list (Appendix C mutants 1-24)
SCOPE_CASES = 31593216          # Appendix C scope: 197376 x 141 + 192 x 19600 (reference cases())
LOOKUP_CASES = 2754048          # lookup scope of test_calibration_use.lookup_scope()
CODE_FILES = ("tests/core/calibration_exhaustive.py", "tests/core/test_calibration_use.py", "core/calibration/use.py",
              "core/calibration/deps.py", "docs/dev/simulator-calibration/reference/calib_use_decision_table.py")


def provenance() -> dict:
    """The commit (from a COMMIT file beside the plugin folder of a snapshot, else git) and the SHA-256 of the files
    that decide the result, recorded in every item (review F10)."""
    import hashlib
    import subprocess
    commit_file = ROOT.parent.parent / "COMMIT"
    if commit_file.is_file():
        commit = commit_file.read_text().strip()
    else:
        try:
            commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                                    timeout=30).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            commit = None
    return {"commit": commit, "files": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}}


CHECKS = {"agree": run_agree, "invariants": run_invariants, "mutants": run_mutants, "lookup": run_lookup}
# The registered gate campaign (simcal-tasks/phase-0.md, test design): item i of the campaign -> (check, k, n).
GATE_SHARDS = ([("agree", k, 32) for k in range(1, 33)] + [("invariants", k, 32) for k in range(1, 33)]
               + [("lookup", k, 4) for k in range(1, 5)] + [("mutants", 1, 2000)])


def _items(folder: Path):
    """Item results: item-<i>.json files, or the batch runner's outputs (<chunk>/<attempt>.json with the worker's JSON
    under "result"); metadata files are skipped."""
    files = sorted(folder.glob("item-*.json")) or sorted(f for f in folder.glob("*/*.json")
                                                         if not f.name.endswith(".meta.json"))
    for f in files:
        d = json.loads(f.read_text())
        yield f, d.get("result", d)


def summarize(folder: Path) -> dict:
    """Gate verdict (simcal-tasks/phase-0.md, test design): every registered shard present exactly once and ok, the
    reference's hash and the same code in every item, the full case counts, all reference mutants caught, and
    mutant 25 (lookup with C.2 only) caught at least once."""
    seen, bad, cases, prov, c2 = {}, [], {}, set(), 0
    mutants_ok = False
    for f, d in _items(folder):
        key = (d.get("check"), d.get("part"))
        seen[key] = seen.get(key, 0) + 1
        if d.get("status") != "ok" or d.get("reference_sha256") != REFERENCE_SHA256:
            bad.append({"file": f.name, "status": d.get("status")})
        cases[d.get("check")] = cases.get(d.get("check"), 0) + int(d.get("cases", 0))
        prov.add(json.dumps(d.get("provenance"), sort_keys=True))
        c2 += int(d.get("mutant_c2_only_caught_in", 0))
        if d.get("check") == "mutants" and d.get("status") == "ok":
            mutants_ok = True
    want = {(c, f"{k}/{n}") for c, k, n in GATE_SHARDS}
    missing = sorted(f"{c} {p}" for c, p in want - set(seen))
    dup = sorted(f"{c} {p}" for (c, p), m in seen.items() if m > 1)
    problems = []
    if len(prov) > 1:
        problems.append("items ran different code (provenance differs)")
    if not missing and cases.get("agree") != SCOPE_CASES:
        problems.append(f"agree covered {cases.get('agree')} cases, not {SCOPE_CASES}")
    if not missing and cases.get("lookup") != LOOKUP_CASES:
        problems.append(f"lookup covered {cases.get('lookup')} cases, not {LOOKUP_CASES}")
    if not missing and c2 == 0:
        problems.append("mutant 25 (lookup with C.2 only) was never caught")
    if not missing and not mutants_ok:
        problems.append("not every reference mutant was caught")
    status = "failed" if (bad or problems) else "incomplete" if (missing or dup) else "ok"
    return {"status": status, "shards_expected": len(want), "shards_found": len(seen), "missing": missing,
            "duplicates": dup, "not_ok": bad, "problems": problems, "cases": cases, "mutant_c2_only_caught_in": c2,
            "provenance": json.loads(next(iter(prov))) if len(prov) == 1 else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", choices=sorted(CHECKS))
    ap.add_argument("--part", default="1/1", help="shard k/n (1-based), default 1/1 (the full scope)")
    ap.add_argument("--item", type=int, help=f"run item i (0-based) of the registered gate campaign "
                    f"({len(GATE_SHARDS)} items) instead of --check/--part")
    ap.add_argument("--out", help="also write the JSON result to this file (its folder must exist)")
    ap.add_argument("--summarize", metavar="DIR", help="gate verdict from the item-<i>.json files in DIR")
    args = ap.parse_args(argv)
    if args.summarize:
        out = summarize(Path(args.summarize))
        print(json.dumps(out, indent=1))
        return {"ok": 0, "failed": 1}.get(out["status"], 3)
    if args.item is not None:
        if not 0 <= args.item < len(GATE_SHARDS):
            print(json.dumps({"status": "rejected", "error": f"--item must be 0..{len(GATE_SHARDS) - 1}"}))
            return 2
        c, k, n = GATE_SHARDS[args.item]
        args.check, args.part = c, f"{k}/{n}"
    if not args.check:
        print(json.dumps({"status": "rejected", "error": "give --check, --item or --summarize"}))
        return 2
    try:
        k, n = (int(x) for x in args.part.split("/"))
        if not 1 <= k <= n:
            raise ValueError
    except ValueError:
        print(json.dumps({"status": "rejected", "error": f"--part must be k/n with 1 <= k <= n, not {args.part!r}"}))
        return 2
    try:
        from test_calibration_use import REF  # loads the reference after checking its SHA-256
    except AssertionError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    from core.calibration import deps, use
    t0 = time.time()
    detail, ok = CHECKS[args.check](REF, use, deps, k, n)
    out = {"status": "ok" if ok else "failed", "check": args.check, "part": f"{k}/{n}",
           "reference_sha256": REFERENCE_SHA256, "provenance": provenance(),
           "seconds": round(time.time() - t0, 1), **detail}
    if args.item is not None:
        out["item"] = args.item
    text = json.dumps(out, indent=1)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
