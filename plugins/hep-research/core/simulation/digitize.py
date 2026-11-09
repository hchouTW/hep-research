"""The digitization of scintillation bins (g4sim plan, Sections 10.3 to 10.5, S8): the composition of response.py's normative stages that
g4sim_digi, its C++ build, reproduces. Pure computation: the caller reads and writes files.

A g4sim-digi-job/1 holds everything the draws need: the run seed and replica; the scintillation stage (name, light yield, resolution scale
and the optional yield variation); the channels; per segmentation bin the efficiencies, already taken from the map (analytic, or mapped with
its Dirichlet replica, which draws once per bin and not per event); the photon timing (decay and rise of the component, and the transit:
exponential, or the bin's arrival-time distribution); the sensor and the electronics stages with their names. Bins are rows
(event, volume ID, bin, E^L, E^S, n^L) of edep_visible_ly_split.

For each (event, volume): the yield factor; for each bin, on the volume stream of the stage at sub-index bin, N_b and its multinomial in
channel order, then, if timing is on, one time per detected photon (response.photon_times), given to the channels in channel order; then for
each channel c, cell volume x C + c, the sensor on its channel stream and the electronics on theirs. Every draw comes from the sub-stream
the response-pipeline/1 table names, so the order of events, volumes and bins does not matter (Section 10.2).
"""
from __future__ import annotations

import math
import struct

from core.simulation import efficiency_map, response, rng

SCHEMA = "g4sim-digi-job/1"
TRANSIT_KINDS = ("exponential", "mapped")


class DigiError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def check_job(job: dict) -> None:
    if job.get("schema") != SCHEMA:
        raise DigiError("schema", f"{job.get('schema')!r} is not {SCHEMA}")
    channels = job["channels"]
    if not channels or len(set(channels)) != len(channels):
        raise DigiError("channels", "the channels are named once each")
    for bin_index, values in job["efficiencies"].items():
        if len(values) != len(channels) or any(not 0.0 <= value <= 1.0 for value in values) or math.fsum(values) > 1.0:
            raise DigiError("efficiencies", f"bin {bin_index}: {values}")
    timing = job.get("timing")
    if timing is not None:
        if not isinstance(timing, dict) or "transit" not in timing:
            raise DigiError("timing", "timing is null or an object with decay_ns and transit")
        transit = timing["transit"]
        if transit["kind"] not in TRANSIT_KINDS:
            raise DigiError("transit", f"transit {transit['kind']!r}")
        if timing["decay_ns"] <= 0 or timing.get("rise_ns", 0.0) < 0:
            raise DigiError("timing", "decay must be positive and rise not negative")
        if transit["kind"] == "exponential" and not transit.get("transit_ns", 0.0) > 0:
            raise DigiError("transit", "an exponential transit needs a positive transit_ns")
        if transit["kind"] == "mapped" and any(not isinstance(count, int) or count < 0 for counts in transit["counts"].values() for count in counts):
            raise DigiError("transit", "transit counts are non-negative integers")
    electronics = job["electronics"]
    if not isinstance(electronics["bits"], int) or not 1 <= electronics["bits"] <= 62 or not electronics["lsb"] > 0:
        raise DigiError("electronics", "bits is an integer from 1 to 62 and lsb positive (g4sim_digi holds codes in 64 bits)")
    names = [job["stage"]["name"], job["sensor"]["name"], job["electronics"]["name"]]
    if len(set(names)) != 3:
        raise DigiError("stage-name", "the scintillation, sensor and electronics stages need distinct names")


def from_bits(text: str) -> float:
    """A continuous value of g4sim_digi's output: the 16 hex digits of its IEEE 754 bits."""
    return struct.unpack(">d", bytes.fromhex(text))[0]


TIME_BLOCKS = 64  # keys for 64 blocks of 2^15 photons: 2^21 detected photons in one bin


def job_with_keys(job: dict, blocks: int = TIME_BLOCKS) -> dict:
    """The job for g4sim_digi: the same job with the two key words of every stream it draws from, computed here with canonical/1, so the
    C++ side needs no canonical encoder (g4sim/Philox.hh)."""
    seed, replica, stage = job["run_seed"], job["replica"], job["stage"]["name"]
    keys = {"stage": list(rng.volume_key(seed, stage, replica)), "yield": list(rng.volume_key(seed, response.YIELD_STAGE, replica)),
            "sensor": list(rng.channel_key(seed, job["readout"], job["sensor"]["name"], replica)),
            "electronics": list(rng.channel_key(seed, job["readout"], job["electronics"]["name"], replica)),
            "time_blocks": [list(rng.volume_key(seed, f"{stage}/time/{block}", replica)) for block in range(blocks)]}
    return {**job, "keys": keys}


