#!/usr/bin/env python3
"""Aggregate runner: every check in one JSON summary, with pass / fail / skip kept separate.

Usage: python3 tools/run_all_checks.py [--out DIR] [--no-cli] [--module-timeout S] [--jobs N]
                                       [--part all|units|checks|static|ams-optional] [--shard K/N]
                                       [--plan FILE] [--write-timings FILE] [--summary FILE]
Writes DIR/check-run-<UTC timestamp>.json when --out is given; always prints the summary.
Exit 0 when nothing failed (skips are reported, not hidden), 1 otherwise.
Each test module runs in its own process with a timeout (default 600 s, or HEP_MODULE_TIMEOUT): a module that
does not finish is a failure with its reason, never a hang, and every module's duration is in the JSON output.
Each check script has the same timeout; one that does not finish fails with its reason and the other checks still run.
Test modules start slowest first (tools/module_timings.json). --part and --shard split the work across CI runners:
'units' runs the test modules (all of them, or shard K of N, balanced by the recorded timings), 'checks' runs the
profile suites and the static and host checks; every module belongs to exactly one shard. 'checks' is 'static' (profile
suites, static and host checks) plus 'ams-optional' (tools/check_ams_optional.py, the generic suites in a copy without
the AMS-02 profile), so CI can run the two in parallel jobs.
Every check records its seconds; a units run records its plan (the full module list with its digest and the modules
of this shard), which tools/reconcile_check_runs.py checks across shards. --extra NAME (with --part units) runs only
the modules tools/optional_modules.json lists for an optional extra: the CI optional jobs on pull requests; pushes to
main and the weekly run keep the full suite, and tools/optional_selection.py verify checks the list against them.
--plan FILE (a pull request's CI plan, tools/ci_plan.py): units shards split only the modules the plan selects, and a
part the plan does not select runs nothing but still writes its record (selection.selected false), so the gate can tell
a skipped part from a lost one; every record names the plan's digest. Failed test ids and traceback tails are
printed, and written as Markdown to --summary FILE (CI passes $GITHUB_STEP_SUMMARY).
Passing checks shows software consistency only, not physical validity or statistical coverage.
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

import argparse
import hashlib
import json
import platform
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULE_TIMEOUT = float(os.environ.get("HEP_MODULE_TIMEOUT", "600"))  # seconds per test module or check
# check_ams_optional.py reruns the generic suites in a copy of the tree: about 190 s locally, 7-10 min on CI runners
AMS_OPTIONAL_TIMEOUT = 1200.0
TIMINGS = ROOT / "tools" / "module_timings.json"
OPTIONAL_MODULES = ROOT / "tools" / "optional_modules.json"
SLOW_MODULE_SECONDS = 60.0  # a fast-tier module above this belongs in the slow tier (HEP_SLOW_TESTS=1)


MODULE_RUNNER = """
import io, json, sys, unittest
suite = unittest.TestLoader().loadTestsFromName(sys.argv[1])
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
print(json.dumps({"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
                  "failed": [str(t) for t, _ in res.failures + res.errors], "skipped_list": [f"{t}: {r}" for t, r in res.skipped],
                  "messages": {str(t): tb[-800:] for t, tb in res.failures + res.errors}}))
