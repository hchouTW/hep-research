"""T07 scoring of the evaluation harness (D4 stage E6b; d4-e6b-brief.md; freeze-b-proposal.md section 4, row E6). Scoring side.

Sections cited are of t04-values-v4.md (Freeze A). This module turns the products of the T07 recipes and the truth files of one complete bin into
the typed records of E6a's statistics core (tests/adapters/t04_evaluation_core.py), for every gate of section 8.2 and 8.5, and the pooled angle
slices; it judges nothing of its own: every pass, fail and inconclusive word is the core's (sections 5.2, 10). It reads truth, so no recipe imports
it (section 3.1; NoRecipeImportsTheScoring). It lives beside the core for the same reasons (the core's docstring).

What it holds:
- section 7's definitions, coded once: track match (more than a fraction of the track's measurements, noise hits included; 50 %, and 70 % for the
  recorded sensitivity rerun, line 533), the primary rule, reconstructable track (6 hits on distinct planes) and vertex (3 reconstructable tracks),
  fake, duplicate (reconstructed convention), charge sign, vertex match (more than 50 % of the summed weights, weights of unmatched tracks in the
  denominator), vertex primary with U-K1 (decisions.md: "most tracks" counts tracks with weight >= 0.5), wrong assignment, far and near events, the
  angle slices; U-K3 (an event is search-truncated if any delivered track is marked truncated);
- the track state at plane 1 (section 7, "Track state, surface"; R16): the smoothed state at plane 1, or the first smoothed state propagated to plane
  1 with its covariance along the fixture's helix (the development refit's closed form, test_acts_refit_field.helix_to_plane), by a Jacobian of
  central differences;
- every gate of section 8.2, per bin, in a fixed order (bin_gates), and the 60 pooled angle-slice tests per fixture (slice_gates): the count is
  section 5.3's 1,260 in its composition, checked at import (required_composition);
- F1 (section 8.3) as the core's rate test at C(o) = 0.005; F2 with r_dev and L_dev read from the Freeze-B run's rate record, which is refused if its
  SHA-256 is not FREEZE_B_RATE_RECORD_SHA256 or its block is not 2 (freeze_b_rate_record);
- N1 of the E6a re-review: the T07 refit ranges are outside the layout's completeness check, so collect_refit checks them as the layout checks a bin
  (attempt selection, ranges complete, each product's SHA-256 and events), and score_bin refuses a short refit set: its 21 tests read "required
  output missing" (section 10), never a smaller sample (section 3.4, "Top-up: never");
- O5 of the E6a review: a pooled angle slice has an identity of its own, the core's core.PooledIdentity (E6 merge stage: pool = the slice,
  members strata 0-11; its stratum code core.POOL_STRATUM_BASE + slice, so its bootstrap rows are its own, never a bin's), and is scored only
  when all 12 bins of its fixture and block are complete (score_slices, layout.pool_status); a primary with no plane-1 result counts as a
  failure in its slice's tail (E6b re-review N1; v4 5.1, 7);
- the reported, not gated, items of section 8.4 as readings, with no result word;
- E5 at evaluation (section 11): the kept negative-case file, its SHA-256 checked first, and v4 11's expected outcomes as negative checks;
- block 1 as a development reading only (DevelopmentBin: labelled "development reading, block 1", the attempt-1 rule, never a workflow verdict).
The interface E6c's T07 tasks call is the command line (main): score-bin, score-slices, negative-cases, summary, count; each ends with its own
result line (RESULT_LINE). Constants are v4's and are not tuned (R12): none derives from pulls or targets.

Run from anywhere: python -B -s -E t07_evaluation_scoring.py score-bin --block B --fixture-id F --stratum S --events N --record R --product P
    --truth T [--truth-seeded-record TS] [--refit-collection J] [--rate-record RR] --out DIR
"""
from __future__ import annotations

import argparse
import builtins
import collections
import dataclasses
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
import acts_finding_record as finding_record  # noqa: E402
import acts_native_product as native_product  # noqa: E402
import t07_fake_rate as fake_rate  # noqa: E402
import t07_negative_cases as negative_cases  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402

WORKFLOW = "T07"
FIXTURES = {7001: "clean", 7002: "noise"}                  # section 3.2; the CAI fixtures 7003, 7004 are outside these gates (section 4.1)
EVALUATION_BLOCKS = (11, 12)                                # section 3.2
DEVELOPMENT_BLOCK = 1                                       # section 3.2: tuning; read here as a development reading only
DEVELOPMENT_LABEL = "development reading, block 1"
DEVELOPMENT_RULE_BLOCK = 11                                 # a development reading is computed by the attempt-1 rule (95 %), never a verdict
PARAMETERS = ("loc0", "loc1", "phi", "theta", "q/p")       # section 7, "Track state, surface"
CHARGES = (("positive", 1), ("negative", -1))               # section 8.2, "q/p per charge"; section 7: by the truth charge of the matched particle
AXES = ("x", "y", "z")                                      # section 7, "Vertex pull": global ACTS frame
PULL_STATISTICS = ("trimmed-centre", "sigma68-width", "tail")   # section 6: location, width, tail
MATCH_FRACTION = Fraction(1, 2)                             # section 7, "Track match": more than 50 %
SENSITIVITY_FRACTION = Fraction(7, 10)                      # section 7.1, "Matching sensitivity": repeated at 70 %
SENSITIVITY_RATE_CHANGE = 0.005                             # ibid.: a change of more than 0.005 in any gated rate
SENSITIVITY_PULL_CHANGE = 0.02                              # ibid.: more than 0.02 in any centre or width
SENSITIVITY_SENTENCE = "not sensitive to the matching threshold"
LEAST_HITS = 6                                              # section 7, "Reconstructable track"
RECONSTRUCTABLE_VERTEX_TRACKS = 3                           # section 7, "Reconstructable vertex"
WEIGHT_THRESHOLD = 0.5                                      # section 7, "Wrong assignment"; U-K1 for the vertex primary
NEAR_MODULUS = 5                                            # section 4.1: event_index mod 5 = 0 is near
TAIL_PULL, TAIL_LIMIT = 3.0, 0.01                           # section 6, "Tail": P(|pull| > 3), L = 1 %
RATE_LIMIT = 0.01                                           # section 8.2: fakes clean, duplicates, charge sign, vertex assignment, L = 1 %
CLEAN_EFFICIENCY_LIMIT = 1.0 - core.DELTA_FLOOR             # section 8.2, "Efficiency, clean": R - delta = 0.99 (R = 1, delta(1) = 0.01)
R_FLOOR_OF_LEVEL = (0.99937, 0.99812, 0.99374)              # section 4.1, "Analytic references": R_floor(o) = (1 - p_w)^8
FLOOR_MARGIN = 0.01                                         # section 8.2, "Efficiency, noise (b)": R_floor(o) - 0.01
PAIRED_LIMIT = -0.01                                        # section 8.2, "Efficiency, noise (a)"
VERTEX_FINDING_FLOOR = 0.95                                 # section 8.5; section 16, accepted by the user
FAKE_CAP_OF_LEVEL = fake_rate.LIMIT_OF_LEVEL                # section 8.3: C(o) = 0.005 at Freeze A, all three levels
STABILITY_TOLERANCE = 0.0025                                # section 8.3, tau
# F2's bound (section 8.3): "the 95 % bounds of section 5.2" at attempt 1; at attempt 2 the whole bound at 99 %, U_eval and L_dev both, L_dev
# recomputed from the Freeze-B record's k, n, N_ev and DEFF_hat (the user, decisions.md "The user's answers on the attempt-2 levels (K09,
# 2026-11-12)").
STABILITY_CONFIDENCE_OF_ATTEMPT = {1: 0.95, 2: 0.99}
# The r_dev record of attempt 1: the Freeze-B run on block 2 (job 7585954, noise/noise-b2.rate.record, listed in its outputs.sha256 3091ea36).
# Before attempt 2 r_dev renews (v4 3.4, "On that return"): from the block-5 Freeze-B run's record, whose hash and block replace these two.
FREEZE_B_RATE_RECORD_SHA256 = "ebf2aa0e54de13c2626c20c4d0d1a997ddf6ea2694d1cbe7354b5e8e3a2deb73"
FREEZE_B_BLOCK = 2                                          # decisions.md, "The Freeze-B run on block 2: results"
FREEZE_B_CONFIGURATION_SHA256 = "2448d935fd8a20d8856be6772d7dfbaa774819f74a0a90d139cdc680531a3050"   # ibid.: T07 configuration_sha256 (v4 11: fixed at Freeze B)
FREEZE_B_EVENTS_PER_BIN = 12000                             # section 3.2, T07 noise
SLICE_EDGES = (-0.15, -0.075, 0.0, 0.075, 0.15)             # section 7, "Angle slices": truth u-slope at the vertex, the last slice closed
SLICE_STRATUM_BASE = core.POOL_STRATUM_BASE                # O5: a slice's stratum code (the core's pooled code); never a stratum of section 3.2 (0-11)
SLICE_MEMBERS = tuple(range(12))                            # a slice pools strata 0-11 of its fixture (section 8.2, "Angle")
REFIT_RECIPE = "reco.track.acts-kf-refit/1"                # section 8.1
# E5 (decisions.md, "D4 builds E1 and E2"; collect-7585958.out, "RECORD beside Freeze B (U-B8)"): the kept negative-case folder by its hashes.
NEGATIVE_CASE_SHA256 = "06a7741a4fe0eb89bd412a53bc8c5c1fca668a8ed6cbc18ea129922d23dd6a9d"
NEGATIVE_DESCRIPTION_SHA256 = "ff501223b08221b675e3402bba5e1ea54699c904900a721bf6df5b4bf4ad10c5"
NEGATIVE_SUMS_SHA256 = "978853d24c34b15290619d2a8acbad3c2b138b4b142a99a3486f69a9a59207b2"
LOST_PAIRS_LIMIT = 3                                        # test_acts_finding.LOST_TO_THE_CHI2_CUT: Poisson 0.34, above 3 at 5e-4
LOST_ALONE_LIMIT = 12                                       # test_acts_finding.LOST_ALONE_LIMIT: of 168
# The fixture's helix (section 4.1): planes 50 mm apart along ACTS x, field 1 T along ACTS z.
PLANE_PITCH_MM = 50.0
GEV_PER_TESLA_MM = 0.299792458e-3
FIELD_TESLA = 1.0
FINITE_STEPS = numpy.array([1e-3, 1e-3, 1e-6, 1e-6, 1e-5])   # as test_acts_refit_field.FINITE_STEPS
# The result line E6c requires (layout.classify_script_run); "crashed" never matches. "incomplete" (exit 3): the summary, when a required check
# is absent or a check is given twice (E6 merge stage; E6c re-review: an absent check is incomplete, never a fail).
RESULT_LINE = r"^RESULT t07-scoring [a-z-]+ (ok|failed|rejected|incomplete):"
EXIT_OK, EXIT_NEGATIVE, EXIT_BAD_INPUT, EXIT_INCOMPLETE = 0, 1, 2, 3   # core/status.py


class ScoringError(ValueError):
    """An input this scoring refuses (another bin's files, a record of another hash or block, a product that is not whole); the reason names it."""


# ---- Identities: an evaluation bin is the core's; block 1 is a development reading; a pooled slice has its own (O5).

@dataclass(frozen=True)
class DevelopmentBin(core.BinIdentity):
    """A block-1 bin, read as a development reading: computed by the attempt-1 rule, labelled so on every record, and never judged."""

    def __post_init__(self):
        super().__post_init__()
        if self.block != DEVELOPMENT_BLOCK or self.fixture_id not in FIXTURES:
            raise ScoringError(f"a development reading is of block {DEVELOPMENT_BLOCK}, fixture 7001 or 7002: block {self.block}, fixture {self.fixture_id}")

    @property
    def label(self) -> str:
        return f"{DEVELOPMENT_LABEL}: {WORKFLOW} fixture {self.fixture_id} block {self.block} stratum {self.stratum}"

    @property
    def level(self) -> core.Level:
        return core.level_of_block(DEVELOPMENT_RULE_BLOCK)


def slice_of(slope_u: float):
    """Section 7, "Angle slices": [-0.15, -0.075), [-0.075, 0), [0, 0.075), [0.075, 0.15]; None outside (no fixture slope is)."""
    if not SLICE_EDGES[0] <= slope_u <= SLICE_EDGES[-1]:
        return None
    for index in range(len(SLICE_EDGES) - 1):
        if slope_u < SLICE_EDGES[index + 1]:
            return index
    return len(SLICE_EDGES) - 2


def slice_name(slice_index: int) -> str:
    """The pool name of an angle slice: its index and its truth u-slope interval (the last slice closed)."""
    low, high = SLICE_EDGES[slice_index], SLICE_EDGES[slice_index + 1]
    closing = "]" if slice_index == len(SLICE_EDGES) - 2 else ")"
    return f"angle slice {slice_index} [{low}, {high}{closing} pooled over strata 0-11"


@dataclass(frozen=True)
class DevelopmentSlice(core.PooledIdentity):
    """A pooled angle slice of block 1: the core's pooled identity (its bootstrap entropy, members and name), read as a development reading by
    the attempt-1 rule, labelled so, never judged (as DevelopmentBin is of core.BinIdentity)."""

    def __post_init__(self):
        super().__post_init__()
        if self.block != DEVELOPMENT_BLOCK:
            raise ScoringError(f"a development slice is of block {DEVELOPMENT_BLOCK}: block {self.block}")

    @property
    def label(self) -> str:
        return f"{DEVELOPMENT_LABEL}: {super().label}"

    @property
    def level(self) -> core.Level:
        return core.level_of_block(DEVELOPMENT_RULE_BLOCK)


def bin_identity(fixture_id: int, block: int, stratum: int) -> core.BinIdentity:
    """The identity of a T07 bin: the core's on blocks 11 and 12, a DevelopmentBin on block 1; any other block (2-6) is refused."""
    if fixture_id not in FIXTURES:
        raise ScoringError(f"fixture {fixture_id} has no T07 gate (section 8.2: 7001 clean, 7002 noise)")
    if block in EVALUATION_BLOCKS:
        return core.BinIdentity(WORKFLOW, fixture_id, block, stratum)
    if block == DEVELOPMENT_BLOCK:
        return DevelopmentBin(WORKFLOW, fixture_id, block, stratum)
    raise ScoringError(f"block {block} is neither an evaluation block (11, 12) nor block 1 (a development reading): refused")


def slice_identity(fixture_id: int, block: int, slice_index: int) -> core.PooledIdentity:
    """O5 on the core's pooled identity (E6 merge stage, E6b's slice identity becomes core.PooledIdentity): pool = the slice, members strata
    0-11, so its entropy (520, fixture, block, 100 + slice) is never a bin's or another slice's; blocks 11 and 12 the core's, block 1 a
    DevelopmentSlice; any other fixture, block or slice is refused."""
    if fixture_id not in FIXTURES:
        raise ScoringError(f"a pooled angle slice is T07's, fixture 7001 or 7002: {fixture_id}")
    if not 0 <= slice_index < len(SLICE_EDGES) - 1:
        raise ScoringError(f"slice {slice_index}: slices 0 to {len(SLICE_EDGES) - 2}")
    if block in EVALUATION_BLOCKS:
        return core.PooledIdentity(WORKFLOW, fixture_id, block, slice_index, SLICE_MEMBERS, slice_name(slice_index))
    if block == DEVELOPMENT_BLOCK:
        return DevelopmentSlice(WORKFLOW, fixture_id, block, slice_index, SLICE_MEMBERS, slice_name(slice_index))
    raise ScoringError(f"block {block}: slices are scored on blocks 11 and 12, or read on block 1")


def is_development(identity) -> bool:
    return identity.block == DEVELOPMENT_BLOCK


# ---- The gates and the count (sections 5.3, 8.2).

def _pull_gates(prefix: str) -> list:
    gates = [(f"{prefix} pull {name}", statistic) for name in PARAMETERS for statistic in PULL_STATISTICS]
    return gates + [(f"{prefix} q/p pull {charge}", statistic) for charge, _ in CHARGES for statistic in PULL_STATISTICS]


TRACK_GATES = [(f"T07 track pull {name}", s) for name in PARAMETERS for s in PULL_STATISTICS]                       # 15 per bin
CHARGE_GATES = [(f"T07 q/p pull {charge}", s) for charge, _ in CHARGES for s in PULL_STATISTICS]                    # 6
VERTEX_GATES = [(f"T07 vertex pull {axis}", s) for axis in AXES for s in PULL_STATISTICS]                          # 9
REFIT_GATES = _pull_gates("T07 refit")                                                                             # 21, clean only
CLEAN_RATE_GATES = [("T07 efficiency clean", "efficiency"), ("T07 fakes clean", "rate"), ("T07 duplicates", "rate"), ("T07 charge sign", "rate"),
                    ("T07 vertex finding", "efficiency"), ("T07 vertex assignment", "rate")]                         # 6
