"""The module table (Section 15.4): every shape, placement and modifier, with the phase that opens it. Static, so a test can
confirm the Python and C++ sides list the same modules; core/provider's run-time registry is not reused."""
from __future__ import annotations

from core.geometry.numbers import GeometryError

SHAPES = {"box": "S1", "trd": "S3", "tube": "S3", "polygon_prism": "S3", "cone": "S7", "sphere_section": "S7", "polycone": "S7",
          "polyhedra": "S7"}
PLACEMENTS = {"single": "S1", "linear": "S1", "stack": "S1", "grid": "S3", "ring": "S3", "explicit": "S3"}
MODIFIERS = {"shell": "S3", "clip": "S3", "absent": "S3"}
OPEN_PHASE = 1  # this code implements S1


def require_open(table: dict, name: str, kind: str, path: str) -> None:
    if name not in table:
        raise GeometryError("module-unknown", f"{name!r} is not a {kind}", path)
    if int(table[name][1:]) > OPEN_PHASE:
        raise GeometryError("module-not-open", f"{kind} {name!r} opens in {table[name]}", path)
