#!/usr/bin/env python3
"""Aggregate runner: every check in one JSON summary, with pass / fail / skip kept separate.

Usage: python3 tools/run_all_checks.py [--out DIR] [--no-cli]
Writes DIR/check-run-<UTC timestamp>.json when --out is given; always prints the summary.
Exit 0 when nothing failed (skips are reported, not hidden), 1 otherwise.
Passing checks shows software consistency only, not physical validity or statistical coverage.
"""
from __future__ import annotations

import io
import json
import platform
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_unittests() -> dict:
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    stream = io.StringIO()
    res = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {"name": "unittest", "command": "python3 -m unittest discover -s tests -t .",
            "status": "pass" if res.wasSuccessful() else "fail",
            "counts": {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
                       "passed": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)},
            "failed": [str(t) for t, _ in res.failures + res.errors], "skipped": [f"{t}: {r}" for t, r in res.skipped]}


PROFILE_RUNNER = """
import io, json, sys, unittest
suite = unittest.TestLoader().discover("tests", top_level_dir="tests")
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
print(json.dumps({"status": "pass" if res.wasSuccessful() else "fail",
  "counts": {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors), "skipped": len(res.skipped),
             "passed": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)},
  "failed": [str(t) for t, _ in res.failures + res.errors], "skipped": [f"{t}: {r}" for t, r in res.skipped]}))
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
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
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
    p = subprocess.run([exe, "plugin", "validate", str(ROOT), "--strict"], capture_output=True, text=True)
    return {"name": "claude-plugin-validate", "command": "claude plugin validate <plugin> --strict", "exit_code": p.returncode,
            "status": "pass" if p.returncode == 0 else "fail", "detail": p.stdout.strip()[-1500:]}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    py = sys.executable
    checks = [
        run_unittests(),
        *run_profile_tests(),
        run_script("check_layering", [py, "tools/check_layering.py"]),
        run_script("stanza_consistency", [py, "tools/build_stanzas.py", "--check"]),
        run_script("registry", [py, "contracts/registry.py"]),
        run_script("ams_ledger_preservation", [py, "tools/check_ams_ledger_preservation.py"]),
        run_script("ams_optional", [py, "tools/check_ams_optional.py"]),
        run_script("measure_entrypoints", [py, "tools/measure_entrypoints.py"] + (["--no-cli"] if "--no-cli" in args else [])),
        host_validate() if "--no-cli" not in args else {"name": "claude-plugin-validate", "status": "skip", "reason": "--no-cli"},
    ]
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plugin_version": json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "executable": py},
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip() or "unknown",
        "counts": {s: sum(1 for c in checks if c["status"] == s) for s in ("pass", "fail", "skip")},
        "checks": checks,
        "caveat": "Software checks only; not physical validity, proof, statistical coverage, or authorization to unblind.",
    }
    text = json.dumps(summary, indent=1)
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / f"check-run-{summary['timestamp_utc'].replace(':', '')}.json").write_text(text + "\n")
    print(json.dumps({"counts": summary["counts"], "checks": [{k: c.get(k) for k in ("name", "status", "counts", "exit_code", "reason")} for c in checks]}, indent=1))
    return 0 if summary["counts"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
