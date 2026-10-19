#!/usr/bin/env python3
"""Cross-trained BDT for an analysis: k folds by event number, xgboost (primary) or scikit-learn (fallback) (ML3), for
a classifier or a regression.

Purpose: the executable path for a boosted-decision-tree classifier in a physics analysis, with the choices that bias
results made explicit: every event is scored only by a model that never saw it, hyperparameters are chosen on
validation events inside the training folds and reported on the test folds, negative event weights are handled by a
declared policy, and the run summary is the input of write_ml_artifact.py. See
<plugin root>/skills/hep-ml/references/multivariate-analysis-bdt-nn.md, "XGBoost in an analysis".

Method:
  folds    each event goes to fold (event number mod K) when the event key is one integer column, else to
           sha256(key) mod K for a composite key such as (run, event); rows that share a key share a fold. The fold
           manifest (fold0..foldK-1, groups) is checked with check_split_integrity.py before training.
  training for test fold k the model trains on the other folds; a validation part of those folds (sha256 of the key,
           fraction validation_fraction) drives early stopping and the hyperparameter choice, never the test fold.
           With no fold's validation part holding both classes the run is refused before training (exit 2).
  selection every grid point of "hyperparameters" is trained for every fold; the point with the best mean objective
           on the validation parts is kept: weighted AUC ("auc") or the Asimov significance
           Z_A = sqrt(2((s+b) ln(1+s/b) - s)) maximized over the score cut ("asimov", s and b = physical-weight sums
           above the cut times asimov_scale). Test-fold metrics are reported once, for that point.
  weights  --negative-weights has no default: reject (exit 3 when a negative weight is present; XGBoost refuses
           negative weights since 1.3.0), abs-train-signed-eval (train on |w|, evaluate with signed w) or drop (drop
           negative-weight events from training; evaluation keeps every event with its signed weight). Training and
           physical weights are recorded separately, with the fraction and sum of negative weights.
  checks   overtraining: the weighted Kolmogorov distance between the training and test score distributions per
           class and the effective entries n_eff = (sum w)^2 / sum w^2; a distance, never a p-value. Importance
           (xgboost): gain, cover and TreeSHAP (mean |pred_contribs| on the test folds). Working points: score cuts
           at the target signal efficiencies, from the out-of-fold scores with physical weights (simulation).
  regression  "task": "regression" fits the numeric "label" column (for example an energy calibration) with squared
           error; "objective" must be "rmse" (the hyperparameter point with the lowest weighted validation RMSE is kept).
           The test folds give the RMSE, the mean bias and the ml-artifact regression checks: response (median of
           prediction / target) and resolution (half the central 68% width of that ratio) in bins of the true and of the
           predicted value, the outlier fraction (|ratio - median| beyond 5 resolutions), and closure on another truth
           spectrum, which needs a second sample and is recorded as not run. No working points.
  sculpting with "mass_column" (classification): the Jensen-Shannon distance (base 2, in [0, 1]) between the background
           mass shapes that pass and fail each working-point cut (or the median score cut without working points), on
           "mass_bins" quantile bins of the background mass, with |physical weights|; 0 means no sculpting.
  models   xgboost models are saved with save_model as JSON or UBJSON (model_fold<k>.json|ubj); model_hash is the
           sha256 of those files. scikit-learn has no pickle-free format: its models are not saved, and model_hash is
           the sha256 of the tree node arrays. No pickle is written or read.
Input:
  --data FILE    CSV (header row), .npz (one array per column; loaded without pickle), .parquet (pyarrow) or .root
                 (uproot; config "tree")
  --config JSON  {"features": [...], "label": COL, "signal_label": 1, "weight": COL, "event_number": COL or [COLS],
                  "folds": K, "backend": "xgboost"|"sklearn", "hyperparameters": {"max_depth": [...],
                  "learning_rate": [...], "n_estimators": [...]}, "objective": "auc"|"asimov",
                  optional: "id" (row id column; default the row index), "missing_values": {feature: sentinel},
                  "mass_column", "seed" (0), "n_threads" (1), "early_stopping_rounds" (0 = off),
                  "validation_fraction" (0.2), "working_point_efficiencies" ([]), "tree_method" (xgboost, "hist"),
                  "model_format" ("json"|"ubj"), "asimov_scale" (1.0), "units" ({feature: unit}), "tree" (ROOT)}
Output (--out-dir): fold_manifest.json, split_report.json, scores.csv (id, fold, label, weight, score), the models,
run_summary.json (accepted by write_ml_artifact.py); JSON on stdout with "status", "status_label", "inputs",
"defaults_used", metrics, working points, overtraining, importance and weights.
Validity: binary classification; deterministic for a fixed seed and thread count on one machine and library version.
Exit codes: 0 ok; 2 bad input (missing column, bad config, missing --negative-weights, a fold or all validation
parts too small); 3 incomplete or a missing dependency (numpy, xgboost or scikit-learn, pyarrow, uproot: the output
gives the pip command; negative weights under reject; a leaky or incomplete fold manifest).
Run: python3 <plugin root>/skills/hep-ml/scripts/train_bdt.py --data events.csv --config bdt.json \
       --negative-weights abs-train-signed-eval --out-dir bdt_run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

POLICIES = ("reject", "abs-train-signed-eval", "drop")
BACKENDS = ("xgboost", "sklearn")
INSTALL = {"numpy": "pip install 'numpy>=2.4,<3'",
           "xgboost": "pip install 'xgboost>=3.4,<4'  (optional extra `bdt`: pip install '.[bdt]')",
           "sklearn": "pip install 'scikit-learn>=1.9,<2'  (optional extra `bdt`: pip install '.[bdt]')",
           "pyarrow": "pip install pyarrow  (for Parquet input; or use CSV/.npz)",
           "uproot": "pip install uproot awkward  (optional extra `root-uproot`; for ROOT input)"}
DEFAULTS = {"signal_label": 1, "seed": 0, "n_threads": 1, "early_stopping_rounds": 0, "validation_fraction": 0.2,
            "working_point_efficiencies": [], "tree_method": "hist", "model_format": "json", "asimov_scale": 1.0,
            "missing_values": {}, "units": {}, "task": "classification", "mass_bins": 20}
REQUIRED = ("features", "label", "weight", "event_number", "folds", "backend", "hyperparameters", "objective")


class InputError(ValueError):
    """Bad input: exit 2."""


class Stop(Exception):
    """A run that cannot finish: status incomplete or missing-dependency (exit 3)."""

    def __init__(self, status, **fields):
        super().__init__(fields.get("reason") or fields.get("error"))
        self.status, self.fields = status, fields


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def need(module):
    try:
        return __import__(module)
    except ImportError as exc:
        raise Stop("missing-dependency", error=f"{module} is not installed ({exc})", install=INSTALL[module]) from exc


# ---------------------------------------------------------------- input

def load_config(path) -> tuple[dict, list[str]]:
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read the config {path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise InputError("the config must be a JSON object")
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise InputError(f"config is missing {missing} (no defaults for these)")
    defaults_used = sorted(k for k in DEFAULTS if k not in cfg)
    cfg = {**json.loads(json.dumps(DEFAULTS)), **cfg}
    if cfg["backend"] not in BACKENDS:
        raise InputError(f"backend must be one of {BACKENDS}")
    if cfg["task"] not in ("classification", "regression"):
        raise InputError("task must be classification or regression")
    if cfg["task"] == "regression":
        if cfg["objective"] != "rmse":
            raise InputError("a regression needs objective rmse (squared-error loss, lowest validation RMSE kept)")
        if cfg.get("mass_column") or cfg["working_point_efficiencies"]:
            raise InputError("mass_column and working_point_efficiencies apply to a classifier only")
    elif cfg["objective"] not in ("auc", "asimov"):
        raise InputError("objective must be auc or asimov")
    if not isinstance(cfg["mass_bins"], int) or isinstance(cfg["mass_bins"], bool) or cfg["mass_bins"] < 2:
        raise InputError("mass_bins must be an integer >= 2")
    if not isinstance(cfg["folds"], int) or isinstance(cfg["folds"], bool) or cfg["folds"] < 2:
        raise InputError("folds must be an integer >= 2")
    if not (isinstance(cfg["features"], list) and cfg["features"] and all(isinstance(f, str) for f in cfg["features"])):
        raise InputError("features must be a non-empty list of column names")
    hp = cfg["hyperparameters"]
    if not isinstance(hp, dict) or not hp or not all(isinstance(v, list) and v for v in hp.values()):
        raise InputError("hyperparameters must map names to non-empty lists of values")
    unknown = set(hp) - {"max_depth", "learning_rate", "n_estimators", "min_child_weight", "subsample", "reg_lambda"}
    if unknown:
        raise InputError(f"unknown hyperparameters {sorted(unknown)}")
    if not 0 < float(cfg["validation_fraction"]) < 1:
        raise InputError("validation_fraction must be in (0, 1)")
    if cfg["model_format"] not in ("json", "ubj"):
        raise InputError("model_format must be json or ubj (no pickle)")
    if cfg.get("mass_column") and cfg["mass_column"] in cfg["features"]:
        raise InputError("mass_column must not be a training feature")
    for e in cfg["working_point_efficiencies"]:
        if not 0 < float(e) <= 1:
            raise InputError("working_point_efficiencies must be in (0, 1]")
    return cfg, defaults_used


def read_table(path: Path, cfg: dict) -> dict[str, list]:
    """Column name -> list of values (strings or numbers)."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                cols: dict[str, list] = {c: [] for c in (reader.fieldnames or [])}
                for row in reader:
                    for c in cols:
                        cols[c].append(row[c])
        except OSError as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
        return cols
    np = need("numpy")
    if suffix == ".npz":
        try:
            with np.load(path, allow_pickle=False) as z:
                return {k: z[k].tolist() for k in z.files}
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
    if suffix == ".parquet":
        need("pyarrow")
        import pyarrow.parquet as pq
        return pq.read_table(path).to_pydict()
    if suffix == ".root":
        uproot = need("uproot")
        if not cfg.get("tree"):
            raise InputError("ROOT input needs config 'tree'")
        tree = uproot.open(path)[cfg["tree"]]
        return {k: v.tolist() for k, v in tree.arrays(library="np").items()}
    raise InputError(f"unsupported input format {suffix!r} (csv, npz, parquet, root)")


