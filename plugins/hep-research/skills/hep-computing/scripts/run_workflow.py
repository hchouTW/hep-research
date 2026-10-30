#!/usr/bin/env python3
"""Run a workflow DAG of analysis steps and write a computational-run artifact per step (C6). Standard library only.

Purpose: a reproducible chain of steps that a plain Python can run, the same DAG a Snakefile template mirrors
(<plugin root>/skills/hep-computing/assets/workflow/). See
<plugin root>/skills/hep-computing/references/analysis-workflows.md.
Method: the steps run in a topological order of `needs` (ties in file order); each runs as an argument list (no
shell) in the work folder, with placeholders {python} (this interpreter), {plugin} (the plugin root) and {workflow}
(the folder of the workflow file) replaced; a step's declared inputs must exist before it runs and its outputs after.
Each step writes runs/<id>.computational-run.json: inputs with SHA-256, the command with the placeholders kept (so the
record does not depend on where it ran), the Python version, seeds, exit status and output hashes. Paths inside the
work folder are relative, so a rerun on the same inputs is byte-identical.
From contracts 3.11.0 (detector design M2, INC-01) each record also carries extension.argv (the recorded argument
list), extension.script_sha256 (each .py script named in argv), versions.plugin_release (contracts/identity.py) and
the NumPy version in environment.
Incremental (--incremental, INC-02..INC-04): a step is skipped, its record kept, only when its previous record has the
same argv, script_sha256, plugin release digest (never when that digest is unknown), environment and input hashes,
the same complete output contract (the declared outputs), and its outputs still have the recorded hashes. A step may
declare "parameter_digest": {"argv": [...], "replaces": [INPUT, ...]}: the command prints JSON with a
parameter_digest (evaluate_design.py run --digest-only), recorded as extension.parameter_digest, and the listed inputs
(candidate files) are then compared by that digest instead of their file hash, so a change to a parameter the step
does not read does not rerun it.
Output freshness and termination (reconstruction v12 B1, OUT-01, CACHE-01, EXEC-02): every input, output and stdout
path is relative to the work folder, without `..` and not through a symlink (anything else is refused before any step
runs); an output counts only when this run wrote it (a file left from before and not rewritten makes the step fail);
each step runs in its own process group, which is stopped and confirmed gone on a timeout and after the step exits.
The record carries extension.end_status (success, failure, timeout), extension.termination (confirmed, unconfirmed),
extension.output_contract and extension.artifact_digest (SHA-256 of the canonical output manifest); output hashes
are recorded only when termination is confirmed. Termination is observed on POSIX hosts only (tested on Linux): a
process that leaves the group and clears its environment is not seen.
Input: workflow JSON {"workflow": NAME, "steps": [{"id" (one plain name: letters, digits, '_', '.', ':', '-', not
starting with '.', ':' or '-', at most 128 characters; it names the run record and the receipt), "needs": [...],
"inputs": [...], "outputs": [...],
"argv": [...], "stdout": FILE (optional), "seeds": {...} (optional), "parameter_digest": {...} (optional),
"timeout_s": SECONDS (optional, default 3600), "check": {...} (optional: a check run's declared identity, below)}]}.
A check step (reconstruction v12 A2 fields, defined in scripts/check_definitions.py) declares "check":
{"check_digest", "criterion_digest", "target_artifact_digest" (SHA-256 hex), "criteria_file", "result_file" (relative
paths: an input and an output of the step), "target_manifest" ({target logical name: staged input path}), "role"
(closure, confirmation-holdout, confirmation-independent), "type" (threshold, performance-estimate), "samples" (the
read list)}; the object is validated before any step runs and recorded as extension.check. After the check program
ends, its result file must bind to the run (B2, VAL-06): the check digest is the hash of a script in argv, the
criterion digest the hash of the criteria file, the target digest the canonical digest of the staged target outputs,
and the result file repeats the three digests with a four-valued result, a reason and samples from the read list;
extension.check_result records the verdict, and an unbound result fails the step.
Receipts (B2, --receipt-dir DIR): one <attempt>.receipt.json per executed step, outside the run records so that the
records stay byte-identical. The attempt id is --attempt-prefix + step id and is used once: a run in which any step's
attempt id already has a receipt is refused before any step runs (exit 2), and a receipt is never replaced. Fields:
attempt, step, end status, termination, outputs (logical name, location in the work folder, digest), artifact digest, observed input evidence (not observable: declared inputs only, DEC-10), conditions
resolution (not recorded: G6 unsupported), the run record's path and SHA-256, start and end times and resource usage
(wall and CPU seconds of the step's process tree, POSIX).
Usage: run_workflow.py WORKFLOW.json --work DIR [--created YYYY-MM-DD] [--dry-run] [--incremental] [--status LABEL]
       [--receipt-dir DIR] [--attempt-prefix TEXT]
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, order and per-step results.
Exit codes: 0 every step ran; 1 a step failed or its termination is unconfirmed (later steps are not run); 2 bad
input (malformed workflow, an unsafe path or step id, a cycle, an unknown dependency, a missing input or output,
an attempt id that already has a receipt).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # the imports below leave no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import trace  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

STEP_TIMEOUT_S = 3600
STOP_GRACE_S = 5.0     # SIGTERM, then SIGKILL after this many seconds
CONFIRM_S = 5.0        # how long to wait for the process group to disappear
MARKER = "HEP_RUN_WORKFLOW_ATTEMPT"  # environment token used to find processes that left the group (Linux /proc)
STEP_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._:-]{0,127}")  # one plain path component: names records and receipts


class WorkflowError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_digest(document) -> str:
    """SHA-256 of the canonical JSON form (sorted keys, no whitespace, UTF-8), as the reconstruction spec defines it."""
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def safe_relative(p) -> bool:
    """A path the runner may use: a non-empty relative POSIX path without `..`, `.`-only or empty parts."""
    if not isinstance(p, str) or not p or "\\" in p or "\0" in p:
        return False
    pp = PurePosixPath(p)
    return not pp.is_absolute() and all(part not in ("", ".", "..") for part in pp.parts) and not p.endswith("/")


CHECK_KEYS = {"check_digest", "criterion_digest", "target_artifact_digest", "criteria_file", "result_file",
              "target_manifest", "role", "type", "samples"}


def check_problem(step: dict) -> str | None:
    """The declared identity of a check run (A2 fields; scripts/check_definitions.py ROLES and TYPES)."""
    from check_definitions import ROLES, TYPES  # noqa: PLC0415  (sibling script)
    c = step["check"]
    if not isinstance(c, dict) or set(c) != CHECK_KEYS:
        return f"needs exactly {sorted(CHECK_KEYS)}"
    hexes = [c["check_digest"], c["criterion_digest"], c["target_artifact_digest"]]
    if not all(isinstance(x, str) and len(x) == 64 and set(x) <= set("0123456789abcdef") for x in hexes):
        return "check, criterion and target digests are SHA-256 hex"
    if c["role"] not in ROLES or c["type"] not in TYPES:
        return f"role in {ROLES}, type in {TYPES}"
    if c["criteria_file"] not in step.get("inputs", []) or c["result_file"] not in step.get("outputs", []):
        return "the criteria file is an input and the result file an output of the step"
    tm = c["target_manifest"]
    if not isinstance(tm, dict) or not tm or not all(isinstance(k, str) and v in step.get("inputs", [])
                                                     for k, v in tm.items()):
        return "target_manifest maps each target logical name to a staged input of the step"
    if not isinstance(c["samples"], list) or not all(isinstance(x, str) for x in c["samples"]):
        return "samples is the read list (a list of names)"
    return None


def check_binding(step: dict, work: Path, inputs: list[dict], scripts: dict, outputs: dict) -> dict:
    """Whether a check run's result file binds to this run (B2, VAL-06; reconstruction v12.1 Control §7.2)."""
    from check_definitions import RESULTS  # noqa: PLC0415  (sibling script)
    c = step["check"]
    have = {i["path"]: i["sha256"] for i in inputs}
    problems = []
    if c["check_digest"] not in set(scripts.values()):
        problems.append("the check digest is not the hash of a script the run executed")
    if have.get(c["criteria_file"]) != c["criterion_digest"]:
        problems.append("the criterion digest is not the hash of the criteria file")
    staged = {name: have.get(path) for name, path in c["target_manifest"].items()}
    if canonical_digest(staged) != c["target_artifact_digest"]:
        problems.append("the staged target outputs do not reproduce the target artifact digest")
    try:
        res = json.loads((work / c["result_file"]).read_text(encoding="utf-8")) if c["result_file"] in outputs else None
    except (OSError, ValueError):
        res = None
    if not isinstance(res, dict):
        return {"bound": False, "problems": problems + ["no readable result file"]}
    for key in ("check_digest", "criterion_digest", "target_artifact_digest"):
        if res.get(key) != c[key]:
            problems.append(f"the result's {key} differs from the declared one")
    if res.get("result") not in RESULTS or not isinstance(res.get("reason"), str) or not res.get("reason"):
        problems.append("the result is not four-valued with a reason")
    used = res.get("samples", [])
    if not isinstance(used, list) or not set(used) <= set(c["samples"]):
        problems.append("a sample used is not in the read list")
    return {"bound": not problems, "problems": problems, "result": res.get("result"), "reason": res.get("reason"),
            "samples": used if isinstance(used, list) else []}


