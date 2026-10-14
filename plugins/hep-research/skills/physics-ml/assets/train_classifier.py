#!/usr/bin/env python3
"""PyTorch classifier training template for physics events: grouped splits, event weights, held-out test.

Data, two ways:
  --data events.csv --split-manifest splits.json
      Real data. The CSV has an id column, feature columns, a label column (integer class index, or a name from
      --label-names) and optionally a weight column. The manifest is the JSON that check_split_integrity.py reads
      ({"train": [ids], "val": [ids], "test": [ids], "groups": {id: group}}); rows are matched by id.
  (no --data)
      Synthetic events in groups of --synthetic-group-size that share a latent offset (like events from one run
      block or one generator job), split by group, never by row. The generated manifest is written to the output
      directory and checked like a real one, so the script runs immediately.

Before any model is built, scripts/check_split_integrity.py --strict runs on the manifest; training is refused
(exit 1) unless it passes. --allow-unchecked-split overrides that, and the summary then records "fail" or "not-run".

Event weights: evaluation weights are the signed input weights; training weights are derived from them
(--negative-weights, --class-balancing) and recorded separately in the checkpoint. The loss is
hep_losses.weighted_bce for two classes, a signed-weight cross-entropy otherwise; batches whose per-class net
weight is not positive are counted (training_log.json). Model selection uses the validation split only; working
points (thresholds at fixed signal efficiency) are fixed on validation and applied unchanged to the test split,
which is evaluated once, after selection.

Outputs in --output-dir: config.json, split_manifest.json (synthetic only), split_check.json, best.pt, last.pt,
training_log.json, val_scores.csv (calibration fit sample), test_scores.csv, run_summary.json. Checkpoints hold
plain types only and load with torch.load(..., weights_only=True).
--config config.yaml supplies defaults; flags given on the command line override it.
Exit codes: 0 done, 1 split check did not pass (training refused), 2 usage or input error, 3 PyTorch not available.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHECK_SCRIPT = HERE.parent / "scripts" / "check_split_integrity.py"
SPLITS = ("train", "val", "test")
CONFIG_RENAMES = {"learning_rate": "lr"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="YAML file with defaults (sections data/model/training are flattened)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    data = parser.add_argument_group("data")
    data.add_argument("--data", help="CSV of events (requires --split-manifest)")
    data.add_argument("--split-manifest", help="JSON split manifest (check_split_integrity.py format)")
    data.add_argument("--allow-unchecked-split", action="store_true",
                      help="train even if the split check fails or cannot run (recorded in run_summary.json)")
    data.add_argument("--id-col", default="id")
    data.add_argument("--label-col", default="label")
    data.add_argument("--weight-col", help="per-event weight column (signed weights allowed)")
    data.add_argument("--features", help="comma-separated feature columns (default: every other column)")
    data.add_argument("--label-names", help="comma-separated class names, in class-index order")
    data.add_argument("--units", help="JSON file mapping feature name -> unit")
    data.add_argument("--grouping-key", help="what the manifest groups are (run/lumi block, generator job, ...)")
    data.add_argument("--status", action="append",
                      choices=("synthetic", "asimov", "observed", "preliminary", "unvalidated", "user-supplied"),
                      help="status label of the input data, written to run_summary.json (repeatable); the synthetic "
                      "path always records 'synthetic'")
    synth = parser.add_argument_group("synthetic data (used without --data)")
    synth.add_argument("--train-size", type=int, default=8000)
    synth.add_argument("--val-size", type=int, default=2000)
    synth.add_argument("--test-size", type=int, default=2000)
    synth.add_argument("--input-dim", type=int, default=32)
    synth.add_argument("--num-classes", type=int, default=2)
    synth.add_argument("--synthetic-group-size", type=int, default=8)
    synth.add_argument("--synthetic-negative-fraction", type=float, default=0.0,
                       help="fraction of synthetic events with negative weight (like NLO generators)")
    model = parser.add_argument_group("model")
    model.add_argument("--hidden-dim", type=int, default=128)
    model.add_argument("--dropout", type=float, default=0.2)
    train = parser.add_argument_group("training")
    train.add_argument("--batch-size", type=int, default=128)
    train.add_argument("--num-workers", type=int, default=2)
    train.add_argument("--epochs", type=int, default=10)
    train.add_argument("--lr", type=float, default=1e-3)
    train.add_argument("--weight-decay", type=float, default=1e-4)
    train.add_argument("--grad-clip", type=float, default=1.0)
    train.add_argument("--precision", choices=("fp32", "bf16", "fp16"), default="fp32",
                       help="bf16 autocast on CPU or CUDA; fp16 (with a gradient scaler) on CUDA only")
    train.add_argument("--negative-weights", choices=("signed", "abs", "resample"), default="signed",
                       help="training treatment of negative weights; evaluation always keeps them signed. signed: "
                       "keep them (large batches); abs: train on |w| (biased where negative weights cluster; the bias "
                       "warning is recorded); resample: cell resampling per class in the standardized inputs "
                       "(Andersen & Maier, arXiv:2109.07851). Dropping them is not offered: it biases the result.")
    train.add_argument("--resample-max-cell", type=int, default=200,
                       help="largest cell for --negative-weights resample (default 200 events)")
    train.add_argument("--class-balancing", choices=("none", "equal-sum"), default="none",
                       help="equal-sum: rescale training weights so every class has the same sum of weights")
    train.add_argument("--working-points", type=float, nargs="+", default=[0.3, 0.5, 0.7],
                       help="signal efficiencies for the working points (two-class only)")
    train.add_argument("--ood-quantile", type=float, default=0.999,
                       help="target in-distribution acceptance of the training-domain model (thresholds calibrated on "
                       "held-out training rows; scripts/check_surrogate_domain.py)")
    train.add_argument("--output-dir", default="runs/example")
    return parser


def config_defaults(path: str, parser: argparse.ArgumentParser) -> dict:
    """Flatten a config YAML into argparse defaults; unknown keys are an error, not silently ignored."""
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ValueError(f"--config needs PyYAML ({exc})") from exc
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    flat = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value
    model_type = flat.pop("type", "mlp")
    if model_type != "mlp":
        raise ValueError(f"config model.type {model_type!r}: this template trains an MLP only")
    dests = {action.dest for action in parser._actions} - {"help", "config"}
    out = {}
    for key, value in flat.items():
        dest = CONFIG_RENAMES.get(key, key).replace("-", "_")
        if dest not in dests:
            raise ValueError(f"unknown config key {key!r} in {path}")
        if dest in ("features", "label_names") and isinstance(value, list):
            value = ",".join(map(str, value))
        out[dest] = value
    return out


def parse_args(argv=None) -> argparse.Namespace:
    parser = build_parser()
    pre, _ = parser.parse_known_args(argv)
    if pre.config:
        try:
            parser.set_defaults(**config_defaults(pre.config, parser))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    return parser.parse_args(argv)


if __name__ == "__main__":
    parse_args()  # --help and usage errors work without PyTorch

try:
    import torch
    from torch.utils.data import DataLoader, TensorDataset
except ModuleNotFoundError as _exc:
    if __name__ != "__main__":
        raise
    print(f"{Path(__file__).name}: torch not available ({_exc}); check the environment with "
          "scripts/check_pytorch_env.py", file=sys.stderr)
    sys.exit(3)

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))  # check_surrogate_domain.DomainModel: one domain method (PML-WP0.7)
from hep_losses import batch_weight_report, weighted_bce  # noqa: E402
from hep_metrics import (cell_resample, effective_entries, efficiency_with_uncertainty,  # noqa: E402
                         rejection_at_signal_efficiency, weighted_auc)
from models import MLPClassifier  # noqa: E402


class InputError(Exception):
    """Bad input data or arguments: exit 2 with a one-line message."""


_ZERO_FRACTION = re.compile(r"^([+-]?\d+)\.0*$")


def canonical_key(value, case_sensitive=False):
    """ID comparison form shared with scripts/check_split_integrity.py and make_grouped_splits.py (copy; a test pins
    the two copies together): stripped, a zero fraction dropped (1, 1.0, "1" are one key), case-folded unless
    case_sensitive; booleans, lists and objects raise ValueError."""
    if isinstance(value, bool) or isinstance(value, (list, dict, tuple, set)):
        raise ValueError(f"{value!r} is not a valid ID or group value (booleans, lists and objects are refused)")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return str(int(value))
        return repr(value)
    text = str(value).strip()
    match = _ZERO_FRACTION.match(text)
    if match:
        text = str(int(match.group(1)))
    return text if case_sensitive else text.casefold()


# ---------------------------------------------------------------- setup

def seed_everything(seed: int) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    return {"torch": seed, "numpy": seed, "python": seed}


def get_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def autocast(device: torch.device, precision: str):
    if precision == "fp32":
        return contextlib.nullcontext()
    dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    return torch.autocast(device_type=device.type, dtype=dtype)


# ---------------------------------------------------------------- data

def make_synthetic(args, output_dir: Path) -> dict:
    """Grouped synthetic events: each group shares a latent offset, and whole groups go to one split."""
    rng = np.random.default_rng(args.seed)
    n_classes, n_features, group_size = args.num_classes, args.input_dim, args.synthetic_group_size
    sizes = (args.train_size, args.val_size, args.test_size)
    if n_classes < 2 or min(sizes) <= 0 or group_size <= 0:
        raise InputError("need --num-classes >= 2, positive split sizes and a positive --synthetic-group-size")
    n = sum(sizes)
    n_groups = math.ceil(n / group_size)
    group = np.repeat(np.arange(n_groups), group_size)[:n]
    y = rng.integers(0, n_classes, n)
    class_means = rng.normal(0.0, 0.6, (n_classes, n_features))
    group_offset = rng.normal(0.0, 0.5, (n_groups, n_features))
    x = class_means[y] + group_offset[group] + rng.normal(size=(n, n_features))
    w = np.abs(rng.normal(1.0, 0.2, n))
    w[rng.random(n) < args.synthetic_negative_fraction] *= -1.0
    ids = [f"evt{i:06d}" for i in range(n)]
    group_names = [f"grp{g:05d}" for g in group]

    # assign whole groups, in random order, until each split reaches its requested size
    manifest = {"_comment": "Synthetic grouped split written by train_classifier.py", "train": [], "val": [], "test": []}
    bounds = np.cumsum(sizes)
    filled = 0
    members = {g: np.flatnonzero(group == g) for g in range(n_groups)}
    for g in rng.permutation(n_groups):
        split = SPLITS[min(int(np.searchsorted(bounds, filled, side="right")), 2)]
        manifest[split].extend(ids[i] for i in members[g])
        filled += members[g].size
    manifest["groups"] = dict(zip(ids, group_names))
    path = output_dir / "split_manifest.json"
    path.write_text(json.dumps(manifest, indent=1))

    return {"ids": ids, "x": x, "y": y, "w": w, "features": [f"x{i:02d}" for i in range(n_features)],
            "labels": ["background", "signal"] if n_classes == 2 else [f"class_{i}" for i in range(n_classes)],
            "units": {f"x{i:02d}": "a.u." for i in range(n_features)}, "weight_source": "synthetic",
            "grouping_key": "synthetic_group", "manifest": path}


def read_events(args) -> dict:
    """Read the CSV: ids, features (float64), integer labels, signed weights (1.0 without a weight column)."""
    with open(args.data, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        raise InputError(f"{args.data}: no rows")
    for col in filter(None, (args.id_col, args.label_col, args.weight_col)):
        if col not in header:
            raise InputError(f"{args.data}: column {col!r} not found")
    reserved = {args.id_col, args.label_col, args.weight_col}
    features = args.features.split(",") if args.features else [c for c in header if c not in reserved]
    missing = [f for f in features if f not in header]
    if missing or not features:
        raise InputError(f"{args.data}: feature columns missing: {missing or 'none selected'}")
    label_names = args.label_names.split(",") if args.label_names else None
    ids = [row[args.id_col] for row in rows]
    if len({canonical_key(value) for value in ids}) != len(ids):
        raise InputError(f"{args.data}: duplicate ids in column {args.id_col!r} (after stripping whitespace, "
                         "folding case and writing 1.0 as 1, as the split tools compare them)")
    try:
        x = np.array([[float(row[f]) for f in features] for row in rows])
        raw_labels = [row[args.label_col] for row in rows]
        if label_names and not all(v.lstrip("-").isdigit() for v in raw_labels):
            y = np.array([label_names.index(v) for v in raw_labels])
        else:
            y = np.array([int(float(v)) for v in raw_labels])
        w = np.array([float(row[args.weight_col]) for row in rows]) if args.weight_col else np.ones(len(rows))
    except ValueError as exc:
        raise InputError(f"{args.data}: {exc}") from exc
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(w)):
        raise InputError(f"{args.data}: non-finite feature or weight values")
    n_classes = len(label_names) if label_names else int(y.max()) + 1
    if y.min() < 0 or y.max() >= n_classes or n_classes < 2:
        raise InputError(f"{args.data}: labels must be class indices 0..{n_classes - 1}, with at least two classes")
    labels = label_names or (["background", "signal"] if n_classes == 2 else [f"class_{i}" for i in range(n_classes)])
    units = {}
    if args.units:
        with open(args.units, encoding="utf-8") as handle:
            units = json.load(handle)
    return {"ids": ids, "x": x, "y": y, "w": w, "features": features, "labels": labels,
            "units": {f: str(units.get(f, "unspecified")) for f in features},
            "weight_source": f"column:{args.weight_col}" if args.weight_col else "none (unit weights)",
            "grouping_key": args.grouping_key or "manifest groups", "manifest": Path(args.split_manifest)}


def run_split_check(manifest: Path, output_dir: Path) -> dict:
    """Run check_split_integrity.py --strict on the manifest; a non-zero exit (failed or incomplete) is a fail."""
    report = output_dir / "split_check.json"
    if not CHECK_SCRIPT.is_file():
        return {"tool": "check_split_integrity.py", "result": "not-run", "report": None,
                "detail": f"{CHECK_SCRIPT} not found"}
    proc = subprocess.run([sys.executable, str(CHECK_SCRIPT), str(manifest), "--json", "--strict"],
                          capture_output=True, text=True, timeout=600)
    report.write_text(proc.stdout or proc.stderr)
    detail = proc.stderr.strip()
    with contextlib.suppress(json.JSONDecodeError):
        parsed = json.loads(proc.stdout)
        detail = f"status {parsed.get('status')}, failure {parsed.get('failure_kind')}"
    return {"tool": "check_split_integrity.py", "result": "pass" if proc.returncode == 0 else "fail",
            "report": str(report.resolve()), "detail": detail}


def assign_splits(data: dict) -> dict:
    """Index arrays for train/val/test from the manifest (rows matched by id)."""
    with open(data["manifest"], encoding="utf-8") as handle:
        manifest = json.load(handle)
    position = {canonical_key(value): i for i, value in enumerate(data["ids"])}
    out = {}
    for split in SPLITS:
        if split not in manifest:
            raise InputError(f"{data['manifest']}: split {split!r} missing (need train, val and test)")
        try:
            keys = [canonical_key(value) for value in manifest[split]]
        except ValueError as exc:
            raise InputError(f"{data['manifest']}: {split}: {exc}") from None
        unknown = [value for value in keys if value not in position]
        if unknown:
            raise InputError(f"{data['manifest']}: {len(unknown)} {split} id(s) not in the data, e.g. {unknown[:3]}")
        out[split] = np.array([position[value] for value in keys], dtype=int)
        if out[split].size == 0:
            raise InputError(f"{data['manifest']}: split {split!r} is empty")
    n_classes = len(data["labels"])
    for split in SPLITS:
        present = set(np.unique(data["y"][out[split]]).tolist())
        missing = [data["labels"][c] for c in range(n_classes) if c not in present]
        if missing:
            raise InputError(f"{data['manifest']}: split {split!r} has no events of class(es) {missing}; it cannot "
                             "be trained or evaluated (build the split with make_grouped_splits.py --label-column)")
    out["unassigned"] = len(data["ids"]) - sum(out[s].size for s in SPLITS)
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    try:
        out["groups"] = {canonical_key(k): v for k, v in groups.items()}
    except ValueError as exc:
        raise InputError(f"{data['manifest']}: groups: {exc}") from None
    return out


TREATMENT = {"signed": "signed", "abs": "abs", "resample": "resampled"}  # CLI choice -> ml-artifact vocabulary


def training_weights(y: np.ndarray, w: np.ndarray, n_classes: int, args, x=None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Training weights from the signed evaluation weights; returns (keep mask, weights, record)."""
    keep = np.ones(w.size, bool)
    wt = w.copy()
    extra: dict = {}
    if args.negative_weights == "abs" and (wt < 0).any():
        wt = np.abs(wt)
        extra["warning"] = ("trained on |w|: the learned density ratio is biased where negative weights cluster; "
                            "compare with signed or resampled training before relying on it")
        print(f"WARNING: {extra['warning']}", file=sys.stderr)
    elif args.negative_weights == "resample" and (wt < 0).any():
        reports = {}
        scale = np.maximum(x.std(axis=0), 1e-12) if x is not None else None
        for c in range(n_classes):
            sel = np.flatnonzero(y == c)
            if sel.size and (wt[sel] < 0).any():
                wt[sel], reports[str(c)] = cell_resample(x[sel], wt[sel], scale, args.resample_max_cell)
        extra["resampling"] = reports
    if args.class_balancing == "equal-sum":
        target = wt[keep].sum() / n_classes
        for c in range(n_classes):
            sel = keep & (y == c)
            total = wt[sel].sum()
            if total <= 0:
                raise InputError(f"class {c} has non-positive training weight sum; cannot balance")
            wt[sel] *= target / total
    record = {"negative_weight_treatment": TREATMENT[args.negative_weights], "class_balancing": args.class_balancing,
              "n_events": int(keep.sum()),
              "sum_w_per_class": [float(wt[keep & (y == c)].sum()) for c in range(n_classes)],
              "n_negative": int((wt[keep] < 0).sum()), **extra}
    return keep, wt, record


