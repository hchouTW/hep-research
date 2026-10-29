#!/usr/bin/env python3
"""cr-propagation E2: the hep-ml emulator of USINE B/C, its hold-out validation and the synthetic-fit comparison (r3 E2).

Set-up, synthetic data, covariance and run machinery are E1's (tests/adapters/fixtures/cr_propagation/e1/
active_addition.py: FREE_PARAMETERS, TRUTH, SYNTHETIC_BINS, synthetic_covariance, BatchRunner through local_partition,
at most 4 USINE runs at once); E2 replaces E1's placeholder emulator, its candidate-cloud posterior and its hold-out
(VALIDATION CRPROP-E2 states the criteria, fixed before this ran). Run outputs go to --work-dir ($CRPROP_OUT/e2): the
provider cache (E1's cache copied in first, so E1's 111 USINE runs are cache hits, not new evaluations), USINE run
folders with their computational-run records, the models of every round, the tally. Only the final model, its
ml-artifact, the hold-out sets (points, hashes, USINE values, run references) and the summary are written into this
folder; the training values stay in --work-dir (the model file holds the GP weights, not the training table).

Steps:
1. Training set: E1's USINE points (design, hold-out, every active addition) without the truth point, which carries the
   synthetic data. Emulator: skills/hep-ml/scripts/train_emulator.py (Gaussian process per principal component of
   ln B/C, DomainModel), ml-artifact by write_ml_artifact.py (task surrogate, extrapolation_policy reject).
2. Posterior through the emulator provider (adapters/cr-propagation/assets/emulator_provider.py, called by
   core/provider's runner from a registry made by tools/provider_registry.py with the round's model): least-squares
   fit from the box centre, Laplace covariance from the central finite-difference Jacobian, then defensive importance
   sampling (a mixture of 0.7 multivariate t, 5 degrees of freedom, centred at the fit with twice the Laplace
   covariance, and 0.3 uniform on the box; N_PROPOSAL draws) with weights prior x likelihood / proposal; points the
   provider refuses have weight 0. Flat prior on the unit cube, Gaussian likelihood with E1's full covariance.
3. Hold-out: HOLDOUT_SIZE points resampled without replacement from the first posterior (round-0 emulator), run with
   USINE, never trained on. Rounds: E2-1 and E2-2 on the hold-out; if either fails, K_ADD points of the current
   posterior with the largest predicted emulator error max_i sigma_i / sigma_stat_i (each at least MIN_PICK_DISTANCE
   from the others, the training points and the hold-out, unit cube) are run with USINE and the emulator is retrained;
   at most MAX_ROUNDS rounds.
4. Confirmation hold-out: CONFIRM_SIZE points of the final emulator's posterior, run with USINE, evaluated once.
5. E2-3: the synthetic least-squares fit (unit cube, box bounds, start at the centre) through the emulator provider and
   through the USINE provider (at most FIT_USINE_CAP USINE evaluations), Laplace 68.27% intervals at each best fit.
6. The final ml-artifact gains regression_validation (hold-out numbers) and downstream_validation (E2-3).
Every USINE evaluation is tallied in --work-dir/tally.json; a batch that would pass --max-evaluations (500 for E2) is
not started.

Usage (from the plugin root; NumPy and SciPy; HEP_USINE_BIN, HEP_USINE_DATA, USINE, ROOT_INCLUDE_PATH for USINE):
  python3 tests/adapters/fixtures/cr_propagation/e2/emulator_campaign.py run --work-dir "$CRPROP_OUT/e2"
      --e1-cache "$CRPROP_OUT/e1/cache" [--max-evaluations 500] [--jobs 4]
Exit codes: 0 finished (the summary says which criteria passed), 1 stopped (cost cap, a batch that did not complete,
a refused fit), 2 bad input or NumPy/SciPy missing.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
    from scipy.optimize import least_squares
    from scipy.stats import multivariate_t
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
for entry in (str(PLUGIN), str(HERE.parent / "e1"), str(PLUGIN / "adapters" / "cr-propagation" / "assets")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import active_addition as e1  # noqa: E402

HOLDOUT_SIZE, CONFIRM_SIZE, K_ADD, MAX_ROUNDS = 32, 32, 24, 5
MIN_PICK_DISTANCE = 0.02
N_PROPOSAL, DEFENSIVE_FRACTION, T_DOF = 16384, 0.3, 5
POSTERIOR_SEED, HOLDOUT_SEED, PICK_SEED, CONFIRM_SEED, TRAIN_SEED = 20261031, 20261032, 20261033, 20261034, 0
FIT_USINE_CAP, FD_STEP, CHUNK = 300, 0.01, 2048
DCHI2_MAX, BIN_SIGMA_MAX = 1.0, 0.2            # E2-1, E2-2
BEST_FIT_SIGMA, WIDTH_RTOL = 0.2, 0.10          # E2-3
REFUSED_RESIDUAL = 1.0e3
TRAINER = PLUGIN / "skills" / "hep-ml" / "scripts" / "train_emulator.py"
ARTIFACT_WRITER = PLUGIN / "skills" / "hep-ml" / "scripts" / "write_ml_artifact.py"
SPLIT_CHECK = PLUGIN / "skills" / "hep-ml" / "scripts" / "check_split_integrity.py"
REGISTRY_TOOL = PLUGIN / "tools" / "provider_registry.py"
TRANSLATOR = PLUGIN / "adapters" / "cr-propagation" / "assets" / "usine_translate.py"
ARTIFACT_ENV = "HEP_EMULATOR_ML_ARTIFACT"
NAMES = [name for name, *_ in e1.FREE_PARAMETERS]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_json(argv: list[str], cwd: Path | None = None, ok=(0,)) -> dict:
    proc = subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True, cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=3600)
    if proc.returncode not in ok:
        raise RuntimeError(f"{Path(str(argv[0])).name} exit {proc.returncode}: {proc.stdout[-2000:]}{proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------------------------- training
def training_doc(records: list[dict], provider_version: str) -> dict:
    import usine_provider

    edges = e1.bin_edges()
    return {"features": [{"name": n, "min": lo, "max": hi, "scale": s} for n, lo, hi, s in e1.FREE_PARAMETERS],
            "outputs": {"name": "B/C", "count": len(edges) - 1, "transform": "log", "unit": "1", "axis": "rigidity",
                        "edges": edges,
                        "labels": [f"B/C rigidity bin {i} [{edges[i]:.6g}, {edges[i + 1]:.6g}] GV"
                                   for i in range(len(edges) - 1)]},
            "points": [r["point"] for r in records], "values": [r["values"] for r in records],
            "groups": [r["point_hash"] for r in records], "status": ["synthetic", "unvalidated"],
            "context": {"simulator": "USINE V3.5 through the cr-provider/1 provider usine",
                        "provider": "usine", "provider_version": provider_version,
                        "transport": usine_provider.DEFAULT_TRANSPORT,
                        "transport_sha256": e1_canonical(usine_provider.DEFAULT_TRANSPORT),
                        "translator_sha256": sha256_file(TRANSLATOR),
                        "observable": "B/C", "axis": "rigidity", "fixed": {"L_kpc": 4.0}}}


def e1_canonical(document) -> str:
    from core.provider.hashing import canonical_sha256
    return canonical_sha256(document)


def train_round(work: Path, name: str, records: list[dict], provider_version: str, extra: dict | None = None,
                downstream: list | None = None) -> dict:
    """Train in work/models/<name>; write the ml-artifact; return paths and hashes."""
    folder = work / "models" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "training-set.json").write_text(json.dumps(training_doc(records, provider_version)), encoding="utf-8")
    # --max-condition 0: E2's models were trained before the kernel condition bound (K4), so the bound stays off to
    # reproduce them (the trainer's default since K4 is 1e10)
    trained = run_json([TRAINER, "train", "--training-set", "training-set.json", "--out-dir", ".", "--seed",
                        str(TRAIN_SEED), "--max-condition", "0"], cwd=folder)
    write_artifact(folder, extra or {}, downstream)
    return {"folder": folder, "artifact": folder / "emulator.ml-artifact.json", "trained": trained,
            "model_sha256": sha256_file(folder / "emulator-model.json")}


def write_artifact(folder: Path, extra: dict, downstream: list | None) -> None:
    summary = json.loads((folder / "run_summary.json").read_text(encoding="utf-8"))
    summary.pop("training_set", None)
    summary["checkpoint"] = "emulator-model.json"
    summary["extrapolation_policy"] = {
        "action": "reject",
        "consumer": "adapters/cr-propagation/assets/emulator_provider.py: a point the stored DomainModel calls sparse "
                    "or outside (or outside the box) fails with out-of-domain; --allow-outside-validated-range "
                    "evaluates it labelled outside-validated-range",
        "method": "DomainModel of skills/hep-ml/scripts/check_surrogate_domain.py on the unit-cube training points "
                  "(quantile 0.99, k 5)"}
    summary.update(extra)
    (folder / "run_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    argv = [ARTIFACT_WRITER, "--run-summary", "run_summary.json", "--status", "synthetic", "--status", "unvalidated",
            "--output-semantics", "regression-value", "--artifact-id", "ml-emulator-usine-bc-e2",
            "--objective", "Gaussian-process emulator of USINE B/C (20 rigidity bins, 2-1000 GV) in the five transport "
                           "parameters of cr-propagation E2, served as cr-provider/1 provider emulator",
            "--out", "emulator.ml-artifact.json"]
    if (folder / "split-report.json").is_file():
        argv += ["--split-report", "split-report.json"]
    if downstream is not None:
        (folder / "downstream.json").write_text(json.dumps(downstream, indent=1) + "\n", encoding="utf-8")
        argv += ["--downstream", "downstream.json"]
    run_json(argv, cwd=folder)


def round_registry(work: Path, folder: Path, model_sha: str) -> Path:
    base = json.loads((work / "registry.json").read_text(encoding="utf-8"))
    for item in base["providers"]:
        if item["declaration"]["id"] == "emulator":
            item["version"] = f"{item['declaration']['version']}+model.{model_sha[:12]}"
    path = folder / "registry.json"
    path.write_text(json.dumps(base, indent=1) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------------- emulator client
class EmulatorClient:
    """The round's emulator through core/provider (one --serve session), never cached."""

    def __init__(self, registry: Path, artifact: Path, allow_outside: bool = False):
        from core.provider.registry import load_registry
        from core.provider.runner import ProviderRunner

        os.environ[ARTIFACT_ENV] = str(artifact)
        self.version = load_registry(registry)["emulator"].version
        self.runner = ProviderRunner(registry, session="serve", allow_outside=allow_outside)
        self.request = {"protocol": "cr-provider/1", "provider": "emulator", "provider_version": self.version,
                        "points": [], "observables": copy.deepcopy(e1.base_request("0")["observables"]),
                        "want": ["lis"], "seed": None}
        self.calls = 0

    def close(self):
        self.runner.close()

    def evaluate(self, unit_rows) -> list[dict]:
        """Per row {status, values, sigma, labels, reason}."""
        out = []
        rows = np.atleast_2d(unit_rows)
        for start in range(0, len(rows), CHUNK):
            pts = [e1.to_physical(np.clip(u, 0.0, 1.0)) for u in rows[start:start + CHUNK]]
            resp = self.runner.evaluate(dict(self.request, points=pts))
            self.calls += 1
            if not resp.get("results"):
                raise RuntimeError(f"emulator request refused: {resp.get('reason')} {resp.get('detail', '')}")
            for res in resp["results"]:
                if res["status"] != "ok":
                    out.append({"status": "failed", "reason": res.get("reason"), "detail": res.get("detail")})
                    continue
                pred = res["predictions"][0]
                var = np.zeros(len(pred["values"]["values"]))
                for comp in pred["uncertainties"]:
                    var += np.asarray(comp["values"]) ** 2
                out.append({"status": "ok", "values": np.asarray(pred["values"]["values"]), "sigma": np.sqrt(var),
                            "labels": res["labels"], "domain": pred["parameter_point"]["domain_status"]})
        return out