NOISE_RATE_GATES = [("T07 efficiency noise (a) paired", "paired-difference"), ("T07 efficiency noise (b) floor", "efficiency"),
                    ("T07 fakes noise F1", "rate"), ("T07 fakes noise F2", "stability"), ("T07 duplicates", "rate"), ("T07 charge sign", "rate"),
                    ("T07 vertex finding", "efficiency"), ("T07 vertex assignment", "rate")]                         # 8
COMPOSITION_V4 = {"track pulls": 360, "q/p per charge": 144, "vertex pulls": 216, "clean rates": 72, "noise rates": 96, "refit": 252, "angle": 120,
                  "total": 1260}   # section 5.3


def bin_gates(fixture_id: int) -> list:
    """The (gate, statistic) of one bin, in the order gate_records writes them: 57 for a clean bin, 38 for a noise bin."""
    if fixture_id == 7001:
        return TRACK_GATES + CHARGE_GATES + VERTEX_GATES + CLEAN_RATE_GATES + REFIT_GATES
    if fixture_id == 7002:
        return TRACK_GATES + CHARGE_GATES + VERTEX_GATES + NOISE_RATE_GATES
    raise ScoringError(f"fixture {fixture_id} has no T07 gate (section 8.2: 7001 clean, 7002 noise)")


def slice_gates(parameters=PARAMETERS) -> list:
    """The 60 tests of one fixture's pooled slices (section 8.2, "Angle": 5 track parameters x 3 in 4 slices), slice by slice."""
    return [(f"T07 angle slice {index} pull {name}", s) for index in range(len(SLICE_EDGES) - 1) for name in parameters for s in PULL_STATISTICS]


def required_composition() -> dict:
    found = {"track pulls": 24 * len(TRACK_GATES), "q/p per charge": 24 * len(CHARGE_GATES), "vertex pulls": 24 * len(VERTEX_GATES),
             "clean rates": 12 * len(CLEAN_RATE_GATES), "noise rates": 12 * len(NOISE_RATE_GATES), "refit": 12 * len(REFIT_GATES),
             "angle": len(FIXTURES) * len(slice_gates())}
    found["total"] = sum(found.values())
    every = 12 * len(bin_gates(7001)) + 12 * len(bin_gates(7002)) + len(FIXTURES) * len(slice_gates())
    if found != COMPOSITION_V4 or every != found["total"] or found["total"] != core.REQUIRED_TESTS[WORKFLOW]:
        raise ScoringError(f"the T07 count is not section 5.3's 1,260 in its composition: {found}, {every}")
    return found


required_composition()   # checked at import: the gate lists cannot drift from section 5.3


# ---- Section 7's definitions, coded once.

def owners_of(tracks, particles, fraction=MATCH_FRACTION) -> list:
    """Per track (its hit keys), the particle supplying more than `fraction` of its measurements, noise hits included in the count, or None. A track
    matches one particle at most. A hit key held by two particles is refused: the fixture gives each hit one owner at most."""
    fraction = Fraction(str(fraction)) if not isinstance(fraction, Fraction) else fraction
    owner = {}
    for index, keys in enumerate(particles):
        for key in keys:
            if key in owner:
                raise ScoringError(f"hit key {key} belongs to particles {owner[key]} and {index}")
            owner[key] = index
    found = []
    for keys in tracks:
        count = collections.Counter(owner[key] for key in keys if key in owner)
        found.append(next((p for p, c in count.items() if c > fraction * len(keys)), None))
    return found


def track_event(tracks, particles, fraction=MATCH_FRACTION) -> dict:
    """Section 7 for one event. tracks: delivered tracks in index order, {"hit_keys", "chi2", "ndf"}; particles: hit keys each truth particle
    left. Primary: highest matched fraction, then most hits, then lowest chi2/ndf, then lowest index. Efficiency over reconstructable particles;
    fake: matching no particle; duplicate: matched tracks that are not primary."""
    owners = owners_of([track["hit_keys"] for track in tracks], particles, fraction)
    matched = {}
    for index, (track, particle_index) in enumerate(zip(tracks, owners)):
        if particle_index is None:
            continue
        own = sum(1 for key in track["hit_keys"] if key in set(particles[particle_index]))
        ratio = track["chi2"] / track["ndf"] if track["ndf"] > 0 else math.inf     # review M1: ndf <= 0 ranks last on chi2/ndf, never a crash
        matched.setdefault(particle_index, []).append((-Fraction(own, len(track["hit_keys"])), -len(track["hit_keys"]), ratio, index))
    reconstructable = [index for index, keys in enumerate(particles) if len(keys) >= LEAST_HITS]
    all_matched = sum(len(found) for found in matched.values())
    primaries = {particle_index: min(found)[3] for particle_index, found in matched.items()}
    return {"reconstructable": len(reconstructable), "with_primary": sum(index in primaries for index in reconstructable),
            "lost": [index for index in reconstructable if index not in primaries], "reconstructed": len(tracks), "fakes": sum(o is None for o in owners),
            "matched": all_matched, "duplicates": all_matched - len(primaries), "primaries": primaries, "owners": owners,
            "reconstructable_particles": reconstructable}


def search_truncated(found) -> bool:
    """U-K3: the event is search-truncated if any delivered (selected) track is marked truncated."""
    return any(item["outcome"] == "selected" and item["search_truncated"] for item in found)


def truth_position(vertex) -> tuple:
    """Section 4.1 [R14]: a truth vertex (u, v, z) in the global ACTS frame: x = z, y = u, z = v."""
    return (float(vertex["z_mm"]), float(vertex["u_mm"]), float(vertex["v_mm"]))


def is_near(event_index: int) -> bool:
    return int(event_index) % NEAR_MODULUS == 0


def vertex_event(vertices, owners, primary_tracks, vertex_of_particle, positions, *, reconstructable_particles) -> dict:
    """Section 7's vertex rows for one event. vertices: {"position_mm", "covariance" (xx xy xz yy yz zz), "tracks": [{"track_key", "weight"}]};
    owners: track key -> matched particle or None; primary_tracks: primary track key -> its particle; vertex_of_particle: each particle's truth
    vertex; positions: truth vertices in the global frame; reconstructable_particles: the truth vertex of each reconstructable particle.
    Match: more than 50 % of the summed track weights (unmatched tracks' weights in the denominator). Primary: highest share, then most tracks
    with weight >= 0.5 (U-K1), then smallest distance to truth, then lowest index. Wrong assignment: a primary track with weight >= 0.5 in a
    matched vertex that is not its truth vertex, over primary tracks with weight >= 0.5 in matched vertices."""
    reconstructable_count = collections.Counter(reconstructable_particles)
    reconstructable = [t for t in range(len(positions)) if reconstructable_count[t] >= RECONSTRUCTABLE_VERTEX_TRACKS]
    matched_truth, candidates = {}, {}
    for index, item in enumerate(vertices):
        total = sum(track["weight"] for track in item["tracks"])
        by_truth = collections.Counter()
        for track in item["tracks"]:
            particle_index = owners.get(track["track_key"])
            if particle_index is not None:
                by_truth[vertex_of_particle[particle_index]] += track["weight"]
        best = next((t for t, weight in by_truth.items() if total > 0.0 and 2.0 * weight > total), None)
        if best is None:
            continue
        matched_truth[index] = best
        heavy = sum(1 for track in item["tracks"] if track["weight"] >= WEIGHT_THRESHOLD)
        distance = math.dist(item["position_mm"], positions[best])
        candidates.setdefault(best, []).append((-by_truth[best] / total, -heavy, distance, index))
    primaries = {t: min(found)[3] for t, found in candidates.items()}
    pulls, residuals, without_result, without_reconstructable = [], [], 0, 0
    for t, index in sorted(primaries.items()):
        item = vertices[index]
        residual = [fitted - true for fitted, true in zip(item["position_mm"], positions[t])]
        variances = (item["covariance"][0], item["covariance"][3], item["covariance"][5])
        if not all(math.isfinite(v) and v > 0 for v in variances):
            without_result += 1      # no result (review M1): counted as a failure in the pull tails and in vertex finding, never a crash
            without_reconstructable += int(t in reconstructable)
            continue
        residuals.append(residual)
        pulls.append([value / math.sqrt(variance) for value, variance in zip(residual, variances)])
    assigned = wrong = 0
    for key, particle_index in primary_tracks.items():
        held_in = [matched_truth[index] for index, item in enumerate(vertices) if index in matched_truth
                   for track in item["tracks"] if track["track_key"] == key and track["weight"] >= WEIGHT_THRESHOLD]
        if held_in:
            assigned += 1
            wrong += int(any(t != vertex_of_particle[particle_index] for t in held_in))
    largest = {}
    for t in range(len(positions)):
        weight_in = collections.Counter()
        for index, item in enumerate(vertices):
            for track in item["tracks"]:
                particle_index = owners.get(track["track_key"])
                if particle_index is not None and vertex_of_particle[particle_index] == t:
                    weight_in[index] += track["weight"]
        if weight_in and max(weight_in.values()) > 0.0:
            largest[t] = min(index for index, weight in weight_in.items() if weight == max(weight_in.values()))
    holders = collections.Counter(largest.values())
    return {"reconstructable": len(reconstructable), "found": sum(t in primaries for t in reconstructable), "primaries": primaries, "pulls": pulls,
            "residuals": residuals, "without_result": without_result, "without_result_reconstructable": without_reconstructable, "assigned": assigned, "wrong": wrong, "vertices": len(vertices), "unmatched": len(vertices) - len(matched_truth),
            "split": sum(len(found) > 1 for found in candidates.values()), "merged": sum(holders[index] > 1 for index in largest.values())}


# ---- The state at plane 1 (section 7, "Track state, surface"; R16).

def helix_to_plane(position_mm, phi, theta, q_over_p, plane_x_mm):
    """A track in a field along z (test_acts_refit_field.helix_to_plane, the development refit's closed form): T_z constant, phi falling at
    (q/p) k B per unit transverse path. Returns loc0, loc1 and phi at the plane x = plane_x_mm."""
    distance_mm = plane_x_mm - position_mm[:, 0]
    transverse = numpy.sin(theta)
    end_phi = numpy.arcsin(numpy.sin(phi) - q_over_p * GEV_PER_TESLA_MM * FIELD_TESLA * distance_mm / transverse)
    middle_phi = 0.5 * (phi + end_phi)
    half_turn = 0.5 * (phi - end_phi)
    arc_over_chord = numpy.where(numpy.abs(half_turn) < 1e-8, 1.0 + half_turn ** 2 / 6.0, half_turn / numpy.where(half_turn == 0.0, 1.0, numpy.sin(half_turn)))
    loc0_mm = position_mm[:, 1] + distance_mm * numpy.tan(middle_phi)
    loc1_mm = position_mm[:, 2] + numpy.cos(theta) / transverse * distance_mm / numpy.cos(middle_phi) * arc_over_chord
    return loc0_mm, loc1_mm, end_phi


def _moved_to_plane_one(states, plane: int):
    states = numpy.atleast_2d(states)
    x_mm = PLANE_PITCH_MM * (plane - 1)
    position = numpy.stack([numpy.full(len(states), x_mm), states[:, 0], states[:, 1]], -1)
    loc0, loc1, phi = helix_to_plane(position, states[:, 2], states[:, 3], states[:, 4], 0.0)
    return numpy.stack([loc0, loc1, phi, states[:, 3], states[:, 4]], -1)


def plane_one_state(state, covariance, *, plane: int) -> tuple:
    """(state, covariance) at plane 1: a plane-1 state as it is; a later plane's smoothed state propagated along the helix, with J C J^T, J by
    central differences (steps FINITE_STEPS)."""
    state = numpy.asarray(state, float)
    covariance = numpy.asarray(covariance, float)
    if plane == 1:
        return state, covariance
    if not 1 < plane <= 8:
        raise ScoringError(f"plane {plane} is not a telescope plane")
    moved = _moved_to_plane_one(state, plane)[0]
    steps = numpy.diag(FINITE_STEPS)
    jacobian = ((_moved_to_plane_one(state + steps, plane) - _moved_to_plane_one(state - steps, plane)) / (2.0 * FINITE_STEPS[:, None])).T
    return moved, jacobian @ covariance @ jacobian.T


# ---- Products, read as a stream (an o3 finder product of 12,000 events is about 7 GB, a refit product 12 GB).

TRIANGLE = [(i, j) for i in range(6) for j in range(i, 6)]


def _covariance(values) -> numpy.ndarray:
    matrix = numpy.zeros((6, 6))
    for (i, j), value in zip(TRIANGLE, values):
        matrix[i, j] = matrix[j, i] = value
    return matrix[:5, :5]


def read_product(path, *, recipe: str, keys=None) -> dict:
    """acts-tracking-product/1 or /2 as a stream: the header (whose recipe must be `recipe`), each track's status and event ordinal, and for each
    track (or each of `keys`) its lowest-plane state: plane, kind, the hit (loc0, loc1 and covariance) and the predicted, filtered and smoothed
    parameters with their covariance. The end record's counts are checked against the lines read: a cut file is refused."""
    path = Path(path)
    wanted = None if keys is None else set(keys)
    status, ordinals, lowest, kept = {}, {}, {}, {}
    counts = collections.Counter()
    order = {"track": 0, "state": 1, "parameters": 2}
    stage = 0
    end = None
    with open(path, encoding="utf-8") as stream:
        first = stream.readline().rstrip("\n")
        if first not in (native_product.PRODUCT_FORMAT, native_product.PRODUCT_FORMAT_R33):
            raise ScoringError(f"{path.name}: not {native_product.PRODUCT_FORMAT} or /2")
        fields = native_product.TEXT_HEADER_FIELDS + (native_product.R33_HEADER_FIELDS if first == native_product.PRODUCT_FORMAT_R33 else ())
        try:
            header = native_product._header_from_lines([stream.readline().rstrip("\n") for _ in fields], fields)
        except native_product.ProductFormatError as error:
            raise ScoringError(f"{path.name}: {error}") from error
        if header["recipe"] != recipe:
            raise ScoringError(f"{path.name}: recipe {header['recipe']}, not {recipe}")
        for line in stream:
            if end is not None:
                raise ScoringError(f"{path.name}: text after the end record")
            if not line.endswith("\n"):
                raise ScoringError(f"{path.name}: the last line is not finished")
            kind = line[:line.find(" ")]
            if kind in order:
                if order[kind] < stage:
                    raise ScoringError(f"{path.name}: a {kind} line after the next section (not the writer's order)")
                stage = order[kind]
            counts[kind] += 1
            if kind == "track":
                tokens = line.split()
                status[tokens[1]], ordinals[tokens[1]] = tokens[3], int(tokens[2])
            elif kind == "state":
                tokens = line.split()
                key = tokens[1]
                if wanted is not None and key not in wanted:
                    continue
                plane = int(tokens[3])
                if key not in lowest or plane < lowest[key]["plane"]:
                    hit = None if tokens[4] == "hole" else (float(tokens[6]), float(tokens[7]), tuple(float(t) for t in tokens[8:11]))
                    lowest[key] = {"plane": plane, "index": int(tokens[2]), "kind": tokens[4], "hit": hit}
            elif kind == "parameters":
                head = line.split(" ", 4)
                key, index, state_type = head[1], int(head[2]), head[3]
                if key in lowest and lowest[key]["index"] == index:
                    tokens = line.split()
                    values = [float(t) for t in tokens[4:31]]
                    kept.setdefault(key, {})[state_type] = (numpy.array(values[:5]), _covariance(values[6:]))
            elif kind == "end":
                end = [int(t) for t in line.split()[1:]]
            elif kind not in ("alignment_payload", "track_output", "residual", "measurement_output", "residual_covariance"):
                raise ScoringError(f"{path.name}: unknown record {kind}")
    if end is None:
        raise ScoringError(f"{path.name}: the product ends before its end record")
    r33 = [counts[name] for name in ("track_output", "residual", "measurement_output", "residual_covariance")]
    expected = [counts["track"], counts["state"], counts["parameters"]] + (r33 if first == native_product.PRODUCT_FORMAT_R33 else [])
    if end != expected:
        raise ScoringError(f"{path.name}: the end record counts {end}, the product holds {expected}")
    states = {}
    for key, found in lowest.items():
        entry = dict(found)
        for state_type in ("predicted", "filtered", "smoothed"):
            if state_type in kept.get(key, {}):
                entry[state_type], entry[f"{state_type}_covariance"] = kept[key][state_type]
        states[key] = entry
    return {"header": header, "status": status, "ordinals": ordinals, "states": states,
            "counts": {"tracks": counts["track"], "states": counts["state"], "parameters": counts["parameters"]}}


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def plane_one_pull(entry, truth5):
    """The pull vector of one track at plane 1, or None when the track has no smoothed state with a positive finite covariance. Returns
    (pulls, fitted q/p, propagated)."""
    if entry is None or "smoothed" not in entry:
        return None
    state, covariance = plane_one_state(entry["smoothed"], entry["smoothed_covariance"], plane=entry["plane"])
    variances = numpy.diag(covariance)
    if not (numpy.isfinite(state).all() and numpy.isfinite(variances).all() and (variances > 0).all()):
        return None
    return (state - numpy.asarray(truth5)) / numpy.sqrt(variances), float(state[4]), entry["plane"] != 1