DOMAIN_MAX_POINTS = 5000  # training points kept for the k-NN part of the domain model (seeded subsample beyond)


def domain_record(x_train: np.ndarray, groups_train, quantile: float, seed: int) -> dict:
    """The training domain as scripts/check_surrogate_domain.py's DomainModel, fitted on the training split only: the
    thresholds are calibrated on held-out training rows (split by the manifest's groups when every row has one) that
    the mean, covariance and neighbours were not fit on. The per-feature range is kept as a diagnostic."""
    from check_surrogate_domain import DomainModel  # scripts/, on sys.path below

    idx = np.arange(len(x_train))
    if len(idx) > DOMAIN_MAX_POINTS:
        idx = np.sort(np.random.default_rng(seed).choice(idx, DOMAIN_MAX_POINTS, replace=False))
    groups = None
    if groups_train is not None and all(g is not None for g in groups_train):
        groups = [groups_train[i] for i in idx]
    record = {"min": x_train.min(axis=0).tolist(), "max": x_train.max(axis=0).tolist(), "fit_on": "train",
              "quantile": quantile}
    try:
        model = DomainModel.fit(x_train[idx], quantile=quantile, seed=seed, groups=groups)
    except ValueError as exc:  # too few training rows to hold some out: only the range can be checked, and is said so
        print(f"WARNING: training-domain model not fitted ({exc}); inference checks the per-feature range only",
              file=sys.stderr)
        return {**record, "method": "box-only (too few training rows to calibrate a domain model)", "model": None,
                "range_role": "the only check"}
    return {**record, "method": DomainModel.METHOD, "model": model.to_dict(),
            "range_role": "diagnostic (a value outside the training range alone does not flag a row)"}


