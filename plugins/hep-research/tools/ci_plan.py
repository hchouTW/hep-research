#!/usr/bin/env python3
"""CI plan: which test modules and check parts a pull request runs, from the files it changes.

Usage: python3 tools/ci_plan.py plan (--base SHA [--head REF] | --paths PATH ... | --full REASON) [--out FILE]
       python3 tools/ci_plan.py selects PLAN --part units|static|ams-optional [--shard K/N]

plan: the changed files are `git diff --name-only BASE HEAD` (repository paths; HEAD defaults to the checkout, on a
pull request the merge commit, so the diff is the pull request applied to its base). They go through the impact map of
contracts/rules/registry.json (contracts/rule_registry.py impact), which names the test modules and parts a change to
each path must run. The plan is the full run, all modules and both parts, when:
- a changed path is outside plugins/hep-research/ (the workflows, root evals/, other repository files);
- a changed path is CI tooling (FULL_PATTERNS: this file, the runner, the reconciler, module timings, the lock);
- the impact map asks for it (a path no group covers, a group marked full, a check not available yet);
- the diff cannot be read, or nothing changed (the change cannot be bounded);
- --full is given (pushes to main, the weekly and manual runs).
Otherwise the plan lists the impact map's test modules (a deleted test module is dropped, and recorded) and its parts,
plus, for a changed test helper (a .py file under tests/ that is not a test module), every test module that imports it
by name; a helper no test module imports is the full run (its users cannot be bounded).
The AMS-optionality check is selected like the units: ams_optional_modules lists the selected modules that are in its
suites (tools/check_ams_optional.py all_modules), and the part ams-optional is selected when that list is not empty;
it runs only those modules. When the impact map names the part (part:ams-optional), or the plan is full, it lists
every module of those suites.
Skipping is never silent: tools/run_all_checks.py --plan writes a record for every part, selected or not, and
tools/reconcile_check_runs.py --plan recomputes the plan and fails when a run used another one.
The plan carries plan_sha256 over its content, so runs and the gate can name the plan they used.

selects: prints true or false: whether the plan gives this job anything to run (CI skips installing the pinned set
for a job with nothing selected; the job still writes its record).

Exit 0, 2 on bad usage or an unreadable plan. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PLUGIN = PurePosixPath("plugins/hep-research")
PLAN_VERSION = "1.1.0"  # 1.1.0: ams_optional_modules
PARTS = ("static", "ams-optional")
# CI tooling: a change to how checks are selected, run or reconciled runs everything
FULL_PATTERNS = ("tools/ci_plan.py", "tools/run_all_checks.py", "tools/reconcile_check_runs.py", "tools/check_ams_optional.py",
                 "tools/module_timings.json", "tools/optional_modules.json", "tools/optional_selection.py",
                 "requirements-ci.lock", "pyproject.toml", "tests/tools/test_ci_plan.py")


def _runner():
    spec = importlib.util.spec_from_file_location("run_all_checks", ROOT / "tools" / "run_all_checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ams_modules() -> list[str]:
    """The test modules the AMS-optionality check reruns (tools/check_ams_optional.py)."""
    spec = importlib.util.spec_from_file_location("check_ams_optional", ROOT / "tools" / "check_ams_optional.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.all_modules(ROOT)


def digest(plan: dict) -> str:
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _finish(plan: dict) -> dict:
    plan["plan_sha256"] = digest(plan)
    return plan


def full_plan(reasons: list[str], changed: list[str] | None = None, modules: list[str] | None = None) -> dict:
    every = modules if modules is not None else _runner().test_modules()
    return _finish({"plan_version": PLAN_VERSION, "full": True, "reasons": list(reasons), "changed": sorted(changed or []),
                    "modules": sorted(every), "parts": list(PARTS), "ams_optional_modules": ams_modules(), "dropped": []})


def helper_importers(rel: str, every: list[str], root: Path = ROOT) -> list[str]:
    """Test modules whose source imports the test helper at rel (by its module name, e.g. design_fixtures)."""
    name = PurePosixPath(rel).stem
    pattern = re.compile(rf"^\s*(?:import|from)\s+(?:[\w.]*\.)?{re.escape(name)}\b", re.M)
    out = []
    for m in every:
        try:
            if pattern.search((root / Path(*m.split("."))).with_suffix(".py").read_text(encoding="utf-8")):
                out.append(m)
        except OSError:
            continue
    return sorted(out)


def _is_helper(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.parts[:1] == ("tests",) and p.suffix == ".py" and not p.name.startswith("test_") and p.name != "__init__.py"


def plan_for(changed: list[str], every: list[str], registry: dict, root: Path = ROOT) -> dict:
    """The plan for these changed repository paths, given the tree's test modules and the impact map."""
    from contracts.rule_registry import impact
    if not changed:
        return full_plan(["no changed path: the change cannot be bounded"], changed, every)
    outside = [p for p in changed if not PurePosixPath(p).is_relative_to(PLUGIN)]
    if outside:
        return full_plan([f"outside the plugin: {p}" for p in outside], changed, every)
    rel = [str(PurePosixPath(p).relative_to(PLUGIN)) for p in changed]
    tooling = [p for p in rel if p in FULL_PATTERNS]
    if tooling:
        return full_plan([f"CI tooling changed: {p}" for p in tooling], changed, every)
    imp = impact(rel, registry)
    if imp["full"]:
        return full_plan(imp.get("reasons") or ["the impact map asks for the full run"], changed, every)
    users: set[str] = set()
    for h in (p for p in rel if _is_helper(p)):
        found = helper_importers(h, every, root)
        if not found:
            return full_plan([f"test helper {h}: no test module imports it by name, so its users cannot be bounded"],
                             changed, every)
        users |= set(found)
    known = set(every)
    modules = sorted(m for m in set(imp["modules"]) | users if m in known)
    suites = ams_modules()
    ams = suites if "ams-optional" in imp["parts"] else sorted(set(modules) & set(suites))
    parts = [p for p in PARTS if p in imp["parts"] or (p == "ams-optional" and ams)]
    return _finish({"plan_version": PLAN_VERSION, "full": False, "reasons": [f"impact groups: {imp['groups']}"],
                    "changed": sorted(changed), "modules": modules, "parts": parts, "ams_optional_modules": ams,
                    "dropped": sorted(set(imp["modules"]) - known)})


