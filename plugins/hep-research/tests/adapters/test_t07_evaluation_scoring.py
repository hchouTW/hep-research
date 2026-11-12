"""D4 stage E6b: T07 scoring of the evaluation harness (d4-e6b-brief.md; freeze-b-proposal.md section 4, row E6).

The scoring is tests/adapters/t07_evaluation_scoring.py, scoring side, on E6a's core and layout. Sections cited are of t04-values-v4.md (Freeze A).
Every test here runs on hand-made inputs: hand-written truth files, finding records and products in their own formats, fixed counts, and the kept
negative-case folder; no draw of any fixture, no Monte Carlo, no program of the build. Expectations, fixed before the first run
(d4-e6b-report.md, "Predictions"): each definition of v4 7 holds at its boundary; every gate's record equals the core's own call on the same
inputs; the count is v4 5.3's 1,260 in its composition.

Run from the plugin root: python -m unittest tests.adapters.test_t07_evaluation_scoring -v
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.adapters import t07_evaluation_scoring as scoring  # noqa: E402
from tests.adapters import test_acts_finding as finding_tests  # noqa: E402
from tests.adapters import test_acts_refit_field as refit_tests  # noqa: E402
import acts_finding_record as finding_record  # noqa: E402
import acts_native_product as native_product  # noqa: E402
import t07_fake_rate as fake_rate  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402

KEPT_NEGATIVE_CASES = ROOT / "tests" / "adapters" / "data" / "t07-negative-cases"


# ---- Hand-made files in the formats the recipe and the generator write.

def particle(hit_keys, *, charge=1, q_over_p=0.25, slope_u=0.01, vertex_index=0, crossing=(1.0, 2.0, 0.01, 1.5), key=None):
    return {"hit_keys": list(hit_keys), "charge": charge, "q_over_p": q_over_p, "slope_u": slope_u, "vertex_index": vertex_index, "crossing": crossing, "key": key}


def truth_file_bytes(events, *, fixture_id=7001, block=1, stratum=0, data_sha256="ab" * 32) -> bytes:
    """A t07 truth file (t07_truth_files layouts). events: {"event_index", "vertices": [(u, v, z)], "particles": [particle(...)]}."""
    header = numpy.zeros(1, dtype=truth_files.TRUTH_HEADER)
    header["magic"], header["role"], header["generator"] = truth_files.TRUTH_MAGIC, truth_files.TRUTH_ROLE.encode(), b"t07-telescope-clean/1"
    header["fixture_id"], header["block"], header["stratum"], header["event_count"] = fixture_id, block, stratum, len(events)
    header["sigma_loc0_mm"] = header["sigma_loc1_mm"] = 0.02
    header["data_sha256"] = bytes.fromhex(data_sha256)
    pieces = [header.tobytes()]
    for event in events:
        head = numpy.zeros(1, dtype=truth_files.TRUTH_EVENT)
        head["event_index"], head["momentum_bin"], head["occupancy_level"] = event["event_index"], stratum // 3, stratum % 3
        head["near_separation"] = int(event["event_index"] % 5 == 0)
        head["vertex_count"], head["track_count"] = len(event["vertices"]), len(event["particles"])
        vertices = numpy.zeros(len(event["vertices"]), dtype=truth_files.VERTEX)
        for row, (u, v, z) in enumerate(event["vertices"]):
            vertices[row] = (u, v, z)
        tracks = numpy.zeros(len(event["particles"]), dtype=truth_files.TRACK)
        for row, item in enumerate(event["particles"]):
            keys = item["hit_keys"] + [truth_files.NO_HIT_KEY] * (8 - len(item["hit_keys"]))
            crossings = numpy.zeros((8, 4))
            crossings[0] = item["crossing"]
            tracks[row] = (row if item["key"] is None else item["key"], item["vertex_index"], item["charge"], 0, 1.0 / abs(item["q_over_p"]), item["slope_u"], 0.0,
                           item["q_over_p"], keys, crossings)
        pieces += [head.tobytes(), vertices.tobytes(), tracks.tobytes()]
    return b"".join(pieces)


def candidate(ordinal, index, hit_keys, *, outcome="selected", truncated=False, fit_chi2=8.0, q_over_p=0.25):
    category = finding_record.CANDIDATE_CATEGORY_OF_OUTCOME[outcome]
    return {"key": f"event-{ordinal}-candidate-{index}", "ordinal": ordinal, "seed_planes": "1-2-3", "outcome": outcome, "failure_category": category,
            "search_truncated": truncated, "measurements": len(hit_keys), "holes": 0, "search_chi2": 5.0, "q_over_p": q_over_p,
            "fit_chi2": fit_chi2 if outcome == "selected" else 0.0, "fit_coordinates": 2 * len(hit_keys) if outcome == "selected" else 0, "hit_keys": list(hit_keys)}


def vertex(ordinal, index, position, tracks, variances=(0.01, 0.01, 0.01)):
    """tracks: [(candidate index, weight)]."""
    return {"key": f"event-{ordinal}-vertex-{index}", "ordinal": ordinal, "position_mm": list(position),
            "covariance": [variances[0], 0.0, 0.0, variances[1], 0.0, variances[2]], "chi2": 1.0, "ndf": 2.0,
            "tracks": [{"track_key": f"event-{ordinal}-candidate-{c}", "weight": w, "chi2": 1.0, "compatibility": 1.0} for c, w in tracks]}


def record_text(events, *, data_sha256="ab" * 32, product_events=None, product_id="hand-made", configuration=None) -> str:
    """acts-tracking-finding-record/2. events: {"found": [candidate(...)], "vertices": [vertex(...)], "budget": (seed, ambiguity)}."""
    config = {name: "1" for name in finding_record.CONFIGURATION_KEYS}
    config.update(configuration or {})
    vconfig = {name: "1" for name in finding_record.VERTEX_CONFIGURATION_KEYS}
    header = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": finding_record.FINDING_EVIDENCE_CLASS,
              "product_id": product_id, "data_sha256": data_sha256, "product_events": len(events) if product_events is None else product_events,
              "configuration_sha256": "cd" * 32, "vertex_recipe": finding_record.VERTEX_RECIPE,
              "vertex_configuration_sha256": finding_record.vertex_configuration_sha256(vconfig)}
    documents = []
    for ordinal, event in enumerate(events):
        found = event["found"]
        selected = [item for item in found if item["outcome"] == "selected"]
        seed_budget, ambiguity_budget = event.get("budget", (0, 0))
        truncated = any(item["search_truncated"] for item in found)
        documents.append({"ordinal": ordinal, "hit_count": 48, "seeds_found": max(len(found), 1), "seeds_run": max(len(found), 1), "seeds_skipped": 0, "seeds_failed": 0,
                          "seeds_without_candidate": 0 if found else 1, "seeds_truncated": int(truncated), "seed_budget_reached": seed_budget,
                          "ambiguity_budget_reached": ambiguity_budget, "candidates": len(found), "selected": len(selected),
                          "failure_category": "none" if selected else ("search-truncated" if truncated or seed_budget or ambiguity_budget else "seed-or-finding"),
                          "found": found, "vertexing": {"status": "ok", "input_tracks": len(selected), "unconverted_tracks": 0, "vertices": event.get("vertices", [])}})
    return finding_record.format_record({"header": header, "configuration": config, "vertex_configuration": vconfig, "events": documents})


def upper(matrix) -> list:
    return [float(matrix[i][j]) for i in range(6) for j in range(i, 6)]


def product_text(tracks, *, recipe=finding_record.FINDING_RECIPE, stage="find-ckf", evidence="data-side", product_id="hand-made", data_sha256="ab" * 32) -> str:
    """acts-tracking-product/1. tracks: {"key", "ordinal", "states": [(plane, kind, hit_key, (loc0, loc1))], "smoothed": {state index: (6 params, 6x6)},
    optional "predicted", "filtered" alike, "status"}."""
    header = {"product_id": product_id, "revision": 1, "recipe": recipe, "stage": stage, "evidence_class": evidence, "data_product": "t07-measurements-x",
              "data_sha256": data_sha256, "hit_sets_sha256": "none", "field_tesla": 1.0, "qop_status": "measured", "material_model": "none",
              "start_prior": [-50.0, 10.0, 0.1, 1.0, 1.0], "acts_version": "48.2.0"}
    document = {"header": header, "tracks": [], "states": [], "parameters": []}
    for item in tracks:
        status = item.get("status", "fitted")
        document["tracks"].append({"key": item["key"], "event_ordinal": item["ordinal"], "status": status, "failure_category": "none" if status == "fitted" else "fit",
                                   "measurements": len(item["states"]), "holes": 0, "outliers": 0, "chi2": 5.0, "measured_coordinates": 2 * len(item["states"]),
                                   "assumed_q_over_p": 0.25})
        for index, (plane, kind, hit_key, (loc0, loc1)) in enumerate(item["states"]):
            document["states"].append({"track_key": item["key"], "index": index, "plane": plane, "kind": kind, "hit_key": hit_key, "loc0_mm": loc0, "loc1_mm": loc1,
                                       "covariance": [0.0004, 0.0, 0.0004], "path_length_mm": 50.0 * plane, "chi2": 1.0})
        for state_type in ("predicted", "filtered", "smoothed"):
            for index, (parameters, covariance) in item.get(state_type, {}).items():
                document["parameters"].append({"track_key": item["key"], "state_index": index, "state_type": state_type, "parameters": list(parameters),
                                               "covariance": upper(covariance)})
    return native_product.format_product(document)


def diagonal(*sigmas) -> numpy.ndarray:
    return numpy.diag([s * s for s in sigmas] + [1.0])


SIGMAS = (0.01, 0.02, 0.001, 0.002, 0.004)


def state_at(truth5, pull5=(0.0, 0.0, 0.0, 0.0, 0.0)):
    """Smoothed parameters that sit `pull5` sigmas from truth, with the covariance diag(SIGMAS^2)."""
    values = [t + p * s for t, p, s in zip(truth5, pull5, SIGMAS)] + [0.0]
    return values, diagonal(*SIGMAS)


def hand_bin(folder: Path, *, fixture_id=7001, stratum=0, block=1, with_product=True, product_events=None):
    """A bin of four events: event 0 near, events 1-3 far. Each event: two vertices, particles 0-2 from vertex 0, 3-5 from vertex 1. Tracks
    match every particle in events 0-2; event 3 loses particle 5 and holds a fake and a duplicate of particle 0."""
    events, found_events, product_tracks = [], [], []
    for ordinal in range(4):
        particles = []
        for p in range(6):
            keys = list(range(10 * p, 10 * p + 8))
            charge = 1 if p % 2 == 0 else -1
            particles.append(particle(keys, charge=charge, q_over_p=0.25 * charge, slope_u=(-0.12, -0.05, 0.02, 0.1, 0.13, -0.14)[p], vertex_index=p // 3,
                                      crossing=(1.0 + p, 2.0 - p, 0.01 * p, 1.5 + 0.01 * p)))
        events.append({"event_index": ordinal, "vertices": [(0.01, 5.0, -100.0), (0.02, 6.0, -100.0)], "particles": particles})
        found = []
        kept = range(6) if ordinal < 3 else range(5)
        for p in kept:
            found.append(candidate(ordinal, len(found), particles[p]["hit_keys"]))
        if ordinal == 3:
            found.append(candidate(ordinal, len(found), [900, 901, 902, 903, 904, 905]))                  # a fake
            found.append(candidate(ordinal, len(found), particles[0]["hit_keys"][:6] + [906, 907]))       # a duplicate of particle 0 (6 of 8)
        tracks0 = [(c, 1.0) for c in range(3)]
        tracks1 = [(c, 1.0) for c in range(3, len(kept))]
        vertices = [vertex(ordinal, 0, (-100.0 + 0.1, 0.01, 5.0), tracks0), vertex(ordinal, 1, (-100.0, 0.02 - 0.1, 6.0), tracks1)]
        found_events.append({"found": found, "vertices": vertices})
        for c, item in enumerate(found):
            if item["outcome"] != "selected":
                continue
            p = c if c < len(kept) else 0
            truth5 = list(particles[p]["crossing"]) + [particles[p]["q_over_p"]]
            pull = (0.5, -0.5, 0.2, -0.2, 0.1) if ordinal % 2 == 0 else (-0.4, 0.4, -0.1, 0.1, -0.2)
            product_tracks.append({"key": item["key"], "ordinal": ordinal, "states": [(plane, "measurement", item["hit_keys"][plane - 1], (0.0, 0.0)) for plane in range(1, 7)],
                                   "smoothed": {0: state_at(truth5, pull)}})
    truth_path = folder / "bin.t07truth"
    truth_path.write_bytes(truth_file_bytes(events, fixture_id=fixture_id, stratum=stratum, block=block))
    record_path = folder / "bin.record"
    record_path.write_text(record_text(found_events, product_events=product_events), encoding="utf-8")
    product_path = folder / "bin.product"
    if with_product:
        product_path.write_text(product_text(product_tracks), encoding="utf-8")
    return {"truth": truth_path, "record": record_path, "product": product_path, "events": events, "found": found_events}


def truth_seeded_text(events, *, data_sha256="ab" * 32, recipe_configuration="cd" * 32) -> str:
    """acts-tracking-truth-seeded-record/2. events: per event the hit-key lists of its delivered tracks, one start per particle (6)."""
    from tests.adapters import test_acts_truth_seeded as seeded_tests
    header = {"recipe": finding_record.FINDING_RECIPE, "stage": seeded_tests.STAGE, "evidence_class": seeded_tests.EVIDENCE_CLASS, "variant": seeded_tests.SECTION_7_VARIANT,
              "product_id": "seeded", "data_sha256": data_sha256, "start_sha256": "ee" * 32, "product_events": 0, "recipe_configuration_sha256": recipe_configuration,
              "configuration_sha256": "ff" * 32}
    lines = [seeded_tests.RECORD_FORMAT] + [f"truth-seeded {name} {header[name]}" for name in seeded_tests.HEADER_FIELDS]
    lines += [f"truth-seeded configuration {name} 1" for name in finding_record.CONFIGURATION_KEYS]
    lines += [f"truth-seeded configuration {name} {value}" for name, value in seeded_tests.START_CONFIGURATION.items()]
    candidates = 0
    for ordinal, tracks in enumerate(events):
        n = len(tracks)
        lines.append(f"truth-seeded event {ordinal} 48 6 6 0 0 {6 - n} 0 0 0 {n} {n} {'none' if n else 'seed-or-finding'}")
        for start in range(6):
            got = start < n
            lines.append(f"truth-seeded start {start} {'candidates' if got else 'no-candidate'} {start if got else 0} {1 if got else 0} 0")
        for index, keys in enumerate(tracks):
            lines.append(f"truth-seeded candidate event-{ordinal}-candidate-{index} {ordinal} start-{index} selected none 0 {len(keys)} 0 5 0.25 8 {2 * len(keys)} "
                         + ",".join(str(k) for k in keys))
            candidates += 1
    lines.append(f"truth-seeded end {len(events)} {candidates}")
    return "\n".join(lines) + "\n"


# ---- Section 7's definitions at their boundaries.

class TrackMatchAtItsBoundary(unittest.TestCase):
    """Section 7, "Track match": more than 50 % of the track's measurements, noise hits included; 70 % for the recorded sensitivity rerun."""

    def setUp(self):
        self.particles = [list(range(0, 8)), list(range(10, 18))]

    def test_exactly_half_is_no_match_and_one_more_is(self):
        self.assertEqual(scoring.owners_of([[0, 1, 2, 3, 100, 101, 102, 103]], self.particles), [None])
        self.assertEqual(scoring.owners_of([[0, 1, 2, 3, 4, 100, 101, 102]], self.particles), [0])

    def test_seventy_percent_at_its_boundary(self):
        self.assertEqual(scoring.owners_of([list(range(7)) + [100, 101, 102]], self.particles, fraction=0.7), [None])      # 7 of 10: exactly 70 %
        self.assertEqual(scoring.owners_of([list(range(5)) + [100, 101]], self.particles, fraction=0.7), [0])              # 5 of 7: 71 %
        self.assertEqual(scoring.owners_of([list(range(5)) + [100, 101]], self.particles), [0])

    def test_a_hit_of_two_particles_is_refused(self):
        with self.assertRaises(scoring.ScoringError):
            scoring.owners_of([[0, 1]], [[0, 1], [1, 2]])

    def test_the_primary_rule_in_order(self):
        tracks = [{"hit_keys": [0, 1, 2, 3, 4, 100], "chi2": 1.0, "ndf": 7}, {"hit_keys": [0, 1, 2, 3, 4, 5], "chi2": 9.0, "ndf": 7}]
        self.assertEqual(scoring.track_event(tracks, self.particles)["primaries"], {0: 1})               # higher matched fraction
        tracks = [{"hit_keys": [0, 1, 2, 3, 4, 5], "chi2": 1.0, "ndf": 7}, {"hit_keys": [0, 1, 2, 3, 4, 5, 6], "chi2": 9.0, "ndf": 9}]
        self.assertEqual(scoring.track_event(tracks, self.particles)["primaries"], {0: 1})               # then most hits
        tracks = [{"hit_keys": [0, 1, 2, 3, 4, 5], "chi2": 9.0, "ndf": 7}, {"hit_keys": [0, 1, 2, 3, 4, 6], "chi2": 1.0, "ndf": 7}]
        self.assertEqual(scoring.track_event(tracks, self.particles)["primaries"], {0: 1})               # then lowest chi2/ndf
        tracks = [{"hit_keys": [0, 1, 2, 3, 4, 5], "chi2": 1.0, "ndf": 7}, {"hit_keys": [0, 1, 2, 3, 4, 6], "chi2": 1.0, "ndf": 7}]
        self.assertEqual(scoring.track_event(tracks, self.particles)["primaries"], {0: 0})               # then lowest index

    def test_reconstructable_needs_six_hits(self):
        particles = [list(range(0, 6)), list(range(10, 15))]
        scores = scoring.track_event([{"hit_keys": list(range(10, 15)), "chi2": 1.0, "ndf": 5}], particles)
        self.assertEqual((scores["reconstructable"], scores["with_primary"], scores["matched"], scores["fakes"]), (1, 0, 1, 0))

    def test_equal_to_the_development_scorer_at_fifty_percent(self):
        """test_acts_finding.scored_event is the development runs' judge; the same events give the same counts and primaries."""
        generator = numpy.random.default_rng([520, 7, 1])   # hand-made inputs: a fixed stream, no fixture
        for trial in range(200):
            particles = [list(range(20 * p, 20 * p + int(generator.integers(4, 9)))) for p in range(4)]
            tracks = []
            for _ in range(int(generator.integers(0, 7))):
                owner = particles[int(generator.integers(0, 4))]
                keys = sorted(set(generator.choice(owner, size=int(generator.integers(1, len(owner) + 1)), replace=False).tolist()
                                  + [1000 + int(k) for k in generator.integers(0, 5, size=int(generator.integers(0, 4)))]))
                tracks.append({"hit_keys": keys, "chi2": float(generator.integers(1, 4)), "ndf": int(generator.integers(1, 3))})
            ours = scoring.track_event(tracks, particles)
            theirs = finding_tests.scored_event(tracks, [{"hit_keys": keys} for keys in particles])
            with self.subTest(trial=trial):
                for name in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates", "primaries"):
                    self.assertEqual(ours[name], theirs[name], name)


