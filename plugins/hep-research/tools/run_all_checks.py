#!/usr/bin/env python3
"""Aggregate runner: every check in one JSON summary, with pass / fail / skip kept separate.

Usage: python3 tools/run_all_checks.py [--out DIR] [--no-cli] [--module-timeout S] [--jobs N]
Writes DIR/check-run-<UTC timestamp>.json when --out is given; always prints the summary.
Exit 0 when nothing failed (skips are reported, not hidden), 1 otherwise.
Each test module runs in its own process with a timeout (default 600 s, or HEP_MODULE_TIMEOUT): a module that
does not finish is a failure with its reason, never a hang, and every module's duration is in the JSON output.
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
SLOW_MODULE_SECONDS = 60.0  # a fast-tier module above this belongs in the slow tier (HEP_SLOW_TESTS=1)


MODULE_RUNNER = """
import io, json, sys, unittest
suite = unittest.TestLoader().loadTestsFromName(sys.argv[1])
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
print(json.dumps({"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
                  "failed": [str(t) for t, _ in res.failures + res.errors], "skipped_list": [f"{t}: {r}" for t, r in res.skipped]}))
"""


def test_modules() -> list[str]:
    return sorted(".".join(p.relative_to(ROOT).with_suffix("").parts) for p in (ROOT / "tests").rglob("test_*.py"))


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
            "failed": r["failed"], "skipped": r["skipped_list"]}


def run_unittests(timeout: float = MODULE_TIMEOUT, jobs: int = 1) -> dict:
    modules = test_modules()
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        rows = list(pool.map(lambda m: run_module(m, timeout), modules))
    total = {k: sum((r["counts"] or {}).get(k, 0) for r in rows) for k in ("run", "failures", "errors", "skipped")}
    total["passed"] = total["run"] - total["failures"] - total["errors"] - total["skipped"]
    broken = [r for r in rows if r["counts"] is None]
    slow = sorted((r for r in rows if r["seconds"] > SLOW_MODULE_SECONDS), key=lambda r: -r["seconds"])
    return {"name": "unittest", "command": "python3 -m unittest <module>, one process per module under tests/",
            "status": "pass" if all(r["status"] == "pass" for r in rows) else "fail",
            "counts": dict(total, modules=len(rows), modules_failed_to_finish=len(broken)),
            "module_timeout_seconds": timeout,
            "failed": [f for r in rows for f in r["failed"]] + [f"{r['module']}: {r['reason']}" for r in broken],
            "skipped": [s for r in rows for s in r["skipped"]],
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


def run_script(name: str, cmd: list[str], cwd: Path = ROOT) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=MODULE_TIMEOUT)
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
    p = subprocess.run([exe, "plugin", "validate", str(ROOT), "--strict"], capture_output=True, text=True, timeout=MODULE_TIMEOUT)
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
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=120)
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
        out[host] = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=MODULE_TIMEOUT).stdout.strip() if exe else "not installed"
    return out


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 epilog="Passing checks shows software consistency only, not physical validity or statistical coverage.")
    ap.add_argument("--out", metavar="DIR", type=Path, help="write DIR/check-run-<UTC timestamp>.json")
    ap.add_argument("--no-cli", action="store_true", help="skip the host CLI checks (claude plugin validate, codex plugin load)")
    ap.add_argument("--module-timeout", type=float, default=MODULE_TIMEOUT, metavar="S",
                    help="seconds allowed per test module (default 600 or HEP_MODULE_TIMEOUT)")
    ap.add_argument("--jobs", type=int, default=1, metavar="N", help="test modules run in parallel (default 1)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    opts = parse_args(argv)
    py = sys.executable
    checks = [
        run_unittests(opts.module_timeout, opts.jobs),
        *run_profile_tests(),
        run_script("check_layering", [py, "tools/check_layering.py"]),
        run_script("stanza_consistency", [py, "tools/build_stanzas.py", "--check"]),
        run_script("registry", [py, "contracts/registry.py"]),
        run_script("ams_optional", [py, "tools/check_ams_optional.py"]),
        run_script("routing_static", [py, "tools/check_routing_static.py"]),
        run_script("ownership", [py, "tools/check_ownership.py"]),
        run_script("reference_inventory", [py, "tools/reference_inventory.py", "--check"]),
        run_script("packaging_scan", [py, "tools/check_packaging.py"]),
        run_script("host_neutral", [py, "tools/check_host_neutral.py"]),
        run_script("host_manifests", [py, "tools/check_host_manifests.py"]),
        run_script("measure_entrypoints", [py, "tools/measure_entrypoints.py"] + (["--no-cli"] if opts.no_cli else [])),
        host_validate() if not opts.no_cli else {"name": "claude-plugin-validate", "status": "skip", "reason": "--no-cli"},
        codex_load() if not opts.no_cli else {"name": "codex-plugin-load", "status": "skip", "reason": "--no-cli"},
    ]
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plugin_version": json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "executable": py,
                        "hosts": host_versions()},
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT), timeout=MODULE_TIMEOUT).stdout.strip() or "unknown",
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
