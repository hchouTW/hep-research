"""adapters/acts-tracking: what jobs 7494285 and 7494405 could not show (D1 stage 5 review m1, m3, m4, m7, m10; D1 stage 5d report). A diagnosis on block 1, tuning, not a gate reading.

Every finder reads the same data files: the current one, the kept binaries of earlier jobs (HEP_ACTS_TRACKING_EARLIER_FINDERS, name=path pairs joined by commas) and the two diagnostic builds of
CMakeLists.txt. So a track lost by one and kept by another is a paired fact, not a fluctuation. It prints each fake of the detailed stratum with its fit, owners and hits, each lost particle, the
evicted candidates of those events, lost tracks by class for each pair of finders, what became of true seeds, and how many tracks had a foreign hit inside each window on plane 1. Lines start
DIAGNOSIS-. Records, seed files and truth stay under HEP_ACTS_TRACKING_EVIDENCE/diagnosis, and the detailed stratum's data file too: the noise data files are 600 MB each, and the frozen generators
remake them. Truth is read here, after the finders have finished. Tests fail only on a binary that does not read its own job's numbers, or on a behaviour or a configuration that moved.
Run from the plugin root: python -m unittest tests.adapters.test_acts_finding_diagnosis -v
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import math
import os
import unittest
from collections import Counter, defaultdict
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests

finding_record, truth_files, fixture_files = finding_tests.finding_record, finding_tests.truth_files, finding_tests.fixture_files

EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
EARLIER_FINDERS = dict(pair.split("=", 1) for pair in os.environ.get("HEP_ACTS_TRACKING_EARLIER_FINDERS", "").split(",") if pair)
RUNNABLE = finding_tests.BUILT and bool(EVIDENCE_DIR) and bool(EARLIER_FINDERS)
NOT_RUNNABLE = "needs the T07 build job: HEP_ACTS_TRACKING_BUILD, HEP_ACTS_TRACKING_EVIDENCE and HEP_ACTS_TRACKING_EARLIER_FINDERS"

CURRENT, CHORD_SLOPE, TWO_SHARED_HITS = "current", "chord-slope", "two-shared-hits"
JOB_BEFORE_HELIX, JOB_OF_HELIX = "job-7494285", "job-7494405"
DETAILED_CASE = ("clean", 2)
CASES = (DETAILED_CASE, ("noise", 2), ("noise", 5), ("noise", 8), ("noise", 11))  # the review's stratum, and the o3 noise strata, one per momentum bin
LOST_IN_ITS_JOB = {JOB_BEFORE_HELIX: {("clean", 2): 5, ("noise", 2): 185, ("noise", 5): 146, ("noise", 8): 151, ("noise", 11): 158},  # FINDING-READING of each job
                   JOB_OF_HELIX: {("clean", 2): 6, ("noise", 2): 187, ("noise", 5): 192, ("noise", 8): 188, ("noise", 11): 214}}
SEED_TRIPLES = ((1, 2, 3), (1, 2, 4), (3, 4, 5), (6, 7, 8))
PLANE_SPACING_MM = 50.0
HIT_SIGMA_MM = finding_tests.HIT_SIGMA_MM
SEED_PRIOR_INFLATION = 1.5
CHI2_CUT = 16.0
NOISE_OWNER = -1


# ---- Judges of one track, testable without a build.

def missed_class(missed: tuple) -> str:
    """A particle's missed planes, in the classes of the stage 5 review's m2."""
    if not missed:
        return "all-kept"
    if len(missed) == 1:
        return "single-plane-1" if missed == (1,) else "single-other"
    if 1 not in missed:
        return "pair-without-1"
    return "pair-1-breaks-3-4-5" if set(missed) & {3, 4, 5} else "pair-1-keeps-3-4-5"


def owner_counts(hit_keys, owner_of_hit: dict) -> Counter:
    return Counter(owner_of_hit.get(key, NOISE_OWNER) for key in hit_keys)


def is_fake(hit_keys, owner_of_hit: dict) -> bool:
    """Section 7: no particle holds more than 50 % of the track's measurements. Noise counts in the denominator and owns nothing."""
    return not any(owner != NOISE_OWNER and 2 * count > len(hit_keys) for owner, count in owner_counts(hit_keys, owner_of_hit).items())


