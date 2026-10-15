#!/usr/bin/env python3
"""Reconcile the check-run records of one CI run: the gate that says the required checks all ran and passed.

Usage: python3 tools/reconcile_check_runs.py RUNS_DIR --python 3.11,3.12,3.13 --shards N
                                             [--parts static,ams-optional] [--sha SHA] [--summary FILE]

RUNS_DIR holds the check-run-*.json files written by tools/run_all_checks.py --out (any depth, e.g. one folder per
downloaded artifact). For every Python version it expects one units run per shard 1/N..N/N and one run of each
listed part, all of the same commit (and of --sha when given). It fails when:
- a run is missing, duplicated, or of another commit or Python version;
- a run has a failed check, or a check-level skip other than the host CLI checks;
- the units shards do not partition the module list: a module in no shard or in two, shards planned from different
  module timings, shards that disagree on the full module list, a module planned but not run (or run but not planned), or a module that did not finish;
- the full module list or the check names differ from what this tree defines (tests/ and run_all_checks.py), so a
  dropped module or check cannot pass by being absent from every record.
Equal test counts are never taken as evidence: modules and checks are compared by name.
Exit 0 when everything reconciles, 1 when anything is missing or failed, 2 on bad usage. Prints a JSON report.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CHECK_SKIPS = {"claude-plugin-validate", "codex-plugin-load"}  # skipped by --no-cli in CI


def _runner():
    spec = importlib.util.spec_from_file_location("run_all_checks", ROOT / "tools" / "run_all_checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_runs(folder: Path) -> tuple[list[dict], list[str]]:
    runs, problems = [], []
    for path in sorted(folder.rglob("check-run-*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc["_file"] = str(path.relative_to(folder))
            runs.append(doc)
        except (OSError, ValueError) as exc:
            problems.append(f"{path.relative_to(folder)}: unreadable ({exc})")
    return runs, problems


def run_key(doc: dict) -> tuple[str, str]:
    py = ".".join(str((doc.get("environment") or {}).get("python", "?")).split(".")[:2])
    part = doc.get("part") or "?"
    if part == "units":
        unit = next((c for c in doc.get("checks") or [] if c.get("name") == "unittest"), {})
        part = f"units {(unit.get('plan') or {}).get('shard') or doc.get('shard') or '1/1'}"
    return py, part


def reconcile(runs: list[dict], pythons: list[str], shards: int, parts: list[str], sha: str | None,
              expected_modules: list[str], expected_checks: dict[str, list[str]]) -> dict:
    problems: list[str] = []
    wanted = [(py, f"units {k}/{shards}") for py in pythons for k in range(1, shards + 1)] + \
             [(py, part) for py in pythons for part in parts]
    by_key: dict[tuple[str, str], list[dict]] = {}
    for doc in runs:
        by_key.setdefault(run_key(doc), []).append(doc)
    for key in wanted:
        n = len(by_key.get(key, []))
        if n == 0:
            problems.append(f"missing run: Python {key[0]}, {key[1]}")
        elif n > 1:
            problems.append(f"duplicate runs: Python {key[0]}, {key[1]} ({', '.join(d['_file'] for d in by_key[key])})")
    for key in by_key:
        if key not in wanted:
            problems.append(f"unexpected run: Python {key[0]}, {key[1]} ({', '.join(d['_file'] for d in by_key[key])})")
    commits = {d.get("git_commit") for d in runs}
    if len(commits) > 1:
        problems.append(f"runs of different commits: {sorted(str(c) for c in commits)}")
    if sha and commits and commits != {sha}:
        problems.append(f"runs not of the tested commit {sha}: {sorted(str(c) for c in commits)}")
    for doc in runs:
        for c in doc.get("checks") or []:
            if c.get("status") == "fail":
                problems.append(f"{doc['_file']}: check {c.get('name')} failed")
            elif c.get("status") == "skip" and c.get("name") not in ALLOWED_CHECK_SKIPS:
                problems.append(f"{doc['_file']}: check {c.get('name')} skipped ({c.get('reason')}), not a permitted skip")
            elif c.get("status") not in ("pass", "skip", "fail"):
                problems.append(f"{doc['_file']}: check {c.get('name')} has no result ({c.get('status')!r})")
        part = doc.get("part")
        if part in expected_checks:
            got = [c.get("name") for c in doc.get("checks") or []]
            missing = [n for n in expected_checks[part] if n not in got]
            extra = [n for n in got if n not in expected_checks[part]]
            if missing:
                problems.append(f"{doc['_file']}: checks not run: {missing}")
            if extra:
                problems.append(f"{doc['_file']}: checks not planned for part {part}: {extra}")
    for py in pythons:
        units = [d for k in wanted if k[0] == py and k[1].startswith("units") for d in by_key.get(k, [])[:1]]
        seen: dict[str, str] = {}
        for doc in units:
            unit = next((c for c in doc.get("checks") or [] if c.get("name") == "unittest"), None)
            if unit is None or not unit.get("plan"):
                problems.append(f"{doc['_file']}: units run without a recorded plan")
                continue
            plan = unit["plan"]
            if sorted(plan.get("all_modules") or []) != sorted(expected_modules):
                lost = sorted(set(expected_modules) - set(plan.get("all_modules") or []))
                added = sorted(set(plan.get("all_modules") or []) - set(expected_modules))
                problems.append(f"{doc['_file']}: full module list differs from tests/ (missing {lost}, extra {added})")
            ran = [r.get("module") for r in unit.get("modules") or []]
            if sorted(ran) != sorted(plan.get("modules") or []):
                problems.append(f"{doc['_file']}: modules run differ from the plan "
                                f"(not run {sorted(set(plan['modules']) - set(ran))}, unplanned {sorted(set(ran) - set(plan['modules']))})")
            unfinished = [r.get("module") for r in unit.get("modules") or [] if r.get("counts") is None]
            if unfinished:
                problems.append(f"{doc['_file']}: modules that did not finish: {unfinished}")
            if not plan.get("modules") and len(expected_modules) >= shards:
                problems.append(f"{doc['_file']}: empty shard {plan.get('shard')}")
            for m in plan.get("modules") or []:
                if m in seen:
                    problems.append(f"Python {py}: module {m} in two shards ({seen[m]}, {plan.get('shard')})")
                seen[m] = plan.get("shard")
        plans = [(next((c for c in d.get("checks") or [] if c.get("name") == "unittest"), None) or {}).get("plan") or {}
                 for d in units]
        if len({p.get("timings_sha256") for p in plans}) > 1:
            problems.append(f"Python {py}: shards planned from different module timings (timings_sha256 differ), "
                            "so they cannot partition the modules")
        if units and len(units) == shards:
            lost = sorted(set(expected_modules) - set(seen))
            if lost:
                problems.append(f"Python {py}: modules in no shard: {lost}")
    return {"ok": not problems, "runs": len(runs), "expected_runs": len(wanted),
            "commit": sorted(str(c) for c in commits)[0] if len(commits) == 1 else None, "problems": problems}


def markdown(report: dict) -> str:
    head = "### Check-run reconciliation: " + ("all required runs complete and passing" if report["ok"] else "**FAILED**")
    lines = [head, "", f"{report['runs']} of {report['expected_runs']} expected runs found; commit `{report['commit']}`"]
    lines += [f"- {p}" for p in report["problems"]]
    return "\n".join(lines) + "\n\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", type=Path, metavar="RUNS_DIR")
    ap.add_argument("--python", required=True, help="comma-separated Python versions, e.g. 3.11,3.12,3.13")
    ap.add_argument("--shards", type=int, required=True, help="units shards per Python version")
    ap.add_argument("--parts", default="static,ams-optional", help="other parts expected per Python version")
    ap.add_argument("--sha", help="the commit every run must have tested")
    ap.add_argument("--summary", type=Path, metavar="FILE", help="append a Markdown report to FILE")
    opts = ap.parse_args(argv)
    if opts.shards < 1 or not opts.runs.is_dir():
        print("need --shards >= 1 and an existing RUNS_DIR", file=sys.stderr)
        return 2
    parts = [p for p in opts.parts.split(",") if p]
    runner = _runner()
    runs, unreadable = load_runs(opts.runs)
    report = reconcile(runs, [p for p in opts.python.split(",") if p], opts.shards, parts, opts.sha,
                       runner.test_modules(), {p: runner.planned_check_names(p) for p in parts})
    report["problems"] = unreadable + report["problems"]
    report["ok"] = not report["problems"]
    print(json.dumps(report, indent=1))
    if opts.summary:
        with opts.summary.open("a", encoding="utf-8") as fh:
            fh.write(markdown(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
