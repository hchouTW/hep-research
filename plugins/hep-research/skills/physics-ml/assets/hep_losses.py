"""PyTorch losses and masked operations for physics classifiers.

  weighted_bce          binary cross-entropy with signed event weights and an explicit normalization
  batch_weight_report   per-class weight sums in a batch, to monitor batches with non-positive net weight
  disco_penalty         weighted squared distance correlation between score and a protected variable (DisCo)
  masked_softmax        softmax over a masked axis that returns zeros, not NaN, for fully masked rows
  masked_mean           mean over a masked axis; empty sets give zeros

Status: verified with torch 2.14.1 on CPU (2026-10-13). The NumPy reference for disco_penalty is
distance_correlation_sq in hep_metrics.py; tests/skills/physics_ml/test_hep_losses.py compares the two, checks the
NaN guards (empty sets, constant-score batches) and the gradients when torch is installed.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def weighted_bce(logits: torch.Tensor, targets: torch.Tensor, weights: torch.Tensor | None = None,
                 norm: str = "abs") -> torch.Tensor:
    """Weighted BCE on logits. Signed weights are kept.

    norm="abs": divide by sum|w| (default; stable when sum(w) is near zero, keeps the sign of each term).
    norm="sum": divide by sum(w) (the unbiased weighted mean; unstable with strong cancellation).
    norm="none": return the weighted sum.
    With signed weights a flexible model can make the loss unbounded below; see ml-analysis.md, "Negative
    weights", for batch sizing, monitoring and the resampling alternatives.
    """
    logits = logits.reshape(-1)
    targets = targets.reshape(-1).to(logits.dtype)
    if logits.shape != targets.shape:
        raise ValueError(f"logits {tuple(logits.shape)} vs targets {tuple(targets.shape)}")
    per_event = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    if weights is None:
        return per_event.mean()
    w = weights.reshape(-1).to(per_event.dtype)
    if w.shape != per_event.shape:
        raise ValueError(f"weights {tuple(w.shape)} vs events {tuple(per_event.shape)}")
    total = (w * per_event).sum()
    if norm == "none":
        return total
    if norm == "abs":
        return total / w.abs().sum().clamp(min=torch.finfo(per_event.dtype).tiny)
    if norm == "sum":
        return total / w.sum()
    raise ValueError(f"unknown norm {norm!r}")


@torch.no_grad()
def batch_weight_report(targets: torch.Tensor, weights: torch.Tensor) -> dict:
    """Per-class sum(w), sum|w| and negative fraction for one batch. Log it; alert when sum(w) <= 0."""
    t = targets.reshape(-1).bool()
    w = weights.reshape(-1)
    out = {}
    for name, sel in (("signal", t), ("background", ~t)):
        ws = w[sel]
        out[name] = {"sum_w": float(ws.sum()), "sum_abs_w": float(ws.abs().sum()),
                     "neg_fraction": float((ws < 0).float().mean()) if ws.numel() else 0.0}
    return out


def disco_penalty(score: torch.Tensor, protected: torch.Tensor, weights: torch.Tensor | None = None,
                  eps: float = 1e-12, check_weights: bool = True) -> torch.Tensor:
    """Weighted squared distance correlation dCor^2(score, protected) (Kasieczka & Shih, arXiv:2001.05310).

    Call it on background events of the batch only: loss = bce + lam * disco_penalty(score[bkg], mass[bkg], |w|).
    Weights must be non-negative (use |w|); they are normalized to mean one inside. Memory is O(B^2).
    Computed in at least float32 (half precision loses the double-centering cancellation). eps sits inside the
    square root so a degenerate batch (constant scores) gives a finite gradient. check_weights=True (the default)
    refuses negative weights at the cost of a device synchronization; pass False only once the weights are known to
    be non-negative and the synchronization matters.
    """
    x = score.reshape(-1)
    if x.dtype in (torch.float16, torch.bfloat16):
        x = x.float()
    y = protected.reshape(-1).to(x.dtype)
    n = x.numel()
    if y.numel() != n:
        raise ValueError("score and protected variable must have the same length")
    if n < 2:
        return x.new_zeros(())
    w = torch.ones_like(x) if weights is None else weights.reshape(-1).to(x.dtype)
    if check_weights and bool((w < 0).any()):
        raise ValueError("disco_penalty needs non-negative weights; pass |w|")
    w = w / w.mean()

    def centered(v):
        a = (v[:, None] - v[None, :]).abs()
        row = (a * w[None, :]).mean(dim=1)
        return a - row[None, :] - row[:, None] + (row * w).mean()

    A, B = centered(x), centered(y)

    def dcov(P, Q):
        return ((P * Q * w[None, :]).mean(dim=1) * w).mean()

    denom = torch.sqrt((dcov(A, A) * dcov(B, B)).clamp(min=eps))
    return dcov(A, B) / denom


def masked_softmax(scores: torch.Tensor, mask: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """Softmax over `dim` ignoring positions where mask is False. Fully masked rows return all zeros (not NaN).

    `mask` must broadcast to `scores` (for attention: [B, 1, 1, N] key mask against [B, H, N, N] scores).
    """
    if mask.dim() != scores.dim():
        raise ValueError(f"mask must have the same number of dimensions as scores ({mask.dim()} vs {scores.dim()}); "
                         "reshape it explicitly, e.g. key_mask[:, None, None, :]")
    mask = mask.to(torch.bool).expand_as(scores)
    filled = scores.masked_fill(~mask, float("-inf"))
    any_valid = mask.any(dim=dim, keepdim=True)
    filled = torch.where(any_valid, filled, torch.zeros_like(filled))
    return torch.softmax(filled, dim=dim) * mask


def masked_mean(x: torch.Tensor, mask: torch.Tensor, dim: int = 1) -> torch.Tensor:
    """Mean of x [B, N, F] over the set axis with mask [B, N]; empty sets give zeros."""
    m = mask.to(x.dtype).unsqueeze(-1)
    return (x * m).sum(dim) / m.sum(dim).clamp(min=1.0)
