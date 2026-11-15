"""adapters/acts-tracking, the noise, finding and ambiguity steps of T07 (t07-t09-task-sheets.md, Steps): recipe reco.track.acts-ckf-planar/1.

Sections cited are of t04-values-v4.md. Everything printed here is a development reading of block 1, tuning, not a gate result: pass or fail waits
for K09 (sheet, Acceptance) and tuning runs feed nothing (section 2.2). Truth enters here, on the scoring side, and never reaches the finder: its only
input is a data file. Efficiency, fake and duplicate are section 7's, word for word, in scored_event. Correction, stage 6: the section 7 truth-seeded run is
built, a program of its own on the scoring side (acts_truth_seeded_run), and gate "Efficiency, noise (a)" is read against it in tests/adapters/test_acts_truth_seeded.py;
FinderStaysTruthFree below fails if this finder gains a truth input.

Predictions, fixed here before the first run of this recipe. Closed form, unless named:

| Fixture | Efficiency | Fake rate | Duplicate rate |
| --- | --- | --- | --- |
| Clean | R = 1 (section 4.1). Loss at most the share of tracks with another track's hit within 0.15 mm on some plane: 0.0006, 0.0016, 0.0046 at o1, o2, o3 | 0 expected (section 4.1) | 0 expected |
| Noise | At least R_floor(o) = 0.99937, 0.99812, 0.99374; expected above 0.999 | Chance candidates about 2e-5 per track at o3, 1e-7 and less at o1, o2 | 0 expected |

- Overlap shares: an independent numpy toy of the fan of tracks from one vertex, 4,000 events per point, largest over momentum. Section 4.1's "at most 0.0024" takes tracks
  spread over 90 x 90 mm; they leave the vertex as a fan, so near plane 1 they sit closer and the toy reads 0.0038 to 0.0046 at o3. Those tracks are not lost, since each keeps
  its own hits: expected loss is far below this, which is a limit.
- Noise efficiency: a track with 6 of 8 hits has a whole triple (SeedPlanes test); a true hit fails the chi2 cut 3.4e-4 of the time, and 3 such in a track are out of reach.
- Chance candidates: expected_chance_seeds gives 336 triples per event at o3, 9 at o2, 0.4 at o1. Each must collect 3 more noise hits. Windows of a wide seed, plane by plane:
  about 0.09, 0.01, 0.002 noise hits at o3, so 2e-6 per seed, 6e-4 per event, 2e-5 per track. Section 8.3's 1e-7 is for a 6-hit chance alignment; this is larger because a seed's
  first windows are wider than a converged track's. An estimate, good to a factor of a few.
- Duplicates: two tracks of one particle hold more than 50 % of their hits from it, so at least 4 each of at most 8, and ambiguity resolution keeps two only if they share at
  most 1 hit: at least 6 distinct true hits and 3 or more noise hits on the pair: the chance-candidate rate at most. Correction, stage 5 review m3: ambiguity_most_shared_hits = 1
  means they share none (track_finding.hpp), so all 8 true hits and at least 4 noise hits. The prediction of 0 stands, on a stronger argument. Correction, stage 5e: the value is
  now 2, a development value for Freeze B (decisions.md, "Recipe choice after stage 5d"), which means each selected track holds at most one hit another selected track holds,
  so the first argument of this item is again the one that applies: at least 3 hits on the pair are not the particle's. Its reason is not the duplicates but section 7's match:
  a track that took one foreign hit in place of a hole still matches its particle. The prediction of 0 stands; job 7496491 read 0 at this value.

Correction after job 7493849, in D1 stage 5 report, Fix round 1. The table above stands as written, and no limit moved. "Expected above 0.999" and the reading of the noise row assumed
windows near section 4.1's 0.15 mm, which the first recipe's diagonal seed prior did not have; R_floor assumes the same, so R_floor is right and the recipe was wrong. With the correlated
prior the estimate is efficiency at least about 0.9998, 0.9990, 0.9986 at o1, o2, o3, a linear estimate of foreign hits in the window on a plane where the track has none.

Correction after job 7494285, Fix round 2. LOST_TO_THE_CHI2_CUT's "0.34 expected" treated 168 cases as independent. The 7 pairs for which 6-7-8 is the only whole triple share one seed
per track, so a seed that fails counts up to 7 at once. The limit stands: with a start on the helix a seed fails at about 1e-4, so 0.34 stays the expected order.

Correction after job 7494405, stage 5 review m4. The table's "0 expected" for clean fakes stands as written and missed: 2 in clean stratum 2. It reckoned with no track of two particles'
hits, and a clean fake is one: an exact tie or three owners. Cause open until tests/adapters/test_acts_finding_diagnosis.py reads it. The same job made o3 noise worse than job 7494285 on
identical events, 640 to 781 lost, which the text of Fix round 2 did not predict. Every reading stays inside its limit, and no limit moved.

Stage 6 (D1 stage 6 brief): only tidy changes reach the finder. The no-phi build is gone, the steps after the start are one function shared with the truth-seeded run, and an
optional output prints ACTS's own ambiguity removal sequence for named events. The record is predicted byte for byte as job 7502411's, and the configuration hash unchanged.

Stage 5e, the user's two changes after job 7496491 (decisions.md, "Recipe choice after stage 5d"): the seed start takes the slope along v from the first and last hit, its covariance
holds the phi term it lacked, and ambiguity_most_shared_hits is 2. The table above and the tolerances below stand as written, and no limit moved. Their predictions are in the D1 stage 5e
report, fixed before its job.

Tolerances, fixed before the first run, and they do not move after results (sheet, Stop). A reading outside one is a disagreement with a prediction, for finding the cause:

- PREDICTION_Z = 4 standard errors on every count, so about 72 readings stop this run at most 0.5 % of the time if the prediction is right.
- RARE_RATE_LIMIT = 1e-4, for fake and duplicate on both fixtures: five times the 2e-5 above, for an estimate good to a factor of a few.
- FIT_AGREEMENT_SIGMA, as for the refit: test_acts_refit_field.py.

Development sample: all 12 strata of fixtures 7001 and 7002, block 1, EVENTS_PER_BIN = 3,000 events each, section 3.2's size for clean runs: 72,000 events, 864,000 tracks at most. No evaluation
block is read. Negative cases derive from block 1 files (section 11). The built tests need the build job and skip without it; that job counts a skip as a failure. Each judge is driven with
honest input and one defect. Run from the plugin root: python -m unittest tests.adapters.test_acts_finding -v
"""
from __future__ import annotations

import concurrent.futures
import itertools
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "acts-tracking"
NATIVE = ADAPTER / "assets" / "native"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER / "assets" / "fixture_tools"))

import acts_finding_record as finding_record  # noqa: E402
import acts_native_product as native_product  # noqa: E402
import t07_fixture_files as fixture_files  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402
import t07_negative_cases as negative_cases  # noqa: E402
from tests.adapters import test_acts_refit_field as refit_tests  # noqa: E402

BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
WORKERS = int(os.environ.get("HEP_ACTS_TRACKING_WORKERS", "1"))
FINDER = Path(BUILD_DIR) / "acts_tracking_finder"
GENERATOR = Path(BUILD_DIR) / "t07_fixture_generator"
BUILT = bool(BUILD_DIR) and FINDER.is_file() and GENERATOR.is_file()
# D4 E5 (freeze-b-proposal.md, section 2.5): the negative-case input file, written once from block 1 by t07_negative_cases.py, kept and hashed. The kept
# copy lives in tests/adapters/data/t07-negative-cases/; the job that writes it names its own folder by HEP_ACTS_TRACKING_NEGATIVE_CASES.
NEGATIVE_CASES_FOLDER = Path(os.environ.get("HEP_ACTS_TRACKING_NEGATIVE_CASES", "") or ROOT / "tests" / "adapters" / "data" / "t07-negative-cases")
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built finder: this test needs the T07 build job, which runs it"

# Section 4.1 and 7.
PLANES = 8
LEAST_HITS = 6
PLANE_AREA_MM2 = 300.0 * 300.0
TRACKS_OF_LEVEL = (6, 12, 36)
NOISE_OF_LEVEL = (100, 300, 1000)
R_FLOOR_OF_LEVEL = (0.99937, 0.99812, 0.99374)
HIT_SIGMA_MM = 0.020
OVERLAP_SHARE_OF_LEVEL = (0.0006, 0.0016, 0.0046)  # the toy of the module text
FIXTURE_IDS = {"clean": 7001, "noise": 7002}

PREDICTION_Z = 4.0
RARE_RATE_LIMIT = 1e-4
EVENTS_PER_BIN = 3000
PRODUCT_EVENTS = 50
TUNING_BLOCK = 1
NEGATIVE_STRATUM = negative_cases.SOURCE_STRATUM  # the lowest momentum bin at o1: the widest curvature window
SHIFT_WRONG_HIT_MM = negative_cases.SHIFT_WRONG_HIT_MM  # 50 hit sigmas; D4 E5: the constants of the cases live with their builder
EXPLOSION_EXTRA_HITS = negative_cases.EXPLOSION_EXTRA_HITS
LOST_TO_THE_CHI2_CUT = 3  # Poisson 0.34: above this 5e-4 of the time
LOST_ALONE_LIMIT = 12  # of 168: about 2 expected with the correlated prior, about 33 with the diagonal one, at o1 (D1 stage 5 report, Fix round 1)
ALL_HITS_KEPT_SHARE = 0.95  # 8 x 3.4e-4 of tracks lose a hit to the chi2 cut: 0.27 %


# ---- The judges. Each takes numbers and names what is wrong, so each is tested without a build.

def header_constant(text: str, name: str) -> float:
    return float(re.search(rf"{name} = ([0-9.e+-]+);", text).group(1))


def seed_triples_of(text: str) -> list:
    body = re.search(r"seed_plane_triples\{\{(.*)\}\};", text).group(1)
    return [tuple(int(plane) for plane in found) for found in re.findall(r"\{(\d), (\d), (\d)\}", body)]


def uncovered_plane_pairs(triples) -> list:
    """Section 7: a reconstructable track may lose any two planes. Those losses that leave no whole seed triple."""
    return [pair for pair in itertools.combinations(range(1, PLANES + 1), 2) if not any(set(pair).isdisjoint(triple) for triple in triples)]


def expected_chance_seeds(hits_per_plane: float, triples, slope_u: float, slope_v: float, window_sigma: float, turning_per_mm: float) -> float:
    """Closed form: uniform hits, the windows of track_finding.cpp. Pairs inside the slope window, times hits inside the middle window, per triple."""
    density = hits_per_plane / PLANE_AREA_MM2
    slope_norm = math.sqrt(1.0 + slope_u ** 2 + slope_v ** 2)
    curvature_u = turning_per_mm * slope_norm * (1.0 + slope_u ** 2)
    curvature_v = turning_per_mm * slope_norm * slope_u * slope_v
    total = 0.0
    for first, middle, last in triples:
        to_middle, from_middle = 50.0 * (middle - first), 50.0 * (last - middle)
        lever = to_middle + from_middle
        share = to_middle / lever
        noise_mm = window_sigma * HIT_SIGMA_MM * math.sqrt(1.0 + share ** 2 + (1.0 - share) ** 2)
        pair_area = 2.0 * slope_u * lever * 2.0 * slope_v * lever
        middle_area = 2.0 * (noise_mm + 0.5 * curvature_u * to_middle * from_middle) * 2.0 * (noise_mm + 0.5 * curvature_v * to_middle * from_middle)
        total += hits_per_plane * pair_area * density * middle_area * density
    return total