"""


DEFAULT_JOBS = min(8, os.cpu_count() or 1)


def test_modules() -> list[str]:
    return sorted(".".join(p.relative_to(ROOT).with_suffix("").parts) for p in (ROOT / "tests").rglob("test_*.py"))


def load_timings(path: Path = TIMINGS) -> dict[str, float]:
    try:
        return {k: float(v) for k, v in json.loads(path.read_text(encoding="utf-8"))["seconds"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def expected_seconds(modules: list[str], timings: dict[str, float]) -> dict[str, float]:
    """Recorded seconds per module; a module without a record gets the median, so a new module is neither first nor
    last by accident."""
    known = sorted(timings.values())
    default = known[len(known) // 2] if known else 1.0
    return {m: timings.get(m, default) for m in modules}


def slowest_first(modules: list[str], timings: dict[str, float]) -> list[str]:
    est = expected_seconds(modules, timings)
    return sorted(modules, key=lambda m: (-est[m], m))


def shard_modules(modules: list[str], k: int, n: int, timings: dict[str, float]) -> list[str]:
    """Shard k (1-based) of n: modules placed slowest first, each on the shard with the least expected time so far
    (ties to the lowest shard), so the shards finish together and every module is in exactly one shard."""
    if not 1 <= k <= n:
        raise ValueError(f"shard {k}/{n}: need 1 <= K <= N")
    est = expected_seconds(modules, timings)
    load = [0.0] * n
    parts: list[list[str]] = [[] for _ in range(n)]
    for m in slowest_first(modules, timings):
        i = min(range(n), key=lambda j: (load[j], j))
        parts[i].append(m)
        load[i] += est[m]
    return parts[k - 1]


def modules_digest(modules: list[str]) -> str:
    """SHA-256 of the sorted module list, one name per line: every shard of one revision must report the same."""
    return hashlib.sha256("".join(m + "\n" for m in sorted(modules)).encode()).hexdigest()


def parse_shard(text: str) -> tuple[int, int]:
    try:
        k, n = (int(x) for x in text.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"--shard wants K/N, got {text!r}") from None
    if not 1 <= k <= n:
        raise argparse.ArgumentTypeError(f"--shard {text}: need 1 <= K <= N")
    return k, n


def run_module(module: str, timeout: float) -> dict:
    start = time.monotonic()
    try:
        p = subprocess.run([sys.executable, "-c", MODULE_RUNNER, module], capture_output=True, text=True, cwd=str(ROOT),
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"module": module, "status": "fail", "seconds": round(time.monotonic() - start, 2),
                "reason": f"timed out after {timeout:g} s", "counts": None, "failed": [module], "skipped": []}
    seconds = round(time.monotonic() - start, 2)
    try:
        r = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"module": module, "status": "fail", "seconds": seconds, "reason": "the module did not load or crashed",
                "counts": None, "failed": [module], "skipped": [], "stderr": p.stderr[-1500:]}
    counts = {k: r[k] for k in ("run", "failures", "errors", "skipped")}
    ok = not r["failures"] and not r["errors"]
    return {"module": module, "status": "pass" if ok else "fail", "seconds": seconds, "counts": counts,
            "failed": r["failed"], "skipped": r["skipped_list"], "messages": r.get("messages") or {}}


def extra_modules(extra: str, every: list[str], path: Path | None = None) -> list[str]:
    """The test modules listed for an optional extra in tools/optional_modules.json (written by
    tools/optional_selection.py generate). An unknown extra, or a listed module that no longer exists, is refused."""
    doc = json.loads((path or OPTIONAL_MODULES).read_text(encoding="utf-8"))
    listed = doc.get("extras", {}).get(extra)
    if not listed:
        raise ValueError(f"--extra {extra}: not in {OPTIONAL_MODULES.name} (known: {sorted(doc.get('extras', {}))})")
    gone = sorted(set(listed) - set(every))
    if gone:
        raise ValueError(f"--extra {extra}: listed modules no longer exist: {gone} (regenerate with optional_selection.py)")
    return sorted(listed)


def run_unittests(timeout: float = MODULE_TIMEOUT, jobs: int = 1, shard: tuple[int, int] | None = None,
                  extra: str | None = None, selected: list[str] | None = None) -> dict:
    """selected: the modules a CI plan selects (tools/ci_plan.py); the shards split these instead of every module."""
    timings = load_timings()
    every = test_modules()
    pool = every if selected is None else sorted(set(selected) & set(every))
    if extra:
        modules = extra_modules(extra, every)
    else:
        modules = shard_modules(pool, *shard, timings) if shard else list(pool)
    plan = {"all_modules": every, "all_modules_sha256": modules_digest(every), "modules": sorted(modules),
            "shard": f"{shard[0]}/{shard[1]}" if shard else "1/1", "extra": extra,
            "timings_sha256": hashlib.sha256(json.dumps(timings, sort_keys=True).encode()).hexdigest()}
    if selected is not None:
        plan["selected_modules"] = pool
    modules = slowest_first(modules, timings)  # a long module started last would hold up the whole run
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        rows = list(pool.map(lambda m: run_module(m, timeout), modules))
    seconds = round(time.monotonic() - start, 2)
    total = {k: sum((r["counts"] or {}).get(k, 0) for r in rows) for k in ("run", "failures", "errors", "skipped")}
    total["passed"] = total["run"] - total["failures"] - total["errors"] - total["skipped"]
    broken = [r for r in rows if r["counts"] is None]
    slow = sorted((r for r in rows if r["seconds"] > SLOW_MODULE_SECONDS), key=lambda r: -r["seconds"])
    return {"name": "unittest", "command": "python3 -m unittest <module>, one process per module under tests/",
            "status": "pass" if all(r["status"] == "pass" for r in rows) else "fail", "seconds": seconds,
            "counts": dict(total, modules=len(rows), modules_failed_to_finish=len(broken)),
            "module_timeout_seconds": timeout, "shard": f"{shard[0]}/{shard[1]}" if shard else None,
            "failed": [f for r in rows for f in r["failed"]] + [f"{r['module']}: {r['reason']}" for r in broken],
            "skipped": [s for r in rows for s in r["skipped"]],
            "messages": {t: m for r in rows for t, m in (r.get("messages") or {}).items()},  # traceback tails of failures
            "slow_modules": [{"module": r["module"], "seconds": r["seconds"]} for r in slow], "plan": plan,
            "modules": [{k: r.get(k) for k in ("module", "status", "seconds", "counts", "reason")} for r in rows]}


PROFILE_RUNNER = """
import io, json, sys, unittest
suite = unittest.TestLoader().discover("tests", top_level_dir="tests")
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
print(json.dumps({"status": "pass" if res.wasSuccessful() else "fail",
  "counts": {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
             "passed": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)},
  "failed": [str(t) for t, _ in res.failures + res.errors], "skipped": [f"{t}: {r}" for t, r in res.skipped],
  "messages": {str(t): tb[-800:] for t, tb in res.failures + res.errors}}))