# ---------------------------------------------------------------------------------------------- fit and posterior
class Likelihood:
    def __init__(self, observed):
        self.observed = np.asarray(observed, float)
        self.sigma_stat, self.cov = e1.synthetic_covariance(self.observed)
        self.cov_inv = np.linalg.inv(self.cov)
        self.chol_inv = np.linalg.inv(np.linalg.cholesky(self.cov))

    def residual(self, values):
        return self.chol_inv @ (self.observed - values)

    def errors(self, pred, truth):
        b = np.asarray(pred) - np.asarray(truth)
        return float(b @ self.cov_inv @ b), np.abs(b) / self.sigma_stat


def least_squares_fit(predict, like: Likelihood, start, counter=None):
    """Least squares in the unit cube; predict(rows) -> list of values or None (refused). Jacobian by forward
    differences evaluated as one batch."""
    def resid(u):
        v = predict(np.atleast_2d(u))[0]
        return like.residual(v) if v is not None else np.full(len(like.observed), REFUSED_RESIDUAL)

    def jac(u):
        rows = []
        steps = []
        for j in range(len(u)):
            h = FD_STEP / 10.0 if u[j] + FD_STEP / 10.0 <= 1.0 else -FD_STEP / 10.0
            row = u.copy()
            row[j] += h
            rows.append(row)
            steps.append(h)
        vals = predict(np.array(rows))
        r0 = resid(u)
        cols = []
        for j, v in enumerate(vals):
            rj = like.residual(v) if v is not None else np.full(len(like.observed), REFUSED_RESIDUAL)
            cols.append((rj - r0) / steps[j])
        return np.array(cols).T

    sol = least_squares(resid, np.asarray(start, float), jac=jac, bounds=(0.0, 1.0), x_scale="jac")
    return sol.x, float((sol.fun ** 2).sum()), sol


