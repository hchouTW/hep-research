"""Mapped light-collection efficiency maps (g4sim plan, Section 10.4, S7): built from a mapping run, read by the digitization of Section 10.3.

A mapping run emits optical photons of one scintillation component, uniformly over a template's volume and isotropically, with optical
physics on; photon_detected counts them per detecting volume. Each emitted photon falls in the bin of the production segmentation that
holds its emission point, so a bin holds n emitted photons, k_c detected in each channel c, and the transit times of the detected ones.

- Nominal efficiencies are k_c / n. A replica r >= 1 draws the bin's vector (eps_1, ..., eps_C, not detected) from Dirichlet(k_1 + 1/2, ...,
  k_C + 1/2, n - sum k + 1/2), the Jeffreys posterior, which keeps the channels' negative correlation and gives k = 0 and k = n a variance.
  Replica draws depend on the map's hash, the replica and the bin only, so a replica is the same systematic variation in every run.
- With only along_axis segmentation, a bin's transverse sub-cells must agree (the transverse-uniformity check): a chi-square test of
  homogeneity of the detected fraction across the sub-cells, each bin at alpha / B (Bonferroni over the B bins), every expected count >= 5.
- Bins follow the C++ Grid of NewScorers.hh for a box: count = max(1, ceil(2h / w - 1e-9)) per segmented axis, index clamped to the grid.

Gamma variates of shape below 1 use Marsaglia and Tsang's boost, Gamma(a) = Gamma(a + 1) U^(1/a) (ACM TOMS 26 (2000) 363, Section 4)."""
from __future__ import annotations

import hashlib
import math

from core.canonical import canonical_json
from core.simulation import rng

SCHEMA = "efficiency-map/1"
FORM = "mapped"
MINIMUM_REPLICAS = 100
UNIFORMITY_ALPHA = 0.01
MINIMUM_EXPECTED = 5.0
TRANSIT_BINS = 50
_COUNT_SLACK = 1e-9  # Grid's own slack, so a box of exactly n widths has n bins


class MapError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def bin_counts(segmentation: dict, half_mm: list) -> list[int]:
    """The bins of each local axis of a box, as Grid counts them."""
    widths = axis_widths(segmentation)
    return [max(1, math.ceil(2.0 * half / width - _COUNT_SLACK)) if width > 0 else 1 for half, width in zip(half_mm, widths)]


def axis_widths(segmentation: dict) -> list[float]:
    kind = segmentation["kind"]
    width = [float(value) for value in segmentation.get("width_mm", [])]
    if kind == "none":
        return [0.0, 0.0, 0.0]
    if kind == "along_axis":
        return [width[0] if axis == segmentation["axis"] else 0.0 for axis in range(3)]
    if kind == "cartesian_xy":
        return [width[0], width[1], 0.0]
    if kind == "cartesian_xyz":
        return width[:3]
    raise MapError("map-segmentation", f"a mapped efficiency map takes none, along_axis or cartesian segmentation, not {kind}")


def bin_of(segmentation: dict, half_mm: list, local: list) -> int:
    """Grid::Bin of NewScorers.hh for a box whose bounding limits are [-h, h]."""
    widths, counts = axis_widths(segmentation), bin_counts(segmentation, half_mm)
    index = [min(max(int(math.floor((point + half) / width)), 0), count - 1) if width > 0 else 0
             for point, half, width, count in zip(local, half_mm, widths, counts)]
    return index[0] + counts[0] * (index[1] + counts[1] * index[2])


def sub_cell(segmentation: dict, half_mm: list, local: list, side: int) -> int:
    """The transverse sub-cell of a point, on a side x side grid across the two axes along_axis leaves unsegmented."""
    across = [axis for axis in range(3) if axis != segmentation["axis"]]
    index = [min(max(int(math.floor((local[axis] + half_mm[axis]) / (2.0 * half_mm[axis]) * side)), 0), side - 1) for axis in across]
    return index[0] + side * index[1]