def event_keys(cols: dict, cfg: dict, n: int) -> tuple[list[str], str, list[int]]:
    key_cols = cfg["event_number"] if isinstance(cfg["event_number"], list) else [cfg["event_number"]]
    for c in key_cols:
        if c not in cols:
            raise InputError(f"event-number column {c!r} is not in the data")
    parts = [[str(cols[c][i]).strip() for c in key_cols] for i in range(n)]
    keys = [json.dumps(p) if len(p) > 1 else p[0] for p in parts]
    folds_k = cfg["folds"]
    if len(key_cols) == 1:
        try:
            nums = [int(float(k)) for k in keys]
            if all(float(k) == int(float(k)) for k in keys):
                return keys, f"event number mod {folds_k}", [x % folds_k for x in nums]
        except ValueError:
            pass
    folds = [int(hashlib.sha256(k.encode()).hexdigest()[:16], 16) % folds_k for k in keys]
    return keys, f"sha256(event key) mod {folds_k}", folds


def is_validation(key: str, fraction: float) -> bool:
    return int(hashlib.sha256(f"validation:{key}".encode()).hexdigest()[:16], 16) / 2.0 ** 64 < fraction


# ---------------------------------------------------------------- metrics (signed weights)

def weighted_auc(np, s, y, w):
    order = np.argsort(-s, kind="mergesort")
    s, y, w = s[order], y[order], w[order]
    ws, wb = np.where(y == 1, w, 0.0), np.where(y == 0, w, 0.0)
    ts, tb = ws.sum(), wb.sum()
    if ts == 0 or tb == 0:
        return float("nan")
    # group ties so tied scores share one ROC step
    _, idx = np.unique(-s, return_index=True)
    cs, cb = np.cumsum(ws), np.cumsum(wb)
    ends = np.append(idx[1:] - 1, len(s) - 1)
    tpr = np.concatenate([[0.0], cs[ends] / ts])
    fpr = np.concatenate([[0.0], cb[ends] / tb])
    return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) / 2.0))