sys.exit(0 if res.wasSuccessful() else 1)  # run_script reads the exit code; without this a failing suite counted as pass
"""


def run_profile_tests() -> list[dict]:
    """Each registered profile's own tests, one subprocess per profile so test module names cannot collide."""
    reg = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
    out = []
    for prof in reg["profiles"]:
        pdir = ROOT / "profiles" / prof["path"]
        if not (pdir / "tests").is_dir():
            out.append({"name": f"profile-tests:{prof['id']}", "status": "skip", "reason": "no tests folder"})
            continue
        r = run_script(f"profile-tests:{prof['id']}", [sys.executable, "-c", PROFILE_RUNNER], cwd=pdir)
        r["command"] = f"(cd profiles/{prof['path']} && python3 -m unittest discover -s tests -t tests)"
        r["counts"] = (r.get("detail") or {}).get("counts")
        out.append(r)
    return out


def timed_out(name: str, cmd: list[str], exc: subprocess.TimeoutExpired) -> dict:
    """A check that does not finish is a failure with its reason; it must not abort the remaining checks."""
    return {"name": name, "command": " ".join(cmd), "exit_code": None, "status": "fail",
            "reason": f"timed out after {exc.timeout:g} s"}


def run_script(name: str, cmd: list[str], cwd: Path = ROOT, timeout: float = MODULE_TIMEOUT) -> dict:
    start = time.monotonic()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return dict(timed_out(name, cmd, exc), seconds=round(time.monotonic() - start, 2))
    try:
        detail = json.loads(p.stdout)
    except ValueError:
        detail = {"stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    status = "pass" if p.returncode == 0 else ("skip" if isinstance(detail, dict) and detail.get("status") == "skip" else "fail")
    return {"name": name, "command": " ".join(cmd), "exit_code": p.returncode, "status": status, "detail": detail,
            "seconds": round(time.monotonic() - start, 2), **({"reason": detail.get("reason")} if status == "skip" else {})}


def host_validate() -> dict:
    exe = shutil.which("claude")
    if not exe:
        return {"name": "claude-plugin-validate", "status": "skip", "reason": "claude CLI not found"}
    cmd = [exe, "plugin", "validate", str(ROOT), "--strict"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=MODULE_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        return timed_out("claude-plugin-validate", cmd, exc)
    return {"name": "claude-plugin-validate", "command": "claude plugin validate <plugin> --strict", "exit_code": p.returncode,
            "status": "pass" if p.returncode == 0 else "fail", "detail": p.stdout.strip()[-1500:]}


def codex_load() -> dict:
    """Codex has no `plugin validate`: install this plugin from the repository's own marketplace into a throwaway
    CODEX_HOME (no login, no network) and require Codex to list it as installed at the manifest version."""
    exe = shutil.which("codex")
    if not exe:
        return {"name": "codex-plugin-load", "status": "skip", "reason": "codex CLI not found"}
    repo = ROOT.parents[1]
    if not (repo / ".agents" / "plugins" / "marketplace.json").is_file():
        return {"name": "codex-plugin-load", "status": "skip", "reason": "no repository marketplace (relocated copy)"}
    version = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
    market = json.loads((repo / ".agents" / "plugins" / "marketplace.json").read_text())["name"]
    with tempfile.TemporaryDirectory(prefix="codex-home-") as home:
        env = dict(os.environ, CODEX_HOME=home)
        steps = [[exe, "plugin", "marketplace", "add", str(repo)], [exe, "plugin", "add", f"hep-research@{market}"],
                 [exe, "plugin", "list"]]
        for cmd in steps:
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=120)
            except subprocess.TimeoutExpired as exc:
                return timed_out("codex-plugin-load", cmd, exc)
            if p.returncode:
                return {"name": "codex-plugin-load", "command": " ".join(cmd[1:]), "exit_code": p.returncode, "status": "fail",
                        "detail": (p.stdout + p.stderr)[-1500:]}
        row = next((l for l in p.stdout.splitlines() if l.startswith(f"hep-research@{market}")), "")
        ok = "installed" in row and version in row.split()
    return {"name": "codex-plugin-load", "command": "codex plugin marketplace add <repo>; plugin add; plugin list (temp CODEX_HOME)",
            "exit_code": 0 if ok else 1, "status": "pass" if ok else "fail", "detail": row.strip()}


def git_commit() -> str:
    """HEAD of the plugin's checkout, or "unknown" when git is absent, hangs or fails: the summary is still written."""
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT),
                           timeout=MODULE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else "unknown"