# ---- F2's development record (section 8.3), read by hash.

def freeze_b_rate_record(path, expected_sha256: str = FREEZE_B_RATE_RECORD_SHA256) -> dict:
    """The Freeze-B run's t07-noise-fake-rate/1 record: refused unless its SHA-256 is expected_sha256, its block 2, its fixture 7002 (the parser's
    rule), every one of the 12 noise bins present and 12,000 events per bin; every bound recomputed by E2's parser."""
    content = Path(path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != expected_sha256:
        raise ScoringError(f"the r_dev record's SHA-256 is {digest}, not the Freeze-B run's {expected_sha256}: refused")
    try:
        document = fake_rate.parse_rate_record(content.decode("utf-8"))
    except (fake_rate.RateRecordError, UnicodeDecodeError) as error:
        raise ScoringError(f"the r_dev record does not read: {error}") from error
    if document["header"]["block"] != FREEZE_B_BLOCK:
        raise ScoringError(f"the r_dev record is of block {document['header']['block']}, not the Freeze-B run's block {FREEZE_B_BLOCK}: refused")
    strata = sorted(item["stratum"] for item in document["bins"])
    if strata != list(range(12)) or document["header"]["events_per_bin"] != FREEZE_B_EVENTS_PER_BIN:
        raise ScoringError(f"the r_dev record holds strata {strata} at {document['header']['events_per_bin']} events: section 8.3 needs all 12 at 12,000")
    return {"sha256": digest, "header": document["header"], "bins": {item["stratum"]: item for item in document["bins"]}}


def development_lower_bound(item: dict, attempt: int) -> float:
    """L_dev of one bin of the Freeze-B record at the attempt's F2 level: the record's own 95 % bound at attempt 1; at attempt 2 the same
    expressions at 99 % (core.bounds_at) on the record's k, n, N_ev and DEFF_hat (the user's answer on the attempt-2 levels)."""
    confidence = STABILITY_CONFIDENCE_OF_ATTEMPT[attempt]
    if confidence == fake_rate.CONFIDENCE:
        return item["l_dev"]
    return core.bounds_at(item["fakes"], item["tracks"], item["events"], item["deff_hat"], confidence)["lower"]


def stability_test(name, identity, m, y, *, r_dev: float, l_dev: float, required: bool = True) -> core.TestResult:
    """Section 8.3, F2: (r_eval - r_dev) + sqrt((U_eval - r_eval)^2 + (r_dev - L_dev)^2) <= tau; U_eval section 5.2's bound on the evaluation
    sample at STABILITY_CONFIDENCE_OF_ATTEMPT (E2's rate_rule at 95 %, the core's bounds_at otherwise). Defined at zero counts; k = n gives
    U_eval = 1. No objects, or fewer than 2 events: required output missing."""
    level = identity.level
    m = numpy.asarray(m)
    y = numpy.asarray(y)
    if m.ndim != 1 or m.shape != y.shape or (m < 0).any() or (y < 0).any() or (y > m).any():
        raise ScoringError("F2 takes per-event counts, 0 <= y_e <= m_e")
    n, k, events = int(m.sum()), int(y.sum()), int(m.size)
    common = dict(gate=name, bin=identity.label, statistic="stability", limit=STABILITY_TOLERANCE, attempt=level.attempt, confidence=level.confidence,
                  replicates=None, required=required, standard_error=None, lower=None)
    if n == 0 or events < 2:
        return core.TestResult(estimate=None, upper=None, result="inconclusive", step=0, reason=f"required output missing: {n} objects in {events} events",
                               readings={"events": events, "objects": n}, **common)
    r_eval = k / n
    confidence = STABILITY_CONFIDENCE_OF_ATTEMPT[level.attempt]
    if k == n:
        u_eval = 1.0
    else:
        found = fake_rate.rate_rule(m.astype(numpy.int64), y.astype(numpy.int64))
        u_eval = found["u_dev"] if confidence == fake_rate.CONFIDENCE else core.bounds_at(k, n, events, found["deff_hat"], confidence)["u"]
    statistic = (r_eval - r_dev) + math.sqrt((u_eval - r_eval) ** 2 + (r_dev - l_dev) ** 2)
    word, step = ("pass", 3) if statistic <= STABILITY_TOLERANCE else ("fail", 4)
    return core.TestResult(estimate=statistic, upper=u_eval, result=word, step=step, reason="",
                           readings={"events": events, "objects": n, "failures": k, "r_eval": r_eval, "u_eval": u_eval, "u_eval_confidence": confidence,
                                     "r_dev": r_dev, "l_dev": l_dev}, **common)


# ---- N1: the refit set (the E6a re-review: refit ranges are outside the layout's completeness check).

@dataclass
class RefitInput:
    collection: layout.BinCollection
    products: dict          # first event of the piece -> the refit product's path


def refit_pieces(plan, fixture_id: int, stratum: int) -> list:
    """The refit ranges the evaluation plan holds for one clean bin (layout.evaluation_plan's "T07 refit" tasks), in event order."""
    return sorted(task.span for task in plan.tasks if task.kind == "T07 refit" and task.bin == (7, fixture_id, stratum))


def refit_product_events(path) -> list:
    """The event ordinals a refit product holds (its track lines), the product read whole by read_product's checks (recipe and end record)."""
    found = read_product(path, recipe=REFIT_RECIPE, keys=())
    return sorted(set(found["ordinals"].values()))


def collect_refit(expected, pieces, attempts, products, *, total: int = layout.EVENTS_PER_BIN, inputs=None, data_sha256: str | None = None) -> layout.BinCollection:
    """The refit pieces of one clean bin, checked as layout.collect_bin checks a bin's ranges: the counted attempt of each piece (select_attempt:
    on blocks 11 and 12 only attempts that drew and fitted nothing may precede it), every record of the expected bin and of one stratum file,
    the pieces complete over 0 .. total - 1 (layout.check_ranges: no gap, overlap, duplicate or missing piece), and each product read: its
    SHA-256 its record's and its events exactly its range. Any refusal makes the refit "missing", with the reason (top-up never)."""
    try:
        pieces = list(pieces)
        if not pieces:
            raise layout.LayoutError("missing range: no refit range is planned for this clean bin")
        chosen = []
        for span in pieces:
            tried = list(attempts.get(span, ()))
            if not tried:
                raise layout.LayoutError(f"missing range: refit {span.first}-{span.end - 1} has no attempt")
            index = layout.select_attempt([verdict for verdict, _ in tried], block=expected.block)
            record = tried[index][1]
            if record is None or (record.first, record.count) != (span.first, span.count):
                raise layout.LayoutError(f"missing range: the counted attempt of refit {span.first}-{span.end - 1} left no record of its range")
            chosen.append(record)
        key = (expected.workflow, expected.fixture_id, expected.block, expected.stratum)
        if {(r.workflow, r.fixture_id, r.block, r.stratum) for r in chosen} != {key}:
            raise layout.LayoutError(f"refit records of another bin than {key}")
        if len({r.stratum_sha256 for r in chosen}) != 1:
            raise layout.LayoutError("the refit pieces read more than one data file")
        if data_sha256 is not None and {r.stratum_sha256 for r in chosen} != {data_sha256}:
            raise layout.LayoutError("the refit pieces read another data file than the bin's finding record names (review M3)")
        layout.check_ranges([layout.EventRange(r.first, r.count) for r in chosen], total)
        for r in chosen:
            if tuple(r.events) != tuple(range(r.first, r.first + r.count)):
                raise layout.LayoutError(f"refit {r.first}-{r.first + r.count - 1} lists events other than its own")
            path = products.get(r.first)
            if path is None or not Path(path).is_file():
                raise layout.LayoutError(f"missing range: the refit product of {r.first}-{r.first + r.count - 1} is absent")
            if sha256_file(path) != r.product_sha256:
                raise layout.LayoutError(f"the refit product of {r.first}-{r.first + r.count - 1} is not the one its record names (SHA-256)")
            if inputs is not None:   # review M3: the hit-set file is its record's
                hit_sets = inputs.get(r.first)
                if hit_sets is None or not Path(hit_sets).is_file() or sha256_file(hit_sets) != r.input_sha256:
                    raise layout.LayoutError(f"the hit-set file of refit {r.first}-{r.first + r.count - 1} is absent or not its record's (SHA-256)")
            held = refit_product_events(path)
            if held != list(range(r.first, r.first + r.count)):
                raise layout.LayoutError(f"the refit product of {r.first}-{r.first + r.count - 1} holds events {held[:3]}... ({len(held)}), "
                                         f"not its {r.count}: refused, never a short refit set")
    except (layout.LayoutError, ScoringError) as error:
        return layout.BinCollection("missing", str(error), ())
    return layout.BinCollection("complete", "", tuple(chosen))


def write_refit_collection(path, collection: layout.BinCollection, products: dict) -> None:
    Path(path).write_text(json.dumps({"status": collection.status, "reason": collection.reason, "records": [json.loads(r.to_json()) for r in collection.records],
                                      "products": {str(first): str(p) for first, p in products.items()}}, sort_keys=True) + "\n", encoding="utf-8")


def read_refit_collection(path) -> RefitInput:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    records = tuple(layout.RangeRecord.from_json(json.dumps(r)) for r in document["records"])
    return RefitInput(layout.BinCollection(document["status"], document["reason"], records), {int(k): Path(v) for k, v in document["products"].items()})


# ---- One bin: its tally and its records.

@dataclass
class BinTally:
    """Per-event numbers of one bin, as the gates read them. Each (m, y) pair is per event: objects and failures."""
    events: int
    pulls: list = field(default_factory=list)              # per event, (k, 5): the finder primaries' plane-1 pulls
    pull_charges: list = field(default_factory=list)       # per event, (k,): their particles' truth charges
    without_result: list = field(default_factory=list)     # per event, (j,): truth charges of primaries with no plane-1 result (I2)
    vertex_without_result: list = field(default_factory=list)   # per far event: primary vertices with no finite positive variance
    vertex_pulls: list = field(default_factory=list)       # per far event, (k, 3)
    efficiency: tuple = ()                                 # (reconstructable, lost)
    fakes: tuple = ()                                      # (reconstructed, fakes)
    duplicates: tuple = ()                                 # (matched, matched but not primary)
    charge_sign: tuple = ()                                # (primaries, wrong sign)
    vertex_finding: tuple = ()                             # far events: (reconstructable vertices, not found)
    vertex_assignment: tuple = ()                          # far events: (primary tracks at weight >= 0.5 in matched vertices, wrong)
    paired: tuple | None = None                            # noise: (reconstructable, finder primaries, truth-seeded primaries)
    stability: dict | None = None                          # noise: {"r_dev", "l_dev", "record_sha256"}
    refit_pulls: list | None = None                        # clean: per event, (k, 5)
    refit_charges: list | None = None
    refit_without_result: int = 0                          # refit fits with no plane-1 result (failed fits included): a reading (ruling, I2)
    refit_hit_sets: int = 0
    missing: dict = field(default_factory=dict)            # group ("product", "paired", "stability", "refit") -> reason


def _counts(pair) -> tuple:
    return numpy.asarray(pair[0], dtype=numpy.int64), numpy.asarray(pair[1], dtype=numpy.int64)


def _pull_records(name: str, identity, per_event, reason: str | None, without_result=None) -> list:
    """Section 6 on one population: location and width (the core's pull test), and the tail as the core's rate test, L = 1 %. Objects with no
    result (without_result, per event) count as failures in the tail's rate (v4 5.1: "Objects with no result count in a failure rate"; I2)."""
    if reason:
        return [core.missing_output(name, identity, statistic, reason) for statistic in PULL_STATISTICS]
    per_event = [numpy.asarray(values, float) for values in per_event]
    empty = _empty_replicate(identity, per_event)
    if empty is not None:
        common = dict(gate=name, bin=identity.label, estimate=None, standard_error=None, lower=None, upper=None, limit=core.TOLERANCE, result="inconclusive",
                      step=0, attempt=identity.level.attempt, confidence=identity.level.confidence, replicates=core.BOOTSTRAP_REPLICATES,
                      required=True, reason=f"bootstrap replicate {empty} of the bin's own rows holds no object: se undefined", readings=core.pull_readings(per_event))
        centre, width = core.TestResult(statistic="trimmed-centre", **common), core.TestResult(statistic="sigma68-width", **common)
    else:
        centre, width = core.pull_tests(name, identity, per_event)
    extra = numpy.zeros(len(per_event), dtype=numpy.int64) if without_result is None else numpy.asarray(without_result, dtype=numpy.int64)
    m = numpy.array([values.size for values in per_event], dtype=numpy.int64) + extra
    y = numpy.array([int((numpy.abs(values) > TAIL_PULL).sum()) for values in per_event], dtype=numpy.int64) + extra
    return [centre, width, core.rate_test(name, identity, m, y, TAIL_LIMIT, statistic="tail")]


def _empty_replicate(identity, per_event):
    """The index of the first of the bin's own bootstrap rows (core.bootstrap_indices, the rows the core's pull test draws) that holds no object,
    or None. With so few objects the pull test's se is undefined (the core's sigma_68 has no value on an empty replicate): such a test reads
    inconclusive, with that reason, never a crash. At evaluation sizes no row is empty; this guards small development bins."""
    counts = numpy.array([values.size for values in per_event], dtype=numpy.int64)
    if counts.size == 0 or counts.sum() == 0 or (counts > 0).all():
        return None
    rows = core.bootstrap_indices(identity, counts.size)
    for start in range(0, rows.shape[0], 100):
        held = counts[rows[start:start + 100]].sum(axis=1)
        if (held == 0).any():
            return start + int(numpy.argmax(held == 0))
    return None


def _missing_counts(without, sign=None):
    if not without:
        return None
    return [int(numpy.size(w)) if sign is None else int((numpy.asarray(w) == sign).sum()) for w in without]


def _population_records(prefix: str, identity, pulls, charges, reason, without=None) -> list:
    records = []
    for index, name in enumerate(PARAMETERS):
        records += _pull_records(f"{prefix} pull {name}", identity, None if reason else [p[:, index] for p in pulls], reason, _missing_counts(without))
    return records


def _charge_records(prefix: str, identity, pulls, charges, reason, without=None) -> list:
    records = []
    for charge_name, sign in CHARGES:
        population = None if reason else [p[numpy.asarray(c) == sign, 4] for p, c in zip(pulls, charges)]
        records += _pull_records(f"{prefix} q/p pull {charge_name}", identity, population, reason, _missing_counts(without, sign))
    return records


def _reason(tally: BinTally, group: str) -> str | None:
    return f"{group}: {tally.missing[group]}" if group in tally.missing else None


def gate_records(identity, tally: BinTally) -> list:
    """Every gate of section 8.2 and 8.5 on one bin, as the core's records, in bin_gates order. A group whose input is missing gives section 10's
    "required output missing" for each of its tests."""
    fixture_id = identity.fixture_id
    product = _reason(tally, "product")
    records = _population_records("T07 track", identity, tally.pulls, tally.pull_charges, product, tally.without_result)
    records += _charge_records("T07", identity, tally.pulls, tally.pull_charges, product, tally.without_result)
    for index, axis in enumerate(AXES):
        records += _pull_records(f"T07 vertex pull {axis}", identity, [v[:, index] for v in tally.vertex_pulls], None, tally.vertex_without_result or None)
    rates = {
        "T07 duplicates": lambda: core.rate_test("T07 duplicates", identity, *_counts(tally.duplicates), RATE_LIMIT),
        "T07 charge sign": lambda: (core.missing_output("T07 charge sign", identity, "rate", product) if product
                                    else core.rate_test("T07 charge sign", identity, *_counts(tally.charge_sign), RATE_LIMIT)),
        "T07 vertex finding": lambda: core.efficiency_test("T07 vertex finding", identity, *_counts(tally.vertex_finding), VERTEX_FINDING_FLOOR),
        "T07 vertex assignment": lambda: core.rate_test("T07 vertex assignment", identity, *_counts(tally.vertex_assignment), RATE_LIMIT),
    }
    if fixture_id == 7001:
        rates["T07 efficiency clean"] = lambda: core.efficiency_test("T07 efficiency clean", identity, *_counts(tally.efficiency), CLEAN_EFFICIENCY_LIMIT)
        rates["T07 fakes clean"] = lambda: core.rate_test("T07 fakes clean", identity, *_counts(tally.fakes), RATE_LIMIT)
        records += [rates[name]() for name, _ in CLEAN_RATE_GATES]
        refit = _reason(tally, "refit")
        if not refit and tally.refit_pulls is None:
            refit = "refit: no refit product was scored"
        refit_records = _population_records("T07 refit", identity, tally.refit_pulls, tally.refit_charges, refit)
        refit_records += _charge_records("T07 refit", identity, tally.refit_pulls, tally.refit_charges, refit)
        if not refit:   # the coordinator's ruling (I2): refit fits with no result are counted beside the refit pulls, never dropped silently
            note = {"refit fits without a plane-1 result (a reading, no rate gated)": f"{tally.refit_without_result} of {tally.refit_hit_sets} hit sets"}
            refit_records = [dataclasses.replace(r, readings=dict(r.readings, **note)) for r in refit_records]
        records += refit_records
    else:
        level = identity.stratum % 3
        paired = _reason(tally, "paired") or (None if tally.paired is not None else "paired: no truth-seeded run was scored")
        stability = _reason(tally, "stability") or (None if tally.stability is not None else "stability: no r_dev record was read")
        rates["T07 efficiency noise (a) paired"] = lambda: (core.missing_output("T07 efficiency noise (a) paired", identity, "paired-difference", paired) if paired
                                                            else core.paired_test("T07 efficiency noise (a) paired", identity,
                                                                                  *[numpy.asarray(v, dtype=numpy.int64) for v in tally.paired], PAIRED_LIMIT))
        rates["T07 efficiency noise (b) floor"] = lambda: core.efficiency_test("T07 efficiency noise (b) floor", identity, *_counts(tally.efficiency),
                                                                               round(R_FLOOR_OF_LEVEL[level] - FLOOR_MARGIN, 10))
        rates["T07 fakes noise F1"] = lambda: core.rate_test("T07 fakes noise F1", identity, *_counts(tally.fakes), FAKE_CAP_OF_LEVEL[level])
        rates["T07 fakes noise F2"] = lambda: (core.missing_output("T07 fakes noise F2", identity, "stability", stability) if stability
                                               else stability_test("T07 fakes noise F2", identity, *_counts(tally.fakes), r_dev=tally.stability["r_dev"],
                                                                   l_dev=tally.stability["l_dev"]))
        records += [rates[name]() for name, _ in NOISE_RATE_GATES]
    if [(r.gate, r.statistic) for r in records] != bin_gates(fixture_id):
        raise ScoringError("the bin's records are not bin_gates' list: the count would not be section 5.3's")
    return records


def tally_estimates(tally: BinTally, fixture_id: int) -> dict:
    """Point estimates of every matching-dependent gated quantity (no bootstrap): rates and efficiencies, and every pull centre and width minus 1.
    Refit pulls follow truth hit sets, not the matching, and are left out. Used by the sensitivity rerun (section 7.1, line 533)."""
    found = {}

    def pulls(name, per_event, without=None):
        """without: the objects with no result (per event); they count as failures in the tail, as in the gated tail (_pull_records; the E6 merge
        review's nit: the slices' estimates count them since N1)."""
        values = numpy.concatenate([numpy.asarray(v, float) for v in per_event]) if per_event else numpy.zeros(0)
        missed = int(numpy.sum(without)) if without else 0
        if values.size:
            found[(name, "trimmed-centre")] = core.trimmed_centre(values)
            found[(name, "sigma68-width")] = core.sigma_68(values) - 1.0
        if values.size + missed:
            found[(name, "tail")] = (int((numpy.abs(values) > TAIL_PULL).sum()) + missed) / (values.size + missed)

    if "product" not in tally.missing:
        for index, name in enumerate(PARAMETERS):
            pulls(f"T07 track pull {name}", [p[:, index] for p in tally.pulls], _missing_counts(tally.without_result))
        for charge_name, sign in CHARGES:
            pulls(f"T07 q/p pull {charge_name}", [p[numpy.asarray(c) == sign, 4] for p, c in zip(tally.pulls, tally.pull_charges)],
                  _missing_counts(tally.without_result, sign))
        m, y = _counts(tally.charge_sign)
        if m.sum():
            found[("T07 charge sign", "rate")] = y.sum() / m.sum()
    for index, axis in enumerate(AXES):
        pulls(f"T07 vertex pull {axis}", [v[:, index] for v in tally.vertex_pulls], tally.vertex_without_result or None)
    for gate, pair, kind in (("T07 duplicates", tally.duplicates, "rate"), ("T07 vertex assignment", tally.vertex_assignment, "rate"),
                             ("T07 vertex finding", tally.vertex_finding, "efficiency")):
        m, y = _counts(pair)
        if m.sum():
            found[(gate, kind)] = (1 - y.sum() / m.sum()) if kind == "efficiency" else y.sum() / m.sum()
    m, y = _counts(tally.efficiency)
    fakes_m, fakes_y = _counts(tally.fakes)
    if fixture_id == 7001:
        if m.sum():
            found[("T07 efficiency clean", "efficiency")] = 1 - y.sum() / m.sum()
        if fakes_m.sum():
            found[("T07 fakes clean", "rate")] = fakes_y.sum() / fakes_m.sum()
    else:
        if m.sum():
            found[("T07 efficiency noise (b) floor", "efficiency")] = 1 - y.sum() / m.sum()
        if fakes_m.sum():
            found[("T07 fakes noise F1", "rate")] = fakes_y.sum() / fakes_m.sum()
        if tally.paired is not None and numpy.sum(tally.paired[0]):
            found[("T07 efficiency noise (a) paired", "paired-difference")] = (numpy.sum(tally.paired[1]) - numpy.sum(tally.paired[2])) / numpy.sum(tally.paired[0])
    return {key: float(value) for key, value in found.items()}


def sensitivity_changes(primary: dict, rerun: dict) -> list:
    """Section 7.1, "Matching sensitivity": for each quantity of both runs, the change and whether it is beyond its threshold (0.005 on a gated rate
    or efficiency, 0.02 on a centre or width). A quantity of one run only is listed as beyond (the rerun could not compute it)."""
    changes = []
    for key in sorted(set(primary) | set(rerun)):
        threshold = SENSITIVITY_PULL_CHANGE if key[1] in ("trimmed-centre", "sigma68-width") else SENSITIVITY_RATE_CHANGE
        if key not in primary or key not in rerun:
            changes.append({"quantity": list(key), "at_50": primary.get(key), "at_70": rerun.get(key), "change": None, "threshold": threshold, "beyond": True})
            continue
        change = abs(rerun[key] - primary[key])
        changes.append({"quantity": list(key), "at_50": primary[key], "at_70": rerun[key], "change": change, "threshold": threshold, "beyond": change > threshold})
    return changes


def matching_sentence(changes) -> tuple:
    """(disagrees, sentence): the sentence "not sensitive to the matching threshold" holds only if no change is beyond its threshold. It blocks
    nothing (section 10, "Matching sensitivity disagrees": no effect, recorded)."""
    disagrees = any(change["beyond"] for change in changes)
    return disagrees, (None if disagrees else SENSITIVITY_SENTENCE)


@dataclass
class BinInputs:
    record: Path
    product: Path
    truth: Path
    truth_seeded_record: Path | None = None
    refit: RefitInput | None = None
    rate_record: Path | None = None
    rate_record_sha256: str = FREEZE_B_RATE_RECORD_SHA256


def _truth_particles(truth_event) -> list:
    return [[int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY] for track in truth_event["tracks"]]


def _delivered(event) -> list:
    return [item for item in event["found"] if item["outcome"] == "selected"]


def _as_tracks(selected) -> list:
    return [{"hit_keys": item["hit_keys"], "chi2": item["fit_chi2"], "ndf": item["fit_coordinates"] - 5} for item in selected]


def _truth_five(track) -> numpy.ndarray:
    return numpy.array(list(track["crossings"][0]) + [float(track["q_over_p"])], float)


def _loss_class(particle_keys, event, truncated: bool) -> str:
    """Failure classes (section 8.4; t04-prereg.md): a lost reconstructable particle's class, as test_acts_finding.loss_category, with U-K3."""
    owned = set(particle_keys)
    for item in event["found"]:
        if item["outcome"] != "selected" and 2 * len(owned & set(item["hit_keys"])) > len(item["hit_keys"]):
            return item["failure_category"]
    if truncated or event["seeds_truncated"] or event["seed_budget_reached"] or event["ambiguity_budget_reached"]:
        return "search-truncated"
    return "seed-or-finding"


def _centre_width(values) -> str:
    values = numpy.asarray(values, float)
    if values.size == 0:
        return "count 0"
    return f"count {values.size} centre {core.trimmed_centre(values):+.4f} width {core.sigma_68(values):.4f} mean {values.mean():+.4f} rms {math.sqrt((values * values).mean()):.4f}"


def _unbiased_pull(entry, truth_hit_free=None):
    """Section 8.4, unbiased residuals, at plane 1: r* = V R_s^-1 r_s from the smoothed state that holds the plane-1 hit (acts_native_product)."""
    if entry is None or entry["plane"] != 1 or entry["kind"] != "measurement" or entry["hit"] is None or "smoothed" not in entry:
        return None
    loc0, loc1, measurement = entry["hit"]
    smoothed, covariance = entry["smoothed"], entry["smoothed_covariance"]
    residual, residual_covariance = native_product.residual_of((loc0, loc1), measurement, smoothed[:2], (covariance[0, 0], covariance[0, 1], covariance[1, 1]), True)
    if residual_covariance[0] * residual_covariance[2] - residual_covariance[1] ** 2 <= 0 or residual_covariance[0] <= 0:
        return None
    value, unbiased_covariance = native_product.unbiased_from_smoothed(residual, residual_covariance, measurement)
    if unbiased_covariance[0] <= 0 or unbiased_covariance[2] <= 0:
        return None
    return (value[0] / math.sqrt(unbiased_covariance[0]), value[1] / math.sqrt(unbiased_covariance[2]))


def score_bin(identity, inputs: BinInputs, *, events: int) -> dict:
    """One bin from its files: the finding record (/2, with the vertex step), the finder's product (every event in it), the truth file, and for a
    noise bin the truth-seeded record and the Freeze-B r_dev record, for a clean bin the refit collection (N1). Returns {"records" (bin_gates
    order), "tally", "estimates" (50 %), "rerun" (70 %), "sensitivity", "readings", "slices"}. Refused (ScoringError) if a file is of another bin,
    another data file, or another event count than `events`; a missing part reads "required output missing" on its tests only."""
    if identity.fixture_id not in FIXTURES or identity.workflow != WORKFLOW:
        raise ScoringError(f"not a T07 bin: {identity}")
    fixture_id = identity.fixture_id
    truth_header = truth_files.read_truth_header(inputs.truth)
    if (truth_header["fixture_id"], truth_header["block"], truth_header["stratum"], truth_header["event_count"]) != (fixture_id, identity.block, identity.stratum, events):
        raise ScoringError(f"the truth file is of fixture, block, stratum, events {(truth_header['fixture_id'], truth_header['block'], truth_header['stratum'], truth_header['event_count'])}, "
                           f"not {(fixture_id, identity.block, identity.stratum, events)}")
    try:
        record = finding_record.parse_record(Path(inputs.record).read_text(encoding="utf-8"))
    except (finding_record.RecordFormatError, OSError, UnicodeDecodeError) as error:
        raise ScoringError(f"the finding record is refused: {error}") from error
    header = record["header"]
    if header.get("vertex_recipe") != finding_record.VERTEX_RECIPE:
        raise ScoringError("the finding record holds no vertex step (acts-tracking-finding-record/2): the vertex gates need it")
    if header["data_sha256"] != truth_header["data_sha256"] or len(record["events"]) != events:
        raise ScoringError(f"the record is of data {header['data_sha256']} with {len(record['events'])} events; the truth names {truth_header['data_sha256']}, {events}")
    tally = BinTally(events=events)
    rerun_tally = BinTally(events=events)
    readings = collections.OrderedDict()
    product = None
    if header["product_events"] < events:
        tally.missing["product"] = f"the record's product holds {header['product_events']} of {events} events"
    elif not Path(inputs.product).is_file():
        tally.missing["product"] = "the product is absent"
    else:
        try:
            product = read_product(inputs.product, recipe=finding_record.FINDING_RECIPE)
        except (ScoringError, OSError, UnicodeDecodeError) as error:
            tally.missing["product"] = f"the product is refused: {error}"
        if product is not None:
            selected_keys = {item["key"] for event in record["events"] for item in _delivered(event)}
            if (product["header"]["data_sha256"], product["header"]["product_id"]) != (header["data_sha256"], header["product_id"]) \
                    or product["header"]["stage"] != finding_record.FINDING_STAGE:
                tally.missing["product"] = "the product is not the record's (data_sha256, product_id or stage)"
            elif set(product["status"]) != selected_keys:
                tally.missing["product"] = f"the product holds {len(product['status'])} tracks, the record delivers {len(selected_keys)}"
    rerun_tally.missing = dict(tally.missing)
    states = product["states"] if product is not None and "product" not in tally.missing else {}

    seeded = None
    if fixture_id == 7002:
        seeded, why = _truth_seeded(inputs.truth_seeded_record, header, events)
        if why:
            tally.missing["paired"] = rerun_tally.missing["paired"] = why
        try:
            if inputs.rate_record is None:
                raise ScoringError("no r_dev record given")
            rate = freeze_b_rate_record(inputs.rate_record, inputs.rate_record_sha256)
            if rate["header"]["configuration_sha256"] != header["configuration_sha256"]:
                raise ScoringError("the r_dev record is of another recipe configuration than this record's")
            item = rate["bins"][identity.stratum]
            tally.stability = {"r_dev": item["r_dev"], "l_dev": development_lower_bound(item, identity.level.attempt), "record_sha256": rate["sha256"]}
        except ScoringError as error:
            tally.missing["stability"] = str(error)

    totals = collections.Counter()
    near_pulls, sign_pulls = [], {("loc0", "+"): [], ("loc0", "-"): [], ("loc1", "+"): [], ("loc1", "-"): []}
    predicted, filtered, unbiased, classes = [], [], [], collections.Counter()
    slice_rows = {"0.5": [], "0.7": []}
    slice_without = {"0.5": [], "0.7": []}   # N1 (E6b re-review): (ordinal, truth u-slope) of each primary with no plane-1 result
    per_fraction = {}
    for ordinal, (event, truth_event) in enumerate(zip(record["events"], truth_files.iter_truth_events(inputs.truth))):
        particles = _truth_particles(truth_event)
        tracks_meta = truth_event["tracks"]
        vertex_of_particle = [int(t["vertex_index"]) for t in tracks_meta]
        positions = [truth_position(v) for v in truth_event["vertices"]]
        near = is_near(truth_event["event_index"])
        if bool(int(truth_event["near_separation"])) != near:
            raise ScoringError(f"event {ordinal}: the truth file's near flag disagrees with event_index mod 5 (section 4.1)")
        selected = _delivered(event)
        tracks = _as_tracks(selected)
        truncated = search_truncated(event["found"])
        totals["search-truncated events (U-K3)"] += int(truncated)
        totals["search-truncated delivered tracks"] += sum(1 for item in selected if item["search_truncated"])
        totals["search-truncated candidates (every outcome)"] += sum(1 for item in event["found"] if item["search_truncated"])
        for fraction, target, label in ((MATCH_FRACTION, tally, "0.5"), (SENSITIVITY_FRACTION, rerun_tally, "0.7")):
            scores = track_event(tracks, particles, fraction)
            owners = {item["key"]: owner for item, owner in zip(selected, scores["owners"])}
            primary_tracks = {selected[t]["key"]: p for p, t in scores["primaries"].items()}
            vertices = vertex_event(event["vertexing"]["vertices"], owners, primary_tracks, vertex_of_particle, positions,
                                    reconstructable_particles=[vertex_of_particle[p] for p in scores["reconstructable_particles"]])
            columns = per_fraction.setdefault(label, collections.defaultdict(list))
            for name, value in (("reconstructable", scores["reconstructable"]), ("lost", len(scores["lost"])), ("reconstructed", scores["reconstructed"]),
                                ("fakes", scores["fakes"]), ("matched", scores["matched"]), ("duplicates", scores["duplicates"])):
                columns[name].append(value)
            if not near:
                columns["vertex_reconstructable"].append(vertices["reconstructable"])
                columns["vertex_lost"].append(vertices["reconstructable"] - vertices["found"] + vertices["without_result_reconstructable"])
                target.vertex_without_result.append(vertices["without_result"])
                columns["assigned"].append(vertices["assigned"])
                columns["wrong"].append(vertices["wrong"])
                target.vertex_pulls.append(numpy.asarray(vertices["pulls"], float).reshape(-1, 3))
            if label == "0.5":
                totals["vertex split"] += vertices["split"]
                totals["vertex merged"] += vertices["merged"]
                totals["vertex unmatched"] += vertices["unmatched"]
                totals["vertices"] += vertices["vertices"]
                if near:
                    totals["near vertex reconstructable"] += vertices["reconstructable"]
                    totals["near vertex found"] += vertices["found"]
                    near_pulls += vertices["pulls"]
                for p in scores["lost"]:
                    classes[_loss_class(particles[p], event, truncated)] += 1
            event_pulls, event_charges, wrong_sign, without, without_reconstructable = [], [], 0, [], 0
            reconstructable_set = set(scores["reconstructable_particles"])
            for p in sorted(scores["primaries"]):
                key = selected[scores["primaries"][p]]["key"]
                found = plane_one_pull(states.get(key), _truth_five(tracks_meta[p])) if states else None
                if found is None:
                    if states:   # I2: a primary with no result is a failure in every gated rate (v4 5.1) and stays in the charge-sign denominator (v4 7)
                        totals[f"primaries without a plane-1 result ({label})"] += 1
                        without.append(int(tracks_meta[p]["charge"]))
                        without_reconstructable += int(p in reconstructable_set)
                        slice_without[label].append((ordinal, float(tracks_meta[p]["slope_u"])))
                    continue
                pull, fitted_q_over_p, propagated = found
                event_pulls.append(pull)
                charge = int(tracks_meta[p]["charge"])
                event_charges.append(charge)
                wrong_sign += int((fitted_q_over_p > 0) != (charge > 0))
                slice_rows[label].append((ordinal, float(tracks_meta[p]["slope_u"]), pull))
                if label == "0.5":
                    totals["primaries propagated to plane 1"] += int(propagated)
                    entry = states[key]
                    truth5 = _truth_five(tracks_meta[p])
                    for state_type, sink in (("predicted", predicted), ("filtered", filtered)):
                        if entry["plane"] == 1 and state_type in entry:
                            variances = numpy.diag(entry[f"{state_type}_covariance"])
                            if (variances > 0).all():
                                sink.append((entry[state_type] - truth5) / numpy.sqrt(variances))
                    found_unbiased = _unbiased_pull(entry)
                    if found_unbiased is not None:
                        unbiased.append(found_unbiased)
                    for index, name in ((0, "loc0"), (1, "loc1")):
                        sign_pulls[(name, "+" if truth5[index] >= 0 else "-")].append(pull[index])
            target.pulls.append(numpy.asarray(event_pulls, float).reshape(-1, 5))
            target.pull_charges.append(numpy.asarray(event_charges, dtype=numpy.int64))
            target.without_result.append(numpy.asarray(without, dtype=numpy.int64))
            columns["primaries"].append(len(event_pulls) + len(without))
            columns["wrong_sign"].append(wrong_sign + len(without))
            columns["lost"][-1] += without_reconstructable
            if seeded is not None:
                seeded_scores = track_event(_as_tracks(_delivered(seeded["events"][ordinal])), particles, fraction)
                columns["paired_a"].append(scores["with_primary"] - without_reconstructable)
                columns["paired_b"].append(seeded_scores["with_primary"])
    for label, target in (("0.5", tally), ("0.7", rerun_tally)):
        columns = collections.defaultdict(lambda: numpy.zeros(0, dtype=numpy.int64),
                                          {name: numpy.asarray(values, dtype=numpy.int64) for name, values in per_fraction[label].items()})
        target.efficiency = (columns["reconstructable"], columns["lost"])
        target.fakes = (columns["reconstructed"], columns["fakes"])
        target.duplicates = (columns["matched"], columns["duplicates"])
        target.charge_sign = (columns["primaries"], columns["wrong_sign"])
        target.vertex_finding = (columns["vertex_reconstructable"], columns["vertex_lost"])
        target.vertex_assignment = (columns["assigned"], columns["wrong"])
        if seeded is not None:
            target.paired = (columns["reconstructable"], columns["paired_a"], columns["paired_b"])
    if fixture_id == 7001:
        _score_refit(identity, inputs.refit, inputs.truth, header, tally, totals)
    records = gate_records(identity, tally)
    estimates = tally_estimates(tally, fixture_id)
    rerun = tally_estimates(rerun_tally, fixture_id)
    readings.update({name: int(value) for name, value in sorted(totals.items())})
    readings["failure classes of lost reconstructable particles"] = dict(sorted(classes.items()))
    readings["near vertex pulls (x, y, z)"] = [_centre_width(numpy.asarray(near_pulls, float).reshape(-1, 3)[:, a]) for a in range(3)]
    readings["plane-1 predicted state pulls"] = {name: _centre_width(numpy.asarray(predicted, float).reshape(-1, 5)[:, a]) for a, name in enumerate(PARAMETERS)}
    readings["plane-1 filtered state pulls"] = {name: _centre_width(numpy.asarray(filtered, float).reshape(-1, 5)[:, a]) for a, name in enumerate(PARAMETERS)}
    readings["plane-1 unbiased residual pulls"] = {name: _centre_width(numpy.asarray(unbiased, float).reshape(-1, 2)[:, a]) for a, name in enumerate(("loc0", "loc1"))}
    readings["pulls by sign of local position (truth)"] = {f"{name} {sign}": _centre_width(values) for (name, sign), values in sign_pulls.items()}
    slices = {label: {"ordinal": numpy.array([r[0] for r in rows], dtype=numpy.int64), "slope_u": numpy.array([r[1] for r in rows], float),
                      "pulls": numpy.asarray([r[2] for r in rows], float).reshape(-1, 5),
                      "without_ordinal": numpy.array([r[0] for r in slice_without[label]], dtype=numpy.int64),
                      "without_slope_u": numpy.array([r[1] for r in slice_without[label]], float)} for label, rows in slice_rows.items()}
    return {"records": records, "tally": tally, "estimates": estimates, "rerun": rerun, "sensitivity": sensitivity_changes(estimates, rerun),
            "readings": readings, "slices": slices, "product_complete": "product" not in tally.missing}


def _truth_seeded(path, header, events) -> tuple:
    """Section 7's truth-seeded run of the same recipe on the bin's own events: (record, None), or (None, why it is missing)."""
    if path is None or not Path(path).is_file():
        return None, "no truth-seeded record"
    from tests.adapters import test_acts_truth_seeded as seeded_tests
    try:
        seeded = seeded_tests.parse_truth_seeded_record(Path(path).read_text(encoding="utf-8"))
    except (seeded_tests.TruthSeededFormatError, finding_record.RecordFormatError, ValueError, OSError) as error:
        return None, f"the truth-seeded record is refused: {error}"
    if seeded["header"]["data_sha256"] != header["data_sha256"] or len(seeded["events"]) != events:
        return None, "the truth-seeded record is of other events (data_sha256 or count)"
    if seeded["header"]["recipe_configuration_sha256"] != header["configuration_sha256"]:
        return None, "the truth-seeded run is not of this recipe configuration (section 7: the same recipe)"
    return seeded, None


def _score_refit(identity, refit: RefitInput | None, truth_path, header, tally: BinTally, totals) -> None:
    """The refit pulls of a clean bin (section 8.2, "Refit pulls"), from a complete refit collection only (N1): each piece's product re-read, its
    SHA-256 its record's, every truth particle of every event fitted or failed. A short set is "required output missing"."""
    if refit is None:
        tally.missing["refit"] = "no refit collection given"
        return
    if refit.collection.status != "complete":
        tally.missing["refit"] = f"the refit set is incomplete at the collection: {refit.collection.reason}"
        return
    expected, truth_of_key = [], {}
    for ordinal, truth_event in enumerate(truth_files.iter_truth_events(truth_path)):
        for track in truth_event["tracks"]:
            key = f"event-{ordinal}-track-{int(track['particle_key'])}"
            expected.append((ordinal, key))
            truth_of_key[key] = track
    found_states, found_status = {}, {}
    for record in refit.collection.records:
        path = refit.products.get(record.first)
        if path is None or sha256_file(path) != record.product_sha256:
            tally.missing["refit"] = f"the refit product of {record.first}-{record.first + record.count - 1} is absent or not its record's (SHA-256)"
            return
        try:
            found = read_product(path, recipe=REFIT_RECIPE)
        except ScoringError as error:
            tally.missing["refit"] = f"a refit product is refused: {error}"
            return
        if found["header"]["data_sha256"] != header["data_sha256"]:
            tally.missing["refit"] = "a refit product is of another data file"
            return
        found_states.update(found["states"])
        found_status.update(found["status"])
    absent = [key for _, key in expected if key not in found_status]
    if absent or len(found_status) != len(expected):
        tally.missing["refit"] = f"the refit set is short: {len(expected) - len(absent)} of {len(expected)} hit sets fitted or failed (top-up never)"
        return
    pulls, charges = collections.defaultdict(list), collections.defaultdict(list)
    tally.refit_hit_sets = len(expected)
    for ordinal, key in expected:
        found = plane_one_pull(found_states.get(key), _truth_five(truth_of_key[key])) if found_status[key] == "fitted" else None
        if found is None:
            totals["refit tracks without a plane-1 result (failed fits included)"] += 1
            tally.refit_without_result += 1
            continue
        pulls[ordinal].append(found[0])
        charges[ordinal].append(int(truth_of_key[key]["charge"]))
    tally.refit_pulls = [numpy.asarray(pulls[o], float).reshape(-1, 5) for o in range(tally.events)]
    tally.refit_charges = [numpy.asarray(charges[o], dtype=numpy.int64) for o in range(tally.events)]


# ---- O5: the pooled angle slices.

def score_slices(fixture_id: int, block: int, bins, *, events_per_bin: int = layout.EVENTS_PER_BIN, parameters=PARAMETERS) -> dict:
    """The 60 tests of one fixture's slices (or those of `parameters`), pooled over its 12 bins of `block`. bins: per bin {"fixture_id", "block",
    "stratum", "events", "status", "reason", "populations": {"0.5"|"0.7": {"ordinal", "slope_u", "pulls", "without_ordinal", "without_slope_u"}}}.
    The pool is scored only when every one of strata 0-11 is there once, of this fixture and block, complete (layout.pool_status), with
    events_per_bin events and the count of its primaries with no plane-1 result; else every test reads "required output missing". The event is
    the unit (section 5.1): event e of bin s is pooled event offset(s) + e, bootstrapped by the slice's own identity. A primary with no plane-1
    result counts as a failure in its slice's tail, of every parameter, and in the 70 % estimate (N1; v4 5.1, 7)."""
    gates = slice_gates(parameters)
    identities = {index: slice_identity(fixture_id, block, index) for index in range(len(SLICE_EDGES) - 1)}
    bins = list(bins)
    problem = None
    strata = sorted(item["stratum"] for item in bins)
    if strata != list(range(12)):
        problem = f"the pool holds strata {strata}, not 0-11 once each"
    else:
        for item in bins:
            if (item["fixture_id"], item["block"]) != (fixture_id, block):
                problem = f"bin {item['stratum']} is of fixture {item['fixture_id']}, block {item['block']}"
            elif item["status"] == "complete" and item["events"] != events_per_bin:
                problem = f"bin {item['stratum']} holds {item['events']} events, not {events_per_bin}"
            elif item["status"] == "complete" and any(not {"without_ordinal", "without_slope_u"} <= set(population)
                                                      for population in item["populations"].values()):
                problem = f"bin {item['stratum']}'s slice file holds no count of primaries with no plane-1 result (N1)"
            if problem:
                break
        if not problem:   # E6 merge stage: the core's layout.pool_status, as T09's pool: complete only if every member bin is
            status, reason = layout.pool_status(identities[0], {item["stratum"]: (item["status"], item["reason"]) for item in bins})
            if status != "complete":
                problem = reason
    if problem:
        reason = f"the pooled slice is incomplete (O5): {problem}"
        records = [core.missing_output(gate, identities[int(gate.split()[3])], statistic, reason) for gate, statistic in gates]
        return {"records": records, "estimates": {}, "rerun": {}, "sensitivity": []}
    ordered = sorted(bins, key=lambda item: item["stratum"])
    total = sum(item["events"] for item in ordered)
    offsets = numpy.cumsum([0] + [item["events"] for item in ordered])[:-1]
    found, without = {}, {}
    for label in ("0.5", "0.7"):
        pooled_event = numpy.concatenate([offsets[i] + numpy.asarray(item["populations"][label]["ordinal"], dtype=numpy.int64) for i, item in enumerate(ordered)])
        slopes = numpy.concatenate([numpy.asarray(item["populations"][label]["slope_u"], float) for item in ordered])
        pulls = numpy.concatenate([numpy.asarray(item["populations"][label]["pulls"], float).reshape(-1, 5) for item in ordered])
        found[label] = (pooled_event, numpy.array([-1 if slice_of(s) is None else slice_of(s) for s in slopes]), pulls)
        without_event = numpy.concatenate([offsets[i] + numpy.asarray(item["populations"][label]["without_ordinal"], dtype=numpy.int64)
                                           for i, item in enumerate(ordered)])
        without_slope = numpy.concatenate([numpy.asarray(item["populations"][label]["without_slope_u"], float) for item in ordered])
        without[label] = (without_event, numpy.array([-1 if slice_of(s) is None else slice_of(s) for s in without_slope], dtype=numpy.int64))
    records, estimates, rerun = [], {}, {}
    for index in range(len(SLICE_EDGES) - 1):
        for name in parameters:
            column = PARAMETERS.index(name)
            gate = f"T07 angle slice {index} pull {name}"
            per_event = _pool(found["0.5"], index, column, total)
            records += _pull_records(gate, identities[index], per_event, None, _pool_without(without["0.5"], index, total))
            for target, label in ((estimates, "0.5"), (rerun, "0.7")):
                values = numpy.concatenate(_pool(found[label], index, column, total))
                missed = int(_pool_without(without[label], index, total).sum())
                if values.size:
                    target[(gate, "trimmed-centre")] = core.trimmed_centre(values)
                    target[(gate, "sigma68-width")] = core.sigma_68(values) - 1.0
                if values.size + missed:
                    target[(gate, "tail")] = float(((numpy.abs(values) > TAIL_PULL).sum() + missed) / (values.size + missed))
    if [(r.gate, r.statistic) for r in records] != gates:
        raise ScoringError("the slices' records are not slice_gates' list")
    return {"records": records, "estimates": estimates, "rerun": rerun, "sensitivity": sensitivity_changes(estimates, rerun)}


def _pool_without(population, index: int, total: int):
    """Per pooled event, the primaries of slice `index` with no plane-1 result (N1): failures in the slice's tail rate."""
    pooled_event, slices = population
    return numpy.bincount(pooled_event[slices == index], minlength=total).astype(numpy.int64)


def _pool(population, index: int, column: int, total: int) -> list:
    pooled_event, slices, pulls = population
    chosen = slices == index
    events_of, values = pooled_event[chosen], pulls[chosen, column]
    order = numpy.argsort(events_of, kind="stable")
    counts = numpy.bincount(events_of, minlength=total)
    return numpy.split(values[order], numpy.cumsum(counts)[:-1])


# ---- E5 at evaluation (section 11).

def check_negative_case_folder(folder) -> dict:
    """The kept negative-case folder: SHA256SUMS, the case file and the description by the hashes recorded beside Freeze B, checked before
    anything is read; then t07_negative_cases.read, which rebuilds the case file from its recorded source event. Returns the description."""
    folder = Path(folder)
    for name, expected in (("SHA256SUMS", NEGATIVE_SUMS_SHA256), (negative_cases.CASE_FILE, NEGATIVE_CASE_SHA256), (negative_cases.DESCRIPTION_FILE, NEGATIVE_DESCRIPTION_SHA256)):
        path = folder / name
        if not path.is_file() or sha256_file(path) != expected:
            raise ScoringError(f"{name} of the kept negative-case folder is absent or not the file kept at Freeze B (SHA-256 {expected[:16]}...)")
    try:
        return negative_cases.read(folder)["description"]
    except negative_cases.NegativeCaseError as error:
        raise ScoringError(f"the kept negative-case folder does not read: {error}") from error


def negative_case_checks(description: dict, record: dict, seeds) -> list:
    """v4 11's negative checks on the finder's record (and seed side file) of the kept case file, as tests/adapters/test_acts_finding.NegativeCases
    expects them: wrong hits (honest found, one wrong plane kept off every track, three wrong planes leave no track with its class); branch
    explosion (truncation marked on every candidate, inside the branch budget, ambiguity budget reached); seed failure (no seed, no track, its class);
    the seed budget reached and marked; every seed's outcome balancing the counters; any two lost planes and a track alone losing two still found
    (LOST_PAIRS_LIMIT, LOST_ALONE_LIMIT); limits reached marked search-truncated (U-K3 on delivered tracks). Each a CheckResult of kind negative."""
    cases = negative_cases.cases_of(description)
    names, rows_of = cases["names"], cases["events"]
    events = record["events"]
    if len(events) != len(names) or len(seeds) != len(names):
        return [core.CheckResult("negative cases: the record holds every case", "negative", "fail")]
    by = dict(zip(names, events))
    seeds_by = dict(zip(names, seeds))
    most_branches = int(float(record["configuration"]["finding_most_branches_per_seed"]))
    most_seeds = int(float(record["configuration"]["finding_most_seeds_per_event"]))
    tracks = cases["tracks"]

    def selected(name):
        return [item for item in by[name]["found"] if item["outcome"] == "selected"]

    def found_tracks(name, kept_hits):
        rows = rows_of[names.index(name)]
        own = set(negative_cases.sorted_hits(kept_hits))
        keys = {key for key, row in enumerate(rows) if row in own}
        return any(2 * len(keys & set(item["hit_keys"])) > len(item["hit_keys"]) for item in selected(name))

    results = []

    def check(name, condition):
        results.append(core.CheckResult(name, "negative", "pass" if condition else "fail"))

    honest = by["honest"]
    check("wrong hits: honest", len(selected("honest")) == len(tracks) and honest["failure_category"] == "none")
    one = selected("one-wrong-plane")
    rows = rows_of[names.index("one-wrong-plane")]
    check("wrong hits: one-wrong-plane", len(one) == len(tracks) and all(5 not in {rows[k][0] for k in item["hit_keys"]} and item["holes"] >= 1 for item in one))
    three = by["three-wrong-planes"]
    check("wrong hits: three-wrong-planes", three["selected"] == 0 and three["seeds_without_candidate"] > 0 and three["failure_category"] == "seed-or-finding")
    explosion = by["branch-explosion"]
    explosion_seeds = seeds_by["branch-explosion"]
    check("branch explosion: branch-explosion", explosion["seeds_truncated"] > 0 and explosion["selected"] > 0 and explosion["ambiguity_budget_reached"] == 1
          and bool(explosion["found"]) and all(item["search_truncated"] for item in explosion["found"])
          and sum(seed["candidates"] for seed in explosion_seeds) == explosion["candidates"]
          and max((seed["candidates"] for seed in explosion_seeds), default=0) <= most_branches + 1)
    budget = by["seed-budget"]
    check("seed budget: seed-budget", budget["seed_budget_reached"] == 1 and budget["seeds_found"] == most_seeds)
    for name in ("no-triple", "two-planes"):
        event = by[name]
        check(f"seed failure: {name}", (event["seeds_found"], event["selected"], event["failure_category"]) == (0, 0, "seed-or-finding"))
    balanced = True
    for name in names:
        event, outcomes = by[name], collections.Counter(seed["outcome"] for seed in seeds_by[name])
        balanced &= (len(seeds_by[name]) == event["seeds_found"] and outcomes["skipped"] == event["seeds_skipped"]
                     and outcomes["no-start"] + outcomes["filter-error"] == event["seeds_failed"] and outcomes["no-candidate"] == event["seeds_without_candidate"]
                     and sum(seed["candidates"] for seed in seeds_by[name]) == event["candidates"])
    check("seed outcomes balance the counters in every case", balanced)
    lost = 0
    for name in names:
        if name.startswith("lost-"):
            first, second = (int(part) for part in name.split("-")[1:])
            for keys in tracks:
                if not found_tracks(name, [cases["hits"][k] for k in keys if cases["hits"][k][0] not in (first, second)]):
                    lost += 1
    check(f"any two lost planes: at most {LOST_PAIRS_LIMIT} tracks lost", lost <= LOST_PAIRS_LIMIT)
    alone = sum(1 for name, kept in cases["alone"].items() if not found_tracks(name, kept))
    check(f"a track alone losing two planes: at most {LOST_ALONE_LIMIT} lost", alone <= LOST_ALONE_LIMIT)
    marked = True
    for name in names:
        event = by[name]
        if event["seed_budget_reached"] or event["ambiguity_budget_reached"]:
            marked &= all(item["search_truncated"] for item in event["found"]) and (event["selected"] > 0 or event["failure_category"] == "search-truncated")
            marked &= event["selected"] == 0 or search_truncated(event["found"])
    check("limits reached are marked search-truncated (U-K3 on delivered tracks)", marked)
    return results


# ---- The T07 evaluation tasks (fix round 1, I1: the coordinator's ruling, E6b owns their code; E6c's T07 tasks call this command line).

TASK_BLOCKS = EVALUATION_BLOCKS + (DEVELOPMENT_BLOCK,)     # evaluation attempts; block 1 for the development job only
DRAWS_STARTED, FIT_STARTED = layout.EVENTS_ENTERED         # the milestones the collection classifies attempts by (E6a fix round 1, I4)
REFIT_KEY_RULE = ("event-<ordinal>-track-<particle_key>: the ordinal is the event's position in the bin's whole data file (0 .. N - 1), never its "
                  "place in a refit range; the particle key is the truth file's")
# I3 and the user's answer (decisions.md, the coordinator's message of 2026-11-12: "Rerun at evaluation"): the T07 deterministic checks (v4 11:
# A05, A07, A17, A39; refit never reported as finding) and the CAI checks (R37) run once inside the evaluation submission, at the frozen hash, on
# their own v4 3.2 blocks (block 1 and block 6, the modules' own), and the summary reads that result. No other source is accepted.
DETERMINISTIC_CHECKS_SOURCE = "rerun at evaluation"
T07_CHECKS = (("A05: interleaved events and hit sets keep their own results", "deterministic", "tests.adapters.test_acts_scenarios"),
              ("A07: branches, revisions and counts traceable; refit never reported as finding", "deterministic", "tests.adapters.test_acts_finding"),
              ("A17: results bound to their hypothesis (payload, field)", "deterministic", "tests.adapters.test_acts_cai_refit"),
              ("A39: observable grouping only; the truth-seeded run never finding", "deterministic", "tests.adapters.test_acts_truth_seeded"),
              ("CAI-T07-1 and CAI-T07-2: rigid shift, derivatives against finite differences", "cai", "tests.adapters.test_acts_track_outputs"),
              ("CAI-T07-3 and CAI-T07-4: refit under a payload, sagitta-like weak mode", "cai", "tests.adapters.test_acts_cai_refit"))


class TaskFailed(RuntimeError):
    """A program of a task failed or left no output: the task fails (exit 1, RESULT failed), its attempt NOT-REPEATABLE at the collection."""


def refit_key(ordinal: int, particle_key: int) -> str:
    """The refit hit set's key (REFIT_KEY_RULE): what _score_refit requires of every refit product."""
    return f"event-{int(ordinal)}-track-{int(particle_key)}"


def mark(out, name: str) -> None:
    """A milestone in the task folder's milestones.txt, written before the step it names (E6a re-review N3)."""
    path = Path(out) / "milestones.txt"
    if path.exists() and name in [line.split(" ", 1)[0] for line in path.read_text(encoding="utf-8").splitlines()]:
        return
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(f"{name} {__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime())}\n")


def attempt_name() -> str:
    import os
    job = os.environ.get("SLURM_ARRAY_JOB_ID") or os.environ.get("SLURM_JOB_ID") or "unset"
    task = os.environ.get("SLURM_ARRAY_TASK_ID")
    return f"{job}_{task}" if task is not None else job


def write_range_record(out, kind: str, record: layout.RangeRecord) -> None:
    folder = Path(out) / "records"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{kind}.json").write_text(record.to_json() + "\n", encoding="utf-8")


def read_range_record(folder, kind: str):
    path = Path(folder) / "records" / f"{kind}.json"
    return layout.RangeRecord.from_json(path.read_text(encoding="utf-8")) if path.is_file() else None


def bin_files(folder, fixture_id: int, block: int, stratum: int) -> dict:
    stem = Path(folder) / f"{FIXTURES[fixture_id]}-b{block}-s{stratum}"
    return {kind: Path(f"{stem}.{kind}") for kind in ("t07data", "t07truth", "record", "product", "stderr", "t07starts")} | \
        {"truth-seeded": Path(f"{stem}.truth-seeded.record"), "truth-seeded-product": Path(f"{stem}.truth-seeded.product")}


def _run(command, log) -> float:
    import subprocess
    import time
    started = __import__("time").monotonic()
    with open(log, "w", encoding="utf-8") as stream:
        done = subprocess.run([str(c) for c in command], stdout=stream, stderr=subprocess.STDOUT)
    if done.returncode != 0:
        raise TaskFailed(f"{Path(str(command[0])).name} exited {done.returncode} (log {Path(log).name})")
    return time.monotonic() - started


def bin_task(block: int, fixture_id: int, stratum: int, *, build, out, first: int = 0, count: int = layout.EVENTS_PER_BIN) -> list:
    """One T07 bin task (v4 4.1, 8.1): milestone draws-started; the frozen generator on (fixture, block, stratum, first, count); the finder
    on the data file alone with the vertex step and every event in the product; for a noise bin, milestone fit-started, section 7's
    truth-seeded run of the same recipe on the same events, then the data file deleted after its SHA-256 matched the record's and the truth's
    (U-B11). The clean data file is kept for the refit tasks. Records (records/<kind>.json, layout.RangeRecord): "record" (the finding
    record, the collection's product; stratum_sha256 and input_sha256 the data file's), "product", "truth", and "truth-seeded" for noise."""
    from tests.adapters import test_acts_truth_seeded as seeded_tests
    bin_identity(fixture_id, block, stratum)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = bin_files(out, fixture_id, block, stratum)
    build = Path(build)
    lines = []
    mark(out, DRAWS_STARTED)
    seconds = _run([build / "t07_fixture_generator", "generate", "--fixture", FIXTURES[fixture_id], "--block", block, "--stratum", stratum, "--first-event", first,
                    "--count", count, "--data-file", files["t07data"], "--truth-file", files["t07truth"]], out / "generate.log")
    lines.append(f"COST t07 bin {FIXTURES[fixture_id]} s{stratum} generate {count} events: {seconds:.1f} s")
    head = truth_files.read_truth_header(files["t07truth"])
    if (head["fixture_id"], head["block"], head["stratum"], head["event_count"]) != (fixture_id, block, stratum, count):
        raise TaskFailed(f"the truth file is of {(head['fixture_id'], head['block'], head['stratum'], head['event_count'])}")
    import subprocess
    with open(files["stderr"], "w", encoding="utf-8") as stream:
        started = __import__("time").monotonic()
        done = subprocess.run([str(c) for c in fake_rate.finder_command(build / "acts_tracking_finder", files["t07data"], f"evaluation-{FIXTURES[fixture_id]}-b{block}-s{stratum}",
                                                                         files["product"], files["record"], count)], stdout=subprocess.DEVNULL, stderr=stream)
    if done.returncode != 0:
        raise TaskFailed(f"the finder exited {done.returncode}")
    lines.append(f"COST t07 bin {FIXTURES[fixture_id]} s{stratum} find {count} events: {__import__('time').monotonic() - started:.1f} s")
    data_sha256 = sha256_file(files["t07data"])
    record = finding_record.parse_record(files["record"].read_text(encoding="utf-8"))
    if record["header"]["data_sha256"] != data_sha256 or head["data_sha256"] != data_sha256 or len(record["events"]) != count:
        raise TaskFailed("the record, the truth file and the data file disagree (data_sha256 or events)")
    events = tuple(range(first, first + count))
    write_range_record(out, "record", layout.RangeRecord(WORKFLOW, fixture_id, block, stratum, first, count, events, sha256_file(files["record"]), data_sha256,
                                                         data_sha256, attempt_name()))
    write_range_record(out, "product", layout.RangeRecord(WORKFLOW, fixture_id, block, stratum, first, count, events, sha256_file(files["product"]), data_sha256,
                                                          data_sha256, attempt_name()))
    write_range_record(out, "truth", layout.RangeRecord(WORKFLOW, fixture_id, block, stratum, first, count, events, sha256_file(files["t07truth"]), data_sha256,
                                                        data_sha256, attempt_name()))
    if fixture_id == 7002:
        mark(out, FIT_STARTED)
        files["t07starts"].write_text(seeded_tests.start_file_text(list(truth_files.iter_truth_events(files["t07truth"])), data_sha256), encoding="utf-8")
        seconds = _run([build / "acts_truth_seeded_run", "--data-file", files["t07data"], "--start-file", files["t07starts"], "--product-id",
                        f"truth-seeded-b{block}-s{stratum}", "--product-file", files["truth-seeded-product"], "--record-file", files["truth-seeded"],
                        "--product-events", seeded_tests.PRODUCT_EVENTS], out / "truth-seeded.log")
        seeded, why = _truth_seeded(files["truth-seeded"], record["header"], count)
        if why:
            raise TaskFailed(f"the truth-seeded run: {why}")
        lines.append(f"COST t07 bin noise s{stratum} truth-seeded run: {seconds:.1f} s")
        write_range_record(out, "truth-seeded", layout.RangeRecord(WORKFLOW, fixture_id, block, stratum, first, count, events, sha256_file(files["truth-seeded"]),
                                                                   data_sha256, sha256_file(files["t07starts"]), attempt_name()))
        deletion = fake_rate.delete_after_hash_match(files["t07data"], [record["header"]["data_sha256"], head["data_sha256"]])
        lines.append(f"DELETION noise s{stratum} data file {'deleted' if deletion['deleted'] else 'kept'}: {deletion['reason']}")
        if not deletion["deleted"]:
            raise TaskFailed(deletion["reason"])
    return lines


def refit_task(block: int, stratum: int, *, first: int, count: int, bin_dir, build, out) -> list:
    """One refit range of a clean bin (v4 8.1, reco.track.acts-kf-refit/1 on known hit sets): milestone fit-started; the hit sets of the bin's
    events first .. first + count - 1, keyed by refit_key with the event's ordinal in the bin's whole data file; acts_tracking_driver refit
    on the bin task's data file at 1 T. Record "refit": product_sha256 the refit product's, stratum_sha256 the data file's, input_sha256 the
    hit-set file's."""
    import t07_fixture_files as fixture_files
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mark(out, FIT_STARTED)
    files = bin_files(bin_dir, 7001, block, stratum)
    bin_identity(7001, block, stratum)
    head = truth_files.read_truth_header(files["t07truth"])
    if (head["fixture_id"], head["block"], head["stratum"]) != (7001, block, stratum) or not 0 <= first < first + count <= head["event_count"]:
        raise TaskFailed(f"refit {first}+{count} is not a range of clean block {block} stratum {stratum} ({head['event_count']} events)")
    data_sha256 = sha256_file(files["t07data"])
    if data_sha256 != head["data_sha256"]:
        raise TaskFailed("the bin's data file is not the one its truth file names")
    hit_sets = []
    for ordinal, truth_event in enumerate(truth_files.iter_truth_events(files["t07truth"])):
        if first <= ordinal < first + count:
            for track in truth_event["tracks"]:
                keys = [int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY]
                hit_sets.append((refit_key(ordinal, track["particle_key"]), ordinal, float(track["q_over_p"]), keys))
    name = f"refit-b{block}-s{stratum}-{first}"
    hit_set_file, product = out / f"{name}.hitsets", out / f"{name}.product"
    hit_set_file.write_text(fixture_files.hit_sets_text(data_sha256, hit_sets), encoding="utf-8")
    seconds = _run([Path(build) / "acts_tracking_driver", "refit", "--data-file", files["t07data"], "--hit-sets", hit_set_file, "--field-tesla", "1",
                    "--product-id", name, "--product-file", product], out / "refit.log")
    if not product.is_file():
        raise TaskFailed("the refit exited 0 but left no product")
    write_range_record(out, "refit", layout.RangeRecord(WORKFLOW, 7001, block, stratum, first, count, tuple(range(first, first + count)), sha256_file(product),
                                                        data_sha256, sha256_file(hit_set_file), attempt_name()))
    return [f"COST t07 refit clean s{stratum} events {first}-{first + count - 1}: {seconds:.1f} s, product {product.stat().st_size} bytes"]


def refit_product_path(folder, block: int, stratum: int, first: int) -> Path:
    return Path(folder) / f"refit-b{block}-s{stratum}-{first}.product"


def collect_task(block: int, fixture_id: int, stratum: int, attempts: dict, *, pieces=None, count: int = layout.EVENTS_PER_BIN) -> dict:
    """The collection of one T07 bin (afterany on its tasks): attempts {"bin": [[verdict, folder], ...], "refit": {"first": [[verdict, folder],
    ...]}}, verdicts by layout.classify_attempt (E6c: sacct and each folder's milestones). The bin by layout.collect_bin (the finding record
    as its product, kind t07-record), its product, truth and truth-seeded record by their records' SHA-256, and for a clean bin the refit
    pieces by collect_refit (N1, with the hit-set files and the bin's data file). Returns the collection score-bin --collection reads."""
    identity = bin_identity(fixture_id, block, stratum)
    span = layout.EventRange(0, count)
    tried, folders = [], []
    for verdict, folder in attempts.get("bin", []):
        tried.append((verdict, read_range_record(folder, "record")))
        folders.append(Path(folder))
    files, products = None, {}
    try:
        index = layout.select_attempt([v for v, _ in tried], block=block) if tried else None
        if index is not None:
            files = bin_files(folders[index], fixture_id, block, stratum)
            if files["record"].is_file():
                products = {0: files["record"].read_bytes()}
    except layout.LayoutError:
        pass
    found = layout.collect_bin(identity, [span], {span: tried} if tried else {}, products, kind="t07-record", total=count)
    document = {"workflow": WORKFLOW, "fixture_id": fixture_id, "block": block, "stratum": stratum, "events": count, "status": found.status, "reason": found.reason}
    if found.status == "complete":
        for kind, name in (("product", "product"), ("truth", "t07truth")) + ((("truth-seeded", "truth-seeded"),) if fixture_id == 7002 else ()):
            record = read_range_record(folders[index], kind)
            if record is None or not files[name].is_file() or sha256_file(files[name]) != record.product_sha256:
                document.update(status="missing", reason=f"the {kind} file is absent or not its record's (SHA-256)")
                break
        document["files"] = {name: str(path) for name, path in files.items() if path.is_file()}
    if fixture_id == 7001 and document["status"] == "complete":
        pieces = list(pieces) if pieces is not None else []
        refit_attempts, refit_products, refit_inputs = {}, {}, {}
        for piece in pieces:
            rows = []
            for verdict, folder in attempts.get("refit", {}).get(str(piece.first), []):
                rows.append((verdict, read_range_record(folder, "refit")))
                refit_products.setdefault(piece.first, []).append(refit_product_path(folder, block, stratum, piece.first))
                refit_inputs.setdefault(piece.first, []).append(Path(folder) / f"refit-b{block}-s{stratum}-{piece.first}.hitsets")
            refit_attempts[piece] = rows
        chosen_products, chosen_inputs = {}, {}
        for piece, rows in refit_attempts.items():
            try:
                index_of = layout.select_attempt([v for v, _ in rows], block=block) if rows else None
            except layout.LayoutError:
                index_of = None
            if index_of is not None:
                chosen_products[piece.first] = refit_products[piece.first][index_of]
                chosen_inputs[piece.first] = refit_inputs[piece.first][index_of]
        record = read_range_record(folders[index], "record")
        refit = collect_refit(identity, pieces, refit_attempts, chosen_products, total=count, inputs=chosen_inputs, data_sha256=record.stratum_sha256)
        document["refit"] = {"status": refit.status, "reason": refit.reason, "records": [json.loads(r.to_json()) for r in refit.records],
                             "products": {str(first): str(path) for first, path in chosen_products.items()}}
    return document


def negative_task(block: int, *, build, folder, out) -> tuple:
    """E5 at evaluation (v4 11): the kept case file's hashes first, then the finder on it alone (no vertex step), with its seed side file, then
    negative_case_checks; writes negative-checks.json (CheckResults)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    description = check_negative_case_folder(folder)
    command = fake_rate.finder_command(Path(build) / "acts_tracking_finder", Path(folder) / negative_cases.CASE_FILE, "evaluation-negative-cases",
                                       out / "negative.product", out / "negative.record", 0)
    command = [c for c in command if c not in ("--vertex-recipe", finding_record.VERTEX_RECIPE)] + ["--seed-file", out / "negative.seeds"]
    seconds = _run(command, out / "finder.log")
    record = finding_record.parse_record((out / "negative.record").read_text(encoding="utf-8"))
    if record["header"]["data_sha256"] != NEGATIVE_CASE_SHA256 or record["header"]["configuration_sha256"] != FREEZE_B_CONFIGURATION_SHA256:
        raise ScoringError("the finder's record is not of the kept case file at the configuration fixed at Freeze B (v4 11)")
    checks = negative_case_checks(description, record, list(finding_record.iter_seed_events(out / "negative.seeds")))
    (out / "negative-checks.json").write_text(json.dumps([dataclasses.asdict(c) for c in checks], sort_keys=True) + "\n", encoding="utf-8")
    return [f"COST t07 negative cases finder: {seconds:.1f} s"] + [f"CHECK negative (section 11) {c.name}: {c.result}" for c in checks], checks


class ChecksCrashed(RuntimeError):
    """A check module could not run (E6 merge review I2): no unittest result line, errors with no failure, or an import or OS error in its
    output. A crash (exit 3, core/status.py: the task is rerun), never a failed check; no checks file is written."""


# Exceptions whose traceback in a module's output marks a setup defect, not a check that ran and failed: ImportError and OSError with their
# subclasses (ModuleNotFoundError, PermissionError, FileNotFoundError, a read-only file system's OSError, ...).
SETUP_ERRORS = tuple(sorted(name for name, value in vars(builtins).items() if isinstance(value, type) and issubclass(value, (ImportError, OSError))))


UNITTEST_RAN = r"^Ran \d+ tests? in [\d.]+s$"
UNITTEST_SUMMARY = r"^(OK|FAILED)( \((failures|errors|skipped|expected failures|unexpected successes)=\d+(, (failures|errors|skipped|expected failures|unexpected successes)=\d+)*\))?$"


def unittest_verdict(module: str, text: str) -> str:
    """E6 merge re-review N3: the module's verdict is unittest's own final summary only: the first non-blank line after the last "Ran N tests in
    Xs" line, in unittest's form (OK or FAILED, with its counts). An earlier line that starts with OK or FAILED (a program's output) is never
    the verdict; no such summary (the module killed, or never reaching it) is a crash."""
    import re
    lines = text.splitlines()
    ran = [index for index, line in enumerate(lines) if re.match(UNITTEST_RAN, line)]
    following = [line for line in lines[ran[-1] + 1:] if line.strip()] if ran else []
    if not following or not re.match(UNITTEST_SUMMARY, following[0]):
        raise ChecksCrashed(f"{module} ended with no unittest summary after its 'Ran N tests' line (a crash, not a negative)")
    return following[0]


def module_crash(module: str, text: str, verdict: str) -> None:
    """Raise ChecksCrashed when a check module's run is a crash: its unittest summary counts a skip (re-review N1: a setup gap, such as a build
    or a variable not set) or errors and no failure, or a traceback in its output ends in an import or OS error (SETUP_ERRORS). A module that
    ran and failed (failures, with no skip and no setup error) is a failed check."""
    import re
    counts = dict((name, int(n)) for name, n in re.findall(r"(failures|errors|skipped)=(\d+)", verdict))
    if counts.get("skipped", 0):
        raise ChecksCrashed(f"{module}: {verdict}, a test skipped (a setup gap: a crash, never a pass or a fail; re-review N1)")
    if counts.get("errors", 0) and not counts.get("failures", 0):
        raise ChecksCrashed(f"{module}: {verdict}, errors with no failure (a crash, not a negative)")
    pattern = r"^(?:[A-Za-z_][\w.]*\.)?(" + "|".join(SETUP_ERRORS) + r")(?::|$)"
    found = re.search(pattern, text, flags=re.M)
    if "Traceback (most recent call last)" in text and found:
        raise ChecksCrashed(f"{module}: its output holds a {found.group(1)} traceback (a setup defect, a crash, not a negative): {verdict}")


def checks_task(block: int, *, build, out, workers: int = 1, module_runner=None) -> tuple:
    """I3, DETERMINISTIC_CHECKS_SOURCE: each module of T07_CHECKS run once at the frozen hash with the build (python -B -m unittest -v), on its
    own blocks; a check passes when its module's unittest summary (unittest_verdict) is OK, fails on FAILED with a failure. A module with no
    unittest summary, with a skip, with errors and no failure, or with an import or OS error traceback is a crash (ChecksCrashed: the task is
    incomplete, exit 3; E6 merge review I2, re-review N1 and N3). Writes deterministic-checks.json only when every module was read."""
    import os
    import subprocess
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    def run_module(module):
        environment = dict(os.environ, HEP_ACTS_TRACKING_BUILD=str(build), HEP_ACTS_TRACKING_EVIDENCE=str(out / "evidence"),
                           HEP_ACTS_TRACKING_WORKERS=str(workers))
        (out / "evidence").mkdir(exist_ok=True)
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", module], cwd=str(ROOT), env=environment, capture_output=True, text=True)
        (out / f"{module.rsplit('.', 1)[1]}.log").write_text(done.stdout + done.stderr, encoding="utf-8")
        return done.stdout + done.stderr
    run = module_runner or run_module
    results, lines = {}, []
    for module in dict.fromkeys(module for _, _, module in T07_CHECKS):
        text = run(module)
        verdict = unittest_verdict(module, text)
        module_crash(module, text, verdict)
        results[module] = verdict.startswith("OK")
        lines.append(f"CHECK module {module}: {verdict}")
    checks = [core.CheckResult(name, kind, "pass" if results[module] else "fail") for name, kind, module in T07_CHECKS]
    (out / "deterministic-checks.json").write_text(json.dumps([dataclasses.asdict(c) for c in checks], sort_keys=True) + "\n", encoding="utf-8")
    return lines + [f"CHECK {c.kind} {c.name}: {c.result} ({DETERMINISTIC_CHECKS_SOURCE})" for c in checks], checks


INTERFACE_COMMANDS = {"bin": "bin-task", "refit": "refit-task", "collect": "collect", "score": "score-bin", "pool": "score-slices",
                      "negative-cases": "negative-task", "checks": "checks-task", "summary": "summary"}


def interface_argv(operation: str, **arguments) -> list:
    """The command line t07_interface runs: the operation's command, then each keyword as its option (dashes for underscores; None and False
    left out, True a flag). E6 merge stage: E6c's task runner builds its calls with this, and its test parses them through build_parser."""
    if operation not in INTERFACE_COMMANDS:
        raise ScoringError(f"operation {operation}: one of {sorted(INTERFACE_COMMANDS)}")
    argv = [INTERFACE_COMMANDS[operation]]
    for name, value in arguments.items():
        if value is None or value is False:
            continue
        argv += [f"--{name.replace('_', '-')}"] + ([] if value is True else [str(value)])
    return argv