def asimov_z(s, b):
    if s <= 0 or b <= 0:
        return 0.0
    return math.sqrt(max(2.0 * ((s + b) * math.log1p(s / b) - s), 0.0))


def best_asimov(np, s, y, w, scale):
    order = np.argsort(-s, kind="mergesort")
    ys, ws = y[order], w[order]
    cs = np.cumsum(np.where(ys == 1, ws, 0.0)) * scale
    cb = np.cumsum(np.where(ys == 0, ws, 0.0)) * scale
    return max((asimov_z(float(a), float(b)) for a, b in zip(cs, cb)), default=0.0)


def n_eff(np, w):
    sw2 = float(np.sum(w * w))
    return float(np.sum(w)) ** 2 / sw2 if sw2 > 0 else 0.0


def ks_distance(np, a, wa, b, wb):
    """Weighted Kolmogorov distance sup |F_a - F_b| (a distance; no p-value)."""
    grid = np.unique(np.concatenate([a, b]))
    oa, ob = np.argsort(a, kind="mergesort"), np.argsort(b, kind="mergesort")
    fa = np.cumsum(wa[oa]) / wa.sum()
    fb = np.cumsum(wb[ob]) / wb.sum()
    ia = np.searchsorted(a[oa], grid, side="right") - 1
    ib = np.searchsorted(b[ob], grid, side="right") - 1
    va = np.where(ia >= 0, fa[np.clip(ia, 0, None)], 0.0)
    vb = np.where(ib >= 0, fb[np.clip(ib, 0, None)], 0.0)
    return float(np.max(np.abs(va - vb)))


def weighted_rmse(np, pred, truth, w):
    return float(math.sqrt(np.sum(w * (pred - truth) ** 2) / np.sum(w)))


def _wquantile(np, v, w, q):
    o = np.argsort(v, kind="mergesort")
    c = np.cumsum(w[o]) / w.sum()
    return float(v[o][min(int(np.searchsorted(c, q)), len(v) - 1)])


