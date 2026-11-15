"""adapters/acts-tracking: the exact check of section 7's truth-seeded run on clean, against an independent linear Kalman replica (D1 stage 6c brief).

The user, 2026-11-08 (decisions.md, "After stage 6b: the user's choices"): "exact replica check, keep §7". The module's clean tolerance (0, 0, 3 per stratum by occupancy,
test_acts_truth_seeded.CLEAN_LOST_LIMIT_OF_LEVEL) rested on the belief that only close pairs lose clean tracks, refuted by job 7512409; it stays there as a record. In its place,
per clean stratum of block 1, read from the files the truth-seeded step keeps (each stratum's data file, truth file and truth-seeded record):

- A. acts: the particles ACTS's truth-seeded run loses as seed-or-finding (test_acts_finding.loss_category); replica: the particles the replica loses
  (fixture_tools/t07_kalman_replica.py) under the same start, cut and hole stop, read from that run's own record. A particle in acts and not in replica fails. Its line marks any
  plane where the replica took a hole while a foreign hit passed: "replica path not available to ACTS", since ACTS makes no hole branch when a measurement passes. Still a failure.
- B. A particle in replica that ACTS keeps (it has a primary) passes only if the replica listed a foreign measurement under the cut on a plane its branch reached, and ACTS's primary
  track for the particle holds that hit key on that plane: ACTS took the split (coordinator's ruling on review M1; "a foreign hit under the cut" alone excused about 19 % of o3
  particles in job 7512409's stratum 8). Otherwise it fails, or is borderline under C. Each is printed. A particle both lose, ACTS in another category than seed-or-finding, is
  not a B case: it is printed as lost by both, and D or the rule on other categories bounds it.
- C. Borderline: a case of A, or of B that fails its split test, whose deciding chi2 in the replica (the own hit's chi2 nearest the cut, over the planes reached) lies within
  BORDERLINE_CHI2 of the cut is printed as borderline, counted, and does not fail. More than BORDERLINE_MOST over the 12 strata fails. Basis (coordinator's ruling on review M2):
  in job 7512409's traces the replica's chi2 differs from ACTS's by about 1e-3 relative, at most 0.0068 below chi2 14 and up to 0.0128 within 0.33 of the cut; 0.15 is about ten
  times that agreement near the cut, and the cap of 2 bounds what it can excuse. Superseded: 0.01 on "agreed to about 1e-3", which was one times the agreement near the cut.
- D. Ambiguity losses: at most 3 per o3 stratum, none at o1 and o2 (the user's words, unchanged).
- E. Printed per stratum: |acts|, |replica|, their intersection, the B and C cases, and each particle in both.
- Not in the user's words, stated here before the job: a clean loss of any other category (search-truncated, fit-failed, ...) is in neither A nor D, so it would escape both; it
  fails here. Job 7512409 had none.

Lines start TS-REPLICA-. The predictions are in the D1 stage 6c report, fixed before the job. The judges and the replica's own tests need no build and run in seconds; the kept-strata
class needs HEP_ACTS_TRACKING_EVIDENCE, which the build job sets, and fails, not skips, when a stratum's files are missing. The job runs this module after its truth-seeded step.
Run from the plugin root: python -m unittest tests.adapters.test_acts_truth_seeded_replica -v
"""
from __future__ import annotations

import concurrent.futures
import math
import os
import unittest
from collections import Counter
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests
from tests.adapters import test_acts_refit_field as refit_tests
from tests.adapters import test_acts_truth_seeded as seeded_tests

import t07_kalman_replica as replica  # noqa: E402  fixture_tools is on the path through test_acts_finding

finding_record, truth_files, fixture_files = finding_tests.finding_record, finding_tests.truth_files, finding_tests.fixture_files

EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
RUNNABLE = bool(EVIDENCE_DIR)
NOT_RUNNABLE = "needs the T07 build job: HEP_ACTS_TRACKING_EVIDENCE, holding the clean files its truth-seeded step keeps"
FIXTURE_CONSTANTS = finding_tests.NATIVE / "t07_fixture_constants.hpp"
TRACK_FINDING_HEADER = finding_tests.NATIVE / "track_finding.hpp"

SEED_OR_FINDING, AMBIGUITY = "seed-or-finding", "ambiguity"
BORDERLINE_CHI2 = 0.15  # C: about ten times the 0.0128 seen near the cut in job 7512409 (review M2); superseded value 0.01, from a wrong 1e-3 basis
BORDERLINE_MOST = 2     # C: over the 12 clean strata
AMBIGUITY_LIMIT_OF_LEVEL = (0, 0, 3)  # D: the user's words
CLEAN_STRATA = tuple(range(12))
# The helix carried plane to plane against the truth crossings. It reads about 2.9e-7 mm at 1.5-3 GeV and falls as about 1/p^2 (5.5e-8, 1.2e-8, 2.7e-9 mm by bin in job
# 7512409); what it is meant to catch, a wrong field sign or frame, is off by twice the sagitta, 0.03 mm or more at 24 GeV over 50 mm.
FRAME_LIMIT_MM = 1e-5
# Review m3: the loc0, phi and q/p block against ACTS itself. Job 7512409, clean stratum 0, event 1556, particle 5: ACTS's "No measurement candidate. Return empty chi2=" at
# planes 6, 7 and 8 (d1-stage6b-reading.md, Task 2). The replica read 17.406, 16.082 and 19.662 there.
REGRESSION_STRATUM, REGRESSION_KEY, REGRESSION_HOLES = 0, (1556, 5), ((6, 17.399), (7, 16.069), (8, 19.637))
REGRESSION_AGREEMENT = 0.05


