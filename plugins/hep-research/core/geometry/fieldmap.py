"""Field maps (Section 6.2.8, S7): the g4sim-field-map/1 text format, its grid, and trilinear interpolation. Pure computation:
contracts/geometry.py reads the file by its recorded hash, and the C++ builder (FieldMap.hh) interpolates in the same order.

The file, in UTF-8:

    g4sim-field-map/1
    origin_mm X Y Z
    step_mm DX DY DZ
    count NX NY NZ
    bx_tesla by_tesla bz_tesla
    then NX * NY * NZ lines of three numbers, x fastest, then y, then z

The grid lies in the local frame of the one template that declares the field. A point outside the grid takes the field at
the nearest point of the grid; check-spec requires the grid to cover that template's bounding box, so only a trial point
of the stepper outside the volume ever reaches that case."""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

from core.geometry.numbers import GeometryError, as_text

FORMAT = "g4sim-field-map/1"
COLUMNS = "bx_tesla by_tesla bz_tesla"


def _header(line: str, key: str, path: str) -> list[str]:
    parts = line.split()
    if len(parts) != 4 or parts[0] != key:
        raise GeometryError("field-map-format", f"expected '{key} A B C', found {line[:60]!r}", path)
    return parts[1:]


def parse(text: str, path: str = "") -> dict:
    """{origin_mm, step_mm, count} as exact text and integers, and values as floats (bx, by, bz per node, x fastest)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) < 5 or lines[0] != FORMAT:
        raise GeometryError("field-map-format", f"the first line is not {FORMAT}", path)
    try:
        origin = [Decimal(value) for value in _header(lines[1], "origin_mm", path)]
        step = [Decimal(value) for value in _header(lines[2], "step_mm", path)]
    except InvalidOperation as err:
        raise GeometryError("field-map-format", f"a grid number is not decimal ({err})", path) from err
    count_text = _header(lines[3], "count", path)
    if not all(value.isdigit() for value in count_text):
        raise GeometryError("field-map-format", f"count {count_text} is not three integers", path)
    count = [int(value) for value in count_text]
    if not all(value.is_finite() for value in origin + step) or any(value <= 0 for value in step):
        raise GeometryError("field-map-format", f"steps {step} must be finite and positive", path)
    if any(value < 2 for value in count):
        raise GeometryError("field-map-format", f"count {count} needs at least two nodes on each axis", path)
    if " ".join(lines[4].split()) != COLUMNS:
        raise GeometryError("field-map-format", f"the column line is not {COLUMNS!r}", path)
    rows = lines[5:]
    nodes = count[0] * count[1] * count[2]
    if len(rows) != nodes:
        raise GeometryError("field-map-format", f"{len(rows)} value lines for {nodes} nodes", path)
    values = []
    for number, row in enumerate(rows, start=6):
        parts = row.split()
        try:
            triple = [float(value) for value in parts]
        except ValueError as err:
            raise GeometryError("field-map-format", f"line {number}: {err}", path) from err
        if len(triple) != 3 or not all(math.isfinite(value) for value in triple):
            raise GeometryError("field-map-format", f"line {number} is not three finite numbers", path)
        values.extend(triple)
    return {"grid": {"origin_mm": [as_text(value) for value in origin], "step_mm": [as_text(value) for value in step], "count": count},
            "values": values}


def extent(grid: dict) -> list[tuple[Decimal, Decimal]]:
    """Each axis's [first node, last node] in mm, exactly."""
    return [(Decimal(origin), Decimal(origin) + Decimal(step) * (count - 1))
            for origin, step, count in zip(grid["origin_mm"], grid["step_mm"], grid["count"])]


def interpolate(grid: dict, values: list[float], point_mm) -> list[float]:
    """The field in tesla at a local point: trilinear in the cell that holds it, the point first moved onto the grid. The
    order of operations is FieldMap.hh's, so both sides round alike."""
    cells, weights = [], []
    for axis in range(3):
        origin, step, count = float(grid["origin_mm"][axis]), float(grid["step_mm"][axis]), grid["count"][axis]
        u = min(max((point_mm[axis] - origin) / step, 0.0), float(count - 1))
        index = min(int(math.floor(u)), count - 2)
        cells.append(index)
        weights.append(u - index)
    nx, ny = grid["count"][0], grid["count"][1]
    field = [0.0, 0.0, 0.0]
    for c in (0, 1):
        for b in (0, 1):
            for a in (0, 1):
                w = (weights[0] if a else 1.0 - weights[0]) * (weights[1] if b else 1.0 - weights[1]) * (weights[2] if c else 1.0 - weights[2])
                node = 3 * ((cells[2] + c) * ny * nx + (cells[1] + b) * nx + (cells[0] + a))
                for k in range(3):
                    field[k] += w * values[node + k]
    return field