def usage_now() -> tuple[float, float]:
    """(wall clock, CPU seconds of reaped children) for receipts; CPU is 0.0 where `resource` is missing."""
    try:
        import resource  # noqa: PLC0415  (POSIX only)
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        return time.monotonic(), r.ru_utime + r.ru_stime
    except ImportError:
        return time.monotonic(), 0.0


def through_symlink(work: Path, rel: str) -> bool:
    """True when any existing component of work/rel below the work folder is a symlink (BUG-03)."""
    cur = work
    for part in PurePosixPath(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            return True
        if not cur.exists():
            return False
    return False


def load(path: Path) -> dict:
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"cannot read {path}: {exc}") from exc
    steps = wf.get("steps") if isinstance(wf, dict) else None
    if not isinstance(steps, list) or not steps:
        raise WorkflowError("a workflow needs a non-empty 'steps' list")
    ids = []
    for s in steps:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not s["id"]:
            raise WorkflowError("every step needs a string 'id'")
        if not STEP_ID.fullmatch(s["id"]) or s["id"] in (".", ".."):
            raise WorkflowError(f"step id {s['id']!r}: a step id names the run record and the receipt, so it is one "
                                "plain name (letters, digits, '_', '.', ':', '-'; not starting with '.', ':' or '-'; "
                                "at most 128 characters) (OUT-01)")
        if not isinstance(s.get("argv"), list) or not s["argv"] or not all(isinstance(a, str) for a in s["argv"]):
            raise WorkflowError(f"step {s['id']}: 'argv' must be a non-empty list of strings")
        for key in ("needs", "inputs", "outputs"):
            if not isinstance(s.get(key, []), list):
                raise WorkflowError(f"step {s['id']}: '{key}' must be a list")
        paths = [*s.get("inputs", []), *s.get("outputs", [])] + ([s["stdout"]] if "stdout" in s else [])
        bad = [p for p in paths if not safe_relative(p)]
        if bad:
            raise WorkflowError(f"step {s['id']}: paths must be relative to the work folder, without '..' (OUT-01): "
                                f"{bad}")
        if len(set(s.get("outputs", []))) != len(s.get("outputs", [])):
            raise WorkflowError(f"step {s['id']}: duplicate outputs")
        t = s.get("timeout_s", STEP_TIMEOUT_S)
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0:
            raise WorkflowError(f"step {s['id']}: 'timeout_s' must be a positive finite number of seconds")
        if "check" in s:
            why = check_problem(s)
            if why:
                raise WorkflowError(f"step {s['id']}: check: {why}")
        ids.append(s["id"])
    if len(set(ids)) != len(ids):
        raise WorkflowError("step ids must be unique")
    for s in steps:
        unknown = [n for n in s.get("needs", []) if n not in ids]
        if unknown:
            raise WorkflowError(f"step {s['id']} needs unknown step(s) {unknown}")
    return wf


