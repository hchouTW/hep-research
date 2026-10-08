"""Fake Slurm and HTCondor commands for the batch-scheduler tests (B08). Not a scheduler: jobs run synchronously at
submit time, in local subprocesses, and their outcomes can be forced by fault injection.

Environment:
  HEP_BATCH_SHIM_STATE   directory for the fake job store (required)
  HEP_BATCH_SHIM_LOG     file; every call is appended as one JSON line {"tool", "argv"} (so tests can prove that a
                         dry run or a refusal made no scheduler call)
  HEP_BATCH_SHIM_FAULTS  JSON file {chunk_id: [fault, ...], "_global": {tool: mode}}; each run of a chunk consumes
                         the first fault in its list, and an empty list means a normal run.
Chunk faults (Slurm): exit (code), timeout, oom, node-failure, preempt, cancelled, requeue-duplicate (runs twice,
the first record REQUEUED), vanish (no record anywhere), stuck (PENDING forever), native (state: any text).
Chunk faults (HTCondor): exit (code), signal (signal), evict (evicted before output, then rerun), evict-after-output
(ran, evicted, ran again: a duplicate), hold (reason, code, subcode), remove, stuck (idle forever), vanish.
Any fault may carry "node" (the execution host reported). Global modes: sacct unavailable|malformed, squeue
malformed, eventlog missing|malformed, condor_q malformed.

Output formats are those the backends parse; each emitter names the documentation it follows (see the tool facts
table in skills/hep-computing/references/batch-scheduling.md).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION_SLURM = "slurm 0.0.0-shim"
VERSION_CONDOR = "$CondorVersion: 0.0.0-shim (fake scheduler for tests) $"


# ------------------------------------------------------------------ store, log, faults

def _store_path() -> Path:
    return Path(os.environ["HEP_BATCH_SHIM_STATE"]) / "jobs.json"


def load() -> dict:
    p = _store_path()
    return json.loads(p.read_text()) if p.exists() else {"next_id": 1000, "slurm": {}, "condor": {}}


def save(store: dict) -> None:
    _store_path().parent.mkdir(parents=True, exist_ok=True)
    _store_path().write_text(json.dumps(store, indent=1))


def log_call(tool: str, argv: list) -> None:
    p = os.environ.get("HEP_BATCH_SHIM_LOG")
    if p:
        with open(p, "a") as fh:
            fh.write(json.dumps({"tool": tool, "argv": argv}) + "\n")


def _faults() -> tuple[Path | None, dict]:
    p = os.environ.get("HEP_BATCH_SHIM_FAULTS")
    if not p or not Path(p).exists():
        return None, {}
    return Path(p), json.loads(Path(p).read_text())


def take_fault(chunk: str) -> dict:
    path, f = _faults()
    lst = f.get(chunk) or []
    if not lst:
        return {}
    fault = lst.pop(0)
    path.write_text(json.dumps(f, indent=1))
    return fault


def global_mode(tool: str) -> str | None:
    return _faults()[1].get("_global", {}).get(tool)


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ Slurm

def _expand(spec: str) -> list[int]:
    out = []
    for part in spec.split("%")[0].split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def sbatch(argv: list) -> int:
    if "--version" in argv:
        print(VERSION_SLURM)
        return 0
    opts = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else True) for a in argv if a.startswith("--")}
    script = Path(next(a for a in argv if not a.startswith("--")))
    text = script.read_text()
    for line in text.splitlines():
        if line.startswith("#SBATCH --"):
            k, _, v = line[len("#SBATCH "):].partition("=")
            opts.setdefault(k, v or True)
    exec_line = next(l for l in text.splitlines() if l.startswith("exec "))
    toks = shlex.split(exec_line.replace('"${SLURM_ARRAY_TASK_ID}"', "IDX"))
    rows = json.loads(Path(toks[toks.index("--map") + 1]).read_text())
    store = load()
    jid = store["next_id"]
    store["next_id"] += 1
    for idx in _expand(opts["--array"]):
        chunk = next(r["chunk_id"] for r in rows if r["index"] == idx)
        fault = take_fault(chunk)
        kind = fault.get("kind")
        node = fault.get("node", "shim-node-1")
        key = f"{jid}_{idx}"
        task = {"records": [], "queue": None, "name": opts.get("--job-name")}
        store["slurm"][key] = task

        def run_once():
            env = dict(os.environ, SLURM_ARRAY_TASK_ID=str(idx), SLURM_ARRAY_JOB_ID=str(jid), SLURM_JOB_ID=str(jid + 1 + idx))
            out = str(opts.get("--output", "slurm-%A_%a.out")).replace("%A", str(jid)).replace("%a", str(idx))
            err = str(opts.get("--error", out)).replace("%A", str(jid)).replace("%a", str(idx))
            with open(out, "a") as o, open(err, "a") as e:
                return subprocess.run(["bash", str(script)], stdout=o, stderr=e, env=env, timeout=600).returncode

        def rec(state, code="0:0", ran=True):
            task["records"].append({"state": state, "exit": code, "elapsed": "00:00:01", "rss": "20480K" if ran else "", "nodes": node, "ran": ran})

        if kind == "vanish":
            del store["slurm"][key]
        elif kind == "stuck":
            task["queue"] = "PENDING"
        elif kind == "exit":
            rec("FAILED", f"{fault['code']}:0")
        elif kind == "timeout":
            rec("TIMEOUT", "0:0")
        elif kind == "oom":
            rec("OUT_OF_MEMORY", "0:125")
        elif kind == "node-failure":
            rec("NODE_FAIL", "0:0", ran=False)
        elif kind == "preempt":
            rec("PREEMPTED", "0:0")
        elif kind == "cancelled":
            rec("CANCELLED by 0", "0:0", ran=False)
        elif kind == "native":
            rec(fault["state"], fault.get("exit", "0:0"))
        else:
            if kind == "requeue-duplicate":
                run_once()
                rec("REQUEUED", "0:0")
            code = run_once()
            rec("COMPLETED" if code == 0 else "FAILED", f"{code}:0")
    save(store)
    print(jid)
    return 0


def sacct(argv: list) -> int:
    mode = global_mode("sacct")
    if mode == "unavailable":
        print("sacct: error: Slurm accounting storage is disabled", file=sys.stderr)
        return 1
    if mode == "malformed":
        print("this is not sacct output")
        return 0
    name = next((a.split("=", 1)[1] for a in argv if a.startswith("--name=")), None)
    if name is not None:  # reconciliation: tasks by job name
        for key, task in sorted(load()["slurm"].items()):
            if task.get("name") == name:
                state = task["queue"] or (task["records"][-1]["state"] if task["records"] else "PENDING")
                print(f"{key}|{name}|{state}")
        return 0
    jobs = next(a.split("=", 1)[1] for a in argv if a.startswith("--jobs=")).split(",")
    dup = "--duplicates" in argv
    store = load()
    for key, task in sorted(store["slurm"].items()):
        if key.split("_")[0] not in jobs:
            continue
        recs = task["records"] if dup else task["records"][-1:]
        if task["queue"] and not recs:
            print(f"{key}|{task['queue']}|0:0|00:00:00||None assigned")
        for r in recs:
            print(f"{key}|{r['state']}|{r['exit']}|{r['elapsed']}||{r['nodes']}")
            if r["ran"]:
                print(f"{key}.batch|{r['state'].split()[0]}|{r['exit']}|{r['elapsed']}|{r['rss']}|{r['nodes']}")
    return 0


def squeue(argv: list) -> int:
    if global_mode("squeue") == "malformed":
        print("garbage")
        return 0
    jobs = next(a.split("=", 1)[1] for a in argv if a.startswith("--jobs=")).split(",")
    for key, task in sorted(load()["slurm"].items()):
        if key.split("_")[0] in jobs and task["queue"]:
            print(f"{key}|{task['queue']}")
    return 0


def scancel(argv: list) -> int:
    store = load()
    for key in argv:
        task = store["slurm"].get(key)
        if task and task["queue"]:
            task["queue"] = None
            task["records"].append({"state": "CANCELLED by 0", "exit": "0:0", "elapsed": "00:00:00", "rss": "", "nodes": "None assigned", "ran": False})
    save(store)
    return 0


# ------------------------------------------------------------------ HTCondor

def _parse_submit(text: str) -> tuple[dict, tuple]:
    kv, queue = {}, None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"queue\s+(.+?)\s+from\s+(\S+)$", s)
        if m:
            queue = ([v.strip() for v in m.group(1).split(",")], m.group(2))
            continue
        k, _, v = s.partition("=")
        kv[k.strip().lower()] = v.strip()
    return kv, queue


def _event(log: Path, code: str, cluster: int, proc: int, text: str, detail: list[str] = ()) -> None:
    mode = global_mode("eventlog")
    if mode == "missing":
        return
    with open(log, "a") as fh:
        if mode == "malformed":
            fh.write("this is not an event\n...\n")
            return
        fh.write(f"{code} ({cluster:03d}.{proc:03d}.000) {_now()} {text}\n")
        for d in detail:
            fh.write(f"\t{d}\n")
        fh.write("...\n")


def condor_submit(argv: list) -> int:
    path = Path(argv[-1])
    kv, (names, items_path) = _parse_submit(path.read_text())
    items = [l.split() for l in Path(items_path).read_text().splitlines() if l.strip()]
    store = load()
    cluster = store["next_id"]
    store["next_id"] += 1
    iwd = Path.cwd()
    log = Path(kv["log"])
    cl = store["condor"][str(cluster)] = {"log": str(log), "procs": {}, "tag": kv.get("+hepresearchtag", "").strip('"')}
    for proc, values in enumerate(items):
        macros = dict(zip(names, values), Cluster=str(cluster), Process=str(proc), ClusterId=str(cluster), ProcId=str(proc))
        sub = lambda s: re.sub(r"\$\((\w+)\)", lambda m: macros[m.group(1)], s)
        chunk = macros[names[0]]
        fault = take_fault(chunk)
        kind = fault.get("kind")
        node = fault.get("node", "shim-slot1@shim-node-1")
        st = cl["procs"][str(proc)] = {"JobStatus": 1, "ExitCode": None, "ExitBySignal": False, "ExitSignal": None,
                                       "HoldReason": None, "HoldReasonCode": None, "HoldReasonSubCode": None, "NumJobStarts": 0}
        _event(log, "000", cluster, proc, "Job submitted from host: <127.0.0.1:9618?addrs=127.0.0.1-9618>")

        def execute():
            st["NumJobStarts"] += 1
            _event(log, "001", cluster, proc, f"Job executing on host: <{node}>")

        def run():
            args = shlex.split(sub(kv.get("arguments", "").strip('"')))
            exe = sub(kv["executable"])
            transfer = kv.get("should_transfer_files", "NO").upper() == "YES"
            out, err = sub(kv["output"]), sub(kv["error"])
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            if not transfer:
                with open(out, "a") as o, open(err, "a") as e:
                    return subprocess.run([exe, *args], cwd=iwd, stdout=o, stderr=e, timeout=600).returncode
            with tempfile.TemporaryDirectory(prefix="shim-scratch-") as scratch:
                scratch = Path(scratch)
                inputs = [s.strip() for s in sub(kv.get("transfer_input_files", "")).split(",") if s.strip()]
                for f in inputs:
                    shutil.copy(f, scratch / Path(f).name)
                if kv.get("transfer_executable", "true").lower() == "true":
                    shutil.copy(exe, scratch / Path(exe).name)
                    os.chmod(scratch / Path(exe).name, 0o755)
                    exe = f"./{Path(exe).name}"
                before = {p.name for p in scratch.iterdir()}
                with open(out, "a") as o, open(err, "a") as e:
                    code = subprocess.run([exe, *args], cwd=scratch, stdout=o, stderr=e, timeout=600).returncode
                remaps = {}
                for pair in sub(kv.get("transfer_output_remaps", "").strip('"')).split(";"):
                    if "=" in pair:
                        a, b = pair.split("=", 1)
                        remaps[a.strip()] = b.strip()
                for p in scratch.iterdir():
                    if p.is_file() and p.name not in before:
                        dest = Path(remaps.get(p.name, iwd / p.name))
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(p, dest)
                return code

        def terminate(code=None, signal=None):
            detail = [f"(1) Normal termination (return value {code})" if signal is None else f"(0) Abnormal termination (signal {signal})",
                      "Partitionable Resources :    Usage  Request Allocated", "   Memory (MB)          :       20     1000      1000"]
            _event(log, "005", cluster, proc, "Job terminated.", detail)
            st.update(JobStatus=4, ExitCode=code, ExitBySignal=signal is not None, ExitSignal=signal)

        if kind == "vanish":
            del cl["procs"][str(proc)]
        elif kind == "stuck":
            pass
        elif kind == "hold":
            _event(log, "012", cluster, proc, "Job was held.", [fault["reason"], f"Code {fault['code']} Subcode {fault.get('subcode', 0)}"])
            st.update(JobStatus=5, HoldReason=fault["reason"], HoldReasonCode=fault["code"], HoldReasonSubCode=fault.get("subcode", 0))
        elif kind == "remove":
            _event(log, "009", cluster, proc, "Job was aborted.", ["via condor_rm (by user shim)"])
            st["JobStatus"] = 3
        elif kind == "exit":
            execute()
            terminate(code=fault["code"])
        elif kind == "signal":
            execute()
            terminate(signal=fault["signal"])
        else:
            execute()
            if kind == "evict-after-output":
                run()
                _event(log, "004", cluster, proc, "Job was evicted.", ["(0) Job was not checkpointed."])
                execute()
            elif kind == "evict":
                _event(log, "004", cluster, proc, "Job was evicted.", ["(0) Job was not checkpointed."])
                execute()
            terminate(code=run())
    save(store)
    print(f"{cluster}.0 - {cluster}.{len(items) - 1}")
    return 0


def _ads(argv: list, statuses: set) -> int:
    clusters = [a for a in argv if a.isdigit()]
    attrs = argv[argv.index("-attributes") + 1].split(",") if "-attributes" in argv else None
    want = None
    if "-constraint" in argv:
        m = re.match(r'^HepResearchTag == "([^"]*)"$', argv[argv.index("-constraint") + 1])
        want = m.group(1) if m else "\0no-match"
    ads = []
    for c, cl in sorted(load()["condor"].items()):
        if clusters and c not in clusters:
            continue
        if want is not None and cl.get("tag") != want:
            continue
        for p, st in sorted(cl["procs"].items(), key=lambda t: int(t[0])):
            if st["JobStatus"] in statuses:
                ad = dict(st, ClusterId=int(c), ProcId=int(p))
                ads.append({k: v for k, v in ad.items() if attrs is None or k in attrs})
    if ads:
        print(json.dumps(ads, indent=2))
    return 0


def condor_q(argv: list) -> int:
    if global_mode("condor_q") == "malformed":
        print("[ { not json")
        return 0
    return _ads(argv, {1, 2, 5, 6, 7})


def condor_history(argv: list) -> int:
    return _ads(argv, {3, 4})


def condor_rm(argv: list) -> int:
    store = load()
    for jid in argv:
        c, _, p = jid.partition(".")
        st = store["condor"].get(c, {}).get("procs", {}).get(p)
        if st and st["JobStatus"] in (1, 2, 5):
            st["JobStatus"] = 3
            _event(Path(store["condor"][c]["log"]), "009", int(c), int(p), "Job was aborted.", ["via condor_rm (by user shim)"])
            print(f"Job {jid} marked for removal")
    save(store)
    return 0


def condor_version(argv: list) -> int:
    print(VERSION_CONDOR)
    print("$CondorPlatform: shim $")
    return 0


TOOLS = {"sbatch": sbatch, "sacct": sacct, "squeue": squeue, "scancel": scancel, "condor_submit": condor_submit,
         "condor_q": condor_q, "condor_history": condor_history, "condor_rm": condor_rm, "condor_version": condor_version}


def main(tool: str) -> int:
    log_call(tool, sys.argv[1:])
    return TOOLS[tool](sys.argv[1:])