def host_versions() -> dict:
    out = {}
    for host in ("claude", "codex"):
        exe = shutil.which(host)
        try:
            out[host] = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=MODULE_TIMEOUT).stdout.strip() if exe else "not installed"
        except subprocess.TimeoutExpired:
            out[host] = "no answer to --version"
    return out


STATIC_SCRIPTS = [  # (name, command after the interpreter): the static checks of --part static, in run order
    ("check_layering", ["tools/check_layering.py"]),
    ("stanza_consistency", ["tools/build_stanzas.py", "--check"]),
    ("registry", ["contracts/registry.py"]),
    ("routing_static", ["tools/check_routing_static.py"]),
    ("ownership", ["tools/check_ownership.py"]),
    ("retired_names", ["tools/check_retired_names.py"]),
    ("reference_inventory", ["tools/reference_inventory.py", "--check"]),
    ("wiring", ["tools/check_wiring.py"]),
    ("packaging_scan", ["tools/check_packaging.py"]),
    ("host_neutral", ["tools/check_host_neutral.py"]),
    ("instruction_text", ["tools/check_instruction_text.py"]),
    ("host_manifests", ["tools/check_host_manifests.py"]),
    ("measure_entrypoints", ["tools/measure_entrypoints.py"]),
    ("rule_registry", ["contracts/rule_registry.py", "check"]),
    ("naming_registry", ["contracts/naming_registry.py", "check"]),
    ("naming", ["tools/check_naming.py"]),
]
HOST_CHECKS = ["claude-plugin-validate", "codex-plugin-load"]


def _ci_plan():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_plan", ROOT / "tools" / "ci_plan.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def planned_scripts(part: str, py: str, jobs: int, no_cli: bool, plan: Path | None = None) -> list[tuple[str, list[str]]]:
    """The check scripts a run of this part executes, in order (profile suites and host checks are added by main). With
    a CI plan, the AMS-optionality check runs only the modules the plan selects for it."""
    out = []
    if part in ("all", "checks", "ams-optional"):
        out.append(("ams_optional", [py, "tools/check_ams_optional.py", "--jobs", str(jobs)]
                    + (["--plan", str(plan.resolve())] if plan else [])))
    if part in ("all", "checks", "static"):
        for name, args in STATIC_SCRIPTS:
            out.append((name, [py, *args] + (["--no-cli"] if name == "measure_entrypoints" and no_cli else [])))
    return out