class VertexDefinitions(unittest.TestCase):
    """Section 7's vertex rows, with U-K1 (decisions.md: a vertex's primary "most tracks" counts tracks with weight >= 0.5)."""

    def vertices(self, *specs):
        return [{"key": f"v{i}", "position_mm": list(position), "covariance": [1, 0, 0, 1, 0, 1], "tracks": [{"track_key": k, "weight": w} for k, w in tracks]}
                for i, (position, tracks) in enumerate(specs)]

    def test_u_k1_counts_tracks_at_weight_one_half_or_more(self):
        positions = [(0.0, 0.0, 0.0)]
        owners = {"a": 0, "b": 0, "c": 0, "d": 0, "e": 0}
        # Both vertices hold all their weight from truth vertex 0 (share 1). Vertex 0 holds 4 tracks, one of them at weight >= 0.5; vertex 1 holds
        # 3 tracks, all at 0.5 or more. U-K1 picks vertex 1; the plain track count would pick vertex 0.
        vertices = self.vertices(((0.0, 0.0, 0.1), [("a", 0.9), ("b", 0.2), ("c", 0.2), ("d", 0.2)]), ((0.0, 0.0, 0.5), [("e", 0.5), ("b", 0.5), ("c", 0.6)]))
        scores = scoring.vertex_event(vertices, owners, {}, [0, 0, 0, 0, 0], positions, reconstructable_particles=[0, 0, 0])
        self.assertEqual(scores["primaries"], {0: 1})
        vertices[1]["tracks"][0]["weight"] = 0.4999   # now vertex 1 holds 2 tracks at weight >= 0.5, and vertex 0 one: still vertex 1
        self.assertEqual(scoring.vertex_event(vertices, owners, {}, [0] * 5, positions, reconstructable_particles=[0, 0, 0])["primaries"], {0: 1})
        vertices[1]["tracks"][2]["weight"] = 0.4999   # one each: the distance decides, vertex 0 is nearer
        self.assertEqual(scoring.vertex_event(vertices, owners, {}, [0] * 5, positions, reconstructable_particles=[0, 0, 0])["primaries"], {0: 0})

    def test_a_match_needs_more_than_half_of_the_summed_weight(self):
        positions = [(0.0, 0.0, 0.0), (0.0, 0.0, 9.0)]
        owners = {"a": 0, "b": 1, "x": None}
        vertices = self.vertices(((0.0, 0.0, 0.0), [("a", 0.5), ("b", 0.25), ("x", 0.25)]))     # exactly half: no match (the unmatched weight stays in)
        scores = scoring.vertex_event(vertices, owners, {}, [0, 1], positions, reconstructable_particles=[0, 1])
        self.assertEqual((scores["primaries"], scores["unmatched"]), ({}, 1))
        vertices[0]["tracks"][0]["weight"] = 0.51
        self.assertEqual(scoring.vertex_event(vertices, owners, {}, [0, 1], positions, reconstructable_particles=[0, 1])["primaries"], {0: 0})

    def test_reconstructable_vertex_has_three_reconstructable_tracks(self):
        positions = [(0.0, 0.0, 0.0), (0.0, 0.0, 9.0)]
        scores = scoring.vertex_event([], {}, {}, [0, 0, 0, 1, 1, 1], positions, reconstructable_particles=[0, 0, 0, 1, 1])
        self.assertEqual((scores["reconstructable"], scores["found"]), (1, 0))

    def test_wrong_assignment_counts_weight_one_half_in_a_matched_vertex(self):
        positions = [(0.0, 0.0, 0.0), (0.0, 0.0, 9.0)]
        owners = {"a": 0, "b": 0, "c": 0, "d": 1}
        primary_tracks = {"a": 0, "b": 1, "c": 2, "d": 3}   # primary track key -> its particle
        vertices = self.vertices(((0.0, 0.0, 0.0), [("a", 1.0), ("b", 1.0), ("c", 1.0), ("d", 0.5)]))
        scores = scoring.vertex_event(vertices, owners, primary_tracks, [0, 0, 0, 1], positions, reconstructable_particles=[0, 0, 0, 1])
        self.assertEqual((scores["assigned"], scores["wrong"]), (4, 1))
        vertices[0]["tracks"][3]["weight"] = 0.4999
        scores = scoring.vertex_event(vertices, owners, primary_tracks, [0, 0, 0, 1], positions, reconstructable_particles=[0, 0, 0, 1])
        self.assertEqual((scores["assigned"], scores["wrong"]), (3, 0))

    def test_the_global_frame_and_near_events(self):
        self.assertEqual(scoring.truth_position({"u_mm": 1.0, "v_mm": 2.0, "z_mm": -100.0}), (-100.0, 1.0, 2.0))
        self.assertTrue(scoring.is_near(0) and scoring.is_near(10) and not scoring.is_near(7))


class SearchTruncatedByDeliveredTracks(unittest.TestCase):
    """U-K3: an event is search-truncated if any delivered track is marked truncated (scoring side)."""

    def test_a_delivered_truncated_track_marks_the_event(self):
        found = [candidate(0, 0, [1, 2, 3, 4, 5, 6]), candidate(0, 1, [7, 8, 9, 10, 11, 12], truncated=True)]
        self.assertTrue(scoring.search_truncated(found))

    def test_an_evicted_truncated_candidate_does_not(self):
        found = [candidate(0, 0, [1, 2, 3, 4, 5, 6]), candidate(0, 1, [7, 8, 9, 10, 11, 12], outcome="evicted", truncated=True)]
        self.assertFalse(scoring.search_truncated(found))
        self.assertFalse(scoring.search_truncated([]))


# ---- Plane 1: the state and its propagation (section 7, "Track state, surface"; R16).

