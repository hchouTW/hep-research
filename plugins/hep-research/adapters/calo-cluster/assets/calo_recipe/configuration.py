"""The recipe's configuration, calo-cluster-configuration/1: the written constants of t04-values-v4.md sections 4.2 and 7.1.

Section 2.2 forbids any scale, offset or inflation derived from pulls or targets. The reader therefore accepts exactly the keys
below and no other, so such a constant has nowhere to go; tests/adapters/test_calo_cluster.py also checks the values against
the text of version 4.

calo-cluster-configuration/2 (D2 stage 3) is the configuration of a labelled input (calo-cells/2), another simulation's grid
whose constants section 4.2 does not give. It has the keys of /1 and two more: `label`, the input label it is written for
(cell_input.LABELS), and `sources`, the source of each constant (CONSTANT_KEYS), or null where the constant has none, so a
number without a source says so in the file. The shower profile width and the response model (q, sigma_n) are either all
three numbers (section 7.1 in full, with stated constants) or all three null. Null means: no profile, so a component with two
kept peaks is not split but kept as one object of kind "unsplit"; and no response model, so no uncertainty is formed (status
"no-response-model"). Nothing in it may be fitted or tuned on the labelled sample: such a sample supports no performance
number (t07-t09-task-sheets.md, T08). A /2 file also has `unresolved`: for each constant whose value is used without a source,
its plan 1.1 status (Unresolved), the decision that allows it, its scope, its owner and its exit condition (UNRESOLVED_KEYS); such
a constant's source is null. A labelled product carries this record. A /1 configuration takes no null and no label; the recipe refuses a labelled input with a
/1 configuration and an unlabelled input with a /2 one.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import RECIPE
from .cell_input import LABELS

FORMAT = "calo-cluster-configuration/1"
FORMAT_LABELLED = "calo-cluster-configuration/2"
DEFAULT_FILE = Path(__file__).resolve().parents[1] / "t08-grid-1.configuration.json"
KEYS = {"format", "recipe", "source", "grid", "shower_width_cells", "cell_quantum_mev", "noise_sigma_mev", "cell_threshold_mev",
        "seed_threshold_mev", "sharing_iterations", "peaks_kept"}
CONSTANT_KEYS = KEYS - {"format", "recipe", "source"}
LABELLED_KEYS = KEYS | {"label", "sources", "unresolved"}
UNRESOLVED_KEYS = {"status", "decision", "scope", "owner", "exit"}
UNRESOLVED_STATUS = "Unresolved (plan 1.1)"
NULLABLE = ("shower_width_cells", "cell_quantum_mev", "noise_sigma_mev")     # /2 only, all three or none
GRID_KEYS = {"nx", "ny", "cell_width"}


class ConfigurationError(ValueError):
    """The configuration is refused."""


@dataclass(frozen=True)
class Configuration:
    cells_x: int
    cells_y: int
    cell_width: float
    shower_width: float | None        # None only in /2: no profile
    quantum: float | None             # None only in /2: no response model
    noise_sigma: float | None
    cell_threshold: float
    seed_threshold: float
    sharing_iterations: int
    peaks_kept: int
    sha256: str
    document: dict
    format: str = FORMAT
    label: str | None = None
    unresolved: dict = field(default_factory=dict)   # /2: constants used without a source, with their plan 1.1 record

    @property
    def channels(self) -> int:
        return self.cells_x * self.cells_y

    @property
    def splits(self) -> bool:
        """Whether two kept peaks are shared by section 7.1's profile; without a profile they are left unsplit."""
        return self.shower_width is not None

    @property
    def response_model(self) -> bool:
        """Whether the cell response model (q, sigma_n) is given, so section 7.1's uncertainties can be formed."""
        return self.quantum is not None


def _positive(name: str, value, integer: bool = False):
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        raise ConfigurationError(f"{name} must be {'an integer' if integer else 'a number'}")
    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} must be positive and finite")
    return value