# ---- The replica's inputs, from the files.

def replica_settings(configuration: dict, data_header: dict) -> replica.ReplicaSettings:
    """The cut, holes and start from the record's configuration lines, the hit sigmas from the data file the run read, the geometry from t07_fixture_constants.hpp."""
    return replica.settings_from(configuration, (data_header["sigma_loc0_mm"], data_header["sigma_loc1_mm"]), FIXTURE_CONSTANTS.read_text(encoding="utf-8"),
                                 refit_tests.GEV_PER_TESLA_MM)


def acts_losses(truth_events, record: dict) -> dict:
    """(event ordinal, particle index) to category, for every reconstructable particle the truth-seeded run left without a primary: test_acts_truth_seeded's scoring."""
    lost = {}
    for ordinal, (truth_event, event) in enumerate(zip(truth_events, record["events"])):
        particles = finding_tests.particles_of(truth_event)
        for index in finding_tests.scored_event(finding_tests.tracks_of(event), particles)["lost"]:
            lost[(ordinal, index)] = finding_tests.loss_category(particles[index], event)
    return lost


def acts_primary_hits(truth_events, data_events, record: dict, wanted) -> dict:
    """(event ordinal, particle index) to the set of (plane, hit key) of the particle's primary track in ACTS's record, for the wanted particles that have one (review M1)."""
    by_event = {}
    for ordinal, particle in wanted:
        by_event.setdefault(ordinal, []).append(particle)
    found = {}
    for ordinal, particles_wanted in by_event.items():
        event = record["events"][ordinal]
        tracks = finding_tests.tracks_of(event)
        primaries = finding_tests.scored_event(tracks, finding_tests.particles_of(truth_events[ordinal]))["primaries"]
        hits = data_events[ordinal]["hits"]
        plane_of = {int(key): int(plane) for key, plane in zip(hits["hit_key"], hits["plane"])}
        for particle in particles_wanted:
            if particle in primaries:
                found[(ordinal, particle)] = {(plane_of[int(key)], int(key)) for key in tracks[primaries[particle]]["hit_keys"]}
    return found


def replica_results(truth_events, data_events, settings: replica.ReplicaSettings) -> dict:
    """(event ordinal, particle index) to ParticleReplica, for the reconstructable particles (section 7: at least LEAST_HITS hits). Every particle's hits count as foreign to the rest."""
    per_event = replica.replica_of_events([(truth_event["tracks"], data_event["hits"]) for truth_event, data_event in zip(truth_events, data_events)], settings, truth_files.NO_HIT_KEY)
    results = {}
    for ordinal, (truth_event, event_results) in enumerate(zip(truth_events, per_event)):
        for index, particle in enumerate(finding_tests.particles_of(truth_event)):
            if len(particle["hit_keys"]) >= finding_tests.LEAST_HITS:
                results[(ordinal, index)] = event_results[index]
    return results


# ---- The judge.

def taken_splits(result: replica.ParticleReplica, acts_hits) -> list:
    """The foreign hits the replica listed that ACTS's primary track holds, on the plane where they were listed: the split ACTS took."""
    return sorted({(plane, hit) for plane, hit, _ in result.foreign} & set(acts_hits or ()))


def stratum_verdict(acts: dict, replicas: dict, cut: float, acts_hits: dict) -> dict:
    """A to E for one stratum. acts: (ordinal, particle) to ACTS's loss category; replicas: (ordinal, particle) to the ParticleReplica of every reconstructable particle;
    acts_hits: (ordinal, particle) to the (plane, hit key) set of ACTS's primary track, for at least every particle the replica loses and ACTS keeps."""
    acts_lost = {key for key, category in acts.items() if category == SEED_OR_FINDING}
    replica_lost = {key for key, result in replicas.items() if not result.kept}
    borderline, a_failures, b_split, b_failures, lost_other = [], [], [], [], []
    for key in sorted(acts_lost - replica_lost):
        margin = replicas[key].deciding_margin(cut)
        (borderline if margin <= BORDERLINE_CHI2 else a_failures).append((key, "A", margin))
    for key in sorted(replica_lost - acts_lost):
        margin = replicas[key].deciding_margin(cut)
        if key in acts:
            lost_other.append((key, f"lost-by-both-acts-{acts[key]}", margin))
        elif taken_splits(replicas[key], acts_hits.get(key)):
            b_split.append((key, "B", margin))
        else:
            (borderline if margin <= BORDERLINE_CHI2 else b_failures).append((key, "B", margin))
    categories = Counter(acts.values())
    return {"acts": acts_lost, "replica": replica_lost, "both": acts_lost & replica_lost, "a_failures": a_failures, "b_split": b_split, "b_failures": b_failures,
            "borderline": borderline, "lost_other": lost_other, "ambiguity": categories[AMBIGUITY],
            "other": {name: count for name, count in sorted(categories.items()) if name not in (SEED_OR_FINDING, AMBIGUITY)}}