def t07_interface(operation: str, **arguments) -> int:
    """The one call of E6c's T07 tasks (its stub's signature): operation bin, refit, collect, score, pool, negative-cases, checks or summary,
    with the command line's options as keywords (dashes as underscores). Returns the command's exit code; the command prints its result line."""
    try:
        argv = interface_argv(operation, **arguments)
    except ScoringError as error:
        _result("interface", "rejected", str(error))
        return EXIT_BAD_INPUT
    return main(argv)


# ---- The workflow (section 10), never on development records.

NEGATIVE_CHECK_NAMES = ("wrong hits: honest", "wrong hits: one-wrong-plane", "wrong hits: three-wrong-planes", "branch explosion: branch-explosion",
                        "seed budget: seed-budget", "seed failure: no-triple", "seed failure: two-planes", "seed outcomes balance the counters in every case",
                        f"any two lost planes: at most {LOST_PAIRS_LIMIT} tracks lost", f"a track alone losing two planes: at most {LOST_ALONE_LIMIT} lost",
                        "limits reached are marked search-truncated (U-K3 on delivered tracks)")


class ChecksIncomplete(ScoringError):
    """The summary's checks are not whole (a required check absent, or one given twice): incomplete (exit 3), rerun the check's task; never
    read as a fail (E6c re-review; the E6 merge stage)."""