def build(*, template: str, component: int, spectrum: dict, segmentation: dict, half_mm: list, channels: list, emitted: dict, detected: list,
          hashes: dict, transverse_side: int = 3) -> dict:
    """The map of one component. `emitted` is {event: local emission point}; `detected` is [(event, channel, transit_ns)]."""
    widths = axis_widths(segmentation)
    if segmentation["kind"] != "none" and not any(widths):
        raise MapError("map-segmentation", "the segmentation has no width")
    total = math.prod(bin_counts(segmentation, half_mm))
    index = {name: at for at, name in enumerate(channels)}
    bins = {b: {"emitted": 0, "detected": [0] * len(channels), "times": []} for b in range(total)}
    cells = {} if segmentation["kind"] == "along_axis" else None
    for local in emitted.values():
        b = bin_of(segmentation, half_mm, local)
        bins[b]["emitted"] += 1
        if cells is not None:
            cell = cells.setdefault((b, sub_cell(segmentation, half_mm, local, transverse_side)), [0, 0])
            cell[0] += 1
    longest = max((transit for _, _, transit in detected), default=1.0)
    edges = [longest * (1.0 + 1e-9) * i / TRANSIT_BINS for i in range(TRANSIT_BINS + 1)]
    seen = set()
    for event, channel, transit in detected:
        if event not in emitted:
            raise MapError("map-input", f"a detection in event {event}, which emitted no photon")
        if event in seen:
            raise MapError("map-input", f"event {event} has two detections; a mapping run emits one photon per event")
        if channel not in index:
            raise MapError("map-input", f"channel {channel!r} is not among {channels}")
        seen.add(event)
        b = bin_of(segmentation, half_mm, emitted[event])
        bins[b]["detected"][index[channel]] += 1
        bins[b]["times"].append(transit)
        if cells is not None:
            cells[(b, sub_cell(segmentation, half_mm, emitted[event], transverse_side))][1] += 1
    rows = []
    for b in range(total):
        entry = bins[b]
        if entry["emitted"] == 0:
            raise MapError("map-coverage", f"bin {b} emitted no photon; the mapping run needs more photons")
        counts = [0] * TRANSIT_BINS
        for transit in entry["times"]:
            counts[min(int(transit / edges[-1] * TRANSIT_BINS), TRANSIT_BINS - 1)] += 1
        rows.append({"bin": b, "emitted": entry["emitted"], "detected": entry["detected"], "transit_counts": counts})
    document = {"schema": SCHEMA, "channels": list(channels), "form": {
        "kind": FORM, "template": template, "component": component, "emission_spectrum": spectrum, "segmentation": segmentation,
        "half_mm": [float(value) for value in half_mm], "transit_edges_ns": edges, "bins": rows, "hashes": hashes}}
    if cells is not None:
        document["form"]["transverse"] = {"side": transverse_side, "cells": [{"bin": b, "cell": c, "emitted": n, "detected": k} for (b, c), (n, k) in sorted(cells.items())]}
    return document


def map_sha256(document: dict) -> str:
    return hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def _row(document: dict, bin_index: int) -> dict:
    rows = document["form"]["bins"]
    if not 0 <= bin_index < len(rows) or rows[bin_index]["bin"] != bin_index:
        raise MapError("map-bin", f"bin {bin_index} is not in the map")
    return rows[bin_index]


def _gamma(stream: rng.SubStream, shape: float) -> float:
    if shape >= 1.0:
        return stream.gamma(shape)
    boosted = stream.gamma(shape + 1.0)
    return boosted * stream.group()[0] ** (1.0 / shape)


def efficiencies(document: dict, bin_index: int, replica: int = 0) -> list[float]:
    """eps_c of a bin: nominal (replica 0) or one Dirichlet replica."""
    row = _row(document, bin_index)
    detected, emitted = row["detected"], row["emitted"]
    if replica == 0:
        return [k / emitted for k in detected]
    seed = int(map_sha256(document)[:15], 16)
    stream = rng.SubStream(rng.volume_key(seed, f"efficiency_map/{document['form']['component']}", replica), 0, bin_index)
    draws = [_gamma(stream, k + 0.5) for k in detected] + [_gamma(stream, emitted - sum(detected) + 0.5)]
    total = math.fsum(draws)
    return [value / total for value in draws[:-1]]


def transit_ns(document: dict, bin_index: int, uniform: float) -> float:
    """A transit time from the bin's arrival-time distribution: the inverse of its piecewise-uniform distribution function."""
    row = _row(document, bin_index)
    counts, edges = row["transit_counts"], document["form"]["transit_edges_ns"]
    total = sum(counts)
    if total == 0:
        raise MapError("map-transit", f"bin {bin_index} detected no photon, so it has no transit time")
    target, running = uniform * total, 0.0
    for at, count in enumerate(counts):
        if count and running + count >= target:
            return edges[at] + (target - running) / count * (edges[at + 1] - edges[at])
        running += count
    return edges[-1]


def _chi_square_survival(statistic: float, dof: int) -> float:
    """Q(dof / 2, statistic / 2), the regularized upper incomplete gamma function: a series below a + 1, Lentz's continued fraction above."""
    if statistic <= 0:
        return 1.0
    a, x = dof / 2.0, statistic / 2.0
    prefix = math.exp(-x + a * math.log(x) - math.lgamma(a))
    if x < a + 1.0:
        term = total = 1.0 / a
        n = a
        while abs(term) > abs(total) * 1e-15:
            n += 1.0
            term *= x / n
            total += term
        return max(0.0, 1.0 - prefix * total)
    tiny = 1e-300
    b, c, d = x + 1.0 - a, 1.0 / tiny, 1.0 / (x + 1.0 - a)
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return prefix * h