def borderline_within(counts) -> bool:
    """C over the 12 strata."""
    return sum(counts) <= BORDERLINE_MOST


def ambiguity_within(stratum: int, count: int) -> bool:
    """D: the stratum's occupancy level is its index modulo 3."""
    return count <= AMBIGUITY_LIMIT_OF_LEVEL[stratum % 3]


def unavailable_planes(result: replica.ParticleReplica) -> list:
    """Review m1: planes where the replica took a hole while a foreign hit passed there. ACTS makes no hole branch when a measurement passes, so that path is not ACTS's."""
    return sorted({plane for plane, _ in result.holes} & {plane for plane, _, _ in result.foreign})


def case_text(key, kind: str, result: replica.ParticleReplica, cut: float, acts_hits=None) -> str:
    holes = " ".join(f"p{plane}:{value:.3f}" for plane, value in result.holes) or "none"
    foreign = " ".join(f"p{plane}:hit{hit}:{value:.3f}" for plane, hit, value in result.foreign) or "none"
    text = (f"event {key[0]} particle {key[1]} {kind} replica {'kept' if result.kept else 'lost'} stop plane {result.stop_plane or '-'} measurements {result.measurements} "
            f"holes (plane:chi2) {holes} deciding margin {result.deciding_margin(cut):.4f} foreign under the cut (plane:hit:chi2) {foreign}")
    if kind == "A" and unavailable_planes(result):
        text += " replica path not available to ACTS at planes " + " ".join(f"p{plane}" for plane in unavailable_planes(result))
    if kind == "B":
        taken = taken_splits(result, acts_hits)
        text += " split taken by ACTS's track (plane:hit) " + (" ".join(f"p{plane}:hit{hit}" for plane, hit in taken) or "none")
    return text


def stratum_lines(stratum: int, verdict: dict, replicas: dict, cut: float, acts_hits: dict) -> list:
    lines = [f"TS-REPLICA-STRATUM clean stratum {stratum} acts (seed-or-finding) {len(verdict['acts'])} replica {len(verdict['replica'])} both {len(verdict['both'])} "
             f"A {len(verdict['a_failures'])} B with a split ACTS took {len(verdict['b_split'])} B without {len(verdict['b_failures'])} borderline {len(verdict['borderline'])} "
             f"lost by both in another category {len(verdict['lost_other'])} ambiguity {verdict['ambiguity']} (limit {AMBIGUITY_LIMIT_OF_LEVEL[stratum % 3]}) "
             f"other categories {verdict['other']}"]
    for name in ("a_failures", "b_split", "b_failures", "borderline", "lost_other"):
        for key, kind, _ in verdict[name]:
            lines.append(f"TS-REPLICA-CASE clean stratum {stratum} {name} {case_text(key, kind, replicas[key], cut, acts_hits.get(key))}")
    for key in sorted(verdict["both"]):
        lines.append(f"TS-REPLICA-BOTH clean stratum {stratum} {case_text(key, 'both', replicas[key], cut)}")
    return lines


def lost_result(chi2=(1.0, 1.0, 17.0, 18.0, 19.0), foreign=()) -> replica.ParticleReplica:
    holes = tuple((plane + 1, value) for plane, value in enumerate(chi2) if value >= 16.0)
    return replica.ParticleReplica(kept=False, stop_plane=len(chi2), own_chi2=tuple(chi2) + (None,) * (8 - len(chi2)), holes=holes, foreign=tuple(foreign),
                                   measurements=len(chi2) - len(holes))


def kept_result(chi2=(1.0,) * 8) -> replica.ParticleReplica:
    return replica.ParticleReplica(kept=True, stop_plane=0, own_chi2=tuple(chi2), holes=(), foreign=(), measurements=8)


