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
and its outputs still have the recorded hashes. A step may declare "parameter_digest": {"argv": [...], "replaces":
[INPUT, ...]}: the command prints JSON with a parameter_digest (evaluate_design.py run --digest-only), recorded as
extension.parameter_digest, and the listed inputs (candidate files) are then compared by that digest instead of their
file hash, so a change to a parameter the step does not read does not rerun it.
Input: workflow JSON {"workflow": NAME, "steps": [{"id", "needs": [...], "inputs": [...], "outputs": [...],
"argv": [...], "stdout": FILE (optional), "seeds": {...} (optional), "parameter_digest": {...} (optional)}]}.
Usage: run_workflow.py WORKFLOW.json --work DIR [--created YYYY-MM-DD] [--dry-run] [--incremental] [--status LABEL]
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, order and per-step results.
Exit codes: 0 every step ran; 1 a step failed (later steps are not run); 2 bad input (malformed workflow, a cycle, an
unknown dependency, a missing input or output).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # the imports below leave no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import trace  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

STEP_TIMEOUT_S = 3600


class WorkflowError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
        if not isinstance(s.get("argv"), list) or not s["argv"] or not all(isinstance(a, str) for a in s["argv"]):
            raise WorkflowError(f"step {s['id']}: 'argv' must be a non-empty list of strings")
        for key in ("needs", "inputs", "outputs"):
            if not isinstance(s.get(key, []), list):
                raise WorkflowError(f"step {s['id']}: '{key}' must be a list")
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


def record(wf_name: str, step: dict, cmd: list[str], inputs: list[dict], outputs: dict, code: int, created: str,
           label: str, scripts: dict | None = None, release: dict | None = None, digest: str | None = None) -> dict:
    plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    status = [label] if code == 0 else [label, "failed"]
    extra = {"parameter_digest": digest} if digest else {}
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
                          "output_hashes": outputs, "argv": list(cmd), "script_sha256": scripts or {}, **extra}}


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
    for path, h in (pe.get("output_hashes") or {}).items():
        if not (work / path).is_file() or sha256(work / path) != h:
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
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    base = {"status_label": args.status, "inputs": {"workflow": str(args.workflow), "work": str(args.work)},
            "defaults_used": [k for k in ("created", "status") if f"--{k}" not in given]}
    try:
        wf = load(args.workflow)
        steps = {s["id"]: s for s in wf["steps"]}
        seq = order(wf["steps"])
    except WorkflowError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
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
        digest, replaced = None, set()
        pd = step.get("parameter_digest")
        if isinstance(pd, dict) and isinstance(pd.get("argv"), list):
            q = subprocess.run([fill(a, subst) for a in pd["argv"]], cwd=work, capture_output=True, text=True,
                               timeout=STEP_TIMEOUT_S)
            try:
                digest = json.loads(q.stdout).get("parameter_digest")
            except ValueError:
                digest = None
            if q.returncode != 0 or not isinstance(digest, str):
                print(json.dumps({"status": "rejected", **base, "order": seq, "steps": results,
                                  "error": f"step {sid}: the parameter_digest command failed: {q.stdout[-400:]}"}, indent=1))
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
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=STEP_TIMEOUT_S)
        if stdout_path:
            (work / stdout_path).write_text(p.stdout, encoding="utf-8")
        outputs = {}
        for o in step.get("outputs", []):
            if (work / o).is_file():
                outputs[o] = sha256(work / o)
        code = p.returncode
        if code == 0 and len(outputs) != len(step.get("outputs", [])):
            code = 1  # a step that claims success but did not write its outputs failed
        doc = record(wf.get("workflow", args.workflow.stem), step, rec_cmd, inputs, outputs, code, created, args.status,
                     scripts, release, digest)
        rec_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        results.append({"id": sid, "exit_status": code, "outputs": outputs, "skipped": False,
                        "stderr_tail": p.stderr[-400:] if code else ""})
        if code != 0:
            status = "failed"
            break
    print(json.dumps({"status": status, **base, "order": seq, "steps": results}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