def check_unresolved(unresolved, sources=None) -> None:
    """The unresolved record: constant -> {status, decision, scope, owner, exit}, each a non-empty string, status Unresolved
    (plan 1.1); with the sources given, an unresolved constant has none (null)."""
    if not isinstance(unresolved, dict) or not set(unresolved) <= CONSTANT_KEYS:
        raise ConfigurationError(f"unresolved must map constants of {sorted(CONSTANT_KEYS)} to their record")
    for key, record in unresolved.items():
        if not isinstance(record, dict) or set(record) != UNRESOLVED_KEYS or \
                not all(isinstance(v, str) and v for v in record.values()) or record["status"] != UNRESOLVED_STATUS:
            raise ConfigurationError(f"unresolved {key}: needs exactly {sorted(UNRESOLVED_KEYS)}, status {UNRESOLVED_STATUS!r}")
        if sources is not None and sources.get(key) is not None:
            raise ConfigurationError(f"unresolved {key}: an unresolved constant has no source (null), got {sources[key]!r}")


def from_bytes(content: bytes) -> Configuration:
    try:
        doc = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConfigurationError(f"configuration is not JSON: {exc}") from None
    labelled = isinstance(doc, dict) and doc.get("format") == FORMAT_LABELLED
    keys = LABELLED_KEYS if labelled else KEYS
    if not isinstance(doc, dict) or set(doc) != keys:
        extra = sorted(set(doc) - keys) if isinstance(doc, dict) else []
        raise ConfigurationError(f"configuration keys must be exactly {sorted(keys)}" + (f"; not allowed: {extra}" if extra else ""))
    if doc["format"] not in (FORMAT, FORMAT_LABELLED) or doc["recipe"] != RECIPE:
        raise ConfigurationError(f"configuration must be {FORMAT} or {FORMAT_LABELLED} for {RECIPE}")
    nulls = [k for k in NULLABLE if doc[k] is None]
    if labelled:
        if doc["label"] not in LABELS:
            raise ConfigurationError(f"label {doc['label']!r} is not one of {sorted(LABELS)}")
        sources = doc["sources"]
        if not isinstance(sources, dict) or set(sources) != CONSTANT_KEYS or \
                not all(v is None or (isinstance(v, str) and v) for v in sources.values()):
            raise ConfigurationError(f"sources must name the source of each of {sorted(CONSTANT_KEYS)}, or null where it has none")
        check_unresolved(doc["unresolved"], sources)
        if nulls and len(nulls) != len(NULLABLE):
            raise ConfigurationError(f"{', '.join(NULLABLE)} are numbers together or null together: got null {nulls}")
    elif nulls:
        raise ConfigurationError(f"{FORMAT} takes no null constant: {nulls}")
    width, quantum, noise = (None, None, None) if nulls else (
        float(_positive("shower_width_cells", doc["shower_width_cells"])), float(_positive("cell_quantum_mev", doc["cell_quantum_mev"])),
        float(_positive("noise_sigma_mev", doc["noise_sigma_mev"])))
    grid = doc["grid"]
    if not isinstance(grid, dict) or set(grid) != GRID_KEYS:
        raise ConfigurationError(f"grid keys must be exactly {sorted(GRID_KEYS)}")
    if grid["cell_width"] != 1.0:
        raise ConfigurationError("this recipe works in cell units: cell_width must be 1")
    if doc["peaks_kept"] != 2:
        raise ConfigurationError("section 7.1 keeps the two highest peaks: peaks_kept must be 2")
    return Configuration(cells_x=_positive("grid.nx", grid["nx"], True), cells_y=_positive("grid.ny", grid["ny"], True), cell_width=1.0,
                         shower_width=width, quantum=quantum, noise_sigma=noise,
                         cell_threshold=float(_positive("cell_threshold_mev", doc["cell_threshold_mev"])),
                         seed_threshold=float(_positive("seed_threshold_mev", doc["seed_threshold_mev"])),
                         sharing_iterations=_positive("sharing_iterations", doc["sharing_iterations"], True), peaks_kept=2,
                         sha256=hashlib.sha256(content).hexdigest(), document=doc, format=doc["format"],
                         label=doc["label"] if labelled else None, unresolved=dict(doc["unresolved"]) if labelled else {})


def load(path: Path | str | None = None) -> Configuration:
    path = Path(path) if path is not None else DEFAULT_FILE
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"configuration cannot be read: {exc.strerror}") from None
    return from_bytes(content)