class TheJudge(unittest.TestCase):
    """Each rule, driven with honest input and one defect."""

    def setUp(self):
        self.replicas = {(0, 0): lost_result(), (0, 1): kept_result(), (1, 0): kept_result((2.0,) * 8)}
        # job 7512409's stratum 8 event 2884 particle 22: a foreign plane-1 hit, 15, which ACTS's kept track holds
        self.split = lost_result(foreign=((1, 15, 0.809), (2, 51, 0.205)))
        self.acts_track = {(1, 15), (2, 52), (3, 88), (4, 123), (5, 159), (6, 195), (7, 231), (8, 267)}

    def verdict(self, acts, replicas=None, acts_hits=None):
        return stratum_verdict(acts, self.replicas if replicas is None else replicas, 16.0, acts_hits or {})

    def test_equal_sets_pass(self):
        verdict = self.verdict({(0, 0): SEED_OR_FINDING})
        self.assertEqual((verdict["acts"], verdict["replica"], verdict["both"]), ({(0, 0)}, {(0, 0)}, {(0, 0)}))
        self.assertEqual(verdict["a_failures"] + verdict["b_split"] + verdict["b_failures"] + verdict["borderline"] + verdict["lost_other"], [])

    def test_a_loss_the_replica_keeps_fails(self):
        verdict = self.verdict({(0, 0): SEED_OR_FINDING, (0, 1): SEED_OR_FINDING})
        self.assertEqual([key for key, _, _ in verdict["a_failures"]], [(0, 1)])

    def test_an_a_case_marks_a_replica_path_acts_does_not_have(self):
        """Review m1: a replica hole at plane 3 where a foreign hit passed. Still a failure; the line names the plane."""
        kept_with_hole = replica.ParticleReplica(kept=True, stop_plane=0, own_chi2=(1.0, 1.0, 17.0) + (1.0,) * 5, holes=((3, 17.0),), foreign=((3, 40, 2.0),), measurements=7)
        replicas = {**self.replicas, (0, 1): kept_with_hole}
        verdict = self.verdict({(0, 0): SEED_OR_FINDING, (0, 1): SEED_OR_FINDING}, replicas)
        self.assertEqual([key for key, _, _ in verdict["a_failures"]], [(0, 1)])
        self.assertIn("replica path not available to ACTS at planes p3", case_text((0, 1), "A", kept_with_hole, 16.0))
        self.assertNotIn("not available", case_text((0, 0), "A", lost_result(), 16.0))

    def test_only_seed_or_finding_losses_are_compared(self):
        verdict = self.verdict({(0, 0): SEED_OR_FINDING, (0, 1): AMBIGUITY})
        self.assertEqual((verdict["a_failures"], verdict["ambiguity"], verdict["other"]), ([], 1, {}))
        verdict = self.verdict({(0, 0): SEED_OR_FINDING, (0, 1): "search-truncated"})
        self.assertEqual((verdict["a_failures"], verdict["other"]), ([], {"search-truncated": 1}))

    def test_an_extra_replica_loss_passes_only_where_acts_took_the_split(self):
        """Review M1: the foreign hit must be on ACTS's own track, on the plane where the replica listed it."""
        self.assertEqual([key for key, _, _ in self.verdict({})["b_failures"]], [(0, 0)])  # no foreign hit at all
        replicas = {**self.replicas, (0, 0): self.split}
        verdict = self.verdict({}, replicas, {(0, 0): self.acts_track})
        self.assertEqual(([key for key, _, _ in verdict["b_split"]], verdict["b_failures"]), ([(0, 0)], []))
        for name, track in {"the listed hit is not on ACTS's track": self.acts_track - {(1, 15)} | {(1, 16)},
                            "the hit is on ACTS's track at another plane": self.acts_track - {(1, 15)} | {(3, 15)}, "ACTS's track is not known": None}.items():
            with self.subTest(case=name):
                verdict = self.verdict({}, replicas, {} if track is None else {(0, 0): track})
                self.assertEqual(([key for key, _, _ in verdict["b_failures"]], verdict["b_split"]), ([(0, 0)], []))

    def test_a_particle_both_lose_in_another_category_is_not_a_b_case(self):
        verdict = self.verdict({(0, 0): AMBIGUITY})
        self.assertEqual((verdict["b_failures"], verdict["b_split"], [key for key, _, _ in verdict["lost_other"]], verdict["ambiguity"]), ([], [], [(0, 0)], 1))

    def test_a_borderline_disagreement_is_counted_and_does_not_fail(self):
        near = {**self.replicas, (0, 0): lost_result((1.0, 1.0, 16.1, 18.0, 19.0))}
        verdict = self.verdict({}, near)
        self.assertEqual((verdict["b_failures"], [key for key, _, _ in verdict["borderline"]]), ([], [(0, 0)]))
        kept_near = {**self.replicas, (0, 1): kept_result((1.0,) * 7 + (15.9,))}
        verdict = self.verdict({(0, 0): SEED_OR_FINDING, (0, 1): SEED_OR_FINDING}, kept_near)
        self.assertEqual((verdict["a_failures"], [key for key, _, _ in verdict["borderline"]]), ([], [(0, 1)]))
        far = {**self.replicas, (0, 0): lost_result((1.0, 1.0, 16.16, 18.0, 19.0))}
        verdict = self.verdict({}, far)
        self.assertEqual((len(verdict["b_failures"]), verdict["borderline"]), (1, []))
        listed_not_taken = {**self.replicas, (0, 0): lost_result((1.0, 1.0, 16.1, 18.0, 19.0), foreign=((1, 15, 0.8),))}
        self.assertEqual(len(self.verdict({}, listed_not_taken, {(0, 0): {(1, 16)}})["borderline"]), 1)

    def test_more_than_two_borderline_cases_fail(self):
        self.assertTrue(borderline_within([1, 1, 0] + [0] * 9))
        self.assertFalse(borderline_within([1, 1, 1] + [0] * 9))

    def test_ambiguity_losses_by_level(self):
        cases = ((2, 3), (2, 4), (0, 0), (0, 1), (1, 1), (11, 3), (9, 0))
        self.assertEqual([ambiguity_within(stratum, count) for stratum, count in cases], [True, False, True, False, False, True, True])

    def test_the_lines_name_every_case(self):
        replicas = {**self.replicas, (1, 0): self.split}
        lines = stratum_lines(8, self.verdict({(0, 0): SEED_OR_FINDING}, replicas, {(1, 0): self.acts_track}), replicas, 16.0, {(1, 0): self.acts_track})
        self.assertTrue(lines[0].startswith("TS-REPLICA-STRATUM clean stratum 8 acts (seed-or-finding) 1 replica 2 both 1 A 0 B with a split ACTS took 1 B without 0 borderline 0"))
        self.assertIn("p1:hit15:0.809", lines[1])
        self.assertIn("split taken by ACTS's track (plane:hit) p1:hit15", lines[1])
        self.assertTrue(lines[2].startswith("TS-REPLICA-BOTH clean stratum 8 event 0 particle 0 both replica lost stop plane 5"))