def planned_check_names(part: str) -> list[str]:
    """Every check name a run of this part must report (besides 'unittest' for units): what
    tools/reconcile_check_runs.py expects, computed from this tree rather than taken from the run."""
    names = [name for name, _ in planned_scripts(part, "python", 1, True)]
    if part in ("all", "checks", "static"):
        reg = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
        names = [f"profile-tests:{p['id']}" for p in reg["profiles"]] + names + HOST_CHECKS
    return names


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 epilog="Passing checks shows software consistency only, not physical validity or statistical coverage.")
    ap.add_argument("--out", metavar="DIR", type=Path, help="write DIR/check-run-<UTC timestamp>.json")
    ap.add_argument("--no-cli", action="store_true", help="skip the host CLI checks (claude plugin validate, codex plugin load)")
    ap.add_argument("--module-timeout", type=float, default=MODULE_TIMEOUT, metavar="S",
                    help="seconds allowed per test module and per check script (default 600 or HEP_MODULE_TIMEOUT)")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, metavar="N",
                    help=f"test modules run in parallel (default {DEFAULT_JOBS}: CPU count, at most 8; 1 runs them serially)")
    ap.add_argument("--part", choices=("all", "units", "checks", "static", "ams-optional"), default="all",
                    help="units: the test modules only; checks: static plus ams-optional; static: profile suites, static and "
                         "host checks; ams-optional: tools/check_ams_optional.py only (default all)")
    ap.add_argument("--shard", type=parse_shard, metavar="K/N",
                    help="run only shard K of N of the test modules, balanced by tools/module_timings.json")
    ap.add_argument("--extra", metavar="NAME",
                    help="run only the test modules listed for this optional extra in tools/optional_modules.json (the "
                         "modules with tests that run only when the extra is installed); with --part units")
    ap.add_argument("--plan", type=Path, metavar="FILE",
                    help="a CI plan (tools/ci_plan.py): run only what it selects; unselected parts write an empty record")
    ap.add_argument("--summary", type=Path, metavar="FILE",
                    help="append a Markdown summary (status and seconds per check, failed tests with traceback tails, "
                         "slowest modules) to FILE, e.g. $GITHUB_STEP_SUMMARY")
    ap.add_argument("--write-timings", type=Path, metavar="FILE",
                    help="also write the measured seconds per test module to FILE (the format of tools/module_timings.json)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    opts = parse_args(argv)
    if opts.shard and opts.part not in ("all", "units"):
        print(f"--shard applies to the test modules; it cannot be combined with --part {opts.part}", file=sys.stderr)
        return 2
    if opts.extra and (opts.part != "units" or opts.shard):
        print("--extra selects test modules: use it with --part units and without --shard", file=sys.stderr)
        return 2
    py = sys.executable
    t = opts.module_timeout
    ci_plan, selection = None, None
    if opts.plan:
        if opts.part not in ("units", "static", "ams-optional") or opts.extra:
            print("--plan applies to --part units, static or ams-optional, without --extra", file=sys.stderr)
            return 2
        try:
            ci_plan = _ci_plan().load_plan(opts.plan)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        chosen = opts.part == "units" or opts.part in ci_plan["parts"]
        selection = {"plan_sha256": ci_plan["plan_sha256"], "full": ci_plan["full"], "selected": chosen}
    try:
        units = [run_unittests(opts.module_timeout, opts.jobs, opts.shard, opts.extra,
                               ci_plan["modules"] if ci_plan else None)] if opts.part in ("all", "units") else []
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    run_part = selection is None or selection["selected"]
    static = opts.part in ("all", "checks", "static") and run_part
    checks = units + (run_profile_tests() if static else [])
    for name, cmd in planned_scripts(opts.part, py, opts.jobs, opts.no_cli, opts.plan) if run_part else []:
        checks.append(run_script(name, cmd, timeout=max(t, AMS_OPTIONAL_TIMEOUT) if name == "ams_optional" else t))
    if static:
        checks += [host_validate() if not opts.no_cli else {"name": "claude-plugin-validate", "status": "skip", "reason": "--no-cli"},
                   codex_load() if not opts.no_cli else {"name": "codex-plugin-load", "status": "skip", "reason": "--no-cli"}]
    if opts.write_timings and units:
        old = json.loads(TIMINGS.read_text(encoding="utf-8")) if TIMINGS.is_file() else {}
        record = {"note": old.get("note", ""),
                  "source": f"run_all_checks.py --jobs {opts.jobs} on {platform.platform()}, Python {platform.python_version()}",
                  "seconds": {r["module"]: r["seconds"] for r in sorted(units[0]["modules"], key=lambda r: r["module"])}}
        opts.write_timings.parent.mkdir(parents=True, exist_ok=True)
        opts.write_timings.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plugin_version": json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "executable": py,
                        "hosts": host_versions()},
        "git_commit": git_commit(),
        "ci": {k: os.environ[v] for k, v in (("run_id", "GITHUB_RUN_ID"), ("run_attempt", "GITHUB_RUN_ATTEMPT"),
                                              ("sha", "GITHUB_SHA"), ("job", "GITHUB_JOB")) if os.environ.get(v)},
        "part": opts.part,
        "shard": f"{opts.shard[0]}/{opts.shard[1]}" if opts.shard else None,
        "extra": opts.extra,
        "selection": selection,
        "counts": {s: sum(1 for c in checks if c["status"] == s) for s in ("pass", "fail", "skip")},
        "checks": checks,
        "caveat": "Software checks only; not physical validity, proof, statistical coverage, or authorization to unblind.",
    }
    text = json.dumps(summary, indent=1)
    if opts.out:
        out = opts.out
        out.mkdir(parents=True, exist_ok=True)
        (out / f"check-run-{summary['timestamp_utc'].replace(':', '')}.json").write_text(text + "\n")
    print(json.dumps({"counts": summary["counts"], "checks": [{k: c.get(k) for k in ("name", "status", "seconds", "counts", "exit_code", "reason")} for c in checks]}, indent=1))
    report = failure_report(checks)
    if report:
        print(report, file=sys.stderr)
    if opts.summary:
        with opts.summary.open("a", encoding="utf-8") as fh:
            fh.write(markdown_summary(summary, report))
    return 0 if summary["counts"]["fail"] == 0 else 1


