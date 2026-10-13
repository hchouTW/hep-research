#!/usr/bin/env python3
"""Inference for checkpoints written by train_classifier.py, with input and training-domain checks.

Reads the checkpoint metadata (feature names, preprocessing, training domain, labels, model shape), requires every
training feature to be present in the input CSV by name (refuses otherwise; order does not matter, extra columns are
ignored), applies the stored standardization, and checks each row against the training domain: outside the per-feature
[min, max] of the training split, or a Mahalanobis distance above the threshold stored at training time (an empirical
quantile of train+val distances). Rows with non-finite values are out of domain too.
--on-out-of-domain flag (default) writes a per-row out_of_domain field and counts them in the summary;
--on-out-of-domain reject exits non-zero when any row is out of domain and writes no scores.

The checkpoint is loaded with weights_only=True (tensors and plain containers only); --unsafe-full-unpickle runs a
full unpickle, which can execute arbitrary code: only for files you trust.
Output: per-row CSV (--output) or, without it, the rows inside the JSON summary on stdout.
Exit codes: 0 done, 2 input error (missing features, unreadable or unsafe checkpoint), 3 PyTorch not available,
4 out-of-domain rows with --on-out-of-domain reject.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint")
    parser.add_argument("--input", required=True, help="CSV with (at least) the training feature columns")
    parser.add_argument("--id-col", default="id", help="row id column, if present (default: id)")
    parser.add_argument("--output", help="per-row CSV to write (default: rows in the JSON summary)")
    parser.add_argument("--on-out-of-domain", choices=("flag", "reject"), default="flag")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--unsafe-full-unpickle", action="store_true",
                        help="load with weights_only=False (full pickle, can run arbitrary code); only for files you trust")
    return parser


if __name__ == "__main__":
    build_parser().parse_args()  # --help and usage errors work without PyTorch

try:
    import torch
except ModuleNotFoundError as _exc:
    if __name__ != "__main__":
        raise
    print(f"{Path(__file__).name}: torch not available ({_exc}); check the environment with "
          "scripts/check_pytorch_env.py", file=sys.stderr)
    sys.exit(3)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import MLPClassifier  # noqa: E402


class InputError(Exception):
    pass


def get_device(name: str) -> torch.device:
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
    reasons = domain_flags(x, features, meta["training_domain"])
    n_ood = sum(bool(r) for r in reasons)
    summary = {"checkpoint": args.checkpoint, "n_rows": len(ids), "n_out_of_domain": n_ood,
               "n_outside_range": sum(any(s.startswith("range:") for s in r) for r in reasons),
               "n_mahalanobis": sum(any(s.startswith("mahalanobis:") for s in r) for r in reasons),
               "mahalanobis_threshold": meta["training_domain"]["mahalanobis_threshold"],
               "on_out_of_domain": args.on_out_of_domain}
    if n_ood and args.on_out_of_domain == "reject":
        summary["out_of_domain_ids"] = [ids[i] for i, r in enumerate(reasons) if r][:50]
        print(json.dumps(summary, indent=2))
        print(f"rejected: {n_ood} row(s) outside the training domain", file=sys.stderr)
        return 4

    device = get_device(args.device)
    model = MLPClassifier(cfg["input_dim"], cfg["hidden_dim"], cfg["num_classes"], cfg["dropout"]).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    z = preprocess(np.where(np.isfinite(x), x, 0.0), meta["preprocessing"], features)
    with torch.inference_mode():
        logits = model(torch.as_tensor(z, dtype=torch.float32, device=device)).float()
        probs = torch.sigmoid(logits[:, 0]) if logits.shape[1] == 1 else torch.softmax(logits, dim=1)
    probs = probs.cpu().numpy()
    score_cols = ["score"] if probs.ndim == 1 else [f"score_{name}" for name in labels]
    rows = []
    for i, row_id in enumerate(ids):
        values = [probs[i]] if probs.ndim == 1 else list(probs[i])
        rows.append({"id": row_id, **{c: float(v) for c, v in zip(score_cols, values)},
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
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except (InputError, OSError, KeyError) as exc:
        print(f"{Path(__file__).name}: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