def order(steps: list[dict]) -> list[str]:
    """Kahn's algorithm; ties keep the file order. A cycle is refused."""
    pending = {s["id"]: set(s.get("needs", [])) for s in steps}
    done: list[str] = []
    while pending:
        ready = [i for i in (s["id"] for s in steps) if i in pending and not pending[i]]
        if not ready:
            raise WorkflowError(f"the workflow has a cycle among {sorted(pending)}")
        for i in ready:
            done.append(i)
            del pending[i]
            for deps in pending.values():
                deps.discard(i)
    return done


def environment() -> dict:
    env = {"python": platform.python_version()}
    try:
        import numpy  # type: ignore  # noqa: PLC0415  (optional: the record names it when installed)
        env["numpy"] = numpy.__version__
    except ImportError:
        env["numpy"] = "not-installed"
    return env


def script_hashes(rec_cmd: list[str], cmd: list[str], work: Path) -> dict:
    """INC-01: SHA-256 of each .py script named in argv, keyed by the recorded token."""
    out = {}
    for shown, real in zip(rec_cmd, cmd):
        if real.endswith(".py"):
            p = Path(real) if Path(real).is_absolute() else work / real
            if p.is_file():
                out[shown] = sha256(p)
    return out


def stat_key(path: Path):
    """What identifies the file as it is now; a write by the step changes it (BUG-01)."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _marked(token: str) -> list[int]:
    """PIDs of processes still carrying this attempt's environment token (Linux /proc); [] elsewhere."""
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    needle = f"{MARKER}={token}".encode()
    pids = []
    for d in proc.iterdir():
        if not d.name.isdigit() or int(d.name) == os.getpid():
            continue
        try:
            if needle in (d / "environ").read_bytes().split(b"\0"):
                pids.append(int(d.name))
        except OSError:
            continue
    return pids


