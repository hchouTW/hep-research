"""The response pipeline of g4sim (plan, Section 10): scintillation photons, their distribution among channels, sensor and electronics, in a fixed order of draws.

Sub-streams of response-pipeline/1. Each row is fixed, and the output of a draw depends only on its sub-stream and the draws before it there:

| Draw | Stream, stage | Identity | Sub-index | Order within the sub-stream |
| --- | --- | --- | --- | --- |
| Gamma yield factor | volume, stage `yield_variation` | volume ID | 0 | one draw per event and scintillating volume |
| Photon number N_b, then its multinomial | volume, the stage's name | volume ID | segmentation bin | N_b, then the conditional binomials in channel order |
| Photon time, per detected photon | volume, `<stage>/time/<block>` | volume ID | segmentation bin | emission delay, then transit time, from one output group per photon |
| Noise, gain, dark counts | channel, the stage's name | cellID | 0 | as the stage lists them |

A bin can hold more detected photons than one sub-stream's 2^16 output groups, so times use blocks of 2^15 photons, each block its own stage name and so its own key. Keys stay few: one per block in use.
A sub-stream of N_b and C channels makes at most C + 1 draws, each a rejection sampler at worst; see `exhaustion_bound`.

Charge sharing is a declared, hashed table: `allpix.pixel-charge` cannot supply one (maintainer's decision, g4sim-approvals.md). Pure computation: files are read by the caller.
"""
from __future__ import annotations

import math

from core.simulation import rng

SCHEMA = "response-pipeline/1"
HANDOFF_SCHEMA = "response-handoff/1"
POISSON_LIMIT = 10.0
ROUNDING_VARIANCE = 1.0 / 12.0
PHOTON_BLOCK = 2 ** 15
YIELD_STAGE = "yield_variation"
MINIMUM_ACCEPTANCE = 0.5  # a lower bound on the acceptance of PTRS and BTPE, per attempt


class ResponseError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def check_pipeline(document: dict) -> None:
    """Every parameter carries a source_of_facts, and stage names are unique: Section 10.1 refuses to run otherwise."""
    names = [stage["name"] for stage in document["stages"]]
    if len(set(names)) != len(names):
        raise ResponseError("stage-name", "two stages share a name")
    for stage in document["stages"]:
        for key, parameter in stage["parameters"].items():
            if not isinstance(parameter, dict) or not parameter.get("source_of_facts"):
                raise ResponseError("source-of-facts", f"stage {stage['name']}: {key} has no source_of_facts")


def study_keys(document: dict, readouts: list) -> list:
    """All keys of a pipeline; the response checks refuse a study where two coincide (Section 10.2)."""
    seed, replica = document["run_seed"], document["replica"]
    keys = [rng.volume_key(seed, stage["name"], replica) for stage in document["stages"]]
    keys += [rng.channel_key(seed, readout, stage["name"], replica) for readout in readouts for stage in document["stages"]]
    repeated = rng.distinct_keys(keys)
    if repeated:
        raise ResponseError("key-collision", f"{len(repeated)} keys coincide")
    return keys


def exhaustion_bound(draws: int) -> float:
    """An upper bound on P(a sub-stream needs more than 2^16 output groups) for `draws` rejection draws of acceptance at least 1/2, each attempt two groups at most: Chernoff on the failures."""
    groups = rng.GROUPS_PER_SUB_STREAM // 2
    if draws >= groups * MINIMUM_ACCEPTANCE:
        return 1.0
    ratio = draws / (groups * MINIMUM_ACCEPTANCE)
    log_bound = groups * MINIMUM_ACCEPTANCE * (1.0 - ratio + ratio * math.log(ratio))
    return math.exp(-log_bound)


def photon_moments(light_yield: float, resolution_scale: float, large: float, small: float, large_steps: int) -> tuple:
    """Section 10.3: the mean and variance of a bin. `large` and `small` are E^L and E^S, `large_steps` is n^L."""
    mean = light_yield * (large + small)
    return mean, resolution_scale ** 2 * light_yield * large + light_yield * small + large_steps * ROUNDING_VARIANCE


def bin_photons(stream: rng.SubStream, light_yield: float, resolution_scale: float, large: float, small: float, large_steps: int, factor: float = 1.0) -> int:
    """N_b of Section 10.3, with the optional yield factor multiplied into the mean."""
    mean, variance = photon_moments(light_yield, resolution_scale, large, small, large_steps)
    mean *= factor
    if mean <= POISSON_LIMIT:
        return stream.poisson(mean)
    width = math.sqrt(max(variance * factor - ROUNDING_VARIANCE, 0.0))  # the rounding below adds 1/12 again
    return max(int(math.floor(stream.gaussian(mean, width) + 0.5)), 0)


