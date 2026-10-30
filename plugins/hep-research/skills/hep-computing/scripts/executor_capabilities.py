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
- G5 persistent state (reconstruction v12 C2), with the control-layer helper (control_layer.py) as the persistent
  state: restart recovery (a writer killed mid-session; a fresh process with only the task log derives the same
  state, every acknowledged fact exactly once, an operation id not appended twice, an unknown attempt still unknown
  and blocking its step, a torn last line recovered) and stale lock takeover (the live lease of a killed owner is not
  taken over; once expired it is taken over only after the unknown attempt is reconciled, and the takeover is
  recorded). The control rules that state serves did not pass the S0 spec review (obligation N1);
- G3 submission reconciliation, G4 resource metering with atomic reservation and G6 conditions resolution evidence are
  not provided by this executor: they are recorded as unsupported, never declared.
The qualification record names the platform and the SHA-256 of the runner it tested and, for G5, the SHA-256 of
every control-layer file it tested; a changed runner (or control layer, for G5) makes it stale.
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
CONTROL = HERE / "control_layer.py"
GUARANTEES = ("G1", "G2", "G3", "G4", "G5", "G6")
UNSUPPORTED = {
    "G3": "the local executor submits nothing remotely; submission reconciliation belongs to stage D",
    "G4": "usage is reported in receipts, but there is no atomic quota reservation at intent (stage D)",
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


def control_files() -> dict:
    """{relative name: SHA-256} of the control-layer files G5 qualifies."""
    files = [CONTROL] + sorted((HERE / "control_layer_support").glob("*.py"))
    return {f.relative_to(HERE).as_posix(): sha256_file(f) for f in files}


def control_digest() -> str:
    return hashlib.sha256(canonical(control_files())).hexdigest()


def _ctl(*args, env=None) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, "-B", str(CONTROL), *map(str, args)], capture_output=True, text=True,
                          timeout=600, env=env)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, {"status": "unparsable", "stderr": proc.stderr[-400:]}


G5_WRITER = """import json, sys
sys.path.insert(0, sys.argv[1])
import control_layer
from control_layer_support.task_record import TaskRecord
log = sys.argv[2]
i = 0
while True:
    head = TaskRecord(log).read().log.head
    code = control_layer.main(["exposure", "--task-log", log, "--sample", "CR", "--op", f"w{i}",
                               "--expect-head", str(head)])
    if code == 0:
        print(f"ACK w{i}", flush=True)
        i += 1
"""
G5_LEASE_HOLDER = """import sys
sys.path.insert(0, sys.argv[1])
import control_layer, time
control_layer.main(["lock", "acquire", "--task-log", sys.argv[2], "--owner", "s1", "--lease-s", sys.argv[3]])
print("ACK lease", flush=True)
time.sleep(600)
"""