def _stop(pgid: int | None, token: str, proc: subprocess.Popen) -> bool:
    """Stop the step's process group and any process carrying its token; True when none is left (confirmed)."""
    def signal_all(sig):
        if pgid is not None:
            try:
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError):
                pass
        else:
            try:
                proc.send_signal(sig)
            except OSError:
                pass
        for pid in _marked(token):
            try:
                os.kill(pid, sig)
            except (ProcessLookupError, PermissionError):
                pass

    def left() -> bool:
        if proc.poll() is None:
            return True
        return (pgid is not None and _group_alive(pgid)) or bool(_marked(token))

    if not left():
        return True
    signal_all(signal.SIGTERM)
    deadline = time.monotonic() + STOP_GRACE_S
    while left() and time.monotonic() < deadline:
        time.sleep(0.05)
    if left():
        signal_all(signal.SIGKILL)
        deadline = time.monotonic() + CONFIRM_S
        while left() and time.monotonic() < deadline:
            time.sleep(0.05)
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    return pgid is not None and not left()  # without a process group termination is never confirmed


def execute(cmd: list[str], cwd: Path, timeout: float) -> dict:
    """Run cmd in its own process group (POSIX) under a deadline; stop and confirm the group at the end (BUG-04).
    Returns returncode, stdout, stderr, end ('success', 'failure', 'timeout') and termination ('confirmed',
    'unconfirmed'). Leftover processes after the step exits are stopped and make the step a failure."""
    token = uuid.uuid4().hex
    env = dict(os.environ, **{MARKER: token})
    posix = os.name == "posix"
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                            start_new_session=posix)
    pgid = proc.pid if posix else None
    end, note = None, ""
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        end, note = "timeout", f"timed out after {timeout:g} s"
        confirmed = _stop(pgid, token, proc)
        try:
            out, err = proc.communicate(timeout=CONFIRM_S)
        except subprocess.TimeoutExpired:  # a surviving process still holds the pipes: give them up
            out, err = "", ""
            for pipe in (proc.stdout, proc.stderr):
                if pipe is not None:
                    pipe.close()
        return {"returncode": proc.returncode if proc.returncode is not None else -1, "stdout": out or "",
                "stderr": (err or "") + f"\n[run_workflow] {note}", "end": end,
                "termination": "confirmed" if confirmed else "unconfirmed"}
    leftover = (pgid is not None and _group_alive(pgid)) or bool(_marked(token))
    confirmed = _stop(pgid, token, proc) if leftover else pgid is not None
    code = proc.returncode
    if leftover:
        note = "\n[run_workflow] the step left processes running; they were stopped and the step counts as failed"
        code = code or 1
    return {"returncode": code, "stdout": out, "stderr": err + note, "end": "success" if code == 0 else "failure",
            "termination": "confirmed" if confirmed else "unconfirmed"}


