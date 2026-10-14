#!/usr/bin/env python3
"""J9 (physics-ml -> hep-statistics): SYNTHETIC classifier with grouped splits, calibration and a domain-shift check,
whose calibrated score feeds a binned template fit of a signal strength.

SYNTHETIC and ILLUSTRATIVE. Every sample is invented here: a toy e+e- -> mu+mu- "signal" against a broad
"background" at the illustrative experiment:synthetic-collider (sqrt(s) = 10 GeV), with four features. Nothing
describes a real detector, process or result; the profile's own generator and detector modules are not used.

Chain:
 1. seeded simulation: signal and background events in runs nested in data-taking periods; background carries
    NLO-like counter-events (about 10% negative generator weights); weights normalized to the integrated
    luminosity. A data-like control sample (background with a deliberate pt_miss scale shift) and pseudo-data
    (background + injected signal mu_true, Poisson; labelled pseudo-data, never observed data).
 2. grouped train/val/test split by run (scripts/make_grouped_splits.py), checked with
    scripts/check_split_integrity.py --strict; a row-level random split of the same rows is shown to leak (reported,
    never trained on).
 3. training: NumPy weighted logistic regression on quadratic features (signed weights, class-balanced training
    weights; evaluation weights are the physics weights) by default, or --trainer torch
    (assets/train_classifier.py). Weighted AUC, background rejection at a working point fixed on validation,
    Asimov significance (assets/hep_metrics.py).
 4. calibration (assets/calibration.py CLI): prior correction to the physics class ratio and temperature, fit on
    validation, evaluated on test; ECE before and after.
 5. domain shift: weighted Kolmogorov-Smirnov of the score and of every feature, simulation background versus the
    control sample, against a noise floor from seeded unshifted replicas; inference-time domain flags on the
    pseudo-data (scripts/check_surrogate_domain.py).
 6. ml-artifact (scripts/write_ml_artifact.py), status synthetic, output_semantics probability, downstream
    validation = effect on the signal strength (Asimov closure, toy pulls and coverage, shift from the measured
    control-sample scale), not AUC.
 7. hep-statistics: calibrated-score templates (signal; background with sum w^2 for MC statistics) -> extended
    binned Poisson fit of mu with Barlow-Beeston-lite MC-statistics factors (core.stats.likelihood_limits shape
    model; signed weights need the Gaussian MC-statistics term, not effective counts) -> statistical-result that
    links the ml-artifact by id and sha256; Asimov closure and seeded toys (pull mean, width, 68% coverage).
 8. report.md, results.json, scores_and_calibration.png; exit 0 iff every pre-declared criterion passes.

Usage (from the plugin root): python3 examples/ml-classifier-to-inference/run.py [--out DIR] [--toys 1000]
    [--seed 20261013] [--trainer numpy|torch]
The committed output uses the NumPy trainer (no PyTorch needed). Requires numpy, scipy and matplotlib.
Intermediate files (event tables, split manifests, scores, tool reports) go to DIR/work/ (not committed; rerun to
regenerate them byte for byte).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import optimize

PLUGIN = Path(__file__).resolve().parents[2]
ML = PLUGIN / "skills" / "physics-ml"
PROFILE_DIR = PLUGIN / "profiles" / "experiments" / "synthetic-collider"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(ML / "assets"))
import hep_metrics  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.stats.likelihood_limits import _load_shape, _ShapeModel  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

# ----------------------------------------------------------------------------- configuration (all invented)
FEATURES = ["m_ll", "acop", "pt_miss", "cos_theta"]
UNITS = {"m_ll": "GeV", "acop": "rad", "pt_miss": "GeV", "cos_theta": "1"}
LABELS = ["background", "signal"]
LUMI_FB = 10.0                                   # integrated luminosity [fb^-1]
XSEC_FB = {"signal": 4.0, "background": 30.0}    # cross sections after preselection [fb]
PERIODS, RUNS_PER_PERIOD = 4, 6                  # 24 runs; the run is the grouping key
MC_PER_RUN = {"signal": 150, "background": 200, "counter": 25}  # counter-events: 25 at +w and 25 at -w per run
RUN_SCALE_SIGMA = 0.004                          # run-to-run momentum-scale offset (correlates events in a run)
SHIFT_FEATURE, SHIFT = "pt_miss", 1.10           # deliberate scale shift of the data-like control sample
SHIFT_NUISANCE = "theta_pt_miss_scale"           # fit nuisance: background template at the measured control-sample scale
CONTROL_SIZE, NULL_REPLICAS = 10000, 100
MU_TRUE = 1.0
FRACTIONS = (0.6, 0.2, 0.2)
WP_EFF_S = 0.5                                   # working point: signal efficiency, threshold fixed on validation
L2 = 1.0                                         # ridge penalty of the logistic regression (bias not penalized)
EDGES = [0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0]  # calibrated-probability bins of the template fit
OOD_TRAINING_POINTS, OOD_QUANTILE = 2000, 0.99
CRITERIA = {"split_check_strict": "passed", "rowlevel_split": "failed (leakage)",
            "ece_after_max": 0.03, "domain_shift_detects_injected_shift": True, "ood_outside_fraction_max": 0.05,
            "asimov_mu_abs_dev_max": 1e-3, "toy_mean_pull_abs": 0.15, "toy_pull_width": (0.9, 1.1),
            "toy_coverage_68": (0.635, 0.73), "pseudo_data_mu_within_sigma": 3.0}


# ----------------------------------------------------------------------------- generation
def _cos_1pc2(rng, n):
    """cos theta from 1 + cos^2 theta on |cos theta| < 0.9 (accept-reject)."""
    out = np.empty(0)
    while out.size < n:
        c = rng.uniform(-0.9, 0.9, 2 * n)
        out = np.r_[out, c[rng.uniform(0, 1.81, c.size) < 1 + c ** 2]]
    return out[:n]


def gen(kind: str, rng, n: int, scale: float = 1.0) -> np.ndarray:
    """Features [n, 4] for 'signal', 'background' (the physical background density) or 'counter' (the shape of
    the NLO-like counter-events, which enter with +w and -w and cancel in expectation)."""
    if kind == "signal":
        m = 10.0 * scale * (1 - np.minimum(rng.exponential(0.06, n), 0.6)) + rng.normal(0, 0.35, n)
        acop = rng.exponential(0.04, n)
        pt = rng.gamma(1.5, 0.4, n)
        c = _cos_1pc2(rng, n)
    elif kind == "background":
        m = 10.0 * scale * rng.beta(5.0, 1.5, n)
        acop = rng.exponential(0.08, n)
        pt = rng.gamma(2.0, 0.6, n)
        c = rng.uniform(-0.9, 0.9, n)
    else:
        m = 10.0 * scale * rng.beta(4.0, 1.5, n)
        acop = rng.exponential(0.05, n)
        pt = rng.gamma(1.5, 0.5, n)
        c = rng.uniform(-0.9, 0.9, n)
    return np.c_[m, np.minimum(acop, math.pi), pt, c]


def simulate(seed: int) -> dict:
    """Simulation: per run, signal, background and counter-event pairs, with physics weights (L x sigma)."""
    rng = np.random.default_rng(seed)
    n_runs = PERIODS * RUNS_PER_PERIOD
    w_sig = LUMI_FB * XSEC_FB["signal"] / (n_runs * MC_PER_RUN["signal"])
    w_bkg = LUMI_FB * XSEC_FB["background"] / (n_runs * MC_PER_RUN["background"])
    rows = {"x": [], "y": [], "w": [], "run": [], "period": []}
    for p in range(1, PERIODS + 1):
        for r in range(1, RUNS_PER_PERIOD + 1):
            run, scale = f"p{p}-r{r:02d}", 1.0 + RUN_SCALE_SIGMA * rng.normal()
            k = MC_PER_RUN["counter"]
            parts = [(gen("signal", rng, MC_PER_RUN["signal"], scale), 1, w_sig),
                     (gen("background", rng, MC_PER_RUN["background"], scale), 0, w_bkg),
                     (gen("counter", rng, k, scale), 0, w_bkg), (gen("counter", rng, k, scale), 0, -w_bkg)]
            for x, y, w in parts:
                rows["x"].append(x)
                rows["y"] += [y] * len(x)
                rows["w"] += [w] * len(x)
                rows["run"] += [run] * len(x)
                rows["period"] += [f"p{p}"] * len(x)
    x = np.round(np.vstack(rows["x"]), 6)
    return {"x": x, "y": np.array(rows["y"]), "w": np.array(rows["w"]), "run": rows["run"], "period": rows["period"],
            "id": [f"ev{i:05d}" for i in range(len(x))]}


def pseudo_data(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    nb, ns = rng.poisson(LUMI_FB * XSEC_FB["background"]), rng.poisson(MU_TRUE * LUMI_FB * XSEC_FB["signal"])
    x = np.round(np.vstack([gen("background", rng, nb), gen("signal", rng, ns)]), 6)
    return {"x": x, "n_background_drawn": int(nb), "n_signal_drawn": int(ns)}


def control_sample(rng, shift: float) -> np.ndarray:
    x = gen("background", rng, CONTROL_SIZE)
    x[:, FEATURES.index(SHIFT_FEATURE)] *= shift
    return np.round(x, 6)


# ----------------------------------------------------------------------------- tools (subprocess, cwd = out)
def tool(out: Path, script: Path, *args) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=out, capture_output=True, text=True,
                          timeout=600)
    return proc.returncode, proc.stdout if proc.stdout.strip() else proc.stderr


def write_events(path: Path, sim: dict) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["id", "run", "period", "label", "weight", *FEATURES])
        for i in range(len(sim["id"])):
            wr.writerow([sim["id"][i], sim["run"][i], sim["period"][i], int(sim["y"][i]), f"{sim['w'][i]:.10g}",
                         *(f"{v:.6f}" for v in sim["x"][i])])


def rowlevel_manifest(sim: dict, seed: int) -> dict:
    """The mistake to catch: the same rows split at random, ignoring the run."""
    order = np.random.default_rng(seed).permutation(len(sim["id"]))
    a, b = int(FRACTIONS[0] * len(order)), int((FRACTIONS[0] + FRACTIONS[1]) * len(order))
    ids = np.array(sim["id"])
    return {"_comment": "SYNTHETIC: row-level random split (the leakage example); never trained on",
            "train": ids[order[:a]].tolist(), "val": ids[order[a:b]].tolist(), "test": ids[order[b:]].tolist(),
            "groups": dict(zip(sim["id"], sim["run"]))}


# ----------------------------------------------------------------------------- NumPy trainer
def design(z: np.ndarray) -> np.ndarray:
    """[1, z_i, z_i^2, z_i z_j (i < j)] from standardized features."""
    cols = [np.ones(len(z))] + [z[:, i] for i in range(z.shape[1])] + [z[:, i] ** 2 for i in range(z.shape[1])]
    cols += [z[:, i] * z[:, j] for i in range(z.shape[1]) for j in range(i + 1, z.shape[1])]
    return np.column_stack(cols)


def train_numpy(x, y, w_train) -> dict:
    """Weighted logistic regression by damped Newton iterations; signed weights enter the loss unchanged."""
    mean, std = x.mean(axis=0), np.maximum(x.std(axis=0), 1e-12)
    a = design((x - mean) / std)
    pen = np.full(a.shape[1], L2)
    pen[0] = 0.0
    beta = np.zeros(a.shape[1])

    def loss(b):
        t = a @ b
        return float(np.sum(w_train * (np.logaddexp(0, t) - y * t)) + 0.5 * np.sum(pen * b * b))

    it, damping = 0, 0.0
    while it < 100:
        it += 1
        p = 1.0 / (1.0 + np.exp(-(a @ beta)))
        g = a.T @ (w_train * (p - y)) + pen * beta
        h = (a * (w_train * p * (1 - p))[:, None]).T @ a + np.diag(pen)
        while True:  # Levenberg damping until the (signed-weight) Hessian is positive definite and the step descends
            try:
                np.linalg.cholesky(h + damping * np.eye(len(h)))
                step = np.linalg.solve(h + damping * np.eye(len(h)), g)
                if loss(beta - step) <= loss(beta) + 1e-12:
                    break
            except np.linalg.LinAlgError:
                pass
            damping = max(2 * damping, 1e-6)
        beta -= step
        damping /= 10.0
        if np.max(np.abs(step)) < 1e-10:
            break
    return {"type": "weighted logistic regression on quadratic features (NumPy, Newton)", "features": FEATURES,
            "mean": mean.tolist(), "std": std.tolist(), "beta": beta.tolist(), "l2": L2, "iterations": it,
            "converged": bool(np.max(np.abs(step)) < 1e-10), "final_loss": loss(beta)}


def numpy_scorer(model: dict):
    mean, std, beta = (np.array(model[k]) for k in ("mean", "std", "beta"))
    return lambda x: 1.0 / (1.0 + np.exp(-(design((x - mean) / std) @ beta)))


def torch_scorer(run_dir: Path):
    import torch
    sys.path.insert(0, str(ML / "assets"))
    from models import MLPClassifier
    ck = torch.load(run_dir / "best.pt", map_location="cpu", weights_only=True)
    mc, pre = ck["metadata"]["model"], ck["metadata"]["preprocessing"][0]
    net = MLPClassifier(mc["input_dim"], mc["hidden_dim"], mc["num_classes"], mc["dropout"])
    net.load_state_dict(ck["model_state_dict"])
    net.eval()

    def score(x):
        z = (x - np.array(pre["mean"])) / np.array(pre["std"])
        with torch.inference_mode():
            return torch.sigmoid(net(torch.as_tensor(z, dtype=torch.float32))[:, 0]).double().numpy()
    return score


def train_torch(out: Path, seed: int) -> tuple:
    (out / "work" / "units.json").write_text(json.dumps(UNITS))
    code, msg = tool(out, ML / "assets" / "train_classifier.py", "--data", "work/events_mc.csv",
                     "--split-manifest", "work/splits.json", "--weight-col", "weight", "--features", ",".join(FEATURES),
                     "--label-col", "label", "--units", "work/units.json", "--grouping-key", "run",
                     "--class-balancing", "equal-sum", "--epochs", "15", "--num-workers", "0", "--seed", str(seed),
                     "--device", "cpu", "--working-points", str(WP_EFF_S), "--output-dir", "work/torch")
    if code != 0:
        raise SystemExit(f"train_classifier.py failed ({code}): {msg[-2000:]}")
    summary = json.loads((out / "work" / "torch" / "run_summary.json").read_text())
    return torch_scorer(out / "work" / "torch"), summary


# ----------------------------------------------------------------------------- metrics and checks
def write_scores(path: Path, ids, y, w, s) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["id", "label", "weight", "score"])
        for i in range(len(ids)):
            wr.writerow([ids[i], int(y[i]), f"{w[i]:.10g}", f"{s[i]:.12g}"])


def calibrate(p, params: dict, prior_r: float) -> np.ndarray:
    """The map the calibration CLI fitted: prior correction ln r on the logit, then temperature."""
    z = np.log(np.clip(p, 1e-12, 1 - 1e-12)) - np.log(np.clip(1 - p, 1e-12, 1))
    return 1.0 / (1.0 + np.exp(-(z + math.log(prior_r)) / params["temperature"]))


def weighted_ks(a, wa, b, wb) -> float:
    """sup |F_a - F_b| with signed weights (each ECDF normalized to its net weight)."""
    grid = np.sort(np.r_[a, b])
    fa = np.cumsum(wa[np.argsort(a)])[np.searchsorted(np.sort(a), grid, side="right") - 1] / wa.sum()
    fb = np.cumsum(wb[np.argsort(b)])[np.searchsorted(np.sort(b), grid, side="right") - 1] / wb.sum()
    fa[grid < a.min()] = 0.0
    fb[grid < b.min()] = 0.0
    return float(np.max(np.abs(fa - fb)))


def domain_shift(sim_x, sim_w, score, seed: int) -> dict:
    """Weighted KS of score and features: simulation background (val+test) versus the control sample, with a noise
    floor (95% quantile of the same statistic for seeded control-sized replicas drawn without the shift)."""
    rng = np.random.default_rng(seed)
    ctrl = control_sample(rng, SHIFT)
    one = np.ones(CONTROL_SIZE)
    variables = {"score": (score(sim_x), lambda x: score(x))}
    variables.update({f: (sim_x[:, i], (lambda j: lambda x: x[:, j])(i)) for i, f in enumerate(FEATURES)})
    null = {k: [] for k in variables}
    for _ in range(NULL_REPLICAS):
        rep = control_sample(rng, 1.0)
        for k, (sv, fn) in variables.items():
            null[k].append(weighted_ks(sv, sim_w, fn(rep), one))
    out = {}
    for k, (sv, fn) in variables.items():
        d = weighted_ks(sv, sim_w, fn(ctrl), one)
        floor = float(np.quantile(null[k], 0.95))
        out[k] = {"ks_d": d, "noise_floor_95": floor, "shift_detected": d > floor}
    i = FEATURES.index(SHIFT_FEATURE)
    scale = float(np.mean(ctrl[:, i]) / (np.sum(sim_w * sim_x[:, i]) / np.sum(sim_w)))
    return {"per_variable": out, "measured_scale": {"feature": SHIFT_FEATURE, "control_over_simulation_mean": scale},
            "control_sample": ctrl}


# ----------------------------------------------------------------------------- template fit (hep-statistics)
def templates(score, x, y, w, scale_by_class) -> dict:
    h = {}
    for c, name in enumerate(LABELS):
        sel = y == c
        s = score(x[sel])
        k = scale_by_class[c]
        h[name] = {"sumw": (np.histogram(s, EDGES, weights=w[sel])[0] * k).tolist(),
                   "sumw2": (np.histogram(s, EDGES, weights=w[sel] ** 2)[0] * k * k).tolist()}
    return h


def shape_model(t: dict, counts, b_up=None) -> _ShapeModel:
    """Shape model; with b_up, the background template at the control-sample pt_miss scale is a +1 sigma shape
    variation (mirrored for -1 sigma) of a Gaussian-constrained nuisance: the measured domain shift is carried by the
    fit (domain_shift outcome bounded-by-nuisance), not left uncorrected."""
    doc = {"bins": [{"n": int(n), "b": b, "s": s, "mc_stat": math.sqrt(v)} for n, b, s, v in
                    zip(counts, t["background"]["sumw"], t["signal"]["sumw"], t["background"]["sumw2"])]}
    if b_up is not None:
        b0 = np.array(t["background"]["sumw"])
        doc["nuisances"] = [{"kind": "background_shape", "name": SHIFT_NUISANCE, "up": [float(v) for v in b_up],
                             "down": [float(v) for v in np.maximum(2 * b0 - np.asarray(b_up), 0.0)],
                             "interpolation": "code0"}]
    bins, nuis, chol = _load_shape(doc)  # the core input checks (ranges, positive background where mc_stat is set)
    return _ShapeModel(bins, nuis, chol)


def fit_mu(model: _ShapeModel, ns, aux) -> dict:
    """Best fit (mu >= 0) and the profile-likelihood 68.27% interval (Delta(-2 ln L) = 1)."""
    mu_hat, _, nll_min = model.glob(list(ns), list(aux))
    f = lambda mu: 2.0 * (model.cond(mu, list(ns), list(aux))[1] - nll_min) - 1.0  # noqa: E731
    hi_end = mu_hat + 1.0
    while f(hi_end) < 0:
        hi_end += 1.0
    hi = optimize.brentq(f, mu_hat, hi_end, xtol=1e-9)
    lo = optimize.brentq(f, 0.0, mu_hat, xtol=1e-9) if mu_hat > 0 and f(0.0) > 0 else 0.0
    return {"mu_hat": float(mu_hat), "lo": float(lo), "hi": float(hi), "err_down": float(mu_hat - lo),
            "err_up": float(hi - mu_hat), "nll_min": float(nll_min), "at_boundary": lo == 0.0}


def toys(model: _ShapeModel, t: dict, n_toys: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s, b = np.array(t["signal"]["sumw"]), np.array(t["background"]["sumw"])
    rel = np.sqrt(np.array(t["background"]["sumw2"])) / b
    pulls, covered, failed = [], 0, 0
    for _ in range(n_toys):
        ns = rng.poisson(MU_TRUE * s + b)
        aux = np.maximum(1.0 + rel * rng.normal(size=b.size), 1e-3)  # auxiliary MC-statistics measurement redrawn
        theta_aux = rng.normal(size=model.k).tolist()  # auxiliary measurement of each Gaussian nuisance redrawn
        try:
            r = fit_mu(model, ns.tolist(), theta_aux + aux.tolist())
        except (ValueError, RuntimeError):
            failed += 1
            continue
        err = r["err_up"] if r["mu_hat"] < MU_TRUE else r["err_down"]
        pulls.append((r["mu_hat"] - MU_TRUE) / err)
        covered += r["lo"] <= MU_TRUE <= r["hi"]
    p = np.array(pulls)
    return {"n": n_toys, "seed": seed, "failed": failed, "pull_mean": float(p.mean()), "pull_width": float(p.std(ddof=1)),
            "coverage_68": covered / len(p)}


# ----------------------------------------------------------------------------- artifacts
def rnd(o, sig=6):
    """Round floats to `sig` significant digits so results.json does not carry last-bit BLAS differences."""
    if isinstance(o, dict):
        return {k: rnd(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rnd(v, sig) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(f"{float(o):.{sig}g}") if math.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def stat_artifact(fit, asimov, toy, ml_doc, ml_ref, ml_sha, gof, created) -> dict:
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": "synthetic-j9-signal-strength",
            "artifact_type": "statistical-result", "required_capabilities": ["stats:result-semantics"],
            "objective": "SYNTHETIC J9: signal strength from calibrated-classifier score templates fitted to pseudo-data",
            "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(),
                         "profiles": {PROFILE["id"]: PROFILE["version"]}},
            "provenance": {"producer_skill": "hep-statistics", "created": created, "evidence_ids": []},
            "inputs": [{"ref": ml_ref, "artifact_type": "ml-artifact", "artifact_id": ml_doc["artifact_id"],
                        "sha256": ml_sha, "version": ml_doc["contract_version"], "status": ml_doc["status"]}],
            "outputs": [], "status": ["synthetic"], "unresolved_inputs": [],
            "extension": {
                "paradigm": "frequentist",
                "likelihood": {"form": "extended binned Poisson in the calibrated classifier probability "
                                       f"({len(EDGES) - 1} bins), mean mu s_i + gamma_i b_i(theta); b_i(theta) "
                                       f"interpolates the background template to its {SHIFT_FEATURE}-scale variation "
                                       "(code0, Gaussian theta); gamma_i Gaussian-constrained MC-statistics factors "
                                       "(Barlow-Beeston-lite, width sqrt(sum w^2)/b of the signed-weight background "
                                       "template)",
                               "backend": "core.stats.likelihood_limits shape model (_ShapeModel)",
                               "model_ref": "results.json#templates"},
                "parameters_of_interest": ["mu (signal strength)"],
                "nuisances": [f"{SHIFT_NUISANCE} (background shape: template at the control-sample {SHIFT_FEATURE} "
                              "scale as +1 sigma, mirrored for -1 sigma; Gaussian constraint)"]
                             + [f"gamma_{i} (background MC statistics, bin {i})" for i in range(len(EDGES) - 1)],
                "test_statistic": "-2 ln lambda(mu), profile likelihood ratio with mu >= 0",
                "construction": "profile-likelihood-wilks",
                "coverage": {"check": "toys", "method": "seeded toys at mu_true from the template model with the "
                                                        "MC-statistics auxiliary measurements redrawn; fraction of "
                                                        "68.27% profile intervals containing mu_true",
                             "n_toys": toy["n"], "coverage": toy["coverage_68"], "cl": 0.6827,
                             "ensemble": f"mu_true = {MU_TRUE}, templates as fitted", "failures": toy["failed"],
                             "seed": toy["seed"]},
                "goodness_of_fit": {"statistic": "saturated-model -2 ln lambda", "p_value": gof["p"], "calibration": "asymptotic"},
                "fit_status": "converged",
                "results": {"mu_hat": fit["mu_hat"], "interval_68": [fit["lo"], fit["hi"]], "data": "pseudo-data (SYNTHETIC)",
                            "asimov_mu_hat": asimov["mu_hat"], "ref": "results.json#fit"}}}


def write_ml_artifact(out: Path, created: str) -> tuple[int, dict]:
    code, msg = tool(out, ML / "scripts" / "write_ml_artifact.py", "--run-summary", "work/run_summary.json",
                     "--calibration", "work/calibration.json", "--domain-shift", "work/domain_shift.json",
                     "--downstream", "work/downstream.json", "--split-report", "work/split_check.json",
                     "--status", "synthetic", "--output-semantics", "probability",
                     "--artifact-id", "synthetic-j9-classifier", "--created", created,
                     "--objective", "SYNTHETIC J9: calibrated event classifier whose probability feeds a template fit",
                     "--out", "artifacts/ml_artifact.json")
    return code, json.loads(msg)


# ----------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=20261013)
    ap.add_argument("--toys", type=int, default=1000)
    ap.add_argument("--trainer", choices=("numpy", "torch"), default="numpy")
    ap.add_argument("--created", default="2026-10-13")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    work = out / "work"
    for d in (work, out / "artifacts"):
        d.mkdir(parents=True, exist_ok=True)

    # 1. samples
    sim = simulate(a.seed)
    write_events(work / "events_mc.csv", sim)
    pd_ = pseudo_data(a.seed + 1)
    x, y, w = sim["x"], sim["y"], sim["w"]

    # 2. grouped split by run, strict check; the row-level split of the same rows must be caught
    code_split, msg = tool(out, ML / "scripts" / "make_grouped_splits.py", "work/events_mc.csv", "--id-column", "id",
                           "--group-column", "run", "--fractions", *FRACTIONS, "--seed", a.seed, "--out", "work/splits.json")
    if code_split != 0:
        raise SystemExit(f"make_grouped_splits.py failed: {msg}")
    split_summary = json.loads(msg)
    code_check, msg = tool(out, ML / "scripts" / "check_split_integrity.py", "work/splits.json", "--json", "--strict")
    (work / "split_check.json").write_text(msg)
    split_report = json.loads(msg)
    (work / "splits_rowlevel.json").write_text(json.dumps(rowlevel_manifest(sim, a.seed + 2)))
    code_row, msg = tool(out, ML / "scripts" / "check_split_integrity.py", "work/splits_rowlevel.json", "--json", "--strict")
    (work / "split_check_rowlevel.json").write_text(msg)
    row_report = json.loads(msg)
    manifest = json.loads((work / "splits.json").read_text())
    pos = {v: i for i, v in enumerate(sim["id"])}
    idx = {s: np.array([pos[i] for i in manifest[s]]) for s in ("train", "val", "test")}
    tr, va, te = idx["train"], idx["val"], idx["test"]

    # 3. training: training weights (class-balanced, signed) are separate from the evaluation (physics) weights
    w_train = w[tr].copy()
    for c in (0, 1):
        sel = y[tr] == c
        w_train[sel] *= (len(tr) / 2) / w_train[sel].sum()
    if a.trainer == "torch":
        score_raw, tsum = train_torch(out, a.seed)
        model_info = {"type": "MLPClassifier via assets/train_classifier.py", "model_hash": tsum["model_hash"]}
        environment = tsum["environment"]
    else:
        model = train_numpy(x[tr], y[tr], w_train)
        (work / "model.json").write_text(json.dumps(model, indent=1) + "\n")
        score_raw = numpy_scorer(model)
        model_info = {k: model[k] for k in ("type", "iterations", "converged", "l2")}
        environment = {"framework": f"numpy {np.__version__}", "device": "cpu", "precision": "fp64",
                       "seeds": {"simulation_and_split": a.seed, "pseudo_data": a.seed + 1, "toys": a.seed + 3,
                                 "domain_shift": a.seed + 4}}
    s_val, s_test = score_raw(x[va]), score_raw(x[te])
    write_scores(work / "val_scores.csv", [sim["id"][i] for i in va], y[va], w[va], s_val)
    write_scores(work / "test_scores.csv", [sim["id"][i] for i in te], y[te], w[te], s_test)

    wp_val = hep_metrics.rejection_at_signal_efficiency(s_val, y[va], w[va], WP_EFF_S)
    sel = s_test >= wp_val["threshold"]
    es, es_u = hep_metrics.efficiency_with_uncertainty(sel[y[te] == 1], w[te][y[te] == 1])
    eb, eb_u = hep_metrics.efficiency_with_uncertainty(sel[y[te] == 0], w[te][y[te] == 0])
    s_exp, b_exp = LUMI_FB * XSEC_FB["signal"] * es, LUMI_FB * XSEC_FB["background"] * eb
    metrics = {"val": {"auc_weighted": hep_metrics.weighted_auc(s_val, y[va], w[va]), "working_point": wp_val},
               "test": {"auc_weighted": hep_metrics.weighted_auc(s_test, y[te], w[te]),
                        "working_point": {"threshold_from": "val", "threshold": wp_val["threshold"], "eff_s": es,
                                          "eff_s_unc": es_u, "eff_b": eb, "eff_b_unc": eb_u, "rejection": 1 / eb},
                        "asimov_significance_at_wp": hep_metrics.asimov_significance(s_exp, b_exp),
                        "expected_at_wp": {"signal": s_exp, "background": b_exp}}}

    # 4. calibration: fit on validation, evaluate on test, prior corrected to the physics class ratio
    prior_r = float(w[va][y[va] == 1].sum() / w[va][y[va] == 0].sum())
    code_cal, msg = tool(out, ML / "assets" / "calibration.py", "--fit", "work/val_scores.csv", "--eval",
                         "work/test_scores.csv", "--method", "temperature", "--id-col", "id",
                         "--prior-ratio-change", f"{prior_r:.10g}", "--bins", 10)
    if code_cal != 0:
        raise SystemExit(f"calibration.py failed: {msg}")
    (work / "calibration.json").write_text(msg)
    calib = json.loads(msg)
    prior_r = calib["prior_shift"]["prior_ratio_change"]
    score = lambda xx: calibrate(score_raw(xx), calib["calibration"]["params"], prior_r)  # noqa: E731

    # 5. domain shift on held-out simulation background versus the control sample; domain flags on pseudo-data
    bkg_ho = np.r_[va, te][y[np.r_[va, te]] == 0]
    ds = domain_shift(x[bkg_ho], w[bkg_ho], score, a.seed + 4)
    ctrl = ds.pop("control_sample")
    sub = np.random.default_rng(a.seed + 5).choice(tr, size=min(OOD_TRAINING_POINTS, len(tr)), replace=False)
    (work / "domain_query.json").write_text(json.dumps({"features": FEATURES, "training": x[np.sort(sub)].tolist(),
                                                        "queries": pd_["x"].tolist()}))
    code_ood, msg = tool(out, ML / "scripts" / "check_surrogate_domain.py", "work/domain_query.json",
                         "--quantile", OOD_QUANTILE, "--seed", a.seed)
    ood_rep = json.loads(msg)
    ood_counts = {k: int(sum(1 for q in ood_rep["queries"] if q["status"] == k)) for k in ("inside", "sparse", "outside")}
    n_q = len(pd_["x"])

    # 7a. templates from the test split (held out from training and from the calibration fit), scaled to the full MC
    scale_by_class = [np.sum(y == c) / np.sum(y[te] == c) for c in (0, 1)]
    t = templates(score, x[te], y[te], w[te], scale_by_class)
    s_t, b_t = np.array(t["signal"]["sumw"]), np.array(t["background"]["sumw"])
    counts = np.histogram(score(pd_["x"]), EDGES)[0]
    # effect of the measured control-sample scale on mu: the background template rebuilt at that scale
    xs = x[te].copy()
    xs[:, FEATURES.index(SHIFT_FEATURE)] *= ds["measured_scale"]["control_over_simulation_mean"]
    b_shift = np.array(templates(score, xs, y[te], w[te], scale_by_class)["background"]["sumw"])
    nominal_only = shape_model(t, counts)  # without the nuisance: the size of the shift on mu (Asimov)
    asimov_shift = fit_mu(nominal_only, (MU_TRUE * s_t + b_shift).tolist(), nominal_only.aux_obs())
    model_fit = shape_model(t, counts, b_up=b_shift)  # the fit carries the shift as a nuisance
    aux0 = model_fit.aux_obs()
    asimov = fit_mu(model_fit, (MU_TRUE * s_t + b_t).tolist(), aux0)
    toy = toys(model_fit, t, a.toys, a.seed + 3)

    # 6. ml-artifact (downstream validation = effect on the fitted signal strength)
    split_ok = split_report["status"] == "passed"
    run_summary = {
        "task": "classification", "features": FEATURES, "units": UNITS, "labels": LABELS,
        "grouping_key": "run (data-taking run; runs nested in periods p1-p4)", "split_manifest": "work/splits.json",
        "split_check": {"tool": "check_split_integrity.py", "result": "pass" if split_ok else "fail",
                        "report": "work/split_check.json"},
        "training_domain": {f: [float(x[tr][:, i].min()), float(x[tr][:, i].max())] for i, f in enumerate(FEATURES)},
        "preprocessing": [{"step": "standardize", "features": FEATURES, "fit_on": "train"},
                          {"step": "quadratic expansion", "terms": "1, z_i, z_i^2, z_i z_j"}] if a.trainer == "numpy"
                         else tsum["preprocessing"],
        "weights": {"source": "generator weights x L x sigma / N_generated (SYNTHETIC; NLO-like counter-events +-w)",
                    "negative_weight_treatment": "signed",
                    "class_balancing": {"training": "per class, signed weights rescaled to equal sums (train split)",
                                        "evaluation": "physics weights unchanged (metrics, calibration, templates)",
                                        "prior_correction": f"logit + ln r, r = {prior_r:.6g} (physics S/B on the calibration fit sample)"},
                    "used_in": ["loss", "metrics", "calibration", "templates"]},
        "model_hash": ("sha256:" + hashlib.sha256((work / "model.json").read_bytes()).hexdigest()) if a.trainer == "numpy"
                      else tsum["model_hash"],
        "checkpoint": "work/model.json" if a.trainer == "numpy" else "work/torch/best.pt",
        "environment": environment, "metrics": rnd(metrics, 10),
        "scores": {"val": "work/val_scores.csv", "test": "work/test_scores.csv"}}
    (work / "run_summary.json").write_text(json.dumps(run_summary, indent=1) + "\n")
    shift_found = ds["per_variable"][SHIFT_FEATURE]["shift_detected"]
    flagged = sorted(k for k, v in ds["per_variable"].items() if v["shift_detected"])
    (work / "domain_shift.json").write_text(json.dumps({"domain_shift": {
        "control_sample": f"SYNTHETIC data-like background control sample ({CONTROL_SIZE} events, {SHIFT_FEATURE} scaled "
                          f"by {SHIFT} by construction)",
        "method": f"weighted Kolmogorov-Smirnov, held-out simulation background versus control sample, noise floor = "
                  f"95% quantile over {NULL_REPLICAS} seeded unshifted replicas; inference-time domain flags on the "
                  "pseudo-data (check_surrogate_domain.py)",
        "result": rnd({"verdict": f"shift above the noise floor in {', '.join(flagged)}; the measured {SHIFT_FEATURE} "
                                  f"scale enters the template fit as the shape nuisance {SHIFT_NUISANCE}",
                       "variables_above_noise_floor": flagged, "per_variable": ds["per_variable"],
                       "measured_scale": ds["measured_scale"],
                       "delta_mu_asimov_from_measured_scale": asimov_shift["mu_hat"] - MU_TRUE,
                       "pseudo_data_domain_flags": dict(ood_counts, n=n_q)}),
        "status": "checked", "outcome": "bounded-by-nuisance",
        "nuisance": {"name": SHIFT_NUISANCE, "ref": "artifacts/statistical_result.json#extension.nuisances"}}},
        indent=1) + "\n")
    downstream = rnd([
        {"metric": "Asimov closure of the signal strength in the calibrated-score template fit",
         "value": asimov["mu_hat"] - MU_TRUE, "criterion": f"abs < {CRITERIA['asimov_mu_abs_dev_max']}"},
        {"metric": "toy pull mean and width of mu, and 68% interval coverage", "pull_mean": toy["pull_mean"],
         "pull_width": toy["pull_width"], "coverage_68": toy["coverage_68"], "n_toys": toy["n"]},
        {"metric": "expected uncertainty on mu (Asimov, profile likelihood)", "err_down": asimov["err_down"],
         "err_up": asimov["err_up"]},
        {"metric": f"shift of mu on Asimov when the background {SHIFT_FEATURE} scale is the one measured in the "
                   "control sample (fit without the nuisance)", "delta_mu": asimov_shift["mu_hat"] - MU_TRUE,
         "note": f"the fit carries this shift as the nuisance {SHIFT_NUISANCE}; the pseudo-data are generated "
                 "without the shift"}])
    (work / "downstream.json").write_text(json.dumps(downstream, indent=1) + "\n")
    code_ml, ml_out = write_ml_artifact(out, a.created)
    ml_path = out / "artifacts" / "ml_artifact.json"
    vocab = Vocabulary.with_profiles([PROFILE])
    ml_doc = json.loads(ml_path.read_text()) if code_ml == 0 else None
    if ml_doc is not None:  # bind the illustrative profile, then revalidate what is kept
        ml_doc["bindings"]["experiments"] = [{"profile": PROFILE["id"], "version": PROFILE["version"]}]
        ml_doc["versions"]["profiles"] = {PROFILE["id"]: PROFILE["version"]}
        ml_path.write_text(json.dumps(ml_doc, indent=1) + "\n")
    ml_rep = validate_artifact(ml_doc, vocab) if ml_doc else None

    # 7b. fit the pseudo-data; statistical-result linked to the ml-artifact by id and sha256
    fit = fit_mu(model_fit, counts.tolist(), aux0)
    from core.stats.likelihood_limits import shape_gof
    gof_doc = {"bins": [{"n": int(n), "b": b, "s": s, "mc_stat": math.sqrt(v)} for n, b, s, v in
                        zip(counts, b_t, s_t, t["background"]["sumw2"])]}
    g = shape_gof(gof_doc, 0, 1)
    gof = {"statistic": g["statistic"], "ndf": g["asymptotic_chi2_reference"]["ndf"], "p": g["asymptotic_chi2_reference"]["p_value"]}
    ml_sha = hashlib.sha256(ml_path.read_bytes()).hexdigest() if ml_doc else ""
    stat = stat_artifact(fit, asimov, toy, ml_doc or {"artifact_id": "", "contract_version": "", "status": []},
                         "artifacts/ml_artifact.json", ml_sha, gof, a.created)
    (out / "artifacts" / "statistical_result.json").write_text(json.dumps(stat, indent=1) + "\n")
    stat_rep = validate_artifact(stat, vocab)
    contract = {"ml_artifact": {"ok": bool(ml_rep and ml_rep.ok), "errors": [f.message for f in ml_rep.errors] if ml_rep else ["not written"],
                                "unresolved": [f.code for f in ml_rep.findings if f.severity == "unresolved"] if ml_rep else []},
                "statistical_result": {"ok": stat_rep.ok, "errors": [f.message for f in stat_rep.errors],
                                       "unresolved": [f.code for f in stat_rep.findings if f.severity == "unresolved"]}}
    linked = bool(ml_doc) and stat["inputs"][0]["artifact_id"] == ml_doc["artifact_id"] \
        and stat["inputs"][0]["sha256"] == hashlib.sha256(ml_path.read_bytes()).hexdigest()

    err = fit["err_up"] if fit["mu_hat"] < MU_TRUE else fit["err_down"]
    passes = {
        "grouped_split_check_strict": code_check == 0 and split_ok,
        "rowlevel_split_leak_caught": code_row == 1 and row_report["status"] == "failed",
        "calibration_ece_after": calib["metrics"]["ece_after"] < CRITERIA["ece_after_max"]
                                 and calib["sample_check"]["disjoint"],
        "domain_shift_detects_injected_shift": bool(shift_found),
        "pseudo_data_out_of_domain_fraction": ood_counts["outside"] / n_q < CRITERIA["ood_outside_fraction_max"],
        "asimov_closure": abs(asimov["mu_hat"] - MU_TRUE) < CRITERIA["asimov_mu_abs_dev_max"],
        "toy_pull_mean": abs(toy["pull_mean"]) < CRITERIA["toy_mean_pull_abs"],
        "toy_pull_width": CRITERIA["toy_pull_width"][0] < toy["pull_width"] < CRITERIA["toy_pull_width"][1],
        "toy_coverage_68": CRITERIA["toy_coverage_68"][0] < toy["coverage_68"] < CRITERIA["toy_coverage_68"][1],
        "pseudo_data_fit": abs(fit["mu_hat"] - MU_TRUE) < CRITERIA["pseudo_data_mu_within_sigma"] * err,
        "ml_artifact_valid": code_ml == 0 and contract["ml_artifact"]["ok"] and not contract["ml_artifact"]["unresolved"],
        "statistical_result_valid_and_linked": contract["statistical_result"]["ok"] and linked,
    }
    results = rnd({
        "label": "SYNTHETIC and ILLUSTRATIVE: invented samples, pseudo-data not observed data; describes no experiment",
        "profiles_loaded": [PROFILE["id"]], "trainer": a.trainer, "seed": a.seed, "criteria": CRITERIA, "pass": passes,
        "config": {"features": FEATURES, "units": UNITS, "lumi_fb": LUMI_FB, "xsec_fb": XSEC_FB, "periods": PERIODS,
                   "runs_per_period": RUNS_PER_PERIOD, "mc_per_run": MC_PER_RUN, "shift": [SHIFT_FEATURE, SHIFT],
                   "mu_true": MU_TRUE, "edges": EDGES, "fractions": FRACTIONS, "working_point_eff_s": WP_EFF_S},
        "samples": {"n_mc": len(y), "n_negative_weight": int(np.sum(w < 0)),
                    "negative_weight_fraction_background": float(np.sum(w < 0) / np.sum(y == 0)),
                    "sum_w": {"signal": float(w[y == 1].sum()), "background": float(w[y == 0].sum())},
                    "pseudo_data": {k: pd_[k] for k in ("n_background_drawn", "n_signal_drawn")}},
        "splits": {"summary": {k: split_summary.get(k) for k in ("mode", "seed", "groups", "splits")},
                   "check": {"exit": code_check, "status": split_report["status"]},
                   "rowlevel": {"exit": code_row, "status": row_report["status"], "failure_kind": row_report.get("failure_kind"),
                                "leaked_groups": len(row_report.get("group_leakage") or {})}},
        "training": {"model": model_info,
                     "weights": {"training_sum_per_class": [float(w_train[y[tr] == c].sum()) for c in (0, 1)],
                                 "evaluation_sum_per_class_train_split": [float(w[tr][y[tr] == c].sum()) for c in (0, 1)],
                                 "n_negative_train": int(np.sum(w_train < 0))}},
        "metrics": metrics,
        "calibration": {"method": calib["calibration"]["method"], "params": calib["calibration"]["params"],
                        "prior_ratio_change": prior_r, "fit_sample": calib["calibration"]["fit_sample"],
                        "eval_sample": calib["calibration"]["validation"]["sample"],
                        **{k: calib["metrics"][k] for k in ("ece_before", "ece_after", "ece_floor_after", "nll_before", "nll_after")}},
        "domain_shift": {"per_variable": ds["per_variable"], "measured_scale": ds["measured_scale"],
                         "delta_mu_asimov_from_measured_scale": asimov_shift["mu_hat"] - MU_TRUE,
                         "pseudo_data_domain_flags": dict(ood_counts, n=n_q, method=ood_rep.get("method"),
                                                          exit=code_ood)},
        "templates": {"edges": EDGES, **t, "scale_to_full_mc": scale_by_class, "source": "test split"},
        "pseudo_data_counts": counts.tolist(),
        "fit": {**fit, "gof": gof},
        "asimov": asimov, "toys": toy,
        "artifacts": {"ml_artifact_id": ml_doc["artifact_id"] if ml_doc else None, "statistical_result_inputs_link": linked,
                      "ml_artifact_writer": {"exit": code_ml, "findings": [f.get("code") for f in ml_out.get("findings", [])]}},
        "contract_validation": contract,
    })
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    figure(out, score, t, counts, ctrl, calib)
    write_report(out, results)
    print(json.dumps({"pass": passes}, indent=1))
    return 0 if all(passes.values()) else 1


def figure(out, score, t, counts, ctrl, calib) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    e = np.array(EDGES)
    b, s = np.array(t["background"]["sumw"]), np.array(t["signal"]["sumw"])
    ax[0].stairs(b / np.diff(e), e, label="background template (test split, at L)")
    ax[0].stairs((b + MU_TRUE * s) / np.diff(e), e, label=f"background + signal (mu = {MU_TRUE})")
    ax[0].stairs(np.histogram(score(ctrl), e)[0] / len(ctrl) * b.sum() / np.diff(e), e, ls="--",
                 label=f"control sample ({SHIFT_FEATURE} x {SHIFT}), scaled to the background")
    n = np.asarray(counts)
    c = 0.5 * (e[1:] + e[:-1])
    ax[0].errorbar(c, n / np.diff(e), np.sqrt(n) / np.diff(e), fmt="ko", ms=3, label="pseudo-data (SYNTHETIC)")
    ax[0].set(xlabel="calibrated P(signal)", ylabel="events per unit probability", yscale="log")
    ax[0].legend(fontsize=6)
    for key, style in (("before", "s--"), ("after", "o-")):
        rows = [r for r in calib["reliability"][key]["bins"] if r["observed"] is not None]
        ax[1].errorbar([r["mean_pred"] for r in rows], [r["observed"] for r in rows],
                       [r["observed_unc"] for r in rows], fmt=style, ms=3, label=f"{key} temperature (test split)")
    ax[1].plot([0, 1], [0, 1], "k:", lw=1)
    ax[1].set(xlabel="mean predicted P(signal)", ylabel="observed signal fraction (weighted)")
    ax[1].legend(fontsize=7)
    fig.suptitle("SYNTHETIC J9: classifier scores and calibration (illustrative)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "scores_and_calibration.png", dpi=110, metadata={"Software": None})
    plt.close(fig)


def write_report(out: Path, r: dict) -> None:
    yes = lambda k: "pass" if r["pass"][k] else "FAIL"  # noqa: E731
    cr, m, c, d, f = r["criteria"], r["metrics"], r["calibration"], r["domain_shift"], r["fit"]
    flags = d["pseudo_data_domain_flags"]
    lines = [
        "# J9 report: classifier to signal-strength fit (SYNTHETIC, ILLUSTRATIVE)", "",
        f"**Status: synthetic.** {r['label']}. Profile bound: `{r['profiles_loaded'][0]}` (illustrative); its generator "
        "and detector modules are not used. The pseudo-data are drawn from the same invented model and are labelled "
        "pseudo-data, never observed data.", "",
        f"Reproduce: `python3 examples/ml-classifier-to-inference/run.py --seed {r['seed']} --toys {r['toys']['n']}` "
        f"(from the plugin root; trainer `{r['trainer']}`). Intermediate files are written to `work/` (not committed).", "",
        "## Pre-declared criteria and outcome", "",
        "| Check | Criterion | Result |", "|---|---|---|",
        f"| Grouped split by run | check_split_integrity.py --strict passes | {yes('grouped_split_check_strict')} |",
        f"| Row-level split of the same rows | caught as leakage (exit 1) | {yes('rowlevel_split_leak_caught')} ({r['splits']['rowlevel']['leaked_groups']} runs leak) |",
        f"| Calibration (fit on val, evaluated on test) | ECE after < {cr['ece_after_max']} | {yes('calibration_ece_after')} (ECE {c['ece_before']:.4f} -> {c['ece_after']:.4f}, floor {c['ece_floor_after']:.4f}) |",
        f"| Domain-shift check | detects the injected {r['config']['shift'][0]} shift | {yes('domain_shift_detects_injected_shift')} |",
        f"| Domain flags on pseudo-data | outside fraction < {cr['ood_outside_fraction_max']} | {yes('pseudo_data_out_of_domain_fraction')} ({flags['outside']}/{flags['n']} outside, {flags['sparse']} sparse) |",
        f"| Asimov closure of mu | abs(mu_hat - {r['config']['mu_true']}) < {cr['asimov_mu_abs_dev_max']} | {yes('asimov_closure')} (mu_hat {r['asimov']['mu_hat']:.6f}) |",
        f"| Toys: pull mean | abs < {cr['toy_mean_pull_abs']} | {yes('toy_pull_mean')} ({r['toys']['pull_mean']:.3f}) |",
        f"| Toys: pull width | in {tuple(cr['toy_pull_width'])} | {yes('toy_pull_width')} ({r['toys']['pull_width']:.3f}) |",
        f"| Toys: 68% interval coverage | in {tuple(cr['toy_coverage_68'])} | {yes('toy_coverage_68')} ({r['toys']['coverage_68']:.3f}, {r['toys']['n']} toys) |",
        f"| Pseudo-data fit | within {cr['pseudo_data_mu_within_sigma']} sigma of mu_true | {yes('pseudo_data_fit')} |",
        f"| ml-artifact | valid, no unresolved finding | {yes('ml_artifact_valid')} |",
        f"| statistical-result | valid, links the ml-artifact by id and sha256 | {yes('statistical_result_valid_and_linked')} |",
        "", "## Result on the pseudo-data", "",
        f"mu = {f['mu_hat']:.3f} +{f['err_up']:.3f} -{f['err_down']:.3f} (68.27% profile-likelihood interval; true "
        f"mu = {r['config']['mu_true']}); saturated goodness of fit {f['gof']['statistic']:.2f} / {f['gof']['ndf']} "
        f"(asymptotic p = {f['gof']['p']:.2f}). Asimov expected uncertainty +{r['asimov']['err_up']:.3f} "
        f"-{r['asimov']['err_down']:.3f}.", "",
        "## Classifier (held-out test split, physics weights)", "",
        f"Weighted AUC {m['test']['auc_weighted']:.4f} (validation {m['val']['auc_weighted']:.4f}). Working point fixed on "
        f"validation at signal efficiency {r['config']['working_point_eff_s']}: on test eff_S = "
        f"{m['test']['working_point']['eff_s']:.3f}, eff_B = {m['test']['working_point']['eff_b']:.4f} ± "
        f"{m['test']['working_point']['eff_b_unc']:.4f} (rejection {m['test']['working_point']['rejection']:.1f}), "
        f"Asimov significance {m['test']['asimov_significance_at_wp']:.2f} for the counting experiment at that cut. "
        "These are ML metrics; the physics validation is the effect on mu above.", "",
        f"Weights: {r['samples']['n_negative_weight']} negative-weight background events "
        f"({100 * r['samples']['negative_weight_fraction_background']:.1f}% of background MC). Training weights are "
        "class-balanced and signed; metrics, calibration and templates use the physics weights unchanged. The "
        f"classifier is calibrated to the physics class ratio (prior correction r = {c['prior_ratio_change']:.4g}) and "
        f"then by temperature T = {c['params']['temperature']:.4f}, fitted on `{c['fit_sample']}` and evaluated on "
        f"`{c['eval_sample']}`. ECE (10 equal-width bins, weighted) {c['ece_before']:.4f} before and {c['ece_after']:.4f} "
        f"after the temperature, against a finite-sample floor of {c['ece_floor_after']:.4f}: differences at the level "
        "of the floor are not resolved by this test sample.", "",
        "## Domain shift", "",
        "| Variable | KS D (simulation vs control) | noise floor (95%) | above floor |", "|---|---|---|---|"]
    for k, v in d["per_variable"].items():
        lines.append(f"| {k} | {v['ks_d']:.4f} | {v['noise_floor_95']:.4f} | {'yes' if v['shift_detected'] else 'no'} |")
    lines += [
        "", f"The control sample was built with {r['config']['shift'][0]} x {r['config']['shift'][1]}; the measured "
        f"scale (control over simulation mean) is {d['measured_scale']['control_over_simulation_mean']:.4f}. Rebuilding "
        f"the background template at that scale moves mu on Asimov data by {d['delta_mu_asimov_from_measured_scale']:+.4f}. "
        f"The fit carries that shift as the Gaussian-constrained shape nuisance `{SHIFT_NUISANCE}` (background template "
        "at the measured scale as +1 sigma), so the ml-artifact records the domain-shift outcome bounded-by-nuisance; "
        "the pseudo-data are generated without the shift.", "",
        "## Limitations (by construction)", "",
        "- One invented model generates simulation, control sample and pseudo-data; mismodeling of the simulation is "
        "studied only through the injected scale shift.",
        "- The signal template's MC statistics are not in the likelihood (only the background's, Barlow-Beeston-lite).",
        "- Templates are normalized to the full MC by event counts per class; the luminosity and cross sections carry no "
        "uncertainty.",
        "- Passing these checks shows the chain is internally consistent on synthetic data, nothing about a real analysis.",
        "", "Figure: `scores_and_calibration.png`. Artifacts: `artifacts/ml_artifact.json`, "
        "`artifacts/statistical_result.json` (status `synthetic`).", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