def yield_factor(document: dict, event: int, volume_id: int, relative_width: float) -> float:
    """The Gamma factor of mean 1, once per event and scintillating volume, off in any comparison with Geant4."""
    if relative_width <= 0:
        return 1.0
    shape = 1.0 / relative_width ** 2
    key = rng.volume_key(document["run_seed"], YIELD_STAGE, document["replica"])
    return rng.SubStream(key, event, volume_id).gamma(shape) / shape


def efficiencies(map_document: dict, bin_index: int) -> list:
    """epsilon_c(x_b) of an analytic efficiency-map/1."""
    form = map_document["form"]
    count = len(map_document["channels"])
    values = list(form["value"]) if form["kind"] == "uniform" else [a + b * bin_index for a, b in zip(form["intercept"], form["slope_per_bin"])]
    if len(values) != count or any(value < 0 for value in values) or math.fsum(values) > 1.0:
        raise ResponseError("efficiency-map", f"efficiencies {values} in bin {bin_index}")
    return values


def scintillation_event(document: dict, stage: dict, event: int, volume_id: int, bins: dict, map_document: dict, factor: float = 1.0) -> dict:
    """Photoelectrons per channel of one volume in one event. `bins` is {bin: (E^L, E^S, n^L)}; each bin has its own sub-stream, so the order of the bins does not matter."""
    parameters = stage["parameters"]
    light_yield, scale = parameters["light_yield_per_MeV"]["value"], parameters["resolution_scale"]["value"]
    key = rng.volume_key(document["run_seed"], stage["name"], document["replica"])
    channels = {name: 0 for name in map_document["channels"]}
    for bin_index, (large, small, steps) in bins.items():
        stream = rng.SubStream(key, event, volume_id, bin_index)
        photons = bin_photons(stream, light_yield, scale, large, small, steps, factor)
        for name, count in zip(map_document["channels"], stream.multinomial(photons, efficiencies(map_document, bin_index))):
            channels[name] += count
    return channels


def photon_times(document: dict, stage_name: str, event: int, volume_id: int, bin_index: int, photons: int, decay_ns: float, transit_ns: float) -> list:
    """A time per detected photon: an exponential delay and an exponential transit, from one output group each, in blocks of 2^15 photons."""
    times = []
    for start in range(0, photons, PHOTON_BLOCK):
        key = rng.volume_key(document["run_seed"], f"{stage_name}/time/{start // PHOTON_BLOCK}", document["replica"])
        stream = rng.SubStream(key, event, volume_id, bin_index)
        for _ in range(min(PHOTON_BLOCK, photons - start)):
            first, second = stream.group()
            times.append(-decay_ns * math.log(first) - transit_ns * math.log(second))
    return times


def ionisation_quanta(stream: rng.SubStream, deposit_ev: float, w_value_ev: float, fano: float) -> int:
    """Carriers from a deposit: mean E / W, variance F E / W, with Poisson at small means, as for photons."""
    mean = deposit_ev / w_value_ev
    if mean <= POISSON_LIMIT:
        return stream.poisson(mean)
    return max(int(math.floor(stream.gaussian(mean, math.sqrt(fano * mean)) + 0.5)), 0)


def share_charge(charge: float, offsets: list) -> dict:
    """Charge sharing from a declared table: {neighbour offset: fraction}, whose fractions sum to one; deterministic, so it draws nothing."""
    total = math.fsum(row["fraction"] for row in offsets)
    if abs(total - 1.0) > 1e-12:
        raise ResponseError("charge-table", f"fractions sum to {total}")
    return {row["offset"]: charge * row["fraction"] for row in offsets}


def sensor_response(stream: rng.SubStream, photoelectrons: int, gain: float, excess_noise: float, dark_rate_per_ns: float, gate_ns: float) -> float:
    """Dark counts first, then the gain with its excess noise, in that fixed order."""
    total = photoelectrons + stream.poisson(dark_rate_per_ns * gate_ns)
    return max(stream.gaussian(total * gain, excess_noise * gain * math.sqrt(total)), 0.0) if total else 0.0


def electronics_response(stream: rng.SubStream, charge: float, noise_sigma: float, threshold: float, lsb: float, bits: int) -> int | None:
    """Noise, then the threshold, then the ADC. None below threshold. This is the normative stage 4; the FE series connects through the stage hand-off file instead."""
    signal = stream.gaussian(charge, noise_sigma)
    if signal < threshold:
        return None
    return min(int(signal / lsb), 2 ** bits - 1)


def handoff(stage_from: str, stage_to: str, event_rows: list) -> dict:
    """The file between stages 3 and 4 or 4 and 5, so that core imports neither the FE series nor simreco-strip."""
    return {"schema": HANDOFF_SCHEMA, "from": stage_from, "to": stage_to, "rows": event_rows}


def read_handoff(document: dict, stage_to: str) -> list:
    if document.get("schema") != HANDOFF_SCHEMA or document.get("to") != stage_to:
        raise ResponseError("handoff-form", f"not a hand-off to {stage_to}")
    return document["rows"]