def record(wf_name: str, step: dict, cmd: list[str], inputs: list[dict], outputs: dict, code: int, created: str,
           label: str, scripts: dict | None = None, release: dict | None = None, digest: str | None = None,
           end: str = "success", termination: str = "confirmed") -> dict:
    plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    status = [label] if code == 0 else [label, "failed"]
    extra = {"parameter_digest": digest} if digest else {}
    if "check" in step:
        extra["check"] = step["check"]  # the declared identity of a check run (A2 fields)
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": f"{wf_name}-{step['id']}-run",
            "artifact_type": "computational-run",
            "objective": f"step {step['id']} of workflow {wf_name}, run by run_workflow.py",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "profiles": {},
                         "plugin_release": release or plugin_release()},
            "provenance": {"producer_skill": "hep-computing", **trace.provenance(), "created": created, "evidence_ids": []},
            "inputs": [], "outputs": [], "status": list(dict.fromkeys(status)), "unresolved_inputs": [],
            "extension": {"input_manifest": inputs, "tools": [{"name": "python", "version": platform.python_version()}],
                          "commands": [" ".join(cmd)], "environment": environment(),
                          "seeds": step.get("seeds", {}), "tolerances": {}, "exit_status": code,
                          "output_hashes": outputs, "argv": list(cmd), "script_sha256": scripts or {},
                          "output_contract": sorted(step.get("outputs", [])), "end_status": end,
                          "termination": termination, "artifact_digest": canonical_digest(outputs), **extra}}