class PlaneOneState(unittest.TestCase):
    def test_propagation_follows_the_development_helix(self):
        """A state at plane 3 of a helix, propagated to plane 1, is the helix's plane-1 crossing (test_acts_refit_field.crossings_from_vertex)."""
        slope_u, slope_v, q_over_p = numpy.array([0.1, -0.12]), numpy.array([0.05, -0.02]), numpy.array([0.6, -0.3])
        crossings = refit_tests.crossings_from_vertex(numpy.array([0.02, -0.01]), numpy.array([3.0, -7.0]), slope_u, slope_v, q_over_p)
        for track in range(2):
            at_three = list(crossings[track, 2]) + [q_over_p[track]]
            state, _ = scoring.plane_one_state(numpy.array(at_three), numpy.eye(5) * 1e-6, plane=3)
            expected = list(crossings[track, 0]) + [q_over_p[track]]
            numpy.testing.assert_allclose(state, expected, rtol=0, atol=1e-9)

    def test_a_plane_one_state_is_kept_as_it_is(self):
        state = numpy.array([1.0, 2.0, 0.1, 1.5, 0.3])
        covariance = numpy.diag([1.0, 2.0, 3.0, 4.0, 5.0])
        found, moved = scoring.plane_one_state(state, covariance, plane=1)
        self.assertTrue((found == state).all() and (moved == covariance).all())

    def test_the_covariance_follows_the_jacobian(self):
        """Propagating loc0 back one plane leaves its variance; phi's variance feeds loc0 by the lever arm (50 mm per plane)."""
        state = numpy.array([0.0, 0.0, 0.0, math.pi / 2, 1e-9])
        covariance = numpy.diag([1e-4, 1e-4, 1e-6, 1e-6, 1e-8])
        _, moved = scoring.plane_one_state(state, covariance, plane=2)
        self.assertAlmostEqual(moved[0, 0], 1e-4 + 50.0 ** 2 * 1e-6, delta=1e-7)
        self.assertAlmostEqual(moved[2, 2], 1e-6, delta=1e-9)

    def test_the_product_reader_streams_what_the_full_reader_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.product"
            truth5 = [1.0, 2.0, 0.01, 1.5, 0.25]
            tracks = [{"key": "event-0-candidate-0", "ordinal": 0, "states": [(1, "measurement", 0, (1.0, 2.0)), (2, "measurement", 1, (1.5, 2.5))],
                       "smoothed": {0: state_at(truth5, (1, 1, 1, 1, 1)), 1: state_at(truth5)}, "predicted": {0: state_at(truth5, (2, 2, 2, 2, 2))},
                       "filtered": {0: state_at(truth5, (3, 3, 3, 3, 3))}},
                      {"key": "event-0-candidate-1", "ordinal": 0, "states": [(3, "measurement", 5, (0.0, 0.0))], "smoothed": {0: state_at(truth5)}}]
            path.write_text(product_text(tracks), encoding="utf-8")
            found = scoring.read_product(path, recipe=finding_record.FINDING_RECIPE)
            numpy.testing.assert_allclose(found["states"]["event-0-candidate-0"]["smoothed"], [t + s for t, s in zip(truth5, SIGMAS)])
            self.assertEqual(found["states"]["event-0-candidate-0"]["plane"], 1)
            self.assertEqual(found["states"]["event-0-candidate-1"]["plane"], 3)
            numpy.testing.assert_allclose(found["states"]["event-0-candidate-0"]["predicted"], [t + 2 * s for t, s in zip(truth5, SIGMAS)])
            parsed = native_product.parse_product(path.read_text(encoding="utf-8"))
            self.assertEqual(found["counts"], {"tracks": len(parsed["tracks"]), "states": len(parsed["states"]), "parameters": len(parsed["parameters"])})
            path.write_text(product_text(tracks)[:-30], encoding="utf-8")
            with self.assertRaises(scoring.ScoringError):
                scoring.read_product(path, recipe=finding_record.FINDING_RECIPE)
            path.write_text(product_text(tracks, recipe="reco.track.acts-kf-refit/1"), encoding="utf-8")
            with self.assertRaises(scoring.ScoringError):
                scoring.read_product(path, recipe=finding_record.FINDING_RECIPE)


# ---- The count (v4 5.3) and the gates' wiring to the core.

class TheTestCount(unittest.TestCase):
    def test_1260_in_v4_5_3s_composition(self):
        composition = scoring.required_composition()
        self.assertEqual(composition, {"track pulls": 360, "q/p per charge": 144, "vertex pulls": 216, "clean rates": 72, "noise rates": 96, "refit": 252,
                                       "angle": 120, "total": 1260})
        self.assertEqual(composition["total"], core.REQUIRED_TESTS["T07"])

    def test_per_bin_and_per_fixture(self):
        self.assertEqual(len(scoring.bin_gates(7001)), 57)
        self.assertEqual(len(scoring.bin_gates(7002)), 38)
        self.assertEqual(len(scoring.slice_gates()), 60)
        self.assertEqual(12 * 57 + 12 * 38 + 2 * 60, 1260)
        every = [(f, s, g) for f in (7001, 7002) for s in range(12) for g in scoring.bin_gates(f)] + [(f, g) for f in (7001, 7002) for g in scoring.slice_gates()]
        self.assertEqual(len(every), 1260)
        self.assertEqual(len(set(scoring.bin_gates(7001))), 57)

    def test_cai_and_other_workflows_refused(self):
        for fixture in (7003, 7004, 8001):
            with self.assertRaises(scoring.ScoringError):
                scoring.bin_gates(fixture)


def tally_for(fixture_id, events=40, *, seed=3):
    """A hand-made tally: per-event counts and pulls from a fixed stream (no fixture event)."""
    generator = numpy.random.default_rng([520, 7, seed])
    tally = scoring.BinTally(events=events)
    per_event = [generator.normal(0.0, 1.0, size=(int(k), 5)) for k in generator.integers(0, 7, size=events)]
    tally.pulls = per_event
    tally.pull_charges = [numpy.where(numpy.arange(len(p)) % 2 == 0, 1, -1) for p in per_event]
    tally.vertex_pulls = [generator.normal(0.0, 1.0, size=(2, 3)) for _ in range(events - 8)]
    counts = generator.integers(3, 8, size=events)
    tally.efficiency = (counts, numpy.minimum(counts, generator.integers(0, 2, size=events)))
    tally.fakes = (counts, numpy.zeros(events, dtype=numpy.int64))
    tally.duplicates = (counts, numpy.zeros(events, dtype=numpy.int64))
    tally.charge_sign = (counts, numpy.zeros(events, dtype=numpy.int64))
    tally.vertex_finding = (numpy.full(events - 8, 2), numpy.zeros(events - 8, dtype=numpy.int64))
    tally.vertex_assignment = (numpy.full(events - 8, 6), numpy.zeros(events - 8, dtype=numpy.int64))
    if fixture_id == 7001:
        tally.refit_pulls = [generator.normal(0.0, 1.0, size=(6, 5)) for _ in range(events)]
        tally.refit_charges = [numpy.array([1, -1, 1, -1, 1, -1]) for _ in range(events)]
    else:
        tally.paired = (counts, counts - 1, counts - 1)
        tally.stability = {"r_dev": 0.0, "l_dev": 0.0, "record_sha256": "e" * 64}
    return tally


_EVALUATION_RECORDS = []


def evaluation_records() -> list:
    """The 24 bins' records of block 11 from hand-made tallies, computed once for the summary tests."""
    if not _EVALUATION_RECORDS:
        for fixture in (7001, 7002):
            for stratum in range(12):
                _EVALUATION_RECORDS.extend(scoring.gate_records(core.BinIdentity("T07", fixture, 11, stratum), tally_for(fixture, seed=stratum)))
    return list(_EVALUATION_RECORDS)


class GateWiring(unittest.TestCase):
    """Each gate of v4 8.2 and 8.5 is the core's own test, called with section 8.2's limit on the tally's numbers."""

    def check(self, fixture_id, stratum=4):
        identity = core.BinIdentity("T07", fixture_id, 11, stratum)
        tally = tally_for(fixture_id)
        records = scoring.gate_records(identity, tally)
        self.assertEqual([(r.gate, r.statistic) for r in records], scoring.bin_gates(fixture_id))
        by = {(r.gate, r.statistic): r for r in records}
        loc0 = core.pull_tests("T07 track pull loc0", identity, [p[:, 0] for p in tally.pulls])
        self.assertEqual(by[("T07 track pull loc0", "trimmed-centre")], loc0[0])
        self.assertEqual(by[("T07 track pull loc0", "sigma68-width")], loc0[1])
        tail = core.rate_test("T07 track pull loc0", identity, numpy.array([len(p) for p in tally.pulls]),
                              numpy.array([int((numpy.abs(p[:, 0]) > 3).sum()) for p in tally.pulls]), 0.01, statistic="tail")
        self.assertEqual(by[("T07 track pull loc0", "tail")], tail)
        positive = core.pull_tests("T07 q/p pull positive", identity, [p[c > 0, 4] for p, c in zip(tally.pulls, tally.pull_charges)])
        self.assertEqual(by[("T07 q/p pull positive", "trimmed-centre")], positive[0])
        z = core.pull_tests("T07 vertex pull z", identity, [v[:, 2] for v in tally.vertex_pulls])
        self.assertEqual(by[("T07 vertex pull z", "sigma68-width")], z[1])
        self.assertEqual(by[("T07 duplicates", "rate")], core.rate_test("T07 duplicates", identity, *tally.duplicates, 0.01))
        self.assertEqual(by[("T07 charge sign", "rate")], core.rate_test("T07 charge sign", identity, *tally.charge_sign, 0.01))
        self.assertEqual(by[("T07 vertex finding", "efficiency")], core.efficiency_test("T07 vertex finding", identity, *tally.vertex_finding, 0.95))
        self.assertEqual(by[("T07 vertex assignment", "rate")], core.rate_test("T07 vertex assignment", identity, *tally.vertex_assignment, 0.01))
        return identity, tally, by

    def test_clean_bin(self):
        identity, tally, by = self.check(7001)
        self.assertEqual(by[("T07 efficiency clean", "efficiency")], core.efficiency_test("T07 efficiency clean", identity, *tally.efficiency, 0.99))
        self.assertEqual(by[("T07 fakes clean", "rate")], core.rate_test("T07 fakes clean", identity, *tally.fakes, 0.01))
        note = "refit fits without a plane-1 result (a reading, no rate gated)"
        bare = (lambda r: dataclasses.replace(r, readings={k: v for k, v in r.readings.items() if k != note}))
        refit = core.pull_tests("T07 refit pull theta", identity, [p[:, 3] for p in tally.refit_pulls])
        self.assertEqual(bare(by[("T07 refit pull theta", "trimmed-centre")]), refit[0])
        self.assertEqual(by[("T07 refit pull theta", "trimmed-centre")].readings[note], "0 of 0 hit sets")
        negative = core.pull_tests("T07 refit q/p pull negative", identity, [p[c < 0, 4] for p, c in zip(tally.refit_pulls, tally.refit_charges)])
        self.assertEqual(bare(by[("T07 refit q/p pull negative", "sigma68-width")]), negative[1])

    def test_noise_bin(self):
        for stratum, floor in ((3, 0.98937), (4, 0.98812), (5, 0.98374)):   # R_floor(o) - 0.01, section 8.2 (4.1's R_floor 0.99937, 0.99812, 0.99374)
            identity, tally, by = self.check(7002, stratum)
            self.assertEqual(by[("T07 efficiency noise (b) floor", "efficiency")].limit, floor)
            self.assertEqual(by[("T07 efficiency noise (b) floor", "efficiency")], core.efficiency_test("T07 efficiency noise (b) floor", identity, *tally.efficiency, floor))
        self.assertEqual(by[("T07 efficiency noise (a) paired", "paired-difference")], core.paired_test("T07 efficiency noise (a) paired", identity, *tally.paired, -0.01))
        self.assertEqual(by[("T07 fakes noise F1", "rate")], core.rate_test("T07 fakes noise F1", identity, *tally.fakes, 0.005))
        self.assertEqual(by[("T07 fakes noise F2", "stability")].limit, 0.0025)

    def test_attempt_2_is_the_blocks_level(self):
        records = scoring.gate_records(core.BinIdentity("T07", 7002, 12, 4), tally_for(7002))
        self.assertEqual({(r.attempt, r.confidence) for r in records}, {(2, 0.99)})

    def test_a_population_too_sparse_for_its_bootstrap_reads_inconclusive(self):
        """One object in 40 events: some of the bin's own bootstrap rows hold none, so the se is undefined; inconclusive with the reason, no crash."""
        identity = core.BinIdentity("T07", 7001, 11, 4)
        tally = tally_for(7001)
        tally.vertex_pulls = [numpy.zeros((0, 3))] * 31 + [numpy.full((1, 3), 0.5)]
        by = {(r.gate, r.statistic): r for r in scoring.gate_records(identity, tally)}
        for statistic in ("trimmed-centre", "sigma68-width"):
            self.assertEqual(by[("T07 vertex pull x", statistic)].result, "inconclusive")
            self.assertIn("holds no object", by[("T07 vertex pull x", statistic)].reason)
        self.assertEqual(by[("T07 vertex pull x", "tail")].result, "inconclusive")   # 32 events, under N_min

    def test_a_missing_group_is_required_output_missing(self):
        identity = core.BinIdentity("T07", 7001, 11, 4)
        tally = tally_for(7001)
        tally.missing["product"] = "the product is absent"
        records = {(r.gate, r.statistic): r for r in scoring.gate_records(identity, tally)}
        for key in (("T07 track pull phi", "tail"), ("T07 q/p pull negative", "trimmed-centre"), ("T07 charge sign", "rate")):
            self.assertEqual((records[key].result, records[key].required), ("inconclusive", True))
            self.assertIn("required output missing", records[key].reason)
        self.assertNotIn("required output missing", records[("T07 fakes clean", "rate")].reason)