# ---- The replica on a synthetic event, against arithmetic done by hand.

def synthetic_settings(**changes) -> replica.ReplicaSettings:
    """The cut, holes and least measurements as track_finding.hpp holds them, written as a record writes them, then section 7's start as the truth-seeded record writes it."""
    header = TRACK_FINDING_HEADER.read_text(encoding="utf-8")
    configuration = {name: "%.17g" % finding_tests.header_constant(header, name) for name in ("finding_chi2_cut", "finding_most_holes", "finding_least_measurements")}
    configuration.update(seeded_tests.START_CONFIGURATION)
    configuration.update(changes)
    sigma = replica.header_constant(FIXTURE_CONSTANTS.read_text(encoding="utf-8"), "hit_sigma_mm")
    return replica.settings_from(configuration, (sigma, sigma), FIXTURE_CONSTANTS.read_text(encoding="utf-8"), refit_tests.GEV_PER_TESLA_MM)


def helix_track(settings, start, offsets, first_key: int):
    """A truth row whose crossings follow the helix from start (loc0, loc1, phi, theta, q/p), with hits at crossing + offsets (planes, 2), keys first_key, first_key + 1, ..."""
    track = numpy.zeros(1, dtype=truth_files.TRACK)
    state = numpy.asarray(start, float)
    for plane in range(settings.planes):
        if plane:
            state = replica.propagate(state, settings.plane_spacing_mm, settings.turn_per_qop_mm)
        track["crossings"][0, plane] = state[:4]
    track["q_over_p"] = start[4]
    track["hit_keys"][0] = numpy.arange(first_key, first_key + settings.planes)
    hits = [(first_key + plane, plane + 1, *(track["crossings"][0, plane, :2] + offsets[plane])) for plane in range(settings.planes)]
    return track, hits


def hits_array(rows):
    hits = numpy.zeros(len(rows), dtype=fixture_files.HIT)
    for index, row in enumerate(rows):
        hits[index] = row
    return hits


def by_hand(settings, crossings, q_over_p: float, along_v) -> dict:
    """Planes 1 to 3 along loc1 alone, for a particle at theta = pi/2 whose loc0 hits sit on its truth: there loc1 = v and theta form a system of their own (d loc1 / d theta = -s,
    the arc length; d loc0 / d theta = 0; d loc1 / d (phi, q/p) = 0, all from cos theta = 0), and the loc0 part has no residual, so the chi2 is the loc1 part. Scalars, no matrices."""
    p, q, h = settings.start_sigmas[1] ** 2, settings.start_sigmas[3] ** 2, settings.hit_sigmas_mm[1] ** 2
    arcs = [(crossings[plane + 1, 2] - crossings[plane, 2]) / (q_over_p * settings.turn_per_qop_mm) for plane in range(2)]
    a1, a2 = -arcs[0], -arcs[1]
    e1, e2, e3 = along_v
    s1 = p + h
    v1, pvv1 = p * e1 / s1, p * h / s1  # plane 1 update; theta untouched, no correlation
    pvv, pvt, ptt = pvv1 + a1 * a1 * q, a1 * q, q  # carried to plane 2; the angle estimate is 0, so v is carried unchanged
    s2 = pvv + h
    r2 = e2 - v1
    v2, t2 = v1 + pvv / s2 * r2, pvt / s2 * r2
    pvv, pvt, ptt = pvv - pvv * pvv / s2, pvt - pvv * pvt / s2, ptt - pvt * pvt / s2
    v3, s3 = v2 + a2 * t2, pvv + 2.0 * a2 * pvt + a2 * a2 * ptt + h
    return {"chi2_1": e1 * e1 / s1, "chi2_2": r2 * r2 / s2, "chi2_3": (e3 - v3) ** 2 / s3, "v3": v3, "s3": s3}


