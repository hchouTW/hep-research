#!/usr/bin/env python3
"""AMS optionality check (AC09): copy the plugin to a temporary folder without the AMS-02 profile and
without its registry entry, then run Path B, Path C, the registry validator and the generic test suites
(core, contracts, hep-statistics, hep-computing) there. Exit 0 when all pass; prints a JSON summary.

Each test module runs in its own process, up to --jobs at a time (default 1), slowest first
(tools/module_timings.json); the suite results are the same as one 'unittest discover' per suite.

With --plan FILE (a pull request's CI plan, tools/ci_plan.py) only the suite modules the plan lists under
ams_optional_modules run, as the units shards run only the plan's modules; a suite with none selected is reported as
skipped. The registry validator, Path B and Path C and the two profile suites (a few seconds) always run. The output
names the modules that ran (modules_run), which the gate compares with the plan.

With --shard K/N only shard K of N of those modules runs, split by the planner of the units shards (tools/run_all_checks.py
shard_modules: slowest first by tools/module_timings.json, each module on the least loaded shard; deterministic), so CI
can run the rerun on N runners. The output records the shard (shard: the shard, its modules, the pool they were split
from with its SHA-256, and the timings digest), which tools/reconcile_check_runs.py --ams-optional-shards N checks
across shards: every module in exactly one shard. A suite with no module in this shard is reported as skipped. The fixed
steps (the AMS-02 profile absent, the registry validator, Path B and Path C, the two profile suites; a few seconds) run
in every shard, so each shard's copy is checked on its own and every shard reports the same check names. Without
--shard the whole rerun runs, as before.

Usage: python3 tools/check_ams_optional.py [--keep] [--jobs N] [--plan FILE] [--shard K/N]
"""
from __future__ import annotations

import sys

# The supported floor (pyproject.toml requires-python). This guard and everything above it must stay parseable and
# runnable by old Pythons (tests/tools/test_python_compat.py parses this file as Python 3.9), so an unsupported
# interpreter gets one clear message and exit 2 instead of version-dependent failures.
MIN_PYTHON = (3, 13)


