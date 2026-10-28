#!/usr/bin/env python3
"""cr-propagation E1: Sobol training design, provider runs through local_partition, bounded active addition (r3 E1).

What it does (run outputs stay in --work-dir, which is $CRPROP_OUT/e1; only the design file and the summary, with
per-point hashes and computational-run references, are written into this folder, r3 E1 and E1-3):
1. Design. N0 points of a scrambled Sobol sequence (scipy.stats.qmc, seed DESIGN_SEED) in the unit cube of the free
   parameters, mapped to the box FREE_PARAMETERS (D0_cm2_s on a log axis, the others linear). N0 = 10 x the number of
   free parameters rounded up to a power of 2 and k = N0/10 rounded to the nearest integer (decision Q9). The
   design's minimum distance d_min is the smallest pairwise distance of the N0 points in the unit cube.
2. Runs. Every batch of points (design, truth, hold-out, each round's additions) is run through
   skills/hep-computing/scripts/local_partition.py (decision D6: no batch client on this host), one chunk per point,
   in at most 4 shards at once; each chunk calls the registered provider through core/provider (ProviderRunner, cache
   under --work-dir/cache) and USINE keeps one computational-run record per point under HEP_USINE_RUN_DIR. A point
   whose provider result is not ok is recorded with its reason; more than 5% failures in the design stops (E1-1).
   Provider evaluations (points sent to the provider, not cache hits) are tallied in --work-dir/tally.json; a batch
   that would pass --max-evaluations is not started (status stopped, reason cost-cap).
3. Synthetic data. B/C on SYNTHETIC_BINS rigidity bins, the provider's value at TRUTH (an Asimov dataset, labelled
   synthetic), with an ILLUSTRATIVE covariance: statistical sigma_i = STAT_REL (R_i / 10 GV)^STAT_SLOPE times the
   value (uncorrelated) plus a systematic SYST_REL times the value with a Gaussian correlation of length SYST_CORR_LEN
   in log10 R. Never a real dataset; it only drives the loop.
4. Placeholder emulator (E2 replaces it; see "What E2 replaces"): scipy RBFInterpolator (thin-plate spline, degree 1)
   of ln(B/C) per bin on the unit-cube coordinates; its error estimate at a point is the jackknife spread over
   N_FOLDS models each trained without one fold (fold = training index mod N_FOLDS).
5. Active-addition loop (Plan-and-Solve), each round: fit the synthetic data with the current emulator (least squares
   in the unit cube from the best CANDIDATE points); the 95% posterior region is approximated by the candidates
   (N_CANDIDATES Sobol points, seed CANDIDATE_SEED) with emulator delta chi2 <= chi2_0.95(n_free) from the best fit
   (flat prior in the box, Gaussian likelihood); pick the k candidates of largest estimated error max_i |e_i| /
   sigma_stat_i, each at least d_min from the picks before it; run them with the original provider; retrain.
   Termination: both E2 criteria on the hold-out set (E2-1: every hold-out point has delta chi2 = b^T C^-1 b <= 1 with
   C the full synthetic covariance and b emulator minus provider; E2-2: every bin |b_i| <= 0.2 sigma_stat_i). The
   hold-out is HOLDOUT_SIZE points of the round-0 posterior region (Sobol subsample, seed HOLDOUT_SEED), fixed for
   all rounds and never trained on. Maximum rounds: 5 (then status max-rounds, with the best emulator and its
   failing bins). Early stop: the largest hold-out error max |b_i|/sigma_stat_i falls by less than 10% for 2
   consecutive rounds (early-stop-error-plateau), or every pick lies closer to an existing training point than
   d_min (early-stop-min-distance; those picks are not run). Cost cap: --max-evaluations.
   --forced-max-rounds-test (E1-2) sets both termination thresholds to 0 and switches the two early-stop rules off,
   so the loop must end at the maximum number of rounds and say so; with the cache it reruns no point already run.

What E2 replaces: the placeholder emulator (hep-ml model with an ml-artifact, training_domain, extrapolation_policy
and regression_validation, domain judged by DomainModel of check_surrogate_domain.py), the candidate-cloud
approximation of the posterior region (a posterior through the emulator provider of E2b), and the hold-out and
covariance used for termination (E2's hold-out and the real data covariance). The design, the run records and the
loop limits stay.

Usage (from the plugin root; NumPy and SciPy needed):
  python3 tests/adapters/fixtures/cr_propagation/e1/active_addition.py run --work-dir "$CRPROP_OUT/e1"
      --registry REGISTRY.json [--summary FILE] [--design FILE] [--max-rounds 5] [--max-evaluations 1500] [--jobs 4]
      [--forced-max-rounds-test]
  python3 .../active_addition.py evaluate --points POINTS.json --registry REGISTRY.json --cache-dir DIR
      --start I --stop J --out OUT.json        (the local_partition chunk command)
Environment: HEP_USINE_BIN, HEP_USINE_DATA (provider), HEP_USINE_RUN_DIR is set to --work-dir/runs.
Exit codes: 0 loop ended (converged, max-rounds or an early stop), 1 stopped (failures over 5%, cost cap, a batch
that did not complete), 2 bad input or NumPy/SciPy missing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import numpy as np
    from scipy.interpolate import RBFInterpolator
    from scipy.optimize import least_squares
    from scipy.spatial.distance import cdist, pdist
    from scipy.stats import chi2 as chi2_dist
    from scipy.stats import qmc
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
sys.path.insert(0, str(PLUGIN))

PROVIDER_ID = "usine"
FREE_PARAMETERS = (("D0_cm2_s", 1.0e28, 1.0e29, "log"), ("delta", 0.3, 0.8, "linear"), ("eta", -1.5, 1.5, "linear"),
                   ("V_A_kms", 0.0, 100.0, "linear"), ("V_c_kms", 0.0, 30.0, "linear"))
TRUTH = {"D0_cm2_s": 3.0e28, "delta": 0.5, "eta": 1.0, "V_A_kms": 30.0, "V_c_kms": 5.0}
DESIGN_SEED, CANDIDATE_SEED, HOLDOUT_SEED = 20261028, 20261029, 20261030
N_CANDIDATES, HOLDOUT_SIZE, N_FOLDS = 8192, 16, 8
SYNTHETIC_BINS = {"axis": "rigidity", "unit": "GV", "lo": 2.0, "hi": 1000.0, "n": 20}
STAT_REL, STAT_SLOPE, SYST_REL, SYST_CORR_LEN = 0.015, 0.4, 0.02, 0.3
MAX_ROUNDS, PLATEAU_FRACTION, PLATEAU_ROUNDS, POSTERIOR_LEVEL = 5, 0.10, 2, 0.95
DCHI2_MAX, BIN_SIGMA_MAX = 1.0, 0.2           # E2-1, E2-2
FAILURE_LIMIT = 0.05                          # E1-1
MAX_JOBS = 4
PASSTHROUGH = ("HEP_USINE_BIN", "HEP_USINE_DATA", "HEP_USINE_RUN_DIR", "USINE", "ROOT_INCLUDE_PATH", "ROOTSYS",
               "DYLD_LIBRARY_PATH", "PYTHONDONTWRITEBYTECODE")
SMALL_STEP_TIMEOUT = 600  # s; partition plan/merge handle one shard manifest (milliseconds in practice)
PARTITION = PLUGIN / "skills" / "hep-computing" / "scripts" / "local_partition.py"


# ---------------------------------------------------------------------------------------------- design and request
def design_sizes(n_free: int) -> tuple[int, int]:
    """(N0, k) of decision Q9."""
    n0 = 1 << math.ceil(math.log2(10 * n_free))
    return n0, max(1, round(n0 / 10))


def to_physical(unit_row) -> dict:
    point = {}
    for u, (name, lo, hi, scale) in zip(unit_row, FREE_PARAMETERS):
        if scale == "log":
            point[name] = float(10.0 ** (math.log10(lo) + float(u) * (math.log10(hi) - math.log10(lo))))
        else:
            point[name] = float(lo + float(u) * (hi - lo))
    return point


def to_unit(point: dict) -> list[float]:
    row = []
    for name, lo, hi, scale in FREE_PARAMETERS:
        v = point[name]
        row.append((math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) if scale == "log"
                   else (v - lo) / (hi - lo))
    return row


def bin_edges() -> list[float]:
    b = SYNTHETIC_BINS
    return [b["lo"] * (b["hi"] / b["lo"]) ** (i / b["n"]) for i in range(b["n"] + 1)]


def base_request(provider_version: str) -> dict:
    """The request every point is sent in; the transport block is given in full (every field explicit)."""
    sys.path.insert(0, str(PLUGIN / "adapters" / "cr-propagation" / "assets"))
    import usine_provider  # noqa: E402  (read-only use of the provider's documented default transport)
    edges = bin_edges()
    return {"protocol": "cr-provider/1", "provider": PROVIDER_ID, "provider_version": provider_version,
            "transport": usine_provider.DEFAULT_TRANSPORT, "points": [],
            "observables": [{"id": "B/C", "axis": SYNTHETIC_BINS["axis"], "unit": SYNTHETIC_BINS["unit"],
                             "bins": [[edges[i], edges[i + 1]] for i in range(len(edges) - 1)]}],
            "want": ["lis"], "seed": None}


def synthetic_covariance(values) -> tuple:
    """(sigma_stat, full covariance) of the ILLUSTRATIVE synthetic B/C dataset."""
    edges = bin_edges()
    centre = np.sqrt(np.array(edges[:-1]) * np.array(edges[1:]))
    values = np.asarray(values)
    sigma_stat = STAT_REL * (centre / 10.0) ** STAT_SLOPE * values
    lg = np.log10(centre)
    corr = np.exp(-0.5 * ((lg[:, None] - lg[None, :]) / SYST_CORR_LEN) ** 2)
    syst = SYST_REL * values
    return sigma_stat, np.diag(sigma_stat ** 2) + corr * np.outer(syst, syst)


# ---------------------------------------------------------------------------------------------- partition worker
def evaluate_chunk(args) -> int:
    from core.provider.hashing import canonical_sha256, point_hash
    from core.provider.runner import ProviderRunner
    batch = json.loads(Path(args.points).read_text(encoding="utf-8"))
    records = []
    with ProviderRunner(args.registry, cache_dir=args.cache_dir) as runner:
        for index in range(args.start, args.stop):
            point = batch["points"][index]
            request = dict(batch["request"], points=[point])
            response = runner.evaluate(request)
            res = response["results"][0]
            rec = {"index": index, "point": point, "status": res.get("status"),
                   "point_hash": point_hash(request["transport"], request["provider"], request["provider_version"],
                                            point)}
            if res.get("status") == "ok":
                values = res["predictions"][0]["values"]["values"]
                rec.update(values=values, values_sha256=canonical_sha256(values),
                           computational_run_ref=res["evaluation"].get("computational_run_ref"),
                           labels=res.get("labels", []))
            else:
                rec.update(reason=res.get("reason"), detail=str(res.get("detail", ""))[-300:])
            records.append(rec)
        stats = dict(runner.stats)
    Path(args.out).write_text(json.dumps({"records": records, "points_sent": stats["points_sent"],
                                          "cache_hits": stats["cache_hits"]}), encoding="utf-8")
    return 0


class BatchRunner:
    """Runs batches of points through local_partition.py, keeps the evaluation tally and the cost cap."""

    def __init__(self, work_dir: Path, registry: Path, provider_version: str, max_evaluations: int, jobs: int):
        self.work_dir, self.registry = work_dir, registry
        self.request = base_request(provider_version)
        self.max_evaluations, self.jobs = max_evaluations, max(1, min(MAX_JOBS, jobs))
        self.tally_path = work_dir / "tally.json"
        self.invocation = time.strftime("%Y%m%dT%H%M%S") + f"-{os.getpid()}"
        self.tally = json.loads(self.tally_path.read_text()) if self.tally_path.is_file() else \
            {"provider_evaluations": 0, "cache_hits": 0, "batches": []}

    def run(self, name: str, points: list[dict]) -> list[dict]:
        """One record per point, in order. Raises RuntimeError('cost-cap' or 'incomplete-batch: ...')."""
        if self.tally["provider_evaluations"] + len(points) > self.max_evaluations:
            raise RuntimeError(f"cost-cap: {self.tally['provider_evaluations']} + {len(points)} > "
                               f"{self.max_evaluations} provider evaluations")
        bdir = self.work_dir / "batches" / self.invocation / name  # fresh partition state per invocation: the
        # evaluation tally counts only chunks run now (a reused state would replay old outputs); points already run
        # are answered by the provider cache and counted as cache hits
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / "points.json").write_text(json.dumps({"request": self.request, "points": points}), encoding="utf-8")
        env = dict(os.environ, HEP_USINE_RUN_DIR=str(self.work_dir / "runs"), PYTHONDONTWRITEBYTECODE="1")
        (self.work_dir / "runs").mkdir(parents=True, exist_ok=True)
        shards = [s for s in np.array_split(np.arange(len(points)), self.jobs) if len(s)]
        procs = []
        problems = []
        for j, shard in enumerate(shards):
            sdir = bdir / f"shard{j}"
            sdir.mkdir(exist_ok=True)
            # shard j covers points [first, last]; local_partition items are offsets inside the shard
            first = int(shard[0])
            manifest = sdir / "manifest.json"
            try:  # planning and merging only write small JSON files; the bound is far above any legitimate time and
                # exists so a hung child fails the shard with a reason instead of stalling the campaign
                subprocess.run([sys.executable, str(PARTITION), "plan", "--job", f"e1-{name}-s{j}", "--items",
                                str(len(shard)), "--chunk-size", "1", "--seed", str(j), "--out", str(manifest)],
                               check=True, capture_output=True, text=True, env=env, timeout=SMALL_STEP_TIMEOUT)
            except subprocess.TimeoutExpired:
                problems.append(f"shard{j}: plan timed out after {SMALL_STEP_TIMEOUT} s")
                continue
            shard_points = sdir / "points.json"
            shard_points.write_text(json.dumps({"request": self.request,
                                                "points": points[first:first + len(shard)]}), encoding="utf-8")
            cmd = (f"{sys.executable} {Path(__file__).resolve()} evaluate --points {shard_points} --registry "
                   f"{self.registry} --cache-dir {self.work_dir / 'cache'} --start {{start}} --stop {{stop}} "
                   "--out {out}")
            procs.append((first, sdir, manifest, subprocess.Popen(
                [sys.executable, str(PARTITION), "run", "--manifest", str(manifest), "--state", str(sdir / "state"),
                 "--cmd", cmd, "--timeout", "1800", "--env-passthrough", *[n for n in PASSTHROUGH if n in env]],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)))
        records: list[dict | None] = [None] * len(points)
        sent = hits = 0
        for first, sdir, manifest, proc in procs:
            out, err = proc.communicate()
            (sdir / "run.json").write_text(out + err, encoding="utf-8")
            try:
                merged = subprocess.run([sys.executable, str(PARTITION), "merge", "--manifest", str(manifest),
                                         "--state", str(sdir / "state"), "--rule", "records=concat"],
                                        capture_output=True, text=True, env=env, timeout=SMALL_STEP_TIMEOUT)
            except subprocess.TimeoutExpired:
                problems.append(f"{sdir.name}: merge timed out after {SMALL_STEP_TIMEOUT} s")
                continue
            doc = json.loads(merged.stdout or "{}")
            (sdir / "merge.json").write_text(merged.stdout, encoding="utf-8")
            if proc.returncode != 0 or doc.get("status") != "complete":
                problems.append(f"{sdir.name}: run exit {proc.returncode}, merge {doc.get('status')}")
                continue
            total = doc["merged"]
            for rec in total["records"]:
                rec["index"] += first
                records[rec["index"]] = rec
            sent += int(total["points_sent"])
            hits += int(total["cache_hits"])
        self.tally["provider_evaluations"] += sent
        self.tally["cache_hits"] += hits
        self.tally["batches"].append({"invocation": self.invocation, "batch": name, "points": len(points),
                                      "provider_evaluations": sent, "cache_hits": hits, "problems": problems})
        self.tally_path.write_text(json.dumps(self.tally, indent=1) + "\n", encoding="utf-8")
        if problems or any(r is None for r in records):
            raise RuntimeError("incomplete-batch: " + "; ".join(problems or ["a chunk gave no record"]))
        return records  # type: ignore[return-value]


# ---------------------------------------------------------------------------------------------- placeholder emulator
class JackknifeInterpolationEmulator:
    """Radial-basis interpolation of ln(B/C) per bin; error estimate = jackknife spread over N_FOLDS models, each
    trained without one fold."""

    def __init__(self, unit_points, values):
        x, y = np.asarray(unit_points, float), np.log(np.asarray(values, float))
        self.full = RBFInterpolator(x, y, kernel="thin_plate_spline", degree=1)
        folds = np.arange(len(x)) % N_FOLDS
        self.partial = [RBFInterpolator(x[folds != f], y[folds != f], kernel="thin_plate_spline", degree=1)
                        for f in range(N_FOLDS)]

    def predict(self, unit_points):
        x = np.atleast_2d(np.asarray(unit_points, float))
        return np.exp(self.full(x))

    def spread(self, unit_points):
        """Estimated relative error per bin (jackknife standard deviation of ln(B/C))."""
        x = np.atleast_2d(np.asarray(unit_points, float))
        parts = np.stack([m(x) for m in self.partial])
        return np.sqrt((N_FOLDS - 1) / N_FOLDS * ((parts - parts.mean(axis=0)) ** 2).sum(axis=0))


def fit_and_region(emulator, observed, chol_inv, global_cloud, seed: int):
    """(best unit point, best chi2, candidates inside the approximate 95% posterior region).

    Candidates: the global Sobol cloud plus N_CANDIDATES points drawn from a Gaussian around the best fit with twice
    the Laplace covariance (J^T J)^-1 of the whitened residuals (pseudo-inverse; draws outside the box rejected), so
    that a region much smaller than the box still holds many candidates. Region: delta chi2 <= chi2_0.95(n_free)."""
    def chi2_of(x):
        r = chol_inv @ (observed[None, :] - emulator.predict(x)).T
        return (r ** 2).sum(axis=0)

    def residual(x):
        return chol_inv @ (observed - emulator.predict(x)[0])
    cloud_chi2 = chi2_of(global_cloud)
    best_x, best_c, best_jac = None, math.inf, None
    for start in global_cloud[np.argsort(cloud_chi2)[:3]]:
        sol = least_squares(residual, start, bounds=(0.0, 1.0))
        c = float((sol.fun ** 2).sum())
        if c < best_c:
            best_x, best_c, best_jac = sol.x, c, sol.jac
    cov_unit = np.linalg.pinv(best_jac.T @ best_jac)
    cov_unit = 0.5 * (cov_unit + cov_unit.T)
    vals, vecs = np.linalg.eigh(cov_unit)
    root = vecs @ np.diag(np.sqrt(np.clip(vals, 0.0, 1.0))) * math.sqrt(2.0)
    rng = np.random.default_rng(seed)
    local: list = []
    for _ in range(50):
        draw = best_x[None, :] + rng.standard_normal((N_CANDIDATES, len(best_x))) @ root.T
        local.extend(draw[((draw >= 0.0) & (draw <= 1.0)).all(axis=1)])
        if len(local) >= N_CANDIDATES:
            break
    cands = np.vstack([global_cloud, np.array(local[:N_CANDIDATES]).reshape(-1, len(best_x))])
    cand_chi2 = chi2_of(cands)
    if cand_chi2.min() < best_c:
        best_x, best_c = cands[int(np.argmin(cand_chi2))], float(cand_chi2.min())
    level = chi2_dist.ppf(POSTERIOR_LEVEL, len(FREE_PARAMETERS))
    return best_x, best_c, cands[cand_chi2 - best_c <= level]


def holdout_errors(emulator, holdout_x, holdout_y, sigma_stat, cov_inv):
    b = emulator.predict(holdout_x) - holdout_y
    dchi2 = np.einsum("ji,ik,jk->j", b, cov_inv, b)
    pull = np.abs(b) / sigma_stat[None, :]
    return dchi2, pull


# ---------------------------------------------------------------------------------------------- loop
def run_loop(args) -> int:
    from core.provider.registry import load_registry
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    version = load_registry(args.registry)[PROVIDER_ID].version
    runner = BatchRunner(work, Path(args.registry), version, args.max_evaluations, args.jobs)
    forced = bool(args.forced_max_rounds_test)
    dchi2_max, bin_max = (0.0, 0.0) if forced else (DCHI2_MAX, BIN_SIGMA_MAX)
    n_free = len(FREE_PARAMETERS)
    n0, k = design_sizes(n_free)
    unit = qmc.Sobol(d=n_free, scramble=True, seed=DESIGN_SEED).random(n0)
    d_min = float(pdist(unit).min())
    design_points = [to_physical(u) for u in unit]
    summary = {"work_package": "E1", "mode": "forced-max-rounds-test" if forced else "standard",
               "provider": {"id": PROVIDER_ID, "version": version}, "labels": ["synthetic", "unvalidated"],
               "free_parameters": [{"name": n, "min": lo, "max": hi, "scale": s} for n, lo, hi, s in FREE_PARAMETERS],
               "sizes": {"N0": n0, "k": k, "d_min_unit_cube": d_min, "holdout": HOLDOUT_SIZE,
                         "candidates": N_CANDIDATES, "folds": N_FOLDS},
               "limits": {"max_rounds": args.max_rounds, "termination": {"dchi2_max": dchi2_max,
                                                                         "bin_sigma_stat_max": bin_max},
                          "early_stop": "off (forced test)" if forced else
                          {"plateau_fraction": PLATEAU_FRACTION, "plateau_rounds": PLATEAU_ROUNDS,
                           "min_distance": "every pick closer than d_min to a training point"},
                          "max_evaluations": args.max_evaluations},
               "synthetic_data": {"truth": TRUTH, "bins": SYNTHETIC_BINS, "stat_rel": STAT_REL,
                                  "stat_slope": STAT_SLOPE, "syst_rel": SYST_REL, "syst_corr_len_log10": SYST_CORR_LEN,
                                  "note": "Asimov B/C at the truth point with an ILLUSTRATIVE covariance"},
               "rounds": [], "status": None, "reason": None}

    def keep(rec, role):
        out = {k2: rec.get(k2) for k2 in ("point", "status", "point_hash", "values_sha256", "computational_run_ref",
                                           "reason", "detail") if rec.get(k2) is not None}
        out["role"] = role
        return out

    def finish(status, reason, code):
        summary["status"], summary["reason"] = status, reason
        summary["evaluation_tally"] = {"provider_evaluations_cumulative": runner.tally["provider_evaluations"],
                                       "cache_hits_cumulative": runner.tally["cache_hits"]}
        Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": status, "reason": reason, "summary": str(args.summary),
                          "provider_evaluations_cumulative": runner.tally["provider_evaluations"]}))
        return code

    try:
        design_recs = runner.run("design", design_points)
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    summary["design"] = [keep(r, "design") for r in design_recs]
    if not forced:
        design_doc = {"work_package": "E1", "method": "scipy.stats.qmc.Sobol, scrambled", "seed": DESIGN_SEED,
                      "N0": n0, "k": k, "d_min_unit_cube": d_min, "free_parameters": summary["free_parameters"],
                      "provider": summary["provider"], "transport": "usine_provider.DEFAULT_TRANSPORT, sent in full",
                      "points": [{"unit": [float(v) for v in u], "point": r["point"], "point_hash": r["point_hash"],
                                  "values_sha256": r.get("values_sha256"),
                                  "computational_run_ref": r.get("computational_run_ref"), "status": r["status"]}
                                 for u, r in zip(unit, design_recs)]}
        Path(args.design).write_text(json.dumps(design_doc, indent=1) + "\n", encoding="utf-8")
    failed = [r for r in design_recs if r["status"] != "ok"]
    summary["design_failures"] = {"count": len(failed), "fraction": len(failed) / n0, "limit": FAILURE_LIMIT}
    if len(failed) / n0 > FAILURE_LIMIT:
        return finish("stopped", f"design failures {len(failed)}/{n0} exceed {FAILURE_LIMIT:.0%} (E1-1)", 1)
    train_x = [to_unit(r["point"]) for r in design_recs if r["status"] == "ok"]
    train_y = [r["values"] for r in design_recs if r["status"] == "ok"]

    try:
        truth_rec = runner.run("truth", [dict(TRUTH)])[0]
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    summary["truth"] = keep(truth_rec, "truth")
    if truth_rec["status"] != "ok":
        return finish("stopped", "the truth point failed", 1)
    observed = np.array(truth_rec["values"])
    sigma_stat, cov = synthetic_covariance(observed)
    cov_inv = np.linalg.inv(cov)
    chol_inv = np.linalg.inv(np.linalg.cholesky(cov))
    candidates = qmc.Sobol(d=n_free, scramble=True, seed=CANDIDATE_SEED).random(N_CANDIDATES)

    emulator = JackknifeInterpolationEmulator(train_x, train_y)
    best_x, best_c, inside = fit_and_region(emulator, observed, chol_inv, candidates, CANDIDATE_SEED)
    rng = np.random.default_rng(HOLDOUT_SEED)
    summary["holdout_region_candidates"] = int(len(inside))
    pick = rng.choice(len(inside), size=min(HOLDOUT_SIZE, len(inside)), replace=False)
    holdout_points = [to_physical(u) for u in inside[np.sort(pick)]]
    try:
        hold_recs = runner.run("holdout", holdout_points)
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    summary["holdout"] = [keep(r, "holdout") for r in hold_recs]
    hold_ok = [r for r in hold_recs if r["status"] == "ok"]
    hold_x = np.array([to_unit(r["point"]) for r in hold_ok])
    hold_y = np.array([r["values"] for r in hold_ok])

    history: list[float] = []
    for rnd in range(0, args.max_rounds + 1):
        if rnd > 0:
            # one round: fit with the current emulator, pick k, run them, retrain
            best_x, best_c, inside = fit_and_region(emulator, observed, chol_inv, candidates, CANDIDATE_SEED + rnd)
            # the hold-out is never trained on
            inside = inside[cdist(inside, hold_x).min(axis=1) > 1e-9] if len(hold_x) else inside
            err = (emulator.spread(inside) * emulator.predict(inside) / sigma_stat[None, :]).max(axis=1)
            picks: list[np.ndarray] = []
            for i in np.argsort(-err):
                if len(picks) == k:
                    break
                if all(np.linalg.norm(inside[i] - p) >= d_min for p in picks):
                    picks.append(inside[i])
            dist_to_train = cdist(np.array(picks), np.array(train_x)).min(axis=1) if picks else np.array([])
            info = {"round": rnd, "fit_unit": [float(v) for v in best_x], "fit_point": to_physical(best_x),
                    "fit_chi2": best_c, "region_candidates": int(len(inside)),
                    "picks_estimated_error_max": float(err.max()) if len(err) else None,
                    "picks_min_distance_to_training": [float(v) for v in dist_to_train]}
            if not forced and (not picks or bool((dist_to_train < d_min).all())):
                info["added"] = []
                summary["rounds"].append(info)
                last = summary["rounds"][-2]
                return finish("early-stop-min-distance", f"round {rnd}: every pick lies closer than d_min "
                              f"{d_min:.4f} to a training point (picks not run); best emulator = after round "
                              f"{rnd - 1} (E2-1 met: {last['e2_1_met']}, E2-2 met: {last['e2_2_met']}), failing bins "
                              f"{last['failing_bins']}", 0)
            try:
                recs = runner.run(f"round{rnd}", [to_physical(p) for p in picks])
            except RuntimeError as exc:
                summary["rounds"].append(info)
                return finish("stopped", str(exc), 1)
            info["added"] = [keep(r, f"round{rnd}") for r in recs]
            for r in recs:
                if r["status"] == "ok":
                    train_x.append(to_unit(r["point"]))
                    train_y.append(r["values"])
            emulator = JackknifeInterpolationEmulator(train_x, train_y)
        else:
            info = {"round": 0, "fit_unit": [float(v) for v in best_x], "fit_point": to_physical(best_x),
                    "fit_chi2": best_c, "region_candidates": int(len(inside)), "added": []}
        dchi2, pull = holdout_errors(emulator, hold_x, hold_y, sigma_stat, cov_inv)
        largest = float(pull.max())
        failing_bins = sorted({int(i) for i in np.where((pull > bin_max).any(axis=0))[0]})
        info.update(training_points=len(train_x), holdout_dchi2_max=float(dchi2.max()),
                    holdout_dchi2_median=float(np.median(dchi2)), holdout_pull_max=largest,
                    holdout_pull_max_per_bin=[float(v) for v in pull.max(axis=0)],
                    e2_1_met=bool((dchi2 <= dchi2_max).all()), e2_2_met=bool((pull <= bin_max).all()),
                    failing_bins=failing_bins)
        summary["rounds"].append(info)
        if info["e2_1_met"] and info["e2_2_met"]:
            return finish("converged", f"both E2 criteria met on the hold-out after round {rnd}", 0)
        history.append(largest)
        if not forced and len(history) > PLATEAU_ROUNDS:
            drops = [(history[-i - 1] - history[-i]) / history[-i - 1] for i in range(1, PLATEAU_ROUNDS + 1)]
            if all(d < PLATEAU_FRACTION for d in drops):
                return finish("early-stop-error-plateau", f"round {rnd}: largest hold-out error fell by "
                              f"{', '.join(f'{d:.1%}' for d in reversed(drops))} in the last {PLATEAU_ROUNDS} rounds "
                              f"(< {PLATEAU_FRACTION:.0%}); best emulator = the last one, failing bins {failing_bins}",
                              0)
    last = summary["rounds"][-1]
    return finish("max-rounds", f"maximum of {args.max_rounds} rounds reached without both E2 criteria "
                  f"(E2-1 met: {last['e2_1_met']}, E2-2 met: {last['e2_2_met']}; termination thresholds "
                  f"dchi2 <= {dchi2_max}, |b|/sigma_stat <= {bin_max}); best emulator = after round "
                  f"{args.max_rounds}, failing bins {last['failing_bins']}", 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="design, runs and the active-addition loop")
    r.add_argument("--work-dir", required=True, type=Path)
    r.add_argument("--registry", required=True, type=Path)
    r.add_argument("--summary", type=Path, default=HERE / "summary.json")
    r.add_argument("--design", type=Path, default=HERE / "design.json", help="design file (standard mode only)")
    r.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    r.add_argument("--max-evaluations", type=int, default=1500)
    r.add_argument("--jobs", type=int, default=MAX_JOBS)
    r.add_argument("--forced-max-rounds-test", action="store_true",
                   help="E1-2: termination thresholds 0 and early stops off; must end at --max-rounds")
    e = sub.add_parser("evaluate", help="local_partition chunk command")
    e.add_argument("--points", required=True, type=Path)
    e.add_argument("--registry", required=True, type=Path)
    e.add_argument("--cache-dir", required=True, type=Path)
    e.add_argument("--start", required=True, type=int)
    e.add_argument("--stop", required=True, type=int)
    e.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "error", "error": "NumPy and SciPy are needed"}))
        return 2
    if args.cmd == "evaluate":
        return evaluate_chunk(args)
    if args.max_rounds < 0 or args.max_evaluations < 1:
        print(json.dumps({"status": "error", "error": "--max-rounds >= 0 and --max-evaluations >= 1"}))
        return 2
    return run_loop(args)


if __name__ == "__main__":
    sys.exit(main())