class ReplicaOnASyntheticEvent(unittest.TestCase):
    """Two particles: A at theta = pi/2, phi = 0, 2 GeV; B 40 mm away with another direction and charge. Every hit of B sits on its truth."""

    START_A = (0.0, 0.0, 0.0, math.pi / 2.0, 0.5)
    START_B = (40.0, 20.0, 0.05, 1.5, -0.25)

    def setUp(self):
        self.settings = synthetic_settings()

    def run_event(self, offsets_a, extra_hits=(), missing_planes_a=()):
        track_a, hits_a = helix_track(self.settings, self.START_A, offsets_a, 0)
        for plane in missing_planes_a:  # the particle left no hit there
            track_a["hit_keys"][0, plane - 1] = truth_files.NO_HIT_KEY
        hits_a = [hit for hit in hits_a if hit[1] not in missing_planes_a]
        track_b, hits_b = helix_track(self.settings, self.START_B, numpy.zeros((8, 2)), 100)
        tracks = numpy.concatenate([track_a, track_b])
        result = replica.replica_of_events([(tracks, hits_array(hits_a + hits_b + list(extra_hits)))], self.settings, truth_files.NO_HIT_KEY)[0]
        return tracks, result

    def offsets_along_v(self, values):
        offsets = numpy.zeros((8, 2))
        offsets[:len(values), 1] = values
        return offsets

    def test_the_settings_are_the_records(self):
        print(f"TS-REPLICA-SETTINGS synthetic, from track_finding.hpp and section 7's start: {replica.settings_text(self.settings)}", flush=True)
        header = TRACK_FINDING_HEADER.read_text(encoding="utf-8")
        self.assertEqual((self.settings.chi2_cut, self.settings.most_holes, self.settings.least_measurements),
                         tuple(finding_tests.header_constant(header, name) for name in ("finding_chi2_cut", "finding_most_holes", "finding_least_measurements")))
        self.assertEqual(self.settings.start_sigmas, tuple(float(seeded_tests.START_CONFIGURATION[f"truth_start_sigma_{name}"]) for name in ("loc0_mm", "loc1_mm", "phi", "theta")))
        with self.assertRaises(ValueError):
            synthetic_settings(truth_start_plane="2")
        with self.assertRaisesRegex(ValueError, "phi's sigma for both"):  # review n2
            synthetic_settings(truth_start_sigma_theta="0.02")
        configuration = dict(seeded_tests.START_CONFIGURATION, finding_chi2_cut="16", finding_least_measurements="6")
        with self.assertRaisesRegex(ValueError, "finding_most_holes"):
            replica.settings_from(configuration, (0.02, 0.02), FIXTURE_CONSTANTS.read_text(encoding="utf-8"), refit_tests.GEV_PER_TESLA_MM)
        self.assertEqual(synthetic_settings(finding_chi2_cut="25").chi2_cut, 25.0)  # the cut follows the record, not this module

    def test_the_chi2_at_planes_2_and_3_by_hand(self):
        along_v = (0.01, 0.3, 0.65)
        tracks, result = self.run_event(self.offsets_along_v(along_v))
        expected = by_hand(self.settings, tracks["crossings"][0], float(tracks["q_over_p"][0]), along_v)
        print(f"TS-REPLICA-HAND chi2 planes 1 2 3: by hand {expected['chi2_1']:.6f} {expected['chi2_2']:.6f} {expected['chi2_3']:.6f}, replica "
              f"{result[0].own_chi2[0]:.6f} {result[0].own_chi2[1]:.6f} {result[0].own_chi2[2]:.6f}", flush=True)
        self.assertGreater(expected["chi2_2"], 0.1)
        self.assertGreater(expected["chi2_3"], 0.1)
        for plane in range(3):
            self.assertAlmostEqual(result[0].own_chi2[plane] / expected[f"chi2_{plane + 1}"], 1.0, delta=1e-6)
        self.assertLess(max(result[1].own_chi2), 1e-12)  # B's hits sit on its truth

    def test_a_hit_past_the_cut_is_a_hole(self):
        planned = by_hand(self.settings, *self.crossings_of_a(), (0.0, 0.0, 0.0))
        past = planned["v3"] + math.sqrt((self.settings.chi2_cut + 1.0) * planned["s3"])
        _, result = self.run_event(self.offsets_along_v((0.0, 0.0, past)))
        self.assertEqual([plane for plane, _ in result[0].holes], [3])
        self.assertAlmostEqual(result[0].holes[0][1], self.settings.chi2_cut + 1.0, delta=1e-5)
        self.assertEqual((result[0].kept, result[0].stop_plane, result[0].measurements), (True, 0, 7))
        inside = planned["v3"] + math.sqrt((self.settings.chi2_cut - 1.0) * planned["s3"])
        taken = self.run_event(self.offsets_along_v((0.0, 0.0, inside)))[1][0]
        self.assertAlmostEqual(taken.own_chi2[2], self.settings.chi2_cut - 1.0, delta=1e-5)
        self.assertNotIn(3, [plane for plane, _ in taken.holes])  # taken; it then pulls the branch off the later hits, which sit on the truth

    def crossings_of_a(self):
        track, _ = helix_track(self.settings, self.START_A, numpy.zeros((8, 2)), 0)
        return track["crossings"][0], float(track["q_over_p"][0])

    def test_three_holes_stop_the_branch_and_two_do_not(self):
        _, result = self.run_event(self.offsets_along_v((0.0, 0.0, 5.0, 5.0, 5.0)))
        self.assertEqual((result[0].kept, result[0].stop_plane, result[0].measurements), (False, 5, 2))
        self.assertEqual([plane for plane, _ in result[0].holes], [3, 4, 5])
        self.assertEqual(result[0].own_chi2[5:], (None, None, None))
        self.assertTrue(result[1].kept)
        _, result = self.run_event(self.offsets_along_v((0.0, 0.0, 5.0, 5.0)))
        self.assertEqual((result[0].kept, result[0].stop_plane, result[0].measurements), (True, 0, 6))

    def test_a_plane_without_an_own_hit_is_a_hole(self):
        """Review n4: no hit at plane 4 gives chi2 inf there and a hole; three such planes stop the branch."""
        _, result = self.run_event(numpy.zeros((8, 2)), missing_planes_a=(4,))
        self.assertTrue(math.isinf(result[0].own_chi2[3]))
        self.assertEqual(([plane for plane, _ in result[0].holes], result[0].kept, result[0].measurements), ([4], True, 7))
        _, result = self.run_event(numpy.zeros((8, 2)), missing_planes_a=(3, 4, 6))
        self.assertEqual((result[0].kept, result[0].stop_plane, result[0].measurements), (False, 6, 3))
        self.assertTrue(result[1].kept)

    def test_a_foreign_hit_in_the_window_is_a_possible_split(self):
        crossings, _ = self.crossings_of_a()
        near = (900, 4, crossings[3, 0], crossings[3, 1] + 0.03)
        far = (901, 4, crossings[3, 0], crossings[3, 1] + 1.0)
        tracks, result = self.run_event(numpy.zeros((8, 2)), extra_hits=(near, far))
        self.assertEqual([(plane, hit) for plane, hit, _ in result[0].foreign], [(4, 900)])
        self.assertLess(result[0].foreign[0][2], self.settings.chi2_cut)
        self.assertTrue(result[0].kept)  # the own hit passes too: ACTS would branch there
        self.assertEqual(result[1].foreign, ())  # A's hits and the extra ones are 40 mm from B
        late = (902, 7, crossings[6, 0], crossings[6, 1])
        _, result = self.run_event(self.offsets_along_v((0.0, 0.0, 5.0, 5.0, 5.0)), extra_hits=(late,))
        self.assertEqual(result[0].foreign, ())  # plane 7 is after the stop at plane 5: not reached

    def test_a_wrong_field_sign_is_seen_by_the_frame_check(self):
        tracks, _ = self.run_event(numpy.zeros((8, 2)))
        self.assertLess(replica.frame_residual_mm(tracks["crossings"], tracks["q_over_p"], self.settings), 1e-12)
        flipped = replica.ReplicaSettings(**{**self.settings.__dict__, "field_tesla": -self.settings.field_tesla})
        self.assertGreater(replica.frame_residual_mm(tracks["crossings"], tracks["q_over_p"], flipped), 0.1)  # twice the 0.19 mm sagitta of 2 GeV over 50 mm