def regression_checks(np, pred, truth, w, bins=10):
    """Response (median of pred / truth) and resolution (half the 16-84% width) in quantile bins of the truth and of
    the prediction; outlier fraction beyond 5 resolutions of the global median; closure needs a second sample."""
    ok = truth != 0
    ratio, aw = pred[ok] / truth[ok], np.abs(w[ok])

    def binned(var):
        edges = np.unique(np.quantile(var, np.linspace(0, 1, bins + 1)))
        rows = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (var >= lo) & ((var < hi) | (hi == edges[-1]))
            if m.sum() < 5:
                continue
            r, ww = ratio[m], aw[m]
            rows.append({"low": float(lo), "high": float(hi), "n": int(m.sum()), "response": _wquantile(np, r, ww, 0.5),
                         "resolution": 0.5 * (_wquantile(np, r, ww, 0.84) - _wquantile(np, r, ww, 0.16))})
        return rows
    med = _wquantile(np, ratio, aw, 0.5)
    res = 0.5 * (_wquantile(np, ratio, aw, 0.84) - _wquantile(np, ratio, aw, 0.16))
    out = float(aw[np.abs(ratio - med) > 5 * res].sum() / aw.sum()) if res > 0 else 0.0
    return {"response_vs_truth": binned(truth[ok]), "response_vs_reco": binned(pred[ok]),
            "closure_alt_spectrum": {"status": "not-run", "reason": "needs a second sample with another truth spectrum"},
            "outlier_fraction": out, "definition": "response = weighted median of prediction / truth; resolution = half "
                                                   "the weighted 16-84% width of that ratio; outliers beyond 5 resolutions",
            "computed_on": "out-of-fold predictions of every event"}


def js_distance(np, p, q):
    """Jensen-Shannon distance (base 2) between two histograms."""
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        nz = a > 0
        return float(np.sum(a[nz] * np.log2(a[nz] / b[nz])))
    return math.sqrt(max(0.5 * kl(p, m) + 0.5 * kl(q, m), 0.0))


def mass_sculpting(np, mass, score, y, w, cuts, bins):
    bkg = y == 0
    mb, sb, wb = mass[bkg], score[bkg], np.abs(w[bkg])
    edges = np.unique(np.quantile(mb, np.linspace(0, 1, bins + 1)))
    edges[-1] = np.nextafter(edges[-1], np.inf)
    rows = []
    for label, cut in cuts:
        hp, _ = np.histogram(mb[sb >= cut], edges, weights=wb[sb >= cut])
        hf, _ = np.histogram(mb[sb < cut], edges, weights=wb[sb < cut])
        rows.append({"cut": label, "score_cut": float(cut),
                     "js_distance": js_distance(np, hp, hf) if hp.sum() > 0 and hf.sum() > 0 else None,
                     "background_pass_fraction": float(wb[sb >= cut].sum() / wb.sum())})
    return rows


# ---------------------------------------------------------------- backends

class Xgb:
    name = "xgboost"

    def __init__(self, cfg, features):
        self.xgb, self.cfg, self.features = need("xgboost"), cfg, features

    def fit(self, np, xtr, ytr, wtr, xva, yva, wva, hp):
        reg = self.cfg["task"] == "regression"
        params = {"objective": "reg:squarederror" if reg else "binary:logistic", "eval_metric": "rmse" if reg else "logloss",
                  "tree_method": self.cfg["tree_method"],
                  "seed": int(self.cfg["seed"]), "nthread": int(self.cfg["n_threads"]),
                  "max_depth": int(hp.get("max_depth", 6)), "eta": float(hp.get("learning_rate", 0.3))}
        for k in ("min_child_weight", "subsample", "reg_lambda"):
            if k in hp:
                params[{"reg_lambda": "lambda"}.get(k, k)] = float(hp[k])
        dtr = self.xgb.DMatrix(xtr, label=ytr, weight=wtr, missing=np.nan, feature_names=self.features)
        es = int(self.cfg["early_stopping_rounds"])
        evals, kw = [], {}
        if es > 0 and len(yva):
            evals = [(self.xgb.DMatrix(xva, label=yva, weight=wva, missing=np.nan, feature_names=self.features), "val")]
            kw["early_stopping_rounds"] = es
        booster = self.xgb.train(params, dtr, num_boost_round=int(hp.get("n_estimators", 100)), evals=evals,
                                 verbose_eval=False, **kw)
        best = getattr(booster, "best_iteration", None) if es > 0 else None
        n = (best + 1) if best is not None else booster.num_boosted_rounds()
        return {"booster": booster, "rounds": int(n)}

    def predict(self, np, model, x):
        d = self.xgb.DMatrix(x, missing=np.nan, feature_names=self.features)
        return np.asarray(model["booster"].predict(d, iteration_range=(0, model["rounds"])), dtype=float)

    def save(self, model, path: Path) -> Path:
        out = path.with_suffix("." + self.cfg["model_format"])
        model["booster"].save_model(str(out))
        return out

    def importance(self, np, models, x_by_fold):
        gain, cover, shap, nshap = {}, {}, dict.fromkeys(self.features, 0.0), 0
        for m, x in zip(models, x_by_fold):
            for kind, acc in (("gain", gain), ("cover", cover)):
                for f, v in m["booster"].get_score(importance_type=kind).items():
                    acc[f] = acc.get(f, 0.0) + v / len(models)
            if len(x):
                d = self.xgb.DMatrix(x, missing=np.nan, feature_names=self.features)
                c = m["booster"].predict(d, pred_contribs=True, iteration_range=(0, m["rounds"]))
                for i, f in enumerate(self.features):
                    shap[f] += float(np.abs(c[:, i]).sum())
                nshap += len(x)
        return {"gain": {f: gain.get(f, 0.0) for f in self.features},
                "cover": {f: cover.get(f, 0.0) for f in self.features},
                "tree_shap_mean_abs": {f: v / max(nshap, 1) for f, v in shap.items()},
                "note": "gain and cover averaged over the fold models; TreeSHAP = mean |pred_contribs| on the test folds"}

    def version(self):
        return self.xgb.__version__