def seed_covariances(triple, inflation: float, start_x_mm: float = -50.0) -> tuple:
    """Job 7494285's prior, which the finder no longer holds, as (u, u', u'') and (v, v') at the start: least squares of a parabola by matrix inverse; the chord through the first and last
    hit. A reference only: the shipped covariance, f^2 J J^T of seed_start_of, is read by seed_start_probe.cpp, by two roads, beside these numbers."""
    positions = 50.0 * (numpy.array(triple, float) - 1.0)
    basis = numpy.stack([numpy.ones(3), positions - start_x_mm, 0.5 * (positions - start_x_mm) ** 2], 1)
    along_u = (inflation * HIT_SIGMA_MM) ** 2 * numpy.linalg.inv(basis.T @ basis)
    ends = numpy.stack([numpy.ones(2), positions[[0, 2]] - start_x_mm], 1)
    along_v = (inflation * HIT_SIGMA_MM) ** 2 * numpy.linalg.inv(ends.T @ ends)
    return along_u, along_v


def position_sigmas_at(covariances, plane_x_mm: float, start_x_mm: float = -50.0) -> tuple:
    """Sigma of u and v carried from the start to a plane, with no hit in between."""
    step = plane_x_mm - start_x_mm
    along_u, along_v = numpy.array([1.0, step, 0.5 * step ** 2]), numpy.array([1.0, step])
    return math.sqrt(along_u @ covariances[0] @ along_u), math.sqrt(along_v @ covariances[1] @ along_v)


# ---- The seed start of track_finding.cpp in closed form (D1 stage 5e), numpy only, no ACTS: a replica of seed_start_of and of seed_start_probe's two roads, so that
# the slope rule and the phi term are judged before a build. It reproduces job 7496491's probe: every hit road to 1e-4 and every covariance road inside the spread the
# probe's one-sided eigenvector steps allow (D1 stage 5e report). Sign conventions are its own: phi falls at w per unit path, w the signed curvature times the transverse
# share, so a charge here is the probe's opposite charge, a mirror image; nothing judged depends on that.

SEED_START_X_MM = -50.0
SEED_DERIVATIVE_STEP = 0.05
SEED_SIGMA_AGREEMENT = 0.02  # seed_start_probe.cpp's seed_sigma_agreement


def helix_crossings(position_mm, direction, turn_per_mm: float) -> numpy.ndarray:
    """(u, v) at the eight planes of a helix with phi falling at turn_per_mm per unit path, from any start."""
    direction = numpy.asarray(direction, float) / numpy.linalg.norm(direction)
    phi, transverse = math.atan2(direction[1], direction[0]), math.hypot(direction[0], direction[1])
    rows = []
    for plane in range(PLANES):
        sine = math.sin(phi) - turn_per_mm * (50.0 * plane - position_mm[0]) / transverse
        end_phi = math.asin(sine)
        path_mm = (phi - end_phi) / turn_per_mm
        rows.append((position_mm[1] + transverse / turn_per_mm * (math.cos(end_phi) - math.cos(phi)), position_mm[2] + path_mm * direction[2]))
    return numpy.array(rows)


def replica_helix_at_start(points, slope_rule: str) -> tuple:
    """The circle through three transverse points, its tangent at the first, the slope along v by slope_rule ("chord": first to last over their straight transverse
    distance, the recipe; "last-two": ACTS's), carried to x = SEED_START_X_MM. Returns position, unit direction, turn per mm."""
    first, middle, last = (numpy.asarray(point, float) for point in points)
    a, b, c = first[:2], middle[:2], last[:2]
    twice_area = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    centre = numpy.array([(a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1]), (a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])]) / twice_area
    radius = float(numpy.linalg.norm(a - centre))
    tangent = numpy.array([-(a - centre)[1], (a - centre)[0]]) / radius
    tangent = tangent if tangent @ (b - a) > 0 else -tangent
    counterclockwise = (b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0] > 0
    lower, upper = (first, last) if slope_rule == "chord" else (middle, last)
    cotangent = (upper[2] - lower[2]) / float(numpy.linalg.norm(upper[:2] - lower[:2]))
    transverse = 1.0 / math.sqrt(1.0 + cotangent ** 2)
    turn_per_mm = (-1.0 if counterclockwise else 1.0) * transverse / radius
    phi_at_seed = math.atan2(tangent[1], tangent[0])
    phi_at_start = math.asin(math.sin(phi_at_seed) - turn_per_mm * (SEED_START_X_MM - first[0]) / transverse)
    path_mm = (phi_at_seed - phi_at_start) / turn_per_mm
    position = numpy.array([SEED_START_X_MM, first[1] + transverse / turn_per_mm * (math.cos(phi_at_start) - math.cos(phi_at_seed)), first[2] + path_mm * cotangent * transverse])
    return position, numpy.array([transverse * math.cos(phi_at_start), transverse * math.sin(phi_at_start), cotangent * transverse]), turn_per_mm


def curvilinear_axes_of(direction) -> tuple:
    axis_u = numpy.array([-direction[1], direction[0], 0.0]) / math.hypot(direction[0], direction[1])
    return axis_u, numpy.cross(direction, axis_u)


def replica_seed_start(points, slope_rule: str, phi_term_sign: float, inflation: float) -> tuple:
    """seed_start_of: the centre and f^2 J J^T, J the central difference of the bound start in the hit coordinates. phi_term_sign 1 adds w (T . m), the recipe; 0 and -1 are the
    defects. The fifth parameter is the turn per mm, q/p times k B: a constant factor, which changes no road."""
    position, direction, turn_per_mm = replica_helix_at_start(points, slope_rule)
    axis_u, axis_v = curvilinear_axes_of(direction)

    def bound_of(start) -> numpy.ndarray:
        moved = start[0] - position
        phi = math.atan2(start[1][1], start[1][0]) + phi_term_sign * turn_per_mm * (direction @ moved)
        return numpy.array([axis_u @ moved, axis_v @ moved, phi, math.acos(start[1][2] / numpy.linalg.norm(start[1])), start[2]])

    jacobian = numpy.zeros((5, 6))
    step_mm = SEED_DERIVATIVE_STEP * HIT_SIGMA_MM
    for hit in range(3):
        for coordinate in range(2):
            above, below = [numpy.array(point, float) for point in points], [numpy.array(point, float) for point in points]
            above[hit][coordinate + 1] += step_mm
            below[hit][coordinate + 1] -= step_mm
            jacobian[:, 2 * hit + coordinate] = (bound_of(replica_helix_at_start(above, slope_rule)) - bound_of(replica_helix_at_start(below, slope_rule))) * (HIT_SIGMA_MM / (2.0 * step_mm))
    return position, direction, turn_per_mm, inflation ** 2 * jacobian @ jacobian.T


def replica_roads(points, slope_rule: str, phi_term_sign: float, inflation: float) -> dict:
    """seed_start_probe's two roads, sigma of u and v at each plane: each eigenvector of the covariance carried along, and each hit coordinate moved by one inflated sigma."""
    position, direction, turn_per_mm, covariance = replica_seed_start(points, slope_rule, phi_term_sign, inflation)
    centre = helix_crossings(position, direction, turn_per_mm)
    axis_u, axis_v = curvilinear_axes_of(direction)
    phi, theta = math.atan2(direction[1], direction[0]), math.acos(direction[2])
    eigenvalues, eigenvectors = numpy.linalg.eigh(covariance)
    of_covariance = numpy.zeros((PLANES, 2))
    for eigenvalue, axis in zip(eigenvalues, eigenvectors.T):
        if eigenvalue > 0.0:
            step = math.sqrt(eigenvalue) * axis
            moved_direction = numpy.array([math.cos(phi + step[2]) * math.sin(theta + step[3]), math.sin(phi + step[2]) * math.sin(theta + step[3]), math.cos(theta + step[3])])
            of_covariance += (helix_crossings(position + step[0] * axis_u + step[1] * axis_v, moved_direction, turn_per_mm + step[4]) - centre) ** 2
    of_hits = numpy.zeros((PLANES, 2))
    for hit in range(3):
        for coordinate in (1, 2):
            moved_points = [numpy.array(point, float) for point in points]
            moved_points[hit][coordinate] += inflation * HIT_SIGMA_MM
            moved_position, moved_direction, moved_turn = replica_helix_at_start(moved_points, slope_rule)
            of_hits += (helix_crossings(moved_position, moved_direction, moved_turn) - centre) ** 2
    return {"covariance": numpy.sqrt(of_covariance), "hits": numpy.sqrt(of_hits), "centre": centre}


CHORD_SLOPE_LINE = "const double chord_slope = (points[2].z() - points[0].z()) / std::hypot(points[2].x() - points[0].x(), points[2].y() - points[0].y());"
PHI_TERM_LINE = "phi += centre->q_over_p * field_along_v_tesla * Acts::UnitConstants::T * centre->direction.dot(moved_mm);"
DIAGNOSTIC_DEFINITIONS = set()  # none since stage 6: stage 5e's one temporary build, acts_finder_no_phi_term, came out as stated (D1 stage 6 brief, Tidy)


def recipe_choice_defects(header_text: str, source_text: str) -> list:
    """The user's two changes after job 7496491 (decisions.md, "Recipe choice after stage 5d"), as the source must hold them for the recipe's build: the chord slope outside
    any diagnostic block, the phi term with its sign and under no preprocessor block (since stage 6 no build leaves it out), and ambiguity_most_shared_hits 2. A guard of the source text,
    exact lines, not of behaviour: seed_start_probe in the build job judges the behaviour (RecipeChoiceInTheSource)."""
    defects = []
    if header_constant(header_text, "ambiguity_most_shared_hits") != 2:
        defects.append(f"ambiguity_most_shared_hits is {header_constant(header_text, 'ambiguity_most_shared_hits'):g}, not 2")
    used = set(re.findall(r"#\s*if(?:n?def\s+|\s+defined\s*\(\s*)(\w+)", source_text))
    if used != DIAGNOSTIC_DEFINITIONS:
        defects.append(f"diagnostic definitions {sorted(used)}, not {sorted(DIAGNOSTIC_DEFINITIONS)}")
    lines = [line.strip() for line in source_text.splitlines()]
    if CHORD_SLOPE_LINE not in lines or "tangent = Acts::Vector3(tangent.x() / transverse_before, tangent.y() / transverse_before, chord_slope).normalized();" not in lines:
        defects.append("the slope along v is not the chord's")
    if PHI_TERM_LINE not in lines:
        defects.append("the phi term is absent or its sign is not +w (T . m)")
    # Stage 6 review m6: the line above the phi term, any conditional inside seed_start_of's body, and any #if 0 in the file. One defect for all three, since each is the same
    # fault, a build that may leave the term out.
    body = source_text[source_text.find("std::optional<SeedStart> seed_start_of("):]
    body = body[:body.find("\n}\n")] if "std::optional<SeedStart> seed_start_of(" in source_text else ""
    conditional_in_body = any(line.strip().startswith("#if") for line in body.splitlines())
    if_zero = any(re.match(r"#\s*if\s+0\b", line) for line in lines)
    above = PHI_TERM_LINE in lines and lines[lines.index(PHI_TERM_LINE) - 1].startswith("#")
    if PHI_TERM_LINE in lines and (above or conditional_in_body or if_zero):
        defects.append("a preprocessor conditional above the phi term, inside seed_start_of, or #if 0 in the file, so a build may leave code out")
    return defects


