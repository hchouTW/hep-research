"""Dataset template for custom PyTorch projects."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import torch
from torch.utils.data import Dataset


class CustomTensorDataset(Dataset):
    """Example dataset backed by tensors saved on disk.

    Replace this with project-specific loading logic.
    """

    def __init__(self, features_path: str | Path, labels_path: str | Path, transform: Optional[Callable] = None):
        self.features = torch.load(features_path, map_location="cpu")
        self.labels = torch.load(labels_path, map_location="cpu")
        self.transform = transform

        if len(self.features) != len(self.labels):
            raise ValueError(f"features and labels have different lengths: {len(self.features)} vs {len(self.labels)}")

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        x = self.features[idx]
        y = self.labels[idx]
        if self.transform is not None:
            x = self.transform(x)
        return x, y