def require_supported_python(version_info=sys.version_info) -> None:
    if tuple(version_info[:2]) < MIN_PYTHON:
        need, got = "%d.%d" % MIN_PYTHON, "%d.%d" % tuple(version_info[:2])
        print(f"Python {need} or newer is required (running {got})", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    require_supported_python()

import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AMS = "experiment:ams-02"
# the generic suites rerun without the AMS-02 profile: a folder under tests/, or an explicit list of modules
SUITES = {"tests_core": "tests/core", "tests_contracts": "tests/contracts",
          "tests_hep_statistics": "tests/skills/hep_statistics", "tests_hep_computing": "tests/skills/hep_computing",
          "tests_paths_b_c": ["tests.examples.test_collider_angular", "tests.examples.test_qed_prediction"]}


def run(name, cmd, cwd, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "exit_code": None, "status": "fail", "tail": f"timed out after {timeout} s"}
    return {"name": name, "exit_code": p.returncode, "status": "pass" if p.returncode == 0 else "fail",
            "tail": (p.stdout + p.stderr)[-1200:] if p.returncode else ""}


def suite_modules(top: Path, suite: str) -> list[str]:
    return sorted(".".join(p.relative_to(top).with_suffix("").parts) for p in (top / suite).rglob("test_*.py"))


def suite_table(top: Path = ROOT) -> dict[str, list[str]]:
    """Suite name -> its test modules in the tree at top."""
    return {name: (list(src) if isinstance(src, list) else suite_modules(top, src)) for name, src in SUITES.items()}


def all_modules(top: Path = ROOT) -> list[str]:
    """Every test module this check reruns (what tools/ci_plan.py intersects a plan's modules with)."""
    return sorted({m for mods in suite_table(top).values() for m in mods})


def load_selection(path: Path) -> tuple[dict, list[str]]:
    """The plan at path (digest checked by tools/ci_plan.py) and the suite modules it selects for this check."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_plan", ROOT / "tools" / "ci_plan.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    plan = mod.load_plan(path)
    return plan, list(plan["ams_optional_modules"])


def _runner():
    """tools/run_all_checks.py, for the shard planner the units shards use."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_all_checks", ROOT / "tools" / "run_all_checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_shard(text: str) -> tuple[int, int]:
    """K/N with 1 <= K <= N; ValueError otherwise."""
    k, n = (int(x) for x in text.split("/"))
    if not 1 <= k <= n:
        raise ValueError(f"need 1 <= K <= N, got {text}")
    return k, n


def shard_plan(pool: list[str], shard: tuple[int, int], timings: dict[str, float]) -> dict:
    """Shard K of N of the modules in pool, by the units' planner (run_all_checks.shard_modules), with what the gate needs
    to check that the shards partition pool: the pool and its digest, and the digest of the timings it was planned from."""
    import hashlib
    runner = _runner()
    pool = sorted(set(pool))
    return {"shard": f"{shard[0]}/{shard[1]}", "modules": sorted(runner.shard_modules(pool, *shard, timings)),
            "all_modules": pool, "all_modules_sha256": runner.modules_digest(pool),
            "timings_sha256": hashlib.sha256(json.dumps(timings, sort_keys=True).encode()).hexdigest()}


def merge_suite(name: str, rows: list[dict], selected: bool = True, in_shard: bool = True, shard: str = "") -> dict:
    """One result per suite, as 'unittest discover' gave: fail when any of its modules failed (or it has none). A suite
    the CI plan selects no module of is skipped (selected False), and so is one whose modules are all in other shards
    (in_shard False)."""
    if not selected:
        return {"name": name, "exit_code": 0, "status": "skip", "modules": 0, "reason": "no module selected by the CI plan"}
    if not in_shard:
        return {"name": name, "exit_code": 0, "status": "skip", "modules": 0,
                "reason": f"no module of this suite in shard {shard}"}
    bad = [r for r in rows if r["status"] != "pass"]
    return {"name": name, "exit_code": max((r["exit_code"] or 1 for r in bad), default=0),
            "status": "fail" if bad or not rows else "pass", "modules": len(rows),
            "tail": "\n".join(f"{r['name']}: {r['tail']}" for r in bad)[-1200:]}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    jobs = 1
    if "--jobs" in args:
        i = args.index("--jobs")
        try:
            jobs = max(1, int(args[i + 1]))
        except (IndexError, ValueError):
            print("--jobs wants a positive integer", file=sys.stderr)
            return 2
    plan, chosen = None, None
    if "--plan" in args:
        i = args.index("--plan")
        try:
            plan, chosen = load_selection(Path(args[i + 1]))
        except (IndexError, OSError, ValueError, KeyError) as exc:
            print(f"--plan wants a CI plan file: {exc}", file=sys.stderr)
            return 2
    shard = None
    if "--shard" in args:
        i = args.index("--shard")
        try:
            shard = parse_shard(args[i + 1])
        except (IndexError, ValueError) as exc:
            print(f"--shard wants K/N with 1 <= K <= N: {exc}", file=sys.stderr)
            return 2
    tmp = Path(tempfile.mkdtemp(prefix="hep research no ams "))  # a path with spaces on purpose
    dst = tmp / "hep-research"
    reg = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
    # the AMS-02 profile goes, and with it every profile that depends on it (reference:geometry-cases cites its claims)
    gone = {AMS}
    for p in reg["profiles"]:
        if p["id"] != AMS and AMS in json.loads((ROOT / "profiles" / p["path"] / "profile.json").read_text(encoding="utf-8")).get("depends_on", []):
            gone.add(p["id"])
    dirs = {(ROOT / "profiles" / p["path"]).resolve() for p in reg["profiles"] if p["id"] in gone}
    shutil.copytree(ROOT, dst, ignore=lambda d, names: [n for n in names if n in ("__pycache__", "output")
                                                           or (Path(d) / n).resolve() in dirs])
    reg["profiles"] = [p for p in reg["profiles"] if p["id"] not in gone]
    (dst / "profiles" / "registry.json").write_text(json.dumps(reg, indent=1) + "\n", encoding="utf-8")
    py = sys.executable
    out = tmp / "outputs"
    # (name, suite or None, command, cwd): every entry and every test module of a suite is an independent process
    tasks = [
        ("registry", None, [py, "contracts/registry.py"], dst),
        ("path_b", None, [py, "examples/collider-angular/run.py", "--out", str(out / "b")], dst),
        ("path_c", None, [py, "examples/qed-prediction/run.py", "--out", str(out / "c")], dst),
    ]
    suites = suite_table(dst)
    if chosen is not None:
        suites = {suite: [m for m in modules if m in set(chosen)] for suite, modules in suites.items()}
    planned = suites  # before sharding: what all shards together run
    split = None
    if shard:
        split = shard_plan([m for mods in suites.values() for m in mods], shard, _runner().load_timings())
        mine = set(split["modules"])
        suites = {suite: [m for m in modules if m in mine] for suite, modules in suites.items()}
    for suite, modules in suites.items():
        tasks += [(m, suite, [py, "-m", "unittest", m], dst) for m in modules]
    for prof in ("experiments/synthetic-collider", "theory/qed-benchmark"):
        tasks.append((f"profile-tests:{prof}", None, [py, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"],
                      dst / "profiles" / prof))
    try:
        timings = json.loads((ROOT / "tools" / "module_timings.json").read_text(encoding="utf-8"))["seconds"]
    except (OSError, ValueError, KeyError):
        timings = {}
    tasks.sort(key=lambda t: -float(timings.get(t[0], 0.0)))  # slowest first; unrecorded tasks keep their order
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        rows = list(pool.map(lambda t: run(t[0], t[2], t[3]), tasks))
    checks = [{"name": "ams_profile_absent", "status": "pass" if not (dst / "profiles" / "experiments" / "ams-02").exists()
               and AMS not in (dst / "profiles" / "registry.json").read_text() else "fail"}]
    checks += [r for t, r in zip(tasks, rows) if t[1] is None]
    checks += [merge_suite(suite, [r for t, r in zip(tasks, rows) if t[1] == suite], chosen is None or bool(planned[suite]),
                           not split or bool(suites[suite]) or not planned[suite], split["shard"] if split else "")
               for suite in suites]
    ok = all(c["status"] in ("pass", "skip") for c in checks)
    selection = {"plan_sha256": plan["plan_sha256"], "full": plan["full"]} if plan else None
    report = {"ok": ok, "copy": str(dst), "selection": selection,
              "modules_run": sorted(t[0] for t in tasks if t[1] is not None), "checks": checks}
    if split:
        report["shard"] = split
    print(json.dumps(report, indent=1))
    if "--keep" not in args:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