def scored_event(tracks, particles) -> dict:
    """Section 7. tracks: reconstructed tracks in track-index order, {"hit_keys", "chi2", "ndf"}; particles: {"hit_keys": hits it left}, each hit key of one particle at most.

    Track match: more than 50 % of the track's measurements, noise hits included in the count, come from one particle. Primary: highest matched fraction, then most hits, then lowest
    chi2/ndf, then lowest track index. Efficiency: reconstructable particles with a primary, over reconstructable particles. Fake: matching no particle, over all reconstructed
    tracks. Duplicate: matched tracks that are not primary, over all matched tracks.
    """
    owner = {key: index for index, particle in enumerate(particles) for key in particle["hit_keys"]}
    matched = {}
    fakes = 0
    for track_index, track in enumerate(tracks):
        count_by_particle = Counter(owner[key] for key in track["hit_keys"] if key in owner)
        best = next((particle for particle, count in count_by_particle.items() if 2 * count > len(track["hit_keys"])), None)
        if best is None:
            fakes += 1
        else:
            fraction = count_by_particle[best] / len(track["hit_keys"])
            matched.setdefault(best, []).append((-fraction, -len(track["hit_keys"]), track["chi2"] / track["ndf"], track_index))
    reconstructable = [index for index, particle in enumerate(particles) if len(particle["hit_keys"]) >= LEAST_HITS]
    all_matched = sum(len(candidates) for candidates in matched.values())
    return {"reconstructable": len(reconstructable), "with_primary": sum(index in matched for index in reconstructable), "lost": [index for index in reconstructable if index not in matched],
            "reconstructed": len(tracks), "fakes": fakes, "matched": all_matched, "duplicates": all_matched - len(matched),
            "primaries": {particle: min(candidates)[3] for particle, candidates in matched.items()}}


def hits_on_two_selected(event: dict) -> int:
    """Hits held by more than one selected track of an event: what ambiguity_most_shared_hits 2 allows, at most one per track (track_finding.hpp)."""
    held = Counter(key for item in event["found"] if item["outcome"] == "selected" for key in item["hit_keys"])
    return sum(count > 1 for count in held.values())


def loss_category(particle, event: dict) -> str:
    """Why a reconstructable particle has no primary, in t04-prereg.md's failure classes. Scoring side: it needs the particle."""
    owned = set(particle["hit_keys"])
    for item in event["found"]:
        if item["outcome"] != "selected" and 2 * len(owned & set(item["hit_keys"])) > len(item["hit_keys"]):
            return item["failure_category"]
    if event["seeds_truncated"] or event["seed_budget_reached"] or event["ambiguity_budget_reached"]:
        return "search-truncated"
    return "seed-or-finding"


def finding_product_defects(document: dict) -> list:
    """Sheet, Acceptance: a refit or a truth-seeded fit is never reported as finding. Only hits came in, and the product says so."""
    header = document["header"]
    expected = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": finding_record.FINDING_EVIDENCE_CLASS, "hit_sets_sha256": "none", "qop_status": "measured"}
    defects = [f"{name} is {header[name]}" for name, value in expected.items() if header[name] != value]
    return defects + ([] if native_product.fit_summary(document)["reported_as_finding"] else ["not reported as finding"])


def states_apart_defects(document: dict) -> list:
    """Sheet, Output; BP03: at each measured surface a predicted, a filtered and a smoothed record, and the update moved the state."""
    records = {(item["track_key"], item["state_index"], item["state_type"]): item["parameters"] for item in document["parameters"]}
    defects = []
    for state in document["states"]:
        if state["kind"] != "measurement":
            continue
        kept = [records.get((state["track_key"], state["index"], name)) for name in native_product.STATE_TYPES]
        if None in kept:
            defects.append(f"{state['track_key']} state {state['index']} lacks a state type")
        elif kept[0] == kept[1]:
            defects.append(f"{state['track_key']} state {state['index']}: filtered is predicted")
    return defects


def record_matches_product(events, document: dict, product_events: int) -> list:
    """The record's selected candidates of the first events are the product's tracks, with the same hits."""
    selected = {item["key"]: item for event in events[:product_events] for item in event["found"] if item["outcome"] == "selected"}
    tracks = {track["key"]: track for track in document["tracks"]}
    if set(selected) != set(tracks):
        return [f"the record selects {len(selected)} tracks and the product holds {len(tracks)}"]
    hits = {}
    for state in document["states"]:
        if state["hit_key"] is not None:
            hits.setdefault(state["track_key"], []).append(state["hit_key"])
    return [f"{key} differs in its hits" for key, item in selected.items() if hits.get(key) != item["hit_keys"]]


def prediction_defects(reading: dict, fixture: str, level: int) -> list:
    """The module text's table. A defect is a disagreement with a prediction, not a gate result: find the cause and leave the limit."""
    defects = []
    count = reading["reconstructable"]
    efficiency = reading["with_primary"] / count
    expected = 1.0 - OVERLAP_SHARE_OF_LEVEL[level] if fixture == "clean" else R_FLOOR_OF_LEVEL[level]
    if efficiency + PREDICTION_Z * math.sqrt(expected * (1.0 - expected) / count) < expected:
        defects.append(f"efficiency {efficiency:.5f}, predicted at least {expected}")
    for name, denominator in (("fakes", reading["reconstructed"]), ("duplicates", reading["matched"])):
        allowed = RARE_RATE_LIMIT * denominator + PREDICTION_Z * math.sqrt(RARE_RATE_LIMIT * denominator)
        if reading[name] > allowed:
            defects.append(f"{name} {reading[name]} of {denominator}, predicted at most {allowed:.1f}")
    return defects


# ---- Tests that need no build.

class SeedsCoverEveryTwoLostPlanes(unittest.TestCase):
    def setUp(self):
        self.header = (NATIVE / "track_finding.hpp").read_text(encoding="utf-8")

    def test_any_two_lost_planes_leave_a_whole_triple(self):
        self.assertEqual(uncovered_plane_pairs(seed_triples_of(self.header)), [])

    def test_a_triple_less_leaves_a_pair_uncovered(self):
        triples = seed_triples_of(self.header)
        for left_out in triples:
            with self.subTest(left_out=left_out):
                self.assertTrue(uncovered_plane_pairs([triple for triple in triples if triple != left_out]))

    def test_seeding_only_planes_one_to_three_is_the_recipe_section_4_1_fails(self):
        self.assertEqual(len(uncovered_plane_pairs([(1, 2, 3)])), 28 - 10)
        self.assertAlmostEqual(1.0 - 0.98 ** 3, 0.059, delta=1e-3)


class ConfigurationFromTheFixtureAlone(unittest.TestCase):
    """The fixed values are arithmetic on sections 4.1 and 7 (section 2.2's forbidden list), so that arithmetic is held here. seed_prior_inflation is tuned on block 1, as its comment says."""

    def setUp(self):
        self.header = (NATIVE / "track_finding.hpp").read_text(encoding="utf-8")
        self.value = lambda name: header_constant(self.header, name)

    def test_the_slope_windows_hold_section_4_1(self):
        turning = refit_tests.GEV_PER_TESLA_MM / 1.5
        self.assertAlmostEqual(self.value("seed_lowest_momentum_gev"), 1.5)
        bent = 0.15 + turning * 450.0
        self.assertGreater(self.value("seed_largest_slope_u"), bent)
        self.assertGreater(self.value("seed_largest_slope_v"), 0.15 * math.sqrt(1.0 + bent ** 2))

    def test_the_holes_follow_from_section_7(self):
        self.assertEqual(self.value("finding_least_measurements"), LEAST_HITS)
        self.assertEqual(self.value("finding_most_holes"), PLANES - LEAST_HITS)

    def test_the_chi2_cut_is_its_stated_tail_and_stays_inside_the_circle(self):
        cut = self.value("finding_chi2_cut")
        self.assertAlmostEqual(math.exp(-cut / 2.0), 3.4e-4, delta=1e-5)
        self.assertLess(math.sqrt(cut * 2.0 * HIT_SIGMA_MM ** 2), 0.15)

    def test_the_seed_budget_clears_the_expected_chance_triples(self):
        expected = self.expected(NOISE_OF_LEVEL[2] + TRACKS_OF_LEVEL[2])
        self.assertAlmostEqual(expected, 336.0, delta=15.0)
        self.assertGreater(self.value("finding_most_seeds_per_event"), 25.0 * expected)
        self.assertAlmostEqual(self.expected(NOISE_OF_LEVEL[1] + TRACKS_OF_LEVEL[1]), 9.0, delta=1.0)
        self.assertLess(self.expected(NOISE_OF_LEVEL[0] + TRACKS_OF_LEVEL[0]), 0.5)

    def expected(self, hits_per_plane) -> float:
        return expected_chance_seeds(hits_per_plane, seed_triples_of(self.header), self.value("seed_largest_slope_u"), self.value("seed_largest_slope_v"), self.value("seed_window_sigma"),
                                     refit_tests.GEV_PER_TESLA_MM / 1.5)

    def test_the_prior_of_a_late_seed_is_narrow_where_the_hits_put_it(self):
        """Job 7493849's cause. Carried to plane 1, a 3-4-5 seed has Lagrange weights 6, -8, 3, so 0.02 sqrt(109) = 0.209 mm, by matrix inverse here; along v, chord weights 2, -1, so
        0.02 sqrt(5). The diagonal form added the 0.76 mm of the start to both. Along v this is the shipped start again since stage 5e, which takes the chord slope (track_finding.hpp);
        from job 7494405 to job 7496491 it took the last two hits' slope, weights 1, 2, -2, 0.02 sqrt(9), and the 0.090 mm reading of job 7496491 was that. SeedStartClosedForm holds
        the shipped function itself, and seed_start_probe reads it."""
        inflation = self.value("seed_prior_inflation")
        sigma_u, sigma_v = position_sigmas_at(seed_covariances((3, 4, 5), 1.0), 0.0)
        self.assertAlmostEqual(sigma_u, HIT_SIGMA_MM * math.sqrt(109.0), delta=1e-6)
        self.assertAlmostEqual(sigma_v, HIT_SIGMA_MM * math.sqrt(5.0), delta=1e-6)
        area = math.pi * self.value("finding_chi2_cut") * inflation ** 2 * sigma_u * sigma_v
        self.assertLess(area, 1.5)  # mm^2: under 0.08 hits at o3's 0.05 per mm^2

    def test_a_correlation_with_the_wrong_sign_would_widen_that_window(self):
        along_u, along_v = seed_covariances((3, 4, 5), 1.0)
        flipped = along_u.copy()
        flipped[0, 1] = flipped[1, 0] = -flipped[0, 1]
        self.assertGreater(position_sigmas_at((flipped, along_v), 0.0)[0], 2.0 * position_sigmas_at((along_u, along_v), 0.0)[0])  # 0.58 mm against 0.21 mm

    def test_a_seed_starts_on_the_helix_not_on_the_parabola(self):
        """Fix round 2. seed_start_probe.cpp reads it through the propagator; this holds the route. A return to KalmanRefit::start_of would put the centre 0.5 mm off a 6-7-8 seed's hits."""
        source = (NATIVE / "track_finding.cpp").read_text(encoding="utf-8")
        self.assertNotIn("start_of(seed_hits", source)
        self.assertIn("seed_start_of({global_of(", source)

    def test_no_term_of_a_forbidden_source_in_the_configuration(self):
        """Section 2.2: no scale, offset or inflation derived from pulls or T08 targets. A review rule on what the source says of each value."""
        text = (NATIVE / "track_finding.cpp").read_text(encoding="utf-8")
        for word in ("sigma_68", "trimmed", "tail_of_pulls", "pull_scale", "target_"):
            self.assertNotIn(word, self.header + text)