def parabola_chi2(plane_x_mm, loc0_mm, loc1_mm) -> tuple:
    """Chi2 and ndf of a hit set by least squares on the five parameters of a slow helix, independent of ACTS: u'' = c, v'' = c u' v' / (1 + u'^2), as KalmanRefit::start_of writes them. For the
    evicted candidates, which the finder does not fit; on selected tracks it is printed beside the finder's own fit."""
    positions = numpy.asarray(plane_x_mm, float) - numpy.mean(plane_x_mm)
    along_u, along_v = numpy.asarray(loc0_mm, float), numpy.asarray(loc1_mm, float)
    ones, half_square = numpy.ones_like(positions), 0.5 * positions ** 2
    bend_of_v = 0.0
    for _ in range(4):
        matrix = numpy.block([[ones[:, None], positions[:, None], half_square[:, None], 0 * ones[:, None], 0 * ones[:, None]],
                              [0 * ones[:, None], 0 * ones[:, None], bend_of_v * half_square[:, None], ones[:, None], positions[:, None]]])
        measured = numpy.concatenate([along_u, along_v])
        solution = numpy.linalg.lstsq(matrix, measured, rcond=None)[0]
        bend_of_v = solution[1] * solution[4] / (1.0 + solution[1] ** 2)
    residuals = measured - matrix @ solution
    return float(residuals @ residuals) / HIT_SIGMA_MM ** 2, 2 * len(positions) - 5


def seed_window(seed_points, plane_x_mm: float, slope_rule: str) -> tuple:
    """Where a seed's start puts a plane it has not reached, and the residual variances there, in a linear model: Lagrange along u, along v a straight line in the arc length through the first hit.
    slope_rule: "chord" takes the first and last hit (job 7494285), "last-two" the middle and last (ACTS's estimate, read from its disassembly). seed_points: (x, u, v) of the three hits."""
    x_seed = [point[0] for point in seed_points]
    weights_u = [math.prod((plane_x_mm - other) / (x_seed[index] - other) for other in x_seed if other != x_seed[index]) for index in range(3)]
    centre_u = sum(weight * point[1] for weight, point in zip(weights_u, seed_points))
    coefficients = numpy.polyfit(x_seed, [point[1] for point in seed_points], 2)

    def arc_to(x_mm: float) -> float:
        samples = numpy.linspace(x_seed[0], x_mm, 9)
        rise = numpy.polyval(coefficients, samples)
        return float(numpy.sign(x_mm - x_seed[0]) * numpy.hypot(numpy.diff(samples), numpy.diff(rise)).sum())

    arc_mid, arc_last, arc_plane = arc_to(x_seed[1]), arc_to(x_seed[2]), arc_to(plane_x_mm)
    if slope_rule == "chord":
        share = arc_plane / arc_last
        weights_v = [1.0 - share, 0.0, share]
    else:
        share = arc_plane / (arc_last - arc_mid)
        weights_v = [1.0, -share, share]
    centre_v = sum(weight * point[2] for weight, point in zip(weights_v, seed_points))
    spread = (SEED_PRIOR_INFLATION * HIT_SIGMA_MM) ** 2
    return centre_u, centre_v, spread * sum(weight ** 2 for weight in weights_u) + HIT_SIGMA_MM ** 2, spread * sum(weight ** 2 for weight in weights_v) + HIT_SIGMA_MM ** 2


def hits_inside(window: tuple, loc0_mm, loc1_mm):
    """Which hits pass the chi2 cut of a window. The correlation between u and v is left out: a linear count, not the filter."""
    centre_u, centre_v, variance_u, variance_v = window
    return (loc0_mm - centre_u) ** 2 / variance_u + (loc1_mm - centre_v) ** 2 / variance_v < CHI2_CUT