def failure_details(check: dict) -> list[tuple[str, str]]:
    """(failed item, traceback or output tail) for one failing check: test ids with their traceback tails for the
    unit tests, the failed tests of a profile suite, else the check's reason or output tail."""
    if check.get("status") != "fail":
        return []
    detail = check.get("detail") if isinstance(check.get("detail"), dict) else {}
    messages = check.get("messages") or detail.get("messages") or {}
    failed = check.get("failed") or detail.get("failed") or []
    nested = [c for c in detail.get("checks") or [] if isinstance(c, dict) and c.get("status") == "fail"]
    if not failed and nested:  # check_ams_optional: one row per failing suite or entry, with its output tail
        return [(c.get("name", "?"), str(c.get("tail") or c.get("reason") or "")) for c in nested]
    if failed:
        return [(f, messages.get(f, "")) for f in failed]
    tail = check.get("reason") or detail.get("stderr") or detail.get("stdout") or json.dumps(detail)[-800:]
    return [(check["name"], str(tail)[-800:])]


def failure_report(checks: list[dict]) -> str:
    lines = []
    for c in checks:
        for item, tail in failure_details(c):
            lines.append(f"FAILED [{c['name']}] {item}")
            lines += [f"    {line}" for line in tail.strip().splitlines()[-12:]]
    return "\n".join(lines)


def markdown_summary(summary: dict, report: str) -> str:
    def cell(text) -> str:
        return str(text).replace("|", "\\|")
    head = f"### run_all_checks: part {summary['part']}" + (f", shard {summary['shard']}" if summary.get("shard") else "")
    rows = ["| check | status | seconds | tests run / failed / skipped |", "|---|---|---|---|"]
    for c in summary["checks"]:
        n = c.get("counts") or {}
        tests = f"{n.get('run', '')} / {n.get('failures', 0) + n.get('errors', 0) if n else ''} / {n.get('skipped', '')}" if n else ""
        rows.append(f"| {cell(c['name'])} | {c['status']} | {c.get('seconds', '')} | {tests} |")
    out = [head, "", f"commit `{summary['git_commit']}`, Python {summary['environment']['python']}; "
           f"pass {summary['counts']['pass']}, fail {summary['counts']['fail']}, skip {summary['counts']['skip']}", "", *rows]
    unit = next((c for c in summary["checks"] if c["name"] == "unittest"), None)
    if unit:
        slow = sorted(unit.get("modules") or [], key=lambda r: -(r.get("seconds") or 0))[:10]
        out += ["", "Slowest test modules: " + ", ".join(f"`{r['module']}` {r['seconds']} s" for r in slow)]
    if report:
        out += ["", "<details open><summary>Failures</summary>", "", "```", report, "```", "", "</details>"]
    return "\n".join(out) + "\n\n"


if __name__ == "__main__":
    sys.exit(main())
