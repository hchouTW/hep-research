"""adapters/acts-tracking: vertexing of T07, recipe reco.vertex.acts-amvf/1, on the tracks of reco.track.acts-ckf-planar/1 (t07-t09-task-sheets.md, Steps; D1 stage 7 brief).

Sections cited are of t04-values-v4.md. Everything printed is a development reading of block 1, tuning, not a gate result: pass or fail on a section 8 gate waits for K09
(sheet, Acceptance), and tuning runs feed nothing (section 2.2). The finder runs the vertex step when asked for it by name (--vertex-recipe) and then writes
acts-tracking-finding-record/2 (acts_finding_record.py); it never opens truth. Truth enters here, on the scoring side, after the finder has finished.

Section 7's vertex definitions, word for word in scored_vertices:
- Reconstructable vertex: truth vertex with at least 3 reconstructable tracks (a reconstructable track: at least 6 hits on distinct planes in the generator record).
- Vertex match: a reconstructed vertex matches a truth vertex if that vertex supplies more than 50 % of the summed track weights. Weights of tracks with no truth match stay in the
  denominator. A track's truth vertex is that of the particle it matches (section 7, Track match: more than 50 % of its measurements).
- Vertex primary: highest share, then most tracks, then smallest distance to truth, then lowest index.
- Vertex pull: fitted x, y, z in the global frame, primaries, far events only. Near events are reported. The global frame is ACTS's: x = fixture z, y = fixture u, z = fixture v
  (section 4.1 [R14]), so a truth vertex (u, v, z) sits at ACTS (z, u, v) (truth_position).
- Wrong assignment: a primary track with weight at least 0.5 in a matched vertex that is not its truth vertex. Denominator: primary tracks with weight at least 0.5 in matched
  vertices. Far events only.
- Near and far: section 4.1, event_index mod 5 = 0 is near. The truth file's flag is read against that rule, never in its place.
Reported, not gated (section 8.4), with this module's own definitions, stated because section 7 has none: unmatched vertices (matching no truth vertex), split truth vertices
(more than one matched vertex), merged truth vertices (two or more truth vertices whose largest summed weight lies in one reconstructed vertex).

Vertex finding, section 8.5: efficiency over reconstructable far vertices, its lower bound read as the efficiency readings are (test_acts_truth_seeded.paired_difference:
estimate less 1.645 x event-bootstrap se, B = 1,000, seeded from (fixture id, block, stratum)), printed beside the floor 0.95 as a development reading.

Predictions, fixed in the D1 stage 7 report before the first run of this recipe; a reading outside one is a disagreement with a prediction, for finding the cause, not a gate
result, and the limit does not move after results (sheet, Stop):
- Far vertex finding efficiency at least FAR_EFFICIENCY_PREDICTED in every stratum (P1).
- Far wrong-assignment rate at most WRONG_ASSIGNMENT_PREDICTED in every stratum (section 4.1's ideal is 0.020 %, 0.027 % at o3) (P2).
- Far unmatched, split and merged vertices each at most FAR_ODD_PER_EVENT_PREDICTED per event in every stratum (P3).
  P1, P2, P3 and P15 below were refuted in job 7524096. On the user's word after it (decisions.md, "After stage 7b: the user's choices": "make them readings, defaults until
  Freeze B") they fail nothing since: VERTEX-READING and VERTEX-BAD print their numbers beside the old prediction (former_prediction_readings). The constants stay, as the record
  of what was predicted. Every check of correctness stays enforced: failed events, byte, track and product equality, positive-definite covariances, chi2 below zero, P16, the
  frame, the pulls, the files' bound and vertices in every stratum (stratum_check_defects, vertex_prediction_defects).
- Far pulls, x, y, z: centre within PULL_CENTRE_Z design standard errors (1.03 / sqrt n, section 5.1), sigma_68 inside PULL_WIDTH_PREDICTED. Section 8.5: adaptive weights
  guarantee no Gaussian pull, so this range is wider than a gate's and says what this design expects, nothing more.
- No event fails its vertex step and no delivered track fails to reach the reference line.
- What the byte checks prove, and no more (D1 stage 7 review m1): (a) the /2 record of each diagnosis stratum, its vertex lines left out, equals job 7502411's /1 record byte for
  byte, and every stratum's track reading equals job 7502411's FINDING-READING line (the build job compares those): building with track_vertexing.cpp and passing the flag change
  no finding result, and nothing of one event's vertex step reaches a later event. An event's candidate lines are written before its vertex step runs, so (a) cannot see a change
  the vertex step made to that event's own fits. (b) covers that: on one stratum (PRODUCT_CHECK) the product, written from those fits after the vertex step, must be the same bytes
  with and without --vertex-recipe. (c) The vertex step takes its fits as a const reference (TrackVertexer::vertex), a static guarantee no byte check replaces.

D1 stage 7b, after job 7522969 (decisions.md, "Stage 7: results"): AMVF's initialVariances is 1e4 mm^2 on all four components (track_vertexing.hpp), for the numerics. The
limits above do not move. Added predictions: no vertex covariance that is not positive definite and no vertex chi2 below zero in any stratum (VERTEX-BAD, counted before the
reader refuses, so one job gives every count); no failed event, each failure otherwise named by ACTS's message from the finder's kept stderr. A stratum that fails is reported
with its error and its counts, and every stratum runs.

Development sample: all 12 strata of fixtures 7001 and 7002, block 1, 3,000 events each, as the finding module. The built tests need the build job and skip without it; that job
counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_vertexing -v
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import math
import os
import re
import subprocess
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests
from tests.adapters import test_acts_finding_diagnosis as diagnosis_tests
from tests.adapters import test_acts_refit_field as refit_tests
from tests.adapters.test_acts_truth_seeded import BOOTSTRAP_REPLICATES, paired_difference

finding_record, truth_files = finding_tests.finding_record, finding_tests.truth_files
NATIVE = finding_tests.NATIVE

EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
KEPT_RECORDS = os.environ.get("HEP_ACTS_TRACKING_KEPT_RECORDS", "")
RUNNABLE = finding_tests.BUILT and bool(EVIDENCE_DIR) and bool(KEPT_RECORDS)
NOT_RUNNABLE = "needs the T07 build job: HEP_ACTS_TRACKING_BUILD, HEP_ACTS_TRACKING_EVIDENCE and HEP_ACTS_TRACKING_KEPT_RECORDS"

# Section 4.1 and 7.
NEAR_MODULUS = 5
RECONSTRUCTABLE_VERTEX_TRACKS = 3
ASSIGNMENT_WEIGHT = 0.5
VERTICES_OF_LEVEL = (2, 2, 3)
VERTEX_FLOOR = 0.95  # section 8.5, a gate after K09; printed beside the reading only
COORDINATES = ("x", "y", "z")

# Predictions (D1 stage 7 report), fixed before the first run.
# P1, P2, P3 and P15: refuted in job 7524096, readings since (user, decisions.md "After stage 7b: the user's choices"). Kept as the record of the prediction; they fail nothing.
FAR_EFFICIENCY_PREDICTED = 0.995
WRONG_ASSIGNMENT_PREDICTED = 0.002
FAR_ODD_PER_EVENT_PREDICTED = 0.002
LARGE_VARIANCE_SHARE_PREDICTED = 0.001  # stage 7b fix round 1 (report P15); a reading since job 7524096, and still a reason to keep a stratum's record
HIGH_CHI2_TRACKS_PREDICTED = 5          # stage 7b fix round 1 (report P16): enforced
REFUTED_IN = "refuted in job 7524096, a reading since"
PULL_CENTRE_Z = 4.0
PULL_WIDTH_PREDICTED = (0.90, 1.15)
PRODUCT_CHECK = ("clean", 0, 50)  # fixture, stratum, events and product events: the product with and without the vertex step (review m1)
OFF_LINE_MM = 5.0  # a vertex with |x - (-100)| above this is off the reference line: ACTS's recovery path puts a candidate at x = y = 0 (review m2); counted, not judged
FRAME_LIMIT_MM = 1.0  # far primaries: rms residual per axis under this in the right frame; fixture u and v swapped puts y and z tens of mm off (v spans +-30 mm)

VERTEX_DIR = "vertexing"
VERTEX_REFERENCE_X_MM = -100.0  # track_vertexing.hpp, vertex_reference_x_mm (FrameOfAVertex reads it there)


# ---- The judges. Each takes numbers and names what is wrong, so each is tested without a build.

def truth_position(vertex) -> tuple:
    """Section 4.1 [R14]: the global ACTS frame of a truth vertex (u, v, z): x = z, y = u, z = v."""
    return (float(vertex["z_mm"]), float(vertex["u_mm"]), float(vertex["v_mm"]))


def is_near(event_index: int) -> bool:
    return int(event_index) % NEAR_MODULUS == 0


def track_owners(tracks, particles) -> list:
    """Section 7, Track match, per track: the particle supplying more than 50 % of its measurements, or None. The same rule as test_acts_finding.scored_event."""
    owner = {key: index for index, particle in enumerate(particles) for key in particle["hit_keys"]}
    owners = []
    for track in tracks:
        count_by_particle = Counter(owner[key] for key in track["hit_keys"] if key in owner)
        owners.append(next((particle for particle, count in count_by_particle.items() if 2 * count > len(track["hit_keys"])), None))
    return owners


def scored_vertices(event: dict, particles: list, vertex_of_particle: list, positions: list) -> dict:
    """Section 7's vertex quantities for one event of a /2 record. particles: {"hit_keys"} per truth particle; vertex_of_particle: its truth vertex index; positions: each truth
    vertex in the global frame (truth_position)."""
    selected = [item for item in event["found"] if item["outcome"] == "selected"]
    tracks = finding_tests.tracks_of(event)
    owners = track_owners(tracks, particles)
    owner_of_key = {item["key"]: owner for item, owner in zip(selected, owners)}
    primary_tracks = {selected[index]["key"]: particle for particle, index in finding_tests.scored_event(tracks, particles)["primaries"].items()}
    vertices = event["vertexing"]["vertices"]
    truth_count = len(positions)
    reconstructable_tracks = Counter(vertex_of_particle[index] for index, particle in enumerate(particles) if len(particle["hit_keys"]) >= finding_tests.LEAST_HITS)
    reconstructable = [truth for truth in range(truth_count) if reconstructable_tracks[truth] >= RECONSTRUCTABLE_VERTEX_TRACKS]

    matched_truth, candidates = {}, {}
    for index, vertex in enumerate(vertices):
        total = sum(track["weight"] for track in vertex["tracks"])
        by_truth = Counter()
        for track in vertex["tracks"]:
            owner = owner_of_key[track["track_key"]]
            if owner is not None:
                by_truth[vertex_of_particle[owner]] += track["weight"]
        best = next((truth for truth, weight in by_truth.items() if total > 0.0 and 2.0 * weight > total), None)
        if best is None:
            continue
        matched_truth[index] = best
        distance = math.dist(vertex["position_mm"], positions[best])
        candidates.setdefault(best, []).append((-by_truth[best] / total, -len(vertex["tracks"]), distance, index))
    primaries = {truth: min(found)[3] for truth, found in candidates.items()}

    pulls, residuals = [], []
    for truth, index in sorted(primaries.items()):
        vertex = vertices[index]
        residual = [fitted - true for fitted, true in zip(vertex["position_mm"], positions[truth])]
        variances = (vertex["covariance"][0], vertex["covariance"][3], vertex["covariance"][5])
        residuals.append(residual)
        pulls.append([value / math.sqrt(variance) for value, variance in zip(residual, variances)])

    assigned = wrong = 0
    for key, particle in primary_tracks.items():
        held_in = [matched_truth[index] for index, vertex in enumerate(vertices) if index in matched_truth
                   for track in vertex["tracks"] if track["track_key"] == key and track["weight"] >= ASSIGNMENT_WEIGHT]
        if held_in:
            assigned += 1
            wrong += int(any(truth != vertex_of_particle[particle] for truth in held_in))

    largest = {}
    for truth in range(truth_count):
        weight_in = Counter()
        for index, vertex in enumerate(vertices):
            for track in vertex["tracks"]:
                owner = owner_of_key[track["track_key"]]
                if owner is not None and vertex_of_particle[owner] == truth:
                    weight_in[index] += track["weight"]
        if weight_in and max(weight_in.values()) > 0.0:
            largest[truth] = min(index for index, weight in weight_in.items() if weight == max(weight_in.values()))
    holders = Counter(largest.values())
    return {"truth_vertices": truth_count, "reconstructable": len(reconstructable), "found": sum(truth in primaries for truth in reconstructable), "primaries": primaries,
            "pulls": pulls, "residuals": residuals, "assigned": assigned, "wrong": wrong, "vertices": len(vertices), "unmatched": len(vertices) - len(matched_truth),
            "split": sum(len(found) > 1 for found in candidates.values()), "merged": sum(holders[index] > 1 for index in largest.values())}


def near_flag_defects(truth_event) -> list:
    """Section 4.1: near is event_index mod 5 = 0. The truth file's flag must say the same."""
    if bool(int(truth_event["near_separation"])) != is_near(truth_event["event_index"]):
        return [f"event_index {int(truth_event['event_index'])} has near flag {int(truth_event['near_separation'])}"]
    return []