def _spawn_until(script: str, args: list[str], acks: int) -> tuple[list[str], int]:
    """Start a writer, wait for `acks` acknowledgements on stdout, then SIGKILL it (a session dying mid-work)."""
    proc = subprocess.Popen([sys.executable, "-B", "-c", script, *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    seen = []
    deadline = time.monotonic() + 120
    while len(seen) < acks and time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if line.startswith("ACK "):
            seen.append(line.split()[1])
    proc.kill()
    rest = proc.stdout.read()                      # acknowledgements printed before the kill landed
    seen += [line.split()[1] for line in rest.splitlines() if line.startswith("ACK ")]
    proc.stdout.close()
    return seen, proc.wait()


def qualify_g5(root: Path) -> dict:
    """G5: restart recovery and stale lock takeover of the control-layer task record (fault injection)."""
    if os.name != "posix":
        return {"status": "unsupported", "reason": "the record's flock and the fault injection are POSIX only"}
    cases = []

    def case(name, ok, detail=""):
        cases.append({"case": name, "passed": bool(ok), "detail": detail})

    log = root / "hep-research-artifacts" / "g5" / "task-log" / "task-log.jsonl"
    qual = {"kind": "executor-qualification", "executor": "local-run_workflow", "runner_sha256": sha256_file(RUNNER),
            "tests": {"G1": {"status": "pass", "note": "synthetic: G5 qualifies persistence only"}}}
    (root / "qual.json").write_text(json.dumps(qual))
    (root / "decl.json").write_text(json.dumps(declare(qual)))
    contract = {"steps": {"raw": {"program": "pRaw", "environment": "g5"},
                          "reco": {"program": "pReco", "environment": "g5", "upstream": ["raw"], "checked": True,
                                   "required_checks": [["c" * 64, "k" * 64]]}},
                "deliverables": {"D": {"step": "reco", "target": "T2"}}, "families": {},
                "samples": {"CR": "control"}, "budget": None}
    (root / "contract.json").write_text(json.dumps(contract))
    admit_args = ["--declaration", root / "decl.json", "--qualification", root / "qual.json", "--cost", "0"]
    steps = [_ctl("init", "--task-log", log),
             _ctl("contract", "--task-log", log, "--file", root / "contract.json", "--expect-head", 1),
             _ctl("admit", "--task-log", log, "--attempt", "a1:raw", "--step", "raw", "--expect-head", 2, *admit_args),
             _ctl("receipt", "--task-log", log, "--lost", "--attempt", "a1:raw", "--expect-head", 3)]
    case("setup: record, contract, an admitted attempt recorded lost (unknown)", all(c == 0 for c, _ in steps),
         [o.get("status") for _, o in steps])
    # restart recovery: a writer killed mid-session
    acked, _ = _spawn_until(G5_WRITER, [str(HERE), str(log)], 8)
    code, verified = _ctl("verify", "--task-log", log)
    lines = [json.loads(raw) for raw in log.read_bytes().split(b"\n")[:-1]]
    ops = [line["op"] for line in lines if (line["op"] or "").startswith("w")]
    case("the record verifies in a fresh process after the writer was killed", code == 0, verified.get("status"))
    case("every acknowledged fact is present exactly once, nothing duplicated", set(acked) <= set(ops)
         and len(ops) == len(set(ops)) and len(ops) <= len(acked) + 1, f"{len(acked)} acknowledged, {len(ops)} found")
    head = verified.get("head")
    code, again = _ctl("exposure", "--task-log", log, "--sample", "CR", "--op", "w0", "--expect-head", head)
    case("a repeated operation id is replayed, not appended", code == 0 and again.get("replayed") is True
         and again.get("head") == head, again.get("status"))
    first, second = _ctl("resume", "--task-log", log), _ctl("resume", "--task-log", log)
    case("two fresh processes derive the same resumption summary", first == second and first[0] == 0, "")
    summary = first[1]
    case("the unknown attempt stays unknown and is listed as not to be resubmitted",
         summary.get("attempts_by_state", {}).get("unknown") == ["a1:raw"]
         and "a1:raw" in summary.get("do_not_resubmit", []), summary.get("attempts_by_state"))
    code, blocked = _ctl("admit", "--task-log", log, "--attempt", "a2:raw", "--step", "raw", "--expect-head", head,
                         *admit_args)
    case("admission of the same step is refused while the attempt is unknown", code == 1, blocked.get("reason"))
    before = _ctl("status", "--task-log", log)
    with open(log, "ab") as handle:                 # a torn, never acknowledged append
        handle.write(b'{"batch":')
    torn_code, _ = _ctl("verify", "--task-log", log)
    rec_code, recovered = _ctl("recover", "--task-log", log)
    case("a torn last line is refused, then recovered, with the same derived state", torn_code == 2
         and rec_code == 0 and recovered.get("recovered") is True and _ctl("status", "--task-log", log) == before,
         recovered.get("torn_sha256"))
    # stale lock takeover
    _spawn_until(G5_LEASE_HOLDER, [str(HERE), str(log), "3"], 1)
    t_dead = time.monotonic()
    code, live = _ctl("lock", "acquire", "--task-log", log, "--owner", "s2")
    case("the live lease of a killed owner is not taken over", code == 1, live.get("reason"))
    head = _ctl("verify", "--task-log", log)[1].get("head")
    code, out = _ctl("exposure", "--task-log", log, "--sample", "CR", "--owner", "s2", "--expect-head", head)
    case("a write by another owner is refused while that lease is live", code == 1, out.get("reason"))
    time.sleep(max(0.0, 3.3 - (time.monotonic() - t_dead)))
    code, early = _ctl("lock", "acquire", "--task-log", log, "--owner", "s2")
    case("an expired lease is not taken over before the unknown attempt is reconciled", code == 1,
         early.get("reason"))
    work = root / "run-a1"
    work.mkdir()
    workflow = root / "a1.json"
    workflow.write_text(json.dumps({"workflow": "g5", "steps": [
        {"id": "raw", "argv": ["{python}", "-c", "open('o.txt', 'w').write('1')"], "outputs": ["o.txt"]}]}))
    subprocess.run([sys.executable, "-B", str(RUNNER), str(workflow), "--work", str(work), "--receipt-dir",
                    str(root / "receipts"), "--attempt-prefix", "a1:"], capture_output=True, timeout=600)
    code, rec = _ctl("reconcile", "--task-log", log, "--receipt", root / "receipts" / "a1:raw.receipt.json",
                     "--work", work, "--expect-head", head)
    states = _ctl("resume", "--task-log", log)[1].get("attempts_by_state", {})
    case("the unknown attempt is reconciled from the receipt that proves its outcome", code == 0
         and states.get("computed") == ["a1:raw"], rec.get("status"))
    code, taken = _ctl("lock", "acquire", "--task-log", log, "--owner", "s2")
    history = _ctl("lock", "status", "--task-log", log)[1].get("history", [])
    case("after reconciliation the expired lease is taken over and the takeover is recorded",
         code == 0 and taken.get("event") == "takeover" and history and history[-1].get("event") == "takeover"
         and history[-1].get("previous_owner") == "s1", taken.get("event"))
    head = _ctl("verify", "--task-log", log)[1].get("head")
    code, stale = _ctl("exposure", "--task-log", log, "--sample", "CR", "--owner", "s1", "--expect-head", head)
    case("the old owner's write is refused after the takeover", code == 1, stale.get("reason"))
    return {"status": "pass" if all(c["passed"] for c in cases) else "fail", "cases": cases,
            "tested": {"control_layer": control_files(), "runner_sha256": sha256_file(RUNNER),
                       "note": "the control rules this state serves did not pass the S0 spec review (N1)"}}


def qualify() -> dict:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for name in ("g1", "g2", "g5"):
            (root / name).mkdir()
        tests = {"G1": qualify_g1(root / "g1"), "G2": qualify_g2(root / "g2"), "G5": qualify_g5(root / "g5")}
    for g, why in UNSUPPORTED.items():
        tests[g] = {"status": "unsupported", "reason": why}
    return {"kind": "executor-qualification", "executor": "local-run_workflow",
            "runner_sha256": sha256_file(RUNNER), "control_sha256": control_digest(), "platform": {"system": platform.system(), "machine": platform.machine(),
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
        outcome = (qual.get("tests") or {}).get(g) or {}
        if cap is None:
            refused[g] = "not declared"
        elif cap.get("qualification_sha256") != digest:
            refused[g] = "the declaration does not cite this qualification record"
        elif outcome.get("status") != "pass":
            refused[g] = f"qualification {outcome.get('status', 'missing')}"
        elif qual.get("runner_sha256") != sha256_file(RUNNER):
            refused[g] = "the runner changed since it was qualified"
        elif g == "G5" and qual.get("control_sha256") != control_digest():
            refused[g] = "the control layer changed since it was qualified"
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
