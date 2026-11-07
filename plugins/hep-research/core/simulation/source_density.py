"""source-density/1 (g4sim plan, Section 6.3; GL5): the analytic density of a source, so that calibration can use it as the R layer.

`density(source)` validates the distributions' parameters and returns a record of what was sampled; `energy_density` evaluates it. A distribution
with a discrete support reports probabilities. Pure computation, no Geant4.
"""
from __future__ import annotations

import math

SCHEMA = "source-density/1"
ENERGY_KINDS = ("mono", "uniform", "log_uniform", "power_law", "gaussian", "list", "cycle")
POSITION_KINDS = ("point", "box_uniform", "disk_uniform", "gaussian_spot", "sphere_surface")
DIRECTION_KINDS = ("fixed", "cone", "from_point", "isotropic", "cosine_law")


class SourceError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _only(block: dict, kinds: tuple, part: str) -> tuple:
    if not isinstance(block, dict) or len(block) != 1 or next(iter(block)) not in kinds:
        raise SourceError("source-kind", f"{part} is one of {kinds}, not {block!r}")
    return next(iter(block.items()))


def _positive(value, name: str) -> float:
    number = float(value)
    if not number > 0 or math.isinf(number):
        raise SourceError("source-parameter", f"{name} {value!r} is not positive")
    return number


def _range(body: dict) -> tuple:
    low, high = _positive(body["min_MeV"], "min_MeV"), _positive(body["max_MeV"], "max_MeV")
    if low >= high:
        raise SourceError("source-parameter", f"min_MeV {low} is not below max_MeV {high}")
    return low, high


def _normal_cdf(value: float) -> float:
    return 0.5 * math.erfc(-value / math.sqrt(2))


def _energy(kind: str, body: dict) -> dict:
    if kind == "mono":
        return {"kind": kind, "support": "discrete", "energies_MeV": [_positive(body["energy_MeV"], "energy_MeV")], "probabilities": [1.0]}
    if kind in ("uniform", "log_uniform"):
        low, high = _range(body)
        return {"kind": kind, "support": "continuous", "min_MeV": low, "max_MeV": high}
    if kind == "power_law":
        low, high = _range(body)
        return {"kind": kind, "support": "continuous", "min_MeV": low, "max_MeV": high, "index": float(body["index"])}
    if kind == "gaussian":
        mean = _positive(body["mean_MeV"], "mean_MeV")
        sigma = _positive(body["sigma_MeV"], "sigma_MeV") if "sigma_MeV" in body else mean * _positive(body["rel_sigma"], "rel_sigma")
        if "truncate_MeV" not in body:
            raise SourceError("source-parameter", "a gaussian declares its truncation")
        low, high = body["truncate_MeV"]
        low, high = float(low), math.inf if high is None else float(high)
        if low >= high:
            raise SourceError("source-parameter", f"truncation {low} to {high} is empty")
        mass = _normal_cdf((high - mean) / sigma) - _normal_cdf((low - mean) / sigma)
        if mass <= 0:
            raise SourceError("source-parameter", "the truncation holds no probability")
        return {"kind": kind, "support": "continuous", "mean_MeV": mean, "sigma_MeV": sigma, "low_MeV": low, "high_MeV": None if math.isinf(high) else high, "mass": mass}
    energies = [_positive(value, "energy") for value in body["energies_MeV"]]
    if not energies:
        raise SourceError("source-parameter", "the list is empty")
    weights = [1.0] * len(energies) if kind == "cycle" else [_positive(value, "weight") for value in body.get("weights", [1.0] * len(energies))]
    if len(weights) != len(energies):
        raise SourceError("source-parameter", f"{len(weights)} weights for {len(energies)} energies")
    total = math.fsum(weights)
    return {"kind": kind, "support": "discrete", "energies_MeV": energies, "probabilities": [weight / total for weight in weights]}


def _position(kind: str, body: dict) -> dict:
    if "frame" not in body:
        raise SourceError("source-frame", "a position states its frame")
    record = {"kind": kind, "frame": body["frame"], "centre_mm": [float(value) for value in body["centre_mm"]]}
    if kind == "box_uniform":
        record["size_mm"] = [float(value) for value in body["size_mm"]]
        if any(value < 0 for value in record["size_mm"]) or not any(record["size_mm"]):
            raise SourceError("source-parameter", f"box size {body['size_mm']!r}")
    elif kind in ("disk_uniform", "sphere_surface"):
        record["radius_mm"] = _positive(body["radius_mm"], "radius_mm")
    elif kind == "gaussian_spot":
        record["sigma_mm"] = [_positive(value, "sigma_mm") for value in body["sigma_mm"]]
    return record


def _unit(vector) -> list:
    values = [float(value) for value in vector]
    norm = math.sqrt(math.fsum(value * value for value in values))
    if len(values) != 3 or norm == 0:
        raise SourceError("source-parameter", f"direction {vector!r}")
    return [value / norm for value in values]


def _direction(kind: str, body: dict) -> dict:
    if kind != "isotropic" and "frame" not in body:
        raise SourceError("source-frame", "a direction states its frame")
    record = {"kind": kind, "frame": body.get("frame", "world")}
    if kind == "fixed":
        record["vector"] = _unit(body["vector"])
    elif kind == "cone":
        record["axis"] = _unit(body["axis"])
        record["half_angle_deg"] = _positive(body["half_angle_deg"], "half_angle_deg")
        if record["half_angle_deg"] > 180:
            raise SourceError("source-parameter", "a cone's half angle exceeds 180 degrees")
    elif kind == "from_point":
        record["point_mm"] = [float(value) for value in body["point_mm"]]
    elif kind == "cosine_law":
        record["axis"] = _unit(body["axis"])
    return record


def density(source: dict) -> dict:
    """The record of an `analytic` source; raises SourceError on a wrong distribution or parameter."""
    if source.get("density") != "analytic":
        raise SourceError("source-density", "only an analytic source has a density")
    return {"schema": SCHEMA, "particle": source["particle"], "energy": _energy(*_only(source["energy"], ENERGY_KINDS, "energy")),
            "position": _position(*_only(source["position"], POSITION_KINDS, "position")), "direction": _direction(*_only(source["direction"], DIRECTION_KINDS, "direction"))}


def energy_density(record: dict, energy_mev: float) -> float:
    """The probability density at an energy, per MeV; for a discrete support, the probability of that energy."""
    block = record["energy"]
    kind = block["kind"]
    if block["support"] == "discrete":
        return math.fsum(p for value, p in zip(block["energies_MeV"], block["probabilities"]) if value == energy_mev)
    if kind == "gaussian":
        low, high = block["low_MeV"], math.inf if block["high_MeV"] is None else block["high_MeV"]
        if not low <= energy_mev <= high:
            return 0.0
        z = (energy_mev - block["mean_MeV"]) / block["sigma_MeV"]
        return math.exp(-z * z / 2) / (block["sigma_MeV"] * math.sqrt(2 * math.pi) * block["mass"])
    low, high = block["min_MeV"], block["max_MeV"]
    if not low <= energy_mev <= high:
        return 0.0
    if kind == "uniform":
        return 1 / (high - low)
    if kind == "log_uniform":
        return 1 / (energy_mev * math.log(high / low))
    index = block["index"]  # density proportional to E^-index
    norm = math.log(high / low) if index == 1 else (high ** (1 - index) - low ** (1 - index)) / (1 - index)
    return energy_mev ** -index / norm