def vertex_step_defects(text: str) -> list:
    """The vertex step was asked for: the record must be /2 and read whole. A /1 record, one with an event's vertex step missing, or one that drops a vertex or a track, fails."""
    if text.split("\n", 1)[0] != finding_record.VERTEX_RECORD_FORMAT:
        return ["the vertex step was asked for and the record holds none"]
    try:
        finding_record.parse_record(text)
    except finding_record.RecordFormatError as error:
        return [f"the vertex record is refused: {error}"]
    return []


def efficiency_with_bound(found_per_event, reconstructable_per_event, entropy) -> tuple:
    """Section 8.5's efficiency over reconstructable vertices, with the efficiency readings' bound: estimate less 1.645 x event-bootstrap se (B = 1,000), and the 5 % percentile."""
    found = numpy.asarray(found_per_event, float)
    return paired_difference(found, numpy.zeros_like(found), reconstructable_per_event, entropy)


def stratum_vertex_tally(scored: list) -> dict:
    """Sums of one stratum's events, one population: far or near."""
    tally = Counter()
    pulls, residuals = [], []
    for item in scored:
        tally.update({name: item[name] for name in ("truth_vertices", "reconstructable", "found", "assigned", "wrong", "vertices", "unmatched", "split", "merged")})
        pulls += item["pulls"]
        residuals += item["residuals"]
    return {"tally": tally, "pulls": numpy.asarray(pulls, float).reshape(-1, 3), "residuals": numpy.asarray(residuals, float).reshape(-1, 3), "events": len(scored)}


def former_prediction_readings(far: dict, raw: Counter) -> list:
    """P1, P2, P3 and P15, refuted in job 7524096: each as a reading, its number beside the old prediction, and whether it lies inside. They fail nothing."""
    tally, events = far["tally"], far["events"]
    efficiency = tally["found"] / tally["reconstructable"] if tally["reconstructable"] else float("nan")
    rate = tally["wrong"] / tally["assigned"] if tally["assigned"] else float("nan")
    readings = [f"P1 far efficiency {efficiency:.5f} against the old prediction at least {FAR_EFFICIENCY_PREDICTED}: {'inside' if efficiency >= FAR_EFFICIENCY_PREDICTED else 'outside'}",
                f"P2 far wrong assignment {rate:.5f} against the old prediction at most {WRONG_ASSIGNMENT_PREDICTED}: {'inside' if rate <= WRONG_ASSIGNMENT_PREDICTED else 'outside'}"]
    readings += [f"P3 far {name} {tally[name]} against the old prediction at most {FAR_ODD_PER_EVENT_PREDICTED * events:g}: {'inside' if tally[name] <= FAR_ODD_PER_EVENT_PREDICTED * events else 'outside'}"
                 for name in ("unmatched", "split", "merged")]
    allowed = LARGE_VARIANCE_SHARE_PREDICTED * raw["vertices"]
    readings.append(f"P15 vertices with a variance above {LARGE_VARIANCE_MM2:g} mm^2 {raw['large_variance']} against the old prediction at most {allowed:g}: "
                    f"{'inside' if raw['large_variance'] <= allowed else 'outside'}")
    return readings