class FakeStabilityF2(unittest.TestCase):
    """Section 8.3, F2: (r_eval - r_dev) + sqrt((U_eval - r_eval)^2 + (r_dev - L_dev)^2) <= tau = 0.0025, defined at zero counts."""

    identity = core.BinIdentity("T07", 7002, 11, 5)

    def test_zero_counts_on_both_samples(self):
        m, y = numpy.full(12000, 36), numpy.zeros(12000, dtype=numpy.int64)
        record = scoring.stability_test("F2", self.identity, m, y, r_dev=0.0, l_dev=0.0)
        u = fake_rate.rate_rule(m, y)["u_dev"]
        self.assertEqual(record.estimate, u)
        self.assertAlmostEqual(u, 1 - 0.05 ** (1 / 12000), places=12)
        self.assertEqual((record.result, record.step, record.limit), ("pass", 3, 0.0025))

    def test_the_block_2_numbers_of_stratum_5(self):
        """r_dev 4.635735494204172e-06, L_dev 8.236815995775458e-07 (the Freeze-B run's record, stratum 5), against an evaluation with k = 0."""
        m, y = numpy.full(12000, 36), numpy.zeros(12000, dtype=numpy.int64)
        record = scoring.stability_test("F2", self.identity, m, y, r_dev=4.635735494204172e-06, l_dev=8.236815995775458e-07)
        u = fake_rate.rate_rule(m, y)["u_dev"]
        self.assertEqual(record.estimate, (0.0 - 4.635735494204172e-06) + math.sqrt(u ** 2 + (4.635735494204172e-06 - 8.236815995775458e-07) ** 2))

    def test_the_boundary_and_a_fail(self):
        m = numpy.full(12000, 10)
        y = numpy.zeros(12000, dtype=numpy.int64)
        y[:60] = 1    # r_eval 5e-4
        record = scoring.stability_test("F2", self.identity, m, y, r_dev=0.0, l_dev=0.0)
        self.assertEqual(record.result, "pass")
        y[:400] = 1   # r_eval 3.3e-3, beyond tau
        self.assertEqual(scoring.stability_test("F2", self.identity, m, y, r_dev=0.0, l_dev=0.0).result, "fail")
        self.assertEqual(scoring.stability_test("F2", self.identity, numpy.zeros(10, dtype=numpy.int64), numpy.zeros(10, dtype=numpy.int64), r_dev=0.0, l_dev=0.0).result,
                         "inconclusive")

    def test_attempt_2_bound_at_99_percent(self):
        m, y = numpy.full(12000, 36), numpy.zeros(12000, dtype=numpy.int64)
        record = scoring.stability_test("F2", core.BinIdentity("T07", 7002, 12, 5), m, y, r_dev=0.0, l_dev=0.0)
        self.assertAlmostEqual(record.estimate, 1 - 0.01 ** (1 / 12000), places=12)