def _transit_document(job: dict) -> dict | None:
    """An efficiency-map/1 skeleton holding only what response.photon_times reads of a mapped transit."""
    transit = job["timing"]["transit"]
    if transit["kind"] != "mapped":
        return None
    rows = [{"bin": int(index), "transit_counts": counts} for index, counts in sorted(transit["counts"].items(), key=lambda item: int(item[0]))]
    return {"form": {"kind": efficiency_map.FORM, "transit_edges_ns": transit["edges_ns"], "bins": rows}}


def digitize(job: dict, rows: list) -> tuple[list, list]:
    """(channel rows, time rows). A channel row is (event, volume, channel index, photoelectrons, charge, code or None); a time row is
    (event, volume, bin, channel index, time in ns). Rows come out sorted by event, volume, then channel (and bin for times)."""
    check_job(job)
    stage, sensor, electronics = job["stage"], job["sensor"], job["electronics"]
    document = {"run_seed": job["run_seed"], "replica": job["replica"]}
    pipeline_stage = {"name": stage["name"], "parameters": {"light_yield_per_MeV": {"value": stage["light_yield_per_MeV"]},
                                                            "resolution_scale": {"value": stage["resolution_scale"]}}}
    count = len(job["channels"])
    timing = job.get("timing")
    transit_document = _transit_document(job) if timing else None
    sensor_key = rng.channel_key(job["run_seed"], job["readout"], sensor["name"], job["replica"])
    electronics_key = rng.channel_key(job["run_seed"], job["readout"], electronics["name"], job["replica"])
    grouped: dict = {}
    for event, volume, bin_index, large, small, steps in rows:
        if not (math.isfinite(large) and math.isfinite(small)):
            raise DigiError("bin-energy", f"event {event}, volume {volume}, bin {bin_index}: energies must be finite")
        bins = grouped.setdefault((event, volume), {})
        if bin_index in bins:
            raise DigiError("bin-twice", f"event {event}, volume {volume}: bin {bin_index} appears twice")
        bins[bin_index] = (large, small, steps)
    channel_rows, time_rows = [], []
    for (event, volume), bins in sorted(grouped.items()):
        factor = response.yield_factor(document, event, volume, stage.get("yield_relative_width", 0.0))
        key = rng.volume_key(job["run_seed"], stage["name"], job["replica"])
        photoelectrons = [0] * count
        for bin_index in sorted(bins):
            large, small, steps = bins[bin_index]
            efficiencies = job["efficiencies"].get(str(bin_index))
            if efficiencies is None:
                raise DigiError("efficiencies", f"bin {bin_index} has no efficiencies")
            stream = rng.SubStream(key, event, volume, bin_index)
            photons = response.bin_photons(stream, pipeline_stage["parameters"]["light_yield_per_MeV"]["value"],
                                           pipeline_stage["parameters"]["resolution_scale"]["value"], large, small, steps, factor)
            counts = stream.multinomial(photons, efficiencies)[:count]
            for at, drawn in enumerate(counts):
                photoelectrons[at] += drawn
            if timing and sum(counts):
                times = response.photon_times(document, stage["name"], event, volume, bin_index, sum(counts), timing["decay_ns"],
                                              timing["transit"].get("transit_ns", 0.0), transit_document, timing.get("rise_ns", 0.0))
                start = 0
                for at, drawn in enumerate(counts):
                    time_rows += [(event, volume, bin_index, at, value) for value in times[start:start + drawn]]
                    start += drawn
        for at in range(count):
            cell = volume * count + at
            charge = response.sensor_response(rng.SubStream(sensor_key, event, cell), photoelectrons[at], sensor["gain"], sensor["excess_noise"],
                                              sensor["dark_rate_per_ns"], sensor["gate_ns"])
            code = response.electronics_response(rng.SubStream(electronics_key, event, cell), charge, electronics["noise_sigma"],
                                                 electronics["threshold"], electronics["lsb"], electronics["bits"])
            channel_rows.append((event, volume, at, photoelectrons[at], charge, code))
    time_rows.sort(key=lambda row: row[:4])  # stable: within a (event, volume, bin, channel) the draw order is kept
    return channel_rows, time_rows