def required_checks() -> tuple:
    """I3: the names of the checks a T07 outcome needs (v4 10's "deterministic, negative and CAI checks pass"; v4 11's T07 row): E5's negative
    checks (NEGATIVE_CHECK_NAMES) and the deterministic and CAI checks (T07_CHECKS). The summary passes them to core.workflow_outcome
    (required_checks), which refuses an outcome while any is absent: an absent check is incomplete, never a fail (E6 merge stage)."""
    return NEGATIVE_CHECK_NAMES + tuple(name for name, _, _ in T07_CHECKS)


def summarize(records, checks, *, sensitivity_changes, forbidden_constants=(), critical_false_success=(), evaluation_could_not_run=False,
              freeze_b_blocks_used_up=False) -> core.WorkflowOutcome:
    """Section 10 on T07's records (24 bins and 2 slice pools), its required checks (required_checks: E5, the deterministic and CAI checks) and
    the sensitivity rerun: the core's workflow_outcome. Refuses a development record (block 1): a development reading has no verdict; and a
    record whose (bin, gate, statistic) appears twice (review M7: the count alone would not see a doubled file hiding a missing one)."""
    records = list(records)
    if any(record.bin.startswith(DEVELOPMENT_LABEL) for record in records):
        raise ScoringError("a development reading (block 1) has no verdict: summarize takes evaluation records only")
    doubled = [key for key, n in collections.Counter((r.bin, r.gate, r.statistic) for r in records).items() if n > 1]
    if doubled:
        raise ScoringError(f"{len(doubled)} records appear more than once, first {doubled[0]}: refused")
    checks = list(checks)
    given_twice = sorted(name for name, n in collections.Counter(c.name for c in checks).items() if n > 1)
    if given_twice:
        raise ChecksIncomplete(f"checks given more than once: {given_twice}; rerun the task that wrote them (no draw)")
    attempts = {record.attempt for record in records}
    if len(attempts) != 1:
        raise ScoringError(f"the records are of attempts {sorted(attempts)}: one attempt per run (section 3.4)")
    absent = sorted(set(required_checks()) - {c.name for c in checks})
    if absent:   # a required check absent (the core would refuse the outcome), as E6c's summary: incomplete, never a fail
        raise ChecksIncomplete(f"required checks absent: {absent}; rerun the task that writes them (no draw)")
    disagrees, _ = matching_sentence(sensitivity_changes)
    try:
        return core.workflow_outcome(WORKFLOW, records, checks, attempt=attempts.pop(), forbidden_constants=forbidden_constants,
                                     critical_false_success=critical_false_success, evaluation_could_not_run=evaluation_could_not_run,
                                     matching_sensitivity_disagrees=disagrees, freeze_b_blocks_used_up=freeze_b_blocks_used_up,
                                     required_checks=required_checks())
    except core.CoreError as error:   # E6 merge review M2: any other refusal of the core is a record defect, refused (exit 2), not a rerun
        raise ScoringError(f"a record defect, refused by the core (not an absent check; the coordinator's): {error}") from None