class RecipeChoiceInTheSource(unittest.TestCase):
    """D1 stage 5e brief: a test fails on each defect alone: the phi term's sign flipped or the term absent, the slope back to the last two, shared hits back to 1. These guard the
    source text only (stage 5e review m3): a reformat of the same code fails them, and a sign defect written elsewhere passes them. The behaviour is judged in the build job: the
    phi term by seed_start_probe's 2 % agreement of its two roads (step probe-seed-start), the slope by that probe's chord judge along v, shared hits by the record's configuration
    (DevelopmentRun and tests.adapters.test_acts_finding_diagnosis, test_the_configuration_moved_by_the_changed_keys_only), and all three together by the paired comparison."""

    def setUp(self):
        self.header = (NATIVE / "track_finding.hpp").read_text(encoding="utf-8")
        self.source = (NATIVE / "track_finding.cpp").read_text(encoding="utf-8")

    def test_the_shipped_source_holds_both_changes(self):
        self.assertEqual(recipe_choice_defects(self.header, self.source), [])

    def test_each_defect_alone_is_named(self):
        defects = {
            "shared hits 1": (self.header.replace("ambiguity_most_shared_hits = 2;", "ambiguity_most_shared_hits = 1;"), self.source),
            "phi sign flipped": (self.header, self.source.replace(PHI_TERM_LINE, PHI_TERM_LINE.replace("phi +=", "phi -="))),
            "phi absent": (self.header, self.source.replace(PHI_TERM_LINE, "")),
            "phi under a preprocessor block": (self.header, self.source.replace(PHI_TERM_LINE, "#if 0\n    " + PHI_TERM_LINE + "\n#endif")),
            "phi under #if 0 with a comment between": (self.header, self.source.replace(PHI_TERM_LINE, "#if 0\n    // the term\n    " + PHI_TERM_LINE + "\n#endif")),
            "a conditional elsewhere in seed_start_of": (self.header, self.source.replace("  SeedStart start;\n", "#if 1\n  SeedStart start;\n#endif\n", 1)),
            "#if 0 elsewhere in the file": (self.header, self.source + "\n#if 0\n#endif\n"),
            "slope of the last two": (self.header, self.source.replace("(points[2].z() - points[0].z()) / std::hypot(points[2].x() - points[0].x(), points[2].y() - points[0].y())",
                                                                       "(points[2].z() - points[1].z()) / std::hypot(points[2].x() - points[1].x(), points[2].y() - points[1].y())")),
            "chord back under a diagnostic block": (self.header, self.source.replace("  const double transverse_before", "#ifdef T07_DIAGNOSTIC_CHORD_SLOPE\n  const double transverse_before", 1)),
        }
        for name, (header, source) in defects.items():
            with self.subTest(defect=name):
                self.assertNotEqual((header, source), (self.header, self.source))
                self.assertEqual(len(recipe_choice_defects(header, source)), 1, recipe_choice_defects(header, source))


class SeedStartClosedForm(unittest.TestCase):
    """The shipped seed start, by the replica above, before any build: the phi term of D1 stage 5d report section 5 with the sign that brings the probe's two roads together,
    and the chord along v. These judge the replica, not the C++: seed_start_probe.cpp reads the C++ in the build job (step probe-seed-start), and the paired comparison of
    tests.adapters.test_acts_finding_diagnosis reads its effect. They hold the arithmetic the stage 5e predictions rest on."""

    INFLATION = 1.5  # track_finding.hpp's seed_prior_inflation, read in test_the_replica_uses_the_shipped_inflation
    WORST_TRACKS = ((1.5, 1.0, 0.15, 0.15), (1.5, 1.0, -0.15, 0.15), (1.5, -1.0, 0.15, -0.15), (1.5, -1.0, -0.15, -0.15))  # where job 7496491's probe failed worst

    def points_of(self, momentum_gev: float, charge: float, slope_u: float, slope_v: float, triple) -> list:
        turn_per_mm = charge / momentum_gev * refit_tests.GEV_PER_TESLA_MM
        truth = helix_crossings(numpy.array([-100.0, 0.0, 0.0]), numpy.array([1.0, slope_u, slope_v]), turn_per_mm)
        return [numpy.array([50.0 * (plane - 1), truth[plane - 1, 0], truth[plane - 1, 1]]) for plane in triple]

    def worst_disagreement(self, slope_rule: str, phi_term_sign: float) -> float:
        worst = 0.0
        for track in self.WORST_TRACKS:
            for triple in ((3, 4, 5), (6, 7, 8)):
                roads = replica_roads(self.points_of(*track, triple), slope_rule, phi_term_sign, self.INFLATION)
                worst = max(worst, float(numpy.max(numpy.abs(roads["covariance"] / roads["hits"] - 1.0))))
        return worst

    def test_the_replica_uses_the_shipped_inflation(self):
        self.assertEqual(header_constant((NATIVE / "track_finding.hpp").read_text(encoding="utf-8"), "seed_prior_inflation"), self.INFLATION)

    def test_the_replica_reads_job_7496491s_hit_roads(self):
        """seed_start_probe.log of job 7496491, last two's slope, no term: hits u, v. The hit road does not depend on the term, and is the same for a mirror image."""
        logged = {((1, 2, 3), 0.15, 0.15, 8): (1.28945, 0.298104), ((6, 7, 8), 0.15, 0.15, 1): (1.31934, 0.216193), ((3, 4, 5), 0.0, 0.0, 1): (0.312534, 0.089916), ((6, 7, 8), 0.0, 0.0, 1): (1.29562, 0.213717)}
        for (triple, slope_u, slope_v, plane), expected in logged.items():
            with self.subTest(triple=triple, plane=plane):
                roads = replica_roads(self.points_of(1.5, 1.0, slope_u, slope_v, triple), "last-two", 0.0, self.INFLATION)
                for value, reference in zip(roads["hits"][plane - 1], expected):
                    self.assertAlmostEqual(value / reference, 1.0, delta=2e-4)

    def test_with_the_term_the_roads_agree_within_the_probes_limit(self):
        self.assertLess(self.worst_disagreement("chord", 1.0), SEED_SIGMA_AGREEMENT)

    def test_the_term_flipped_or_left_out_fails_that_limit(self):
        for sign in (-1.0, 0.0):
            with self.subTest(sign=sign):
                self.assertGreater(self.worst_disagreement("chord", sign), 10.0 * SEED_SIGMA_AGREEMENT)

    def test_along_v_the_chord_slope_reads_the_chord_and_the_last_two_does_not(self):
        """A 3-4-5 seed at plane 1, zero slope: chord weights 2, -1, 0.03 sqrt(5) = 0.067 mm; last two 1, 2, -2, 0.03 x 3 = 0.090 mm (job 7496491 read 0.0899)."""
        points = self.points_of(1.5, 1.0, 0.0, 0.0, (3, 4, 5))
        chord, last_two = 0.03 * math.sqrt(5.0), 0.09
        self.assertAlmostEqual(replica_roads(points, "chord", 1.0, self.INFLATION)["covariance"][0, 1], chord, delta=0.002)
        self.assertAlmostEqual(replica_roads(points, "last-two", 1.0, self.INFLATION)["covariance"][0, 1], last_two, delta=0.002)

    def test_the_chord_start_meets_its_own_hits(self):
        """seed_start_probe's seed_miss_limit_mm, 0.005. The chord's slope is low against the arc's by at most theta^2 / 24, theta the turn over the seed: under 1e-3 mm."""
        worst = 0.0
        for track in self.WORST_TRACKS:
            for triple in ((1, 2, 3), (1, 2, 4), (3, 4, 5), (6, 7, 8)):
                points = self.points_of(*track, triple)
                centre = replica_roads(points, "chord", 1.0, self.INFLATION)["centre"]
                worst = max(worst, max(float(numpy.max(numpy.abs(centre[point_plane - 1] - point[1:]))) for point, point_plane in zip(points, triple)))
        self.assertLess(worst, 1e-3)
        radius_mm = 1.5 / refit_tests.GEV_PER_TESLA_MM / math.sqrt(1.0 + 0.16 ** 2)
        turn = 150.0 * math.hypot(1.0, 0.25) / radius_mm
        self.assertLess((turn / 2.0) / math.sin(turn / 2.0) - 1.0, 5e-5)


class SectionSevenScoring(unittest.TestCase):
    def track(self, hit_keys, chi2=10.0, ndf=11):
        return {"hit_keys": hit_keys, "chi2": chi2, "ndf": ndf}

    def setUp(self):
        self.particles = [{"hit_keys": list(range(0, 8))}, {"hit_keys": list(range(10, 18))}, {"hit_keys": [20, 21, 22, 23, 24]}]  # the third leaves 5 hits

    def test_honest_tracks(self):
        scores = scored_event([self.track(list(range(0, 8))), self.track(list(range(10, 18)))], self.particles)
        self.assertEqual((scores["reconstructable"], scores["with_primary"], scores["fakes"], scores["duplicates"], scores["matched"]), (2, 2, 0, 0, 2))

    def test_exactly_half_is_no_match(self):
        """More than 50 %: 4 of 8 fails, and the noise hits count in the denominator."""
        scores = scored_event([self.track([0, 1, 2, 3, 100, 101, 102, 103])], self.particles)
        self.assertEqual((scores["fakes"], scores["matched"], scores["with_primary"]), (1, 0, 0))
        self.assertEqual(scored_event([self.track([0, 1, 2, 3, 4, 100, 101, 102])], self.particles)["with_primary"], 1)

    def test_two_particles_in_a_track_match_neither_at_half_each(self):
        self.assertEqual(scored_event([self.track([0, 1, 2, 10, 11, 12])], self.particles)["fakes"], 1)

    def test_a_particle_with_five_hits_matches_and_stays_out_of_efficiency(self):
        scores = scored_event([self.track([20, 21, 22, 23, 24, 100])], self.particles)
        self.assertEqual((scores["matched"], scores["reconstructable"], scores["with_primary"], scores["fakes"]), (1, 2, 0, 0))

    def test_the_primary_takes_each_rule_in_order(self):
        by_fraction = scored_event([self.track([0, 1, 2, 3, 4, 100]), self.track([0, 1, 2, 3, 4, 5])], self.particles)
        self.assertEqual((by_fraction["primaries"][0], by_fraction["duplicates"]), (1, 1))
        by_hits = scored_event([self.track([0, 1, 2, 3, 4, 5]), self.track([0, 1, 2, 3, 4, 5, 6])], self.particles)
        self.assertEqual(by_hits["primaries"][0], 1)
        by_chi2 = scored_event([self.track([0, 1, 2, 3, 4, 5], chi2=20.0), self.track([0, 1, 2, 3, 4, 6], chi2=10.0)], self.particles)
        self.assertEqual(by_chi2["primaries"][0], 1)
        by_index = scored_event([self.track([0, 1, 2, 3, 4, 5]), self.track([0, 1, 2, 3, 4, 6])], self.particles)
        self.assertEqual(by_index["primaries"][0], 0)

    def test_a_hit_on_two_selected_tracks_is_counted_once(self):
        event = {"found": [{"outcome": "selected", "hit_keys": [0, 1, 2]}, {"outcome": "selected", "hit_keys": [2, 3, 4]}, {"outcome": "evicted", "hit_keys": [3, 4, 5]}]}
        self.assertEqual(hits_on_two_selected(event), 1)
        event["found"][1]["outcome"] = "evicted"
        self.assertEqual(hits_on_two_selected(event), 0)

    def test_a_lost_particle_says_why(self):
        particle = self.particles[0]
        event = {"found": [{"outcome": "evicted", "failure_category": "ambiguity", "hit_keys": [0, 1, 2, 3, 4, 5]}], "seeds_truncated": 0, "seed_budget_reached": 0, "ambiguity_budget_reached": 0}
        self.assertEqual(loss_category(particle, event), "ambiguity")
        self.assertEqual(loss_category(particle, dict(event, found=[])), "seed-or-finding")
        self.assertEqual(loss_category(particle, dict(event, found=[], seeds_truncated=1)), "search-truncated")


