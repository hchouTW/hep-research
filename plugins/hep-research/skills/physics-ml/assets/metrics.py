"""Reusable PyTorch metric helpers.

These functions operate on tensors and return Python floats or tensors suitable
for logging. They intentionally avoid external metric dependencies.
"""

from __future__ import annotations

import torch


def multiclass_accuracy(logits: torch.Tensor, targets: torch.Tensor) -> float:
    """Return accuracy for single-label multiclass classification."""
    if logits.ndim != 2:
        raise ValueError(f"Expected logits [B, C], got {tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"Expected targets [B], got {tuple(targets.shape)}")
    preds = logits.argmax(dim=1)
    return (preds == targets).float().mean().item()


def binary_accuracy(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5) -> float:
    """Return accuracy for binary logits and 0/1 targets."""
    logits = logits.squeeze(-1)
    targets = targets.bool()
    preds = torch.sigmoid(logits) >= threshold
    return (preds == targets).float().mean().item()


def multilabel_accuracy(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5) -> float:
    """Return elementwise multilabel accuracy for logits [B, L]."""
    if logits.shape != targets.shape:
        raise ValueError(f"logits and targets must match, got {tuple(logits.shape)} and {tuple(targets.shape)}")
    preds = torch.sigmoid(logits) >= threshold
    return (preds == targets.bool()).float().mean().item()


def regression_mae(preds: torch.Tensor, targets: torch.Tensor) -> float:
    """Return mean absolute error."""
    return (preds - targets).abs().mean().item()


def regression_rmse(preds: torch.Tensor, targets: torch.Tensor) -> float:
    """Return root mean squared error."""
    return torch.sqrt(torch.mean((preds - targets) ** 2)).item()
