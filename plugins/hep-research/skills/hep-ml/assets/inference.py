#!/usr/bin/env python3
"""Inference for checkpoints written by train_classifier.py, with input and training-domain checks.

Reads the checkpoint metadata (feature names, preprocessing, training domain, labels, model shape), requires every
training feature to be present in the input CSV by name (refuses otherwise; order does not matter, extra columns are
ignored), applies the stored standardization, and checks each row with the training-domain model stored at training
time: scripts/check_surrogate_domain.py's DomainModel (whitened Mahalanobis, k-NN and subspace-residual distances,
thresholds calibrated on held-out training rows; the same method the surrogate check uses). A row is 'outside' (far
from the training cloud, off a linear constraint the training data obey, or non-finite) or 'sparse' (in a hole of the
training data); both are out of domain. The per-feature training range is a diagnostic only. A row with a non-finite
value gets no score. Checkpoints written before this domain model (a "mahalanobis_threshold" record) are read with the
old per-feature range and pinv-Mahalanobis check, and the summary says "legacy domain record".
--on-out-of-domain flag (default) writes a per-row out_of_domain field and counts them in the summary;
--on-out-of-domain reject exits non-zero when any row is out of domain and writes no scores.
--calibration FILE applies a calibration map recorded by calibration.py (its "calibration" block, and its
"prior_shift" when present) to the two-class score: temperature, Platt or isotonic. A calibration whose model_hash
names another model is refused (exit 2); one without a model_hash is applied with a warning (F-08).
--split-manifest FILE compares a manifest with the split_manifest_sha256 recorded at training and reports a
difference (split_manifest_check, warnings). The summary carries the checkpoint's model_hash.

External scores (ML3 extensions): --external-scores SCORES.csv (columns id, score) from another tool (TMVA, LightGBM)
go through the same checks without a checkpoint and without PyTorch: --model-file (the external model; its sha256 is
the model_hash a calibration must name), --input (feature rows of the scored events) with --training-features (the
training rows: the same DomainModel is fitted on them and flags each scored row), --split-manifest (every scored id
the manifest lists must be in its test part, or, for a k-fold manifest {fold0.., } with a "fold" column in SCORES, in
the fold whose model scored it: a score on an event the model was trained on is refused, exit 1; scored ids the
manifest does not list are kept with a warning, since the check cannot exclude that the model was trained on them),
--calibration as above, and --run-summary-out (with --labels and --grouping-key) for write_ml_artifact.py.

The checkpoint is loaded with weights_only=True (tensors and plain containers only); --unsafe-full-unpickle runs a
full unpickle, which can execute arbitrary code: only for files you trust.
Output: per-row CSV (--output) or, without it, the rows inside the JSON summary on stdout.
Output JSON: "status" (ok; refused when --on-out-of-domain reject finds out-of-domain rows; rejected; missing-dependency;
core/status.py) and "status_label" (--status, the inputs' artifact label, default unvalidated).
Exit codes: 0 done, 1 out-of-domain rows with --on-out-of-domain reject (a negative verdict; the JSON summary lists
them), 2 input error (missing features, unreadable or unsafe checkpoint), 3 PyTorch not available.
"""

from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import csv
import hashlib
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True  # the imports below leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint", nargs="?", help="train_classifier.py checkpoint (not with --external-scores)")
    parser.add_argument("--input", required=True, help="CSV with (at least) the training feature columns")
    parser.add_argument("--external-scores", help="CSV id,score[,fold] from an external tool (TMVA, LightGBM)")
    parser.add_argument("--external-tool", choices=("tmva", "lightgbm", "other"), help="tool that wrote the scores")
    parser.add_argument("--model-file", help="the external model file; its sha256 is the model_hash")
    parser.add_argument("--training-features", help="CSV of the training rows (external scores: domain model)")
    parser.add_argument("--run-summary-out", help="external scores: write a run summary for write_ml_artifact.py")
    parser.add_argument("--labels", help="external scores: comma-separated class labels for the run summary")
    parser.add_argument("--grouping-key", help="external scores: the split's grouping key for the run summary")
    parser.add_argument("--id-col", default="id", help="row id column, if present (default: id)")
    parser.add_argument("--output", help="per-row CSV to write (default: rows in the JSON summary)")
    parser.add_argument("--on-out-of-domain", choices=("flag", "reject"), default="flag")
    parser.add_argument("--calibration", help="calibration.py output whose map is applied to the two-class score; "
                        "refused when its model_hash names another model")
    parser.add_argument("--split-manifest", help="split manifest to compare with the one the model was trained on "
                        "(split_manifest_sha256 in the checkpoint); a difference is reported")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--unsafe-full-unpickle", action="store_true",
                        help="load with weights_only=False (full pickle, can run arbitrary code); only for files you trust")
    add_status_argument(parser)
    return parser