def laplace(predict, like: Likelihood, u_hat):
    """(covariance in the unit cube, sigma per parameter, J) from the central finite-difference Jacobian (step
    FD_STEP; one-sided at a box edge)."""
    rows, steps = [], []
    for j in range(len(u_hat)):
        lo, hi = u_hat.copy(), u_hat.copy()
        lo[j] = max(0.0, u_hat[j] - FD_STEP)
        hi[j] = min(1.0, u_hat[j] + FD_STEP)
        rows += [lo, hi]
        steps.append(hi[j] - lo[j])
    vals = predict(np.array(rows))
    if any(v is None for v in vals):
        raise RuntimeError("a finite-difference point was refused")
    jmat = np.array([(vals[2 * j + 1] - vals[2 * j]) / steps[j] for j in range(len(u_hat))]).T
    fisher = jmat.T @ like.cov_inv @ jmat
    cov = np.linalg.inv(fisher)
    return cov, np.sqrt(np.diag(cov)), jmat


def emulator_predict(client: EmulatorClient):
    def predict(rows):
        return [r["values"] if r["status"] == "ok" else None for r in client.evaluate(rows)]
    return predict


def posterior(client: EmulatorClient, like: Likelihood, seed: int) -> dict:
    predict = emulator_predict(client)
    u_hat, chi2_hat, sol = least_squares_fit(predict, like, np.full(len(NAMES), 0.5))
    cov, sigma, _ = laplace(predict, like, u_hat)
    rng = np.random.default_rng(seed)
    d = len(NAMES)
    scale = 2.0 * cov + 1e-10 * np.eye(d)
    t = multivariate_t(loc=u_hat, shape=scale, df=T_DOF, seed=rng)
    n_t = int(round((1.0 - DEFENSIVE_FRACTION) * N_PROPOSAL))
    draws = np.vstack([t.rvs(size=n_t), rng.uniform(0.0, 1.0, size=(N_PROPOSAL - n_t, d))])
    q = (1.0 - DEFENSIVE_FRACTION) * t.pdf(draws) + DEFENSIVE_FRACTION * 1.0
    inside = ((draws >= 0.0) & (draws <= 1.0)).all(axis=1)
    draws, q = draws[inside], q[inside]
    results = client.evaluate(draws)
    chi2 = np.array([float((like.residual(r["values"]) ** 2).sum()) if r["status"] == "ok" else np.inf
                     for r in results])
    refused = int(sum(r["status"] != "ok" for r in results))
    logw = -0.5 * (chi2 - chi2_hat) - np.log(q)
    logw[~np.isfinite(chi2)] = -np.inf
    w = np.exp(logw - logw[np.isfinite(logw)].max())
    w[~np.isfinite(logw)] = 0.0
    ess = float(w.sum() ** 2 / (w ** 2).sum())
    wn = w / w.sum()
    mean = wn @ draws
    sd = np.sqrt(wn @ (draws - mean) ** 2)
    sig = np.array([r["sigma"] if r["status"] == "ok" else np.full(len(like.observed), np.inf) for r in results])
    return {"fit_unit": u_hat, "fit_chi2": chi2_hat, "laplace_sigma_unit": sigma, "draws": draws, "weights": wn,
            "ess": ess, "proposal_inside_box": int(inside.sum()), "refused": refused,
            "posterior_mean_unit": mean, "posterior_sd_unit": sd, "emulator_sigma": sig, "fit_success": bool(sol.success)}