def changed_paths(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", base, head], cwd=REPO, capture_output=True, text=True, check=True,
                         timeout=60)
    return [line for line in out.stdout.splitlines() if line.strip()]


def load_plan(path: Path) -> dict:
    """A plan file whose digest matches its content; ValueError otherwise."""
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or plan.get("plan_version") != PLAN_VERSION or plan.get("plan_sha256") != digest(plan):
        raise ValueError(f"{path}: not a CI plan {PLAN_VERSION}, or its plan_sha256 does not match its content")
    return plan


def selects(plan: dict, part: str, shard: tuple[int, int] | None = None) -> bool:
    if part == "units":
        if not shard:
            return bool(plan["modules"])
        runner = _runner()
        return bool(runner.shard_modules(plan["modules"], shard[0], shard[1], runner.load_timings()))
    return part in plan["parts"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="write the plan")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--base", help="the pull request's base commit")
    src.add_argument("--paths", nargs="+", help="changed repository paths (instead of a git diff)")
    src.add_argument("--full", metavar="REASON", help="the full run, for this reason")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--out", type=Path, metavar="FILE")
    s = sub.add_parser("selects", help="print whether a plan selects anything for this job")
    s.add_argument("plan", type=Path)
    s.add_argument("--part", required=True, choices=("units",) + PARTS)
    s.add_argument("--shard", metavar="K/N")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    if args.cmd == "selects":
        try:
            plan = load_plan(args.plan)
            shard = tuple(int(x) for x in args.shard.split("/")) if args.shard else None
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print("true" if selects(plan, args.part, shard) else "false")  # type: ignore[arg-type]
        return 0
    every = _runner().test_modules()
    if args.full:
        plan = full_plan([args.full], [], every)
    else:
        try:
            changed = args.paths if args.paths else changed_paths(args.base, args.head)
            registry = json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text(encoding="utf-8"))
            plan = plan_for(changed, every, registry)
        except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            plan = full_plan([f"the change could not be read: {exc}"], [], every)
    text = json.dumps(plan, indent=1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