def transverse_uniformity(document: dict, alpha: float = UNIFORMITY_ALPHA) -> dict:
    """The check of an along_axis map: per bin, the detected fraction homogeneous across its transverse sub-cells."""
    form = document["form"]
    if form["segmentation"]["kind"] != "along_axis":
        return {"status": "not-needed"}
    by_bin: dict = {}
    for cell in form["transverse"]["cells"]:
        by_bin.setdefault(cell["bin"], []).append(cell)
    level = alpha / len(form["bins"])
    results, failing, short = [], [], []
    for b, cells in sorted(by_bin.items()):
        emitted, detected = sum(cell["emitted"] for cell in cells), sum(cell["detected"] for cell in cells)
        fraction = detected / emitted
        expected = [(cell["emitted"] * fraction, cell["emitted"] * (1.0 - fraction)) for cell in cells]
        if len(cells) < form["transverse"]["side"] ** 2 or min(min(pair) for pair in expected) < MINIMUM_EXPECTED:
            short.append(b)
            continue
        statistic = math.fsum((cell["detected"] - hit) ** 2 / hit + (cell["emitted"] - cell["detected"] - miss) ** 2 / miss
                              for cell, (hit, miss) in zip(cells, expected))
        p_value = _chi_square_survival(statistic, len(cells) - 1)
        results.append({"bin": b, "chi_square": statistic, "dof": len(cells) - 1, "p_value": p_value})
        if p_value < level:
            failing.append(b)
    status = "failed" if failing else "insufficient" if short else "passed"
    return {"status": status, "level_per_bin": level, "failing_bins": failing, "bins_short_of_photons": short, "bins": results}


def replicas(document: dict, count: int = MINIMUM_REPLICAS) -> list[int]:
    """The replica numbers a response study uses: at least 100 (Section 10.4)."""
    if count < MINIMUM_REPLICAS:
        raise MapError("map-replicas", f"{count} replicas; Section 10.4 asks at least {MINIMUM_REPLICAS}")
    return list(range(1, count + 1))


def _finding(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _same_spectrum(first: dict, second: dict) -> bool:
    return [float(value) for value in first["energy_eV"]] == [float(value) for value in second["energy_eV"]] and \
        [float(value) for value in first["value"]] == [float(value) for value in second["value"]]


def component_findings(material: dict, maps: dict, materials_sha256: str | None = None) -> list:
    """Response checks of Section 10.4: every scintillation component has a map; components share one map only when the material's spectral
    tables say they emit the same spectrum; a map holds its component's spectrum, and the materials the run uses (by hash). `maps` is
    {component: map document}."""
    components = material.get("scintillation", {}).get("components") or []
    findings = [_finding("map-missing", f"component {number} has no efficiency map") for number in range(1, len(components) + 1) if number not in maps]
    by_map: dict = {}
    for number, document in maps.items():
        if not 1 <= number <= len(components):
            findings.append(_finding("map-component", f"a map for component {number}, which the material does not have"))
            continue
        by_map.setdefault(map_sha256(document), []).append(number)
        if not _same_spectrum(document["form"]["emission_spectrum"], components[number - 1]["spectrum"]):
            findings.append(_finding("map-spectrum", f"the map of component {number} was made with another emission spectrum"))
        if materials_sha256 is not None and document["form"]["hashes"]["materials_sha256"] != materials_sha256:
            findings.append(_finding("map-stale", f"the map of component {number} was made with other materials than this run's"))
    for numbers in by_map.values():
        for number in numbers[1:]:
            if not _same_spectrum(components[numbers[0] - 1]["spectrum"], components[number - 1]["spectrum"]):
                findings.append(_finding("map-shared", f"components {numbers[0]} and {number} share one map but emit different spectra"))
    return findings


def validation_response_findings(stage: dict, material: dict) -> list:
    """Response checks of a validation run (Section 10.4): the digitization's LY is the material's nominal LY, the extra yield variation is off
    (the scintillation stage's yield_relative_width, which response.yield_factor takes, absent or 0), and the material has a single
    scintillation component (the multi-component difference is a known model difference)."""
    findings = []
    nominal = float(material["scintillation"]["yield_per_MeV"])
    if float(stage["parameters"]["light_yield_per_MeV"]["value"]) != nominal:
        findings.append(_finding("validation-yield", f"the digitization's LY {stage['parameters']['light_yield_per_MeV']['value']} is not the nominal {nominal}"))
    if float(stage["parameters"].get("yield_relative_width", {}).get("value", 0)) > 0:
        findings.append(_finding("validation-yield-variation", "the extra yield variation is on"))
    if len(material["scintillation"].get("components") or []) != 1:
        findings.append(_finding("validation-components", "a validation run uses a material with a single scintillation component"))
    return findings