def seed_fates(hit_of_plane: dict, seeds) -> dict:
    """For each seed triple a particle holds whole, what became of the seed made of its own hits: an outcome, or "not-found"."""
    outcome_of_keys = {tuple(seed["hit_keys"]): seed["outcome"] for seed in seeds}
    return {"-".join(map(str, triple)): outcome_of_keys.get(tuple(hit_of_plane[plane] for plane in triple), "not-found") for triple in SEED_TRIPLES if all(plane in hit_of_plane for plane in triple)}


def finer_loss(category: str, fates: dict) -> str:
    """Stage 5 review m10: what "seed-or-finding" holds, on the scoring side. No seed found, every seed skipped, every seed failed, or the search died."""
    if category != "seed-or-finding":
        return category
    outcomes = set(fates.values())
    if not outcomes or outcomes == {"not-found"}:
        return "no-true-seed"
    if outcomes & {"candidates"}:
        return "search-kept-other-hits"
    if outcomes & {"no-candidate"}:
        return "search-died"
    return "seed-failed-or-skipped"


def shared_with_selected(item: dict, selected) -> dict:
    return {other["key"]: len(set(item["hit_keys"]) & set(other["hit_keys"])) for other in selected if other["key"] != item["key"] and set(item["hit_keys"]) & set(other["hit_keys"])}


def configuration_hash(configuration: dict, keys) -> str:
    """The finder's configuration_sha256, over the lines of the keys named."""
    return hashlib.sha256("".join(f"configuration {name} {configuration[name]}\n" for name in keys).encode()).hexdigest()


def behaviour_of(event: dict) -> list:
    """What a finder decided in one event, leaving out the marks of the record."""
    return [(item["hit_keys"], item["seed_planes"], item["outcome"], item["search_chi2"], item["fit_chi2"]) for item in event["found"]]


# ---- The printed readings.

class EventView:
    """One event of the detailed stratum: truth, hits, and how to write a candidate or a particle."""

    def __init__(self, label: str, ordinal: int, truth_event, data_event, event: dict, seeds):
        self.label, self.ordinal, self.truth_event, self.event, self.seeds = label, ordinal, truth_event, event, seeds
        self.hits = {int(hit["hit_key"]): hit for hit in data_event["hits"]}
        self.tracks = truth_event["tracks"]
        self.owner_of_hit = {int(key): index for index, track in enumerate(self.tracks) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY}
        self.selected = [item for item in event["found"] if item["outcome"] == "selected"]

    def hit_text(self, key: int) -> str:
        return f"p{int(self.hits[key]['plane'])}:{key}({self.owner_of_hit.get(key, 'noise')})"

    def seed_of(self, item: dict):
        position = int(item["key"].rsplit("-", 1)[1])
        return next((seed for seed in self.seeds if seed["first_candidate"] <= position < seed["first_candidate"] + seed["candidates"]), None)

    def fit_text(self, item: dict) -> str:
        rows = [self.hits[key] for key in item["hit_keys"]]
        chi2, ndf = parabola_chi2([PLANE_SPACING_MM * (int(row["plane"]) - 1) for row in rows], [row["loc0_mm"] for row in rows], [row["loc1_mm"] for row in rows])
        fitted = f"fit_chi2/ndf {item['fit_chi2'] / (item['fit_coordinates'] - 5):.3f}" if item["fit_coordinates"] else "fit_chi2/ndf none"
        return f"{fitted} parabola_chi2/ndf {chi2 / ndf:.3f} search_chi2 {item['search_chi2']:.3f}"

    def candidate_text(self, item: dict) -> str:
        seed = self.seed_of(item)
        seed_hits = " ".join(self.hit_text(key) for key in seed["hit_keys"]) if seed else "unknown"
        return (f"{self.label} event {self.ordinal} {item['key']} {item['outcome']} seed {item['seed_planes']} seed_hits [{seed_hits}] measurements {item['measurements']} holes {item['holes']} "
                f"truncated {int(item['search_truncated'])} {self.fit_text(item)} owners {dict(owner_counts(item['hit_keys'], self.owner_of_hit))} hits [{' '.join(self.hit_text(key) for key in item['hit_keys'])}]")

    def particle_text(self, index: int) -> str:
        track = self.tracks[index]
        vertex = self.truth_event["vertices"][int(track["vertex_index"])]
        return (f"{self.label} event {self.ordinal} particle {index} q/p {float(track['q_over_p']):+.5f} slope_u {float(track['slope_u']):+.5f} slope_v {float(track['slope_v']):+.5f} "
                f"vertex {int(track['vertex_index'])} u {float(vertex['u_mm']):+.4f} v {float(vertex['v_mm']):+.4f} z {float(vertex['z_mm']):+.3f}")

    def separation_text(self, first: int, second: int) -> str:
        apart = numpy.hypot(*(self.tracks[first]["crossings"][:, :2] - self.tracks[second]["crossings"][:, :2]).T)
        return f"{self.label} event {self.ordinal} particles {first} {second} separation per plane mm {' '.join(f'{value:.3f}' for value in apart)} smallest {apart.min():.3f} largest {apart.max():.3f}"

    def nearest_other(self, index: int) -> int:
        others = [other for other in range(len(self.tracks)) if other != index]
        return min(others, key=lambda other: float(numpy.abs(self.tracks[index]["crossings"][:, :2] - self.tracks[other]["crossings"][:, :2]).max()))

    def print_block(self, kind: str, owners, item=None) -> None:
        if item is not None:
            print(f"DIAGNOSIS-{kind} {self.candidate_text(item)}", flush=True)
        for index in owners:
            print(f"DIAGNOSIS-OWNER {self.particle_text(index)}", flush=True)
        pairs = list(zip(owners, owners[1:])) or [(owners[0], self.nearest_other(owners[0]))]
        for first, second in pairs:
            print(f"DIAGNOSIS-SEPARATION {self.separation_text(first, second)}", flush=True)
        for other in self.event["found"]:
            if other["outcome"] == "evicted" and set(other["hit_keys"]) & {int(key) for index in owners for key in self.tracks[index]["hit_keys"]}:
                print(f"DIAGNOSIS-EVICTED {self.candidate_text(other)} shares_with_selected {shared_with_selected(other, self.selected)}", flush=True)