def stratum_check_defects(raw: Counter) -> list:
    """The checks of correctness on a stratum's record, enforced after job 7524096 as before: vertices in the stratum (a stratum with no counts is not decided), no covariance
    that is not positive definite, no chi2 below zero, no failed event, and P16."""
    defects = []
    if raw["vertices"] <= 0:
        defects.append("no vertex counted: not decided")
    for name in ("not_positive_definite", "chi2_negative", "failed_events"):
        if raw[name] > 0:
            defects.append(f"{name} {raw[name]}")
    if raw["high_chi2_held_tracks"] > HIGH_CHI2_TRACKS_PREDICTED:
        defects.append(f"P16 held tracks with chi2Track above {HIGH_TRACK_CHI2:g}: {raw['high_chi2_held_tracks']}, at most {HIGH_CHI2_TRACKS_PREDICTED}")
    return defects


def vertex_prediction_defects(far: dict) -> list:
    """The predictions still enforced on far events of one stratum, P4 and P5: pull centre and width per coordinate. P1 to P3 are readings since job 7524096
    (former_prediction_readings). A defect is a disagreement with a prediction, not a gate result."""
    defects = []
    pulls = far["pulls"]
    for axis, name in enumerate(COORDINATES):
        if len(pulls) == 0:
            defects.append(f"no far pull in {name}")
            continue
        reading = refit_tests.pull_reading(pulls[:, axis])
        if abs(reading["centre"]) > PULL_CENTRE_Z * 1.03 / math.sqrt(len(pulls)):
            defects.append(f"far pull {name} centre {reading['centre']:+.4f}")
        if not PULL_WIDTH_PREDICTED[0] <= reading["width"] <= PULL_WIDTH_PREDICTED[1]:
            defects.append(f"far pull {name} width {reading['width']:.4f}, predicted inside {PULL_WIDTH_PREDICTED}")
    return defects


def frame_defects(residuals) -> list:
    """Far primaries: in the right frame every axis's rms residual is far under FRAME_LIMIT_MM. A frame with fixture u and v exchanged, or z and v, is not."""
    residuals = numpy.asarray(residuals, float).reshape(-1, 3)
    if len(residuals) == 0:
        return ["no far primary to read the frame on"]
    rms = numpy.sqrt(numpy.mean(numpy.square(residuals), axis=0))
    return [f"rms residual {name} {value:.4f} mm" for name, value in zip(COORDINATES, rms) if not value < FRAME_LIMIT_MM]


def configuration_keys_in_source(source: str) -> list:
    """The vertex configuration names, in the order track_vertexing.cpp writes them."""
    return re.findall(r'\{"(vertex_[a-z0-9_]+)", ', source)


# ---- Tests that need no build.

def track_item(key: str, hit_keys, chi2: float = 6.0) -> dict:
    return {"key": key, "ordinal": 0, "seed_planes": "1-2-3", "outcome": "selected", "failure_category": "none", "search_truncated": False, "measurements": len(hit_keys), "holes": 0,
            "search_chi2": chi2, "q_over_p": 0.25, "fit_chi2": chi2, "fit_coordinates": 2 * len(hit_keys), "hit_keys": list(hit_keys)}


def vertex_item(key: str, position, tracks, variances=(0.01, 0.0004, 0.0001)) -> dict:
    return {"key": key, "ordinal": 0, "position_mm": list(position), "covariance": [variances[0], 0.0, 0.0, variances[1], 0.0, variances[2]], "chi2": 3.0, "ndf": 4.0,
            "track_count": len(tracks), "tracks": [{"track_key": name, "weight": weight, "chi2": 1.0, "compatibility": 1.0} for name, weight in tracks]}


def tiny_event(vertices, track_count: int = 6) -> tuple:
    """Six particles of 8 hits each, three per truth vertex, each with its own selected track; truth vertices at ACTS (-100, 0, 0) and (-100, 0, 0.2)."""
    particles = [{"hit_keys": list(range(8 * index, 8 * index + 8))} for index in range(track_count)]
    found = [track_item(f"t{index}", particle["hit_keys"]) for index, particle in enumerate(particles)]
    event = {"ordinal": 0, "found": found, "vertexing": {"status": "ok", "input_tracks": track_count, "unconverted_tracks": 0, "vertex_count": len(vertices), "vertices": vertices}}
    return event, particles, [index // 3 for index in range(track_count)], [(-100.0, 0.0, 0.0), (-100.0, 0.0, 0.2)]


class SectionSevenVertexRules(unittest.TestCase):
    def test_honest_event(self):
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.0), [("t0", 1.0), ("t1", 1.0), ("t2", 1.0)]),
                                                         vertex_item("v1", (-100.0, 0.0, 0.2), [("t3", 1.0), ("t4", 1.0), ("t5", 1.0)])])
        scores = scored_vertices(event, particles, owners, positions)
        self.assertEqual((scores["reconstructable"], scores["found"], scores["unmatched"], scores["split"], scores["merged"]), (2, 2, 0, 0, 0))
        self.assertEqual((scores["assigned"], scores["wrong"]), (6, 0))
        self.assertEqual(scores["pulls"], [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])

    def test_a_match_needs_more_than_half_and_a_track_with_no_truth_match_stays_in_the_denominator(self):
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.0), [("t0", 1.0), ("t1", 1.0), ("t6", 1.0), ("t7", 1.0)])])
        fakes = [track_item("t6", [900, 901, 902, 903, 904, 905]), track_item("t7", [910, 911, 912, 913, 914, 915])]  # noise hits only: no truth match
        event["found"] += fakes
        event["vertexing"]["input_tracks"] = 8
        scores = scored_vertices(event, particles, owners, positions)
        self.assertEqual((scores["found"], scores["unmatched"]), (0, 1))  # 2 of 4 weights: exactly half, no match
        event["vertexing"]["vertices"][0]["tracks"][3]["weight"] = 0.9
        self.assertEqual(scored_vertices(event, particles, owners, positions)["found"], 1)  # 2 of 3.9

    def test_the_primary_takes_each_rule_in_order(self):
        def primary(vertices) -> int:
            event, particles, owners, positions = tiny_event(vertices)
            return scored_vertices(event, particles, owners, positions)["primaries"][0]
        three = [("t0", 1.0), ("t1", 1.0), ("t2", 1.0)]
        # highest share first, even against more tracks and a nearer position
        self.assertEqual(primary([vertex_item("v0", (-100.0, 0.0, 0.0), three + [("t3", 1.0)]), vertex_item("v1", (-100.0, 0.0, 0.5), three[:2])]), 1)
        # equal share: most tracks
        self.assertEqual(primary([vertex_item("v0", (-100.0, 0.0, 0.0), three[:2]), vertex_item("v1", (-100.0, 0.0, 0.5), three)]), 1)
        # equal share and tracks: smallest distance to truth
        self.assertEqual(primary([vertex_item("v0", (-100.0, 0.0, 0.05), three[:2]), vertex_item("v1", (-100.0, 0.0, 0.01), three[1:])]), 1)
        # all equal: lowest index
        self.assertEqual(primary([vertex_item("v0", (-100.0, 0.0, 0.01), three[:2]), vertex_item("v1", (-100.0, 0.0, 0.01), three[1:])]), 0)

    def test_two_matched_vertices_split_and_one_holding_both_merges(self):
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.0), [("t0", 1.0), ("t1", 1.0)]), vertex_item("v1", (-100.0, 0.0, 0.0), [("t2", 1.0)]),
                                                         vertex_item("v2", (-100.0, 0.0, 0.2), [("t3", 1.0), ("t4", 1.0), ("t5", 1.0)])])
        self.assertEqual(scored_vertices(event, particles, owners, positions)["split"], 1)
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.1), [(f"t{index}", 1.0) for index in range(6)])])
        scores = scored_vertices(event, particles, owners, positions)
        self.assertEqual((scores["merged"], scores["unmatched"], scores["found"]), (2, 1, 0))  # 3 of 6 each: no match, both merged

    def test_a_reconstructable_vertex_needs_three_reconstructable_tracks(self):
        event, particles, owners, positions = tiny_event([])
        particles[0]["hit_keys"] = particles[0]["hit_keys"][:5]  # five hits: not reconstructable, so vertex 0 has two
        event["found"][0] = track_item("t0", particles[0]["hit_keys"])
        self.assertEqual(scored_vertices(event, particles, owners, positions)["reconstructable"], 1)

    def test_wrong_assignment_counts_from_weight_one_half(self):
        def assignment(weight: float) -> tuple:
            event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.0), [("t0", 1.0), ("t1", 1.0), ("t2", 1.0), ("t3", weight)]),
                                                             vertex_item("v1", (-100.0, 0.0, 0.2), [("t3", 1.0 - weight), ("t4", 1.0), ("t5", 1.0)])])
            scores = scored_vertices(event, particles, owners, positions)
            return scores["assigned"], scores["wrong"]
        self.assertEqual(assignment(0.5), (6, 1))       # t3 at 0.5 in vertex 0, not its own: wrong; 0.5 in its own too
        self.assertEqual(assignment(0.4999), (6, 0))    # under 0.5 in the wrong one, 0.5001 in its own
        self.assertEqual(assignment(0.0), (6, 0))

    def test_a_non_primary_track_or_an_unmatched_vertex_never_counts(self):
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.0), [("t0", 1.0), ("t1", 1.0), ("t2", 1.0), ("d3", 1.0)]),
                                                         vertex_item("v1", (-100.0, 0.0, 0.2), [("t3", 1.0), ("t4", 1.0), ("t5", 1.0)])])
        event["found"].append(track_item("d3", particles[3]["hit_keys"][:6], chi2=60.0))  # a duplicate of particle 3: not primary (higher chi2/ndf, fewer hits)
        event["vertexing"]["input_tracks"] = 7
        self.assertEqual(scored_vertices(event, particles, owners, positions)["wrong"], 0)
        event, particles, owners, positions = tiny_event([vertex_item("v0", (-100.0, 0.0, 0.1), [(f"t{index}", 1.0) for index in range(6)])])
        self.assertEqual(scored_vertices(event, particles, owners, positions)["assigned"], 0)

    def test_near_is_event_index_mod_five(self):
        self.assertEqual([is_near(index) for index in range(11)], [True, False, False, False, False, True, False, False, False, False, True])
        self.assertEqual(near_flag_defects({"event_index": 10, "near_separation": 1}), [])
        self.assertEqual(len(near_flag_defects({"event_index": 10, "near_separation": 0})), 1)
        self.assertEqual(len(near_flag_defects({"event_index": 3, "near_separation": 1})), 1)


