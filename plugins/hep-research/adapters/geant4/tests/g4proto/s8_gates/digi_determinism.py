#!/usr/bin/env python3
"""S8 gate 2: g4sim_digi against core/simulation/digitize.py, judged by the determinism table of Section 10.2 (g4sim plan, Section 19.2).

Two fixed fixtures, written here from a fixed seed: (A) analytic efficiencies, the Gamma yield variation, photon times with rise and decay;
(B) mapped arrival times and a dark-count mean of 50, so the sensor's Poisson takes PTRS. Photon numbers up to about 10^5 per bin send the
multinomial through BTPE, and three volume IDs include one above 2^32. Levels:
  1. integer layer and uniform variates: the first groups of several sub-streams, C++ against Python, identical;
  2. within g4sim_digi: the bins shuffled, and split into three chunks by event, give byte-identical output;
  3. across languages: discrete values (photoelectrons, ADC codes, the number of times) identical; continuous values (charge, times)
     within the ulp tolerance declared in the S8 task card; a discrete disagreement must be traced to a draw within 2^-40 of a decision
     boundary, and the affected sub-streams are counted.
Usage: digi_determinism.py --program PATH --work DIR [--events N]   Prints JSON with a status key. Exit 0 every level holds, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.simulation import digitize, rng  # noqa: E402

CHARGE_ULPS = 8  # the S8 task card: a Gaussian-derived value (rng.CROSS_PLATFORM_ULPS["gaussian"])
TIME_ULPS = 8  # the S8 task card: emission delay plus transit, each from -ln u or a table lookup
VOLUMES = (3, 17, 2 ** 33 + 5)
SEED = 20261109


def fixture_bins(events: int, seed: int) -> list:
    chooser = random.Random(seed)
    rows = []
    for event in range(events):
        for volume in VOLUMES:
            for bin_index in sorted(chooser.sample(range(8), chooser.randint(1, 8))):
                large = 10 ** chooser.uniform(-4, 0.3) if chooser.random() < 0.8 else 0.0
                small = 10 ** chooser.uniform(-5, -1)
                rows.append((event, volume, bin_index, large, small, chooser.randint(0, 60) if large else 0))
    return rows


def fixture_jobs(seed: int) -> dict:
    chooser = random.Random(seed + 1)
    channels = ["left", "right", "top", "bottom"]

    def efficiencies() -> dict:
        out = {}
        for b in range(8):
            values = [chooser.uniform(0.01, 0.2) for _ in channels]
            out[str(b)] = values
        return out
    base = {"schema": digitize.SCHEMA, "run_seed": seed, "replica": 0, "readout": "bar", "channels": channels,
            "sensor": {"name": "sensor", "gain": 1.0, "excess_noise": 0.1, "dark_rate_per_ns": 1e-4, "gate_ns": 100.0},
            "electronics": {"name": "electronics", "noise_sigma": 0.5, "threshold": 2.0, "lsb": 0.25, "bits": 12}}
    analytic = {**base, "stage": {"name": "scintillation", "light_yield_per_MeV": 100.0, "resolution_scale": 0.5, "yield_relative_width": 0.05},
                "efficiencies": efficiencies(), "timing": {"decay_ns": 2.1, "rise_ns": 0.5, "transit": {"kind": "exponential", "transit_ns": 1.0}}}
    edges = [0.25 * k for k in range(41)]
    counts = {str(b): [chooser.randint(0, 50) for _ in range(40)] for b in range(8)}
    mapped = {**base, "stage": {"name": "scintillation_b", "light_yield_per_MeV": 10000.0, "resolution_scale": 1.0},
              "sensor": {**base["sensor"], "dark_rate_per_ns": 0.5}, "efficiencies": efficiencies(),
              "timing": {"decay_ns": 40.0, "transit": {"kind": "mapped", "edges_ns": edges, "counts": counts}}}
    return {"A": analytic, "B": mapped}


def write_bins(path: Path, rows: list) -> None:
    path.write_text("".join(f"{e},{v},{b},{large.hex()},{small.hex()},{n}\n" for e, v, b, large, small, n in rows), encoding="ascii")


def read_csv(path: Path) -> list:
    return [line.split(",") for line in path.read_text(encoding="ascii").splitlines() if line]


def ulps(a: float, b: float) -> int:
    def ordered(x: float) -> int:
        bits = struct.unpack("<q", struct.pack("<d", x))[0]
        return bits if bits >= 0 else -(bits & 0x7FFFFFFFFFFFFFFF)
    return abs(ordered(a) - ordered(b))


def run_program(program: Path, job_path: Path, bins: Path, channels: Path, times: Path) -> None:
    done = subprocess.run([str(program), str(job_path), str(bins), str(channels), str(times)], capture_output=True, text=True, timeout=3000, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"g4sim_digi failed: {done.stderr[-400:]}")


def level_one(program: Path) -> dict:
    mismatches, groups = 0, 0
    for key, event, identity, sub in (((3839095407, 808488736), 0, 0, 0), ((1, 2), 7, 2 ** 40 + 3, 5), ((2 ** 32 - 1, 0), 2 ** 32 - 1, 2 ** 64 - 1, 2 ** 16 - 1)):
        out = subprocess.run([str(program), "--uniforms", str(key[0]), str(key[1]), str(event), str(identity), str(sub), "1000"], capture_output=True, text=True, check=True).stdout
        stream = rng.SubStream(key, event, identity, sub)
        for line in out.splitlines():
            a, b = (float.fromhex(value) for value in line.split(","))
            groups += 1
            mismatches += (a, b) != stream.group()
    return {"groups": groups, "mismatches": mismatches, "holds": groups == 3000 and mismatches == 0}


def level_two(program: Path, folder: Path, job_path: Path, rows: list, reference: tuple) -> dict:
    shuffled = list(rows)
    random.Random(SEED + 7).shuffle(shuffled)
    write_bins(folder / "bins-shuffled.csv", shuffled)
    run_program(program, job_path, folder / "bins-shuffled.csv", folder / "channels-shuffled.csv", folder / "times-shuffled.csv")
    shuffled_same = (folder / "channels-shuffled.csv").read_bytes() == reference[0] and (folder / "times-shuffled.csv").read_bytes() == reference[1]
    events = sorted({row[0] for row in rows})
    cuts = [events[len(events) // 3], events[2 * len(events) // 3]]
    parts = [[row for row in rows if row[0] < cuts[0]], [row for row in rows if cuts[0] <= row[0] < cuts[1]], [row for row in rows if row[0] >= cuts[1]]]
    channel_bytes, time_bytes = b"", b""
    for at, part in enumerate(parts):
        write_bins(folder / f"bins-chunk{at}.csv", part)
        run_program(program, job_path, folder / f"bins-chunk{at}.csv", folder / f"channels-chunk{at}.csv", folder / f"times-chunk{at}.csv")
        channel_bytes += (folder / f"channels-chunk{at}.csv").read_bytes()
        time_bytes += (folder / f"times-chunk{at}.csv").read_bytes()
    chunked_same = channel_bytes == reference[0] and time_bytes == reference[1]
    return {"shuffled_identical": shuffled_same, "three_chunks_identical": chunked_same, "holds": shuffled_same and chunked_same}


SAMPLERS = ("_poisson_inverse", "_poisson_ptrs", "_binomial_inverse", "_binomial_btpe")


def counted_digitize(job: dict, rows: list) -> tuple:
    """digitize with a count of the calls of each sampling path, so the record shows the fixture reaches every branch (PTRS, BTPE, Gamma)."""
    calls = {name: 0 for name in (*SAMPLERS, "gamma", "gaussian")}
    originals = {name: getattr(rng, name) for name in SAMPLERS}
    method_gamma, method_gaussian = rng.SubStream.gamma, rng.SubStream.gaussian

    def counting(name, function):
        def wrapper(*args, **kwargs):
            calls[name] += 1
            return function(*args, **kwargs)
        return wrapper
    try:
        for name, function in originals.items():
            setattr(rng, name, counting(name, function))
        rng.SubStream.gamma = counting("gamma", method_gamma)
        rng.SubStream.gaussian = counting("gaussian", method_gaussian)
        return (*digitize.digitize(job, rows), calls)
    finally:
        for name, function in originals.items():
            setattr(rng, name, function)
        rng.SubStream.gamma, rng.SubStream.gaussian = method_gamma, method_gaussian


def level_three(job: dict, rows: list, folder: Path) -> dict:
    channel_rows, time_rows, calls = counted_digitize(job, rows)
    cpp_channels, cpp_times = read_csv(folder / "channels.csv"), read_csv(folder / "times.csv")
    discrete, charge_ulps, worst_charge, affected = 0, [], 0, set()
    if len(cpp_channels) != len(channel_rows):
        return {"holds": False, "message": f"{len(cpp_channels)} channel rows against {len(channel_rows)}"}
    for python, cpp in zip(channel_rows, cpp_channels):
        event, volume, at, photoelectrons, charge, code = python
        if (int(cpp[0]), int(cpp[1]), int(cpp[2])) != (event, volume, at):
            return {"holds": False, "message": f"row order differs at {python[:3]}"}
        if int(cpp[3]) != photoelectrons or int(cpp[5]) != (-1 if code is None else code):
            discrete += 1
            affected.add((event, volume))
        else:
            distance = ulps(charge, digitize.from_bits(cpp[4]))
            worst_charge = max(worst_charge, distance)
            charge_ulps.append(distance)
    time_count_differs = len(cpp_times) != len(time_rows)
    worst_time, time_rows_compared = 0, 0
    if not time_count_differs:
        for python, cpp in zip(time_rows, cpp_times):
            if (int(cpp[0]), int(cpp[1]), int(cpp[2]), int(cpp[3])) != python[:4]:
                time_count_differs = True
                break
            worst_time = max(worst_time, ulps(python[4], digitize.from_bits(cpp[4])))
            time_rows_compared += 1
    holds = discrete == 0 and not time_count_differs and worst_charge <= CHARGE_ULPS and worst_time <= TIME_ULPS
    return {"sampler_calls": calls, "channel_rows": len(channel_rows), "discrete_disagreements": discrete, "affected_volumes": len(affected),
            "charge_worst_ulps": worst_charge, "charge_identical_fraction": sum(d == 0 for d in charge_ulps) / max(len(charge_ulps), 1),
            "time_rows": len(time_rows), "time_rows_compared": time_rows_compared, "time_count_differs": time_count_differs, "time_worst_ulps": worst_time,
            "tolerances_ulps": {"charge": CHARGE_ULPS, "time": TIME_ULPS}, "holds": holds,
            "boundary_tracing": "not needed: no discrete disagreement" if discrete == 0 else "required: discrete disagreements are present"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int, default=400)
    args = parser.parse_args(argv)
    program = args.program.resolve()
    try:
        rows = fixture_bins(args.events, SEED)
        report = {"level_1": level_one(program), "fixtures": {}}
        for name, job in fixture_jobs(SEED).items():
            folder = args.work / name
            folder.mkdir(parents=True, exist_ok=True)
            job_path = folder / "job.json"
            job_path.write_text(json.dumps(digitize.job_with_keys(job)), encoding="utf-8")
            write_bins(folder / "bins.csv", rows)
            run_program(program, job_path, folder / "bins.csv", folder / "channels.csv", folder / "times.csv")
            reference = ((folder / "channels.csv").read_bytes(), (folder / "times.csv").read_bytes())
            report["fixtures"][name] = {"level_2": level_two(program, folder, job_path, rows, reference), "level_3": level_three(job, rows, folder)}
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    reached = {name: sum(f["level_3"].get("sampler_calls", {}).get(name, 0) for f in report["fixtures"].values()) for name in (*SAMPLERS, "gamma", "gaussian")}
    report["every_sampler_reached"] = all(reached.values())
    holds = report["level_1"]["holds"] and report["every_sampler_reached"] and all(f["level_2"]["holds"] and f["level_3"]["holds"] for f in report["fixtures"].values())
    print(json.dumps({"status": "ok" if holds else "failed", "events": args.events, "bin_rows": len(rows), **report}, indent=1))
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main())
