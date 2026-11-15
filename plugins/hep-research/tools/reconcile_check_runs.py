#!/usr/bin/env python3
"""Reconcile the check-run records of one CI run: the gate that says the required checks all ran and passed.

Usage: python3 tools/reconcile_check_runs.py RUNS_DIR --python 3.13 --shards N
                                             [--parts static,ams-optional] [--ams-optional-shards M]
                                             [--sha SHA] [--plan FILE] [--summary FILE]

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
With --plan FILE (a pull request's CI plan, tools/ci_plan.py; CI recomputes it here rather than trusting the plan job's
copy) the shards must partition the modules the plan selects, every run must name this plan's digest, a selected part
must have run its checks and an unselected part must have a record that says it was not selected (and ran nothing); the
AMS-optionality check must have run exactly the plan's ams_optional_modules.
With --ams-optional-shards M (M > 1; CI's checks-complete uses 2) the part ams-optional is expected as M records, one per
run_all_checks.py --part ams-optional --shard K/M, instead of one: each must carry its shard plan (the shard, its modules,
the pool they were split from and its digest, the timings digest), run exactly its planned modules, and the shards must
partition one pool, planned from one timing file: no module in two shards or in none, no shard missing. The pool must be
the plan's ams_optional_modules (with --plan) or this tree's AMS-optionality module list (tools/check_ams_optional.py
all_modules). The default, 1, expects the unsharded record, as local runs and other workflows write it.
Exit 0 when everything reconciles, 1 when anything is missing or failed, 2 on bad usage. Prints a JSON report.
"""
from __future__ import annotations

import argparse
import hashlib
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


