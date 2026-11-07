"""Segmentation of a volume into readout bins (Section 6.2.6): checks and bin counts, without placing volumes. A bin's index must fit in 16 bits (Section 10)."""
from __future__ import annotations

import math

from core.geometry.numbers import GeometryError

KINDS = ("none", "along_axis", "cartesian_xy", "cartesian_xyz", "polar")
MAXIMUM_BINS = 2 ** 16


def bin_count(block, half_mm: list) -> int:
    """The number of bins of a segmentation over a solid with these half-lengths; raises on a wrong form."""
    if block in (None, "none"):
        return 1
    kind, body = next(iter(block.items()))
    if kind not in KINDS:
        raise GeometryError("segmentation-kind", f"segmentation {kind!r}")
    sizes = [2 * float(value) for value in half_mm]
    if kind == "polar":
        width, sectors = float(body["width_r_mm"]), int(body["phi_bins"])
        if width <= 0 or sectors < 1:
            raise GeometryError("segmentation-size", f"polar {body!r}")
        count = math.ceil(math.hypot(sizes[0], sizes[1]) / 2 / width) * sectors  # to the farthest corner, as Grid in NewScorers.hh
    else:
        widths = [float(body["width_mm"])] if kind == "along_axis" else [float(value) for value in body["width_mm"]]
        extents = [sizes["xyz".index(body["axis"])]] if kind == "along_axis" else sizes[:len(widths)]
        if len(widths) != {"along_axis": 1, "cartesian_xy": 2, "cartesian_xyz": 3}[kind] or any(width <= 0 for width in widths):
            raise GeometryError("segmentation-size", f"{kind} {body!r}")
        count = math.prod(math.ceil(extent / width - 1e-9) for extent, width in zip(extents, widths))
    if count > MAXIMUM_BINS:
        raise GeometryError("segmentation-bins", f"{count} bins exceed {MAXIMUM_BINS}")
    return count