# ---- Files and the command line (the interface of E6c's T07 tasks).

def records_name(fixture_id: int, block: int, stratum: int) -> str:
    return f"t07-score-{fixture_id}-b{block}-s{stratum}.records.jsonl"


def slices_name(fixture_id: int, block: int, stratum: int) -> str:
    return f"t07-score-{fixture_id}-b{block}-s{stratum}.slices.npz"


def slice_records_name(fixture_id: int, block: int, parameters=PARAMETERS) -> str:
    return f"t07-slices-{fixture_id}-b{block}-{'-'.join(p.replace('/', '') for p in parameters)}.records.jsonl"


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (numpy.integer,)):
        return int(value)
    if isinstance(value, (numpy.floating,)):
        return float(value)
    return value


def write_records(path, records) -> None:
    Path(path).write_text("".join(json.dumps(_plain(dataclasses.asdict(r)), sort_keys=True) + "\n" for r in records), encoding="utf-8")


def read_records(path) -> list:
    return [core.TestResult(**json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def write_slices(path, identity, score: dict, record_sha256: str, status: str, reason: str) -> None:
    head = {"fixture_id": identity.fixture_id, "block": identity.block, "stratum": identity.stratum, "events": int(score["tally"].events) if score else 0,
            "status": status, "reason": reason, "record_sha256": record_sha256}
    arrays = {"header": numpy.array(json.dumps(head, sort_keys=True))}
    if score:
        for label, population in score["slices"].items():
            for name, values in population.items():
                arrays[f"{label}/{name}"] = values
    with open(path, "wb") as stream:
        numpy.savez(stream, **arrays)


def read_slices(path) -> dict:
    with numpy.load(path, allow_pickle=False) as found:
        head = json.loads(str(found["header"]))
        head["populations"] = {label: {name: found[f"{label}/{name}"] for name in ("ordinal", "slope_u", "pulls", "without_ordinal", "without_slope_u")
                                       if f"{label}/{name}" in found.files}
                               for label in ("0.5", "0.7") if f"{label}/ordinal" in found.files}
    return head


def record_line(record: core.TestResult) -> str:
    """A record as a printed line. A development record's result word is labelled a development reading: it is no verdict."""
    word = f"{record.result} ({DEVELOPMENT_LABEL})" if record.bin.startswith(DEVELOPMENT_LABEL) else record.result
    numbers = " ".join(f"{name} {value:.6g}" if isinstance(value, float) else f"{name} {value}"
                       for name, value in (("estimate", record.estimate), ("standard_error", record.standard_error), ("lower", record.lower),
                                           ("upper", record.upper), ("limit", record.limit)) if value is not None)
    return f"{record.bin} | {record.gate} {record.statistic} {numbers} step {record.step} attempt {record.attempt} required {int(record.required)}: {word}" \
           + (f" ({record.reason})" if record.reason else "")


def _result(operation: str, word: str, text: str) -> None:
    print(f"RESULT t07-scoring {operation} {word}: {text}", flush=True)


def _score_bin_command(arguments) -> int:
    try:
        identity = bin_identity(arguments.fixture_id, arguments.block, arguments.stratum)
    except (ScoringError, core.CoreError) as error:
        _result("score-bin", "rejected", str(error))
        return EXIT_BAD_INPUT
    out = Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    if arguments.collection:
        try:
            collection = json.loads(Path(arguments.collection).read_text(encoding="utf-8"))
            if (collection["workflow"], collection["fixture_id"], collection["block"], collection["stratum"]) != (WORKFLOW, identity.fixture_id, identity.block, identity.stratum):
                raise ScoringError("the collection is of another bin")
        except (OSError, ValueError, KeyError, ScoringError) as error:
            _result("score-bin", "rejected", f"the collection does not read: {error}")
            return EXIT_BAD_INPUT
        if collection["status"] != "complete":
            reason = f"the bin is incomplete at the collection: {collection['reason']}"
            write_records(out / records_name(identity.fixture_id, identity.block, identity.stratum), layout.missing_bin_records(identity, bin_gates(identity.fixture_id), collection["reason"]))
            write_slices(out / slices_name(identity.fixture_id, identity.block, identity.stratum), identity, None, "", "missing", reason)
            _result("score-bin", "ok", f"{identity.label}: {len(bin_gates(identity.fixture_id))} records written, every one required output missing ({reason})")
            return EXIT_OK
        names = collection["files"]
        arguments.record, arguments.product, arguments.truth = names.get("record", ""), names.get("product", ""), names.get("t07truth", "")
        arguments.truth_seeded_record = names.get("truth-seeded")
        if "refit" in collection:
            refit_path = out / f"refit-collection-{identity.fixture_id}-b{identity.block}-s{identity.stratum}.json"
            refit_path.write_text(json.dumps(collection["refit"], sort_keys=True) + "\n", encoding="utf-8")
            arguments.refit_collection = str(refit_path)
    if not (arguments.record and arguments.product and arguments.truth):
        _result("score-bin", "rejected", "give --collection, or --record, --product and --truth")
        return EXIT_BAD_INPUT
    try:   # review M2: an unreadable refit collection makes the refit tests "required output missing", never a crash
        refit = read_refit_collection(arguments.refit_collection) if arguments.refit_collection else None
    except (OSError, ValueError, KeyError, TypeError, layout.LayoutError) as error:
        refit = RefitInput(layout.BinCollection("missing", f"the refit collection does not read: {error}", ()), {})
    inputs = BinInputs(Path(arguments.record), Path(arguments.product), Path(arguments.truth),
                       Path(arguments.truth_seeded_record) if arguments.truth_seeded_record else None, refit,
                       Path(arguments.rate_record) if arguments.rate_record else None)
    try:
        score = score_bin(identity, inputs, events=arguments.events)
    except ScoringError as error:
        reason = f"the bin's files are refused: {error}"
        write_records(out / records_name(identity.fixture_id, identity.block, identity.stratum),
                      [core.missing_output(g, identity, s, reason) for g, s in bin_gates(identity.fixture_id)])
        write_slices(out / slices_name(identity.fixture_id, identity.block, identity.stratum), identity, None, "", "missing", reason)
        _result("score-bin", "rejected", reason)
        return EXIT_BAD_INPUT
    records = score["records"]
    write_records(out / records_name(identity.fixture_id, identity.block, identity.stratum), records)
    status = "complete" if score["product_complete"] else "missing"
    write_slices(out / slices_name(identity.fixture_id, identity.block, identity.stratum), identity, score, sha256_file(inputs.record), status,
                 "" if status == "complete" else score["tally"].missing["product"])
    (out / records_name(identity.fixture_id, identity.block, identity.stratum).replace(".records.jsonl", ".sensitivity.json")).write_text(
        json.dumps(_plain({"estimates": [[list(k), v] for k, v in score["estimates"].items()], "sensitivity": score["sensitivity"],
                           "readings": score["readings"]}), sort_keys=True) + "\n", encoding="utf-8")
    for record in records:
        print(("READING " if is_development(identity) else "RECORD ") + record_line(record))
    for name, value in score["readings"].items():
        print(f"READING {identity.label} | reported, not gated (section 8.4): {name}: {value}")
    disagrees, sentence = matching_sentence(score["sensitivity"])
    beyond = [c for c in score["sensitivity"] if c["beyond"]]
    print(f"READING {identity.label} | matching at 70 % (section 7.1): {len(score['sensitivity'])} quantities, {len(beyond)} beyond their thresholds; "
          + (sentence if sentence else "the sentence 'not sensitive to the matching threshold' is withheld for this bin") + " (recorded, no effect)")
    words = collections.Counter(r.result for r in records)
    _result("score-bin", "ok", f"{identity.label}: {len(records)} records written ({dict(sorted(words.items()))})"
            + (f"; {DEVELOPMENT_LABEL}, no verdict" if is_development(identity) else ""))
    return EXIT_OK


def _score_slices_command(arguments) -> int:
    try:
        if arguments.block not in EVALUATION_BLOCKS + (DEVELOPMENT_BLOCK,):
            raise ScoringError(f"block {arguments.block}: slices are scored on blocks 11 and 12, or read on block 1")
        slice_identity(arguments.fixture_id, arguments.block, 0)
        parameters = tuple(arguments.parameters.split(",")) if arguments.parameters else PARAMETERS
        if not set(parameters) <= set(PARAMETERS):
            raise ScoringError(f"parameters {parameters}: of {PARAMETERS}")
    except (ScoringError, core.CoreError) as error:
        _result("score-slices", "rejected", str(error))
        return EXIT_BAD_INPUT
    folder = Path(arguments.bins)
    bins = [read_slices(path) for path in sorted(folder.glob(f"t07-score-{arguments.fixture_id}-b{arguments.block}-s*.slices.npz"))]
    found = score_slices(arguments.fixture_id, arguments.block, bins, events_per_bin=arguments.events, parameters=parameters)
    out = Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    name = slice_records_name(arguments.fixture_id, arguments.block, parameters)
    write_records(out / name, found["records"])
    (out / name.replace(".records.jsonl", ".sensitivity.json")).write_text(json.dumps(_plain({"sensitivity": found["sensitivity"]}), sort_keys=True) + "\n",
                                                                           encoding="utf-8")
    development = arguments.block == DEVELOPMENT_BLOCK
    for record in found["records"]:
        print(("READING " if development else "RECORD ") + record_line(record))
    words = collections.Counter(r.result for r in found["records"])
    _result("score-slices", "ok", f"fixture {arguments.fixture_id} block {arguments.block} parameters {','.join(parameters)}: {len(found['records'])} records "
            f"({dict(sorted(words.items()))})" + (f"; {DEVELOPMENT_LABEL}, no verdict" if development else ""))
    return EXIT_OK


def _negative_cases_command(arguments) -> int:
    try:
        description = check_negative_case_folder(arguments.folder)
        record = finding_record.parse_record(Path(arguments.record).read_text(encoding="utf-8"))
        seeds = list(finding_record.iter_seed_events(arguments.seeds))
        if record["header"]["data_sha256"] != NEGATIVE_CASE_SHA256:
            raise ScoringError("the record is not of the kept case file (data_sha256)")
        if record["header"]["configuration_sha256"] != FREEZE_B_CONFIGURATION_SHA256:
            raise ScoringError("the record is not of the recipe configuration fixed at Freeze B (v4 11; review M4)")
    except (ScoringError, finding_record.RecordFormatError, OSError, UnicodeDecodeError) as error:
        _result("negative-cases", "rejected", str(error))
        return EXIT_BAD_INPUT
    checks = negative_case_checks(description, record, seeds)
    Path(arguments.out).write_text(json.dumps([dataclasses.asdict(c) for c in checks], sort_keys=True) + "\n", encoding="utf-8")
    for item in checks:
        print(f"CHECK negative (section 11) {item.name}: {item.result}" + (f" ({DEVELOPMENT_LABEL})" if arguments.block == DEVELOPMENT_BLOCK else ""))
    failing = [c.name for c in checks if c.result != "pass"]
    _result("negative-cases", "ok" if not failing else "failed", f"{len(checks) - len(failing)} of {len(checks)} negative checks fired as v4 11 expects"
            + (f"; not: {failing}" if failing else ""))
    return EXIT_OK if not failing else EXIT_NEGATIVE


def _summary_command(arguments) -> int:
    folder = Path(arguments.scores)
    records = []
    for path in sorted(folder.glob(f"t07-score-*-b{arguments.block}-s*.records.jsonl")) + sorted(folder.glob(f"t07-slices-*-b{arguments.block}-*.records.jsonl")):
        records += read_records(path)
    changes = []
    for path in sorted(folder.glob(f"*-b{arguments.block}*.sensitivity.json")):
        changes += json.loads(path.read_text(encoding="utf-8"))["sensitivity"]
    checks = []
    for name in (arguments.checks.split(",") if arguments.checks else []):
        if Path(name).is_file():
            checks += [core.CheckResult(**item) for item in json.loads(Path(name).read_text(encoding="utf-8"))]
    try:
        outcome = summarize(records, checks, sensitivity_changes=changes)
    except ChecksIncomplete as error:
        print(f"SUMMARY INCOMPLETE T07 block {arguments.block}: {error}")
        _result("summary", "incomplete", str(error))
        return EXIT_INCOMPLETE
    except ScoringError as error:
        _result("summary", "rejected", str(error))
        return EXIT_BAD_INPUT
    print(f"SUMMARY T07 attempt {outcome.attempt}: workflow {outcome.workflow_result}, R11 state {outcome.r11_state}; {len(records)} records")
    for name, word in sorted(outcome.gate_results.items()):
        print(f"GATE {name}: {word}")
    for line in outcome.reasons:
        print(f"REASON {line}")
    for item in outcome.open_obligations:
        print(f"OBLIGATION {item.name} (owner {item.owner}): {item.reason}")
    for line in outcome.recorded:
        print(f"RECORDED {line}")
    _result("summary", "ok", f"T07 {outcome.workflow_result}, {outcome.r11_state}")
    return EXIT_OK


TASK_COMMANDS = ("bin-task", "refit-task", "collect", "negative-task", "checks-task")


def _task_command(arguments) -> int:
    """The T07 tasks' commands: RESULT ok (exit 0), failed (a program failed or a check did not pass, exit 1), rejected (a block or an input this
    scoring refuses, exit 2). Any other exception is a crash: its traceback, no result line (review M8)."""
    operation = arguments.operation
    if arguments.block not in TASK_BLOCKS:
        _result(operation, "rejected", f"block {arguments.block}: T07 tasks run on blocks 11 and 12 (block 1 for development only)")
        return EXIT_BAD_INPUT
    try:
        if operation == "bin-task":
            lines = bin_task(arguments.block, arguments.fixture_id, arguments.stratum, build=arguments.build, out=arguments.out, first=arguments.first,
                             count=arguments.count)
            word, text = "ok", f"bin {arguments.fixture_id} b{arguments.block} s{arguments.stratum} ({arguments.count} events)"
        elif operation == "refit-task":
            lines = refit_task(arguments.block, arguments.stratum, first=arguments.first, count=arguments.count, bin_dir=arguments.bin_dir, build=arguments.build,
                               out=arguments.out)
            word, text = "ok", f"refit b{arguments.block} s{arguments.stratum} {arguments.first}+{arguments.count}"
        elif operation == "collect":
            attempts = json.loads(Path(arguments.attempts).read_text(encoding="utf-8"))
            size = arguments.refit_range or layout.t07_refit_range()
            pieces = layout.split(arguments.count, size) if arguments.fixture_id == 7001 else []
            document = collect_task(arguments.block, arguments.fixture_id, arguments.stratum, attempts, pieces=pieces, count=arguments.count)
            Path(arguments.out).parent.mkdir(parents=True, exist_ok=True)
            Path(arguments.out).write_text(json.dumps(document, sort_keys=True, indent=1) + "\n", encoding="utf-8")
            refit = document.get("refit", {})
            lines = [f"COLLECT T07 {arguments.fixture_id} b{arguments.block} s{arguments.stratum}: {document['status']} {document['reason']}"
                     + (f"; refit {refit['status']} {refit['reason']}" if refit else "")]
            word, text = "ok", f"collection written ({document['status']})"
        elif operation == "negative-task":
            lines, checks = negative_task(arguments.block, build=arguments.build, folder=arguments.folder, out=arguments.out)
            failing = [c.name for c in checks if c.result != "pass"]
            word, text = ("ok" if not failing else "failed"), f"{len(checks) - len(failing)} of {len(checks)} negative checks fired" + (f"; not: {failing}" if failing else "")
        else:
            lines, checks = checks_task(arguments.block, build=arguments.build, out=arguments.out, workers=arguments.workers)
            failing = [c.name for c in checks if c.result != "pass"]
            word, text = ("ok" if not failing else "failed"), f"{len(checks) - len(failing)} of {len(checks)} deterministic and CAI checks pass ({DETERMINISTIC_CHECKS_SOURCE})"
    except TaskFailed as error:
        _result(operation, "failed", str(error))
        return EXIT_NEGATIVE
    except ChecksCrashed as error:   # E6 merge review I2: a check module that could not run is a crash, never a failed check
        _result(operation, "incomplete", str(error))
        return EXIT_INCOMPLETE
    except (ScoringError, core.CoreError, layout.LayoutError, finding_record.RecordFormatError) as error:
        _result(operation, "rejected", str(error))
        return EXIT_BAD_INPUT
    for line in lines:
        print(line, flush=True)
    _result(operation, word, text)
    return EXIT_OK if word == "ok" else EXIT_NEGATIVE


def build_parser() -> argparse.ArgumentParser:
    """Every command's options, in one place, so a test can read each command's namespace (fix round 1: job 7591993's clean s4 read an option
    its parser did not yet define)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="operation", required=True)
    one = commands.add_parser("score-bin", help="one bin's 57 or 38 records, its slice populations and its readings")
    for name, kind in (("--block", int), ("--fixture-id", int), ("--stratum", int), ("--events", int)):
        one.add_argument(name, type=kind, required=True)
    one.add_argument("--out", required=True)
    for name in ("--record", "--product", "--truth"):
        one.add_argument(name, default="")
    for name in ("--truth-seeded-record", "--refit-collection", "--rate-record", "--collection"):
        one.add_argument(name)
    pool = commands.add_parser("score-slices", help="one fixture's pooled angle slices from its 12 bins' slice files")
    for name, kind in (("--block", int), ("--fixture-id", int), ("--events", int)):
        pool.add_argument(name, type=kind, required=True)
    pool.add_argument("--bins", required=True)
    pool.add_argument("--out", required=True)
    pool.add_argument("--parameters", default="")
    negative = commands.add_parser("negative-cases", help="E5: v4 11's checks on the finder's record of the kept case file")
    negative.add_argument("--block", type=int, required=True)
    for name in ("--folder", "--record", "--seeds", "--out"):
        negative.add_argument(name, required=True)
    summary = commands.add_parser("summary", help="section 10 on an evaluation block's records (never block 1)")
    summary.add_argument("--block", type=int, required=True)
    summary.add_argument("--scores", required=True)
    summary.add_argument("--checks", default="")
    commands.add_parser("count", help="section 5.3's T07 count and its composition")
    task = commands.add_parser("bin-task", help="one T07 bin: generation, finding with the vertex step, the truth-seeded run of a noise bin")
    for name in ("--block", "--fixture-id", "--stratum"):
        task.add_argument(name, type=int, required=True)
    task.add_argument("--first", type=int, default=0)
    task.add_argument("--count", type=int, default=layout.EVENTS_PER_BIN)
    task.add_argument("--build", required=True)
    task.add_argument("--out", required=True)
    task = commands.add_parser("refit-task", help="one refit range of a clean bin")
    for name in ("--block", "--stratum", "--first", "--count"):
        task.add_argument(name, type=int, required=True)
    for name in ("--bin-dir", "--build", "--out"):
        task.add_argument(name, required=True)
    task = commands.add_parser("collect", help="one T07 bin's collection, for score-bin --collection")
    for name in ("--block", "--fixture-id", "--stratum"):
        task.add_argument(name, type=int, required=True)
    task.add_argument("--count", type=int, default=layout.EVENTS_PER_BIN)
    task.add_argument("--refit-range", type=int, default=0, help="events per refit range (0: the evaluation plan's)")
    task.add_argument("--attempts", required=True)
    task.add_argument("--out", required=True)
    task = commands.add_parser("negative-task", help="E5: the finder on the kept case file, then v4 11's negative checks")
    task.add_argument("--block", type=int, required=True)
    for name in ("--build", "--folder", "--out"):
        task.add_argument(name, required=True)
    task = commands.add_parser("checks-task", help="I3: the deterministic and CAI checks, rerun at evaluation")
    task.add_argument("--block", type=int, required=True)
    task.add_argument("--workers", type=int, default=1)
    for name in ("--build", "--out"):
        task.add_argument(name, required=True)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as stop:
        if stop.code:
            _result("arguments", "rejected", "the arguments do not parse")
            return EXIT_BAD_INPUT
        return EXIT_OK
    if arguments.operation == "count":
        composition = required_composition()
        print("COUNT T07 " + " ".join(f"{name.replace(' ', '_')} {value}" for name, value in composition.items() if name != "total") + f" total {composition['total']}")
        print(f"COUNT per bin: clean {len(bin_gates(7001))}, noise {len(bin_gates(7002))}; per fixture's slices {len(slice_gates())}")
        _result("count", "ok", f"total {composition['total']} (section 5.3)")
        return EXIT_OK
    if arguments.operation == "summary" and arguments.block not in EVALUATION_BLOCKS:
        _result("summary", "rejected", f"block {arguments.block}: a verdict is of blocks 11 and 12 only")
        return EXIT_BAD_INPUT
    if arguments.operation in TASK_COMMANDS:
        return _task_command(arguments)
    command_of = {"score-bin": _score_bin_command, "score-slices": _score_slices_command, "negative-cases": _negative_cases_command, "summary": _summary_command}
    return command_of[arguments.operation](arguments)


if __name__ == "__main__":
    sys.exit(main())
