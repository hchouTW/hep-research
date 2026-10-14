#!/usr/bin/env python3
"""Aggregate runner: every check in one JSON summary, with pass / fail / skip kept separate.

Usage: python3 tools/run_all_checks.py [--out DIR] [--no-cli] [--module-timeout S] [--jobs N]
                                       [--part all|units|checks] [--shard K/N] [--write-timings FILE]
Writes DIR/check-run-<UTC timestamp>.json when --out is given; always prints the summary.
Exit 0 when nothing failed (skips are reported, not hidden), 1 otherwise.
Each test module runs in its own process with a timeout (default 600 s, or HEP_MODULE_TIMEOUT): a module that
does not finish is a failure with its reason, never a hang, and every module's duration is in the JSON output.
Each check script has the same timeout; one that does not finish fails with its reason and the other checks still run.
Test modules start slowest first (tools/module_timings.json). --part and --shard split the work across CI runners:
'units' runs the test modules (all of them, or shard K of N, balanced by the recorded timings), 'checks' runs the
profile suites and the static and host checks; every module belongs to exactly one shard.
Passing checks shows software consistency only, not physical validity or statistical coverage.
"""
from __future__ import annotations

import argparse
import json
import platform
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULE_TIMEOUT = float(os.environ.get("HEP_MODULE_TIMEOUT", "600"))  # seconds per test module or check
TIMINGS = ROOT / "tools" / "module_timings.json"
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


def run_unittests(timeout: float = MODULE_TIMEOUT, jobs: int = 1, shard: tuple[int, int] | None = None) -> dict:
    timings = load_timings()
    modules = test_modules()
    if shard:
        modules = shard_modules(modules, *shard, timings)
    modules = slowest_first(modules, timings)  # a long module started last would hold up the whole run
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        rows = list(pool.map(lambda m: run_module(m, timeout), modules))
    total = {k: sum((r["counts"] or {}).get(k, 0) for r in rows) for k in ("run", "failures", "errors", "skipped")}
    total["passed"] = total["run"] - total["failures"] - total["errors"] - total["skipped"]
    broken = [r for r in rows if r["counts"] is None]
    slow = sorted((r for r in rows if r["seconds"] > SLOW_MODULE_SECONDS), key=lambda r: -r["seconds"])
    return {"name": "unittest", "command": "python3 -m unittest <module>, one process per module under tests/",
            "status": "pass" if all(r["status"] == "pass" for r in rows) else "fail",
            "counts": dict(total, modules=len(rows), modules_failed_to_finish=len(broken)),
            "module_timeout_seconds": timeout, "shard": f"{shard[0]}/{shard[1]}" if shard else None,
            "failed": [f for r in rows for f in r["failed"]] + [f"{r['module']}: {r['reason']}" for r in broken],
            "skipped": [s for r in rows for s in r["skipped"]],
            "messages": {t: m for r in rows for t, m in (r.get("messages") or {}).items()},  # traceback tails of failures
            "slow_modules": [{"module": r["module"], "seconds": r["seconds"]} for r in slow],
            "modules": [{k: r.get(k) for k in ("module", "status", "seconds", "counts", "reason")} for r in rows]}


