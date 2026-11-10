"""The recipe's configuration, calo-cluster-configuration/1: the written constants of t04-values-v4.md sections 4.2 and 7.1.

Section 2.2 forbids any scale, offset or inflation derived from pulls or targets. The reader therefore accepts exactly the keys
below and no other, so such a constant has nowhere to go; tests/adapters/test_calo_cluster.py also checks the values against
the text of version 4.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from . import RECIPE

FORMAT = "calo-cluster-configuration/1"
DEFAULT_FILE = Path(__file__).resolve().parents[1] / "t08-grid-1.configuration.json"
KEYS = {"format", "recipe", "source", "grid", "shower_width_cells", "cell_quantum_mev", "noise_sigma_mev", "cell_threshold_mev",
        "seed_threshold_mev", "sharing_iterations", "peaks_kept"}
GRID_KEYS = {"nx", "ny", "cell_width"}


class ConfigurationError(ValueError):
    """The configuration is refused."""


@dataclass(frozen=True)
class Configuration:
    cells_x: int
    cells_y: int
    cell_width: float
    shower_width: float
    quantum: float
    noise_sigma: float
    cell_threshold: float
    seed_threshold: float
    sharing_iterations: int
    peaks_kept: int
    sha256: str
    document: dict

    @property
    def channels(self) -> int:
        return self.cells_x * self.cells_y


def _positive(name: str, value, integer: bool = False):
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        raise ConfigurationError(f"{name} must be {'an integer' if integer else 'a number'}")
    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} must be positive and finite")
    return value


def from_bytes(content: bytes) -> Configuration:
    try:
        doc = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConfigurationError(f"configuration is not JSON: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        extra = sorted(set(doc) - KEYS) if isinstance(doc, dict) else []
        raise ConfigurationError(f"configuration keys must be exactly {sorted(KEYS)}" + (f"; not allowed: {extra}" if extra else ""))
    if doc["format"] != FORMAT or doc["recipe"] != RECIPE:
        raise ConfigurationError(f"configuration must be {FORMAT} for {RECIPE}")
    grid = doc["grid"]
    if not isinstance(grid, dict) or set(grid) != GRID_KEYS:
        raise ConfigurationError(f"grid keys must be exactly {sorted(GRID_KEYS)}")
    if grid["cell_width"] != 1.0:
        raise ConfigurationError("this recipe works in cell units: cell_width must be 1")
    if doc["peaks_kept"] != 2:
        raise ConfigurationError("section 7.1 keeps the two highest peaks: peaks_kept must be 2")
    return Configuration(cells_x=_positive("grid.nx", grid["nx"], True), cells_y=_positive("grid.ny", grid["ny"], True), cell_width=1.0,
                         shower_width=float(_positive("shower_width_cells", doc["shower_width_cells"])),
                         quantum=float(_positive("cell_quantum_mev", doc["cell_quantum_mev"])),
                         noise_sigma=float(_positive("noise_sigma_mev", doc["noise_sigma_mev"])),
                         cell_threshold=float(_positive("cell_threshold_mev", doc["cell_threshold_mev"])),
                         seed_threshold=float(_positive("seed_threshold_mev", doc["seed_threshold_mev"])),
                         sharing_iterations=_positive("sharing_iterations", doc["sharing_iterations"], True), peaks_kept=2,
                         sha256=hashlib.sha256(content).hexdigest(), document=doc)


def load(path: Path | str | None = None) -> Configuration:
    path = Path(path) if path is not None else DEFAULT_FILE
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"configuration cannot be read: {exc.strerror}") from None
    return from_bytes(content)