def resample(post: dict, n: int, seed: int, exclude=()) -> np.ndarray:
    """n distinct draws resampled without replacement with the posterior weights."""
    rng = np.random.default_rng(seed)
    w = post["weights"].copy()
    for x in exclude:
        w[np.linalg.norm(post["draws"] - x, axis=1) < 1e-12] = 0.0
    if (w > 0).sum() < n:
        raise RuntimeError(f"only {(w > 0).sum()} draws have weight > 0, {n} needed")
    idx = rng.choice(len(w), size=n, replace=False, p=w / w.sum())
    return post["draws"][np.sort(idx)]


def picks(post: dict, like: Likelihood, k: int, avoid: np.ndarray, seed: int) -> np.ndarray:
    """k posterior draws of largest predicted error max_i sigma_i / sigma_stat_i, pairwise and from `avoid` at least
    MIN_PICK_DISTANCE apart (draws resampled with the weights first, so the picks follow the posterior)."""
    rng = np.random.default_rng(seed)
    pool = np.unique(rng.choice(len(post["weights"]), size=8 * N_PROPOSAL // 16, replace=True, p=post["weights"]))
    err = (post["emulator_sigma"][pool] / like.sigma_stat[None, :]).max(axis=1)
    chosen: list[np.ndarray] = []
    for i in pool[np.argsort(-err)]:
        x = post["draws"][i]
        if len(avoid) and np.linalg.norm(avoid - x, axis=1).min() < MIN_PICK_DISTANCE:
            continue
        if any(np.linalg.norm(x - c) < MIN_PICK_DISTANCE for c in chosen):
            continue
        chosen.append(x)
        if len(chosen) == k:
            break
    return np.array(chosen)


def holdout_check(client: EmulatorClient, like: Likelihood, records: list[dict]) -> dict:
    rows = np.array([e1.to_unit(r["point"]) for r in records])
    results = client.evaluate(rows)
    dchi2, pulls, domains = [], [], []
    for res, rec in zip(results, records):
        if res["status"] != "ok":
            dchi2.append(math.inf)
            pulls.append([math.inf] * len(like.observed))
            domains.append(f"refused: {res.get('reason')}")
            continue
        d, p = like.errors(res["values"], rec["values"])
        dchi2.append(d)
        pulls.append(list(p))
        domains.append(res["domain"])
    dchi2, pulls = np.array(dchi2), np.array(pulls)
    return {"dchi2": dchi2.tolist(), "dchi2_max": float(dchi2.max()), "dchi2_median": float(np.median(dchi2)),
            "pull_max": float(pulls.max()), "pull_max_per_bin": pulls.max(axis=0).tolist(),
            "relative_error_max": float(max((abs(res["values"] / np.asarray(rec["values"]) - 1.0)).max()
                                            for res, rec in zip(results, records) if res["status"] == "ok")),
            "domains": domains, "e2_1_met": bool((dchi2 <= DCHI2_MAX).all()),
            "e2_2_met": bool((pulls <= BIN_SIGMA_MAX).all()),
            "failing_bins": sorted({int(i) for i in np.where((pulls > BIN_SIGMA_MAX).any(axis=0))[0]})}


# ---------------------------------------------------------------------------------------------- USINE fit
class UsineFitter:
    """Sequential USINE evaluations through core/provider for the E2-3 fit, with E1's cache and run folders."""

    def __init__(self, work: Path, registry: Path, batch_runner, cap: int):
        from core.provider.runner import ProviderRunner

        os.environ["HEP_USINE_RUN_DIR"] = str(work / "runs")
        self.runner = ProviderRunner(registry, cache_dir=work / "cache")
        self.request = dict(batch_runner.request)
        self.batch_runner, self.cap, self.sent_before = batch_runner, cap, 0
        self.records: list[dict] = []

    def predict(self, rows):
        from core.provider.hashing import point_hash
        if self.runner.stats["points_sent"] + len(rows) > self.cap:
            raise RuntimeError(f"cost-cap: the E2-3 USINE fit would pass {self.cap} evaluations")
        tally = self.batch_runner.tally
        if tally["provider_evaluations"] + len(rows) > self.batch_runner.max_evaluations:
            raise RuntimeError("cost-cap: the E2 total of USINE evaluations would be passed")
        pts = [e1.to_physical(np.clip(u, 0.0, 1.0)) for u in np.atleast_2d(rows)]
        before = self.runner.stats["points_sent"]
        resp = self.runner.evaluate(dict(self.request, points=pts))
        sent = self.runner.stats["points_sent"] - before
        tally["provider_evaluations"] += sent
        tally["cache_hits"] += len(pts) - sent
        self.batch_runner.tally_path.write_text(json.dumps(tally, indent=1) + "\n", encoding="utf-8")
        out = []
        for res in resp["results"]:
            if res["status"] != "ok":
                out.append(None)
                continue
            self.records.append({"point": res["point"], "point_hash": point_hash(
                self.request["transport"], "usine", self.request["provider_version"], res["point"]),
                "computational_run_ref": res["evaluation"]["computational_run_ref"]})
            out.append(np.asarray(res["predictions"][0]["values"]["values"]))
        return out


# ---------------------------------------------------------------------------------------------- campaign
def e1_points() -> tuple[list[dict], dict]:
    """E1's USINE points (design, hold-out, additions of the standard and forced runs) without the truth point, and
    the truth point."""
    summary = json.loads((HERE.parent / "e1" / "summary.json").read_text(encoding="utf-8"))
    forced = json.loads((HERE.parent / "e1" / "forced-test.json").read_text(encoding="utf-8"))
    seen, points = set(), []
    for doc in (summary, forced):
        recs = list(doc.get("design", [])) + list(doc.get("holdout", []))
        for rnd in doc.get("rounds", []):
            recs += rnd.get("added", [])
        for rec in recs:
            if rec.get("status") == "ok" and rec["point_hash"] not in seen:
                seen.add(rec["point_hash"])
                points.append(rec["point"])
    return points, summary["truth"]["point"]


def keep(rec: dict, role: str) -> dict:
    out = {k: rec.get(k) for k in ("point", "status", "point_hash", "values_sha256", "computational_run_ref", "reason")
           if rec.get(k) is not None}
    out["role"] = role
    return out


def unit_list(rows) -> list:
    return [[float(v) for v in u] for u in rows]


def run(args) -> int:
    from core.provider.registry import load_registry

    work = Path(args.work_dir)
    (work / "cache").mkdir(parents=True, exist_ok=True)
    if args.e1_cache:
        shutil.copytree(args.e1_cache, work / "cache", dirs_exist_ok=True)
    out = run_json([REGISTRY_TOOL, "--write", work / "registry.json"])
    if out.get("status") != "written":
        raise RuntimeError(f"provider_registry.py: {out}")
    usine_version = load_registry(work / "registry.json")["usine"].version
    batch = e1.BatchRunner(work, work / "registry.json", usine_version, args.max_evaluations, args.jobs)
    summary: dict = {"work_package": "E2", "provider": {"id": "usine", "version": usine_version},
                     "labels": ["synthetic", "unvalidated"],
                     "sizes": {"holdout": HOLDOUT_SIZE, "confirmation": CONFIRM_SIZE, "k_add": K_ADD,
                               "max_rounds": MAX_ROUNDS, "min_pick_distance_unit": MIN_PICK_DISTANCE,
                               "proposal_draws": N_PROPOSAL, "defensive_fraction": DEFENSIVE_FRACTION,
                               "t_dof": T_DOF},
                     "criteria": {"dchi2_max": DCHI2_MAX, "bin_sigma_stat_max": BIN_SIGMA_MAX,
                                  "best_fit_sigma": BEST_FIT_SIGMA, "width_rtol": WIDTH_RTOL},
                     "synthetic_data": {"truth": e1.TRUTH, "bins": e1.SYNTHETIC_BINS, "covariance": "E1 ILLUSTRATIVE"},
                     "rounds": [], "status": None}

    def finish(status, reason, code):
        summary["status"], summary["reason"] = status, reason
        summary["usine_evaluations"] = batch.tally["provider_evaluations"]
        (work / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": status, "reason": reason, "usine_evaluations": batch.tally["provider_evaluations"]}))
        return code

    try:
        e1_pts, truth = e1_points()
        train_recs = batch.run("e1-reuse", e1_pts)
        truth_rec = batch.run("truth", [truth])[0]
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    bad = [r for r in train_recs if r["status"] != "ok"]
    if bad or truth_rec["status"] != "ok":
        return finish("stopped", f"E1 points not answered: {len(bad)}", 1)
    summary["e1_reuse"] = {"points": len(train_recs), "new_usine_evaluations": batch.tally["provider_evaluations"]}
    like = Likelihood(truth_rec["values"])
    summary["truth"] = keep(truth_rec, "truth")

    def trained(name, recs, **kw):
        info = train_round(work, name, recs, usine_version, **kw)
        info["registry"] = round_registry(work, info["folder"], info["model_sha256"])
        return info

    model = trained("r0", train_recs)
    client = EmulatorClient(model["registry"], model["artifact"])
    post = posterior(client, like, POSTERIOR_SEED)
    client.close()
    hold_unit = resample(post, HOLDOUT_SIZE, HOLDOUT_SEED)
    try:
        hold_recs = batch.run("holdout", [e1.to_physical(u) for u in hold_unit])
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    hold_recs = [r for r in hold_recs if r["status"] == "ok"]
    summary["holdout_drawn_from"] = {"model_sha256": model["model_sha256"], "ess": post["ess"],
                                     "refused_draws": post["refused"], "draws_in_box": post["proposal_inside_box"]}
    avoid = np.array([e1.to_unit(r["point"]) for r in train_recs + hold_recs])
    converged = None
    for rnd in range(0, MAX_ROUNDS + 1):
        if rnd > 0:
            new_unit = picks(post, like, K_ADD, avoid, PICK_SEED + rnd)
            try:
                recs = batch.run(f"round{rnd}", [e1.to_physical(u) for u in new_unit])
            except RuntimeError as exc:
                return finish("stopped", str(exc), 1)
            train_recs += [r for r in recs if r["status"] == "ok"]
            avoid = np.vstack([avoid, new_unit])
            model = trained(f"r{rnd}", train_recs)
            info_added = [keep(r, f"round{rnd}") for r in recs]
        else:
            info_added = []
        client = EmulatorClient(model["registry"], model["artifact"], allow_outside=True)
        check = holdout_check(client, like, hold_recs)
        client.close()
        client = EmulatorClient(model["registry"], model["artifact"])
        post = posterior(client, like, POSTERIOR_SEED + rnd)
        client.close()
        summary["rounds"].append({"round": rnd, "training_points": len(train_recs), "model_sha256": model["model_sha256"],
                                  "components": model["trained"]["components"], "added": info_added,
                                  "fit_unit": unit_list([post["fit_unit"]])[0],
                                  "fit_point": e1.to_physical(post["fit_unit"]), "fit_chi2": post["fit_chi2"],
                                  "posterior_ess": post["ess"], "posterior_refused_draws": post["refused"],
                                  "holdout": check})
        print(json.dumps({"round": rnd, "training_points": len(train_recs), "dchi2_max": check["dchi2_max"],
                          "pull_max": check["pull_max"], "usine": batch.tally["provider_evaluations"]}), flush=True)
        if check["e2_1_met"] and check["e2_2_met"]:
            converged = (rnd, model, post)
            break
    if converged is None:
        best = min(summary["rounds"], key=lambda r: r["holdout"]["pull_max"])
        summary["best_round"] = best["round"]
        converged = (summary["rounds"][-1]["round"], model, post)
        summary["loop_status"] = (f"max-rounds: E2-1 met {summary['rounds'][-1]['holdout']['e2_1_met']}, E2-2 met "
                                  f"{summary['rounds'][-1]['holdout']['e2_2_met']} after round {MAX_ROUNDS}; lowest "
                                  f"largest |b|/sigma_stat in round {best['round']}")
    else:
        summary["loop_status"] = f"converged: both E2 criteria met on the hold-out after round {converged[0]}"
    rnd, model, post = converged

    # confirmation hold-out from the frozen final emulator
    conf_unit = resample(post, CONFIRM_SIZE, CONFIRM_SEED, exclude=list(avoid))
    try:
        conf_recs = [r for r in batch.run("confirmation", [e1.to_physical(u) for u in conf_unit]) if r["status"] == "ok"]
    except RuntimeError as exc:
        return finish("stopped", str(exc), 1)
    client = EmulatorClient(model["registry"], model["artifact"], allow_outside=True)
    conf = holdout_check(client, like, conf_recs)
    client.close()
    summary["confirmation"] = conf

    # E2-3: the same fit through the emulator and through USINE
    client = EmulatorClient(model["registry"], model["artifact"])
    e_predict = emulator_predict(client)
    start = np.full(len(NAMES), 0.5)
    ue, ce, _ = least_squares_fit(e_predict, like, start)
    cov_e, sig_e, _ = laplace(e_predict, like, ue)
    client.close()
    fitter = UsineFitter(work, work / "registry.json", batch, FIT_USINE_CAP)
    try:
        uu, cu, sol_u = least_squares_fit(fitter.predict, like, start)
        cov_u, sig_u, _ = laplace(fitter.predict, like, uu)
    except RuntimeError as exc:
        summary["e2_3"] = {"status": "stopped", "reason": str(exc)}
        return finish("stopped", str(exc), 1)
    shift = np.abs(ue - uu) / sig_u
    width = sig_e / sig_u - 1.0
    summary["e2_3"] = {
        "start_unit": start.tolist(), "emulator": {"fit_unit": ue.tolist(), "fit_point": e1.to_physical(ue),
                                                   "chi2": ce, "sigma_unit": sig_e.tolist()},
        "usine": {"fit_unit": uu.tolist(), "fit_point": e1.to_physical(uu), "chi2": cu, "sigma_unit": sig_u.tolist(),
                  "evaluations": fitter.runner.stats["points_sent"], "cache_hits": fitter.runner.stats["cache_hits"],
                  "nfev": int(sol_u.nfev), "success": bool(sol_u.success),
                  "computational_run_refs": sorted({r["computational_run_ref"] for r in fitter.records
                                                    if r["computational_run_ref"]})},
        "parameters": NAMES, "shift_in_sigma_usine": shift.tolist(), "width_ratio_minus_one": width.tolist(),
        "boundary_note": "Laplace intervals ignore the box edges; a parameter whose 1-sigma interval crosses an edge "
                         "is listed in near_edge",
        "near_edge": [NAMES[j] for j in range(len(NAMES)) if uu[j] - sig_u[j] < 0.0 or uu[j] + sig_u[j] > 1.0],
        "passed": bool((shift <= BEST_FIT_SIGMA).all() and (np.abs(width) <= WIDTH_RTOL).all())}

    # final artifact with its validation blocks, copied into this folder
    regression = {
        "holdout": {"points": len(hold_recs), "drawn_from": "posterior through the round-0 emulator",
                    "dchi2_max": summary["rounds"][rnd]["holdout"]["dchi2_max"],
                    "pull_max": summary["rounds"][rnd]["holdout"]["pull_max"],
                    "relative_error_max": summary["rounds"][rnd]["holdout"]["relative_error_max"]},
        "confirmation": {"points": len(conf_recs), "drawn_from": "posterior through the final emulator",
                         "dchi2_max": conf["dchi2_max"], "pull_max": conf["pull_max"],
                         "relative_error_max": conf["relative_error_max"]},
        "criteria": "E2-1 dchi2 = b^T C^-1 b <= 1 (C the full ILLUSTRATIVE data covariance); E2-2 |b_i| <= 0.2 "
                    "sigma_stat_i in every bin; b = emulator - USINE",
        "max_relative_error": max(summary["rounds"][rnd]["holdout"]["relative_error_max"], conf["relative_error_max"]),
        "validated_region": "the posterior of the synthetic B/C fit (truth D0 3e28, delta 0.5, eta 1, V_A 30, V_c 5); "
                            "elsewhere in the box the emulator's own error estimate is the only guide"}
    e23 = summary["e2_3"]
    downstream = [
        {"metric": "bias", "quantity_affected": f"best fit of {name} (synthetic B/C fit), emulator minus USINE in "
                                                "units of the USINE Laplace sigma",
         "value": float(e23["shift_in_sigma_usine"][j]), "criterion": f"abs <= {BEST_FIT_SIGMA}",
         "passed": bool(e23["shift_in_sigma_usine"][j] <= BEST_FIT_SIGMA), "ref": "summary.json e2_3"}
        for j, name in enumerate(NAMES)] + [
        {"metric": "expected-uncertainty", "quantity_affected": f"Laplace 68.27% half-width of {name}, emulator over "
                                                                "USINE minus 1",
         "value": float(e23["width_ratio_minus_one"][j]), "criterion": f"abs <= {WIDTH_RTOL}",
         "passed": bool(abs(e23["width_ratio_minus_one"][j]) <= WIDTH_RTOL), "ref": "summary.json e2_3"}
        for j, name in enumerate(NAMES)]
    folder = model["folder"]
    manifest = {"train": [r["point_hash"] for r in train_recs], "holdout": [r["point_hash"] for r in hold_recs],
                "confirmation": [r["point_hash"] for r in conf_recs],
                "groups": {r["point_hash"]: r["point_hash"] for r in train_recs + hold_recs + conf_recs},
                "roles": {"test": "confirmation"}}
    (folder / "split-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    report = run_json([SPLIT_CHECK, "split-manifest.json", "--json"], cwd=folder, ok=(0, 1, 3))
    (folder / "split-report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    write_artifact(folder, {"regression_validation": regression, "split_manifest": "split-manifest.json"}, downstream)
    if sha256_file(folder / "emulator-model.json") != model["model_sha256"]:
        raise RuntimeError("the model changed while writing the artifact")
    for name in ("emulator-model.json", "emulator.ml-artifact.json"):
        shutil.copyfile(folder / name, HERE / name)
    hold_doc = {"note": "USINE B/C (provider usine) at the hold-out points; never trained on",
                "observable": e1.base_request("0")["observables"][0], "truth": {**keep(truth_rec, "truth"),
                                                                                  "values": truth_rec["values"]},
                "holdout": [{**keep(r, "holdout"), "values": r["values"]} for r in hold_recs],
                "confirmation": [{**keep(r, "confirmation"), "values": r["values"]} for r in conf_recs]}
    (HERE / "holdout.json").write_text(json.dumps(hold_doc, indent=1) + "\n", encoding="utf-8")
    summary["final_round"] = rnd
    summary["final_model_sha256"] = model["model_sha256"]
    summary["training_points"] = [{"point_hash": r["point_hash"], "computational_run_ref": r.get("computational_run_ref"),
                                   "values_sha256": r.get("values_sha256")} for r in train_recs]
    summary["e2_1_met"] = bool(summary["rounds"][rnd]["holdout"]["e2_1_met"] and conf["e2_1_met"])
    summary["e2_2_met"] = bool(summary["rounds"][rnd]["holdout"]["e2_2_met"] and conf["e2_2_met"])
    status = "done" if summary["e2_1_met"] and summary["e2_2_met"] and e23["passed"] else "criteria-not-met"
    for rec in summary["rounds"]:
        rec["holdout"].pop("dchi2", None)
    result = finish(status, summary["loop_status"], 0)
    shutil.copyfile(work / "summary.json", HERE / "summary.json")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="train, validate on the hold-out sets, compare the synthetic fits")
    r.add_argument("--work-dir", required=True, type=Path)
    r.add_argument("--e1-cache", type=Path, help="E1's provider cache, copied into --work-dir/cache first")
    r.add_argument("--max-evaluations", type=int, default=500)
    r.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "error", "error": "NumPy and SciPy are needed"}))
        return 2
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
