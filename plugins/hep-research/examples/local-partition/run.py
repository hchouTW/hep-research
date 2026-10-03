#!/usr/bin/env python3
"""T21: local partition, failure, bounded resubmission and merge of a SYNTHETIC event-histogram job.

The job draws cos theta from 1 + cos^2 theta (inverse transform) for 200,000 synthetic events in 10 chunks and fills
a 12-bin histogram plus a floating-point sum. Failures are injected: chunk c0002 fails once (transient), chunk c0004
fails with the same error until its cause is fixed. The run shows, in order:
  1. no run configuration -> no retries; failed chunks are recorded and the merge is 'incomplete' (missing work found)
  2. resubmission with max_attempts = 3 -> finished chunks are not rerun (no double counting), c0002 recovers,
     c0004 stops after two identical failures with its state kept
  3. the cause of c0004 is fixed, its state is reset with a reason, and a final resubmission completes the job
  4. merged and single-run results agree (counts exactly, the floating sum within the declared tolerance)
  5. a stray duplicate chunk file and a chunk from another manifest are detected at merge and not counted

Usage (from the plugin root): python3 examples/local-partition/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy (D5 environment).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / "skills" / "hep-computing" / "scripts"))
import local_partition as lp  # noqa: E402

EDGES = np.linspace(-1.0, 1.0, 13)
N_ITEMS, CHUNK, SEED = 200_000, 20_000, 20261005
TOLERANCE = {"counts": 0, "sum_cos_abs": 1e-9}


def sample(rng, n):
    """Inverse transform for f(c) = 3/8 (1 + c^2): F(c) = (c^3 + 3c + 4) / 8, solved with Cardano."""
    u = rng.uniform(size=n)
    q = 4.0 - 8.0 * u
    d = np.sqrt(q * q / 4.0 + 1.0)
    return np.cbrt(-q / 2.0 + d) + np.cbrt(-q / 2.0 - d)


def compute(chunk):
    rng = np.random.default_rng(chunk["seed"])
    c = sample(rng, chunk["stop"] - chunk["start"])
    return {"counts": np.histogram(c, bins=EDGES)[0].tolist(), "n": int(c.size), "sum_cos": float(c.sum())}


class Worker:
    """compute() with injected failures; counts calls per chunk."""

    def __init__(self, transient=(), persistent=()):
        self.calls, self.transient, self.persistent = {}, set(transient), set(persistent)

    def __call__(self, chunk):
        cid = chunk["id"]
        self.calls[cid] = self.calls.get(cid, 0) + 1
        if cid in self.persistent:
            raise OSError(f"input file for {cid} not found (synthetic injected failure)")
        if cid in self.transient:
            self.transient.discard(cid)
            raise TimeoutError(f"{cid} timed out (synthetic transient failure)")
        return compute(chunk)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = lp.make_manifest("synthetic-angular-histogram", N_ITEMS, CHUNK, SEED)
    log = {}
    with tempfile.TemporaryDirectory() as td:
        state = Path(td) / "state"
        w = Worker(transient={"c0002"}, persistent={"c0004"})
        r1 = lp.run(manifest, state, w)
        m1 = lp.merge(manifest, state)
        log["1_no_config"] = {"not_done": r1["not_done"], "calls": dict(w.calls), "merge_status": m1["status"],
                              "missing": next(p["chunks"] for p in m1["problems"] if p["code"] == "merge.missing_chunks"),
                              "retries_configured": r1["retries_configured"]}
        w.calls.clear()
        r2 = lp.run(manifest, state, w, {"max_attempts": 3})
        log["2_resubmit_max3"] = {"not_done": r2["not_done"], "calls": dict(w.calls),
                                  "c0004": r2["chunks"]["c0004"], "skipped_done": len(r2["skipped_done"])}
        w.calls.clear()
        r2b = lp.run(manifest, state, w, {"max_attempts": 3})
        log["2b_resubmit_again_unfixed"] = {"calls": dict(w.calls), "c0004_status": r2b["chunks"]["c0004"]["status"]}
        w.persistent.clear()
        lp.reset(state, ["c0004"], "input path fixed (synthetic)")
        w.calls.clear()
        r3 = lp.run(manifest, state, w, {"max_attempts": 3})
        merged = lp.merge(manifest, state)
        log["3_after_fix"] = {"complete": r3["complete"], "calls": dict(w.calls), "merge_status": merged["status"]}

        single = [compute(c) for c in manifest["chunks"]]
        s_counts = np.sum([s["counts"] for s in single], axis=0).tolist()
        s_sum = float(np.sum([s["sum_cos"] for s in reversed(single)]))
        agree = {"counts_equal": merged["merged"]["counts"] == s_counts, "n_equal": merged["merged"]["n"] == N_ITEMS,
                 "sum_cos_abs_diff": abs(merged["merged"]["sum_cos"] - s_sum)}

        files = sorted((state / "chunks").glob("*.json"))
        shutil.copy(files[3], state / "chunks" / "zz-stray-copy.json")
        foreign = lp.make_manifest("other-job", N_ITEMS, CHUNK, SEED + 1)
        doc = json.loads(files[0].read_text())
        doc["manifest_hash"] = foreign["manifest_hash"]
        (state / "chunks" / "zz-foreign.json").write_text(json.dumps(doc))
        m5 = lp.merge(manifest, state)
        log["5_stray_files"] = {"status": m5["status"], "chunks_merged": m5["chunks_merged"], "codes": sorted({p["code"] for p in m5["problems"]}),
                                "counts_unchanged": m5["merged"]["counts"] == merged["merged"]["counts"]}
        state_kept = json.loads((state / "state.json").read_text())

    expected_counts = None  # independent reference: expected fraction per bin from the analytic CDF
    cdf = (EDGES ** 3 + 3 * EDGES + 4) / 8
    expected_counts = (N_ITEMS * np.diff(cdf)).tolist()
    pulls = ((np.array(merged["merged"]["counts"]) - expected_counts) / np.sqrt(expected_counts)).tolist()

    passes = {
        "no_retry_without_config": log["1_no_config"]["calls"].get("c0002") == 1 and log["1_no_config"]["calls"].get("c0004") == 1
                                   and not log["1_no_config"]["retries_configured"],
        "missing_work_detected": log["1_no_config"]["merge_status"] == "incomplete" and log["1_no_config"]["missing"] == ["c0002", "c0004"],
        "finished_chunks_not_rerun": set(log["2_resubmit_max3"]["calls"]) == {"c0002", "c0004"} and log["2_resubmit_max3"]["skipped_done"] == 8,
        "transient_failure_recovered": "c0002" not in log["2_resubmit_max3"]["not_done"],
        "repeated_identical_failure_stops": log["2_resubmit_max3"]["c0004"]["status"] == "stopped-repeated-failure"
                                            and log["2_resubmit_max3"]["calls"]["c0004"] == 1
                                            and log["2b_resubmit_again_unfixed"]["calls"] == {},
        "state_retained": len(state_kept.get("resets", [])) == 1 and bool(state_kept["resets"][0]["errors"]),
        "completes_after_fix": log["3_after_fix"]["complete"] and log["3_after_fix"]["calls"] == {"c0004": 1}
                               and log["3_after_fix"]["merge_status"] == "complete",
        "merged_equals_single_run": agree["counts_equal"] and agree["n_equal"] and agree["sum_cos_abs_diff"] <= TOLERANCE["sum_cos_abs"],
        "duplicates_and_foreign_chunks_rejected": log["5_stray_files"]["codes"] == ["merge.duplicate_chunk", "merge.foreign_chunk"]
                                                  and log["5_stray_files"]["counts_unchanged"] and log["5_stray_files"]["chunks_merged"] == 10,
        "histogram_matches_analytic_shape": float(np.sum(np.square(pulls))) < 3 * len(pulls),
    }
    res = {"label": "SYNTHETIC job; injected failures", "manifest": {k: manifest[k] for k in ("job_id", "n_items", "chunk_size", "seed", "manifest_hash")},
           "tolerance": TOLERANCE, "pass": passes, "log": log, "agreement": agree, "merged": merged["merged"],
           "expected_counts": expected_counts, "chi2_vs_analytic": float(np.sum(np.square(pulls))), "ndf": len(pulls)}
    (args.out / "results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({"pass": passes}, indent=1))
    return 0 if all(passes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