class FrameOfAVertex(unittest.TestCase):
    """A vertex placed at known (u, v, z) comes back in the right ACTS axes: x = z, y = u, z = v."""

    def test_a_known_vertex_reads_zero_in_the_right_axes(self):
        truth = {"u_mm": 0.03, "v_mm": 12.5, "z_mm": -100.1}
        self.assertEqual(truth_position(truth), (-100.1, 0.03, 12.5))
        event, particles, owners, _ = tiny_event([vertex_item("v0", (-100.1, 0.03, 12.5), [("t0", 1.0), ("t1", 1.0), ("t2", 1.0)])])
        scores = scored_vertices(event, particles, owners, [truth_position(truth), (-100.0, 0.0, 30.0)])
        self.assertEqual(scores["residuals"], [[0.0, 0.0, 0.0]])
        self.assertEqual(frame_defects(scores["residuals"]), [])

    def test_a_frame_with_two_axes_exchanged_fails(self):
        truth = {"u_mm": 0.03, "v_mm": 12.5, "z_mm": -100.1}
        for swapped in ((truth["z_mm"], truth["v_mm"], truth["u_mm"]), (truth["v_mm"], truth["u_mm"], truth["z_mm"])):
            with self.subTest(swapped=swapped):
                event, particles, owners, _ = tiny_event([vertex_item("v0", (-100.1, 0.03, 12.5), [("t0", 1.0), ("t1", 1.0), ("t2", 1.0)])])
                scores = scored_vertices(event, particles, owners, [swapped, (-100.0, 0.0, 30.0)])
                self.assertTrue(frame_defects(scores["residuals"]))

    def test_the_reference_line_is_section_4_1s_nominal_along_acts_z(self):
        header = (NATIVE / "track_vertexing.hpp").read_text(encoding="utf-8")
        self.assertEqual([finding_tests.header_constant(header, name) for name in ("vertex_reference_x_mm", "vertex_reference_y_mm", "vertex_reference_z_mm")], [-100.0, 0.0, 0.0])


def honest_vertex_record() -> dict:
    document = finding_tests.honest_record()
    document["header"].update(vertex_recipe=finding_record.VERTEX_RECIPE)
    document["vertex_configuration"] = {name: "1" for name in finding_record.VERTEX_CONFIGURATION_KEYS}
    document["header"]["vertex_configuration_sha256"] = finding_record.vertex_configuration_sha256(document["vertex_configuration"])
    vertex = vertex_item("event-0-vertex-0", (-100.0, 0.001, 3.25), [("event-0-candidate-0", 0.75)])
    document["events"][0]["vertexing"] = {"status": "ok", "input_tracks": 1, "unconverted_tracks": 0, "vertex_count": 1, "vertices": [vertex]}
    return document


class VertexRecordFailsOnOneDefect(unittest.TestCase):
    """Section 8.3 of the plan: the driver's own format survives a round trip; the old version still reads where earlier jobs' records are compared."""

    def setUp(self):
        self.document = honest_vertex_record()
        self.text = finding_record.format_record(self.document)

    def refused(self, text: str) -> None:
        with self.assertRaises(finding_record.RecordFormatError):
            finding_record.parse_record(text)

    def test_round_trip(self):
        self.assertTrue(self.text.startswith(finding_record.VERTEX_RECORD_FORMAT + "\n"))
        parsed = finding_record.parse_record(self.text)
        self.assertEqual(finding_record.format_record(parsed), self.text)
        self.assertEqual(parsed["events"][0]["vertexing"]["vertices"][0]["tracks"][0]["weight"], 0.75)
        self.assertEqual(vertex_step_defects(self.text), [])

    def test_the_old_version_still_reads_and_the_track_lines_are_its_bytes(self):
        old = finding_record.format_record(finding_tests.honest_record())
        self.assertTrue(old.startswith(finding_record.RECORD_FORMAT + "\n"))
        self.assertEqual(len(finding_record.parse_record(old)["events"]), 1)
        self.assertEqual(finding_record.finding_lines_of(self.text), old)
        self.assertEqual(finding_record.finding_lines_of(old), old)

    def test_the_vertex_step_asked_for_and_absent_fails(self):
        old = finding_record.format_record(finding_tests.honest_record())
        self.assertEqual(len(vertex_step_defects(old)), 1)
        without_line = "\n".join(line for line in self.text.split("\n") if not line.startswith(("vertexing ", "vertex ", "vertex-track "))).replace("end 1 2 1", "end 1 2 0")
        self.assertEqual(len(vertex_step_defects(without_line)), 1)

    def test_a_dropped_or_foreign_vertex_or_track_is_refused(self):
        self.refused(self.text.replace("end 1 2 1", "end 1 2 2"))
        self.refused("\n".join(line for line in self.text.split("\n") if not line.startswith("vertex-track ")))  # the vertex counts a track it lacks
        self.refused(self.text.replace("vertex-track event-0-vertex-0 event-0-candidate-0", "vertex-track event-0-vertex-0 event-0-candidate-1"))  # an evicted candidate
        self.refused(self.text.replace("vertexing 0 ok 1 0 1", "vertexing 0 ok 2 0 1"))  # hands over more tracks than were delivered
        self.refused(self.text.replace("vertexing 0 ok", "vertexing 0 failed"))  # a failed event keeps a vertex

    def test_a_vertex_configuration_out_of_its_hash_or_keys_is_refused(self):
        self.refused(self.text.replace("vertex_configuration vertex_finder_max_vertex_chi2 1", "vertex_configuration vertex_finder_max_vertex_chi2 2"))
        self.refused("\n".join(line for line in self.text.split("\n") if "vertex_finder_do_full_splitting" not in line))
        self.refused(self.text.replace(f"vertex_recipe {finding_record.VERTEX_RECIPE}", "vertex_recipe reco.vertex.other/1"))

    def test_the_source_writes_the_keys_the_reader_reads_in_its_order(self):
        source = (NATIVE / "track_vertexing.cpp").read_text(encoding="utf-8")
        self.assertEqual(configuration_keys_in_source(source), list(finding_record.VERTEX_CONFIGURATION_KEYS))


