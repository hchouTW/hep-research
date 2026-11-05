"""Bitfields (Section 6.2.6) and the strides of volume IDs (Section 7.1).

A readout's fields are laid out in name order, so a bitfield does not depend on how a specification orders its keys. Strides
are hashed, so each lies within the canonical integer limit.
"""
from __future__ import annotations

from core.geometry.numbers import GeometryError

COPY_FIELD_LIMIT = 31  # a G4 copy number is a signed 32-bit integer
SEGMENTATION_FIELD_LIMIT = 53
TOTAL_LIMIT = 64
STRIDE_LIMIT = 2 ** 53 - 1


def width_for(count: int) -> int:
    """The bits that hold the values 0 ... count - 1."""
    return (count - 1).bit_length()


def layout(fields: dict, copy_fields: set, path: str = "") -> list[dict]:
    """{name: width} as [{name, kind, width, stride}]; copy_fields names the fields made of copy numbers."""
    out, offset = [], 0
    for name in sorted(fields):
        width = fields[name]
        kind = "copy" if name in copy_fields else "segmentation"
        limit = COPY_FIELD_LIMIT if kind == "copy" else SEGMENTATION_FIELD_LIMIT
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise GeometryError("bitfield-width", f"field {name!r}: width {width!r} is not a positive integer", path)
        if width > limit:
            raise GeometryError("bitfield-width", f"field {name!r} ({kind}) has {width} bits, more than {limit}", path)
        stride = 1 << offset
        if stride > STRIDE_LIMIT:
            raise GeometryError("bitfield-stride", f"field {name!r}: stride 2^{offset} is beyond 2^53 - 1", path)
        out.append({"name": name, "kind": kind, "width": width, "stride": stride})
        offset += width
    if offset > TOTAL_LIMIT:
        raise GeometryError("bitfield-total", f"{offset} bits in total, more than {TOTAL_LIMIT}", path)
    return out


def check_range(fields: list[dict], counts: dict, path: str = "") -> None:
    """Each field holds every value its index takes: counts is {name: number of values}."""
    widths = {field["name"]: field["width"] for field in fields}
    for name, count in counts.items():
        if name in widths and width_for(count) > widths[name]:
            raise GeometryError("bitfield-range", f"field {name!r}: {count} values need {width_for(count)} bits, "
                                                  f"it has {widths[name]}", path)


def level_strides(widths: list[int], path: str = "") -> list[int]:
    """The stride of each placement level of a volume ID, from the width of each level's value."""
    strides, offset = [], 0
    for width in widths:
        stride = 1 << offset
        if stride > STRIDE_LIMIT:
            raise GeometryError("volume-stride", f"stride 2^{offset} is beyond 2^53 - 1", path)
        strides.append(stride)
        offset += width
    if offset > TOTAL_LIMIT:
        raise GeometryError("volume-width", f"the level widths total {offset} bits, more than {TOTAL_LIMIT}", path)
    return strides


def check_strides(strides: list[int], path: str = "") -> None:
    if len(set(strides)) != len(strides):
        raise GeometryError("volume-stride", "two placement levels share a stride", path)