class Skl:
    name = "sklearn"

    def __init__(self, cfg, features):
        need("sklearn")
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        self.reg = cfg["task"] == "regression"
        self.cls = HistGradientBoostingRegressor if self.reg else HistGradientBoostingClassifier
        self.cfg, self.features = cfg, features
        try:
            from threadpoolctl import threadpool_limits
            self.limits = threadpool_limits
        except ImportError:
            self.limits = None

    def _make(self, hp, n_iter):
        md = hp.get("max_depth")
        return self.cls(max_depth=None if md is None else int(md), learning_rate=float(hp.get("learning_rate", 0.1)),
                        max_iter=int(n_iter), early_stopping=False, random_state=int(self.cfg["seed"]),
                        min_samples_leaf=int(hp.get("min_child_weight", 20)),
                        l2_regularization=float(hp.get("reg_lambda", 0.0)))

    def _fit(self, est, x, y, w):
        if self.limits:
            with self.limits(limits=int(self.cfg["n_threads"])):
                return est.fit(x, y, sample_weight=w)
        return est.fit(x, y, sample_weight=w)

    def fit(self, np, xtr, ytr, wtr, xva, yva, wva, hp):
        n = int(hp.get("n_estimators", 100))
        est = self._fit(self._make(hp, n), xtr, ytr, wtr)
        es = int(self.cfg["early_stopping_rounds"])
        if es > 0 and len(yva):
            losses = []
            staged = est.staged_predict(xva) if self.reg else est.staged_predict_proba(xva)
            for p in staged:
                if self.reg:
                    losses.append(float(np.sum(wva * (p - yva) ** 2) / np.sum(wva)))
                    continue
                q = np.clip(p[:, 1], 1e-12, 1 - 1e-12)
                losses.append(float(-np.sum(wva * (yva * np.log(q) + (1 - yva) * np.log(1 - q))) / np.sum(wva)))
            best, since = 0, 0
            for i, v in enumerate(losses):
                if v < losses[best]:
                    best, since = i, 0
                else:
                    since += 1
                    if since >= es:
                        break
            if best + 1 < n:
                est = self._fit(self._make(hp, best + 1), xtr, ytr, wtr)
        return {"est": est, "rounds": int(est.n_iter_)}

    def predict(self, np, model, x):
        if self.reg:
            return np.asarray(model["est"].predict(x), dtype=float)
        return np.asarray(model["est"].predict_proba(x)[:, 1], dtype=float)

    def save(self, model, path: Path):
        return None  # scikit-learn has no pickle-free model format: not saved

    def tree_hash(self, model) -> bytes:
        h = hashlib.sha256()
        for it in model["est"]._predictors:
            for pred in it:
                h.update(pred.nodes.tobytes())
        h.update(repr(model["est"]._baseline_prediction.tolist()).encode())
        return h.digest()

    def importance(self, np, models, x_by_fold):
        return {"note": "gain, cover and TreeSHAP need the xgboost backend; use permutation importance on the test folds"}

    def version(self):
        import sklearn
        return sklearn.__version__


# ---------------------------------------------------------------- run