# ---- The kept clean strata of the build job.

def kept_stratum(folder: Path, stratum: int) -> dict:
    """One clean stratum from the truth-seeded step's kept files: ACTS's losses, the replica's, and the verdict."""
    data_file, truth_file, record_file = (folder / name for name in (f"clean-{stratum}.t07data", f"clean-{stratum}.t07truth", f"truth-seeded-clean-{stratum}.record"))
    missing = [path.name for path in (data_file, truth_file, record_file) if not path.is_file()]
    if missing:
        return {"stratum": stratum, "missing": missing}
    record = seeded_tests.parse_truth_seeded_record(record_file.read_text(encoding="utf-8"))
    truth_events = list(truth_files.iter_truth_events(truth_file))
    data_events = list(fixture_files.iter_data_events(data_file))
    settings = replica_settings(record["configuration"], fixture_files.read_data_header(data_file))
    replicas = replica_results(truth_events, data_events, settings)
    acts = acts_losses(truth_events, record)
    acts_hits = acts_primary_hits(truth_events, data_events, record, [key for key, result in replicas.items() if not result.kept])
    crossings = numpy.concatenate([event["tracks"]["crossings"] for event in truth_events])
    q_over_p = numpy.concatenate([event["tracks"]["q_over_p"] for event in truth_events])
    verdict = stratum_verdict(acts, replicas, settings.chi2_cut, acts_hits)
    data_sha256, truth_header = fixture_files.file_sha256(data_file), truth_files.read_truth_header(truth_file)
    # Review m2: the truth file names this data file and is clean's, block 1, this stratum; the three files hold the same number of events, so no zip truncates.
    bound = {"record names the data file": record["header"]["data_sha256"] == data_sha256, "truth names the data file": truth_header["data_sha256"] == data_sha256,
             "truth is clean's": truth_header["fixture_id"] == finding_tests.FIXTURE_IDS["clean"], "truth is block 1": truth_header["block"] == finding_tests.TUNING_BLOCK,
             "truth is this stratum": truth_header["stratum"] == stratum,
             "events agree": len(truth_events) == len(data_events) == len(record["events"]) == finding_tests.EVENTS_PER_BIN}
    return {"stratum": stratum, "missing": [], "events": len(record["events"]), "bound": bound, "settings": settings, "verdict": verdict,
            "lines": stratum_lines(stratum, verdict, replicas, settings.chi2_cut, acts_hits), "frame_mm": replica.frame_residual_mm(crossings, q_over_p, settings),
            "reconstructable": len(replicas), "regression": replicas.get(REGRESSION_KEY) if stratum == REGRESSION_STRATUM else None}


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class CleanLossesEqualTheReplica(unittest.TestCase):
    """A to E on the 12 clean strata of block 1, 3,000 events each, as the truth-seeded step kept them. Replaces test_clean_losses_within_the_tolerance."""

    @classmethod
    def setUpClass(cls):
        folder = Path(EVIDENCE_DIR) / seeded_tests.KEPT_FOLDER
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            cls.readings = list(pool.map(lambda stratum: kept_stratum(folder, stratum), CLEAN_STRATA))
        cls.found = [item for item in cls.readings if not item["missing"]]
        for item in cls.readings:
            if item["missing"]:
                print(f"TS-REPLICA-MISSING clean stratum {item['stratum']}: {' '.join(item['missing'])}", flush=True)
        if cls.found:
            print(f"TS-REPLICA-SETTINGS from the truth-seeded record and the data file: {replica.settings_text(cls.found[0]['settings'])}", flush=True)
        for item in cls.found:
            print(f"TS-REPLICA-READ clean stratum {item['stratum']} events {item['events']} reconstructable {item['reconstructable']} files bound {all(item['bound'].values())} "
                  f"frame residual mm {item['frame_mm']:.3g}", flush=True)
            for line in item["lines"]:
                print(line, flush=True)
        verdicts = [item["verdict"] for item in cls.found]
        print(f"TS-REPLICA-TOTAL strata {len(cls.found)} acts {sum(len(v['acts']) for v in verdicts)} replica {sum(len(v['replica']) for v in verdicts)} "
              f"both {sum(len(v['both']) for v in verdicts)} A {sum(len(v['a_failures']) for v in verdicts)} B with a split {sum(len(v['b_split']) for v in verdicts)} "
              f"B without {sum(len(v['b_failures']) for v in verdicts)} lost by both in another category {sum(len(v['lost_other']) for v in verdicts)} borderline {sum(len(v['borderline']) for v in verdicts)} (at most {BORDERLINE_MOST}) "
              f"ambiguity {sum(v['ambiguity'] for v in verdicts)}", flush=True)

    def test_every_clean_stratum_was_kept_whole(self):
        self.assertEqual([item["stratum"] for item in self.readings if item["missing"]], [])
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertEqual(item["events"], finding_tests.EVENTS_PER_BIN)
                self.assertEqual([name for name, holds in item["bound"].items() if not holds], [])

    def test_the_replica_takes_the_runs_own_constants(self):
        """The cut and holes come from each record; they must be track_finding.hpp's, and the hit sigma the data file's, which the fixture states."""
        header = TRACK_FINDING_HEADER.read_text(encoding="utf-8")
        sigma = replica.header_constant(FIXTURE_CONSTANTS.read_text(encoding="utf-8"), "hit_sigma_mm")
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                settings = item["settings"]
                self.assertEqual((settings.chi2_cut, settings.most_holes), (finding_tests.header_constant(header, "finding_chi2_cut"), finding_tests.header_constant(header, "finding_most_holes")))
                self.assertEqual(settings.hit_sigmas_mm, (sigma, sigma))

    def test_the_frame_is_the_truth_helix(self):
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertLess(item["frame_mm"], FRAME_LIMIT_MM)

    def test_the_loc0_block_agrees_with_acts_on_a_recorded_particle(self):
        """Review m3: job 7512409's ACTS hole chi2 of clean stratum 0, event 1556, particle 5, against the replica's, within REGRESSION_AGREEMENT."""
        regression = [item["regression"] for item in self.found if item["stratum"] == REGRESSION_STRATUM]
        self.assertEqual(len(regression), 1)
        self.assertIsNotNone(regression[0])
        holes = regression[0].holes
        print(f"TS-REPLICA-REGRESSION clean stratum {REGRESSION_STRATUM} event {REGRESSION_KEY[0]} particle {REGRESSION_KEY[1]} ACTS (job 7512409) "
              f"{' '.join(f'p{plane}:{value}' for plane, value in REGRESSION_HOLES)} replica {' '.join(f'p{plane}:{value:.3f}' for plane, value in holes)}", flush=True)
        self.assertEqual([plane for plane, _ in holes], [plane for plane, _ in REGRESSION_HOLES])
        for (_, mine), (_, theirs) in zip(holes, REGRESSION_HOLES):
            self.assertAlmostEqual(mine, theirs, delta=REGRESSION_AGREEMENT)

    def test_a_every_acts_loss_is_a_replica_loss(self):
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertEqual(item["verdict"]["a_failures"], [])

    def test_b_every_extra_replica_loss_has_a_split(self):
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertEqual(item["verdict"]["b_failures"], [])

    def test_c_borderline_cases_at_most_two(self):
        self.assertTrue(borderline_within([len(item["verdict"]["borderline"]) for item in self.found]))

    def test_d_ambiguity_losses_within_the_close_pairs(self):
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertTrue(ambiguity_within(item["stratum"], item["verdict"]["ambiguity"]))

    def test_no_clean_loss_of_another_category(self):
        for item in self.found:
            with self.subTest(stratum=item["stratum"]):
                self.assertEqual(item["verdict"]["other"], {})


if __name__ == "__main__":
    unittest.main()