class VertexingStaysDataSide(unittest.TestCase):
    """Section 3.1: the vertex step reads the finder's fits and nothing of truth, a generator or seed code; only the finder compiles it."""

    def test_no_truth_name_in_the_vertexing_sources(self):
        text = (NATIVE / "track_vertexing.cpp").read_text(encoding="utf-8") + (NATIVE / "track_vertexing.hpp").read_text(encoding="utf-8")
        for word in ("truth_file", "t07_seed_stream", "t07_event_generator", "generation_constants", "t07_cai", "find_from_starts", "PlaneStart"):
            self.assertNotIn(word, text)
        cmake = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")
        compiled_by = [name for name, sources in re.findall(r"add_executable\((\w+) ([^)]*)\)", cmake) if "track_vertexing.cpp" in sources.split()]
        self.assertEqual(compiled_by, ["acts_tracking_finder"])

    def test_the_fitter_is_the_one_the_finder_header_fixes(self):
        """AdaptiveMultiVertexFinder.hpp: "using VertexFitter = AdaptiveMultiVertexFitter;". The sheet's FullBilloirVertexFitter is not used (D1 stage 7 report)."""
        source = (NATIVE / "track_vertexing.cpp").read_text(encoding="utf-8")
        self.assertIn("Acts::AdaptiveMultiVertexFitter fitter(", source)
        self.assertNotIn("FullBilloir", source)
        self.assertIn("machinery.reference_point, false)", source)  # useConstraintInFit false: no beam constraint in any fit (section 4.1)


class PredictionsCanDisagree(unittest.TestCase):
    def far(self, **changes) -> dict:
        generator = numpy.random.default_rng(7)
        tally = Counter({"reconstructable": 4800, "found": 4800, "assigned": 14400, "wrong": 3, "unmatched": 0, "split": 0, "merged": 0})
        tally.update(changes)
        return {"tally": tally, "events": 2400, "pulls": generator.standard_normal((4800, 3)), "residuals": numpy.zeros((4800, 3))}

    def test_each_defect_is_named(self):
        self.assertEqual(vertex_prediction_defects(self.far()), [])
        # P1, P2 and P3 are readings since job 7524096: past their old limits they fail nothing, and the reading says outside.
        for changes in ({"found": -30}, {"wrong": 40}, {"merged": 6}):
            with self.subTest(changes=changes):
                self.assertEqual(vertex_prediction_defects(self.far(**changes)), [])
                self.assertEqual(sum(text.endswith("outside") for text in former_prediction_readings(self.far(**changes), Counter(vertices=5000))), 1)
        wide = self.far()
        wide["pulls"] = wide["pulls"] * numpy.array([1.0, 1.3, 1.0])
        self.assertEqual(len(vertex_prediction_defects(wide)), 1)
        shifted = self.far()
        shifted["pulls"] = shifted["pulls"] + numpy.array([0.0, 0.0, 0.1])
        self.assertEqual(len(vertex_prediction_defects(shifted)), 1)

    def test_a_stratum_like_job_7524096s_o1_passes_and_a_bad_vertex_still_fails(self):
        """The user's choice after job 7524096: noise stratum 0 read efficiency 0.985405 (4,726 of 4,796), wrong assignment 72 of 14,165, merged 78, 5,405 vertices and a pull width
        near 1. Its former predictions are outside and fail nothing; one vertex not positive definite, one chi2 below zero, one failed event or P16 past its limit still fail."""
        generator = numpy.random.default_rng(11)
        far = {"tally": Counter({"reconstructable": 4796, "found": 4726, "assigned": 14165, "wrong": 72, "unmatched": 0, "split": 0, "merged": 78}), "events": 2400,
               "pulls": generator.standard_normal((4730, 3)), "residuals": numpy.zeros((4730, 3))}
        raw = Counter({"vertices": 5405, "large_variance": 6, "high_chi2_held_tracks": 0})  # 6 > 5.405: P15 outside too
        self.assertEqual(stratum_check_defects(raw) + vertex_prediction_defects(far), [])
        self.assertEqual(sum(text.endswith("outside") for text in former_prediction_readings(far, raw)), 4)  # P1, P2, P3 merged, P15
        for bad in ({"not_positive_definite": 1}, {"chi2_negative": 1}, {"failed_events": 1}, {"high_chi2_held_tracks": 6}, {"vertices": -5405}):
            with self.subTest(bad=bad):
                worse = raw.copy()
                worse.update(bad)
                self.assertEqual(len(stratum_check_defects(worse)), 1)
        self.assertEqual(len(vertex_step_defects(self.non_positive_definite_record())), 1)  # and the reader refuses such a record

    def non_positive_definite_record(self) -> str:
        document = honest_vertex_record()
        vertex = document["events"][0]["vertexing"]["vertices"][0]
        vertex["covariance"] = [1.0, 2.0, 0.0, 1.0, 0.0, 1.0]
        return finding_record.format_record(document)

    def test_the_efficiency_bound_is_the_efficiency_readings_bound(self):
        reconstructable = numpy.full(2400, 2)
        found = reconstructable.copy()
        found[::100] = 1  # 24 lost of 4,800
        efficiency, bound, percentile = efficiency_with_bound(found, reconstructable, (7001, 1, 0))
        self.assertAlmostEqual(efficiency, 1.0 - 24 / 4800)
        self.assertEqual((efficiency, bound, percentile), (efficiency, *paired_difference(found.astype(float), numpy.zeros(2400), reconstructable, (7001, 1, 0))[1:]))
        self.assertLess(bound, efficiency)
        self.assertAlmostEqual(bound, efficiency - 1.645 * math.sqrt(24 * (1 - 1 / 100)) / 4800, delta=0.2e-3)