def run(args) -> tuple[str, dict]:
    cfg, defaults_used = load_config(args.config)
    np = need("numpy")
    backend = (Xgb if cfg["backend"] == "xgboost" else Skl)(cfg, cfg["features"])
    cols = read_table(Path(args.data), cfg)
    reg = cfg["task"] == "regression"
    needed = (cfg["features"] + [cfg["label"], cfg["weight"]] + ([cfg["id"]] if cfg.get("id") else [])
              + ([cfg["mass_column"]] if cfg.get("mass_column") else []))
    absent = [c for c in needed if c not in cols]
    if absent:
        raise InputError(f"columns {absent} are not in the data")
    n = len(cols[cfg["label"]])
    if n < 2 * cfg["folds"]:
        raise InputError(f"{n} rows are too few for {cfg['folds']} folds")
    ids = [str(v).strip() for v in cols[cfg["id"]]] if cfg.get("id") else [str(i) for i in range(n)]
    if len(set(ids)) != n:
        raise InputError("row ids must be unique")
    try:
        x = np.array([[float(cols[f][i]) for f in cfg["features"]] for i in range(n)], dtype=float)
        w = np.array([float(v) for v in cols[cfg["weight"]]], dtype=float)
        if reg:
            y = np.array([float(v) for v in cols[cfg["label"]]], dtype=float)
        else:
            y = np.array([1 if str(v).strip() in (str(cfg["signal_label"]), str(float(cfg["signal_label"]))) else 0
                          for v in cols[cfg["label"]]], dtype=float)
        mass = np.array([float(v) for v in cols[cfg["mass_column"]]], dtype=float) if cfg.get("mass_column") else None
    except ValueError as exc:
        raise InputError(f"a feature, weight or label value is not numeric: {exc}") from exc
    for j, f in enumerate(cfg["features"]):
        if f in cfg["missing_values"]:
            x[x[:, j] == float(cfg["missing_values"][f]), j] = np.nan
    if not np.all(np.isfinite(w)):
        raise InputError("non-finite event weight")
    if reg and not np.all(np.isfinite(y)):
        raise InputError("non-finite regression target")
    if not reg and (y.sum() == 0 or y.sum() == n):
        raise InputError("both classes (signal_label and the rest) must be present")

    neg = w < 0
    weights_out = {"physical_weight_column": cfg["weight"], "policy": args.negative_weights,
                   "negative_count": int(neg.sum()), "negative_fraction": float(neg.mean()),
                   "negative_sum": float(w[neg].sum())}
    if args.negative_weights == "reject" and neg.any():
        raise Stop("incomplete", reason=(f"{int(neg.sum())} negative weights (fraction {neg.mean():.3g}, sum "
                                         f"{w[neg].sum():.6g}) under --negative-weights reject; XGBoost refuses "
                                         "negative weights since 1.3.0. Choose abs-train-signed-eval or drop, or remove "
                                         "them locally first (hep_metrics.cell_resample)"), weights=weights_out)
    w_train = np.abs(w) if args.negative_weights == "abs-train-signed-eval" else w.copy()
    train_ok = ~neg if args.negative_weights == "drop" else np.ones(n, dtype=bool)
    weights_out["training_weights"] = {"abs-train-signed-eval": "absolute values of the physical weights",
                                       "drop": "physical weights; negative-weight events left out of training",
                                       "reject": "physical weights (none negative)"}[args.negative_weights]

    keys, fold_method, fold = event_keys(cols, cfg, n)
    fold = np.array(fold)
    is_val = np.array([is_validation(k, float(cfg["validation_fraction"])) for k in keys])
    out_dir = Path(args.out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InputError(f"cannot create {out_dir}: {exc}") from exc
    K = cfg["folds"]
    manifest = {f"fold{k}": [ids[i] for i in range(n) if fold[i] == k] for k in range(K)}
    manifest["groups"] = {ids[i]: keys[i] for i in range(n)}
    man_path = out_dir / "fold_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    man_sha = hashlib.sha256(man_path.read_bytes()).hexdigest()
    check = subprocess.run([sys.executable, "-B", str(HERE / "check_split_integrity.py"), str(man_path), "--json",
                            "--strict"], capture_output=True, text=True, timeout=600)
    (out_dir / "split_report.json").write_text(check.stdout, encoding="utf-8")
    if check.returncode != 0:
        raise Stop("incomplete", reason="the fold manifest did not pass check_split_integrity.py --strict",
                   split_report=str(out_dir / "split_report.json"))
    usable, parts = [], []
    for k in range(K):
        if not reg and len(np.unique(y[fold == k])) < 2:
            raise InputError(f"fold {k} lacks a class; use more events or fewer folds")
        va = (fold != k) & is_val
        usable.append(bool(va.any()) and (reg or len(np.unique(y[va])) == 2))
        parts.append(f"fold {k}: {int(va.sum())}" + ("" if reg else f" ({int((y[va] == 1).sum())} signal)"))
    # hyperparameter selection averages the folds' validation objectives; a fold whose validation part is empty or
    # has one class adds nothing, but with no usable part every grid point is NaN, so refuse before training
    if not any(usable):
        raise InputError(f"no fold has a validation part with both classes ({'; '.join(parts)} events); whole "
                         f"event_number keys ({len(set(keys))} here) go to validation, so raise "
                         "validation_fraction, use fewer folds, a finer key or more events")

    grid_names = sorted(cfg["hyperparameters"])
    grid = [dict(zip(grid_names, combo)) for combo in itertools.product(*(cfg["hyperparameters"][g] for g in grid_names))]
    trained: dict = {}
    objective = []
    for gi, hp in enumerate(grid):
        vals = []
        for k in range(K):
            tr = (fold != k) & ~is_val & train_ok
            va = (fold != k) & is_val
            if not reg and len(np.unique(y[tr])) < 2:
                raise InputError(f"the training part of fold {k} lacks a class")
            model = backend.fit(np, x[tr], y[tr], w_train[tr], x[va & train_ok], y[va & train_ok],
                                w_train[va & train_ok], hp)
            trained[(gi, k)] = model
            if not usable[k]:  # nothing to score (scikit-learn refuses an empty array); nanmean skips it
                vals.append(float("nan"))
                continue
            sv = backend.predict(np, model, x[va])
            if reg:
                vals.append(-weighted_rmse(np, sv, y[va], np.abs(w[va])))
            elif cfg["objective"] == "auc":
                vals.append(weighted_auc(np, sv, y[va], w[va]))
            else:
                vals.append(best_asimov(np, sv, y[va], w[va], float(cfg["asimov_scale"])))
        objective.append(float(np.nanmean(vals)) if len(vals) else float("nan"))
    if not any(math.isfinite(o) for o in objective):
        raise InputError("no hyperparameter point has a finite validation objective (validation parts without "
                         "weight or separable events); raise validation_fraction, use fewer folds or more events")
    best = max(range(len(grid)), key=lambda i: (objective[i] if math.isfinite(objective[i]) else -math.inf, -i))
    models = [trained[(best, k)] for k in range(K)]

    score = np.empty(n)
    train_s, train_w, train_y = [], [], []
    for k in range(K):
        te = fold == k
        score[te] = backend.predict(np, models[k], x[te])
        tr = (fold != k) & ~is_val & train_ok
        train_s.append(backend.predict(np, models[k], x[tr]))
        train_w.append(w[tr])
        train_y.append(y[tr])
    ts, tw, ty = np.concatenate(train_s), np.concatenate(train_w), np.concatenate(train_y)

    with open(out_dir / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["id", "fold", "label", "weight", "prediction" if reg else "score"])
        for i in range(n):
            wr.writerow([ids[i], int(fold[i]), repr(float(y[i])) if reg else int(y[i]), repr(float(w[i])),
                         repr(float(score[i]))])

    regression_validation = None
    if reg:
        res = score - y
        test_metrics = {"rmse": weighted_rmse(np, score, y, np.abs(w)), "mean_bias": float(np.average(res, weights=np.abs(w))),
                        "rmse_per_fold": [weighted_rmse(np, score[fold == k], y[fold == k], np.abs(w[fold == k]))
                                          for k in range(K)],
                        "n_eff": n_eff(np, w), "evaluated_on": "out-of-fold predictions of every event, |physical weights|"}
        regression_validation = regression_checks(np, score, y, w)
        tr_res = ts - ty
        overtraining = {"train_test_distance": {"residual": {
            "ks_distance": ks_distance(np, tr_res, np.abs(tw), res, np.abs(w)), "n_eff_train": n_eff(np, tw),
            "n_eff_test": n_eff(np, w)}}, "note": "weighted Kolmogorov distance between the training-fold and test-fold "
                                                  "residual distributions; a distance, not a test"}
        wps = []
    else:
        test_metrics = {"auc_weighted": weighted_auc(np, score, y, w),
                        "auc_weighted_per_fold": [weighted_auc(np, score[fold == k], y[fold == k], w[fold == k])
                                                  for k in range(K)],
                        "n_eff": {"signal": n_eff(np, w[y == 1]), "background": n_eff(np, w[y == 0])},
                        "evaluated_on": "out-of-fold scores of every event, signed physical weights"}
        if cfg["objective"] == "asimov":
            test_metrics["asimov_z_best_cut"] = best_asimov(np, score, y, w, float(cfg["asimov_scale"]))
        weights_out["evaluated_weight_sum"] = {"signal": float(w[y == 1].sum()), "background": float(w[y == 0].sum())}

        overtraining = {"train_test_distance": {}, "note": ("weighted Kolmogorov distance between the training-fold and "
                                                            "test-fold score distributions and the effective entries; a "
                                                            "distance for judgement, not a test: no p-value is computed")}
        for cls, name in ((1, "signal"), (0, "background")):
            a, wa = ts[ty == cls], np.abs(tw[ty == cls])
            b, wb = score[y == cls], np.abs(w[y == cls])
            overtraining["train_test_distance"][name] = {
                "ks_distance": ks_distance(np, a, wa, b, wb) if len(a) and len(b) else None,
                "n_eff_train": n_eff(np, tw[ty == cls]), "n_eff_test": n_eff(np, w[y == cls])}

        wps = []
        sig = np.argsort(-score[y == 1], kind="mergesort")
        s_sorted, ws_sorted = score[y == 1][sig], w[y == 1][sig]
        tot_s, tot_b = float(w[y == 1].sum()), float(w[y == 0].sum())
        for target in cfg["working_point_efficiencies"]:
            cum = np.cumsum(ws_sorted) / tot_s
            idx = int(np.searchsorted(cum, float(target) - 1e-12))
            idx = min(idx, len(s_sorted) - 1)
            cut = float(s_sorted[idx])
            wps.append({"target_signal_efficiency": float(target), "score_cut": cut,
                        "signal_efficiency": float(w[(y == 1) & (score >= cut)].sum()) / tot_s,
                        "background_efficiency": float(w[(y == 0) & (score >= cut)].sum()) / tot_b,
                        "computed_on": "out-of-fold scores with physical weights (simulation)"})

    sculpting = None
    if mass is not None:
        cuts = ([(f"signal efficiency {wp['target_signal_efficiency']}", wp["score_cut"]) for wp in wps]
                or [("median score", float(np.median(score)))])
        sculpting = {"mass_column": cfg["mass_column"], "bins": int(cfg["mass_bins"]),
                     "working_points": mass_sculpting(np, mass, score, y, w, cuts, int(cfg["mass_bins"])),
                     "definition": "Jensen-Shannon distance (base 2) between the background mass shapes passing and "
                                   "failing the cut, |physical weights|, quantile bins of the background mass"}
    importance = backend.importance(np, models, [x[fold == k] for k in range(K)])
    h = hashlib.sha256()
    model_files = []
    for k, m in enumerate(models):
        path = backend.save(m, out_dir / f"model_fold{k}")
        if path is not None:
            h.update(path.read_bytes())
            model_files.append(str(path.resolve()))
        else:
            h.update(backend.tree_hash(m))
    model_hash = "sha256:" + h.hexdigest()

    finite = np.isfinite(x)
    domain = {f: [float(np.min(x[finite[:, j], j])), float(np.max(x[finite[:, j], j]))]
              for j, f in enumerate(cfg["features"]) if finite[:, j].any()}
    treatment = {"reject": "none-present", "abs-train-signed-eval": "abs",
                 "drop": "dropped" if neg.any() else "none-present"}[args.negative_weights]
    status_labels = list(dict.fromkeys(args.label or []))
    summary = {
        **({"status": status_labels} if status_labels else {}),
        "task": cfg["task"], "features": cfg["features"], "units": cfg["units"] or {},
        "labels": [cfg["label"]] if reg else ["background", "signal"],
        **({"output_semantics": "regression-value", "regression_validation": regression_validation} if reg else {}),
        "grouping_key": "+".join(cfg["event_number"]) if isinstance(cfg["event_number"], list) else cfg["event_number"],
        "split_manifest": str(man_path.resolve()), "split_manifest_sha256": man_sha,
        "split_check": {"tool": "check_split_integrity.py", "result": "pass",
                        "report": str((out_dir / "split_report.json").resolve())},
        "training_domain": domain,
        "preprocessing": ([{"step": "missing-value sentinels to NaN", "features": cfg["missing_values"]}]
                          if cfg["missing_values"] else []),
        "weights": {"source": cfg["weight"], "negative_weight_treatment": treatment, "class_balancing": "none",
                    "used_in": ["loss", "metrics"],
                    "training": {"negative_weight_treatment": ({"abs-train-signed-eval": "abs", "drop": "dropped",
                                                                "reject": "signed"}[args.negative_weights]
                                                               if neg.any() else "none-present"),
                                 "n_negative": int(neg.sum()) if args.negative_weights != "drop" else 0,
                                 "description": weights_out["training_weights"]},
                    "evaluation": {"weights": "signed physical weights", "n_negative": int(neg.sum()),
                                   "negative_sum": weights_out["negative_sum"]}},
        "model_hash": model_hash, "models": model_files,
        "environment": {"framework": f"{backend.name} {backend.version()} (numpy {np.__version__})", "device": "cpu",
                        "precision": "fp32", "seeds": {"seed": int(cfg["seed"]), "n_threads": int(cfg["n_threads"])}},
        "metrics": {"val": {"objective": cfg["objective"], "grid": [{"hyperparameters": g, "mean_objective": o}
                                                                    for g, o in zip(grid, objective)]},
                    "test": test_metrics},
        "scores": {"test": str((out_dir / "scores.csv").resolve())},
        "folds": {"k": K, "method": fold_method, "rows_per_fold": [int((fold == k).sum()) for k in range(K)]},
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=1, allow_nan=False), encoding="utf-8")
    result = {"backend": f"{backend.name} {backend.version()}",
              "folds": summary["folds"],
              "hyperparameters": {"selected": grid[best], "selected_on": "validation folds",
                                  "objective": cfg["objective"], "mean_objective": objective[best],
                                  "grid_size": len(grid)},
              "rounds_per_fold": [m["rounds"] for m in models],
              "metrics": {"test": test_metrics}, "working_points": wps, "overtraining": overtraining,
              "importance": importance, "weights": weights_out, "model_hash": model_hash,
              **({"mass_sculpting": sculpting} if sculpting else {}),
              "run_summary": str((out_dir / "run_summary.json").resolve()), "defaults_used_config": defaults_used}
    return "ok", result


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="events: CSV, .npz, .parquet (pyarrow) or .root (uproot)")
    ap.add_argument("--config", required=True, help="JSON configuration (see the docstring)")
    ap.add_argument("--negative-weights", required=True, choices=POLICIES,
                    help="no default: reject, abs-train-signed-eval or drop")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--label", action="append", help="artifact status label written into the run summary (repeatable)")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {tok.split("=")[0] for tok in (sys.argv[1:] if argv is None else argv) if tok.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    head = {"status_label": args.status, "inputs": inputs}
    try:
        status, out = run(args)
        defaults = (["status"] if "--status" not in given else []) + out.pop("defaults_used_config")
        print(json.dumps({"status": status, **head, "defaults_used": defaults, **out}, indent=1, allow_nan=False))
        return exit_code(status)
    except InputError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    except Stop as stop:
        print(json.dumps({"status": stop.status, **head, **stop.fields}, indent=1))
        return exit_code(stop.status)


if __name__ == "__main__":
    sys.exit(main())
