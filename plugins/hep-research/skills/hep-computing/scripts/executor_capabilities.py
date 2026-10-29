#!/usr/bin/env python3
"""Executor capabilities G1-G6: qualification tests by fault injection, capability declarations, and the admission
check that refuses a capability without a passing qualification (reconstruction v12 B2; CAP-01). Standard library only.

Purpose: a capability may be relied on only when the executor declares it and the declaration cites a passing
qualification record (Delivery §1.2 of the reconstruction v12.1 spec copy). The executor here is the local runner
(skills/hep-computing/scripts/run_workflow.py, DEC-07 default: local executor only). Its qualification tests:
- G1 output isolation: an old same-name output, absolute / `..` / symlinked destinations, an exit-0 command that
  writes nothing -- each must be refused or failed, with a positive control that a fresh output is accepted;
- G2 termination confirmation: a child still alive after its parent times out must be stopped and the record must
  say termination confirmed, with no write after the timeout (POSIX only; tested on Linux);
- G3 submission reconciliation, G4 resource metering with atomic reservation, G5 persistent state and G6 conditions
  resolution evidence are not provided by this executor: they are recorded as unsupported, never declared.
The qualification record names the platform and the SHA-256 of the runner it tested; a changed runner makes it stale.
Usage:
  executor_capabilities.py qualify --out QUAL.json             run the tests, write the qualification record
  executor_capabilities.py declare --qualification QUAL.json --out DECL.json
  executor_capabilities.py admit --declaration DECL.json --qualification QUAL.json (--require G1,G2 | --mode M1|M2|M3)
Output JSON with "status". Exit codes: 0 ok (qualified; declared; admitted), 1 refused (a required capability is
not qualified), 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN))
from core.status import exit_code  # noqa: E402

RUNNER = HERE / "run_workflow.py"
GUARANTEES = ("G1", "G2", "G3", "G4", "G5", "G6")
UNSUPPORTED = {
    "G3": "the local executor submits nothing remotely; submission reconciliation belongs to stage D",
    "G4": "usage is reported in receipts, but there is no atomic quota reservation at intent (stage D)",
    "G5": "no persistent control state or lease lock (stage C2, blocked: S0 N1 did not pass)",
    "G6": "the runner records no resolved conditions payload or interval of validity",
}
MODE_REQUIRES = {"M1": ("G1",), "M2": ("G1", "G2", "G5"), "M3": ("G1", "G2", "G3", "G4", "G5")}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(document) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _run(root: Path, wf: dict, name: str) -> tuple[int, dict, Path]:
    work = root / name
    path = root / f"{name}.json"
    path.write_text(json.dumps(wf), encoding="utf-8")
    p = subprocess.run([sys.executable, "-B", str(RUNNER), str(path), "--work", str(work), "--created", "2026-01-01"],
                       capture_output=True, text=True, timeout=600)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"status": "unparsable", "stderr": p.stderr[-400:]}
    return p.returncode, out, work


def _step(code: str, outputs: list[str], **kw) -> dict:
    return {"workflow": "q", "steps": [{"id": "s", "argv": ["{python}", "-c", code], "outputs": outputs, **kw}]}


def qualify_g1(root: Path) -> dict:
    cases = []

    def case(name, ok, detail):
        cases.append({"case": name, "passed": bool(ok), "detail": detail})

    (root / "stale").mkdir()
    (root / "stale" / "o.txt").write_text("old")
    code, out, _ = _run(root, _step("pass", ["o.txt"]), "stale")
    case("old same-name output is not accepted", code == 1, out.get("status"))
    code, out, _ = _run(root, _step("pass", ["o.txt"]), "noout")
    case("exit 0 without writing fails", code == 1, out.get("status"))
    old = root / "old.txt"
    old.write_text("old")
    code, out, _ = _run(root, _step("pass", [str(old)]), "absolute")
    case("absolute destination refused", code == 2, out.get("status"))
    code, out, _ = _run(root, _step("pass", ["../old.txt"]), "dotdot")
    case("'..' destination refused", code == 2, out.get("status"))
    if os.name == "posix":
        (root / "link").mkdir()
        (root / "link" / "l").symlink_to(root, target_is_directory=True)
        code, out, _ = _run(root, _step("pass", ["l/old.txt"]), "link")
        case("symlinked destination refused", code == 2, out.get("status"))
    code, out, work = _run(root, _step("open('o.txt', 'w').write('new')", ["o.txt"]), "fresh")
    case("positive control: a fresh output is accepted", code == 0 and (work / "o.txt").read_text() == "new",
         out.get("status"))
    return {"status": "pass" if all(c["passed"] for c in cases) else "fail", "cases": cases}


def qualify_g2(root: Path) -> dict:
    if os.name != "posix":
        return {"status": "unsupported", "reason": "termination is observed only on POSIX hosts (DEC-04)"}
    late = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(2.5); open(\"late.txt\", \"w\").write(\"x\")']); import time; time.sleep(60)")
    t0 = time.monotonic()
    code, out, work = _run(root, _step(late, ["o.txt"], timeout_s=1), "timeout")
    elapsed = time.monotonic() - t0
    rec = work / "runs" / "s.computational-run.json"
    ext = json.loads(rec.read_text(encoding="utf-8"))["extension"] if rec.is_file() else {}
    time.sleep(4)
    cases = [{"case": "a run record is written on a timeout", "passed": rec.is_file(), "detail": out.get("status")},
             {"case": "termination confirmed and end status timeout",
              "passed": (ext.get("termination"), ext.get("end_status")) == ("confirmed", "timeout"), "detail": ext.get("termination")},
             {"case": "no write after the timeout", "passed": not (work / "late.txt").exists(), "detail": ""},
             {"case": "the runner returned promptly", "passed": elapsed < 60, "detail": round(elapsed, 1)},
             {"case": "the step failed", "passed": code == 1, "detail": code}]
    return {"status": "pass" if all(c["passed"] for c in cases) else "fail", "cases": cases}


def qualify() -> dict:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "g1").mkdir()
        (root / "g2").mkdir()
        tests = {"G1": qualify_g1(root / "g1"), "G2": qualify_g2(root / "g2")}
    for g, why in UNSUPPORTED.items():
        tests[g] = {"status": "unsupported", "reason": why}
    return {"kind": "executor-qualification", "executor": "local-run_workflow",
            "runner_sha256": sha256_file(RUNNER), "platform": {"system": platform.system(), "machine": platform.machine(),
                                                               "python": platform.python_version()},
            "tests": tests}


def declare(qual: dict) -> dict:
    digest = hashlib.sha256(canonical(qual)).hexdigest()
    caps = {g: {"qualification_sha256": digest} for g, t in qual["tests"].items() if t.get("status") == "pass"}
    return {"kind": "executor-capabilities", "executor": qual["executor"], "capabilities": caps,
            "unsupported": {g: t.get("reason", t.get("status")) for g, t in qual["tests"].items()
                            if t.get("status") != "pass"}}


def admit(decl: dict, qual: dict, required: list[str]) -> dict:
    """Refuse every required capability that is not declared with a passing, current qualification."""
    digest = hashlib.sha256(canonical(qual)).hexdigest()
    refused = {}
    for g in required:
        cap = (decl.get("capabilities") or {}).get(g)
        test = (qual.get("tests") or {}).get(g) or {}
        if cap is None:
            refused[g] = "not declared"
        elif cap.get("qualification_sha256") != digest:
            refused[g] = "the declaration does not cite this qualification record"
        elif test.get("status") != "pass":
            refused[g] = f"qualification {test.get('status', 'missing')}"
        elif qual.get("runner_sha256") != sha256_file(RUNNER):
            refused[g] = "the runner changed since it was qualified"
    return {"status": "refused" if refused else "ok", "required": required, "refused": refused}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("qualify")
    q.add_argument("--out", type=Path, required=True)
    d = sub.add_parser("declare")
    d.add_argument("--qualification", type=Path, required=True)
    d.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("admit")
    a.add_argument("--declaration", type=Path, required=True)
    a.add_argument("--qualification", type=Path, required=True)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--require")
    g.add_argument("--mode", choices=sorted(MODE_REQUIRES))
    args = ap.parse_args(argv)
    try:
        if args.cmd == "qualify":
            qual = qualify()
            args.out.write_text(json.dumps(qual, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            ok = all(qual["tests"][g]["status"] == "pass" for g in ("G1",))
            out = {"status": "ok" if ok else "refused", "tests": {k: v["status"] for k, v in qual["tests"].items()}}
        elif args.cmd == "declare":
            decl = declare(json.loads(args.qualification.read_text(encoding="utf-8")))
            args.out.write_text(json.dumps(decl, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            out = {"status": "ok", "declared": sorted(decl["capabilities"]), "unsupported": sorted(decl["unsupported"])}
        else:
            required = list(MODE_REQUIRES[args.mode]) if args.mode else [x.strip() for x in args.require.split(",")]
            if any(x not in GUARANTEES for x in required):
                raise ValueError(f"unknown guarantee in {required}")
            out = admit(json.loads(args.declaration.read_text(encoding="utf-8")),
                        json.loads(args.qualification.read_text(encoding="utf-8")), required)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        out = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, indent=1, sort_keys=True))
    return exit_code(out["status"])


if __name__ == "__main__":
    sys.exit(main())