class FreezeBRateRecord(unittest.TestCase):
    """F2 reads r_dev and L_dev from the Freeze-B run's record by hash, and refuses a record whose hash or block differs."""

    def record(self, block=2, fakes_of_5=2):
        header = {"recipe": finding_record.FINDING_RECIPE, "configuration_sha256": "cd" * 32, "vertex_configuration_sha256": "ef" * 32, "fixture_id": 7002, "block": block,
                  "events_per_bin": 12000}
        bins = []
        for stratum in range(12):
            m = numpy.full(12000, 36)
            y = numpy.zeros(12000, dtype=numpy.int64)
            if stratum == 5:
                y[:fakes_of_5] = 1
            found = fake_rate.rate_rule(m, y)
            bins.append(fake_rate.bin_line_values(stratum, found, {name: "0" * 64 for name in fake_rate.HASH_FIELDS}))
        return fake_rate.format_rate_record({"header": header, "bins": bins})

    def test_the_record_read_by_its_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "noise-b2.rate.record"
            path.write_text(self.record(), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found = scoring.freeze_b_rate_record(path, expected_sha256=digest)
            self.assertEqual(sorted(found["bins"]), list(range(12)))
            self.assertEqual(found["bins"][5]["r_dev"], 2 / (12000 * 36))
            self.assertEqual(found["sha256"], digest)

    def test_a_changed_r_dev_record_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "noise-b2.rate.record"
            path.write_text(self.record(), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            text = path.read_text(encoding="utf-8").replace(" fakes 2 ", " fakes 3 ", 1)
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(scoring.ScoringError):
                scoring.freeze_b_rate_record(path, expected_sha256=digest)

    def test_a_consistent_record_of_other_numbers_is_refused_by_its_hash_alone(self):
        """A record whose every bound follows from its counts, but whose counts are not the recorded ones: only the hash refuses it."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "noise-b2.rate.record"
            path.write_text(self.record(), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.write_text(self.record(fakes_of_5=3), encoding="utf-8")
            fake_rate.parse_rate_record(path.read_text(encoding="utf-8"))     # it reads: a well-formed record
            with self.assertRaises(scoring.ScoringError):
                scoring.freeze_b_rate_record(path, expected_sha256=digest)
            with self.assertRaises(scoring.ScoringError):
                scoring.freeze_b_rate_record(path)                                # the pinned hash is the Freeze-B run's, not this record's

    def test_a_record_of_another_block_is_refused_even_at_its_own_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "noise-b3.rate.record"
            path.write_text(self.record(block=3), encoding="utf-8")
            with self.assertRaises(scoring.ScoringError):
                scoring.freeze_b_rate_record(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def test_the_pinned_hash_is_the_freeze_b_runs(self):
        self.assertEqual(scoring.FREEZE_B_RATE_RECORD_SHA256, "ebf2aa0e54de13c2626c20c4d0d1a997ddf6ea2694d1cbe7354b5e8e3a2deb73")
        self.assertEqual(scoring.FREEZE_B_BLOCK, 2)


# ---- N1: the refit set's completeness; O5: the pooled slices' identity.

def refit_product(folder: Path, name: str, ordinals, particles_per_event=6, short_by=0) -> Path:
    tracks = []
    for ordinal in ordinals:
        for p in range(particles_per_event):
            tracks.append({"key": f"event-{ordinal}-track-{p}", "ordinal": ordinal, "states": [(1, "measurement", 10 * p, (0.0, 0.0))],
                           "smoothed": {0: state_at([1.0 + p, 2.0 - p, 0.01 * p, 1.5 + 0.01 * p, 0.25 * (1 if p % 2 == 0 else -1)])}})
    tracks = tracks[:len(tracks) - short_by]
    path = folder / f"{name}.product"
    path.write_text(product_text(tracks, recipe=scoring.REFIT_RECIPE, stage="refit-known-hit-set", evidence="truth-assisted"), encoding="utf-8")
    return path


def refit_record(identity, first, count, path, stratum_sha256="1" * 64) -> layout.RangeRecord:
    return layout.RangeRecord("T07", identity.fixture_id, identity.block, identity.stratum, first, count, tuple(range(first, first + count)),
                              layout.sha256_bytes(Path(path).read_bytes()), stratum_sha256, "2" * 64, f"job_{first}")


class RefitSetComplete(unittest.TestCase):
    """N1 (E6a re-review): the refit ranges are outside the layout's completeness check; T07 scoring refuses a short refit set."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.identity = core.BinIdentity("T07", 7001, 11, 2)
        self.pieces = [layout.EventRange(0, 2), layout.EventRange(2, 2)]
        self.paths = {0: refit_product(self.folder, "r0", [0, 1]), 2: refit_product(self.folder, "r2", [2, 3])}
        self.attempts = {span: [("NO-FAILURE", refit_record(self.identity, span.first, span.count, self.paths[span.first]))] for span in self.pieces}

    def collect(self, **changes):
        arguments = dict(pieces=self.pieces, attempts=self.attempts, products=self.paths, total=4)
        arguments.update(changes)
        return scoring.collect_refit(self.identity, arguments.pop("pieces"), arguments.pop("attempts"), arguments.pop("products"), total=arguments.pop("total"))

    def test_a_complete_set(self):
        found = self.collect()
        self.assertEqual(found.status, "complete", found.reason)

    def test_a_missing_or_failed_piece_makes_the_refit_missing(self):
        self.assertEqual(self.collect(attempts={self.pieces[0]: self.attempts[self.pieces[0]]}).status, "missing")
        failed = dict(self.attempts)
        failed[self.pieces[1]] = [("NOT-REPEATABLE", None)]
        self.assertEqual(self.collect(attempts=failed).status, "missing")
        repeated = dict(self.attempts)
        repeated[self.pieces[1]] = [("REPEATABLE", None)] + self.attempts[self.pieces[1]]    # a repeat after a draw: never on block 11
        self.assertEqual(self.collect(attempts=repeated).status, "missing")
        self.assertEqual(self.collect(pieces=[]).status, "missing")

    def test_a_truncated_or_short_product_is_refused(self):
        short = refit_product(self.folder, "short", [2])   # holds event 2 only: a short range
        attempts = dict(self.attempts)
        attempts[self.pieces[1]] = [("NO-FAILURE", refit_record(self.identity, 2, 2, short))]
        found = self.collect(attempts=attempts, products={0: self.paths[0], 2: short})
        self.assertEqual(found.status, "missing")
        self.assertIn("events", found.reason)
        cut = self.folder / "cut.product"
        cut.write_bytes(self.paths[2].read_bytes()[:-20])
        attempts[self.pieces[1]] = [("NO-FAILURE", refit_record(self.identity, 2, 2, cut))]
        self.assertEqual(self.collect(attempts=attempts, products={0: self.paths[0], 2: cut}).status, "missing")

    def test_a_product_changed_after_its_record_is_refused(self):
        self.paths[2].write_text(self.paths[2].read_text(encoding="utf-8").replace("revision 1", "revision 2"), encoding="utf-8")
        self.assertEqual(self.collect().status, "missing")

    def test_another_bins_records_are_refused(self):
        other = core.BinIdentity("T07", 7001, 12, 2)
        attempts = {span: [("NO-FAILURE", refit_record(other, span.first, span.count, self.paths[span.first]))] for span in self.pieces}
        self.assertEqual(self.collect(attempts=attempts).status, "missing")

    def test_the_plans_refit_pieces(self):
        plan = layout.evaluation_plan(block=11)
        pieces = scoring.refit_pieces(plan, 7001, 2)
        self.assertEqual(pieces, [layout.EventRange(0, 4000), layout.EventRange(4000, 4000), layout.EventRange(8000, 4000)])
        self.assertEqual(scoring.refit_pieces(plan, 7002, 2), [])
        self.assertNotIn(layout.EventRange(0, 4000), [r for r in plan.ranges_by_bin()[(7, 7001, 2)] if r.count == 4000])   # the layout's own check omits them (N1)


class AngleSliceIdentity(unittest.TestCase):
    """O5 (E6a review): the pooled angle slices pool 12 bins, so they have an identity of their own for seeding and completeness."""

    def test_slices_by_truth_u_slope_sign_aware(self):
        edges = [(-0.15, 0), (-0.0751, 0), (-0.075, 1), (-1e-12, 1), (0.0, 2), (0.0749, 2), (0.075, 3), (0.15, 3)]
        for slope, expected in edges:
            self.assertEqual(scoring.slice_of(slope), expected, slope)
        for slope in (-0.1501, 0.1501):
            self.assertIsNone(scoring.slice_of(slope))

    def test_each_slice_seeds_apart_from_every_bin_and_from_each_other(self):
        rows = {}
        for fixture in (7001, 7002):
            for stratum in range(12):
                rows[("bin", fixture, stratum)] = core.bootstrap_indices(core.BinIdentity("T07", fixture, 11, stratum), 50, replicates=4).tobytes()
            for index in range(4):
                identity = scoring.slice_identity(fixture, 11, index)
                rows[("slice", fixture, index)] = core.bootstrap_indices(identity, 50, replicates=4).tobytes()
                self.assertEqual(core.seed_entropy(identity), (core.BOOTSTRAP_DOMAIN, fixture, 11, scoring.SLICE_STRATUM_BASE + index))
                self.assertIn(f"angle slice {index}", identity.label)
                self.assertEqual(identity.level, core.level_of_block(11))
        self.assertEqual(len(set(rows.values())), len(rows))
        self.assertEqual(core.bootstrap_indices(scoring.slice_identity(7001, 11, 2), 50).tobytes(), core.bootstrap_indices(scoring.slice_identity(7001, 11, 2), 50).tobytes())

    def test_slice_identities_refused_outside_their_range(self):
        for arguments in ((7001, 11, 4), (7001, 11, -1), (7003, 11, 0), (7001, 2, 0), (8001, 11, 0)):
            with self.assertRaises((scoring.ScoringError, core.CoreError)):
                scoring.slice_identity(*arguments)

    def slice_data(self, fixture, stratum, block=11, status="complete", events=4):
        ordinal = numpy.array([0, 0, 1, 2, 3, 3], dtype=numpy.int64)
        slope = numpy.array([-0.14, 0.01, -0.05, 0.1, 0.13, -0.08])
        pulls = numpy.tile(numpy.linspace(-1, 1, 6)[:, None], (1, 5)) * (1 + stratum / 10)
        return {"fixture_id": fixture, "block": block, "stratum": stratum, "events": events, "status": status, "reason": "" if status == "complete" else "the bin is incomplete",
                "record_sha256": "0" * 64, "populations": {label: {"ordinal": ordinal, "slope_u": slope, "pulls": pulls,
                                                                   "without_ordinal": numpy.zeros(0, dtype=numpy.int64), "without_slope_u": numpy.zeros(0)}
                                                           for label in ("0.5", "0.7")}}

    def test_complete_slices_give_60_records_in_order(self):
        bins = [self.slice_data(7001, s) for s in range(12)]
        records = scoring.score_slices(7001, 11, bins, events_per_bin=4)["records"]
        self.assertEqual([(r.gate, r.statistic) for r in records], scoring.slice_gates())
        self.assertTrue(all(r.required for r in records))
        self.assertIn("angle slice 0", records[0].bin)
        self.assertEqual(records[0].readings["events"], 48)   # pooled over the 12 bins' events

    def test_an_incomplete_pool_is_required_output_missing(self):
        for bins in ([self.slice_data(7001, s) for s in range(11)],
                     [self.slice_data(7001, s) for s in range(11)] + [self.slice_data(7001, 11, status="missing")],
                     [self.slice_data(7001, s) for s in range(11)] + [self.slice_data(7001, 11, block=12)],
                     [self.slice_data(7001, s) for s in range(11)] + [self.slice_data(7001, 10)],
                     [self.slice_data(7001, s, events=3 if s == 4 else 4) for s in range(12)]):
            records = scoring.score_slices(7001, 11, bins, events_per_bin=4)["records"]
            self.assertEqual(len(records), 60)
            self.assertTrue(all(r.result == "inconclusive" and "required output missing" in r.reason for r in records))


# ---- A whole bin from hand-made files.

class WholeBin(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)

    def test_a_clean_bin_end_to_end(self):
        files = hand_bin(self.folder)
        identity = scoring.bin_identity(7001, 1, 0)
        pieces = [layout.EventRange(0, 2), layout.EventRange(2, 2)]
        paths = {0: refit_product(self.folder, "r0", [0, 1]), 2: refit_product(self.folder, "r2", [2, 3])}
        attempts = {s: [("NO-FAILURE", refit_record(identity, s.first, s.count, paths[s.first]))] for s in pieces}
        refit = scoring.RefitInput(scoring.collect_refit(identity, pieces, attempts, paths, total=4), paths)
        score = scoring.score_bin(identity, scoring.BinInputs(files["record"], files["product"], files["truth"], refit=refit), events=4)
        self.assertEqual([(r.gate, r.statistic) for r in score["records"]], scoring.bin_gates(7001))
        tally = score["tally"]
        self.assertEqual((int(tally.efficiency[0].sum()), int(tally.efficiency[1].sum())), (24, 1))          # 24 reconstructable, 1 lost
        self.assertEqual((int(tally.fakes[0].sum()), int(tally.fakes[1].sum())), (25, 1))                    # 23 + 2 delivered in event 3: 25 tracks, 1 fake
        self.assertEqual((int(tally.duplicates[0].sum()), int(tally.duplicates[1].sum())), (24, 1))          # 24 matched, 1 not primary
        self.assertEqual(int(tally.charge_sign[1].sum()), 0)
        self.assertEqual(len(tally.vertex_finding[0]), 3)                                                    # far events 1, 2, 3
        self.assertEqual(sum(len(p) for p in tally.pulls), 23)                                               # 23 primaries
        numpy.testing.assert_allclose(tally.pulls[0][0], [0.5, -0.5, 0.2, -0.2, 0.1], atol=1e-6)
        self.assertEqual(sum(len(p) for p in tally.refit_pulls), 24)
        self.assertTrue(all("development reading, block 1" in r.bin for r in score["records"]))
        self.assertNotIn("required output missing", {r.reason for r in score["records"] if r.gate.startswith("T07 refit")})
        self.assertIn("vertex split", score["readings"])

    def test_the_refit_missing_and_the_product_short_are_named(self):
        files = hand_bin(self.folder, product_events=2)
        identity = scoring.bin_identity(7001, 1, 0)
        missing = scoring.RefitInput(layout.BinCollection("missing", "missing range: 2-3 has no attempt", ()), {})
        records = scoring.score_bin(identity, scoring.BinInputs(files["record"], files["product"], files["truth"], refit=missing), events=4)["records"]
        by = {(r.gate, r.statistic): r for r in records}
        self.assertIn("required output missing", by[("T07 refit pull loc0", "trimmed-centre")].reason)
        self.assertIn("2-3 has no attempt", by[("T07 refit q/p pull positive", "tail")].reason)
        self.assertIn("required output missing", by[("T07 track pull loc0", "trimmed-centre")].reason)   # product_events 2 of 4: the product is short
        self.assertNotIn("required output missing", by[("T07 fakes clean", "rate")].reason)

    def test_a_short_refit_set_is_refused_in_scoring_too(self):
        files = hand_bin(self.folder)
        identity = scoring.bin_identity(7001, 1, 0)
        pieces = [layout.EventRange(0, 2), layout.EventRange(2, 2)]
        paths = {0: refit_product(self.folder, "r0", [0, 1]), 2: refit_product(self.folder, "r2", [2, 3], short_by=1)}
        attempts = {s: [("NO-FAILURE", refit_record(identity, s.first, s.count, paths[s.first]))] for s in pieces}
        refit = scoring.RefitInput(scoring.collect_refit(identity, pieces, attempts, paths, total=4), paths)
        records = scoring.score_bin(identity, scoring.BinInputs(files["record"], files["product"], files["truth"], refit=refit), events=4)["records"]
        self.assertIn("refit set is short", {(r.gate, r.statistic): r for r in records}[("T07 refit pull loc0", "trimmed-centre")].reason)

    def test_files_of_another_bin_are_refused(self):
        files = hand_bin(self.folder, stratum=3)
        with self.assertRaises(scoring.ScoringError):
            scoring.score_bin(scoring.bin_identity(7001, 1, 0), scoring.BinInputs(files["record"], files["product"], files["truth"]), events=4)
        with self.assertRaises(scoring.ScoringError):
            scoring.score_bin(scoring.bin_identity(7001, 1, 3), scoring.BinInputs(files["record"], files["product"], files["truth"]), events=5)


class DevelopmentReadings(unittest.TestCase):
    """Block 1 is read as a development reading: its own label, the attempt-1 rule, and never a workflow verdict."""

    def test_block_1_is_labelled_and_other_blocks_refused(self):
        identity = scoring.bin_identity(7002, 1, 4)
        self.assertTrue(identity.label.startswith("development reading, block 1"))
        self.assertEqual(identity.level, core.level_of_block(11))
        self.assertEqual(scoring.bin_identity(7002, 11, 4), core.BinIdentity("T07", 7002, 11, 4))
        for block in (2, 3, 4, 5, 6):
            with self.assertRaises(scoring.ScoringError):
                scoring.bin_identity(7002, block, 4)

    def test_no_verdict_on_development_records(self):
        records = scoring.gate_records(scoring.bin_identity(7001, 1, 0), tally_for(7001))
        with self.assertRaises(scoring.ScoringError):
            scoring.summarize(records, [], sensitivity_changes=[])

    def test_the_summary_counts_the_required_set(self):
        records = evaluation_records()
        outcome = scoring.summarize(records, every_check(), sensitivity_changes=[])
        self.assertIn("required set not intact: 1140 required tests", outcome.reasons[0])
        slices = []
        for fixture in (7001, 7002):
            slices += scoring.score_slices(fixture, 11, [AngleSliceIdentity.slice_data(None, fixture, s) for s in range(12)], events_per_bin=4)["records"]
        outcome = scoring.summarize(records + slices, every_check(), sensitivity_changes=[])
        self.assertEqual(len(records + slices), 1260)
        self.assertFalse(any("required set not intact" in reason for reason in outcome.reasons), outcome.reasons)
        self.assertEqual((outcome.workflow_result, outcome.r11_state), ("fail", "failed"))   # hand-made bins are too small: inconclusive in required bins
        self.assertIn("a required check was inconclusive (R11)", outcome.reasons)
        self.assertEqual({o.name for o in outcome.open_obligations} >= {"T07 material", "A01"}, True)


class MatchingSensitivity(unittest.TestCase):
    """Section 7, line 533: the rerun at 70 % decides only the sentence "not sensitive to the matching threshold"."""

    def test_the_thresholds(self):
        base = {("T07 fakes clean", "rate"): 0.001, ("T07 track pull loc0", "trimmed-centre"): 0.01}
        for rerun, sentence in (({("T07 fakes clean", "rate"): 0.006, ("T07 track pull loc0", "trimmed-centre"): 0.03}, True),
                                ({("T07 fakes clean", "rate"): 0.0061, ("T07 track pull loc0", "trimmed-centre"): 0.01}, False),
                                ({("T07 fakes clean", "rate"): 0.001, ("T07 track pull loc0", "trimmed-centre"): 0.0301}, False)):
            changes = scoring.sensitivity_changes(base, rerun)
            disagrees, line = scoring.matching_sentence(changes)
            self.assertEqual(disagrees, not sentence)
            self.assertEqual(line == "not sensitive to the matching threshold", sentence)

    def test_the_rerun_is_recorded_in_the_outcome_and_blocks_nothing(self):
        records = evaluation_records()
        changes = scoring.sensitivity_changes({("T07 duplicates", "rate"): 0.0}, {("T07 duplicates", "rate"): 0.5})
        outcome = scoring.summarize(records, every_check(), sensitivity_changes=changes)
        self.assertIn("matching sensitivity disagrees (recorded, no effect)", outcome.recorded)


# ---- E5 at evaluation: the kept negative-case file, its SHA-256 first.

def negative_record(names, overrides=None):
    """A /1 record of the negative-case file, as the finder would write it with every case firing as v4 11 expects."""
    overrides = overrides or {}
    description = scoring.negative_cases.read(KEPT_NEGATIVE_CASES)["description"]
    cases = scoring.negative_cases.cases_of(description)
    tracks = cases["tracks"]
    events, seeds = [], []
    for ordinal, name in enumerate(names):
        rows = cases["events"][ordinal]
        found, event_seeds = [], []
        if name in ("honest", "one-wrong-plane") or name.startswith(("lost-", "alone-")):
            for track in tracks:
                own = set(scoring.negative_cases.sorted_hits([cases["hits"][k] for k in track]))
                keys = [k for k, row in enumerate(rows) if row in own and not (name == "one-wrong-plane" and row[0] == 5)]
                found.append(candidate(ordinal, len(found), keys))
                found[-1]["holes"] = 1 if name == "one-wrong-plane" else 0
        if name == "branch-explosion":
            found = [candidate(ordinal, i, [i, i + 1, i + 2, i + 3, i + 4, i + 5], truncated=True, outcome="selected" if i < 3 else "evicted") for i in range(40)]
        event = {"ordinal": ordinal, "hit_count": len(rows), "seeds_found": len(found), "seeds_run": len(found), "seeds_skipped": 0, "seeds_failed": 0,
                 "seeds_without_candidate": 0, "seeds_truncated": 0, "seed_budget_reached": 0, "ambiguity_budget_reached": 0, "candidates": len(found),
                 "selected": sum(f["outcome"] == "selected" for f in found), "failure_category": "none", "found": found}
        event_seeds = [{"planes": "1-2-3", "hit_keys": [0, 1, 2], "outcome": "candidates", "first_candidate": i, "candidates": 1, "short_branches": 0} for i in range(len(found))]
        if name == "three-wrong-planes":
            event.update(seeds_found=2, seeds_run=2, seeds_without_candidate=2, failure_category="seed-or-finding")
            event_seeds = [{"planes": "1-2-3", "hit_keys": [0, 1, 2], "outcome": "no-candidate", "first_candidate": 0, "candidates": 0, "short_branches": 0}] * 2
        if name in ("no-triple", "two-planes"):
            event.update(seeds_found=0, seeds_run=0, failure_category="seed-or-finding")
        if name == "branch-explosion":
            event.update(seeds_truncated=1, ambiguity_budget_reached=1, seeds_found=40, seeds_run=40)
        if name == "seed-budget":
            event.update(seeds_found=10000, seeds_run=0, seeds_skipped=10000, seed_budget_reached=1, failure_category="search-truncated")
            event_seeds = [{"planes": "1-2-3", "hit_keys": [0, 1, 2], "outcome": "skipped", "first_candidate": 0, "candidates": 0, "short_branches": 0}] * 10000
        event.update(overrides.get(name, {}))
        events.append(event)
        seeds.append(event_seeds)
    config = {name: "1" for name in finding_record.CONFIGURATION_KEYS}
    config.update(finding_most_branches_per_seed="32", finding_most_seeds_per_event="10000")
    header = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": finding_record.FINDING_EVIDENCE_CLASS,
              "product_id": "neg", "data_sha256": scoring.NEGATIVE_CASE_SHA256, "product_events": 0, "configuration_sha256": "cd" * 32}
    return {"header": header, "configuration": config, "events": events}, seeds


def writable_copy(source: Path, target: Path) -> None:
    """A copy of a kept folder whose files and folders this test may change, also when the plugin is a read-only copy (the jobs' snapshots; E6
    merge review I2): the bytes only, never the source's modes."""
    shutil.copytree(source, target, copy_function=shutil.copyfile)
    for folder in [target, *(p for p in target.rglob("*") if p.is_dir())]:
        folder.chmod(0o755)


class NegativeCasesAtEvaluation(unittest.TestCase):
    """E5 (v4 11): the kept file, its SHA-256 checked first; wrong hits, branch explosion, seed failure; limits reached marked search-truncated."""

    def test_the_kept_folder_by_its_hashes(self):
        description = scoring.check_negative_case_folder(KEPT_NEGATIVE_CASES)
        self.assertEqual(description["case_sha256"], scoring.NEGATIVE_CASE_SHA256)
        self.assertEqual(len(description["names"]), 7 + 28 + 6 * 28)

    def test_a_changed_folder_is_refused_before_it_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "kept"
            writable_copy(KEPT_NEGATIVE_CASES, copy)
            flipped = bytearray((copy / "t07-negative-cases-1.t07data").read_bytes())
            flipped[-1] ^= 1
            (copy / "t07-negative-cases-1.t07data").write_bytes(bytes(flipped))
            with self.assertRaises(scoring.ScoringError):
                scoring.check_negative_case_folder(copy)

    def test_a_consistent_folder_of_another_source_event_is_refused_by_the_hashes(self):
        """A folder its own builder would accept (another source event, case file and sums rebuilt): only the hashes kept at Freeze B refuse it."""
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "kept"
            writable_copy(KEPT_NEGATIVE_CASES, copy)
            description = json.loads((copy / scoring.negative_cases.DESCRIPTION_FILE).read_text(encoding="utf-8"))
            description["hits"][0][1] += 0.001
            cases = scoring.negative_cases.cases_of(description)
            case_bytes = scoring.negative_cases.fixture_files.encode_data_file(scoring.negative_cases.HIT_SIGMA_MM, cases["events"])
            description["case_sha256"] = hashlib.sha256(case_bytes).hexdigest()
            (copy / scoring.negative_cases.CASE_FILE).write_bytes(case_bytes)
            (copy / scoring.negative_cases.DESCRIPTION_FILE).write_text(scoring.negative_cases._description_text(description), encoding="utf-8")
            (copy / "SHA256SUMS").write_text("".join(f"{hashlib.sha256((copy / n).read_bytes()).hexdigest()}  {n}\n"
                                                     for n in (scoring.negative_cases.CASE_FILE, scoring.negative_cases.DESCRIPTION_FILE)), encoding="utf-8")
            scoring.negative_cases.read(copy)    # its builder reads it
            with self.assertRaises(scoring.ScoringError):
                scoring.check_negative_case_folder(copy)

    def test_every_case_fires_on_a_record_that_does_what_v4_11_expects(self):
        description = scoring.check_negative_case_folder(KEPT_NEGATIVE_CASES)
        record, seeds = negative_record(description["names"])
        checks = scoring.negative_case_checks(description, record, seeds)
        self.assertTrue(all(check.kind == "negative" for check in checks))
        self.assertEqual([c.name for c in checks if c.result != "pass"], [])
        self.assertGreaterEqual(len(checks), 10)

    def test_each_one_defect_is_a_failing_check(self):
        description = scoring.check_negative_case_folder(KEPT_NEGATIVE_CASES)
        for name, change, check in (("three-wrong-planes", {"selected": 1, "failure_category": "none"}, "wrong hits: three-wrong-planes"),
                                    ("no-triple", {"seeds_found": 1, "seeds_run": 1, "seeds_without_candidate": 1}, "seed failure: no-triple"),
                                    ("seed-budget", {"seed_budget_reached": 0}, "seed budget: seed-budget"),
                                    ("branch-explosion", {"ambiguity_budget_reached": 0}, "branch explosion")):
            record, seeds = negative_record(description["names"], {name: change})
            failing = [c.name for c in scoring.negative_case_checks(description, record, seeds) if c.result == "fail"]
            with self.subTest(name=name):
                self.assertTrue(any(c.startswith(check) for c in failing), failing)


class NoRecipeImportsTheScoring(unittest.TestCase):
    """The scoring reads truth, so it is scoring side: no recipe file imports or names it (v4 3.1)."""

    def test_no_recipe_file_names_it(self):
        from tests.adapters.test_t04_evaluation_core import RECIPE_FILES
        count = 0
        for adapter, files in RECIPE_FILES.items():
            for name in files:
                text = (ROOT / "adapters" / adapter / name).read_text(encoding="utf-8")
                count += 1
                with self.subTest(path=f"{adapter}/{name}"):
                    self.assertNotIn("t07_evaluation_scoring", text)
        self.assertGreaterEqual(count, 40)

    def test_it_imports_no_recipe_module(self):
        source = (ROOT / "tests" / "adapters" / "t07_evaluation_scoring.py").read_text(encoding="utf-8")
        modules = {alias.name.split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Import) for alias in node.names}
        modules |= {(node.module or "").split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
        self.assertFalse(modules & {"light_recipe", "calo_recipe", "acts_tracking", "photon_likelihood", "calo_cluster"})


class CommandLine(unittest.TestCase):
    """The interface E6c's T07 evaluation tasks call: score-bin writes the records and ends with its own result line."""

    def test_score_bin_writes_records_and_its_result_line(self):
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as folder:
            files = hand_bin(Path(folder))
            out = Path(folder) / "out"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = scoring.main(["score-bin", "--block", "1", "--fixture-id", "7001", "--stratum", "0", "--events", "4", "--record", str(files["record"]),
                                     "--product", str(files["product"]), "--truth", str(files["truth"]), "--out", str(out)])
            text = stream.getvalue()
            self.assertEqual(code, 0, text)
            state, line = layout.classify_script_run(code, text, scoring.RESULT_LINE)
            self.assertEqual(state, "ok", line)
            records = scoring.read_records(out / scoring.records_name(7001, 1, 0))
            self.assertEqual([(r.gate, r.statistic) for r in records], scoring.bin_gates(7001))
            self.assertIn("refit: no refit collection given", {r.reason for r in records if r.gate == "T07 refit pull loc0"}.pop())
            self.assertTrue((out / scoring.slices_name(7001, 1, 0)).is_file())

    def test_a_rejected_input_is_negative_and_a_crash_has_no_result_line(self):
        import io
        import contextlib
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = scoring.main(["score-bin", "--block", "3", "--fixture-id", "7001", "--stratum", "0", "--events", "4", "--record", "x", "--product", "x", "--truth", "x",
                                 "--out", "x"])
        self.assertEqual(code, 2)
        self.assertEqual(layout.classify_script_run(code, stream.getvalue(), scoring.RESULT_LINE)[0], "negative")
        self.assertEqual(layout.classify_script_run(3, "Traceback (most recent call last):\n", scoring.RESULT_LINE)[0], "crashed")

    def test_the_count_command(self):
        import io
        import contextlib
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(scoring.main(["count"]), 0)
        self.assertIn("total 1260", stream.getvalue())


class FixRoundOne(unittest.TestCase):
    """Fix round 1 of the review (d4-e6b-review.md) and the user's answers on the attempt-2 levels."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)

    def drop_state(self, files, key):
        text = files["product"].read_text(encoding="utf-8")
        kept = [line for line in text.splitlines() if not (line.startswith("parameters ") and line.split(" ")[1] == key)]
        counts = kept[-1].split(" ")
        removed = len(text.splitlines()) - len(kept)
        kept[-1] = " ".join(counts[:3] + [str(int(counts[3]) - removed)])
        files["product"].write_text("\n".join(kept) + "\n", encoding="utf-8")

    def test_i2_a_primary_with_no_plane_one_result_is_a_failure(self):
        files = hand_bin(self.folder)
        self.drop_state(files, "event-1-candidate-2")     # particle 2 of event 1: matched, primary, reconstructable, no smoothed state
        score = scoring.score_bin(scoring.bin_identity(7001, 1, 0), scoring.BinInputs(files["record"], files["product"], files["truth"]), events=4)
        tally, by = score["tally"], {(r.gate, r.statistic): r for r in score["records"]}
        self.assertEqual((int(tally.charge_sign[0].sum()), int(tally.charge_sign[1].sum())), (23, 1))   # 23 primaries, the one without a result failing
        self.assertEqual((int(tally.efficiency[0].sum()), int(tally.efficiency[1].sum())), (24, 2))     # it counts against the efficiency too
        self.assertEqual(sum(len(p) for p in tally.pulls), 22)
        tail = by[("T07 track pull loc0", "tail")]
        self.assertEqual((tail.readings["objects"], tail.readings["failures"]), (23, 1))
        positive = by[("T07 q/p pull positive", "tail")]                                                 # particle 2 has charge +1
        self.assertEqual((positive.readings["objects"], positive.readings["failures"]), (12, 1))

    def test_i2_refit_fits_without_result_are_a_reading_beside_the_refit_pulls(self):
        files = hand_bin(self.folder)
        identity = scoring.bin_identity(7001, 1, 0)
        pieces = [layout.EventRange(0, 2), layout.EventRange(2, 2)]
        paths = {0: refit_product(self.folder, "r0", [0, 1]), 2: refit_product(self.folder, "r2", [2, 3])}
        text = paths[2].read_text(encoding="utf-8").replace("track event-3-track-5 3 fitted none", "track event-3-track-5 3 failed fit")
        paths[2].write_text(text, encoding="utf-8")
        attempts = {s: [("NO-FAILURE", refit_record(identity, s.first, s.count, paths[s.first]))] for s in pieces}
        refit = scoring.RefitInput(scoring.collect_refit(identity, pieces, attempts, paths, total=4), paths)
        score = scoring.score_bin(identity, scoring.BinInputs(files["record"], files["product"], files["truth"], refit=refit), events=4)
        record = {(r.gate, r.statistic): r for r in score["records"]}[("T07 refit pull loc0", "trimmed-centre")]
        self.assertEqual(record.readings["refit fits without a plane-1 result (a reading, no rate gated)"], "1 of 24 hit sets")
        self.assertEqual(sum(len(p) for p in score["tally"].refit_pulls), 23)

    def test_f2_at_attempt_2_recomputes_l_dev_at_99_percent(self):
        m = numpy.full(12000, 36)
        y = numpy.zeros(12000, dtype=numpy.int64)
        y[:2] = 1
        found = fake_rate.rate_rule(m, y)
        item = {"fakes": 2, "tracks": 432000, "events": 12000, "deff_hat": found["deff_hat"], "l_dev": found["l_dev"], "r_dev": found["r_dev"]}
        self.assertEqual(scoring.development_lower_bound(item, 1), found["l_dev"])
        at_99 = scoring.development_lower_bound(item, 2)
        self.assertEqual(at_99, core.bounds_at(2, 432000, 12000, found["deff_hat"], 0.99)["lower"])
        self.assertLess(at_99, found["l_dev"])
        self.assertEqual(scoring.development_lower_bound(dict(item, fakes=0, l_dev=0.0, deff_hat=1.0), 2), 0.0)

    def test_f2_from_files_takes_the_attempts_l_dev(self):
        records = {}
        for block in (11, 12):
            folder = self.folder / f"b{block}"
            folder.mkdir()
            files = noise_bin(folder, block=block)
            rate = folder / "noise-b2.rate.record"
            rate.write_text(FreezeBRateRecord.record(None), encoding="utf-8")
            inputs = scoring.BinInputs(files["record"], files["product"], files["truth"], truth_seeded_record=files["seeded"], rate_record=rate,
                                       rate_record_sha256=hashlib.sha256(rate.read_bytes()).hexdigest())
            records[block] = {(r.gate, r.statistic): r for r in scoring.score_bin(core.BinIdentity("T07", 7002, block, 5), inputs, events=4)["records"]}
        stored = scoring.freeze_b_rate_record(rate, hashlib.sha256(rate.read_bytes()).hexdigest())["bins"][5]
        self.assertEqual(records[11][("T07 fakes noise F2", "stability")].readings["l_dev"], stored["l_dev"])
        self.assertEqual(records[12][("T07 fakes noise F2", "stability")].readings["l_dev"], scoring.development_lower_bound(stored, 2))
        self.assertEqual(records[12][("T07 fakes noise F2", "stability")].readings["u_eval_confidence"], 0.99)

    def test_m6_a_noise_bin_pairs_the_finder_against_the_truth_seeded_run(self):
        files = noise_bin(self.folder)
        rate = self.folder / "noise-b2.rate.record"
        rate.write_text(FreezeBRateRecord.record(None), encoding="utf-8")
        digest = hashlib.sha256(rate.read_bytes()).hexdigest()
        inputs = scoring.BinInputs(files["record"], files["product"], files["truth"], truth_seeded_record=files["seeded"], rate_record=rate, rate_record_sha256=digest)
        score = scoring.score_bin(scoring.bin_identity(7002, 1, 5), inputs, events=4)
        m, a, b = (numpy.asarray(v) for v in score["tally"].paired)
        self.assertEqual((int(m.sum()), int(a.sum()), int(b.sum())), (24, 23, 24))   # the finder lost one particle; the truth-seeded run found every one
        record = {(r.gate, r.statistic): r for r in score["records"]}[("T07 efficiency noise (a) paired", "paired-difference")]
        self.assertAlmostEqual(record.estimate, -1 / 24)
        files["seeded"].write_text(truth_seeded_text([[]] * 4, recipe_configuration="00" * 32), encoding="utf-8")
        missing = {(r.gate, r.statistic): r for r in scoring.score_bin(scoring.bin_identity(7002, 1, 5), inputs, events=4)["records"]}
        self.assertIn("not of this recipe configuration", missing[("T07 efficiency noise (a) paired", "paired-difference")].reason)
        other = scoring.BinInputs(files["record"], files["product"], files["truth"], truth_seeded_record=files["seeded"], rate_record=rate, rate_record_sha256="0" * 64)
        refused = {(r.gate, r.statistic): r for r in scoring.score_bin(scoring.bin_identity(7002, 1, 5), other, events=4)["records"]}
        self.assertIn("r_dev record", refused[("T07 fakes noise F2", "stability")].reason)

    def test_i3_the_checks_rerun_at_evaluation_is_a_constant(self):
        self.assertEqual(scoring.DETERMINISTIC_CHECKS_SOURCE, "rerun at evaluation")
        names = [name for name, _, _ in scoring.T07_CHECKS]
        for scenario in ("A05", "A07", "A17", "A39", "CAI-T07-1", "CAI-T07-3"):
            self.assertTrue(any(name.startswith(scenario) for name in names), scenario)
        self.assertEqual({kind for _, kind, _ in scoring.T07_CHECKS}, {"deterministic", "cai"})

    def test_i3_the_checks_task_reads_each_modules_result(self):
        outputs = {"tests.adapters.test_acts_scenarios": "Ran 20 tests in 1.0s\n\nOK\n", "tests.adapters.test_acts_finding": "Ran 64 tests in 1.0s\n\nFAILED (failures=2)\n",
                   "tests.adapters.test_acts_cai_refit": "Ran 20 tests in 1.0s\n\nOK\n", "tests.adapters.test_acts_truth_seeded": "Ran 20 tests in 1.0s\n\nFAILED (failures=1)\n",
                   "tests.adapters.test_acts_track_outputs": "Ran 45 tests in 1.0s\n\nOK\n"}
        _, checks = scoring.checks_task(11, build="b", out=self.folder, module_runner=outputs.get)
        words = {c.name.split(":")[0]: c.result for c in checks}
        self.assertEqual(words, {"A05": "pass", "A07": "fail", "A17": "pass", "A39": "fail", "CAI-T07-1 and CAI-T07-2": "pass", "CAI-T07-3 and CAI-T07-4": "pass"})
        outputs["tests.adapters.test_acts_scenarios"] = "Traceback (most recent call last):\n"
        with self.assertRaises(RuntimeError):
            scoring.checks_task(11, build="b", out=self.folder, module_runner=outputs.get)

    def test_i3_a_pass_needs_every_named_check(self):
        """E6 merge stage: the names go to the core (required_checks), and an absent one is incomplete, never a fail (E6c re-review)."""
        records = evaluation_records()
        self.assertEqual(len(scoring.required_checks()), len(scoring.NEGATIVE_CHECK_NAMES) + len(scoring.T07_CHECKS))
        every = every_check()
        for fixture in (7001, 7002):
            records += scoring.score_slices(fixture, 11, [AngleSliceIdentity.slice_data(None, fixture, s) for s in range(12)], events_per_bin=4)["records"]
        with self.assertRaises(scoring.ChecksIncomplete) as raised:
            scoring.summarize(records, every[1:], sensitivity_changes=[])
        self.assertIn("absent", str(raised.exception))
        description = scoring.check_negative_case_folder(KEPT_NEGATIVE_CASES)
        record, seeds = negative_record(description["names"])
        self.assertEqual([c.name for c in scoring.negative_case_checks(description, record, seeds)], list(scoring.NEGATIVE_CHECK_NAMES))

    def test_m7_a_doubled_record_is_refused(self):
        records = evaluation_records()
        with self.assertRaises(scoring.ScoringError):
            scoring.summarize(records + records[:1], [], sensitivity_changes=[])

    def test_i1_the_refit_key_and_the_interface(self):
        self.assertEqual(scoring.refit_key(11999, 35), "event-11999-track-35")
        self.assertIn("never its place in a refit range", scoring.REFIT_KEY_RULE)
        import io
        import contextlib
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(scoring.t07_interface("bogus"), 2)
            self.assertEqual(scoring.t07_interface("bin", block=3, fixture_id=7001, stratum=0, build="b", out=str(self.folder)), 2)
            self.assertEqual(scoring.t07_interface("summary", block=1, scores=str(self.folder)), 2)
        self.assertEqual(stream.getvalue().count("RESULT t07-scoring"), 3)

    def test_i1_collection_and_score_bin_from_task_folders(self):
        import io
        import contextlib
        files = hand_bin(self.folder)
        bin_dir = self.folder / "bin-attempt"
        bin_dir.mkdir()
        named = scoring.bin_files(bin_dir, 7001, 1, 0)
        for kind, name in (("record", "record"), ("product", "product"), ("t07truth", "truth")):
            shutil.copy(files[name], named[kind])
        content = b"x" * 10
        named["t07data"].write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()
        for kind, path in (("record", named["record"]), ("product", named["product"]), ("truth", named["t07truth"])):
            scoring.write_range_record(bin_dir, kind, layout.RangeRecord("T07", 7001, 1, 0, 0, 4, (0, 1, 2, 3), hashlib.sha256(path.read_bytes()).hexdigest(), sha, sha, "1"))
        refit_attempts = {}
        for first in (0, 2):
            folder = self.folder / f"refit-{first}"
            folder.mkdir()
            product = refit_product(folder, "tmp", [first, first + 1])
            product.rename(scoring.refit_product_path(folder, 1, 0, first))
            hit_sets = folder / f"refit-b1-s0-{first}.hitsets"
            hit_sets.write_text("hit sets\n", encoding="utf-8")
            scoring.write_range_record(folder, "refit", layout.RangeRecord("T07", 7001, 1, 0, first, 2, (first, first + 1),
                                                                           hashlib.sha256(scoring.refit_product_path(folder, 1, 0, first).read_bytes()).hexdigest(), sha,
                                                                           hashlib.sha256(hit_sets.read_bytes()).hexdigest(), "2"))
            refit_attempts[str(first)] = [["NO-FAILURE", str(folder)]]
        attempts = {"bin": [["NO-FAILURE", str(bin_dir)]], "refit": refit_attempts}
        document = scoring.collect_task(1, 7001, 0, attempts, pieces=[layout.EventRange(0, 2), layout.EventRange(2, 2)], count=4)
        self.assertEqual((document["status"], document["refit"]["status"]), ("complete", "complete"), document)
        path = self.folder / "collection.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = scoring.main(["score-bin", "--block", "1", "--fixture-id", "7001", "--stratum", "0", "--events", "4", "--collection", str(path), "--out", str(self.folder / "out")])
        self.assertEqual(code, 0, stream.getvalue())
        records = scoring.read_records(self.folder / "out" / scoring.records_name(7001, 1, 0))
        self.assertFalse([r for r in records if "required output missing" in r.reason], [r.reason for r in records if r.reason][:3])
        (self.folder / "refit-2" / "refit-b1-s0-2.hitsets").write_text("other\n", encoding="utf-8")   # review M3: the hit-set file is its record's
        document = scoring.collect_task(1, 7001, 0, attempts, pieces=[layout.EventRange(0, 2), layout.EventRange(2, 2)], count=4)
        self.assertEqual(document["refit"]["status"], "missing")
        self.assertIn("hit-set file", document["refit"]["reason"])
        document = scoring.collect_task(1, 7001, 0, {"bin": [], "refit": {}}, pieces=[], count=4)
        self.assertEqual(document["status"], "missing")
        path.write_text(json.dumps(document), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scoring.main(["score-bin", "--block", "1", "--fixture-id", "7001", "--stratum", "0", "--events", "4", "--collection", str(path),
                                           "--out", str(self.folder / "out2")]), 0)
        self.assertTrue(all("required output missing" in r.reason for r in scoring.read_records(self.folder / "out2" / scoring.records_name(7001, 1, 0))))

    def test_m1_a_vertex_with_no_positive_variance_is_no_result(self):
        positions = [(0.0, 0.0, 0.0)]
        vertices = [{"key": "v0", "position_mm": [0.1, 0.0, 0.0], "covariance": [0.0, 0, 0, 1.0, 0, 1.0], "tracks": [{"track_key": k, "weight": 1.0} for k in "abc"]}]
        scores = scoring.vertex_event(vertices, {"a": 0, "b": 1, "c": 2}, {}, [0, 0, 0], positions, reconstructable_particles=[0, 0, 0])
        self.assertEqual((scores["pulls"], scores["without_result"], scores["without_result_reconstructable"], scores["found"]), ([], 1, 1, 1))
        tracks = [{"hit_keys": [0, 1, 2, 3, 4, 5], "chi2": 1.0, "ndf": 0}, {"hit_keys": [0, 1, 2, 3, 4, 6], "chi2": 9.0, "ndf": 7}]
        self.assertEqual(scoring.track_event(tracks, [list(range(8))])["primaries"], {0: 1})


def noise_bin(folder: Path, *, block=1, stratum=5):
    """A noise bin of four events from hand_bin, with a truth-seeded record that finds every particle of every event."""
    files = hand_bin(folder, fixture_id=7002, stratum=stratum, block=block)
    seeded = folder / "bin.truth-seeded.record"
    seeded.write_text(truth_seeded_text([[p["hit_keys"] for p in event["particles"]] for event in files["events"]]), encoding="utf-8")
    files["seeded"] = seeded
    return files


class EveryCommandsParser(unittest.TestCase):
    """Fix round 1, job 7591993: a command read an option its parser did not define (clean s4's score-bin, run while its source was edited).
    Every command's handler is read for the options it uses (arguments.<name>), and each must be in that command's parsed namespace; every task
    command is then run through main with its functions replaced, so each branch reads its own namespace."""

    MINIMAL = {"score-bin": ["--block", "1", "--fixture-id", "7001", "--stratum", "0", "--events", "4", "--out", "o"],
               "score-slices": ["--block", "1", "--fixture-id", "7001", "--events", "4", "--bins", "b", "--out", "o"],
               "negative-cases": ["--block", "1", "--folder", "f", "--record", "r", "--seeds", "s", "--out", "o"],
               "summary": ["--block", "11", "--scores", "s"], "count": [],
               "bin-task": ["--block", "1", "--fixture-id", "7001", "--stratum", "0", "--build", "b", "--out", "o"],
               "refit-task": ["--block", "1", "--stratum", "0", "--first", "0", "--count", "2", "--bin-dir", "d", "--build", "b", "--out", "o"],
               "collect": ["--block", "1", "--fixture-id", "7001", "--stratum", "0", "--attempts", "a", "--out", "o"],
               "negative-task": ["--block", "1", "--build", "b", "--folder", "f", "--out", "o"],
               "checks-task": ["--block", "1", "--build", "b", "--out", "o"]}
    HANDLERS = {"score-bin": "_score_bin_command", "score-slices": "_score_slices_command", "negative-cases": "_negative_cases_command",
                "summary": "_summary_command", "count": "main"}

    def used(self, function: str) -> set:
        tree = ast.parse((ROOT / "tests" / "adapters" / "t07_evaluation_scoring.py").read_text(encoding="utf-8"))
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == function)
        return {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "arguments"}

    def test_every_command_parses_and_its_handler_reads_only_its_options(self):
        self.assertEqual(set(self.MINIMAL), set(scoring.build_parser()._subparsers._group_actions[0].choices))
        for command, argv in self.MINIMAL.items():
            namespace = vars(scoring.build_parser().parse_args([command] + argv))
            if command in self.HANDLERS and command != "count":
                with self.subTest(command=command):
                    self.assertEqual(self.used(self.HANDLERS[command]) - set(namespace), set())

    def test_every_task_branch_runs_through_main(self):
        import io
        import contextlib
        from unittest import mock
        calls = {}
        fakes = {"bin_task": lambda *a, **k: calls.setdefault("bin", (a, k)) and [],
                 "refit_task": lambda *a, **k: calls.setdefault("refit", (a, k)) and [],
                 "collect_task": lambda *a, **k: calls.setdefault("collect", (a, k)) and {"status": "complete", "reason": ""},
                 "negative_task": lambda *a, **k: (calls.setdefault("negative", (a, k)) and [], []),
                 "checks_task": lambda *a, **k: (calls.setdefault("checks", (a, k)) and [], [])}
        with tempfile.TemporaryDirectory() as folder:
            attempts = Path(folder) / "a"
            attempts.write_text("{}", encoding="utf-8")
            with mock.patch.multiple(scoring, **fakes):
                for command in ("bin-task", "refit-task", "collect", "negative-task", "checks-task"):
                    argv = [x if x not in ("a", "o") else str(Path(folder) / x) for x in self.MINIMAL[command]]
                    stream = io.StringIO()
                    with contextlib.redirect_stdout(stream):
                        code = scoring.main([command] + argv)
                    with self.subTest(command=command):
                        self.assertEqual(code, 0, stream.getvalue())
                        self.assertEqual(layout.classify_script_run(code, stream.getvalue(), scoring.RESULT_LINE)[0], "ok")
        self.assertEqual(set(calls), {"bin", "refit", "collect", "negative", "checks"})

    def test_score_bin_without_files_or_collection_is_rejected_not_a_crash(self):
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as folder:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = scoring.main(["score-bin"] + [x if x != "o" else folder for x in self.MINIMAL["score-bin"]])
        self.assertEqual((code, layout.classify_script_run(code, stream.getvalue(), scoring.RESULT_LINE)[0]), (2, "negative"))


def every_check(result="pass") -> list:
    """One CheckResult of each required T07 check (E5's negative checks, the deterministic and CAI checks)."""
    return [core.CheckResult(n, "negative", result) for n in scoring.NEGATIVE_CHECK_NAMES] + [core.CheckResult(n, k, result) for n, k, _ in scoring.T07_CHECKS]


class MergeStage(unittest.TestCase):
    """The E6 merge stage (d4-e6-merge-brief.md, item 2): E6b re-review N1 (a primary with no plane-1 result is a failure in its slice's tail),
    the summary's required checks passed to the core (an absent check is incomplete, never a fail), the slice identity on core.PooledIdentity."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="t07-merge-"))

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_n1_a_primary_with_no_plane_one_result_is_kept_for_its_slice(self):
        files = hand_bin(self.folder)
        FixRoundOne.drop_state(self, files, "event-1-candidate-2")     # particle 2 of event 1: primary, no smoothed state
        identity = scoring.bin_identity(7001, 1, 0)
        score = scoring.score_bin(identity, scoring.BinInputs(files["record"], files["product"], files["truth"]), events=4)
        population = score["slices"]["0.5"]
        self.assertEqual(population["without_ordinal"].tolist(), [1])
        self.assertEqual(len(population["without_slope_u"]), 1)
        self.assertIsNotNone(scoring.slice_of(float(population["without_slope_u"][0])))
        self.assertEqual(len(population["ordinal"]), 22)                # the 22 with a result, as the bin's pulls
        path = self.folder / "s.slices.npz"
        scoring.write_slices(path, identity, score, "0" * 64, "complete", "")
        back = scoring.read_slices(path)["populations"]["0.5"]
        self.assertEqual(back["without_ordinal"].tolist(), [1])
        self.assertEqual(back["without_slope_u"].tolist(), population["without_slope_u"].tolist())

    def test_n1_the_slice_tail_counts_it_a_failure(self):
        base_bins = [AngleSliceIdentity.slice_data(None, 7001, s) for s in range(12)]
        bins = [AngleSliceIdentity.slice_data(None, 7001, s) for s in range(12)]
        for label in ("0.5", "0.7"):
            bins[3]["populations"][label]["without_ordinal"] = numpy.array([2], dtype=numpy.int64)
            bins[3]["populations"][label]["without_slope_u"] = numpy.array([0.1])     # slice 3, [0.075, 0.15]
        base = scoring.score_slices(7001, 11, base_bins, events_per_bin=4)
        found = scoring.score_slices(7001, 11, bins, events_per_bin=4)
        before = {(r.gate, r.statistic): r for r in base["records"]}
        after = {(r.gate, r.statistic): r for r in found["records"]}
        for name in scoring.PARAMETERS:
            gate = f"T07 angle slice 3 pull {name}"
            self.assertEqual(after[(gate, "tail")].readings["objects"], before[(gate, "tail")].readings["objects"] + 1)
            self.assertEqual(after[(gate, "tail")].readings["failures"], before[(gate, "tail")].readings["failures"] + 1)
            for statistic in ("trimmed-centre", "sigma68-width"):         # no pull value: centre and width as before
                self.assertEqual(after[(gate, statistic)].estimate, before[(gate, statistic)].estimate)
            self.assertGreater(found["estimates"][(gate, "tail")], base["estimates"][(gate, "tail")])
            self.assertGreater(found["rerun"][(gate, "tail")], base["rerun"][(gate, "tail")])
            for other in (0, 1, 2):
                key = (f"T07 angle slice {other} pull {name}", "tail")
                self.assertEqual(after[key].readings, before[key].readings)

    def test_n1_a_slice_file_without_the_count_is_missing(self):
        bins = [AngleSliceIdentity.slice_data(None, 7002, s) for s in range(12)]
        del bins[5]["populations"]["0.5"]["without_ordinal"]
        records = scoring.score_slices(7002, 11, bins, events_per_bin=4)["records"]
        self.assertEqual(len(records), 60)
        self.assertTrue(all(r.result == "inconclusive" and "required output missing" in r.reason and "(N1)" in r.reason for r in records))

    def test_the_slice_identity_is_the_cores_pooled_identity(self):
        identity = scoring.slice_identity(7002, 12, 1)
        self.assertIsInstance(identity, core.PooledIdentity)
        self.assertEqual(identity, core.PooledIdentity("T07", 7002, 12, 1, tuple(range(12)), scoring.slice_name(1)))
        self.assertEqual(identity.level, core.level_of_block(12))
        self.assertIn("angle slice 1 [-0.075, 0.0)", identity.label)
        self.assertIn("angle slice 3 [0.075, 0.15]", scoring.slice_identity(7001, 11, 3).label)
        development = scoring.slice_identity(7001, 1, 0)
        self.assertIsInstance(development, core.PooledIdentity)
        self.assertTrue(development.label.startswith(scoring.DEVELOPMENT_LABEL))
        self.assertEqual(development.level, core.level_of_block(11))
        self.assertEqual(core.seed_entropy(development), (core.BOOTSTRAP_DOMAIN, 7001, 1, core.POOL_STRATUM_BASE))
        bins = [AngleSliceIdentity.slice_data(None, 7001, s) for s in range(12)]
        bins[7] = AngleSliceIdentity.slice_data(None, 7001, 7, status="missing")
        records = scoring.score_slices(7001, 11, bins, events_per_bin=4)["records"]
        self.assertTrue(all("member stratum 7 is incomplete" in r.reason for r in records))   # layout.pool_status names the member

    def test_the_summary_passes_the_required_checks_to_the_core(self):
        records = evaluation_records()
        for fixture in (7001, 7002):
            records += scoring.score_slices(fixture, 11, [AngleSliceIdentity.slice_data(None, fixture, s) for s in range(12)], events_per_bin=4)["records"]
        seen = {}
        original = core.workflow_outcome

        def spy(*arguments, **keywords):
            seen.update(keywords, checks=list(arguments[2]))
            return original(*arguments, **keywords)
        core.workflow_outcome = spy
        try:
            outcome = scoring.summarize(records, every_check(), sensitivity_changes=[])
        finally:
            core.workflow_outcome = original
        self.assertEqual(tuple(seen["required_checks"]), scoring.required_checks())
        self.assertEqual(seen["checks"], every_check())                  # no padding of absent checks
        self.assertFalse(any("absent" in reason for reason in outcome.reasons))
        failing = [core.CheckResult(c.name, c.kind, "fail" if i == 0 else "pass") for i, c in enumerate(every_check())]
        self.assertEqual(scoring.summarize(records, failing, sensitivity_changes=[]).workflow_result, "fail")   # a check that ran and failed: a fail

    def test_an_absent_or_doubled_check_is_incomplete_never_a_fail(self):
        records = evaluation_records()
        for checks in ([], every_check()[1:], every_check() + every_check()[:1]):
            with self.assertRaises(scoring.ChecksIncomplete):
                scoring.summarize(records, checks, sensitivity_changes=[])

    def test_the_summary_command_reads_incomplete_by_its_own_result_line(self):
        records = evaluation_records()
        scoring.write_records(self.folder / "t07-score-7001-b11-s0.records.jsonl", records)
        checks = self.folder / "checks.json"
        checks.write_text(json.dumps([dataclasses.asdict(c) for c in every_check()[1:]]) + "\n", encoding="utf-8")
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = scoring.main(["summary", "--block", "11", "--scores", str(self.folder), "--checks", str(checks)])
        text = stream.getvalue()
        self.assertEqual(code, scoring.EXIT_INCOMPLETE)
        self.assertIn("SUMMARY INCOMPLETE T07 block 11", text)
        self.assertNotIn("SUMMARY T07 attempt", text)
        state, line = layout.classify_script_run(code, text, layout.RESULT_LINES["t07_evaluation_scoring.py"])
        self.assertEqual(state, "incomplete")                            # its own result line, exit 3: incomplete, never negative or crashed
        self.assertIn("RESULT t07-scoring summary incomplete:", line)


class MergeFixRound(unittest.TestCase):
    """Fix round 1 of the E6 merge review (d4-e6-merge-review.md, the coordinator's rulings): a check module that errors with no failure, or
    whose output holds an import or OS error, is a crash (exit 3), never a failed check (I2); a record defect is refused, apart from an absent
    check (M2); the bin's 70 % tail estimate counts primaries with no plane-1 result (nit)."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="t07-merge-fix-"))
        self.addCleanup(shutil.rmtree, self.folder)

    def outputs(self, **changed):
        found = {module: "Ran 20 tests in 1.0s\n\nOK\n" for _, _, module in scoring.T07_CHECKS}
        found.update({f"tests.adapters.{name}": text for name, text in changed.items()})
        return found

    def test_i2_a_module_that_errors_with_no_failure_is_a_crash(self):
        for text in ("Ran 20 tests in 1.0s\n\nFAILED (errors=1)\n", "Ran 20 tests in 1.0s\n\nFAILED (errors=2, skipped=1)\n"):
            with self.subTest(text=text):
                with self.assertRaises(scoring.ChecksCrashed):
                    scoring.checks_task(11, build="b", out=self.folder, module_runner=self.outputs(test_acts_finding=text).get)
                self.assertFalse((self.folder / "deterministic-checks.json").exists())   # no checks file: the summary stays incomplete

    def test_i2_an_import_or_file_system_error_traceback_is_a_crash_even_beside_a_failure(self):
        for error in ("ImportError: cannot import name 'test_acts_tracking' from 'tests.adapters'", "ModuleNotFoundError: No module named 'x'",
                      "PermissionError: [Errno 13] Permission denied: 'evidence'", "OSError: [Errno 30] Read-only file system: 'a'",
                      "FileNotFoundError: [Errno 2] No such file or directory: 'b'"):
            text = f"ERROR: test_x\n----\nTraceback (most recent call last):\n  File \"a.py\", line 1, in f\n{error}\n\nRan 20 tests in 1.0s\n\nFAILED (failures=1, errors=1)\n"
            with self.subTest(error=error.split(":")[0]):
                with self.assertRaises(scoring.ChecksCrashed):
                    scoring.checks_task(11, build="b", out=self.folder, module_runner=self.outputs(test_acts_scenarios=text).get)

    def test_i2_a_failure_without_a_setup_error_is_still_a_failed_check(self):
        text = "FAIL: test_x\nTraceback (most recent call last):\nAssertionError: 1 != 2\n\nRan 20 tests in 1.0s\n\nFAILED (failures=1, errors=1)\n"
        _, checks = scoring.checks_task(11, build="b", out=self.folder, module_runner=self.outputs(test_acts_truth_seeded=text).get)
        self.assertEqual({c.name.split(":")[0]: c.result for c in checks}["A39"], "fail")

    def test_n1_a_module_that_skips_is_a_crash_never_a_pass_or_a_fail(self):
        """E6 merge re-review N1 (the coordinator's ruling): a skip (a build or a variable not set) is a setup gap, so a crash: ChecksCrashed, no
        checks file, the task incomplete (exit 3)."""
        for text in ("Ran 64 tests in 1.0s\n\nOK (skipped=1)\n", "Ran 64 tests in 1.0s\n\nOK (skipped=64)\n",
                     "Ran 64 tests in 1.0s\n\nFAILED (failures=1, skipped=2)\n"):
            with self.subTest(text=text.splitlines()[-1]):
                with self.assertRaises(scoring.ChecksCrashed) as caught:
                    scoring.checks_task(11, build="b", out=self.folder, module_runner=self.outputs(test_acts_finding=text).get)
                self.assertIn("skip", str(caught.exception))
                self.assertFalse((self.folder / "deterministic-checks.json").exists())

    def test_n3_the_verdict_is_unittests_own_final_summary_only(self):
        """E6 merge re-review N3: earlier lines that start with OK or FAILED (a program's own output) are never the verdict; a module whose
        output has no unittest summary after its "Ran N tests" line (killed, or never reached it) is a crash."""
        early = "OK U_dev <= C (0.005) in all 3 bins\nFAILED to open a cache, retried\n"
        _, checks = scoring.checks_task(11, build="b", out=self.folder,
                                        module_runner=self.outputs(test_acts_scenarios=early + "Ran 20 tests in 1.0s\n\nFAILED (failures=1)\n").get)
        self.assertEqual({c.name.split(":")[0]: c.result for c in checks}["A05"], "fail")   # the summary, not the early "OK ..." line
        for text in (early, early + "Ran 20 tests in 1.0s\n", "Ran 20 tests in 1.0s\n\nOK and then a program's output\n"):
            with self.subTest(text=text[-30:]):
                with self.assertRaises(scoring.ChecksCrashed):
                    scoring.checks_task(11, build="b", out=self.folder, module_runner=self.outputs(test_acts_scenarios=text).get)

    def test_i2_the_checks_task_command_reads_a_crash_as_incomplete_exit_3(self):
        import contextlib
        import io
        original = scoring.checks_task

        def crashing(*arguments, **keywords):
            raise scoring.ChecksCrashed("tests.adapters.test_acts_finding: FAILED (errors=1) with no failure")
        scoring.checks_task = crashing
        try:
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                code = scoring.main(["checks-task", "--block", "11", "--build", "b", "--out", str(self.folder)])
        finally:
            scoring.checks_task = original
        self.assertEqual(code, scoring.EXIT_INCOMPLETE)
        self.assertIn("RESULT t07-scoring checks-task incomplete:", stream.getvalue())
        self.assertEqual(layout.classify_script_run(code, stream.getvalue(), scoring.RESULT_LINE)[0], "incomplete")

    def test_m2_a_record_defect_is_refused_not_an_absent_check(self):
        records = evaluation_records()
        for fixture in (7001, 7002):
            records += scoring.score_slices(fixture, 11, [AngleSliceIdentity.slice_data(None, fixture, s) for s in range(12)], events_per_bin=4)["records"]
        index = next(i for i, r in enumerate(records) if r.required)
        defective = list(records)
        defective[index] = dataclasses.replace(records[index], result="not-applicable")
        with self.assertRaises(scoring.ScoringError) as caught:
            scoring.summarize(defective, every_check(), sensitivity_changes=[])
        self.assertNotIsInstance(caught.exception, scoring.ChecksIncomplete)
        self.assertIn("record defect", str(caught.exception))
        with self.assertRaises(scoring.ChecksIncomplete) as absent:
            scoring.summarize(records, every_check()[1:], sensitivity_changes=[])
        self.assertIn("rerun", str(absent.exception))

    def test_nit_the_bins_tail_estimate_counts_a_primary_with_no_plane_one_result(self):
        files = hand_bin(self.folder)
        FixRoundOne.drop_state(self, files, "event-1-candidate-2")
        score = scoring.score_bin(scoring.bin_identity(7001, 1, 0), scoring.BinInputs(files["record"], files["product"], files["truth"]), events=4)
        by = {(r.gate, r.statistic): r for r in score["records"]}
        for gate in ("T07 track pull loc0", "T07 q/p pull positive"):
            with self.subTest(gate=gate):
                record = by[(gate, "tail")]
                self.assertEqual(score["estimates"][(gate, "tail")], record.readings["failures"] / record.readings["objects"])


if __name__ == "__main__":
    unittest.main()
