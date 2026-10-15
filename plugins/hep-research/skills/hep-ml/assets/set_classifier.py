#!/usr/bin/env python3
"""Permutation-invariant set classifier for particles or jet constituents of variable multiplicity (PyTorch).

Contents:
  wrap_phi             Delta-phi into (-pi, pi] (NumPy arrays or torch tensors)
  particle_features    per-particle features relative to the jet axis: d_eta, d_phi, log pT, log(pT/pT_jet), dR
  fit_standardization / apply_standardization   per-feature mean and std from the training partition only
  collate_sets         ragged list of [n_i, F] arrays -> padded x [B, N, F] and boolean mask [B, N]
  PFN                  Deep Sets / Particle Flow Network: rho(pool_i phi(p_i)), masked sum or mean pooling
  ParTLite             masked multi-head self-attention blocks, no positional encoding, masked-mean pooling
                       (a ParT without the pairwise interaction bias; Qu, Li, Qian, arXiv:2202.03772)
  make_toy             synthetic jets: signal has more, more collimated constituents; weights include negatives

CLI: python3 set_classifier.py --model pfn --epochs 3 --output-dir out/
trains on the built-in toy on CPU and writes out/set_classifier.pt (state dict, config, standardization) and
out/metrics.json (weighted AUC from hep_metrics on a separate validation toy). A successful run is a software check
of the pipeline, not a tagger for any detector.

Masking. Padded entries are zeroed at the input, never enter a sum, a mean or an attention key, and are excluded
from pooling, so the output does not depend on padding values or padding length. An empty set (all mask False)
gives a finite output: zeros after pooling, masked_softmax returns zeros for a fully masked row. ParTLite also
feeds log(1 + multiplicity) to the head, because masked-mean pooling alone does not see the multiplicity.

Weights. Training uses hep_losses.weighted_bce with signed weights normalized by sum|w| (ml-analysis.md, "Negative
weights"); the per-batch net weight per class is monitored and the count of batches with sum(w) <= 0 reported.
torch is imported inside functions, so --help and the NumPy helpers work without it.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_MODULES: dict = {}
_CLASSES: dict = {}


def _sibling(name):
    """Load hep_metrics / hep_losses from this directory by path (works when imported from anywhere)."""
    if name not in _MODULES:
        spec = importlib.util.spec_from_file_location(f"_set_classifier_{name}", _HERE / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULES[name] = mod
    return _MODULES[name]


# --------------------------------------------------------------------------- features (NumPy, no torch)

def wrap_phi(dphi):
    """Map angles to (-pi, pi]. Works elementwise on floats, NumPy arrays and torch tensors (Python-style %)."""
    return -((-dphi + math.pi) % (2 * math.pi) - math.pi)


FEATURE_NAMES = ("d_eta", "d_phi", "log_pt", "log_pt_frac", "d_r")


def particle_features(pt, eta, phi, jet_pt=None, jet_eta=None, jet_phi=None):
    """Per-particle features [n, 5] (FEATURE_NAMES) relative to the jet axis.

    Without an explicit axis, the pT-weighted centroid is used, with phi averaged on the circle (atan2 of the
    pT-weighted sin and cos) so that a jet straddling phi = +-pi gets the right axis. jet_pt defaults to the scalar
    sum of constituent pT. An empty set returns shape [0, 5].
    """
    pt, eta, phi = (np.asarray(a, dtype=float).ravel() for a in (pt, eta, phi))
    if not (pt.shape == eta.shape == phi.shape):
        raise ValueError("pt, eta, phi must have the same length")
    if pt.size == 0:
        return np.zeros((0, len(FEATURE_NAMES)))
    if np.any(pt <= 0):
        raise ValueError("constituent pT must be positive")
    tot = pt.sum()
    if jet_pt is None:
        jet_pt = tot
    if jet_eta is None:
        jet_eta = float(np.sum(pt * eta) / tot)
    if jet_phi is None:
        jet_phi = math.atan2(float(np.sum(pt * np.sin(phi))), float(np.sum(pt * np.cos(phi))))
    deta = eta - jet_eta
    dphi = wrap_phi(phi - jet_phi)
    return np.stack([deta, dphi, np.log(pt), np.log(pt / jet_pt), np.hypot(deta, dphi)], axis=1)


def fit_standardization(sets):
    """Per-feature mean and std over all particles of the training partition (never the validation/test)."""
    allp = np.concatenate([np.asarray(s, dtype=float).reshape(-1, np.shape(s)[-1]) for s in sets if len(s)])
    std = allp.std(axis=0)
    return {"mean": allp.mean(axis=0).tolist(), "std": np.where(std > 0, std, 1.0).tolist()}


def apply_standardization(sets, stats):
    m, s = np.asarray(stats["mean"]), np.asarray(stats["std"])
    return [(np.asarray(x, dtype=float) - m) / s if len(x) else np.asarray(x, dtype=float) for x in sets]


def truncation_rate(sets, max_len):
    """Fraction of sets longer than max_len (record it: a cap that cuts high-multiplicity signal biases)."""
    return float(np.mean([len(s) > max_len for s in sets])) if len(sets) else 0.0


def make_toy(n, seed=0, neg_fraction=0.1, empty_fraction=0.01):
    """Synthetic jets as ragged per-particle feature arrays, labels and signed weights.

    Signal: multiplicity ~ Poisson(20), angular spread 0.16; background: Poisson(16), spread 0.22, each with a
    log-normal jet-to-jet spread variation (30 %), so the classes overlap (AUC well below 1). Jet axes are
    uniform in phi, so many jets straddle phi = +-pi (exercises wrap_phi). A fraction of events have no constituents
    (empty sets) and a fraction carry weight -1 (both classes keep positive net weight). Returns (sets, y, w).
    """
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.5).astype(np.float32)
    sets = []
    for lab in y:
        mult = rng.poisson(20 if lab else 16)
        if rng.random() < empty_fraction:
            mult = 0
        spread = (0.16 if lab else 0.22) * math.exp(rng.normal(0, 0.3))   # jet-to-jet variation
        axis_eta, axis_phi = rng.uniform(-2, 2), rng.uniform(-math.pi, math.pi)
        pt = rng.exponential(5.0, mult) + 0.5
        eta = axis_eta + rng.normal(0, spread, mult)
        phi = wrap_phi(axis_phi + rng.normal(0, spread, mult))
        order = np.argsort(-pt)
        sets.append(particle_features(pt[order], eta[order], phi[order]).astype(np.float32))
    w = np.where(rng.random(n) < neg_fraction, -1.0, 1.0).astype(np.float32)
    return sets, y, w


# --------------------------------------------------------------------------- torch parts

def collate_sets(sets, max_len=None, dtype=None):
    """Pad a ragged list of [n_i, F] arrays to x [B, N, F] with a mask [B, N] (True = real particle).

    N = max(n_i) (at least 1, so an all-empty batch still has a valid shape), capped at max_len; sets are
    truncated to their first max_len entries (sort by pT first). Padded entries are zero.
    """
    import torch
    dtype = dtype or torch.float32
    if not len(sets):
        raise ValueError("empty batch")
    arrs = [np.asarray(s, dtype=float) for s in sets]
    nf = {a.shape[-1] for a in arrs if a.ndim == 2 and a.shape[0] > 0}
    if len(nf) > 1:
        raise ValueError(f"inconsistent feature dimensions {sorted(nf)}")
    n_feat = nf.pop() if nf else (arrs[0].shape[-1] if arrs[0].ndim == 2 else 0)
    n_max = max(1, max(a.shape[0] if a.ndim == 2 else 0 for a in arrs))
    if max_len is not None:
        n_max = min(n_max, int(max_len))
    x = torch.zeros(len(arrs), n_max, n_feat, dtype=dtype)
    mask = torch.zeros(len(arrs), n_max, dtype=torch.bool)
    for i, a in enumerate(arrs):
        k = min(a.shape[0] if a.ndim == 2 else 0, n_max)
        if k:
            x[i, :k] = torch.as_tensor(a[:k], dtype=dtype)
            mask[i, :k] = True
    return x, mask


def _classes():
    if _CLASSES:
        return _CLASSES
    import torch
    from torch import nn

    hl = _sibling("hep_losses")

    def mlp(sizes, final_act=False):
        layers = []
        for i, (a, b) in enumerate(zip(sizes[:-1], sizes[1:])):
            layers.append(nn.Linear(a, b))
            if i < len(sizes) - 2 or final_act:
                layers.append(nn.ReLU())
        return nn.Sequential(*layers)

    class PFN(nn.Module):
        """f({p_i}) = rho(pool_i phi(p_i)). pool="sum" (PFN; sees multiplicity) or "mean"."""

        def __init__(self, n_feat, hidden=64, latent=64, pool="sum", n_out=1):
            super().__init__()
            if pool not in ("sum", "mean"):
                raise ValueError("pool must be 'sum' or 'mean'")
            self.pool = pool
            self.phi = mlp([n_feat, hidden, hidden, latent], final_act=True)
            self.rho = mlp([latent, hidden, hidden, n_out])

        def forward(self, x, mask):
            m = mask.unsqueeze(-1).to(x.dtype)
            h = self.phi(x.masked_fill(~mask.unsqueeze(-1), 0.0)) * m
            pooled = h.sum(1) if self.pool == "sum" else h.sum(1) / m.sum(1).clamp(min=1.0)
            return self.rho(pooled).squeeze(-1)

    class MaskedSelfAttention(nn.Module):
        def __init__(self, dim, heads):
            super().__init__()
            if dim % heads:
                raise ValueError("dim must be divisible by heads")
            self.h, self.d = heads, dim // heads
            self.qkv = nn.Linear(dim, 3 * dim)
            self.out = nn.Linear(dim, dim)

        def forward(self, x, mask):
            b, n, _ = x.shape
            q, k, v = self.qkv(x).view(b, n, 3, self.h, self.d).permute(2, 0, 3, 1, 4)
            scores = q @ k.transpose(-2, -1) / math.sqrt(self.d)              # [B, H, N, N]
            att = hl.masked_softmax(scores, mask[:, None, None, :])            # fully masked rows -> 0, not NaN
            return self.out((att @ v).transpose(1, 2).reshape(b, n, -1))

    class Block(nn.Module):
        def __init__(self, dim, heads, ff, dropout):
            super().__init__()
            self.n1, self.n2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
            self.att = MaskedSelfAttention(dim, heads)
            self.ff = nn.Sequential(nn.Linear(dim, ff), nn.GELU(), nn.Linear(ff, dim))
            self.drop = nn.Dropout(dropout)

        def forward(self, x, mask):
            m = mask.unsqueeze(-1).to(x.dtype)
            x = x + self.drop(self.att(self.n1(x), mask))
            x = x + self.drop(self.ff(self.n2(x)))
            return x * m                                                     # keep padded tokens at zero

    class ParTLite(nn.Module):
        """Self-attention over particles without positional encoding (permutation equivariant), then masked-mean
        pooling plus log(1 + multiplicity) into an MLP head (permutation invariant)."""

        def __init__(self, n_feat, dim=64, heads=4, depth=2, ff=128, dropout=0.0, n_out=1):
            super().__init__()
            self.embed = mlp([n_feat, dim, dim])
            self.blocks = nn.ModuleList(Block(dim, heads, ff, dropout) for _ in range(depth))
            self.norm = nn.LayerNorm(dim)
            self.head = mlp([dim + 1, dim, n_out])

        def forward(self, x, mask):
            m = mask.unsqueeze(-1).to(x.dtype)
            h = self.embed(x.masked_fill(~mask.unsqueeze(-1), 0.0)) * m
            for blk in self.blocks:
                h = blk(h, mask)
            pooled = hl.masked_mean(self.norm(h) * m, mask)
            mult = torch.log1p(mask.sum(1, keepdim=True).to(x.dtype))
            return self.head(torch.cat([pooled, mult], dim=-1)).squeeze(-1)

    _CLASSES.update(PFN=PFN, ParTLite=ParTLite)
    return _CLASSES


def __getattr__(name):            # module-level PFN / ParTLite, built on first access (needs torch)
    if name in ("PFN", "ParTLite"):
        return _classes()[name]
    raise AttributeError(name)


def build_model(kind, n_feat, **kw):
    cls = {"pfn": "PFN", "part": "ParTLite"}.get(kind)
    if cls is None:
        raise ValueError("model must be 'pfn' or 'part'")
    return _classes()[cls](n_feat, **kw)


def predict(model, sets, batch_size=512):
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(sets), batch_size):
            x, m = collate_sets(sets[i:i + batch_size])
            out.append(torch.sigmoid(model(x, m)).numpy())
    return np.concatenate(out)


def train(kind="pfn", epochs=3, n_train=4000, n_val=2000, batch_size=128, lr=2e-3, seed=0, max_len=64,
          output_dir=None, log=print):
    """Train on the toy; return the metrics dict (and write checkpoint + metrics.json when output_dir is set)."""
    import torch
    hl, hm = _sibling("hep_losses"), _sibling("hep_metrics")
    torch.manual_seed(seed)
    tr_sets, tr_y, tr_w = make_toy(n_train, seed=seed)
    va_sets, va_y, va_w = make_toy(n_val, seed=seed + 10_000)          # independent validation sample
    stats = fit_standardization(tr_sets)
    tr_sets, va_sets = apply_standardization(tr_sets, stats), apply_standardization(va_sets, stats)
    model = build_model(kind, len(FEATURE_NAMES))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    history, bad_batches = [], 0
    t0 = time.time()
    for ep in range(epochs):
        model.train()
        perm = rng.permutation(n_train)
        tot, nb = 0.0, 0
        for i in range(0, n_train, batch_size):
            idx = perm[i:i + batch_size]
            x, m = collate_sets([tr_sets[j] for j in idx], max_len=max_len)
            y, w = torch.as_tensor(tr_y[idx]), torch.as_tensor(tr_w[idx])
            rep = hl.batch_weight_report(y, w)
            bad_batches += int(rep["signal"]["sum_w"] <= 0 or rep["background"]["sum_w"] <= 0)
            loss = hl.weighted_bce(model(x, m), y, w, norm="abs")
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            tot, nb = tot + float(loss.detach()), nb + 1
        p = predict(model, va_sets)
        auc = hm.weighted_auc(p, va_y.astype(int), va_w)
        history.append({"epoch": ep + 1, "train_loss": tot / nb, "val_auc_weighted": auc})
        log(f"epoch {ep + 1}: train_loss {tot / nb:.4f} val_auc_weighted {auc:.4f}")
    metrics = {
        "model": kind, "seed": seed, "epochs": epochs, "n_train": n_train, "n_val": n_val,
        "val_auc_weighted": history[-1]["val_auc_weighted"], "history": history,
        "negative_weight_fraction_train": float(np.mean(tr_w < 0)),
        "n_empty_sets_train": int(sum(len(s) == 0 for s in tr_sets)),
        "truncation_rate_train": truncation_rate(tr_sets, max_len), "max_len": max_len,
        "batches_nonpositive_class_weight": bad_batches, "features": list(FEATURE_NAMES),
        "torch": torch.__version__, "device": "cpu", "seconds": round(time.time() - t0, 2),
        "note": "toy data: a software check of the pipeline, not a physics result",
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": model.state_dict(), "model": kind, "n_feat": len(FEATURE_NAMES),
                    "standardization": stats, "features": list(FEATURE_NAMES), "max_len": max_len},
                   out / "set_classifier.pt")
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False))
    return metrics, model


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", choices=("pfn", "part"), default="pfn")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--n-train", type=int, default=4000)
    ap.add_argument("--n-val", type=int, default=2000)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--max-len", type=int, default=64, help="multiplicity cap (truncation rate is reported)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output-dir", default="set_classifier_out")
    a = ap.parse_args(argv)
    try:
        import torch  # noqa: F401
    except ImportError:
        print("error: PyTorch is required for training (pip install torch)", file=sys.stderr)
        return 2
    metrics, _ = train(a.model, a.epochs, a.n_train, a.n_val, a.batch_size, a.lr, a.seed, a.max_len, a.output_dir,
                       log=lambda s: print(s, file=sys.stderr))
    print(json.dumps({"val_auc_weighted": metrics["val_auc_weighted"], "output_dir": a.output_dir}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