def honest_record() -> dict:
    configuration = {name: "1" for name in finding_record.CONFIGURATION_KEYS}
    selected = {"key": "event-0-candidate-0", "ordinal": 0, "seed_planes": "1-2-3", "outcome": "selected", "failure_category": "none", "search_truncated": False, "measurements": 6, "holes": 2,
                "search_chi2": 5.5, "q_over_p": 0.25, "fit_chi2": 7.5, "fit_coordinates": 12, "hit_keys": [0, 1, 2, 3, 4, 5]}
    evicted = dict(selected, key="event-0-candidate-1", outcome="evicted", failure_category="ambiguity", fit_chi2=0.0, fit_coordinates=0)
    event = {"ordinal": 0, "hit_count": 48, "seeds_found": 4, "seeds_run": 2, "seeds_skipped": 2, "seeds_failed": 0, "seeds_without_candidate": 0, "seeds_truncated": 0, "seed_budget_reached": 0,
             "ambiguity_budget_reached": 0, "candidates": 2, "selected": 1, "failure_category": "none", "found": [selected, evicted]}
    header = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": finding_record.FINDING_EVIDENCE_CLASS, "product_id": "one", "data_sha256": "a" * 64,
              "product_events": 1, "configuration_sha256": "b" * 64}
    return {"header": header, "configuration": configuration, "events": [event]}


class RecordFailsOnOneDefect(unittest.TestCase):
    def setUp(self):
        self.document = honest_record()
        self.text = finding_record.format_record(self.document)

    def refused(self, text: str) -> None:
        with self.assertRaises(finding_record.RecordFormatError):
            finding_record.parse_record(text)

    def test_round_trip(self):
        parsed = finding_record.parse_record(self.text)
        self.assertEqual(finding_record.format_record(parsed), self.text)
        self.assertEqual(parsed["events"][0]["found"][1]["failure_category"], "ambiguity")

    def test_a_truncated_or_unknown_record_is_refused(self):
        self.refused(self.text[:self.text.rfind("end ")])
        self.refused(self.text.replace("end 1 2", "end 1 3"))
        self.refused(self.text.replace("end 1 2", "seed x\nend 1 2"))
        self.refused("acts-tracking-finding-record/2\n" + self.text.split("\n", 1)[1])

    def test_a_limit_left_out_of_the_configuration_is_refused(self):
        self.refused("\n".join(line for line in self.text.split("\n") if "finding_most_branches_per_seed" not in line))

    def test_a_refit_or_truth_assisted_record_is_refused(self):
        self.refused(self.text.replace("evidence_class data-side", "evidence_class truth-assisted"))
        self.refused(self.text.replace("stage find-ckf", "stage refit-known-hit-set"))

    def test_a_candidate_without_its_category_is_refused(self):
        self.refused(self.text.replace(" evicted ambiguity ", " evicted none "))
        self.refused(self.text.replace(" selected none ", " selected fit "))

    def test_a_dropped_candidate_or_seed_is_refused(self):
        self.refused("\n".join(line for line in self.text.split("\n") if "candidate-1" not in line).replace("end 1 2", "end 1 1"))
        self.document["events"][0]["seeds_run"] = 1
        self.refused(finding_record.format_record(self.document))

    def test_seeds_run_must_balance_their_outcomes(self):
        self.document["events"][0].update(seeds_failed=2, seeds_without_candidate=1)
        self.refused(finding_record.format_record(self.document))
        self.document["events"][0].update(seeds_found=9, seeds_run=7, seeds_failed=1, seeds_without_candidate=1)  # 5 seeds left for 2 candidates
        self.refused(finding_record.format_record(self.document))

    def test_an_event_budget_reaches_every_candidate(self):
        """Stage 5 review m9: the mark follows the event's budgets too, not only the seed's."""
        event = self.document["events"][0]
        event["ambiguity_budget_reached"] = 1
        self.refused(finding_record.format_record(self.document))
        self.assertEqual(len(finding_record.parse_record(finding_record.format_record(self.document), marks_event_budgets=False)["events"]), 1)
        for item in event["found"]:
            item["search_truncated"] = True
        self.assertEqual(len(finding_record.parse_record(finding_record.format_record(self.document))["events"]), 1)

    def test_a_truncated_candidate_with_no_truncated_seed_is_refused(self):
        self.document["events"][0]["found"][0]["search_truncated"] = True
        self.refused(finding_record.format_record(self.document))
        self.document["events"][0]["seeds_truncated"] = 1
        self.assertEqual(len(finding_record.parse_record(finding_record.format_record(self.document))["events"]), 1)

    def test_an_event_with_no_track_names_its_class(self):
        event = self.document["events"][0]
        event["found"][0].update(outcome="evicted", failure_category="ambiguity")
        event.update(selected=0, failure_category="none")
        self.refused(finding_record.format_record(self.document))
        event["failure_category"] = "seed-or-finding"
        self.assertEqual(finding_record.event_defects(event), [])
        event["seed_budget_reached"] = 1
        for item in event["found"]:
            item["search_truncated"] = True
        self.assertEqual(len(finding_record.event_defects(event)), 1)
        event["failure_category"] = "search-truncated"
        self.assertEqual(finding_record.event_defects(event), [])


class FindingIsNeverARefit(unittest.TestCase):
    def document(self, **changes) -> dict:
        header = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": "data-side", "hit_sets_sha256": "none", "qop_status": "measured"}
        return {"header": dict(header, **changes), "tracks": []}

    def test_honest_header(self):
        self.assertEqual(finding_product_defects(self.document()), [])
        self.assertTrue(native_product.fit_summary(self.document())["reported_as_finding"])

    def test_a_refit_product_fails_and_is_not_reported_as_finding(self):
        refit = {"recipe": "reco.track.acts-kf-refit/1", "stage": "refit-known-hit-set", "evidence_class": "truth-assisted", "hit_sets_sha256": "c" * 64}
        self.assertEqual(len(finding_product_defects(self.document(**refit))), 5)
        self.assertFalse(native_product.fit_summary(self.document(**refit))["reported_as_finding"])

    def test_one_field_changed_fails(self):
        for name, wrong in (("evidence_class", "truth-assisted"), ("stage", "refit-known-hit-set")):
            with self.subTest(name=name):
                self.assertFalse(native_product.fit_summary(self.document(**{name: wrong}))["reported_as_finding"])
                self.assertTrue(finding_product_defects(self.document(**{name: wrong})))
        self.assertEqual(len(finding_product_defects(self.document(hit_sets_sha256="c" * 64))), 1)

    def test_the_finder_program_has_no_hit_set_route(self):
        source = (NATIVE / "acts_tracking_finder.cpp").read_text(encoding="utf-8")
        self.assertIn('known{"data-file", "product-id", "product-file", "record-file", "product-events"}', source)
        for word in ("truth_file", "t07_seed_stream", "t07_event_generator", "generation_constants", "read_hit_sets"):
            self.assertNotIn(word, source + (NATIVE / "track_finding.cpp").read_text(encoding="utf-8") + (NATIVE / "track_finding.hpp").read_text(encoding="utf-8"))


FINDER_FLAGS = {"data-file", "product-id", "product-file", "record-file", "product-events"}
FINDER_OPTIONAL_OUTPUTS = {"seed-file", "ambiguity-trace-file", "ambiguity-trace-events", "r33-outputs"}  # D1 stage 9: R33's outputs of the delivered tracks, an output; it takes no input
FINDER_OPTIONAL_STEPS = {"vertex-recipe"}  # D1 stage 7: the vertex step on the delivered tracks, by its recipe's name; it takes no input
TRUTH_SEEDED_ONLY = ("find_from_starts", "PlaneStart", "truth_seeded", "truth-seeded", ".t07truth", "t07starts", "truth-starts", "start-file")


def finder_truth_input_defects(finder_source: str, finding_source: str, cmake_text: str) -> list:
    """Section 3.1 and decisions.md, "T07 stage 5": the finder stays truth-free. Its flags are exactly the hits, its outputs and the named-event trace; its program names
    nothing of the truth-seeded run; its CMake target compiles neither truth-seeded source; and find_from_starts is defined in truth_seeded_search.cpp alone, which only
    acts_truth_seeded_run compiles. The build job reads the same on the binary: link line and symbols."""
    defects = []
    known = re.search(r"const std::set<std::string> known\{([^}]*)\}", finder_source)
    optional = re.search(r"const std::set<std::string> optional_outputs\{([^}]*)\}", finder_source)
    steps = re.search(r"const std::set<std::string> optional_steps\{([^}]*)\}", finder_source)
    if not known or set(re.findall(r'"([^"]+)"', known.group(1))) != FINDER_FLAGS:
        defects.append("the finder's required flags are not the hits and its outputs")
    if not optional or set(re.findall(r'"([^"]+)"', optional.group(1))) != FINDER_OPTIONAL_OUTPUTS:
        defects.append("the finder's optional flags are not its outputs")
    if not steps or set(re.findall(r'"([^"]+)"', steps.group(1))) != FINDER_OPTIONAL_STEPS:
        defects.append("the finder's optional steps are not the vertex step alone")
    named = [word for word in TRUTH_SEEDED_ONLY if word in finder_source]
    if named:
        defects.append(f"the finder's program names {named}")
    target = re.search(r"add_executable\(acts_tracking_finder ([^)]*)\)", cmake_text)
    if not target or set(target.group(1).split()) & {"truth_seeded_search.cpp", "acts_truth_seeded_run.cpp"}:
        defects.append("the finder's target compiles truth-seeded code")
    if "TrackFinder::find_from_starts(" in finding_source:
        defects.append("track_finding.cpp, which the finder compiles, defines find_from_starts")
    compiled_by = re.findall(r"add_executable\((\w+) ([^)]*)\)", cmake_text)
    others = sorted(name for name, sources in compiled_by if "truth_seeded_search.cpp" in sources.split() and name not in ("acts_tracking_finder", "acts_truth_seeded_run"))
    if others or not any(name == "acts_truth_seeded_run" and "truth_seeded_search.cpp" in sources.split() for name, sources in compiled_by):
        defects.append(f"truth_seeded_search.cpp is compiled by {others or 'no program'}, not by acts_truth_seeded_run alone")
    return defects