def _ams_modules() -> list[str]:
    """The test modules the AMS-optionality check reruns in this tree (tools/check_ams_optional.py all_modules)."""
    spec = importlib.util.spec_from_file_location("check_ams_optional", ROOT / "tools" / "check_ams_optional.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.all_modules()


def _digest(modules: list[str]) -> str:
    """run_all_checks.modules_digest: SHA-256 of the sorted list, one name per line."""
    return hashlib.sha256("".join(m + "\n" for m in sorted(modules)).encode()).hexdigest()


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
    elif part == "ams-optional" and doc.get("shard"):
        part = f"ams-optional {doc['shard']}"
    return py, part


def reconcile(runs: list[dict], pythons: list[str], shards: int, parts: list[str], sha: str | None,
              expected_modules: list[str], expected_checks: dict[str, list[str]], plan: dict | None = None,
              ams_shards: int = 1, ams_modules: list[str] | None = None) -> dict:
    """ams_shards: how many records the part ams-optional is split into (1: one unsharded record); ams_modules: the
    module list the AMS-optionality check reruns in this tree, which sharded records must partition (without a plan)."""
    problems: list[str] = []
    selected = sorted(plan["modules"]) if plan else list(expected_modules)
    if plan:
        expected_checks = {p: (names if p in plan["parts"] else []) for p, names in expected_checks.items()}
        for doc in runs:
            sel = doc.get("selection") or {}
            if sel.get("plan_sha256") != plan["plan_sha256"]:
                problems.append(f"{doc['_file']}: not run under this CI plan ({sel.get('plan_sha256')!r})")
            part = doc.get("part")
            if part in parts and bool(sel.get("selected")) != (part in plan["parts"]):
                problems.append(f"{doc['_file']}: part {part} selection {sel.get('selected')!r} disagrees with the plan")
    ams_keys = ["ams-optional"] if ams_shards == 1 else [f"ams-optional {k}/{ams_shards}" for k in range(1, ams_shards + 1)]
    wanted = [(py, f"units {k}/{shards}") for py in pythons for k in range(1, shards + 1)] + \
             [(py, key) for py in pythons for part in parts for key in (ams_keys if part == "ams-optional" else [part])]
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
            uplan = unit["plan"]
            if sorted(uplan.get("all_modules") or []) != sorted(expected_modules):
                lost = sorted(set(expected_modules) - set(uplan.get("all_modules") or []))
                added = sorted(set(uplan.get("all_modules") or []) - set(expected_modules))
                problems.append(f"{doc['_file']}: full module list differs from tests/ (missing {lost}, extra {added})")
            if plan and sorted(plan_mods := uplan.get("selected_modules") or []) != selected:
                problems.append(f"{doc['_file']}: selected modules differ from the CI plan "
                                f"(missing {sorted(set(selected) - set(plan_mods))}, extra {sorted(set(plan_mods) - set(selected))})")
            ran = [r.get("module") for r in unit.get("modules") or []]
            if sorted(ran) != sorted(uplan.get("modules") or []):
                problems.append(f"{doc['_file']}: modules run differ from the plan "
                                f"(not run {sorted(set(uplan['modules']) - set(ran))}, unplanned {sorted(set(ran) - set(uplan['modules']))})")
            unfinished = [r.get("module") for r in unit.get("modules") or [] if r.get("counts") is None]
            if unfinished:
                problems.append(f"{doc['_file']}: modules that did not finish: {unfinished}")
            if not uplan.get("modules") and len(selected) >= shards:
                problems.append(f"{doc['_file']}: empty shard {uplan.get('shard')}")
            for m in uplan.get("modules") or []:
                if m in seen:
                    problems.append(f"Python {py}: module {m} in two shards ({seen[m]}, {uplan.get('shard')})")
                seen[m] = uplan.get("shard")
        plans = [(next((c for c in d.get("checks") or [] if c.get("name") == "unittest"), None) or {}).get("plan") or {}
                 for d in units]
        if len({p.get("timings_sha256") for p in plans}) > 1:
            problems.append(f"Python {py}: shards planned from different module timings (timings_sha256 differ), "
                            "so they cannot partition the modules")
        if units and len(units) == shards:
            lost = sorted(set(selected) - set(seen))
            if lost:
                problems.append(f"Python {py}: modules in no shard: {lost}")
    if "ams-optional" in parts:
        want = sorted(plan.get("ams_optional_modules") or []) if plan else (sorted(ams_modules) if ams_modules is not None else None)
        for py in pythons:
            problems += _reconcile_ams(py, [by_key[(py, k)][0] for k in ams_keys if by_key.get((py, k))], ams_shards,
                                       want, plan is not None)
    return {"ok": not problems, "runs": len(runs), "expected_runs": len(wanted),
            "commit": sorted(str(c) for c in commits)[0] if len(commits) == 1 else None, "problems": problems}


def _reconcile_ams(py: str, docs: list[dict], ams_shards: int, want: list[str] | None, planned: bool) -> list[str]:
    """The AMS-optionality records of one Python version: unsharded, the modules it ran are the plan's (with a plan);
    sharded, the shards partition one pool (want, when known), each ran its planned modules. A record without the
    ams_optional check (an unselected part, or a dropped check, reported elsewhere) is not counted."""
    problems: list[str] = []
    source = "the CI plan" if planned else "this tree's AMS-optionality suites"
    splits: list[tuple[dict, dict]] = []
    for doc in docs:
        ams = next((c for c in doc.get("checks") or [] if c.get("name") == "ams_optional"), None)
        if ams is None:
            continue
        detail = ams.get("detail") if isinstance(ams.get("detail"), dict) else {}
        ran = sorted(detail.get("modules_run") or [])
        if ams_shards == 1:
            if planned and ran != want:
                problems.append(f"{doc['_file']}: AMS-optionality modules differ from the CI plan "
                                f"(not run {sorted(set(want or []) - set(ran))}, unplanned {sorted(set(ran) - set(want or []))})")
            continue
        split = detail.get("shard")
        if not isinstance(split, dict):
            problems.append(f"{doc['_file']}: AMS-optionality shard run without a recorded shard plan")
            continue
        if split.get("shard") != doc.get("shard"):
            problems.append(f"{doc['_file']}: the AMS-optionality record of shard {doc.get('shard')} names shard "
                            f"{split.get('shard')!r}")
        mods = sorted(split.get("modules") or [])
        if ran != mods:
            problems.append(f"{doc['_file']}: AMS-optionality modules run differ from the shard plan "
                            f"(not run {sorted(set(mods) - set(ran))}, unplanned {sorted(set(ran) - set(mods))})")
        if split.get("all_modules_sha256") != _digest(split.get("all_modules") or []):
            problems.append(f"{doc['_file']}: AMS-optionality all_modules_sha256 does not match its module list")
        splits.append((doc, split))
    if ams_shards == 1 or not splits:
        return problems
    if len({_digest(s.get("all_modules") or []) for _, s in splits}) > 1:
        problems.append(f"Python {py}: AMS-optionality shards split different module lists, so they cannot partition it")
    if len({s.get("timings_sha256") for _, s in splits}) > 1:
        problems.append(f"Python {py}: AMS-optionality shards planned from different module timings (timings_sha256 differ)")
    pool = sorted(splits[0][1].get("all_modules") or [])
    if want is not None and pool != want:
        problems.append(f"Python {py}: AMS-optionality module list differs from {source} "
                        f"(missing {sorted(set(want) - set(pool))}, extra {sorted(set(pool) - set(want))})")
    seen: dict[str, str] = {}
    for doc, split in splits:
        if not split.get("modules") and len(pool) >= ams_shards:
            problems.append(f"{doc['_file']}: empty AMS-optionality shard {split.get('shard')}")
        for m in split.get("modules") or []:
            if m in seen:
                problems.append(f"Python {py}: AMS-optionality module {m} in two shards ({seen[m]}, {split.get('shard')})")
            seen[m] = split.get("shard")
    if len(splits) == ams_shards:
        lost = sorted(set(want if want is not None else pool) - set(seen))
        if lost:
            problems.append(f"Python {py}: AMS-optionality modules in no shard: {lost}")
        stray = sorted(set(seen) - set(want if want is not None else pool))
        if stray:
            problems.append(f"Python {py}: AMS-optionality modules outside its module list: {stray}")
    return problems


def markdown(report: dict) -> str:
    head = "### Check-run reconciliation: " + ("all required runs complete and passing" if report["ok"] else "**FAILED**")
    lines = [head, "", f"{report['runs']} of {report['expected_runs']} expected runs found; commit `{report['commit']}`"]
    lines += [f"- {p}" for p in report["problems"]]
    return "\n".join(lines) + "\n\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", type=Path, metavar="RUNS_DIR")
    ap.add_argument("--python", required=True, help="comma-separated Python versions, e.g. 3.13")
    ap.add_argument("--shards", type=int, required=True, help="units shards per Python version")
    ap.add_argument("--parts", default="static,ams-optional", help="other parts expected per Python version")
    ap.add_argument("--ams-optional-shards", type=int, default=1, metavar="M",
                    help="records the part ams-optional is split into (run_all_checks.py --part ams-optional --shard K/M); "
                         "default 1, the unsharded record")
    ap.add_argument("--sha", help="the commit every run must have tested")
    ap.add_argument("--plan", type=Path, metavar="FILE", help="the CI plan the runs must follow (tools/ci_plan.py)")
    ap.add_argument("--summary", type=Path, metavar="FILE", help="append a Markdown report to FILE")
    opts = ap.parse_args(argv)
    if opts.shards < 1 or opts.ams_optional_shards < 1 or not opts.runs.is_dir():
        print("need --shards >= 1, --ams-optional-shards >= 1 and an existing RUNS_DIR", file=sys.stderr)
        return 2
    parts = [p for p in opts.parts.split(",") if p]
    runner = _runner()
    plan = None
    if opts.plan:
        try:
            plan = runner._ci_plan().load_plan(opts.plan)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    runs, unreadable = load_runs(opts.runs)
    report = reconcile(runs, [p for p in opts.python.split(",") if p], opts.shards, parts, opts.sha,
                       runner.test_modules(), {p: runner.planned_check_names(p) for p in parts}, plan,
                       ams_shards=opts.ams_optional_shards,
                       ams_modules=_ams_modules() if opts.ams_optional_shards > 1 and "ams-optional" in parts else None)
    if plan:
        report["plan"] = {k: plan[k] for k in ("plan_sha256", "full", "parts", "reasons")} | {"modules": len(plan["modules"])}
    report["problems"] = unreadable + report["problems"]
    report["ok"] = not report["problems"]
    print(json.dumps(report, indent=1))
    if opts.summary:
        with opts.summary.open("a", encoding="utf-8") as fh:
            fh.write(markdown(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
