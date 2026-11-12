"""destriper-timestream/1: per sample a pixel index and a value; baselines are consecutive runs of baseline_length samples."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy

FORMAT = "destriper-timestream/1"
KEYS = frozenset({"format", "role", "unit", "pixels", "baseline_length", "noise_premise", "pixel", "value"})


class InputError(ValueError):
    """The input cannot be read or used (exit 2, rejected)."""


class Refusal(ValueError):
    """The input is readable, and the map is not determined by it and the one zero-sum constraint (exit 1, refused)."""

    def __init__(self, message: str, components: list | None = None):
        super().__init__(message)
        self.components = components or []


@dataclass(frozen=True)
class Timestream:
    pixel: numpy.ndarray
    value: numpy.ndarray
    pixels: int
    length: int
    unit: str
    noise_premise: str

    @property
    def samples(self) -> int:
        return int(self.pixel.size)

    @property
    def baselines(self) -> int:
        return self.samples // self.length

    @property
    def baseline(self) -> numpy.ndarray:
        return numpy.arange(self.samples) // self.length


def _components(pixel: list[int], length: int, pixels: int) -> list[dict]:
    """Connected components of the graph whose nodes are pixels and baselines, joined by every sample (union-find)."""
    parent = list(range(pixels + len(pixel) // length))

    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for t, p in enumerate(pixel):
        first, second = root(p), root(pixels + t // length)
        if first != second:
            parent[max(first, second)] = min(first, second)
    groups: dict[int, dict] = {}
    for node in range(len(parent)):
        group = groups.setdefault(root(node), {"pixels": [], "baselines": []})
        (group["pixels"] if node < pixels else group["baselines"]).append(node if node < pixels else node - pixels)
    return sorted(groups.values(), key=lambda group: (group["pixels"] or [pixels], group["baselines"]))


def read(document) -> Timestream:
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise InputError(f"not a {FORMAT} document")
    if set(document) != KEYS:
        raise InputError(f"{FORMAT} has exactly the keys {sorted(KEYS)}; missing {sorted(KEYS - set(document))}, "
                         f"unknown {sorted(set(document) - KEYS)}")
    if document["role"] != "reconstruction-input":
        raise InputError("the timestream's role is reconstruction-input")
    pixels, length, pixel, value = document["pixels"], document["baseline_length"], document["pixel"], document["value"]
    for name, number in (("pixels", pixels), ("baseline_length", length)):
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise InputError(f"{name} is a positive integer")
    if not isinstance(pixel, list) or not isinstance(value, list) or len(pixel) != len(value) or not pixel:
        raise InputError("pixel and value are lists of one length, not empty")
    if len(pixel) % length:
        raise InputError(f"{len(pixel)} samples are not a whole number of baselines of {length}")
    for t, p in enumerate(pixel):
        if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p < pixels:
            raise InputError(f"sample {t}: pixel {p!r} is not an integer in [0, {pixels})")
    for t, y in enumerate(value):
        if not isinstance(y, (int, float)) or isinstance(y, bool) or not math.isfinite(y):
            raise InputError(f"sample {t}: value {y!r} is not a finite number")
    for name in ("unit", "noise_premise"):
        if not isinstance(document[name], str) or not document[name]:
            raise InputError(f"{name} is a non-empty string")
    hits = numpy.bincount(pixel, minlength=pixels)
    unseen = [int(p) for p in numpy.flatnonzero(hits == 0)]
    if unseen:
        raise Refusal(f"pixel {unseen[0]} is never observed ({len(unseen)} such): its map value is not determined by the data")
    parts = _components(pixel, length, pixels)
    if len(parts) > 1:
        raise Refusal(f"the scan has {len(parts)} connected components, so {len(parts)} offset null modes; the one zero-sum constraint "
                      f"fixes one, and {len(parts) - 1} null mode(s) remain (the offset of one component's map against another's)",
                      components=parts)
    return Timestream(numpy.array(pixel, dtype=int), numpy.array(value, dtype=float), pixels, length, document["unit"],
                      document["noise_premise"])
