"""The task environment of a merged phase-5 study file (A33, review F10): the interpreter, NumPy and file hashes each
Slurm task recorded in its own `provenance`, so a merged file states what the tasks ran with, not only the merging
process's `provenance`. Used by the merges of simcal_phase5_{g4l,pooling_s2,vmodel_s3,tv}.py; reported, never
a part of a study's registered decision rule."""
from __future__ import annotations

import json


def task_environment(records) -> dict:
    """{python, numpy, sha256, agree, n_tasks}: the distinct (python, numpy) pairs and file-hash sets of the task
    records (None entries, missing tasks, skipped). agree: one pair and one hash set over every task; sha256: that
    set when they agree, else None (the distinct sets under sha256_sets)."""
    recs = [r for r in records if r]
    prov = [r.get("provenance") or {} for r in recs]
    envs = sorted({(p.get("python"), p.get("numpy")) for p in prov}, key=repr)
    shas = sorted({json.dumps(p.get("sha256"), sort_keys=True) for p in prov})
    agree = len(envs) == 1 and len(shas) == 1
    out = {"n_tasks": len(recs), "python": sorted({str(e[0]) for e in envs}),
           "numpy": sorted({str(e[1]) for e in envs}), "agree": agree,
           "sha256": json.loads(shas[0]) if agree else None,
           "note": "from the task records; `provenance` is the merging process's"}
    if not agree:
        out["sha256_sets"] = [json.loads(s) for s in shas]
    return out