def fate_in_finder(particle: dict, event: dict) -> str:
    """How one finder treated a particle, in a line: the track that holds its majority, or the candidates that did."""
    owned = set(particle["hit_keys"])
    kept = [f"{item['key']} {item['outcome']} hits {len(item['hit_keys'])} own {len(owned & set(item['hit_keys']))}" for item in event["found"] if 2 * len(owned & set(item["hit_keys"])) > len(item["hit_keys"])]
    return "; ".join(kept[:6]) or "no candidate holds its majority"


def analysed_case(case: tuple, data_file: Path, truth_file: Path, runs: dict, seed_files: dict) -> dict:
    """Every finder's record against truth, event by event."""
    fixture, stratum = case
    label = f"{fixture} stratum {stratum}"
    records = {name: finding_record.parse_record(path.read_text(encoding="utf-8"), finding_record.EARLIER_CONFIGURATION_KEYS if name in EARLIER_FINDERS else finding_record.CONFIGURATION_KEYS, name not in EARLIER_FINDERS)
               for name, path in runs.items()}
    tally = {name: Counter() for name in runs}
    categories = {name: Counter() for name in runs}
    paired = defaultdict(Counter)
    seed_counts = Counter()
    fate_counts = Counter()
    intruders = Counter()
    ambiguity_shares = Counter()
    changed_events = {name: 0 for name in runs}
    seed_streams = {name: finding_record.iter_seed_events(path) for name, path in seed_files.items()}
    comparisons = [(JOB_BEFORE_HELIX, CURRENT), (CURRENT, CHORD_SLOPE), (CURRENT, TWO_SHARED_HITS)]
    for ordinal, (truth_event, data_event) in enumerate(zip(truth_files.iter_truth_events(truth_file), fixture_files.iter_data_events(data_file))):
        particles = finding_tests.particles_of(truth_event)
        missed = [finding_tests.missed_planes_of(track) for track in truth_event["tracks"]]
        seeds = {name: next(stream) for name, stream in seed_streams.items()}
        owner_of_hit = {key: index for index, particle in enumerate(particles) for key in particle["hit_keys"]}
        rows = data_event["hits"]
        plane_of_hit = rows["plane"]
        lost = {}
        for name, record in records.items():
            event = record["events"][ordinal]
            scores = finding_tests.scored_event(finding_tests.tracks_of(event), particles)
            tally[name].update({key: scores[key] for key in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates")})
            lost[name] = set(scores["lost"])
            if name != JOB_OF_HELIX and JOB_OF_HELIX in records:
                changed_events[name] += behaviour_of(event) != behaviour_of(records[JOB_OF_HELIX]["events"][ordinal])
            for index in scores["lost"]:
                category = finding_tests.loss_category(particles[index], event)
                if name in seeds:
                    hit_of_plane = {int(rows["plane"][key]): key for key in particles[index]["hit_keys"]}
                    fates = seed_fates(hit_of_plane, seeds[name])
                    category = finer_loss(category, fates)
                    if name == CURRENT:
                        fate_counts.update((missed_class(missed[index]), triple, outcome) for triple, outcome in fates.items())
                categories[name][(missed_class(missed[index]), category)] += 1
                if name == CURRENT and category == "ambiguity":
                    owned = set(particles[index]["hit_keys"])
                    best = min((sum(shared_with_selected(item, [other for other in event["found"] if other["outcome"] == "selected"]).values())
                                for item in event["found"] if item["outcome"] == "evicted" and 2 * len(owned & set(item["hit_keys"])) > len(item["hit_keys"])), default=-1)
                    ambiguity_shares[min(best, 4)] += 1
        for first, second in comparisons:
            if first in lost and second in lost:
                for index, particle in enumerate(particles):
                    if len(particle["hit_keys"]) >= finding_tests.LEAST_HITS and (index in lost[first] or index in lost[second]):
                        side = "both" if index in lost[first] and index in lost[second] else f"only-{first}" if index in lost[first] else f"only-{second}"
                        paired[(first, second)][(missed_class(missed[index]), side)] += 1
        for seed in seeds.get(CURRENT, ()):
            owners = {owner_of_hit.get(key, NOISE_OWNER) for key in seed["hit_keys"]}
            seed_counts[(seed["planes"], "true" if len(owners) == 1 and NOISE_OWNER not in owners else "other", seed["outcome"])] += 1
        loc0_of_plane_1, loc1_of_plane_1 = rows["loc0_mm"][plane_of_hit == 1], rows["loc1_mm"][plane_of_hit == 1]
        for index, particle in enumerate(particles):
            if 1 not in missed[index] or len(particle["hit_keys"]) < finding_tests.LEAST_HITS:
                continue
            hit_of_plane = {int(rows["plane"][key]): key for key in particle["hit_keys"]}
            for triple in ((3, 4, 5), (6, 7, 8)):
                if all(plane in hit_of_plane for plane in triple):
                    points = [(PLANE_SPACING_MM * (plane - 1), float(rows["loc0_mm"][hit_of_plane[plane]]), float(rows["loc1_mm"][hit_of_plane[plane]])) for plane in triple]
                    inside = tuple(bool(hits_inside(seed_window(points, 0.0, rule), loc0_of_plane_1, loc1_of_plane_1).any()) for rule in ("chord", "last-two"))
                    cell = (missed_class(missed[index]), triple, inside)
                    intruders[cell + ("tracks",)] += 1
                    intruders.update(cell + (f"lost-{name}",) for name in lost if index in lost[name])
        if case == DETAILED_CASE:
            print_detailed_event(label, ordinal, truth_event, data_event, records, seeds, particles, lost)
    return {"case": case, "label": label, "tally": tally, "categories": categories, "paired": paired, "seed_counts": seed_counts, "fate_counts": fate_counts, "intruders": intruders,
            "ambiguity_shares": ambiguity_shares, "changed_events": changed_events, "configurations": {name: record["configuration"] for name, record in records.items()},
            "hashes": {name: record["header"]["configuration_sha256"] for name, record in records.items()}}


def print_detailed_event(label: str, ordinal: int, truth_event, data_event, records: dict, seeds: dict, particles: list, lost: dict) -> None:
    """The review's list, for each fake and each lost particle of the detailed stratum under the current finder, then what the earlier finder did with the same particles."""
    event = records[CURRENT]["events"][ordinal]
    view = EventView(label, ordinal, truth_event, data_event, event, seeds[CURRENT])
    fakes = [item for item in view.selected if is_fake(item["hit_keys"], view.owner_of_hit)]
    gone = sorted(lost[CURRENT])
    if not fakes and not gone and not lost.get(JOB_BEFORE_HELIX):
        return
    print(f"DIAGNOSIS-EVENT {label} event {ordinal}: fakes {len(fakes)} lost {gone} lost in {JOB_BEFORE_HELIX} {sorted(lost.get(JOB_BEFORE_HELIX, ()))} near_separation {int(truth_event['near_separation'])} "
          f"seeds_truncated {event['seeds_truncated']}", flush=True)
    for item in fakes:
        owners = [owner for owner, _ in owner_counts(item["hit_keys"], view.owner_of_hit).most_common() if owner != NOISE_OWNER]
        view.print_block("FAKE", owners, item)
    for index in gone:
        print(f"DIAGNOSIS-LOST {view.particle_text(index)} planes {finding_tests.missed_planes_of(view.tracks[index])} category {finding_tests.loss_category(particles[index], event)}", flush=True)
        view.print_block("LOST", [index])
    for index in sorted(set(gone) | {owner for item in fakes for owner in owner_counts(item["hit_keys"], view.owner_of_hit) if owner != NOISE_OWNER}):
        for name in records:
            if name != CURRENT:
                print(f"DIAGNOSIS-ELSEWHERE {label} event {ordinal} particle {index} in {name}: {fate_in_finder(particles[index], records[name]['events'][ordinal])}", flush=True)


def print_case(reading: dict) -> None:
    label = reading["label"]
    for name, tally in reading["tally"].items():
        print(f"DIAGNOSIS-READING {label} {name}: reconstructable {tally['reconstructable']} lost {tally['reconstructable'] - tally['with_primary']} reconstructed {tally['reconstructed']} fakes {tally['fakes']} "
              f"matched {tally['matched']} duplicates {tally['duplicates']}", flush=True)
        for (klass, category), count in sorted(reading["categories"][name].items()):
            print(f"DIAGNOSIS-LOST-CLASS {label} {name} {klass} {category}: {count}", flush=True)
    for pair, cells in reading["paired"].items():
        for (klass, side), count in sorted(cells.items()):
            print(f"DIAGNOSIS-PAIRED {label} {pair[0]} against {pair[1]} {klass} {side}: {count}", flush=True)
    for (planes, kind, outcome), count in sorted(reading["seed_counts"].items()):
        print(f"DIAGNOSIS-SEEDS {label} current seed {planes} {kind} {outcome}: {count}", flush=True)
    for (klass, triple, outcome), count in sorted(reading["fate_counts"].items()):
        print(f"DIAGNOSIS-SEED-FATE {label} current lost {klass} own seed {triple} {outcome}: {count}", flush=True)
    for cell in sorted({key[:3] for key in reading["intruders"]}, key=str):
        klass, triple, (in_chord, in_last_two) = cell
        counts = {key[3]: count for key, count in reading["intruders"].items() if key[:3] == cell}
        print(f"DIAGNOSIS-INTRUDER {label} {klass} seed {triple} foreign hit in chord window {int(in_chord)} in last-two window {int(in_last_two)}: {counts}", flush=True)
    print(f"DIAGNOSIS-AMBIGUITY {label} current ambiguity losses by fewest hits an evicted majority candidate shares with selected tracks (4 means 4 or more, -1 no such candidate): "
          f"{dict(sorted(reading['ambiguity_shares'].items()))}", flush=True)


def run_case(case: tuple, folder: Path) -> tuple:
    fixture, stratum = case
    data_file, truth_file = finding_tests.generate(folder, fixture, stratum, finding_tests.EVENTS_PER_BIN)
    return case, data_file, truth_file


def run_finder(job: tuple, folder: Path) -> tuple:
    case, name, program, data_file = job
    title = f"diagnosis-{case[0]}-{case[1]}-{name}"
    seed_file = folder / f"{title}.seeds" if name in (CURRENT, CHORD_SLOPE) else None
    _, record_file, product_file = finding_tests.find(folder, data_file, title, 0, program=program, seed_file=seed_file)
    product_file.unlink()
    return case, name, record_file, seed_file


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class PairedDiagnosis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = Path(EVIDENCE_DIR) / "diagnosis"
        folder.mkdir(parents=True, exist_ok=True)
        build = Path(finding_tests.BUILD_DIR)
        finders = {**{name: Path(path) for name, path in EARLIER_FINDERS.items()}, CURRENT: finding_tests.FINDER, CHORD_SLOPE: build / "acts_finder_chord_slope", TWO_SHARED_HITS: build / "acts_finder_two_shared_hits"}
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            files = {case: (data_file, truth_file) for case, data_file, truth_file in pool.map(lambda case: run_case(case, folder), CASES)}
            jobs = [(case, name, program, files[case][0]) for case in reversed(CASES) for name, program in finders.items()]
            finished = list(pool.map(lambda job: run_finder(job, folder), jobs))
        cls.readings = []
        for case in CASES:
            runs = {name: record_file for found_case, name, record_file, _ in finished if found_case == case}
            seed_files = {name: seed_file for found_case, name, _, seed_file in finished if found_case == case and seed_file}
            reading = analysed_case(case, files[case][0], files[case][1], runs, seed_files)
            print_case(reading)
            cls.readings.append(reading)
            if case != DETAILED_CASE:
                files[case][0].unlink()
        hashes = cls.readings[0]["hashes"]
        configurations = cls.readings[0]["configurations"]
        for name, value in hashes.items():
            print(f"DIAGNOSIS-CONFIGURATION {name} configuration_sha256 {value} over the earlier keys {configuration_hash(configurations[name], finding_record.EARLIER_CONFIGURATION_KEYS)}", flush=True)
        for key, value in configurations[CURRENT].items():
            print(f"DIAGNOSIS-CONFIGURATION current {key} {value}", flush=True)

    def test_each_kept_binary_reads_its_own_job(self):
        for reading in self.readings:
            for name, lost_of_case in LOST_IN_ITS_JOB.items():
                tally = reading["tally"].get(name)
                with self.subTest(case=reading["case"], name=name):
                    self.assertIsNotNone(tally)
                    self.assertEqual(tally["reconstructable"] - tally["with_primary"], lost_of_case[reading["case"]])

    def test_the_current_finder_decides_as_job_7494405_did(self):
        """This stage changes marks and prints, not the recipe: every candidate, outcome, search chi2 and fit, event by event."""
        for reading in self.readings:
            with self.subTest(case=reading["case"]):
                self.assertEqual(reading["changed_events"][CURRENT], 0)

    def test_no_configuration_value_changed(self):
        """Stage 5 review m7: the earlier jobs' hash, recomputed from today's values of the same keys."""
        reading = self.readings[0]
        current = reading["configurations"][CURRENT]
        for name in EARLIER_FINDERS:
            with self.subTest(name=name):
                self.assertEqual(configuration_hash(current, finding_record.EARLIER_CONFIGURATION_KEYS), reading["hashes"][name])
        self.assertEqual(current["diagnostic_build"], "none")

    def test_a_diagnostic_build_differs_in_what_it_names(self):
        configurations = self.readings[0]["configurations"]
        current = configurations[CURRENT]
        differing = {name: sorted(key for key, value in configurations[name].items() if value != current[key]) for name in (CHORD_SLOPE, TWO_SHARED_HITS)}
        self.assertEqual(differing, {CHORD_SLOPE: ["diagnostic_build"], TWO_SHARED_HITS: ["ambiguity_most_shared_hits", "diagnostic_build"]})


class TrackJudges(unittest.TestCase):
    def test_classes_follow_the_review(self):
        expected = {(): "all-kept", (1,): "single-plane-1", (5,): "single-other", (1, 4): "pair-1-breaks-3-4-5", (1, 2): "pair-1-keeps-3-4-5", (1, 8): "pair-1-keeps-3-4-5", (2, 4): "pair-without-1"}
        for missed, klass in expected.items():
            with self.subTest(missed=missed):
                self.assertEqual(missed_class(missed), klass)

    def test_a_tie_is_fake_and_a_majority_is_not(self):
        owners = {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1}
        self.assertTrue(is_fake(list(range(8)), owners))
        self.assertFalse(is_fake([0, 1, 2, 3, 4], owners))
        self.assertTrue(is_fake([0, 1, 2, 100, 101, 102], owners))

    def test_the_fit_reads_a_straight_track_at_zero_and_one_hit_off(self):
        positions = 50.0 * numpy.arange(8)
        along_u, along_v = 0.1 * positions, -0.05 * positions
        self.assertAlmostEqual(parabola_chi2(positions, along_u, along_v)[0], 0.0, places=6)
        self.assertEqual(parabola_chi2(positions, along_u, along_v)[1], 11)
        moved = along_v.copy()
        moved[4] += 5.0 * HIT_SIGMA_MM
        self.assertGreater(parabola_chi2(positions, along_u, moved)[0], 15.0)

    def test_the_windows_read_the_arithmetic_of_the_report(self):
        """A 3-4-5 seed at plane 1: along v the chord has weights 2, -1 and the last two 1, 2, -2, so sqrt(5) and 3 hit sigmas, inflated, and the area grows by 1.32."""
        points = [(100.0, 0.0, 0.0), (150.0, 0.0, 0.0), (200.0, 0.0, 0.0)]
        chord, last_two = seed_window(points, 0.0, "chord"), seed_window(points, 0.0, "last-two")
        spread = (SEED_PRIOR_INFLATION * HIT_SIGMA_MM) ** 2
        self.assertAlmostEqual(chord[3], 5.0 * spread + HIT_SIGMA_MM ** 2, places=9)
        self.assertAlmostEqual(last_two[3], 9.0 * spread + HIT_SIGMA_MM ** 2, places=9)
        self.assertAlmostEqual(chord[2], last_two[2])
        self.assertAlmostEqual(chord[2], 109.0 * spread + HIT_SIGMA_MM ** 2, places=9)
        self.assertAlmostEqual(math.sqrt(last_two[3] / chord[3]), 1.317, places=3)

    def test_a_window_holds_what_the_cut_holds(self):
        window = (0.0, 0.0, 0.01, 0.01)
        self.assertEqual(list(hits_inside(window, numpy.array([0.0, 0.39, 0.41]), numpy.zeros(3))), [True, True, False])

    def test_seed_fates_and_the_finer_loss(self):
        hits = {3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80}
        seeds = [{"hit_keys": [30, 40, 50], "outcome": "no-candidate"}]
        fates = seed_fates(hits, seeds)
        self.assertEqual(fates, {"3-4-5": "no-candidate", "6-7-8": "not-found"})
        self.assertEqual(finer_loss("seed-or-finding", fates), "search-died")
        self.assertEqual(finer_loss("seed-or-finding", {"6-7-8": "not-found"}), "no-true-seed")
        self.assertEqual(finer_loss("seed-or-finding", {"3-4-5": "skipped"}), "seed-failed-or-skipped")
        self.assertEqual(finer_loss("seed-or-finding", {"3-4-5": "candidates"}), "search-kept-other-hits")
        self.assertEqual(finer_loss("ambiguity", {}), "ambiguity")

    def test_the_configuration_hash_covers_the_finder_text(self):
        expected = hashlib.sha256(b"configuration one 1\nconfiguration two 2\n").hexdigest()
        self.assertEqual(configuration_hash({"one": "1", "two": "2", "left-out": "3"}, ("one", "two")), expected)


if __name__ == "__main__":
    unittest.main()
