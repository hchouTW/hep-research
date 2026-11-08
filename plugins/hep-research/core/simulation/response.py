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

import hashlib
import math

from core.simulation import efficiency_map, rng

SCHEMA = "response-pipeline/1"
HANDOFF_SCHEMA = "response-handoff/1"
DRIFT_TABLE_FORMAT = "garfield-gas-table-query-output/1"
TABLE_STAGES = ("charge_sharing", "drift_table")  # stages whose numbers live in a declared, hashed file
POISSON_LIMIT = 10.0
ROUNDING_VARIANCE = 1.0 / 12.0
PHOTON_BLOCK = 2 ** 15
YIELD_STAGE = "yield_variation"
EXTERNAL_STAGES = {"electronics_external": "fe4", "readout_external": "simreco-strip"}  # programs core does not import; each is reached through the hand-off file
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
        if stage["kind"] in TABLE_STAGES and "table" not in stage:
            raise ResponseError("table-reference", f"stage {stage['name']} declares no table")
        if stage["kind"] == "drift_table" and "detsim_run_id" not in stage.get("table", {}):
            raise ResponseError("table-reference", f"stage {stage['name']}: a drift table is referenced by its detsim run_id")
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


def efficiencies(map_document: dict, bin_index: int, replica: int = 0) -> list:
    """epsilon_c(x_b) of an efficiency-map/1: analytic (S4), or mapped (S7), where the pipeline's replica r > 0 takes the map's Dirichlet replica r."""
    form = map_document["form"]
    if form["kind"] == efficiency_map.FORM:
        try:
            return efficiency_map.efficiencies(map_document, bin_index, replica)
        except efficiency_map.MapError as err:
            raise ResponseError("efficiency-map", str(err)) from err
    count = len(map_document["channels"])
    values = list(form["value"]) if form["kind"] == "uniform" else [a + b * bin_index for a, b in zip(form["intercept"], form["slope_per_bin"])]
    if len(values) != count or any(value < 0 for value in values) or math.fsum(values) > 1.0:
        raise ResponseError("efficiency-map", f"efficiencies {values} in bin {bin_index}")
    return values


def scintillation_event(document: dict, stage: dict, event: int, volume_id: int, bins: dict, map_document: dict, factor: float = 1.0, map_replica: int | None = None) -> dict:
    """Photoelectrons per channel of one volume in one event. `bins` is {bin: (E^L, E^S, n^L)}; each bin has its own sub-stream, so the order of the bins does not matter.
    A mapped map takes the pipeline's replica unless `map_replica` names another (S7: a test of the map alone holds the photon streams fixed)."""
    parameters = stage["parameters"]
    light_yield, scale = parameters["light_yield_per_MeV"]["value"], parameters["resolution_scale"]["value"]
    key = rng.volume_key(document["run_seed"], stage["name"], document["replica"])
    channels = {name: 0 for name in map_document["channels"]}
    for bin_index, (large, small, steps) in bins.items():
        stream = rng.SubStream(key, event, volume_id, bin_index)
        photons = bin_photons(stream, light_yield, scale, large, small, steps, factor)
        for name, count in zip(map_document["channels"], stream.multinomial(photons, efficiencies(map_document, bin_index, document["replica"] if map_replica is None else map_replica))):
            channels[name] += count
    return channels


def photon_times(document: dict, stage_name: str, event: int, volume_id: int, bin_index: int, photons: int, decay_ns: float, transit_ns: float,
                 map_document: dict | None = None, rise_ns: float = 0.0) -> list:
    """A time per detected photon, emission delay plus transit, from one output group each, in blocks of 2^15 photons. The transit is
    exponential, or with a mapped map drawn from the bin's arrival-time distribution (S7); a component with a rise time adds an exponential
    rise from a second group, so the delay is the convolution of rise and decay (Section 10.4)."""
    mapped = map_document is not None and map_document["form"]["kind"] == efficiency_map.FORM
    times = []
    for start in range(0, photons, PHOTON_BLOCK):
        key = rng.volume_key(document["run_seed"], f"{stage_name}/time/{start // PHOTON_BLOCK}", document["replica"])
        stream = rng.SubStream(key, event, volume_id, bin_index)
        for _ in range(min(PHOTON_BLOCK, photons - start)):
            first, second = stream.group()
            delay = -decay_ns * math.log(first) - (rise_ns * math.log(stream.group()[0]) if rise_ns > 0 else 0.0)
            transit = efficiency_map.transit_ns(map_document, bin_index, second) if mapped else -transit_ns * math.log(second)
            times.append(delay + transit)
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


def verify_table(stage: dict, content: bytes) -> bytes:
    """The bytes of a stage's table, refused unless they are the ones the pipeline declared."""
    found = hashlib.sha256(content).hexdigest()
    if found != stage["table"]["sha256"]:
        raise ResponseError("table-hash", f"stage {stage['name']}: the table hashes to {found}")
    return content


def drift_points(content: bytes) -> list:
    """(field in V/cm, drift speed in cm/ns) of a complete Garfield++ gas-table query output, in rising field."""
    lines = content.decode("ascii").splitlines()
    if not lines or lines[0].split() != ["format", DRIFT_TABLE_FORMAT]:
        raise ResponseError("drift-table", f"not a {DRIFT_TABLE_FORMAT} file")
    points = [(float(words[2]), float(words[6])) for words in map(str.split, lines) if words[0] == "point"]
    if lines[-1].split() != ["end", str(len(points))] or not points:
        raise ResponseError("drift-table", "the table is incomplete")
    return sorted(points)


def drift_speed(points: list, field: float) -> float:
    """Linear between the table's points; outside them the query made no statement, so it is refused rather than extrapolated."""
    if not points[0][0] <= field <= points[-1][0]:
        raise ResponseError("drift-range", f"field {field} V/cm is outside the table, {points[0][0]} to {points[-1][0]}")
    above = next(at for at, point in enumerate(points) if point[0] >= field)
    if points[above][0] == field:
        return points[above][1]
    (low_field, low_speed), (high_field, high_speed) = points[above - 1], points[above]
    return low_speed + (high_speed - low_speed) * (field - low_field) / (high_field - low_field)


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


def external_program(stage: dict) -> str:
    """The registered program of a stage that runs outside core."""
    if stage["kind"] not in EXTERNAL_STAGES:
        raise ResponseError("stage-kind", f"stage {stage['name']} runs in core")
    return EXTERNAL_STAGES[stage["kind"]]


def read_handoff(document: dict, stage_to: str) -> list:
    if document.get("schema") != HANDOFF_SCHEMA or document.get("to") != stage_to:
        raise ResponseError("handoff-form", f"not a hand-off to {stage_to}")
    keys = [(row["event"], row["cell"]) for row in document["rows"]]
    if len(set(keys)) != len(keys):
        raise ResponseError("handoff-rows", "two rows share an event and a cell, so they would share their draws: a channel stream has sub-index 0 (Section 10.2)")
    return document["rows"]
