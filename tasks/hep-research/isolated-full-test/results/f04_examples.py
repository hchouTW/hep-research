#!/usr/bin/env python3
"""F04: run each example twice into a scratch directory; compare the two runs byte for byte, then compare with the
committed output (byte for byte, else results.json numerically at rel 1e-9 / abs 1e-12). Not part of the plugin.

usage: f04_examples.py PLUGIN_DIR SCRATCH_DIR OUT_JSON   (run with the E2 venv Python)
"""
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

PLUGIN, SCRATCH, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
# arguments as used by tests/examples/*; end-to-end-sample has no committed output
EXAMPLES = {name: ["--out"] for name in ("ams-flux-ratio", "batch-partition", "collider-angular", "detector-resolution",
                                         "local-partition", "published-comparison", "qed-prediction", "recasting",
                                         "theory-comparison")}
EXAMPLES["end-to-end-sample"] = ["--seed", "1", "--outdir"]


def files(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def numeric_diffs(a, b, path="$", out=None):
    out = [] if out is None else out
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)):
            out.append(f"{path}: {a!r} != {b!r}")
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: only in {'run' if k in a else 'committed'}")
            else:
                numeric_diffs(a[k], b[k], f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                numeric_diffs(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(f"{path}: {str(a)[:80]!r} != {str(b)[:80]!r}")
    return out


rows = []
for name, args in EXAMPLES.items():
    script = PLUGIN / "examples" / name / "run.py"
    runs, row = [], {"example": name, "command": f"python examples/{name}/run.py {' '.join(args)} <dir>"}
    for k in (1, 2):
        d = SCRATCH / name / f"run{k}"
        d.mkdir(parents=True, exist_ok=True)
        t = time.time()
        p = subprocess.run([sys.executable, str(script), *args, str(d)], capture_output=True, text=True, cwd=PLUGIN)
        row[f"run{k}_exit"], row[f"run{k}_seconds"] = p.returncode, round(time.time() - t, 1)
        if p.returncode:
            row[f"run{k}_stderr_tail"] = p.stderr[-1500:]
        runs.append(d)
    f1, f2 = files(runs[0]), files(runs[1])
    row["rerun_identical"] = f1 == f2
    row["rerun_differing_files"] = sorted(k for k in set(f1) | set(f2) if f1.get(k) != f2.get(k))
    committed = PLUGIN / "examples" / name / "output"
    if committed.is_dir():
        fc = files(committed)
        row["committed_identical"] = f1 == fc
        row["committed_differing_files"] = sorted(k for k in set(f1) | set(fc) if f1.get(k) != fc.get(k))
        rj, cj = runs[0] / "results.json", committed / "results.json"
        if rj.exists() and cj.exists() and rj.read_bytes() != cj.read_bytes():
            d = numeric_diffs(json.loads(rj.read_text()), json.loads(cj.read_text()))
            row["results_json_numeric_equal"] = not d
            row["results_json_diffs"] = d[:20]
    else:
        row["committed_identical"] = None
    rows.append(row)
    print(name, {k: row[k] for k in ("run1_exit", "run2_exit", "rerun_identical", "committed_identical")},
          row.get("results_json_numeric_equal", ""), flush=True)

OUT.write_text(json.dumps(rows, indent=1) + "\n")