# ---------------------------------------------------------------- training

def loss_fn(logits: torch.Tensor, targets: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    logits = logits.float()
    if logits.shape[1] == 1:
        return weighted_bce(logits, targets, weights, norm="abs")
    per_event = torch.nn.functional.cross_entropy(logits, targets, reduction="none")
    return (weights * per_event).sum() / weights.abs().sum().clamp(min=torch.finfo(per_event.dtype).tiny)


def nonpositive_classes(targets: torch.Tensor, weights: torch.Tensor, n_classes: int) -> list[int]:
    """Classes present in the batch whose net weight is <= 0."""
    if n_classes == 2:
        report = batch_weight_report(targets, weights)
        sums = [report["background"]["sum_w"], report["signal"]["sum_w"]]
        present = [bool((targets == c).any()) for c in range(2)]
    else:
        sums = [float(weights[targets == c].sum()) for c in range(n_classes)]
        present = [bool((targets == c).any()) for c in range(n_classes)]
    return [c for c in range(n_classes) if present[c] and sums[c] <= 0]


def train_one_epoch(model, loader, optimizer, device, scaler, args, n_classes):
    model.train()
    total_loss, total_abs_w, bad_batches = 0.0, 0.0, 0
    for inputs, targets, weights in loader:
        inputs, targets, weights = (t.to(device, non_blocking=True) for t in (inputs, targets, weights))
        if nonpositive_classes(targets, weights, n_classes):
            bad_batches += 1
        optimizer.zero_grad(set_to_none=True)
        with autocast(device, args.precision):
            logits = model(inputs)
        loss = loss_fn(logits, targets, weights)
        scaler.scale(loss).backward()
        if args.grad_clip and args.grad_clip > 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        scaler.step(optimizer)
        scaler.update()
        abs_w = float(weights.abs().sum())
        total_loss += loss.item() * abs_w
        total_abs_w += abs_w
    return {"loss_weighted": total_loss / max(total_abs_w, 1e-300), "nonpositive_net_weight_batches": bad_batches,
            "batches": len(loader)}


def predict(model, x: np.ndarray, device, args) -> np.ndarray:
    """Scores: P(signal) [N] for two classes, class probabilities [N, C] otherwise."""
    model.eval()
    out = []
    with torch.inference_mode():
        for start in range(0, len(x), 4096):
            batch = torch.as_tensor(x[start:start + 4096], dtype=torch.float32, device=device)
            with autocast(device, args.precision):
                logits = model(batch).float()
            out.append((torch.sigmoid(logits[:, 0]) if logits.shape[1] == 1 else torch.softmax(logits, 1)).cpu())
    return torch.cat(out).numpy().astype(np.float64)


def weighted_loss_np(scores: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    eps = 1e-12
    if scores.ndim == 1:
        per_event = -(y * np.log(scores + eps) + (1 - y) * np.log(1 - scores + eps))
    else:
        per_event = -np.log(scores[np.arange(y.size), y] + eps)
    return float(np.sum(w * per_event) / np.sum(np.abs(w)))


def evaluate(scores: np.ndarray, y: np.ndarray, w: np.ndarray, labels: list[str]) -> dict:
    """Weighted metrics (signed weights kept) on one split."""
    pred = (scores >= 0.5).astype(int) if scores.ndim == 1 else scores.argmax(1)
    out = {"n_events": int(y.size), "loss_weighted": weighted_loss_np(scores, y, w),
           "accuracy_weighted": float(np.sum(w * (pred == y)) / np.sum(w)),
           "sum_w_per_class": {name: float(w[y == c].sum()) for c, name in enumerate(labels)},
           "n_eff_per_class": {name: effective_entries(w[y == c]) for c, name in enumerate(labels)}}
    if scores.ndim == 1:
        out["auc_weighted"] = _safe_auc(scores, y, w)
    else:
        out["auc_weighted_one_vs_rest"] = {name: _safe_auc(scores[:, c], (y == c).astype(int), w)
                                           for c, name in enumerate(labels)}
    return out


def _safe_auc(score, y, w):
    try:
        return weighted_auc(score, y, w)
    except ValueError:  # a class with non-positive total weight: no AUC rather than a wrong one
        return None


def working_points_val(scores, y, w, targets) -> list[dict]:
    points = []
    for eff in targets:
        try:
            points.append(rejection_at_signal_efficiency(scores, y, w, eff))
        except ValueError as exc:
            points.append({"target_eff_s": eff, "error": str(exc)})
    return points


def working_points_test(scores, y, w, val_points) -> list[dict]:
    """Apply the validation thresholds unchanged to the test split."""
    points = []
    for vp in val_points:
        if "threshold" not in vp:
            points.append(dict(vp))
            continue
        sel = scores >= vp["threshold"]
        es, es_unc = efficiency_with_uncertainty(sel[y == 1], w[y == 1])
        eb, eb_unc = efficiency_with_uncertainty(sel[y == 0], w[y == 0])
        points.append({"target_eff_s": vp["target_eff_s"], "threshold_from": "val", "threshold": vp["threshold"],
                       "eff_s": es, "eff_s_unc": es_unc, "eff_b": eb, "eff_b_unc": eb_unc,
                       "rejection": 1.0 / eb if eb > 0 else None})
    return points


def save_checkpoint(path: Path, model, optimizer, scheduler, epoch, best, metadata, args) -> None:
    torch.save({"epoch": epoch, "model_state_dict": model.state_dict(), "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(), "best_metric": best["value"],
                "best_metric_name": best["name"], "best_epoch": best["epoch"], "metadata": metadata,
                "config": vars(args)}, path)


def weights_hash(path: Path) -> str:
    """sha256 over the model weights only (parameter names, dtypes, shapes and bytes, in name order): the hash names
    the model, not the file, so it does not change with paths, optimizer state or the epoch counter."""
    state = torch.load(path, map_location="cpu", weights_only=True)["model_state_dict"]
    h = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        h.update(f"{name}|{tensor.dtype}|{tuple(tensor.shape)}|".encode())
        h.update(tensor.numpy().tobytes())
    return "sha256:" + h.hexdigest()


def write_scores(path: Path, ids, y, w, scores, labels) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        score_cols = ["score"] if scores.ndim == 1 else [f"score_{name}" for name in labels]
        writer.writerow(["id", "label", "weight", *score_cols])
        for i in range(len(ids)):
            row_scores = [scores[i]] if scores.ndim == 1 else list(scores[i])
            writer.writerow([ids[i], int(y[i]), repr(float(w[i])), *(repr(float(s)) for s in row_scores)])


def run(args) -> int:
    seeds = seed_everything(args.seed)
    device = get_device(args.device)
    if args.precision == "fp16" and device.type != "cuda":
        raise InputError("--precision fp16 needs a CUDA device; use bf16 on CPU")
    if args.data and not args.split_manifest:
        raise InputError("--data needs --split-manifest (a grouped split; see scripts/make_grouped_splits.py)")
    if args.split_manifest and not args.data:
        raise InputError("--split-manifest needs --data (the synthetic path writes its own manifest)")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text(json.dumps(vars(args), indent=2))

    data = read_events(args) if args.data else make_synthetic(args, output_dir)
    split_check = run_split_check(data["manifest"], output_dir)
    if split_check["result"] != "pass":
        message = f"split check {split_check['result']}: {split_check['detail']}"
        if not args.allow_unchecked_split:
            print(f"refusing to train: {message} (report: {split_check['report']}); fix the split, or pass "
                  "--allow-unchecked-split to override (recorded in run_summary.json)", file=sys.stderr)
            return 1
        print(f"WARNING: training on an unchecked split ({message})", file=sys.stderr)
    idx = assign_splits(data)
    if idx["unassigned"]:
        print(f"note: {idx['unassigned']} event(s) are in no split and are not used", file=sys.stderr)

    x, y, w, labels, features = data["x"], data["y"], data["w"], data["labels"], data["features"]
    n_classes = len(labels)
    tr, va, te = idx["train"], idx["val"], idx["test"]
    keep, w_train_all, train_weight_record = training_weights(y[tr], w[tr], n_classes, args, x[tr])
    tr_fit = tr[keep]
    mean = x[tr].mean(axis=0)
    std = x[tr].std(axis=0)
    constant = [features[j] for j in np.flatnonzero(std <= 1e-12 * np.maximum(np.abs(mean), 1.0))]
    if constant:  # standardizing by a floor of 1e-12 would amplify any deviation by 1e12 at inference
        raise InputError(f"feature(s) {constant} are constant on the training split; drop them or fix the input")
    preprocessing = [{"step": "standardize", "features": features, "mean": mean.tolist(), "std": std.tolist()}]
    groups_train = [idx["groups"].get(canonical_key(data["ids"][i])) for i in tr]
    domain = domain_record(x[tr], groups_train, args.ood_quantile, args.seed)
    z = (x - mean) / std

    eval_has_negative = bool((w < 0).any())
    unit_eval = bool(np.all(w == 1.0))
    weights_summary = {
        "source": data["weight_source"],
        "negative_weight_treatment": ("none-present" if not eval_has_negative else TREATMENT[args.negative_weights]),
        "class_balancing": args.class_balancing,
        "used_in": ([] if unit_eval and args.class_balancing == "none" else ["loss"]) + ([] if unit_eval else ["metrics"]),
    }
    weights_metadata = {"training": {"source": data["weight_source"], **train_weight_record},
                        "evaluation": {"source": data["weight_source"], "treatment": "signed, unmodified",
                                       "n_negative": int((w < 0).sum())}}
    weights_summary.update(weights_metadata)  # training and evaluation weights recorded separately (contracts 2.8.0)

    out_dim = 1 if n_classes == 2 else n_classes
    model_config = {"type": "MLPClassifier", "input_dim": len(features), "hidden_dim": args.hidden_dim,
                    "num_classes": out_dim, "dropout": args.dropout}
    metadata = {"task": "classification", "features": features, "units": data["units"], "labels": labels,
                "model": model_config, "preprocessing": preprocessing, "training_domain": domain,
                "weights": weights_metadata, "seeds": seeds, "precision": args.precision,
                "grouping_key": data["grouping_key"], "split_manifest": str(Path(data["manifest"]).resolve())}

    train_ds = TensorDataset(torch.as_tensor(z[tr_fit], dtype=torch.float32), torch.as_tensor(y[tr_fit]),
                             torch.as_tensor(w_train_all[keep], dtype=torch.float32))
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers,
                              pin_memory=device.type == "cuda", persistent_workers=args.num_workers > 0,
                              generator=torch.Generator().manual_seed(args.seed))
    model = MLPClassifier(len(features), args.hidden_dim, out_dim, args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))
    scaler = torch.amp.GradScaler("cuda", enabled=args.precision == "fp16")

    best = {"name": "val_loss_weighted", "value": math.inf, "epoch": -1}
    history = []
    for epoch in range(args.epochs):
        train_metrics = train_one_epoch(model, train_loader, optimizer, device, scaler, args, n_classes)
        val_loss = weighted_loss_np(predict(model, z[va], device, args), y[va], w[va])
        scheduler.step()
        history.append({"epoch": epoch, "train": train_metrics, "val_loss_weighted": val_loss})
        print(f"epoch={epoch + 1:03d}/{args.epochs:03d} train_loss={train_metrics['loss_weighted']:.4f} "
              f"val_loss={val_loss:.4f} nonpositive_net_weight_batches={train_metrics['nonpositive_net_weight_batches']}")
        improved = val_loss < best["value"]
        if improved:  # update first, so last.pt records the best value including this epoch
            best = {"name": "val_loss_weighted", "value": val_loss, "epoch": epoch}
        save_checkpoint(output_dir / "last.pt", model, optimizer, scheduler, epoch, best, metadata, args)
        if improved:
            save_checkpoint(output_dir / "best.pt", model, optimizer, scheduler, epoch, best, metadata, args)
    if best["epoch"] < 0:
        raise InputError("no epoch produced a finite validation loss; nothing to select")
    bad = sum(h["train"]["nonpositive_net_weight_batches"] for h in history)
    if bad:
        print(f"WARNING: {bad} training batch(es) had a class with non-positive net weight; consider larger batches "
              "or a resampling treatment (see the physics-ml guidance on negative weights)", file=sys.stderr)
    (output_dir / "training_log.json").write_text(json.dumps(
        {"epochs": history, "nonpositive_net_weight_batches": bad, "best": best,
         "unassigned_events": idx["unassigned"]}, indent=2))

    # selection is finished: reload the best model, fix working points on val, evaluate test once
    best_path = output_dir / "best.pt"
    model.load_state_dict(torch.load(best_path, map_location=device, weights_only=True)["model_state_dict"])
    val_scores, test_scores = predict(model, z[va], device, args), predict(model, z[te], device, args)
    metrics = {"val": evaluate(val_scores, y[va], w[va], labels), "test": evaluate(test_scores, y[te], w[te], labels)}
    metrics["val"]["selection"] = dict(best)
    if n_classes == 2:
        metrics["val"]["working_points"] = working_points_val(val_scores, y[va], w[va], args.working_points)
        metrics["test"]["working_points"] = working_points_test(test_scores, y[te], w[te],
                                                                metrics["val"]["working_points"])
    scores_path, val_scores_path = output_dir / "test_scores.csv", output_dir / "val_scores.csv"
    write_scores(scores_path, [data["ids"][i] for i in te], y[te], w[te], test_scores, labels)
    write_scores(val_scores_path, [data["ids"][i] for i in va], y[va], w[va], val_scores, labels)

    labels_out = list(dict.fromkeys((["synthetic"] if not args.data else []) + list(args.status or [])))
    summary = {
        **({"status": labels_out} if labels_out else {}),
        "task": "classification", "features": features, "units": data["units"], "labels": labels,
        "grouping_key": data["grouping_key"], "split_manifest": str(Path(data["manifest"]).resolve()),
        "split_check": {k: split_check[k] for k in ("tool", "result", "report")},
        "training_domain": {f: [domain["min"][i], domain["max"][i]] for i, f in enumerate(features)},
        "preprocessing": preprocessing, "weights": weights_summary,
        "model_hash": weights_hash(best_path), "checkpoint": str(best_path.resolve()),
        "environment": {"torch_version": torch.__version__, "device": str(device), "precision": args.precision,
                        "seeds": seeds},
        "metrics": metrics, "scores": {"val": str(val_scores_path.resolve()), "test": str(scores_path.resolve())},
    }
    (output_dir / "run_summary.json").write_text(json.dumps(_finite(summary), indent=2, allow_nan=False))
    test = metrics["test"]
    shown = test.get("auc_weighted", test.get("auc_weighted_one_vs_rest"))
    print(f"best epoch {best['epoch'] + 1} ({best['name']}={best['value']:.4f}); test (held out): "
          f"loss={test['loss_weighted']:.4f} auc={shown}")
    print(f"run summary: {output_dir / 'run_summary.json'}")
    return 0


def _finite(o):
    """Replace non-finite floats with None so run_summary.json is strict JSON."""
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_finite(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except (InputError, OSError, json.JSONDecodeError) as exc:
        print(f"{Path(__file__).name}: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
