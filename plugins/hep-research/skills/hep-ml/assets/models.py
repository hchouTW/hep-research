"""Reusable PyTorch model templates."""

from __future__ import annotations

import hashlib

import torch
from torch import nn


def state_dict_hash(state: dict) -> str:
    """sha256 over the model weights only (parameter names, dtypes, shapes and bytes, in name order): the hash names
    the model, not the file, so it does not change with paths, optimizer state or the epoch counter. train_classifier.py
    records it as model_hash, calibration.py as the model a calibration was made for, inference.py compares them."""
    h = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        h.update(f"{name}|{tensor.dtype}|{tuple(tensor.shape)}|".encode())
        h.update(tensor.numpy().tobytes())
    return "sha256:" + h.hexdigest()


class MLPClassifier(nn.Module):
    """Simple MLP classifier.

    Input:  [batch_size, input_dim]
    Output: [batch_size, num_classes]
    """

    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class SmallCNN(nn.Module):
    """Small CNN for image classification.

    Input:  [batch_size, in_channels, height, width]
    Output: [batch_size, num_classes]
    """

    def __init__(self, in_channels: int = 3, num_classes: int = 10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)