if __name__ == "__main__":
    build_parser().parse_args()  # --help and usage errors work without PyTorch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_surrogate_domain import DomainModel  # noqa: E402  (one domain method; PML-WP0.7)

_EXTERNAL = __name__ == "__main__" and "--external-scores" in sys.argv[1:]
try:
    import torch
    from models import MLPClassifier, state_dict_hash
except ModuleNotFoundError as _exc:
    if __name__ != "__main__":
        raise
    if not _EXTERNAL:  # external scores need no PyTorch
        print(json.dumps({"status": "missing-dependency", "error": f"torch not available ({_exc}); check the "
                          "environment with scripts/check_pytorch_env.py"}))
        sys.exit(3)
    torch = None


class InputError(Exception):
    pass


def get_device(name: str) -> "torch.device":
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load_checkpoint(path: str, unsafe: bool) -> dict:
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=not unsafe)
    except pickle.UnpicklingError as exc:
        raise InputError(f"refused to load {path} with weights_only=True: {exc}; re-run with "
                         "--unsafe-full-unpickle only if you trust this file") from exc
    if not isinstance(ckpt, dict) or "metadata" not in ckpt:
        raise InputError(f"{path} has no 'metadata' (feature names, preprocessing, domain); "
                         "write it with train_classifier.py")
    return ckpt


def read_inputs(path: str, features: list[str], id_col: str) -> tuple[list[str], np.ndarray]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [f for f in features if f not in header]
        if missing:
            raise InputError(f"{path}: training feature(s) missing from the input: {missing}; refusing to guess "
                             f"(expected {features})")
        rows = list(reader)
    if not rows:
        raise InputError(f"{path}: no rows")
    ids = [row[id_col] if id_col in header else str(i) for i, row in enumerate(rows)]
    try:
        x = np.array([[float(row[f]) for f in features] for row in rows], dtype=np.float64)
    except ValueError as exc:
        raise InputError(f"{path}: {exc}") from exc
    return ids, x


def domain_flags(x: np.ndarray, features: list[str], domain: dict) -> list[list[str]]:
    """Reasons each row is outside the training domain (empty list = inside)."""
    if "model" not in domain:
        return legacy_domain_flags(x, features, domain)
    if domain["model"] is None:  # too few training rows for a calibrated model: the range is the only check
        lo, hi = np.asarray(domain["min"]), np.asarray(domain["max"])
        return [["outside:non-finite"] if not np.all(np.isfinite(row)) else
                [f"outside:range:{features[j]}" for j in np.flatnonzero((row < lo) | (row > hi))] for row in x]
    model = DomainModel.from_dict(domain["model"])
    status, reasons = model.classify(x)
    # outside the per-feature training range alone is a diagnostic, not a flag (see the docstring)
    return [[] if st == "inside" else [f"{st}:" + "; ".join(why)] for st, why in zip(status, reasons)]


def legacy_domain_flags(x: np.ndarray, features: list[str], domain: dict) -> list[list[str]]:
    """Checkpoints from before the shared domain model: per-feature range and pinv-Mahalanobis threshold."""
    lo, hi = np.asarray(domain["min"]), np.asarray(domain["max"])
    finite = np.all(np.isfinite(x), axis=1)
    precision = np.linalg.pinv(np.asarray(domain["cov"]))
    diff = np.where(np.isfinite(x), x, 0.0) - np.asarray(domain["mean"])
    dist = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", diff, precision, diff), 0.0))
    reasons = []
    for i in range(len(x)):
        row = []
        if not finite[i]:
            row.append("non-finite")
        outside = [features[j] for j in np.flatnonzero((x[i] < lo) | (x[i] > hi))]
        row += [f"range:{name}" for name in outside]
        if finite[i] and dist[i] > domain["mahalanobis_threshold"]:
            row.append(f"mahalanobis:{dist[i]:.3g}>{domain['mahalanobis_threshold']:.3g}")
        reasons.append(row)
    return reasons