class BadVerticesAreAllCounted(unittest.TestCase):
    """D1 stage 7b: every bad vertex of a stratum is counted before the reader refuses the first; a positive diagonal is not positive definiteness."""

    def test_counts_and_refusal(self):
        document = honest_vertex_record()
        first = document["events"][0]["vertexing"]["vertices"][0]
        second = dict(first, key="event-0-vertex-1", covariance=[1.0, 2.0, 0.0, 1.0, 0.0, 1.0], chi2=-0.5)  # positive diagonal, indefinite
        third = dict(first, key="event-0-vertex-2", covariance=[1.0, 0.0, 0.0, -1.0, 0.0, 1.0])
        document["events"][0]["vertexing"].update(vertices=[first, second, third], vertex_count=3)
        text = finding_record.format_record(document)
        counts = raw_vertex_counts(text)
        self.assertEqual((counts["vertices"], counts["not_positive_definite"], counts["chi2_negative"], counts["failed_events"]), (3, 2, 1, 0))
        self.assertEqual(len(vertex_step_defects(text)), 1)
        self.assertEqual(vertex_configuration_of(text)[0], document["header"]["vertex_configuration_sha256"])
        self.assertEqual(len(vertex_configuration_of(text)[1]), len(finding_record.VERTEX_CONFIGURATION_KEYS))
        self.assertTrue(finding_record.covariance_is_positive_definite(first["covariance"]))
        self.assertFalse(finding_record.covariance_is_positive_definite(second["covariance"]))

    def test_the_prior_readings_are_counted(self):
        document = honest_vertex_record()
        first = document["events"][0]["vertexing"]["vertices"][0]
        wide = dict(first, key="event-0-vertex-1", covariance=[9.7e3, 0.0, 0.0, 0.0004, 0.0, 0.0001],
                    tracks=[{"track_key": "event-0-candidate-0", "weight": 0.98, "chi2": 12148.0, "compatibility": 1.0}])
        document["events"][0]["vertexing"].update(vertices=[first, wide], vertex_count=2)
        counts = raw_vertex_counts(finding_record.format_record(document))
        self.assertEqual((counts["large_variance"], counts["high_chi2_held_tracks"], counts["not_positive_definite"]), (1, 1, 0))
        wide["tracks"][0]["weight"] = 0.4  # not held: not counted
        self.assertEqual(raw_vertex_counts(finding_record.format_record(document))["high_chi2_held_tracks"], 0)

    def test_failure_messages_are_counted_by_message(self):
        stderr = "vertexing event 3 failed: Seed vertex not found\nother line\nvertexing event 9 failed: Seed vertex not found\nvertexing event 11 failed: exception: x\n"
        self.assertEqual(failure_messages(stderr), Counter({"Seed vertex not found": 2, "exception: x": 1}))

    def test_the_prior_is_the_stage_7b_value(self):
        header = (NATIVE / "track_vertexing.hpp").read_text(encoding="utf-8")
        self.assertEqual(finding_tests.header_constant(header, "vertex_initial_variance"), 1e4)
        self.assertIn("finder_config.initialVariances = Acts::Vector4::Constant(vertex_initial_variance);", (NATIVE / "track_vertexing.cpp").read_text(encoding="utf-8"))