class FinderStaysTruthFree(unittest.TestCase):
    """D1 stage 6 brief: a test that fails if the finder gains a truth input. Driven with the shipped sources and with one defect each."""

    def setUp(self):
        self.finder = (NATIVE / "acts_tracking_finder.cpp").read_text(encoding="utf-8")
        self.finding = (NATIVE / "track_finding.cpp").read_text(encoding="utf-8")
        self.cmake = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")

    def test_the_shipped_finder_is_truth_free(self):
        self.assertEqual(finder_truth_input_defects(self.finder, self.finding, self.cmake), [])
        self.assertIn("EventFinding TrackFinder::find_from_starts(", (NATIVE / "truth_seeded_search.cpp").read_text(encoding="utf-8"))

    def test_each_truth_input_alone_is_named(self):
        required = 'known{"data-file", "product-id", "product-file", "record-file", "product-events"}'
        optional = 'optional_outputs{"seed-file", "ambiguity-trace-file", "ambiguity-trace-events", "r33-outputs"}'
        steps = 'optional_steps{"vertex-recipe"}'
        finder_target = "add_executable(acts_tracking_finder acts_tracking_finder.cpp track_finding.cpp kalman_refit.cpp track_vertexing.cpp)"
        defects = {
            "a truth file flag": (self.finder.replace(required, required.replace('"product-events"', '"product-events", "truth-file"')), self.finding, self.cmake),
            "a particle file as an optional flag": (self.finder.replace(optional, optional.replace('"seed-file"', '"seed-file", "particle-file"')), self.finding, self.cmake),
            "a truth vertex file as an optional step": (self.finder.replace(steps, steps.replace('"vertex-recipe"', '"vertex-recipe", "truth-vertex-file"')), self.finding, self.cmake),
            "the probe compiles truth-seeded code": (self.finder, self.finding, self.cmake.replace("add_executable(seed_start_probe seed_start_probe.cpp", "add_executable(seed_start_probe seed_start_probe.cpp truth_seeded_search.cpp")),
            "a call of the truth-seeded entry": (self.finder.replace("finder.find(event, ordinal, trace_this)", "finder.find_from_starts(event, ordinal, {})"), self.finding, self.cmake),
            "the target compiles truth-seeded code": (self.finder, self.finding, self.cmake.replace(finder_target, finder_target.replace("track_vertexing.cpp)", "track_vertexing.cpp truth_seeded_search.cpp)"))),
            "the entry defined where the finder compiles it": (self.finder, self.finding + "\nEventFinding TrackFinder::find_from_starts(\n", self.cmake),
        }
        for name, sources in defects.items():
            with self.subTest(defect=name):
                self.assertNotEqual(sources, (self.finder, self.finding, self.cmake))
                self.assertEqual(len(finder_truth_input_defects(*sources)), 1, finder_truth_input_defects(*sources))


class StatesStayApart(unittest.TestCase):
    def document(self) -> dict:
        parameters = [{"track_key": "one", "state_index": 0, "state_type": name, "parameters": [float(index)] * 6} for index, name in enumerate(native_product.STATE_TYPES)]
        return {"states": [{"track_key": "one", "index": 0, "kind": "measurement"}], "parameters": parameters}

    def test_each_defect_fails(self):
        self.assertEqual(states_apart_defects(self.document()), [])
        lost = self.document()
        lost["parameters"].pop(1)
        self.assertEqual(len(states_apart_defects(lost)), 1)
        same = self.document()
        same["parameters"][1]["parameters"] = same["parameters"][0]["parameters"]
        self.assertEqual(len(states_apart_defects(same)), 1)

    def test_a_product_and_its_record_must_agree(self):
        events = honest_record()["events"]
        states = [{"track_key": "event-0-candidate-0", "hit_key": key} for key in range(6)]
        document = {"tracks": [{"key": "event-0-candidate-0"}], "states": states}
        self.assertEqual(record_matches_product(events, document, 1), [])
        self.assertEqual(len(record_matches_product(events, dict(document, tracks=[]), 1)), 1)
        self.assertEqual(len(record_matches_product(events, dict(document, states=states[:-1]), 1)), 1)


class PredictionsCanDisagree(unittest.TestCase):
    def reading(self, **changes) -> dict:
        return dict({"reconstructable": 18000, "with_primary": 18000, "reconstructed": 18000, "matched": 18000, "fakes": 0, "duplicates": 0}, **changes)

    def test_each_defect_is_named(self):
        self.assertEqual(prediction_defects(self.reading(), "clean", 0), [])
        self.assertEqual(len(prediction_defects(self.reading(with_primary=17900), "clean", 0)), 1)
        self.assertEqual(len(prediction_defects(self.reading(with_primary=17900), "noise", 0)), 1)
        self.assertEqual(len(prediction_defects(self.reading(fakes=20), "noise", 2)), 1)
        self.assertEqual(len(prediction_defects(self.reading(duplicates=20), "clean", 2)), 1)

    def test_a_bin_at_the_floor_does_not_disagree(self):
        self.assertEqual(prediction_defects(self.reading(with_primary=int(18000 * R_FLOOR_OF_LEVEL[0])), "noise", 0), [])


# ---- The built tests.

def run_program(arguments, check: bool = True) -> subprocess.CompletedProcess:
    finished = subprocess.run([str(item) for item in arguments], capture_output=True, text=True, timeout=7200)
    if check and finished.returncode != 0:
        raise AssertionError(f"{arguments[0]} exit {finished.returncode}: {finished.stdout}{finished.stderr[-2000:]}")
    return finished


def generate(folder: Path, fixture: str, stratum: int, count: int) -> tuple:
    data_file, truth_file = folder / f"{fixture}-{stratum}.t07data", folder / f"{fixture}-{stratum}.t07truth"
    run_program([GENERATOR, "generate", "--fixture", fixture, "--block", TUNING_BLOCK, "--stratum", stratum, "--first-event", 0, "--count", count, "--data-file", data_file, "--truth-file", truth_file])
    header = truth_files.read_truth_header(truth_file)
    if (header["block"], header["stratum"], header["fixture_id"]) != (TUNING_BLOCK, stratum, FIXTURE_IDS[fixture]):
        raise AssertionError(f"the truth file says {header}")
    return data_file, truth_file


def find(folder: Path, data_file: Path, name: str, product_events: int, program: Path = FINDER, seed_file: Path = None) -> tuple:
    record_file, product_file = folder / f"{name}.record", folder / f"{name}.product"
    finished = run_program([program, "--data-file", data_file, "--product-id", name, "--product-file", product_file, "--record-file", record_file, "--product-events", product_events]
                           + (["--seed-file", seed_file] if seed_file else []))
    return finished, record_file, product_file


def particles_of(truth_event) -> list:
    return [{"hit_keys": [int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY]} for track in truth_event["tracks"]]


def tracks_of(event: dict) -> list:
    return [{"hit_keys": item["hit_keys"], "chi2": item["fit_chi2"], "ndf": item["fit_coordinates"] - 5} for item in event["found"] if item["outcome"] == "selected"]


def missed_planes_of(truth_track) -> tuple:
    return tuple(plane + 1 for plane in range(PLANES) if int(truth_track["hit_keys"][plane]) == truth_files.NO_HIT_KEY)