def apply_calibration(p: np.ndarray, path: str, model_hash: str, warnings: list) -> tuple[np.ndarray, dict]:
    """Apply calibration.py's recorded map (prior shift first, then temperature, Platt or isotonic). A calibration that
    names another model (its model_hash differs from the checkpoint's) is refused (F-08)."""
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    cal = doc.get("calibration") if isinstance(doc, dict) else None
    if not isinstance(cal, dict) or not isinstance(cal.get("params"), dict):
        raise InputError(f"{path}: needs a 'calibration' block with 'method' and 'params' (calibration.py output)")
    made_for = doc.get("model_hash")
    if made_for is None:
        warnings.append(f"{path} does not name the model it was made for (no model_hash): it cannot be checked "
                        "against this checkpoint; rerun calibration.py with --model-hash or --run-summary")
    elif made_for != model_hash:
        raise InputError(f"{path} was made for another model ({made_for}); this checkpoint is {model_hash}")
    z = np.log(np.clip(p, 1e-12, 1 - 1e-12)) - np.log(np.clip(1 - p, 1e-12, 1))
    prior = doc.get("prior_shift") or {}
    if prior.get("prior_ratio_change"):
        z = z + math.log(float(prior["prior_ratio_change"]))
    method, par = cal.get("method"), cal["params"]
    if method == "temperature":
        out = 1 / (1 + np.exp(-z / float(par["temperature"])))
    elif method == "platt":
        out = 1 / (1 + np.exp(-(float(par["a"]) * z + float(par["b"]))))
    elif method == "isotonic":
        out = np.interp(1 / (1 + np.exp(-z)), np.asarray(par["x"], float), np.asarray(par["y"], float))
    else:
        raise InputError(f"{path}: unknown calibration method {method!r}")
    return out, {"file": path, "method": method, "prior_ratio_change": prior.get("prior_ratio_change"),
                 "model_hash": made_for}


def preprocess(x: np.ndarray, steps: list[dict], features: list[str]) -> np.ndarray:
    for step in steps:
        if step["step"] != "standardize" or step["features"] != features:
            raise InputError(f"unsupported preprocessing step {step['step']!r}")
        x = (x - np.asarray(step["mean"])) / np.asarray(step["std"])
    return x


def run(args) -> int:
    ckpt = load_checkpoint(args.checkpoint, args.unsafe_full_unpickle)
    meta = ckpt["metadata"]
    features, labels, cfg = meta["features"], meta["labels"], meta["model"]
    ids, x = read_inputs(args.input, features, args.id_col)
    domain = meta["training_domain"]
    reasons = domain_flags(x, features, domain)
    finite = np.all(np.isfinite(x), axis=1)
    n_ood = sum(bool(r) for r in reasons)
    summary = {"checkpoint": args.checkpoint, "n_rows": len(ids), "n_out_of_domain": n_ood,
               "n_outside": sum(any(s.startswith("outside:") or s.startswith("range:") for s in r) for r in reasons),
               "n_sparse": sum(any(s.startswith("sparse:") for s in r) for r in reasons),
               "n_mahalanobis": sum(any("ahalanobis" in s for s in r) for r in reasons),
               "n_non_finite": int((~finite).sum()),
               "domain_method": domain.get("method", "legacy domain record (per-feature range + pinv Mahalanobis)"),
               "on_out_of_domain": args.on_out_of_domain, "status_label": args.status,
               "model_hash": state_dict_hash(ckpt["model_state_dict"]), "warnings": []}
    recorded = meta.get("split_manifest_sha256")
    if args.split_manifest:
        current = "sha256:" + hashlib.sha256(Path(args.split_manifest).read_bytes()).hexdigest()
        summary["split_manifest_check"] = {"manifest": args.split_manifest, "recorded": recorded, "current": current,
                                           "match": recorded == current if recorded else None}
        if recorded is None:
            summary["warnings"].append("the checkpoint records no split_manifest_sha256 (trained before F-08)")
        elif recorded != current:
            summary["warnings"].append(f"split manifest {args.split_manifest} differs from the one the model was "
                                       "trained on: the train/val/test assignment may have changed")
    if n_ood and args.on_out_of_domain == "reject":
        summary["out_of_domain_ids"] = [ids[i] for i, r in enumerate(reasons) if r][:50]
        summary["status"] = "refused"
        summary["reason"] = f"{n_ood} row(s) outside the training domain; no scores written"
        print(json.dumps(summary, indent=2))
        return 1

    device = get_device(args.device)
    model = MLPClassifier(cfg["input_dim"], cfg["hidden_dim"], cfg["num_classes"], cfg["dropout"]).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    z = preprocess(np.where(np.isfinite(x), x, 0.0), meta["preprocessing"], features)
    with torch.inference_mode():
        logits = model(torch.as_tensor(z, dtype=torch.float32, device=device)).float()
        probs = torch.sigmoid(logits[:, 0]) if logits.shape[1] == 1 else torch.softmax(logits, dim=1)
    probs = probs.cpu().numpy()
    if args.calibration:
        if probs.ndim != 1:
            raise InputError("--calibration applies to a two-class score only")
        probs, summary["calibration"] = apply_calibration(probs, args.calibration, summary["model_hash"],
                                                          summary["warnings"])
    score_cols = ["score"] if probs.ndim == 1 else [f"score_{name}" for name in labels]
    rows = []
    for i, row_id in enumerate(ids):
        values = [probs[i]] if probs.ndim == 1 else list(probs[i])
        if not finite[i]:  # a row with a non-finite input gets no score, not one computed from a substituted 0
            values = [None] * len(score_cols)
        rows.append({"id": row_id, **{c: (None if v is None else float(v)) for c, v in zip(score_cols, values)},
                     "out_of_domain": int(bool(reasons[i])), "ood_reasons": ";".join(reasons[i])})
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary["output"] = args.output
    else:
        summary["rows"] = [{k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()}
                           for r in rows]
    summary["status"] = "ok"
    print(json.dumps(summary, indent=2))
    return 0