PROFILE_RUNNER = """
import io, json, sys, unittest
suite = unittest.TestLoader().discover("tests", top_level_dir="tests")
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
print(json.dumps({"status": "pass" if res.wasSuccessful() else "fail",
  "counts": {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
             "passed": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)},
  "failed": [str(t) for t, _ in res.failures + res.errors], "skipped": [f"{t}: {r}" for t, r in res.skipped]}))
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
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return timed_out(name, cmd, exc)
    try:
        detail = json.loads(p.stdout)
    except ValueError:
        detail = {"stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    status = "pass" if p.returncode == 0 else ("skip" if isinstance(detail, dict) and detail.get("status") == "skip" else "fail")
    return {"name": name, "command": " ".join(cmd), "exit_code": p.returncode, "status": status, "detail": detail,
            **({"reason": detail.get("reason")} if status == "skip" else {})}


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


def host_versions() -> dict:
    out = {}
    for host in ("claude", "codex"):
        exe = shutil.which(host)
        try:
            out[host] = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=MODULE_TIMEOUT).stdout.strip() if exe else "not installed"
        except subprocess.TimeoutExpired:
            out[host] = "no answer to --version"
    return out


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 epilog="Passing checks shows software consistency only, not physical validity or statistical coverage.")
    ap.add_argument("--out", metavar="DIR", type=Path, help="write DIR/check-run-<UTC timestamp>.json")
    ap.add_argument("--no-cli", action="store_true", help="skip the host CLI checks (claude plugin validate, codex plugin load)")
    ap.add_argument("--module-timeout", type=float, default=MODULE_TIMEOUT, metavar="S",
                    help="seconds allowed per test module and per check script (default 600 or HEP_MODULE_TIMEOUT)")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, metavar="N",
                    help=f"test modules run in parallel (default {DEFAULT_JOBS}: CPU count, at most 8; 1 runs them serially)")
    ap.add_argument("--part", choices=("all", "units", "checks"), default="all",
                    help="units: the test modules only; checks: profile suites, static and host checks only (default all)")
    ap.add_argument("--shard", type=parse_shard, metavar="K/N",
                    help="run only shard K of N of the test modules, balanced by tools/module_timings.json")
    ap.add_argument("--write-timings", type=Path, metavar="FILE",
                    help="also write the measured seconds per test module to FILE (the format of tools/module_timings.json)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    opts = parse_args(argv)
    if opts.shard and opts.part == "checks":
        print("--shard applies to the test modules; it cannot be combined with --part checks", file=sys.stderr)
        return 2
    py = sys.executable
    t = opts.module_timeout
    units = [run_unittests(opts.module_timeout, opts.jobs, opts.shard)] if opts.part in ("all", "units") else []
    checks = units + ([] if opts.part == "units" else [
        *run_profile_tests(),
        run_script("check_layering", [py, "tools/check_layering.py"], timeout=t),
        run_script("stanza_consistency", [py, "tools/build_stanzas.py", "--check"], timeout=t),
        run_script("registry", [py, "contracts/registry.py"], timeout=t),
        run_script("ams_optional", [py, "tools/check_ams_optional.py", "--jobs", str(opts.jobs)], timeout=t),
        run_script("routing_static", [py, "tools/check_routing_static.py"], timeout=t),
        run_script("ownership", [py, "tools/check_ownership.py"], timeout=t),
        run_script("reference_inventory", [py, "tools/reference_inventory.py", "--check"], timeout=t),
        run_script("packaging_scan", [py, "tools/check_packaging.py"], timeout=t),
        run_script("host_neutral", [py, "tools/check_host_neutral.py"], timeout=t),
        run_script("instruction_text", [py, "tools/check_instruction_text.py"], timeout=t),
        run_script("host_manifests", [py, "tools/check_host_manifests.py"], timeout=t),
        run_script("measure_entrypoints", [py, "tools/measure_entrypoints.py"] + (["--no-cli"] if opts.no_cli else []), timeout=t),
        host_validate() if not opts.no_cli else {"name": "claude-plugin-validate", "status": "skip", "reason": "--no-cli"},
        codex_load() if not opts.no_cli else {"name": "codex-plugin-load", "status": "skip", "reason": "--no-cli"},
    ])
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
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT), timeout=MODULE_TIMEOUT).stdout.strip() or "unknown",
        "part": opts.part,
        "counts": {s: sum(1 for c in checks if c["status"] == s) for s in ("pass", "fail", "skip")},
        "checks": checks,
        "caveat": "Software checks only; not physical validity, proof, statistical coverage, or authorization to unblind.",
    }
    text = json.dumps(summary, indent=1)
    if opts.out:
        out = opts.out
        out.mkdir(parents=True, exist_ok=True)
        (out / f"check-run-{summary['timestamp_utc'].replace(':', '')}.json").write_text(text + "\n")
    print(json.dumps({"counts": summary["counts"], "checks": [{k: c.get(k) for k in ("name", "status", "counts", "exit_code", "reason")} for c in checks]}, indent=1))
    return 0 if summary["counts"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