class CostLinesPair(unittest.TestCase):
    def test_the_finding_cost_of_a_stratum_is_read_from_its_line(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "finding.log"
            log.write_text("FINDING-COST clean stratum 2 events 3000 generate_seconds 1.0 find_seconds 13.3 stderr_bytes 0\nFINDING-READING x\n", encoding="utf-8")
            self.assertEqual(finding_costs(log), {("clean", 2): 13.3})
            self.assertEqual(finding_costs(Path(folder) / "absent.log"), {})


# ---- The built tests.

def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


LARGE_VARIANCE_MM2 = 1.0  # a vertex with any variance above this is reported: at 1e4 a prior-dominated axis comes back positive definite (D1 stage 7b review m3)
HIGH_TRACK_CHI2, HELD_WEIGHT = 100.0, 0.5  # a track held at weight above 0.5 with chi2Track above 100 is reported (d1-stage7-reading.md section 5, item 2)
BAD_COUNTS = ("not_positive_definite", "chi2_negative", "failed_events")  # a stratum with any of these keeps its record (review M1)


def raw_vertex_counts(text: str) -> Counter:
    """D1 stage 7b: every bad vertex of a /2 record, counted from its lines before the reader refuses the first: covariances that are not positive definite, chi2 below
    zero, failed events; and, as readings with no gate (review m3), vertices with any variance above LARGE_VARIANCE_MM2 and tracks with chi2Track above HIGH_TRACK_CHI2 at
    weight above HELD_WEIGHT. The reader's refusal stands."""
    counts = Counter()
    for line in text.splitlines():
        tokens = line.split(" ")
        if tokens[0] == "vertex" and len(tokens) == 15:
            covariance = [float(token) for token in tokens[6:12]]
            counts["vertices"] += 1
            counts["not_positive_definite"] += int(not finding_record.covariance_is_positive_definite(covariance))
            counts["chi2_negative"] += int(float(tokens[12]) < 0.0)
            counts["large_variance"] += int(max(covariance[0], covariance[3], covariance[5]) > LARGE_VARIANCE_MM2)
        elif tokens[0] == "vertex-track" and len(tokens) == 6:
            counts["high_chi2_held_tracks"] += int(float(tokens[4]) > HIGH_TRACK_CHI2 and float(tokens[3]) > HELD_WEIGHT)
        elif tokens[0] == "vertexing" and len(tokens) == 6:
            counts["failed_events"] += int(tokens[2] == "failed")
    return counts


def vertex_configuration_of(text: str) -> tuple:
    """The vertex configuration hash and lines from a /2 record's header, whether the reader accepts the record or not (review n3)."""
    sha256, configuration = None, {}
    for line in text.splitlines():
        tokens = line.split(" ")
        if tokens[0] == "vertex_configuration_sha256" and len(tokens) == 2:
            sha256 = tokens[1]
        elif tokens[0] == "vertex_configuration" and len(tokens) == 3:
            configuration[tokens[1]] = tokens[2]
        elif tokens[0] == "event":
            break
    return sha256, configuration


def failure_messages(stderr: str) -> Counter:
    """D1 stage 7b: the finder's line per failed event, "vertexing event N failed: <ACTS's message>", counted by message. A message of several lines is counted by its first;
    the whole stderr stays in its file (review n4)."""
    return Counter(found.group(1) for found in re.finditer(r"^vertexing event \d+ failed: (.*)$", stderr, re.MULTILINE))


def stratum_vertex_reading(fixture: str, stratum: int, folder: Path) -> dict:
    """Generate, find with the vertex step, score tracks and vertices. The data and truth files are deleted whatever happens, and every record but a diagnosis stratum's (kept
    under the name job 7502411 used); the finder's stderr stays beside them. A stratum that fails returns its error and its bad-vertex counts rather than raising, so every
    stratum runs and is read (D1 stage 7b: job 7522969 left 4.0 GB behind and never ran four strata)."""
    diagnosis = (fixture, stratum) in diagnosis_tests.CASES
    name = f"diagnosis-{fixture}-{stratum}-recipe" if diagnosis else f"t07-dev-vertex-{fixture}-{stratum}"
    reading = {"fixture": fixture, "stratum": stratum, "error": None, "raw": Counter(), "failures": Counter(), "tracks_equal": None, "raw_configuration": (None, {}),
               "record_kept": False}
    # The names finding_tests.generate writes, fixed before the call, so a generator that fails after writing leaves nothing behind (review n2).
    data_file, truth_file = folder / f"{fixture}-{stratum}.t07data", folder / f"{fixture}-{stratum}.t07truth"
    record_file = folder / f"{name}.record"
    stderr_file = folder / f"{name}.stderr"
    try:
        started = time.monotonic()
        data_file, truth_file = finding_tests.generate(folder, fixture, stratum, finding_tests.EVENTS_PER_BIN)
        generated = time.monotonic()
        product_file = folder / f"{name}.product"
        finished = finding_tests.run_program([finding_tests.FINDER, "--data-file", data_file, "--product-id", name, "--product-file", product_file, "--record-file", record_file,
                                              "--product-events", 0, "--vertex-recipe", finding_record.VERTEX_RECIPE], check=False)
        searched = time.monotonic()
        product_file.unlink(missing_ok=True)
        stderr_file.write_text(finished.stderr, encoding="utf-8")
        reading.update(failures=failure_messages(finished.stderr), stderr_bytes=len(finished.stderr), generate_seconds=generated - started, search_seconds=searched - generated)
        if finished.returncode != 0:
            reading["error"] = f"the finder exited {finished.returncode}: {finished.stderr[-400:]!r}"
            return reading
        text = record_file.read_text(encoding="utf-8")
        reading["raw"] = raw_vertex_counts(text)
        reading["raw_configuration"] = vertex_configuration_of(text)
        step_defects = vertex_step_defects(text)
        if step_defects:  # review n4: name the defect, rather than a traceback from the reader
            reading["error"] = step_defects[0]
            return reading
        record = finding_record.parse_record(text)
        if diagnosis:
            kept = Path(KEPT_RECORDS) / f"{name}.record"
            reading["tracks_equal"] = hashlib.sha256(finding_record.finding_lines_of(text).encode("utf-8")).hexdigest() == file_sha256(kept)
        if truth_files.read_truth_header(truth_file)["event_count"] != len(record["events"]):
            reading["error"] = "the record does not hold every event"
            return reading
        tally, status, near_defects = Counter(), Counter(), []
        scored = {"far": [], "near": []}
        per_event = {"found": [], "reconstructable": []}
        for event, truth_event in zip(record["events"], truth_files.iter_truth_events(truth_file)):
            particles = finding_tests.particles_of(truth_event)
            scores = finding_tests.scored_event(finding_tests.tracks_of(event), particles)
            tally.update({key: scores[key] for key in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates")})
            near_defects += near_flag_defects(truth_event)
            vertexing = event["vertexing"]
            status.update({"failed": int(vertexing["status"] != "ok"), "input_tracks": vertexing["input_tracks"], "unconverted_tracks": vertexing["unconverted_tracks"],
                           "off_line_vertices": sum(abs(vertex["position_mm"][0] - VERTEX_REFERENCE_X_MM) > OFF_LINE_MM for vertex in vertexing["vertices"])})
            vertex_of_particle = [int(track["vertex_index"]) for track in truth_event["tracks"]]
            positions = [truth_position(vertex) for vertex in truth_event["vertices"]]
            item = scored_vertices(event, particles, vertex_of_particle, positions)
            population = "near" if is_near(truth_event["event_index"]) else "far"
            scored[population].append(item)
            if population == "far":
                per_event["found"].append(item["found"])
                per_event["reconstructable"].append(item["reconstructable"])
        fixture_id = finding_tests.FIXTURE_IDS[fixture]
        reading.update({"events": len(record["events"]), "tally": tally, "status": status, "far": stratum_vertex_tally(scored["far"]), "near": stratum_vertex_tally(scored["near"]),
                        "efficiency": efficiency_with_bound(per_event["found"], per_event["reconstructable"], (fixture_id, finding_tests.TUNING_BLOCK, stratum)),
                        "near_defects": near_defects, "vertex_configuration": record["vertex_configuration"],
                        "vertex_configuration_sha256": record["header"]["vertex_configuration_sha256"], "configuration_sha256": record["header"]["configuration_sha256"]})
    except Exception as error:  # every stratum is read; the error is reported with the stratum
        reading["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, subprocess.TimeoutExpired) and error.stderr:  # review n4: the stderr of a finder that timed out is kept too
            stderr_file.write_text(error.stderr if isinstance(error.stderr, str) else error.stderr.decode("utf-8", "replace"), encoding="utf-8")
    finally:
        # Data and truth are regenerable and go on every path. A record stays for a diagnosis stratum, and for a stratum that erred or holds a bad vertex or a failed event,
        # or one beyond P15's or P16's limit (stage 7b re-review m-new-1), so a refutation can be read from its record without another job (review M1); at most about 0.4 GB
        # for all 24 records, the five diagnosis records included, and nothing beyond those five on a clean pass.
        raw = reading["raw"]
        reading["record_kept"] = (diagnosis or reading["error"] is not None or any(raw[key] > 0 for key in BAD_COUNTS)
                                  or raw["large_variance"] > LARGE_VARIANCE_SHARE_PREDICTED * raw["vertices"] or raw["high_chi2_held_tracks"] > HIGH_CHI2_TRACKS_PREDICTED)
        for path in (data_file, truth_file) + (() if reading["record_kept"] else (record_file,)):
            path.unlink(missing_ok=True)
    return reading


def product_with_and_without_vertexing(folder: Path) -> dict:
    """Review m1: one stratum, the finder with and without the vertex step, product bytes compared. The product is written from the fits after the vertex step has read them."""
    fixture, stratum, events = PRODUCT_CHECK
    name = f"t07-dev-vertex-product-{fixture}-{stratum}"
    created = []
    try:
        data_file, truth_file = finding_tests.generate(folder, fixture, stratum, events)
        created += [data_file, truth_file]
        products = {}
        for label, extra in (("without", []), ("with", ["--vertex-recipe", finding_record.VERTEX_RECIPE])):
            record_file, product_file = folder / f"{name}-{label}.record", folder / f"{name}-{label}.product"
            created += [record_file, product_file]
            finding_tests.run_program([finding_tests.FINDER, "--data-file", data_file, "--product-id", name, "--product-file", product_file, "--record-file", record_file,
                                       "--product-events", events] + extra)
            products[label] = product_file.read_bytes()
        return {"equal": products["with"] == products["without"], "bytes": len(products["without"]), "tracks": products["without"].count(b"\ntrack "), "error": None}
    except Exception as error:
        return {"equal": False, "bytes": 0, "tracks": 0, "error": f"{type(error).__name__}: {error}"}
    finally:
        for path in created:
            path.unlink(missing_ok=True)


def finding_costs(path: Path) -> dict:
    """This job's FINDING-COST find_seconds per stratum, without the vertex step, from the finding step's log (review m4): the vertex step's cost is the difference."""
    costs = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            found = re.match(r"FINDING-COST (\w+) stratum (\d+) events \d+ generate_seconds [0-9.]+ find_seconds ([0-9.]+)", line)
            if found:
                costs[(found.group(1), int(found.group(2)))] = float(found.group(3))
    return costs


def population_line(item: dict, population: str) -> str:
    reading = item[population]
    tally = reading["tally"]
    efficiency = tally["found"] / tally["reconstructable"] if tally["reconstructable"] else float("nan")
    rate = tally["wrong"] / tally["assigned"] if tally["assigned"] else float("nan")
    return (f"{item['fixture']} stratum {item['stratum']} {population} events {reading['events']} truth_vertices {tally['truth_vertices']} reconstructable {tally['reconstructable']} "
            f"found {tally['found']} efficiency {efficiency:.6f} wrong_assignment {tally['wrong']} of {tally['assigned']} rate {rate:.6f} vertices {tally['vertices']} "
            f"unmatched {tally['unmatched']} split {tally['split']} merged {tally['merged']}")


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class VertexDevelopmentRun(unittest.TestCase):
    """Both fixtures, every stratum, block 1, with the vertex step. Readings printed; a test here fails on a broken record, a moved track or a disagreement with a prediction."""

    @classmethod
    def setUpClass(cls):
        folder = Path(EVIDENCE_DIR) / VERTEX_DIR
        folder.mkdir(parents=True, exist_ok=True)
        jobs = [(fixture, stratum) for fixture in ("noise", "clean") for stratum in (11, 8, 5, 2, 10, 7, 4, 1, 9, 6, 3, 0)]  # slowest first
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            cls.readings = sorted(pool.map(lambda job: stratum_vertex_reading(job[0], job[1], folder), jobs), key=lambda item: (item["fixture"], item["stratum"]))
        cls.read = [item for item in cls.readings if item["error"] is None]
        cls.product_check = product_with_and_without_vertexing(folder)
        print(f"VERTEX-PRODUCT {PRODUCT_CHECK[0]} stratum {PRODUCT_CHECK[1]} events {PRODUCT_CHECK[2]} product-events {PRODUCT_CHECK[2]}: product with and without --vertex-recipe "
              f"{'equal' if cls.product_check['equal'] else 'DIFFERENT'}, {cls.product_check['bytes']} bytes, {cls.product_check['tracks']} tracks"
              + (f"; error {cls.product_check['error']}" if cls.product_check["error"] else ""), flush=True)
        costs = finding_costs(Path(EVIDENCE_DIR) / "finding.log")
        # From the first record's header, read or refused (review n3).
        configured = next((item["raw_configuration"] for item in cls.readings if item["raw_configuration"][0] is not None), (None, {}))
        print(f"VERTEX-CONFIGURATION sha256 {configured[0]}", flush=True)
        for name, value in configured[1].items():
            print(f"VERTEX-CONFIGURATION {name} {value}", flush=True)
        for item in cls.readings:
            raw = item["raw"]
            # Every stratum, read or refused (D1 stage 7b): its bad vertices, failed events and ACTS's messages.
            print(f"VERTEX-BAD {item['fixture']} stratum {item['stratum']} vertices {raw['vertices']} not_positive_definite {raw['not_positive_definite']} chi2_negative "
                  f"{raw['chi2_negative']} failed_events {raw['failed_events']} failure_messages {dict(item['failures'].most_common())}; readings, no section 8 gate (P15 {REFUTED_IN}, P16 enforced as a prediction): "
                  f"variance_above_{LARGE_VARIANCE_MM2:g}_mm2 {raw['large_variance']} tracks_chi2_above_{HIGH_TRACK_CHI2:g}_at_weight_above_{HELD_WEIGHT:g} {raw['high_chi2_held_tracks']}; "
                  f"record_kept {int(item['record_kept'])}", flush=True)
            if item["error"] is not None:
                print(f"VERTEX-ERROR {item['fixture']} stratum {item['stratum']}: {item['error']}", flush=True)
                continue
            tally = item["tally"]
            # The same text as test_acts_finding's FINDING-READING line, so the build job compares it with job 7502411's.
            print(f"VERTEX-TRACKS-READING development reading, not a gate (K09): {item['fixture']} stratum {item['stratum']} events {item['events']} reconstructable {tally['reconstructable']} "
                  f"with_primary {tally['with_primary']} efficiency {tally['with_primary'] / tally['reconstructable']:.6f} reconstructed {tally['reconstructed']} fakes {tally['fakes']} "
                  f"matched {tally['matched']} duplicates {tally['duplicates']}", flush=True)
            efficiency, bound, percentile = item["efficiency"]
            print(f"VERTEX-READING development reading, not a gate (K09): {population_line(item, 'far')}; lower bound (estimate - 1.645 se, event bootstrap B "
                  f"{BOOTSTRAP_REPLICATES}) {bound:.6f}, 5 % percentile, reading only, {percentile:.6f}; section 8.5 floor {VERTEX_FLOOR}: "
                  f"{'at or above' if bound >= VERTEX_FLOOR else 'below'}; former predictions, {REFUTED_IN}: {'; '.join(former_prediction_readings(item['far'], item['raw']))}", flush=True)
            print(f"VERTEX-NEAR reported, not gated (section 8.4): {population_line(item, 'near')}", flush=True)
            for population in ("far", "near"):
                pulls = item[population]["pulls"]
                for axis, name in enumerate(COORDINATES):
                    if len(pulls) == 0:
                        print(f"VERTEX-PULL {item['fixture']} stratum {item['stratum']} {population} {name} count 0", flush=True)
                        continue
                    pull = refit_tests.pull_reading(pulls[:, axis])
                    print(f"VERTEX-PULL {item['fixture']} stratum {item['stratum']} {population} {name} count {pull['count']} centre {pull['centre']:+.4f} width {pull['width']:.4f} "
                          f"mean {pull['mean']:+.4f} rms {pull['rms']:.4f} tail {pull['tail']:.5f}", flush=True)
            residuals = item["far"]["residuals"]
            rms = numpy.sqrt(numpy.mean(numpy.square(residuals), axis=0)) if len(residuals) else [float("nan")] * 3
            print(f"VERTEX-FRAME {item['fixture']} stratum {item['stratum']} far primaries {len(residuals)} rms residual mm x {rms[0]:.5f} y {rms[1]:.5f} z {rms[2]:.5f}", flush=True)
            status = item["status"]
            print(f"VERTEX-STATUS {item['fixture']} stratum {item['stratum']} failed_events {status['failed']} input_tracks {status['input_tracks']} unconverted_tracks {status['unconverted_tracks']} "
                  f"tracks_equal_job_7502411 {'n/a' if item['tracks_equal'] is None else int(item['tracks_equal'])} off_line_vertices {status['off_line_vertices']} "
                  f"(|x + 100| > {OFF_LINE_MM:g} mm)", flush=True)
            without = costs.get((item["fixture"], item["stratum"]))
            print(f"VERTEX-COST {item['fixture']} stratum {item['stratum']} events {item['events']} generate_seconds {item['generate_seconds']:.1f} find_seconds {item['search_seconds']:.1f} "
                  f"stderr_bytes {item['stderr_bytes']}; FINDING-COST find_seconds without the vertex step, this job {'n/a' if without is None else f'{without:.1f}'}", flush=True)

    def read_items(self) -> list:
        """Each stratum read; a refused or failed stratum fails here, by name, and is left out of the readings below."""
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertIsNone(item["error"])
        return self.read

    def test_every_stratum_ran_under_one_configuration_and_wrote_its_vertex_step(self):
        self.assertEqual(len(self.readings), 24)
        read = self.read_items()
        self.assertEqual({item["events"] for item in read}, {finding_tests.EVENTS_PER_BIN})
        self.assertEqual({item["configuration_sha256"] for item in read}, {diagnosis_tests.RECIPE_CONFIGURATION_SHA256})
        self.assertEqual(len({item["vertex_configuration_sha256"] for item in read}), 1)
        for item in read:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(item["near_defects"], [])
                self.assertEqual(item["vertex_configuration"]["vertex_finder_initial_variances"], "10000,10000,10000,10000")  # D1 stage 7b
                self.assertEqual(item["far"]["tally"]["truth_vertices"] + item["near"]["tally"]["truth_vertices"], VERTICES_OF_LEVEL[item["stratum"] % 3] * item["events"])

    def test_no_vertex_is_bad(self):
        """Enforced: vertices in every stratum (a stratum with no counts is not decided, review m2), no covariance that is not positive definite, no chi2 below zero, no failed
        event, P16; counted in every stratum, refused or not. P15 is a reading since job 7524096 (VERTEX-BAD prints it)."""
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(stratum_check_defects(item["raw"]), [])

    def test_the_vertex_step_moved_no_track(self):
        """The /2 record of each diagnosis stratum, its vertex lines left out, is job 7502411's /1 record byte for byte."""
        checked = [item for item in self.read_items() if item["tracks_equal"] is not None]
        self.assertEqual(len(checked), len(diagnosis_tests.CASES))
        for item in checked:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertTrue(item["tracks_equal"])

    def test_the_vertex_step_leaves_the_product_alone(self):
        """Review m1: the product, written from the fits the vertex step read, is the same bytes with and without it."""
        self.assertIsNone(self.product_check["error"])
        self.assertGreater(self.product_check["tracks"], 0)
        self.assertTrue(self.product_check["equal"])

    def test_no_event_failed_and_every_track_reached_the_reference_line(self):
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(item["raw"]["failed_events"], 0, dict(item["failures"]))
        for item in self.read_items():
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual((item["status"]["failed"], item["status"]["unconverted_tracks"]), (0, 0))
                self.assertEqual(item["status"]["input_tracks"], item["tally"]["reconstructed"])

    def test_the_frame(self):
        for item in self.read_items():
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(frame_defects(item["far"]["residuals"]), [])

    def test_readings_against_the_predictions(self):
        for item in self.read_items():
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(vertex_prediction_defects(item["far"]), [])


if __name__ == "__main__":
    unittest.main()