def _read_scores(path: str) -> tuple[list[str], np.ndarray, list[str] | None]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        if "id" not in header or "score" not in header:
            raise InputError(f"{path}: needs columns id and score")
        rows = list(reader)
    if not rows:
        raise InputError(f"{path}: no rows")
    try:
        scores = np.array([float(r["score"]) for r in rows], dtype=np.float64)
    except ValueError as exc:
        raise InputError(f"{path}: {exc}") from exc
    return [r["id"] for r in rows], scores, ([r["fold"] for r in rows] if "fold" in header else None)


def leakage_check(ids: list[str], folds: list[str] | None, manifest_path: str) -> dict:
    """Compare scored ids with the split manifest.

    Counts the scored ids the manifest puts in training (train/val, or another fold than the one whose model scored
    them: scored_training_ids, which run_external refuses) and the scored ids the manifest does not list at all
    (ids_not_in_manifest). The second are not refused, since scoring real data or other samples is legitimate, but the
    check cannot exclude that the model was trained on them: missing_manifest_warning() states it.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    kfold = sorted(k for k in manifest if k.startswith("fold"))
    bad, missing = [], []
    if kfold:
        if folds is None:
            raise InputError("a k-fold manifest needs a 'fold' column in the score file (the fold whose model scored it)")
        where = {i: k[len("fold"):] for k in kfold for i in manifest[k]}
        for i, f in zip(ids, folds):
            if i not in where:
                missing.append(i)
            elif where[i] != str(f).strip():
                bad.append(i)
        rule = "each event scored by the model of its own fold (the model that did not see it)"
    else:
        train = set(manifest.get("train", [])) | set(manifest.get("val", [])) | set(manifest.get("validation", []))
        test = set(manifest.get("test", []))
        bad = [i for i in ids if i in train]
        missing = [i for i in ids if i not in train and i not in test]
        rule = "every scored event in the manifest's test part"
    return {"manifest": manifest_path, "rule": rule, "scored_training_ids": len(bad), "examples": bad[:20],
            "ids_not_in_manifest": len(missing),
            "sha256": "sha256:" + hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()}


def missing_manifest_warning(leak: dict) -> str | None:
    """The warning for scored ids absent from the split manifest, or None when every scored id is listed."""
    n = leak["ids_not_in_manifest"]
    if not n:
        return None
    return (f"{n} scored event(s) are not in the split manifest, so the check cannot exclude that the model was "
            "trained on them; if they are simulated events from the training sample, the manifest is incomplete")


def run_external(args) -> int:
    for need in ("external_tool", "model_file", "training_features"):
        if not getattr(args, need):
            raise InputError(f"--external-scores needs --{need.replace('_', '-')}")
    model_hash = "sha256:" + hashlib.sha256(Path(args.model_file).read_bytes()).hexdigest()
    ids, scores, folds = _read_scores(args.external_scores)
    leak = leakage_check(ids, folds, args.split_manifest) if args.split_manifest else None
    if leak and leak["scored_training_ids"]:
        print(json.dumps({"status": "refused", "external": {"tool": args.external_tool}, "model_hash": model_hash,
                          "leakage_check": leak, "status_label": args.status,
                          "warnings": [w for w in (missing_manifest_warning(leak),) if w],
                          "reason": "scores on events the model was trained on: not usable for evaluation; no scores "
                                    "written"}, indent=2))
        return 1
    with open(args.training_features, newline="", encoding="utf-8") as handle:
        header = csv.DictReader(handle).fieldnames or []
    features = [c for c in header if c != args.id_col]
    _, x_train = read_inputs(args.training_features, features, args.id_col)
    in_ids, x = read_inputs(args.input, features, args.id_col)
    pos = {i: k for k, i in enumerate(in_ids)}
    absent = [i for i in ids if i not in pos]
    if absent:
        raise InputError(f"{len(absent)} scored id(s) have no feature row in {args.input} (e.g. {absent[:3]})")
    x = x[[pos[i] for i in ids]]
    model = DomainModel.fit(x_train[np.all(np.isfinite(x_train), axis=1)], seed=0)
    status, reasons = model.classify(x)
    reasons = [[] if st == "inside" else [f"{st}:" + "; ".join(why)] for st, why in zip(status, reasons)]
    n_ood = sum(bool(r) for r in reasons)
    summary = {"external": {"tool": args.external_tool, "scores": args.external_scores, "model_file": args.model_file},
               "model_hash": model_hash, "n_rows": len(ids), "n_out_of_domain": n_ood, "features": features,
               "domain_method": "check_surrogate_domain.DomainModel fitted on --training-features",
               "on_out_of_domain": args.on_out_of_domain, "status_label": args.status, "warnings": []}
    if leak:
        summary["leakage_check"] = leak
        if missing_manifest_warning(leak):
            summary["warnings"].append(missing_manifest_warning(leak))
    else:
        summary["warnings"].append("no --split-manifest: the scores were not checked for training events")
    if n_ood and args.on_out_of_domain == "reject":
        summary["status"] = "refused"
        summary["reason"] = f"{n_ood} row(s) outside the training domain; no scores written"
        print(json.dumps(summary, indent=2))
        return 1
    if args.calibration:
        scores, summary["calibration"] = apply_calibration(scores, args.calibration, model_hash, summary["warnings"])
    rows = [{"id": i, "score": float(sc), "out_of_domain": int(bool(r)), "ood_reasons": ";".join(r)}
            for i, sc, r in zip(ids, scores, reasons)]
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary["output"] = args.output
    else:
        summary["rows"] = rows
    if args.run_summary_out:
        if not (args.labels and args.grouping_key):
            raise InputError("--run-summary-out needs --labels and --grouping-key")
        finite = np.isfinite(x_train)
        rs = {"task": "classification", "features": features,
              "labels": [t.strip() for t in args.labels.split(",") if t.strip()], "grouping_key": args.grouping_key,
              "training_domain": {f: [float(np.min(x_train[finite[:, j], j])), float(np.max(x_train[finite[:, j], j]))]
                                  for j, f in enumerate(features) if finite[:, j].any()},
              "model_hash": model_hash, "output_semantics": "probability" if args.calibration else "score",
              "environment": {"framework": f"external: {args.external_tool}", "device": "cpu", "precision": "fp32"},
              "notes": f"scores written by {args.external_tool} and checked by assets/inference.py --external-scores",
              "scores": {"test": args.output} if args.output else {}}
        if "leakage_check" in summary:
            rs["split_manifest"] = args.split_manifest
            rs["split_manifest_sha256"] = summary["leakage_check"]["sha256"].split(":", 1)[1]
        Path(args.run_summary_out).write_text(json.dumps(rs, indent=1), encoding="utf-8")
        summary["run_summary"] = args.run_summary_out
    summary["status"] = "ok"
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.external_scores:
            return run_external(args)
        if not args.checkpoint:
            raise InputError("give a checkpoint, or --external-scores")
        return run(args)
    except (InputError, OSError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