def stratum_reading(fixture: str, stratum: int, folder: Path) -> dict:
    """Generate, find, score one stratum, then delete its files. Truth is read here, after the finder has finished."""
    started = time.monotonic()
    data_file, truth_file = generate(folder, fixture, stratum, EVENTS_PER_BIN)
    generated = time.monotonic()
    finished, record_file, product_file = find(folder, data_file, f"t07-dev-find-{fixture}-{stratum}", PRODUCT_EVENTS)
    searched = time.monotonic()
    record = finding_record.parse_record(record_file.read_text(encoding="utf-8"))
    document = native_product.parse_product(product_file.read_text(encoding="utf-8"))
    tally = Counter()
    losses = Counter()
    tracks_by_missed, lost_by_missed = Counter(), Counter()
    if truth_files.read_truth_header(truth_file)["event_count"] != len(record["events"]):
        raise AssertionError(f"{fixture} stratum {stratum}: the record does not hold every event")
    for event, truth_event in zip(record["events"], truth_files.iter_truth_events(truth_file)):
        particles = particles_of(truth_event)
        scores = scored_event(tracks_of(event), particles)
        tally.update({name: scores[name] for name in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates")})
        losses.update(loss_category(particles[index], event) for index in scores["lost"])
        missed = [missed_planes_of(track) for track in truth_event["tracks"]]
        tracks_by_missed.update(missed[index] for index, particle in enumerate(particles) if len(particle["hit_keys"]) >= LEAST_HITS)
        lost_by_missed.update(missed[index] for index in scores["lost"])
        tally.update({name: event[name] for name in ("seeds_found", "seeds_run", "seeds_skipped", "seeds_failed", "seeds_without_candidate", "seeds_truncated", "candidates", "selected")})
        tally["fit_failed"] += sum(item["outcome"] == "fit-failed" for item in event["found"])
        tally["evicted"] += sum(item["outcome"] == "evicted" for item in event["found"])
        tally["hits_on_two_tracks"] += hits_on_two_selected(event)
        tally["truncated_events"] += int(event["seeds_truncated"] > 0 or event["seed_budget_reached"] or event["ambiguity_budget_reached"])
    for path in (data_file, truth_file, record_file, product_file):
        path.unlink()
    return {"fixture": fixture, "stratum": stratum, "tally": tally, "losses": losses, "events": len(record["events"]), "tracks_by_missed": tracks_by_missed, "lost_by_missed": lost_by_missed, "generate_seconds": generated - started, "search_seconds": searched - generated,
            "stderr_bytes": len(finished.stderr), "product_defects": finding_product_defects(document) + states_apart_defects(document) + record_matches_product(record["events"], document, PRODUCT_EVENTS),
            "configuration_sha256": record["header"]["configuration_sha256"], "configuration": record["configuration"]}


@unittest.skipUnless(BUILT, NOT_BUILT)
class DevelopmentRun(unittest.TestCase):
    """Both fixtures, every stratum, block 1. Readings printed; a test here fails on a broken product or on a disagreement with a prediction. Neither is a gate."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        jobs = [(fixture, stratum) for fixture in ("noise", "clean") for stratum in (11, 8, 5, 2, 10, 7, 4, 1, 9, 6, 3, 0)]  # slowest first
        with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
            cls.readings = list(pool.map(lambda job: stratum_reading(job[0], job[1], Path(cls.folder.name)), jobs))
        print(f"FINDING-CONFIGURATION sha256 {cls.readings[0]['configuration_sha256']}", flush=True)
        for name, value in cls.readings[0]["configuration"].items():
            print(f"FINDING-CONFIGURATION {name} {value}", flush=True)
        for item in sorted(cls.readings, key=lambda item: (item["fixture"], item["stratum"])):
            tally = item["tally"]
            print(f"FINDING-READING development reading, not a gate (K09): {item['fixture']} stratum {item['stratum']} events {item['events']} reconstructable {tally['reconstructable']} "
                  f"with_primary {tally['with_primary']} efficiency {tally['with_primary'] / tally['reconstructable']:.6f} reconstructed {tally['reconstructed']} fakes {tally['fakes']} "
                  f"matched {tally['matched']} duplicates {tally['duplicates']}", flush=True)
            print(f"FINDING-SEARCH {item['fixture']} stratum {item['stratum']} per event: seeds_found {tally['seeds_found'] / item['events']:.1f} seeds_run {tally['seeds_run'] / item['events']:.1f} "
                  f"candidates {tally['candidates'] / item['events']:.2f}; totals: seeds_failed {tally['seeds_failed']} seeds_without_candidate {tally['seeds_without_candidate']} "
                  f"seeds_truncated {tally['seeds_truncated']} truncated_events {tally['truncated_events']} evicted {tally['evicted']} fit_failed {tally['fit_failed']} "
                  f"hits_on_two_tracks {tally['hits_on_two_tracks']} losses {dict(item['losses'])}", flush=True)
            worst = sorted(item["lost_by_missed"], key=lambda missed: -item["lost_by_missed"][missed])[:8]
            print(f"FINDING-LOSS-PATTERN {item['fixture']} stratum {item['stratum']} lost/tracks by missed planes: all hits kept {item['lost_by_missed'][()]}/{item['tracks_by_missed'][()]}; "
                  + ", ".join(f"{missed} {item['lost_by_missed'][missed]}/{item['tracks_by_missed'][missed]}" for missed in worst if missed), flush=True)
            print(f"FINDING-COST {item['fixture']} stratum {item['stratum']} events {item['events']} generate_seconds {item['generate_seconds']:.1f} find_seconds {item['search_seconds']:.1f} "
                  f"stderr_bytes {item['stderr_bytes']}", flush=True)

    def test_every_stratum_ran_at_its_size_under_one_configuration(self):
        self.assertEqual(len(self.readings), 24)
        self.assertEqual({item["events"] for item in self.readings}, {EVENTS_PER_BIN})
        self.assertEqual(len({item["configuration_sha256"] for item in self.readings}), 1)
        self.assertEqual(self.readings[0]["configuration"]["diagnostic_build"], "none")
        self.assertEqual(self.readings[0]["configuration"]["ambiguity_most_shared_hits"], "2")  # in the record's configuration too (stage 5e brief)
        self.assertEqual((self.readings[0]["configuration"]["seed_slope_along_v"], self.readings[0]["configuration"]["seed_covariance_phi_term"]), ("chord", "present"))  # review m5

    def test_no_reconstructable_particle_left_a_denominator(self):
        """Section 7's denominator is the generator's: clean holds every track, and the noise fixture about 0.99958 of them."""
        for item in self.readings:
            tracks = TRACKS_OF_LEVEL[item["stratum"] % 3] * EVENTS_PER_BIN
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                if item["fixture"] == "clean":
                    self.assertEqual(item["tally"]["reconstructable"], tracks)
                else:
                    self.assertAlmostEqual(item["tally"]["reconstructable"] / tracks, 0.99958, delta=PREDICTION_Z * math.sqrt(0.00042 / tracks))
                self.assertEqual(item["tally"]["with_primary"] + sum(item["losses"].values()), item["tally"]["reconstructable"])

    def test_products_keep_their_states_apart_and_say_finding(self):
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(item["product_defects"], [])

    def test_readings_against_the_predictions(self):
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual(prediction_defects(item["tally"], item["fixture"], item["stratum"] % 3), [])


def sorted_hits(hits) -> list:
    """Hits as the fixture writes them: on the grid, by plane and position (t07_data_file.hpp), key = position."""
    gridded = [(plane, float(fixture_files.on_hit_grid(loc0_mm)), float(fixture_files.on_hit_grid(loc1_mm))) for plane, loc0_mm, loc1_mm in hits]
    return sorted(gridded)


def hit_tuples(data_event) -> list:
    return [(int(hit["plane"]), float(hit["loc0_mm"]), float(hit["loc1_mm"])) for hit in data_event["hits"]]


class NegativeCaseFile(unittest.TestCase):
    """D4 E5, on hand-made files: the builder writes the case file, its description and SHA256SUMS; the reader refuses any byte that does not follow
    from the recorded block-1 source event, and a source that is not block 1's (section 11). No build is needed."""

    def setUp(self):
        from tests.adapters.test_acts_fake_rate import truth_file_bytes
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)
        hits = [(plane, fixture_files.on_hit_grid(0.25 * plane + 3.0 * track).item(), fixture_files.on_hit_grid(-0.125 * plane).item())
                for track in range(2) for plane in range(1, PLANES + 1)]
        order = sorted(range(len(hits)), key=lambda index: hits[index])
        self.source_data = self.work / "source.t07data"
        self.source_data.write_bytes(fixture_files.encode_data_file(HIT_SIGMA_MM, [[hits[index] for index in order]]))
        position = {index: rank for rank, index in enumerate(order)}
        particles = [[position[track * PLANES + plane] for plane in range(PLANES)] for track in range(2)]
        self.truth = self.work / "source.t07truth"
        self.write_truth(truth_file_bytes, particles)

    def write_truth(self, truth_file_bytes, particles, **identity) -> None:
        identity = {"stratum": negative_cases.SOURCE_STRATUM, "block": negative_cases.SOURCE_BLOCK, "fixture_id": negative_cases.SOURCE_FIXTURE_ID, **identity}
        self.truth.write_bytes(truth_file_bytes([particles], fixture_files.file_sha256(self.source_data), **identity))

    def test_the_cases_and_their_order(self):
        case_bytes, description = negative_cases.build(self.source_data, self.truth)
        names = description["names"]
        self.assertEqual(names[:7], ["honest", "one-wrong-plane", "three-wrong-planes", "branch-explosion", "no-triple", "two-planes", "seed-budget"])
        self.assertEqual(names[7:35], [f"lost-{first}-{second}" for first, second in itertools.combinations(range(1, PLANES + 1), 2)])
        self.assertEqual(len(names), 7 + 28 + 2 * 28)
        cases = negative_cases.cases_of(description)
        self.assertEqual(case_bytes, fixture_files.encode_data_file(HIT_SIGMA_MM, cases["events"]))
        one_wrong = cases["events"][names.index("one-wrong-plane")]
        self.assertEqual(sorted(hit for hit in one_wrong if hit[0] != 5), sorted(hit for hit in cases["events"][0] if hit[0] != 5))
        self.assertEqual(len(cases["events"][names.index("seed-budget")]), 16 + 3 * 26)
        self.assertEqual(len(cases["events"][names.index("branch-explosion")]), 16 + 2 * 2 * EXPLOSION_EXTRA_HITS)

    def test_write_then_read(self):
        description = negative_cases.write(self.work / "kept", self.source_data, self.truth)
        read = negative_cases.read(self.work / "kept")
        self.assertEqual(read["description"], description)
        self.assertEqual(read["case_file"].read_bytes(), negative_cases.build(self.source_data, self.truth)[0])
        self.assertEqual(read["description"]["source"]["block"], 1)
        listed = (self.work / "kept" / negative_cases.SUMS_FILE).read_text(encoding="utf-8")
        for name in (negative_cases.CASE_FILE, negative_cases.DESCRIPTION_FILE):
            self.assertIn(f"{fixture_files.file_sha256(self.work / 'kept' / name)}  {name}\n", listed)

    def test_one_changed_byte_or_a_missing_file_is_refused(self):
        negative_cases.write(self.work / "kept", self.source_data, self.truth)
        case = self.work / "kept" / negative_cases.CASE_FILE
        raw = bytearray(case.read_bytes())
        raw[-1] ^= 1
        case.write_bytes(bytes(raw))
        with self.assertRaises(negative_cases.NegativeCaseError):
            negative_cases.read(self.work / "kept")
        (self.work / "kept" / negative_cases.SUMS_FILE).unlink()
        with self.assertRaises(negative_cases.NegativeCaseError):
            negative_cases.read(self.work / "kept")
        with self.assertRaises(negative_cases.NegativeCaseError):
            negative_cases.read(self.work / "nowhere")

    def test_a_case_file_that_does_not_follow_from_its_source_is_refused_even_with_matching_sums(self):
        import json
        negative_cases.write(self.work / "kept", self.source_data, self.truth)
        kept = self.work / "kept"
        description = json.loads((kept / negative_cases.DESCRIPTION_FILE).read_text(encoding="utf-8"))
        description["hits"][0][1] += 2.0 ** -20
        (kept / negative_cases.DESCRIPTION_FILE).write_text(json.dumps(description, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        (kept / negative_cases.SUMS_FILE).write_text("".join(f"{fixture_files.file_sha256(kept / name)}  {name}\n" for name in (negative_cases.CASE_FILE, negative_cases.DESCRIPTION_FILE)), encoding="utf-8")
        with self.assertRaises(negative_cases.NegativeCaseError):
            negative_cases.read(kept)

    def test_a_source_other_than_block_1_clean_stratum_0_or_a_truth_of_other_data_is_refused(self):
        from tests.adapters.test_acts_fake_rate import truth_file_bytes
        particles = [list(range(8)), list(range(8, 16))]
        for identity in ({"block": 2}, {"block": 11}, {"stratum": 3}, {"fixture_id": 7002}):
            with self.subTest(identity=identity):
                self.write_truth(truth_file_bytes, particles, **identity)
                with self.assertRaises(negative_cases.NegativeCaseError):
                    negative_cases.build(self.source_data, self.truth)
        self.truth.write_bytes(truth_file_bytes([particles], "0" * 64, stratum=0, block=1, fixture_id=7001))
        with self.assertRaises(negative_cases.NegativeCaseError):
            negative_cases.build(self.source_data, self.truth)

    @unittest.skipUnless((NEGATIVE_CASES_FOLDER / negative_cases.SUMS_FILE).is_file(), "the kept negative-case file is written by the D4 E2 job and copied here after it passes")
    def test_the_kept_file_reads_and_comes_from_block_1(self):
        read = negative_cases.read(NEGATIVE_CASES_FOLDER)
        source = read["description"]["source"]
        self.assertEqual((source["fixture_id"], source["block"], source["stratum"], source["first_event"], source["count"]), (7001, 1, 0, 0, 1))


@unittest.skipUnless(BUILT, NOT_BUILT)
class NegativeCases(unittest.TestCase):
    """Sheet, Acceptance: wrong hits, branch explosion, seed failure, from block 1 files (section 11). One data file; each event's meaning is its position.
    D4 E5: the file is the kept one (NEGATIVE_CASES_FOLDER), read by t07_negative_cases.read; block 1's clean stratum 0, event 0, regenerated here, must
    build it byte for byte, so the kept file is what the frozen generator gives today."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        data_file, truth_file = generate(folder, "clean", NEGATIVE_STRATUM, 1)
        cls.clean_file, cls.truth_file = data_file, truth_file
        kept = negative_cases.read(NEGATIVE_CASES_FOLDER)
        built_bytes, built = negative_cases.build(data_file, truth_file)
        if built_bytes != kept["case_file"].read_bytes() or built != kept["description"]:
            raise AssertionError("block 1 clean stratum 0 event 0 no longer builds the kept negative-case file")
        print(f"FINDING-NEGATIVE kept file {negative_cases.CASE_FILE} sha256 {fixture_files.file_sha256(kept['case_file'])}", flush=True)
        cases = negative_cases.cases_of(kept["description"])
        cls.hits = cases["hits"]
        cls.tracks = [{"hit_keys": keys} for keys in cases["tracks"]]
        for index, track in enumerate(next(truth_files.iter_truth_events(truth_file))["tracks"]):
            print(f"FINDING-NEGATIVE track {index}: q/p {float(track['q_over_p']):+.4f} slope_u {float(track['slope_u']):+.4f} slope_v {float(track['slope_v']):+.4f}", flush=True)
        cls.pairs = list(itertools.combinations(range(1, PLANES + 1), 2))
        cls.alone = cases["alone"]
        cls.names = cases["names"]
        cls.events = cases["events"]
        cls.case_file = kept["case_file"]
        cls.seed_file = folder / "negative.seeds"
        cls.finished, record_file, _ = find(folder, cls.case_file, "t07-negative-cases", 0, seed_file=cls.seed_file)
        cls.record = finding_record.parse_record(record_file.read_text(encoding="utf-8"))
        cls.seeds = list(finding_record.iter_seed_events(cls.seed_file))
        for name, event in zip(cls.names, cls.record["events"]):
            if name.startswith("alone-"):
                continue
            print(f"FINDING-NEGATIVE {name}: seeds_found {event['seeds_found']} seeds_truncated {event['seeds_truncated']} seed_budget {event['seed_budget_reached']} "
                  f"ambiguity_budget {event['ambiguity_budget_reached']} candidates {event['candidates']} "
                  f"selected {event['selected']} category {event['failure_category']}", flush=True)

    def event(self, name: str) -> dict:
        return self.record["events"][self.names.index(name)]

    def planes_of(self, name: str, item: dict) -> set:
        return {self.events[self.names.index(name)][key][0] for key in item["hit_keys"]}

    def selected(self, name: str) -> list:
        return [item for item in self.event(name)["found"] if item["outcome"] == "selected"]

    def test_the_honest_event_finds_every_track_and_the_record_reads(self):
        self.assertEqual(len(self.selected("honest")), len(self.tracks))
        self.assertEqual(self.event("honest")["failure_category"], "none")

    def test_one_wrong_hit_per_track_stays_off_every_track(self):
        tracks = self.selected("one-wrong-plane")
        self.assertEqual(len(tracks), len(self.tracks))
        for item in tracks:
            with self.subTest(track=item["key"]):
                self.assertNotIn(5, self.planes_of("one-wrong-plane", item))
                self.assertGreaterEqual(item["holes"], 1)

    def test_three_wrong_hits_per_track_leave_no_track_and_a_named_class(self):
        event = self.event("three-wrong-planes")
        self.assertEqual(event["selected"], 0)
        self.assertGreater(event["seeds_without_candidate"], 0)
        self.assertEqual(event["failure_category"], "seed-or-finding")

    def test_a_branch_explosion_is_marked_and_stays_inside_its_budget(self):
        event = self.event("branch-explosion")
        self.assertGreater(event["seeds_truncated"], 0)
        self.assertTrue(any(item["search_truncated"] for item in event["found"]))
        self.assertGreater(event["selected"], 0)  # candidates reaching a limit may be delivered, marked (BP03)
        seeds = self.seeds[self.names.index("branch-explosion")]
        self.assertEqual(sum(seed["candidates"] for seed in seeds), event["candidates"])
        most_branches = header_constant((NATIVE / "track_finding.hpp").read_text(encoding="utf-8"), "finding_most_branches_per_seed")
        self.assertLessEqual(max(seed["candidates"] for seed in seeds), most_branches + 1)  # per seed, which the count by seed type of jobs 7493849 to 7494405 could not fail
        self.assertEqual(event["ambiguity_budget_reached"], 1)  # 1,221 candidates against 1,000 iterations in job 7494405: the conflicted tracks left are delivered, marked
        self.assertTrue(all(item["search_truncated"] for item in event["found"]))

    def test_every_seed_has_one_outcome_and_the_counters_agree(self):
        """Stage 5 review m10: the outcomes of a seed balance the event's counters, in every case of this file."""
        for name, event, seeds in zip(self.names, self.record["events"], self.seeds):
            with self.subTest(name=name):
                outcomes = Counter(seed["outcome"] for seed in seeds)
                self.assertEqual(len(seeds), event["seeds_found"])
                self.assertEqual(outcomes["skipped"], event["seeds_skipped"])
                self.assertEqual(outcomes["no-start"] + outcomes["filter-error"], event["seeds_failed"])
                self.assertEqual(outcomes["no-candidate"], event["seeds_without_candidate"])
                self.assertEqual(sum(seed["candidates"] for seed in seeds), event["candidates"])

    def test_a_seed_budget_reached_is_marked(self):
        event = self.event("seed-budget")
        self.assertEqual(event["seed_budget_reached"], 1)
        self.assertEqual(event["seeds_found"], header_constant((NATIVE / "track_finding.hpp").read_text(encoding="utf-8"), "finding_most_seeds_per_event"))

    def test_seed_failure_stays_in_the_record_with_its_class(self):
        for name in ("no-triple", "two-planes"):
            with self.subTest(name=name):
                event = self.event(name)
                self.assertEqual((event["seeds_found"], event["selected"], event["failure_category"]), (0, 0, "seed-or-finding"))

    def test_any_two_lost_planes_still_find_every_track(self):
        """Section 7's reconstructable track, for all 28 pairs, in the built program: the coverage argument, run. A third hit failing the chi2 cut drops a 6-hit track:
        28 x 6 tracks x 6 hits x 3.4e-4 = 0.34 expected, so LOST_TO_THE_CHI2_CUT in all. A missing triple would lose all 6 tracks of one pair."""
        lost = {f"{first}-{second}": len(self.tracks) - len(self.selected(f"lost-{first}-{second}")) for first, second in self.pairs}
        for first, second in self.pairs:
            rows = self.events[self.names.index(f"lost-{first}-{second}")]
            for index, particle in enumerate(self.tracks):
                own = set(sorted_hits([self.hits[key] for key in particle["hit_keys"] if self.hits[key][0] not in (first, second)]))
                keys = {key for key, row in enumerate(rows) if row in own}
                if not any(2 * len(keys & set(item["hit_keys"])) > len(item["hit_keys"]) for item in self.selected(f"lost-{first}-{second}")):
                    print(f"FINDING-NEGATIVE lost-track pair {first}-{second} track {index}", flush=True)
        self.assertLessEqual(sum(lost.values()), LOST_TO_THE_CHI2_CUT, lost)

    def test_a_track_that_alone_lost_two_planes_is_found_among_the_others(self):
        """Job 7493849's cause, on one event: a plane where only this track has no hit, with the other tracks' hits still on it. A foreign hit in a wide window takes the hole's place."""
        lost = []
        for name, kept in self.alone.items():
            rows = self.events[self.names.index(name)]
            own = set(sorted_hits(kept))
            keys = {key for key, row in enumerate(rows) if row in own}
            if not any(2 * len(keys & set(item["hit_keys"])) > len(item["hit_keys"]) for item in self.selected(name)):
                lost.append(name)
        print(f"FINDING-NEGATIVE alone: lost {len(lost)} of {len(self.alone)}: {lost[:12]}", flush=True)
        self.assertLessEqual(len(lost), LOST_ALONE_LIMIT, lost)

    def test_truth_reaches_the_finder_by_no_input(self):
        folder = Path(self.folder.name)
        arguments = ["--product-id", "t07-refused", "--product-file", folder / "refused.product", "--record-file", folder / "refused.record", "--product-events", 0]
        self.assertEqual(run_program([FINDER, "--data-file", self.truth_file] + arguments, check=False).returncode, 2)
        renamed = folder / "renamed.t07data"
        renamed.write_bytes(self.truth_file.read_bytes())
        self.assertEqual(run_program([FINDER, "--data-file", renamed] + arguments, check=False).returncode, 2)
        honest_named_as_truth = folder / "honest.t07truth"
        honest_named_as_truth.write_bytes(self.clean_file.read_bytes())
        self.assertEqual(run_program([FINDER, "--data-file", honest_named_as_truth] + arguments, check=False).returncode, 2)
        self.assertEqual(run_program([FINDER, "--data-file", self.clean_file, "--hit-sets", self.clean_file] + arguments, check=False).returncode, 2)
        self.assertFalse((folder / "refused.record").exists())

    def test_the_binary_holds_no_seed_or_truth_code(self):
        """Section 3.1. The build job checks symbols too. The search finds the names where they are."""
        finder, generator = FINDER.read_bytes(), GENERATOR.read_bytes()
        for name in (b"EventSeedStream", b"TruthFileWriter"):
            self.assertNotIn(name, finder)
            self.assertIn(name, generator)
        self.assertNotIn(b"event_seed_digest", finder)


@unittest.skipUnless(BUILT, NOT_BUILT)
class FoundTracksAreFits(unittest.TestCase):
    """The clean fixture at o1, in the lowest momentum bin, against closed-form least squares that shares nothing with ACTS, and a second run for reproducibility."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.data_file, _ = generate(folder, "clean", NEGATIVE_STRATUM, PRODUCT_EVENTS)
        _, cls.record_file, product_file = find(folder, cls.data_file, "t07-found", PRODUCT_EVENTS)
        cls.document = native_product.parse_product(product_file.read_text(encoding="utf-8"))

    def test_each_found_track_is_the_least_squares_fit_of_its_hits(self):
        """kalman_refit.hpp's domain: the seed's q/p is a start only because the fit repeats from its own result. A prior left in the fit, or a seed's hits counted twice, fails here."""
        hits_of_event = [event["hits"] for event in fixture_files.iter_data_events(self.data_file)]
        tracks = [track for track in self.document["tracks"] if track["measurements"] == PLANES]
        self.assertGreaterEqual(len(tracks), ALL_HITS_KEPT_SHARE * PRODUCT_EVENTS * TRACKS_OF_LEVEL[0])
        keys = [track["key"] for track in tracks]
        states, sigmas = refit_tests.plane_one_arrays(self.document, keys)
        by_track = {}
        for state in self.document["states"]:
            by_track.setdefault(state["track_key"], []).append(state["hit_key"])
        hits_mm = numpy.array([refit_tests.hit_coordinates(hits_of_event[track["event_ordinal"]], by_track[track["key"]]) for track in tracks])
        reference_states, reference_sigmas, _ = refit_tests.least_squares_fit(hits_mm, states)
        print(f"FINDING-LEAST-SQUARES tracks {len(tracks)} largest state offset {numpy.abs((states - reference_states) / reference_sigmas).max():.5f} sigma", flush=True)
        self.assertEqual(refit_tests.agreement_defects(states, sigmas, reference_states, reference_sigmas), [])

    def test_a_second_run_gives_the_same_bytes(self):
        folder = Path(self.folder.name)
        _, second_record, _ = find(folder, self.data_file, "t07-found-again", PRODUCT_EVENTS)
        first = self.record_file.read_text(encoding="utf-8").replace("t07-found", "same")
        self.assertEqual(second_record.read_text(encoding="utf-8").replace("t07-found-again", "same"), first)


@unittest.skipUnless(BUILT, NOT_BUILT)
class TwoPlanesInAFieldFail(unittest.TestCase):
    """D1 stage 4 review, m5: planes 1 and 8 at 1 T measure no q/p, so the set fails as a track and stays in the product. Three planes are a measurement."""

    def test_two_planes_fail_and_three_do_not(self):
        driver = Path(BUILD_DIR) / "acts_tracking_driver"
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            hits = [(1, 0.0, 0.0), (4, 15.0, 3.0), (8, 35.0, 7.0)]
            data_file = folder / "hits.t07data"
            data_file.write_bytes(fixture_files.encode_data_file(HIT_SIGMA_MM, [hits]))
            sets = fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), [("two-planes", 0, 0.25, [0, 2]), ("three-planes", 0, 0.25, [0, 1, 2])])
            hit_sets_file, product_file = folder / "sets.hitsets", folder / "sets.product"
            hit_sets_file.write_text(sets, encoding="utf-8")
            run_program([driver, "refit", "--data-file", data_file, "--hit-sets", hit_sets_file, "--field-tesla", "1", "--product-id", "t07-planes", "--product-file", product_file])
            document = native_product.parse_product(product_file.read_text(encoding="utf-8"))
        tracks = {track["key"]: track for track in document["tracks"]}
        self.assertEqual((tracks["two-planes"]["status"], tracks["two-planes"]["failure_category"]), ("failed", "fit"))
        self.assertEqual(tracks["three-planes"]["status"], "fitted")


if __name__ == "__main__":
    unittest.main()
