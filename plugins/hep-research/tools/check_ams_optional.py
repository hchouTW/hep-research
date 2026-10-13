#!/usr/bin/env python3
"""AMS optionality check (AC09): copy the plugin to a temporary folder without the AMS-02 profile and
without its registry entry, then run Path B, Path C, the registry validator and the generic test suites
(core, contracts, hep-statistics, hep-computing) there. Exit 0 when all pass; prints a JSON summary.

Each test module runs in its own process, up to --jobs at a time (default 1), slowest first
(tools/module_timings.json); the suite results are the same as one 'unittest discover' per suite.

Usage: python3 tools/check_ams_optional.py [--keep] [--jobs N]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AMS = "experiment:ams-02"


def run(name, cmd, cwd, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "exit_code": None, "status": "fail", "tail": f"timed out after {timeout} s"}
    return {"name": name, "exit_code": p.returncode, "status": "pass" if p.returncode == 0 else "fail",
            "tail": (p.stdout + p.stderr)[-1200:] if p.returncode else ""}


def suite_modules(top: Path, suite: str) -> list[str]:
    return sorted(".".join(p.relative_to(top).with_suffix("").parts) for p in (top / suite).rglob("test_*.py"))


def merge_suite(name: str, rows: list[dict]) -> dict:
    """One result per suite, as 'unittest discover' gave: fail when any of its modules failed."""
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
    tmp = Path(tempfile.mkdtemp(prefix="hep research no ams "))  # a path with spaces on purpose
    dst = tmp / "hep-research"
    ams_dir = None
    reg = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
    for p in reg["profiles"]:
        if p["id"] == AMS:
            ams_dir = (ROOT / "profiles" / p["path"]).resolve()
    shutil.copytree(ROOT, dst, ignore=lambda d, names: [n for n in names if n in ("__pycache__", "output")
                                                           or (ams_dir and (Path(d) / n).resolve() == ams_dir)])
    reg["profiles"] = [p for p in reg["profiles"] if p["id"] != AMS]
    (dst / "profiles" / "registry.json").write_text(json.dumps(reg, indent=1) + "\n", encoding="utf-8")
    py = sys.executable
    out = tmp / "outputs"
    # (name, suite or None, command, cwd): every entry and every test module of a suite is an independent process
    tasks = [
        ("registry", None, [py, "contracts/registry.py"], dst),
        ("path_b", None, [py, "examples/collider-angular/run.py", "--out", str(out / "b")], dst),
        ("path_c", None, [py, "examples/qed-prediction/run.py", "--out", str(out / "c")], dst),
    ]
    suites = {"tests_core": suite_modules(dst, "tests/core"), "tests_contracts": suite_modules(dst, "tests/contracts"),
              "tests_hep_statistics": suite_modules(dst, "tests/skills/hep_statistics"),
              "tests_hep_computing": suite_modules(dst, "tests/skills/hep_computing"),
              "tests_paths_b_c": ["tests.examples.test_collider_angular", "tests.examples.test_qed_prediction"]}
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
    checks += [merge_suite(suite, [r for t, r in zip(tasks, rows) if t[1] == suite]) for suite in suites]
    ok = all(c["status"] == "pass" for c in checks)
    print(json.dumps({"ok": ok, "copy": str(dst), "checks": checks}, indent=1))
    if "--keep" not in args:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
