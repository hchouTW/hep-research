#!/usr/bin/env python3
"""B11: the T21 SYNTHETIC event-histogram job (200,000 events, 10 chunks) as a batch campaign on fake Slurm and
fake HTCondor schedulers (tests/adapters/batch_shims), with injected faults. Per backend, in order:
  1. a dry run makes no scheduler call; then everything is submitted
  2. faults: c0001 runs twice (Slurm: a site-forced requeue; HTCondor: evicted after writing its output), c0003 runs
     out of memory (HTCondor: held for memory), c0004 fails with exit code 3 every time until "fixed"
  3. with no max_attempts nothing is resubmitted
  4. max_attempts 3 and a larger memory request; c0003 resubmitted with the resource change recorded (HTCondor: after
     a reset, since a held job always needs a person); c0004 reset once and resubmitted: the same failure again stops
     it (two identical failures), and resubmit refuses it
  5. the cause of c0004 is fixed, it is reset with a reason and resubmitted; the campaign completes
  6. the merge equals the local single-run merge exactly (counts, n, floating sum); the duplicate is not summed
  7. a computational-run artifact is written and validates; the job logs pass a blinding audit
These are fake schedulers: the example shows the protocol, not real Slurm or HTCondor support.

Usage (from the plugin root): python3 examples/batch-partition/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes for both backends, 1 otherwise. Requires numpy (D5 environment).
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
SHIMS = PLUGIN / "tests" / "adapters" / "batch_shims"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "adapters" / "batch-schedulers"))
import batch_campaign  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.partition import engine  # noqa: E402

spec = importlib.util.spec_from_file_location("t21", PLUGIN / "examples" / "local-partition" / "run.py")
t21 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t21)

FAULTS = {
    "slurm": {"c0001": [{"kind": "requeue-duplicate"}], "c0003": [{"kind": "oom"}],
              "c0004": [{"kind": "exit", "code": 3}, {"kind": "exit", "code": 3}]},
    "htcondor": {"c0001": [{"kind": "evict-after-output"}],
                 "c0003": [{"kind": "hold", "reason": "Job exceeded its memory request (synthetic)", "code": 34, "subcode": 0}],
                 "c0004": [{"kind": "exit", "code": 3}, {"kind": "exit", "code": 3}]},
}
SEALED = 987654.321  # a stand-in "blinded" number that no output of this synthetic job contains


def campaign(backend: str, root: Path, manifest: dict) -> dict:
    work = root / backend
    work.mkdir()
    cfg = json.loads((HERE / f"batch-config.{backend}.json").read_text())
    faults = work / "faults.json"
    faults.write_text(json.dumps(FAULTS[backend]))
    calls = work / "calls.jsonl"
    env = dict(os.environ, PATH=f"{SHIMS}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
               HEP_BATCH_SHIM_STATE=str(work / "store"), HEP_BATCH_SHIM_LOG=str(calls), HEP_BATCH_SHIM_FAULTS=str(faults))
    (work / "manifest.json").write_text(json.dumps(manifest))
    q = shlex.quote
    cmd = f"{q(sys.executable)} {q(str(HERE / 'worker.py'))} --start {{start}} --stop {{stop}} --seed {{seed}} --out {{out}} --id {{id}}"

    def write(c):
        (work / "config.json").write_text(json.dumps(c))

    def cli(*a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = batch_campaign.main([a[0], "--config", str(work / "config.json"), *a[1:]], env=env)
        return code, json.loads(buf.getvalue())

    def n_calls():
        return len(calls.read_text().splitlines()) if calls.exists() else 0

    def records(cid):
        st = json.loads((work / "campaign" / "state.json").read_text())
        return st["chunks"][cid]["attempt_records"]

    write(cfg)
    log = {}
    cli("plan", "--manifest", str(work / "manifest.json"), "--cmd", cmd)
    cli("submit")
    log["1_dry_run_calls"] = n_calls()
    cli("submit", "--submit")
    _, s1 = cli("status")
    log["2_first_status"] = {c: r["status"] for c, r in s1["chunks"].items() if r["status"] != "done"}
    log["2_duplicates"] = s1["duplicates"]
    _, r0 = cli("resubmit", "--submit")
    log["3_no_max_attempts"] = {"resubmitted": r0["resubmitted"], "blocked": {c: d["decision"] for c, d in r0["blocked"].items()}}
    cfg = dict(cfg, max_attempts=3, resources=dict(cfg["resources"], memory_mb=2000))
    write(cfg)
    if backend == "htcondor":
        cli("reset", "--chunks", "c0003", "--reason", "memory request raised after the hold (synthetic)")
    cli("reset", "--chunks", "c0004", "--reason", "input checked, retry once (synthetic)")
    _, r1 = cli("resubmit", "--submit")
    _, s2 = cli("status")
    _, r2 = cli("resubmit", "--submit")
    log["4_resubmit"] = {"resubmitted": r1["resubmitted"], "c0004_after": s2["chunks"]["c0004"]["status"],
                         "c0004_attempts": s2["chunks"]["c0004"]["attempts"],
                         "again": {"resubmitted": r2["resubmitted"], "c0004": r2["blocked"].get("c0004", {}).get("decision")}}
    log["4_c0003_resource_change"] = records("c0003")[-1]["resource_change"]
    cli("reset", "--chunks", "c0004", "--reason", "input path fixed (synthetic)")
    _, r3 = cli("resubmit", "--submit")
    code, s3 = cli("status")
    log["5_after_fix"] = {"resubmitted": r3["resubmitted"], "complete": s3["complete"], "exit": code}
    _, merged = cli("merge")
    log["attempts"] = {c: [r["final_state"] for r in records(c)] for c in ("c0001", "c0003", "c0004")}
    out = work / "artifact.json"
    acode, _ = cli("report", "--out", str(out), "--label", "synthetic", "--objective",
                   "SYNTHETIC batch-partition example on a fake scheduler")
    art = json.loads(out.read_text())
    sealed = root / f"{backend}-sealed.json"
    sealed.write_text(json.dumps({"sealed": [SEALED], "region": {"low": 0, "high": 1}}))
    audit = subprocess.run([sys.executable, str(PLUGIN / "skills" / "hep-computing" / "scripts" / "audit_blinded_outputs.py"),
                            "scan", "--sealed", str(sealed), str(work / "campaign" / "submissions"), str(work / "campaign" / "outputs")],
                           capture_output=True, text=True)
    tools = {}
    for line in calls.read_text().splitlines():
        t = json.loads(line)["tool"]
        tools[t] = tools.get(t, 0) + 1
    log["scheduler_calls"] = dict(sorted(tools.items()))
    return {"log": log, "merged": merged, "artifact": art, "artifact_exit": acode, "audit_exit": audit.returncode}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = engine.make_manifest("synthetic-angular-histogram", t21.N_ITEMS, t21.CHUNK, t21.SEED)
    with tempfile.TemporaryDirectory(prefix="hepbatch") as td:
        root = Path(td)
        local_state = root / "local"
        engine.run(manifest, local_state, t21.compute)
        local = engine.merge(manifest, local_state)["merged"]
        runs = {b: campaign(b, root, manifest) for b in ("slurm", "htcondor")}
    passes, summary = {}, {}
    for b, r in runs.items():
        lg, m, art = r["log"], r["merged"], r["artifact"]
        p = {
            "dry_run_makes_no_scheduler_call": lg["1_dry_run_calls"] == 0,
            "faults_seen_on_first_poll": sorted(lg["2_first_status"]) == ["c0003", "c0004"],
            "no_resubmission_without_max_attempts": lg["3_no_max_attempts"]["resubmitted"] == []
                                                     and sorted(lg["3_no_max_attempts"]["blocked"]) == ["c0003", "c0004"],
            "duplicate_recorded_not_summed": lg["2_duplicates"] == 1 and lg["attempts"]["c0001"][0] == "preempted-or-evicted",
            "memory_failure_resubmitted_with_resource_change": lg["4_c0003_resource_change"] is not None
                and lg["4_c0003_resource_change"]["from"]["memory_mb"] == 1000 and lg["4_c0003_resource_change"]["to"]["memory_mb"] == 2000,
            "repeated_identical_failure_stops": lg["4_resubmit"]["c0004_after"] == "stopped-repeated-failure"
                and lg["4_resubmit"]["c0004_attempts"] == 2 and lg["4_resubmit"]["again"]["resubmitted"] == []
                and lg["4_resubmit"]["again"]["c0004"] == "stopped-repeated-failure",
            "completes_after_fix_and_reset": lg["5_after_fix"] == {"resubmitted": ["c0004"], "complete": True, "exit": 0},
            "merged_equals_local_exactly": m["status"] == "complete" and m["merged"] == local,
            "artifact_validates_and_is_labeled_synthetic": validate_artifact(art).ok and "synthetic" in art["status"]
                and "failed" not in art["status"] and r["artifact_exit"] == 0,
            "job_logs_pass_the_blinding_audit": r["audit_exit"] == 0,
        }
        passes[b] = p
        summary[b] = dict(lg, merge_status=m["status"], chunks_merged=m["chunks_merged"],
                          artifact_status=art["status"], scheduler_tool=art["extension"]["tools"][0])
    res = {"label": "SYNTHETIC job on FAKE schedulers (tests/adapters/batch_shims); injected faults; not real Slurm or HTCondor",
           "manifest": {k: manifest[k] for k in ("job_id", "n_items", "chunk_size", "seed", "manifest_hash")},
           "tolerance": {"merge": "exact equality with the local single-run merge"},
           "pass": passes, "log": summary, "merged_local": local}
    (args.out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"pass": passes}, indent=1))
    return 0 if all(all(p.values()) for p in passes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