def skip_reason(prev: dict | None, rec: dict, work: Path, replaced: set[str]) -> str | None:
    """None when the step may be skipped (INC-02, INC-03), else why it reruns."""
    if prev is None:
        return "no previous record"
    pe, ne = prev.get("extension") or {}, rec["extension"]
    digest = ((rec.get("versions") or {}).get("plugin_release") or {}).get("digest")
    if not digest or digest == "unknown":
        return "the plugin release digest is unknown (INC-03)"
    if ((prev.get("versions") or {}).get("plugin_release") or {}).get("digest") != digest:
        return "another plugin release"
    for key in ("argv", "script_sha256", "environment", "exit_status"):
        if pe.get(key) != ne.get(key):
            return f"{key} changed"
    if pe.get("parameter_digest") != ne.get("parameter_digest"):
        return "a parameter the step reads changed"
    keep = lambda m: [i for i in m if i.get("path") not in replaced]  # noqa: E731
    if keep(pe.get("input_manifest") or []) != keep(ne["input_manifest"]):
        return "an input changed"
    declared = ne.get("output_contract") or []
    if sorted(pe.get("output_hashes") or {}) != declared or pe.get("output_contract", declared) != declared:
        return "the output contract changed (CACHE-01)"
    if pe.get("termination", "confirmed") != "confirmed":
        return "the previous termination is unconfirmed"
    for path, h in (pe.get("output_hashes") or {}).items():
        if not safe_relative(path) or through_symlink(work, path) or not (work / path).is_file() \
                or sha256(work / path) != h:
            return f"output {path} changed or is missing"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workflow", type=Path)
    ap.add_argument("--work", type=Path, required=True, help="the work folder (created); relative paths resolve here")
    ap.add_argument("--created", help="the created date written into the run records (default: today)")
    ap.add_argument("--dry-run", action="store_true", help="print the order and run nothing")
    ap.add_argument("--incremental", action="store_true",
                    help="skip a step whose previous record matches (INC-02); never when the release digest is unknown")
    ap.add_argument("--receipt-dir", type=Path, help="write one <attempt>.receipt.json per executed step here (B2)")
    ap.add_argument("--attempt-prefix", default="", help="prefix of the attempt id in receipts (default: none)")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    base = {"status_label": args.status, "inputs": {"workflow": str(args.workflow), "work": str(args.work)},
            "defaults_used": [k for k in ("created", "status") if f"--{k}" not in given]}
    if args.attempt_prefix and not safe_relative(args.attempt_prefix + "x"):
        print(json.dumps({"status": "rejected", **base, "error": "--attempt-prefix must stay inside --receipt-dir"},
                         indent=1))
        return exit_code("rejected")
    try:
        wf = load(args.workflow)
        steps = {s["id"]: s for s in wf["steps"]}
        seq = order(wf["steps"])
    except WorkflowError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    if args.receipt_dir is not None:  # an attempt id identifies one attempt: never replace an earlier receipt
        used = [f"{args.attempt_prefix}{sid}" for sid in seq
                if (args.receipt_dir / f"{args.attempt_prefix}{sid}.receipt.json").exists()]
        if used:
            print(json.dumps({"status": "rejected", **base, "order": seq,
                              "error": f"attempt id(s) {used} already have a receipt in {args.receipt_dir}; an "
                                       "attempt id is used once: choose a new --attempt-prefix"}, indent=1))
            return exit_code("rejected")
    if args.dry_run:
        print(json.dumps({"status": "ok", **base, "order": seq}, indent=1))
        return 0
    created = args.created or datetime.date.today().isoformat()
    work = args.work
    try:
        (work / "runs").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(json.dumps({"status": "rejected", **base, "order": seq, "error": f"cannot create {work}: {exc}"}, indent=1))
        return exit_code("rejected")
    subst = {"{python}": sys.executable, "{plugin}": str(PLUGIN), "{workflow}": str(args.workflow.resolve().parent)}
    shown = {"{python}": "python3", "{plugin}": "<plugin root>", "{workflow}": "<workflow>"}
    results, status = [], "ok"
    for sid in seq:
        step = steps[sid]
        outs = list(step.get("outputs", [])) + ([step["stdout"]] if step.get("stdout") else [])
        linked = [p for p in [*step.get("inputs", []), *outs] if through_symlink(work, p)]
        if linked:
            print(json.dumps({"status": "rejected", **base, "order": seq, "steps": results,
                              "error": f"step {sid}: path(s) {linked} pass through a symlink (OUT-01)"}, indent=1))
            return exit_code("rejected")
        missing = [i for i in step.get("inputs", []) if not (work / i).is_file()]
        if missing:
            print(json.dumps({"status": "rejected", **base, "order": seq, "steps": results,
                              "error": f"step {sid}: input(s) {missing} missing in the work folder"}, indent=1))
            return exit_code("rejected")
        inputs = [{"path": i, "sha256": sha256(work / i)} for i in step.get("inputs", [])]

        def fill(arg: str, table: dict) -> str:
            for k, v in table.items():
                arg = arg.replace(k, v)
            return arg
        cmd = [fill(a, subst) for a in step["argv"]]
        rec_cmd = [fill(a, shown) for a in step["argv"]]
        scripts = script_hashes(rec_cmd, cmd, work)
        stdout_path = step.get("stdout")
        if stdout_path:
            rec_cmd += [">", stdout_path]
        release = plugin_release()
        timeout = float(step.get("timeout_s", STEP_TIMEOUT_S))
        digest, replaced = None, set()
        pd = step.get("parameter_digest")
        if isinstance(pd, dict) and isinstance(pd.get("argv"), list):
            q = execute([fill(a, subst) for a in pd["argv"]], work, timeout)
            try:
                digest = json.loads(q["stdout"]).get("parameter_digest")
            except (ValueError, AttributeError):
                digest = None
            if q["end"] != "success" or q["termination"] != "confirmed" or not isinstance(digest, str):
                print(json.dumps({"status": "rejected", **base, "order": seq, "steps": results,
                                  "parameter_digest_termination": q["termination"],
                                  "error": f"step {sid}: the parameter_digest command failed ({q['end']}, termination "
                                           f"{q['termination']}): {q['stdout'][-400:]}"}, indent=1))
                return exit_code("rejected")
            replaced = set(pd.get("replaces", []))
        rec_path = work / "runs" / f"{sid}.computational-run.json"
        if args.incremental:
            try:
                prev = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else None
            except ValueError:
                prev = None
            probe = record(wf.get("workflow", args.workflow.stem), step, rec_cmd, inputs, {}, 0, created, args.status,
                           scripts, release, digest)
            why = skip_reason(prev, probe, work, replaced)
            if why is None:
                results.append({"id": sid, "skipped": True, "exit_status": 0,
                                "outputs": (prev or {}).get("extension", {}).get("output_hashes", {})})
                continue
        before = {o: stat_key(work / o) for o in outs}  # BUG-01: what existed before this run
        started, (t0, cpu0) = datetime.datetime.now(datetime.timezone.utc), usage_now()
        p = execute(cmd, work, timeout)
        t1, cpu1 = usage_now()
        confirmed = p["termination"] == "confirmed"
        if stdout_path and confirmed:
            (work / stdout_path).write_text(p["stdout"], encoding="utf-8")
        outputs, stale = {}, []
        if confirmed:  # an output digest is valid only once termination is confirmed
            for o in step.get("outputs", []):
                f = work / o
                if f.is_file() and not f.is_symlink():
                    if before[o] is not None and stat_key(f) == before[o] and o != stdout_path:
                        stale.append(o)  # left from before, not written by this run
                    else:
                        outputs[o] = sha256(f)
        code = p["returncode"]
        if code == 0 and (len(outputs) != len(step.get("outputs", [])) or not confirmed):
            code = 1  # a step that claims success but did not write its outputs (or whose end is unconfirmed) failed
        bind = check_binding(step, work, inputs, scripts, outputs) if "check" in step and confirmed and code == 0 else None
        if bind is not None and not bind["bound"]:
            code = 1  # an unbound check result is not a result of the declared check
        end = p["end"] if p["end"] != "success" or code == 0 else "failure"
        doc = record(wf.get("workflow", args.workflow.stem), step, rec_cmd, inputs, outputs, code, created, args.status,
                     scripts, release, digest, end=end, termination=p["termination"])
        if bind is not None:
            doc["extension"]["check_result"] = bind
        rec_bytes = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")
        rec_path.write_bytes(rec_bytes)
        if args.receipt_dir is not None:
            attempt = f"{args.attempt_prefix}{sid}"
            receipt = {"attempt": attempt, "step": sid, "end_status": end, "termination": p["termination"],
                       "outputs": [{"logical": o, "location": o, "location_kind": "attempt-owned", "sha256": h}
                                   for o, h in sorted(outputs.items())],
                       "artifact_digest": canonical_digest(outputs),
                       "observed_inputs": {"observable": False, "declared": inputs},
                       "conditions_resolution": None,
                       "environment_ref": {"run_record": f"runs/{sid}.computational-run.json",
                                           "sha256": hashlib.sha256(rec_bytes).hexdigest()},
                       "started": started.isoformat(timespec="seconds"),
                       "ended": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                       "usage": {"wall_s": round(t1 - t0, 3), "cpu_s": round(cpu1 - cpu0, 3)},
                       "check_result": bind}
            rpath = args.receipt_dir / f"{attempt}.receipt.json"
            rpath.parent.mkdir(parents=True, exist_ok=True)
            try:
                with rpath.open("x", encoding="utf-8") as fh:  # exclusive: a concurrent run took the id first
                    fh.write(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
            except FileExistsError:
                print(json.dumps({"status": "rejected", **base, "order": seq, "steps": results,
                                  "error": f"attempt id {attempt} got a receipt from another run while step {sid} "
                                           "ran; its receipt was not written"}, indent=1))
                return exit_code("rejected")
        stderr = p["stderr"] + (f"\n[run_workflow] output(s) {stale} existed before and were not written by this run"
                                if stale else "")
        if bind is not None and not bind["bound"]:
            stderr += "\n[run_workflow] check result not bound to this run: " + "; ".join(bind["problems"])
        results.append({"id": sid, "exit_status": code, "outputs": outputs, "skipped": False, "end_status": end,
                        "termination": p["termination"], "stderr_tail": stderr[-400:] if code else "",
                        **({"check_result": bind} if bind is not None else {})})
        if code != 0:
            status = "failed"
            break
    out = {"status": status, **base, "order": seq, "steps": results}
    if any(r.get("termination") == "unconfirmed" for r in results):
        out["termination"] = "unconfirmed"
    print(json.dumps(out, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
