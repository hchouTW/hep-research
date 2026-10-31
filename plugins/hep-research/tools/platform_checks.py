#!/usr/bin/env python3
"""Platform checks of the skill scripts (tools/skill_scripts.json) for the CI jobs old-python (tests.yml) and windows
(platforms.yml): every script is run with `--help` under each interpreter-guard case, in parallel.

  old-python --old PY39 --ro PY313 --wrapper W --writable PYW [--root-prefix CMD]
      AC2: python3.9 <script> --help with
        (a) HEP_RESEARCH_PYTHON unset: exit 2, one stderr line starting "hep-research:", empty stdout;
        (b) HEP_RESEARCH_PYTHON=PY313 (a 3.13 interpreter whose file and folder this account cannot write): the same
            exit code and stdout as PY313 run on the script directly;
        (c) HEP_RESEARCH_PYTHON=PY39 itself, and =W (a read-only wrapper that launches 3.9): exit 2 with the
            "did not provide one" line (one switch, no loop);
        (d) a relative value, a bare command name, PYW (a 3.13 in a writable folder), `--protected` among the
            arguments, and (with --root-prefix, e.g. "sudo -n --preserve-env=HEP_RESEARCH_PYTHON") running as root:
            no switch, exit 2 with the guidance line.
      AC3: find_python.py under 3.9 reports status "found" with a 3.13+ interpreter; core/partition/runner.py --help
      under 3.9 exits 0. AC4: a process switched from 3.9 to PY313 starts another skill script with python3.9 and gets
      the same result as PY313 running it directly.
  windows --python PY
      AC11: with PYTHONUTF8 unset every script exits 2 with the PYTHONUTF8 line and no traceback; with PYTHONUTF8=1
      every --help exits 0, or exits 3 with JSON "reason": "unsupported-platform" (USAGE_EXIT lists the scripts that
      answer --help with their usage text and exit 2 on every platform); zero tracebacks; core.hostcaps.state_dir()
      is under LOCALAPPDATA.

Prints a JSON report with "status" ("passed" or "failed") and every failing case; exit 0 passed, 1 failed, 2 bad
usage. Standard library only; run it with Python 3.13.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = "hep-research: Python 3.13 or newer is required (running 3.9). Set HEP_RESEARCH_PYTHON"
NOT_PROVIDED = ("hep-research: Python 3.13 or newer is required (running 3.9); HEP_RESEARCH_PYTHON did not provide "
                "one.\n")
UTF8_LINE = "hep-research: set PYTHONUTF8=1 (UTF-8 mode) to run hep-research scripts on Windows.\n"
USAGE_EXIT = {  # scripts whose --help prints the usage text and exits 2 on every platform (no argparse)
    "contracts/comparison/gate.py": "prints its docstring as usage and exits 2 on any argument it does not take",
    "contracts/project.py": "prints its docstring as usage and exits 2 on any argument it does not take",
}
GUARD_VARIABLES = ("HEP_RESEARCH_PYTHON", "HEP_RESEARCH_GUARD_REEXEC")


def scripts() -> list[dict]:
    return json.loads((ROOT / "tools" / "skill_scripts.json").read_text(encoding="utf-8"))["scripts"]


def base_env(drop=()) -> dict:
    return {k: v for k, v in os.environ.items() if k not in (*GUARD_VARIABLES, "PYTHONPATH", "PYTHONHOME", *drop)}


def run(cmd: list[str], env: dict, cwd: str) -> tuple:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                           timeout=300, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return "timeout", "", ""


def one_line(err: str, start: str) -> bool:
    return err.count("\n") == 1 and err.startswith(start) and "Traceback" not in err


def old_python(args, cwd: str) -> dict:
    root_prefix = shlex.split(args.root_prefix) if args.root_prefix else []

    def check(entry):
        path = str(ROOT / entry["path"])
        env = base_env()
        res = {}
        rc, out, err = run([args.old, path, "--help"], env, cwd)
        res["a"] = rc == 2 and out == "" and one_line(err, GUIDANCE)
        direct = run([args.ro, path, "--help"], env, cwd)
        rc, out, err = run([args.old, path, "--help"], dict(env, HEP_RESEARCH_PYTHON=args.ro), cwd)
        res["b"] = (rc, out) == direct[:2]
        for name, target in (("c_old", args.old), ("c_wrapper", args.wrapper)):
            rc, out, err = run([args.old, path, "--help"], dict(env, HEP_RESEARCH_PYTHON=target), cwd)
            res[name] = rc == 2 and out == "" and err == NOT_PROVIDED
        for name, target in (("d_relative", "bin/python3.13"), ("d_bare", "python3.13"), ("d_writable", args.writable)):
            rc, out, err = run([args.old, path, "--help"], dict(env, HEP_RESEARCH_PYTHON=target), cwd)
            res[name] = rc == 2 and out == "" and one_line(err, GUIDANCE)
        rc, out, err = run([args.old, path, "--help", "--protected"], dict(env, HEP_RESEARCH_PYTHON=args.ro), cwd)
        res["d_protected"] = rc == 2 and out == "" and one_line(err, GUIDANCE)
        if root_prefix:
            rc, out, err = run([*root_prefix, args.old, path, "--help"], dict(env, HEP_RESEARCH_PYTHON=args.ro), cwd)
            res["d_root"] = rc == 2 and out == "" and one_line(err, GUIDANCE)
        bad = {k: v for k, v in res.items() if not v}
        return entry["path"], (bad and {"failed": sorted(bad), "direct_exit": direct[0], "direct_stderr": direct[2][-400:]})

    with cf.ThreadPoolExecutor(args.jobs) as pool:
        results = dict(pool.map(check, scripts()))
    failures = {p: r for p, r in results.items() if r}
    env = base_env()
    p = run([args.old, str(ROOT / "skills/hep-computing/scripts/find_python.py")], env, cwd)
    try:
        found = json.loads(p[1])
        ac3_find = found.get("status") == "found" and tuple(int(x) for x in found["python_version"].split(".")[:2]) >= (3, 13)
    except (ValueError, KeyError, AttributeError):
        ac3_find, found = False, p[1][-400:]
    ac3_runner = run([args.old, str(ROOT / "core/partition/runner.py"), "--help"], env, cwd)[0] == 0
    child = ROOT / "skills/hep-statistics/scripts/li_ma_significance.py"
    child_args = ["--on", "10", "--off", "40", "--alpha", "0.2"]
    parent = ("import subprocess, sys\n"
              "sys.dont_write_bytecode = True\n"
              f"sys.path.insert(0, {str(ROOT)!r})\n"
              "from core.interpreter_guard import guard\n"
              "guard()\n"
              "assert sys.version_info >= (3, 13), sys.version\n"
              f"p = subprocess.run([{args.old!r}, {str(child)!r}, *{child_args!r}], capture_output=True, text=True)\n"
              "sys.stdout.write(str(p.returncode) + '\\n' + p.stdout)\n")
    parent_file = Path(cwd) / "ac4_parent.py"
    parent_file.write_text(parent, encoding="utf-8")
    nested = run([args.old, str(parent_file)], dict(env, HEP_RESEARCH_PYTHON=args.ro), cwd)
    direct = run([args.ro, str(child), *child_args], env, cwd)
    ac4 = nested[0] == 0 and nested[1] == f"{direct[0]}\n{direct[1]}" and direct[0] == 0
    ok = not failures and ac3_find and ac3_runner and ac4
    cases = ["a", "b", "c_old", "c_wrapper", "d_relative", "d_bare", "d_writable", "d_protected"] + (
        ["d_root"] if root_prefix else [])
    return {"status": "passed" if ok else "failed", "scripts": len(results), "cases": cases,
            "ac2_failures": failures, "ac3": {"find_python": ac3_find, "runner_help": ac3_runner},
            "ac3_find_python": found if not ac3_find else "found", "ac4": ac4,
            "ac4_detail": None if ac4 else {"nested": nested, "direct": direct}}


def windows(args, cwd: str) -> dict:
    def check(entry):
        path = str(ROOT / entry["path"])
        problems = []
        rc, out, err = run([args.python, path, "--help"], base_env(drop=("PYTHONUTF8", "PYTHONIOENCODING")), cwd)
        if not (rc == 2 and err == UTF8_LINE and out == ""):
            problems.append({"case": "utf8-unset", "exit": rc, "stderr": err[-400:]})
        rc, out, err = run([args.python, path, "--help"], dict(base_env(), PYTHONUTF8="1"), cwd)
        if "Traceback" in err:
            problems.append({"case": "traceback", "exit": rc, "stderr": err[-800:]})
        elif rc == 3:
            try:
                reason = json.loads(out).get("reason")
            except ValueError:
                reason = None
            if reason != "unsupported-platform":
                problems.append({"case": "exit-3-without-unsupported-platform", "stdout": out[-400:]})
        elif rc != 0 and not (rc == 2 and entry["path"] in USAGE_EXIT):
            problems.append({"case": "help-exit", "exit": rc, "stderr": err[-400:]})
        return entry["path"], (problems, rc)

    with cf.ThreadPoolExecutor(args.jobs) as pool:
        results = dict(pool.map(check, scripts()))
    failures = {p: probs for p, (probs, _) in results.items() if probs}
    unsupported = sorted(p for p, (probs, rc) in results.items() if rc == 3 and not probs)
    local = os.environ.get("LOCALAPPDATA", "")
    probe = run([args.python, "-c", "import sys; sys.path.insert(0, sys.argv[1]); from core import hostcaps; "
                 "print(hostcaps.state_dir('hep-review'))", str(ROOT)], dict(base_env(), PYTHONUTF8="1"), cwd)
    state = probe[1].strip()
    state_ok = bool(local) and probe[0] == 0 and os.path.normcase(state).startswith(os.path.normcase(local))
    ok = not failures and state_ok
    return {"status": "passed" if ok else "failed", "scripts": len(results), "failures": failures,
            "unsupported_platform": unsupported, "usage_exit_2": USAGE_EXIT,
            "state_dir": {"value": state, "localappdata": local, "ok": state_ok}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--work", type=Path, help="working folder for the runs (default: a new temporary folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("old-python")
    for name in ("--old", "--ro", "--wrapper", "--writable"):
        o.add_argument(name, required=True)
    o.add_argument("--root-prefix", help="command prefix that runs as root, e.g. 'sudo -n --preserve-env=...'")
    w = sub.add_parser("windows")
    w.add_argument("--python", required=True)
    args = ap.parse_args(argv)
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:
        cwd = str(args.work or scratch)
        os.makedirs(cwd, exist_ok=True)
        report = old_python(args, cwd) if args.cmd == "old-python" else windows(args, cwd)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
