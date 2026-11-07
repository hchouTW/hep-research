"""adapters/acts-tracking, the field step of T07 (t07-t09-task-sheets.md, Steps): the refit of a known hit set at section 4.1's 1 T.

Recipe reco.track.acts-kf-refit/1 (t04-values-v4.md section 8.1): truth-assisted, counted apart, never reported as finding. These are
development readings of block 1, not gate results: pass or fail waits for K09 (sheet, Acceptance), and tuning runs feed nothing
(section 2.2). Sections cited are of t04-values-v4.md.

The prior on q/p. kalman_refit.hpp states it and why; prior_defects holds the arithmetic. A prior of width s centred on the assumed value
moves a fit of width m by the share (m/s)^2 of its distance to that value and narrows a truth-centred pull to s / sqrt(s^2 + m^2). The old
prior, 10 % of q/p, gives the widths of D1 stage 2 review C-M1 at m = 0.00412 per GeV, 0.82 in [12, 24) GeV.

Expectations, fixed here before any ACTS run with a field. Nothing below reads ACTS:

- Closed form: pull centre 0, width 1, P(|pull| > 3) = 0.0027, mean chi2 = 16 - 5 = 11, in every momentum bin.
- PREDICTED tables: an independent numpy extended Kalman filter and smoother on the closed-form helix, and a Gauss-Newton least-squares
  fit that holds no prior at all. The filter reproduces job 7492427's chord row under the old prior, which it had never been fitted to.
  At 20,000 tracks per bin it read q/p sigma_68 1.004, 0.995, 0.997, 1.007 under the settled prior, against 1.000, 0.979, 0.938, 0.824
  under the old one.

Tolerances, fixed here before the first run, and they do not move after results (sheet, Stop):

- Pulls: PULL_Z = 4 design standard errors of section 5.1, n recorded, as R37 asks of a statistical check. Tracks of a clean event are
  independent in their smearing, so design se stands in for the gate's event bootstrap here. About 90 statistics at 6.3e-5 each: a
  correct fit stops this run at most 0.6 % of the time. In [12, 24) GeV the old prior misses by more than 6 limits.
- FIT_AGREEMENT_SIGMA 0.05 of a parameter's sigma, per track, against least squares: five times the filter's largest reading, 0.0105, as
  a largest reading grows with the sample; the stepper's 6e-6 mm is 3e-4 of a hit sigma. COVARIANCE_AGREEMENT 5e-3 of sigma, per track: a
  seventh of section 5.4's slack at the cap, 0.0356, against the filter's 2.7e-4.
- ASSUMPTION_SHIFT_SIGMA 0.02 of sigma per track for an assumed q/p 10 % off: five times the filter's 0.0037. The old prior moves q/p by
  a third of a sigma and more in [12, 24) GeV.

The development sample: clean fixture 7001, block 1 (section 3.2, tuning), strata 0, 3, 6, 9 (o1 in each momentum bin), 3,000 events each,
the size of section 3.2's clean runs, so 18,000 tracks per bin and 12,000 events in all. A known hit set does not depend on occupancy, so
o2 and o3 are left to the Freeze-B run. No evaluation block is read. The built tests need the T07 build job and skip without it; that job
counts a skip as a failure. Everything else runs anywhere in a few seconds. Each judge is driven with honest input and with one defect.
Run from the plugin root: python -m unittest tests.adapters.test_acts_refit_field -v
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "acts-tracking"
NATIVE = ADAPTER / "assets" / "native"
sys.path.insert(0, str(ADAPTER / "assets" / "fixture_tools"))

import acts_native_product as native_product  # noqa: E402
import t07_fixture_files as fixture_files  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402

BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
ZERO_FIELD_REFERENCE = os.environ.get("HEP_ACTS_TRACKING_ZERO_FIELD_REFERENCE", "")
DRIVER = Path(BUILD_DIR) / "acts_tracking_driver"
GENERATOR = Path(BUILD_DIR) / "t07_fixture_generator"
BUILT = bool(BUILD_DIR) and DRIVER.is_file() and GENERATOR.is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built program: this test needs the T07 build job, which runs it"

# Section 4.1.
STATED_SIGMA_Q_OVER_P = 0.00412
GEV_PER_TESLA_MM = 0.299792458e-3
FIELD_TESLA = 1.0
HIT_SIGMA_MM = 0.020
PLANE_X_MM = 50.0 * numpy.arange(8)
MOMENTUM_BIN_EDGES = (1.5, 3.0, 6.0, 12.0, 24.0)
VERTEX_X_MM = -100.0
VERTEX_U_HALF_MM, VERTEX_V_HALF_MM, SLOPE_HALF = 0.05, 30.0, 0.15
# kalman_refit.hpp, the start and the priors that do not change.
START_X_MM = -50.0
PRIOR_LOC_SIGMA_MM, PRIOR_ANGLE_SIGMA = 10.0, 0.1
SETTLED_PRIOR_PER_GEV = 1.0
OLD_RELATIVE_PRIOR = 0.1

# Section 5.1's design se at the largest population of any bin, 12,000 events of 36 tracks: no pull statistic can see less.
SMALLEST_DESIGN_ERROR = 0.962 / math.sqrt(12000 * 36)
WIDEST_BIN_IN_Q_OVER_P = 1.0 / MOMENTUM_BIN_EDGES[0] - 1.0 / MOMENTUM_BIN_EDGES[1]
WIDEST_SAFE_PRIOR_PER_GEV = 10.0  # the independent filter: sigma(q/p) 9e-4 off at 10, under SMALLEST_DESIGN_ERROR; 7e-2 off at 100

# Tolerances: the module text says why.
PULL_Z = 4.0
FIT_AGREEMENT_SIGMA = 0.05
COVARIANCE_AGREEMENT = 5e-3
ASSUMPTION_SHIFT_SIGMA = 0.02
ASSUMPTION_FACTOR = 1.1
ZERO_FIELD_AGREEMENT_SIGMA = 1e-6  # a straight-line fit holds no q/p, so only rounding through the smoother's inverse may differ
GAUSSIAN_TAIL_ABOVE_3 = 0.0026998

# Predictions fixed before any run. The first row is D1 stage 2 review C-M1's, the others the independent filter's.
PREDICTED_RMS_WIDTH_OLD_PRIOR = (0.996, 0.984, 0.941, 0.816)
PREDICTED_RMS_WIDTH_SETTLED_PRIOR = (1.000, 1.000, 1.000, 1.000)
# Largest relative error of the sagitta bias over cai_payload_probe.cpp's five tracks, 3 to 12 GeV, and its limit there.
PREDICTED_SAGITTA_ERROR_SETTLED, PREDICTED_SAGITTA_ERROR_OLD, SAGITTA_LIMIT = 0.0316, 0.2101, 0.10

CLEAN_BLOCK = 1
EVENTS_PER_BIN = 3000
STRATA_OF_BINS = (0, 3, 6, 9)  # 3 x momentum bin + occupancy level, section 3.2
LEAST_SQUARES_TRACKS_PER_BIN = 2000
SHIFTED_EVENTS_PER_BIN = 500
PARAMETER_NAMES = ("loc0", "loc1", "phi", "theta", "q/p")
COVARIANCE_DIAGONAL = (0, 6, 11, 15, 18, 20)  # the upper triangle of 6 x 6, row by row
FINITE_STEPS = numpy.array([1e-3, 1e-3, 1e-6, 1e-6, 1e-5])

PROBE_START_TRACKS = numpy.array([[0.02, 12.0, 0.13, -0.05, 3.0, 1.0], [-0.03, -20.0, -0.14, 0.13, 3.0, -1.0], [0.0, 25.0, 0.14, 0.13, 6.0, 1.0],
                                  [0.01, -8.0, 0.05, -0.14, 6.0, -1.0], [0.04, 3.0, -0.12, 0.09, 12.0, 1.0], [0.0, 30.0, 0.15, 0.15, 1.5, 1.0],
                                  [0.0, -30.0, -0.15, 0.15, 1.5, -1.0]])  # cai_refit_start_probe.cpp: u, v at x = -100 mm, slopes, p, charge


# ---- The judges. Each takes numbers and names what is wrong, so each is tested without a build.

def prior_shrink(prior_sigma, measurement_sigma=STATED_SIGMA_Q_OVER_P):
    """Share of the measurement kept by a Gaussian prior: s^2 / (s^2 + m^2). A truth-centred pull has width sqrt of this."""
    return prior_sigma ** 2 / (prior_sigma ** 2 + measurement_sigma ** 2)


def prior_defects(prior_sigma_per_gev: float) -> list:
    """kalman_refit.hpp's limits on the prior on q/p. R37: it may not constrain the mode. Section 5.1: no statistic may see it."""
    kept = prior_shrink(prior_sigma_per_gev)
    defects = []
    if 1.0 - math.sqrt(kept) > SMALLEST_DESIGN_ERROR:
        defects.append("narrows a pull")
    if 1.0 - kept > SMALLEST_DESIGN_ERROR:
        defects.append("hides a true bias")
    if STATED_SIGMA_Q_OVER_P * WIDEST_BIN_IN_Q_OVER_P / prior_sigma_per_gev ** 2 > SMALLEST_DESIGN_ERROR:
        defects.append("moves a pull with the assumed q/p")
    if prior_sigma_per_gev > WIDEST_SAFE_PRIOR_PER_GEV:
        defects.append("loses sigma(q/p) in the smoother")
    return defects


def field_gate_defects(driver_text: str, header_text: str, refit_text: str) -> list:
    """C-M1's gate, past the point where it held the field shut: a field opens only with the settled prior, and only the fixture's field."""
    defects = []
    if "if (field != 0.0 && field != t07::field_tesla) {" not in driver_text:
        defects.append("the driver takes a field the prior was not settled for")
    width = re.search(r"refit_prior_qop_sigma_per_gev = ([0-9.e+-]+);", header_text)
    if width is None:
        defects.append("no absolute prior on q/p")
    else:
        defects.extend(prior_defects(float(width.group(1))))
    if "prior(Acts::eBoundQOverP, Acts::eBoundQOverP) = refit_prior_qop_sigma_per_gev * refit_prior_qop_sigma_per_gev;" not in refit_text:
        defects.append("the fit does not use that prior")
    return defects


def trimmed_centre(values) -> float:
    """Section 5.1: trimmed mean, 10 % cut from each side."""
    ordered = numpy.sort(values)
    cut = int(0.1 * len(ordered))
    return float(ordered[cut:len(ordered) - cut].mean())


def sigma_68(values) -> float:
    """Section 5.1: half the central 68.27 % interval."""
    lower, upper = numpy.quantile(values, [0.5 - 0.3413447, 0.5 + 0.3413447])
    return float(0.5 * (upper - lower))


def pull_reading(pulls) -> dict:
    return {"count": len(pulls), "centre": trimmed_centre(pulls), "width": sigma_68(pulls), "mean": float(numpy.mean(pulls)), "rms": float(numpy.sqrt(numpy.mean(numpy.square(pulls)))),
            "tail": float(numpy.mean(numpy.abs(pulls) > 3.0))}


def pull_defects(reading: dict) -> list:
    """Centre 0, width 1, Gaussian tail, each within PULL_Z design standard errors at this count."""
    count = reading["count"]
    defects = []
    if abs(reading["centre"]) > PULL_Z * 1.03 / math.sqrt(count):
        defects.append(f"centre {reading['centre']:.4f}")
    if abs(reading["width"] - 1.0) > PULL_Z * 0.962 / math.sqrt(count):
        defects.append(f"width {reading['width']:.4f}")
    tail_limit = PULL_Z * math.sqrt(GAUSSIAN_TAIL_ABOVE_3 * (1.0 - GAUSSIAN_TAIL_ABOVE_3) / count)
    if abs(reading["tail"] - GAUSSIAN_TAIL_ABOVE_3) > tail_limit:
        defects.append(f"tail {reading['tail']:.5f}")
    return defects


def chi2_defects(chi2_values) -> list:
    """16 measurements, 5 fitted parameters and a prior that adds nothing: chi2 of 11 degrees of freedom, variance 22."""
    mean = float(numpy.mean(chi2_values))
    return [f"mean chi2 {mean:.3f}"] if abs(mean - 11.0) > PULL_Z * math.sqrt(22.0 / len(chi2_values)) else []


def agreement_defects(states, sigmas, reference_states, reference_sigmas) -> list:
    """A fit against a least-squares fit of the same hits, track by track."""
    defects = []
    offset = float(numpy.abs((states - reference_states) / reference_sigmas).max())
    if offset > FIT_AGREEMENT_SIGMA:
        defects.append(f"state {offset:.4f} sigma from least squares")
    covariance_offset = float(numpy.abs(sigmas / reference_sigmas - 1.0).max())
    if covariance_offset > COVARIANCE_AGREEMENT:
        defects.append(f"sigma {covariance_offset:.5f} from least squares")
    return defects


def assumption_defects(states, sigmas, shifted_states, shifted_sigmas) -> list:
    """The assumed q/p is the start, not a constraint: moving it moves no state and no sigma."""
    defects = []
    moved = float(numpy.abs((shifted_states - states) / sigmas).max())
    if moved > ASSUMPTION_SHIFT_SIGMA:
        defects.append(f"state moved {moved:.4f} sigma")
    resized = float(numpy.abs(shifted_sigmas / sigmas - 1.0).max())
    if resized > COVARIANCE_AGREEMENT:
        defects.append(f"sigma moved {resized:.5f}")
    return defects


def counted_apart_defects(document: dict) -> list:
    """Sheet, Acceptance; section 8.1: a refit is truth-assisted, counted apart, never finding. At 1 T its q/p is measured, and says so."""
    header = document["header"]
    expected = {"recipe": "reco.track.acts-kf-refit/1", "stage": "refit-known-hit-set", "evidence_class": "truth-assisted", "qop_status": "measured", "field_tesla": FIELD_TESLA}
    defects = [f"{name} is {header[name]}" for name, value in expected.items() if header[name] != value]
    if header["start_prior"][3] != SETTLED_PRIOR_PER_GEV:
        defects.append(f"start_prior holds q/p width {header['start_prior'][3]}")
    if native_product.fit_summary(document)["reported_as_finding"] is not False:
        defects.append("reported as finding")
    return defects


def track_defects(tracks, expected_count: int) -> list:
    """Every set of the clean fixture is fitted in full: eight hits, no hole, no outlier. A lost fit stays in the denominator."""
    defects = [] if len(tracks) == expected_count else [f"{len(tracks)} tracks of {expected_count}"]
    incomplete = [track["key"] for track in tracks if (track["status"], track["measurements"], track["holes"], track["outliers"], track["measured_coordinates"]) != ("fitted", 8, 0, 0, 16)]
    return defects + ([f"{len(incomplete)} tracks not fitted in full, first {incomplete[0]}"] if incomplete else [])


def without_chi2(records) -> list:
    return [{name: value for name, value in record.items() if name != "chi2"} for record in records]


def zero_field_defects(reference: dict, document: dict) -> list:
    """The settled prior moves nothing at zero field but q/p's own width. Reference: job 7492427's product. Time carries q/p's width, so it is left out."""
    defects = []
    for name in reference["header"]:
        if name != "start_prior" and reference["header"][name] != document["header"][name]:
            defects.append(f"header {name} moved")
    if [value for index, value in enumerate(reference["header"]["start_prior"]) if index != 3] != [value for index, value in enumerate(document["header"]["start_prior"]) if index != 3]:
        defects.append("start_prior moved outside q/p")
    for collection in ("states", "tracks"):
        if without_chi2(reference[collection]) != without_chi2(document[collection]):
            defects.append(f"{collection} moved")
        elif any(abs(earlier["chi2"] - current["chi2"]) > ZERO_FIELD_AGREEMENT_SIGMA * (1.0 + earlier["chi2"]) for earlier, current in zip(reference[collection], document[collection])):
            defects.append(f"chi2 of {collection} moved")
    if len(reference["parameters"]) != len(document["parameters"]):
        return defects + ["parameter records lost"]
    entries = [(row, column) for row in range(6) for column in range(row, 6)]
    for old_record, new_record in zip(reference["parameters"], document["parameters"]):
        if (old_record["track_key"], old_record["state_index"], old_record["state_type"]) != (new_record["track_key"], new_record["state_index"], new_record["state_type"]):
            return defects + ["parameter records reordered"]
        sigmas = [math.sqrt(old_record["covariance"][index]) for index in COVARIANCE_DIAGONAL]
        for index in range(5):
            scale = sigmas[index] if index != 4 else abs(old_record["parameters"][4])
            if abs(old_record["parameters"][index] - new_record["parameters"][index]) > ZERO_FIELD_AGREEMENT_SIGMA * scale:
                defects.append(f"{PARAMETER_NAMES[index]} moved in {old_record['track_key']}")
        for entry, (row, column) in enumerate(entries):
            if max(row, column) < 4 and abs(old_record["covariance"][entry] - new_record["covariance"][entry]) > ZERO_FIELD_AGREEMENT_SIGMA * sigmas[row] * sigmas[column]:
                defects.append(f"covariance {row} {column} moved in {old_record['track_key']}")
    return defects


# ---- The independent filter and least-squares fit: closed-form helix, numpy only, no ACTS and no stepper.

def helix_to_plane(position_mm, phi, theta, q_over_p, plane_x_mm):
    """A track in a field along z: T_z is constant and phi falls at (q/p) k B per unit path. No division by q/p, which a filter may take through 0."""
    distance_mm = plane_x_mm - position_mm[:, 0]
    transverse = numpy.sin(theta)
    end_phi = numpy.arcsin(numpy.sin(phi) - q_over_p * GEV_PER_TESLA_MM * FIELD_TESLA * distance_mm / transverse)
    middle_phi = 0.5 * (phi + end_phi)
    half_turn = 0.5 * (phi - end_phi)
    arc_over_chord = numpy.where(numpy.abs(half_turn) < 1e-8, 1.0 + half_turn ** 2 / 6.0, half_turn / numpy.where(half_turn == 0.0, 1.0, numpy.sin(half_turn)))
    loc0_mm = position_mm[:, 1] + distance_mm * numpy.tan(middle_phi)
    loc1_mm = position_mm[:, 2] + numpy.cos(theta) / transverse * distance_mm / numpy.cos(middle_phi) * arc_over_chord
    return loc0_mm, loc1_mm, end_phi


def unit_direction(phi, theta):
    return numpy.stack([numpy.cos(phi) * numpy.sin(theta), numpy.sin(phi) * numpy.sin(theta), numpy.cos(theta)], -1)


def plane_frame(plane_x_mm: float, count: int) -> tuple:
    origin = numpy.zeros((count, 3))
    origin[:, 0] = plane_x_mm
    return origin, numpy.tile([0.0, 1.0, 0.0], (count, 1)), numpy.tile([0.0, 0.0, 1.0], (count, 1))


def curvilinear_frame(position_mm, phi, theta) -> tuple:
    tangent = unit_direction(phi, theta)
    axis_u = numpy.stack([-tangent[:, 1], tangent[:, 0], numpy.zeros_like(phi)], -1)
    axis_u /= numpy.linalg.norm(axis_u, axis=1, keepdims=True)
    return position_mm, axis_u, numpy.cross(tangent, axis_u)


def transported(state, frame, plane_x_mm: float):
    """Bound parameters (loc0, loc1, phi, theta, q/p) in a frame to those on a plane."""
    origin, axis_u, axis_v = frame
    position_mm = origin + state[:, 0:1] * axis_u + state[:, 1:2] * axis_v
    loc0_mm, loc1_mm, end_phi = helix_to_plane(position_mm, state[:, 2], state[:, 3], state[:, 4], plane_x_mm)
    return numpy.stack([loc0_mm, loc1_mm, end_phi, state[:, 3], state[:, 4]], -1)


def transport_jacobian(state, frame, plane_x_mm: float):
    jacobian = numpy.zeros((len(state), 5, 5))
    for column in range(5):
        step = numpy.zeros(5)
        step[column] = FINITE_STEPS[column]
        jacobian[:, :, column] = (transported(state + step, frame, plane_x_mm) - transported(state - step, frame, plane_x_mm)) / (2.0 * FINITE_STEPS[column])
    return jacobian


def independent_filter(hits_mm, start_mm, start_direction, q_over_p, prior_sigma, measured_planes=None) -> dict:
    """One pass and a smoother, as a plain Kalman refit: the start, its prior, an update per measured plane. All tracks at once."""
    count = len(hits_mm)
    measured = numpy.ones(8, bool) if measured_planes is None else measured_planes
    phi, theta = numpy.arctan2(start_direction[:, 1], start_direction[:, 0]), numpy.arccos(start_direction[:, 2])
    state = numpy.stack([numpy.zeros(count), numpy.zeros(count), phi, theta, q_over_p], -1)
    covariance = numpy.zeros((count, 5, 5))
    covariance[:, 0, 0] = covariance[:, 1, 1] = PRIOR_LOC_SIGMA_MM ** 2
    covariance[:, 2, 2] = covariance[:, 3, 3] = PRIOR_ANGLE_SIGMA ** 2
    covariance[:, 4, 4] = prior_sigma ** 2
    frame = curvilinear_frame(start_mm, phi, theta)
    predicted, predicted_covariance, filtered, filtered_covariance, jacobians = [], [], [], [], []
    chi2 = numpy.zeros(count)
    for plane, plane_x_mm in enumerate(PLANE_X_MM):
        jacobian = transport_jacobian(state, frame, plane_x_mm)
        state = transported(state, frame, plane_x_mm)
        covariance = jacobian @ covariance @ jacobian.transpose(0, 2, 1)
        predicted.append(state)
        predicted_covariance.append(covariance)
        jacobians.append(jacobian)
        if measured[plane]:
            inverse_residual_covariance = numpy.linalg.inv(covariance[:, :2, :2] + numpy.eye(2) * HIT_SIGMA_MM ** 2)
            gain = covariance[:, :, :2] @ inverse_residual_covariance
            residual = hits_mm[:, plane, :] - state[:, :2]
            chi2 += numpy.einsum("ni,nij,nj->n", residual, inverse_residual_covariance, residual)
            state = state + numpy.einsum("nij,nj->ni", gain, residual)
            covariance = covariance - gain @ covariance[:, :2, :]
        filtered.append(state)
        filtered_covariance.append(covariance)
        frame = plane_frame(plane_x_mm, count)
    smoothed, smoothed_covariance = [None] * 8, [None] * 8
    smoothed[7], smoothed_covariance[7] = filtered[7], filtered_covariance[7]
    for plane in range(6, -1, -1):
        smoother_gain = filtered_covariance[plane] @ jacobians[plane + 1].transpose(0, 2, 1) @ numpy.linalg.inv(predicted_covariance[plane + 1])
        smoothed[plane] = filtered[plane] + numpy.einsum("nij,nj->ni", smoother_gain, smoothed[plane + 1] - predicted[plane + 1])
        smoothed_covariance[plane] = filtered_covariance[plane] + smoother_gain @ (smoothed_covariance[plane + 1] - predicted_covariance[plane + 1]) @ smoother_gain.transpose(0, 2, 1)
    return {"smoothed": smoothed, "smoothed_covariance": smoothed_covariance, "chi2": chi2}


def diagonal_sigmas(covariance):
    return numpy.sqrt(numpy.einsum("nii->ni", covariance))


def chord_start(hits_mm) -> tuple:
    """cai_refit_start_probe.cpp's old start."""
    slope_u, slope_v = (hits_mm[:, 7, 0] - hits_mm[:, 0, 0]) / PLANE_X_MM[7], (hits_mm[:, 7, 1] - hits_mm[:, 0, 1]) / PLANE_X_MM[7]
    position_mm = numpy.stack([numpy.full(len(slope_u), START_X_MM), hits_mm[:, 0, 0] + slope_u * START_X_MM, hits_mm[:, 0, 1] + slope_v * START_X_MM], -1)
    direction = numpy.stack([numpy.ones_like(slope_u), slope_u, slope_v], -1)
    return position_mm, direction / numpy.linalg.norm(direction, axis=1, keepdims=True)


def curve_start(hits_mm, q_over_p) -> tuple:
    """KalmanRefit::start_of: the curve through the first and last hit with the assumed q/p."""
    slope_u, slope_v = (hits_mm[:, 7, 0] - hits_mm[:, 0, 0]) / PLANE_X_MM[7], (hits_mm[:, 7, 1] - hits_mm[:, 0, 1]) / PLANE_X_MM[7]
    bending_per_mm = q_over_p * GEV_PER_TESLA_MM * FIELD_TESLA
    slope_norm = numpy.sqrt(1.0 + slope_u ** 2 + slope_v ** 2)
    half_u = -0.5 * bending_per_mm * slope_norm * (1.0 + slope_u ** 2)
    half_v = -0.5 * bending_per_mm * slope_norm * slope_u * slope_v
    from_first, from_last = START_X_MM, START_X_MM - PLANE_X_MM[7]
    position_mm = numpy.stack([numpy.full(len(slope_u), START_X_MM), hits_mm[:, 0, 0] + slope_u * from_first + half_u * from_first * from_last,
                               hits_mm[:, 0, 1] + slope_v * from_first + half_v * from_first * from_last], -1)
    direction = numpy.stack([numpy.ones_like(slope_u), slope_u + half_u * (from_first + from_last), slope_v + half_v * (from_first + from_last)], -1)
    return position_mm, direction / numpy.linalg.norm(direction, axis=1, keepdims=True)


def crossings_from_vertex(vertex_u_mm, vertex_v_mm, slope_u, slope_v, q_over_p):
    """Truth at every plane, (count, 8, 4): loc0, loc1, phi, theta."""
    direction = numpy.stack([numpy.ones_like(slope_u), slope_u, slope_v], -1)
    direction /= numpy.linalg.norm(direction, axis=1, keepdims=True)
    phi, theta = numpy.arctan2(direction[:, 1], direction[:, 0]), numpy.arccos(direction[:, 2])
    position_mm = numpy.stack([numpy.full_like(slope_u, VERTEX_X_MM), vertex_u_mm, vertex_v_mm], -1)
    crossings = numpy.zeros((len(slope_u), 8, 4))
    for plane, plane_x_mm in enumerate(PLANE_X_MM):
        loc0_mm, loc1_mm, end_phi = helix_to_plane(position_mm, phi, theta, q_over_p, plane_x_mm)
        crossings[:, plane] = numpy.stack([loc0_mm, loc1_mm, end_phi, theta], -1)
    return crossings


def simulated_tracks(generator, momentum_bin: int, count: int) -> tuple:
    """Section 4.1's tracks by the closed form, for this module's numpy checks only. Never a fixture event."""
    momentum = numpy.exp(generator.uniform(math.log(MOMENTUM_BIN_EDGES[momentum_bin]), math.log(MOMENTUM_BIN_EDGES[momentum_bin + 1]), count))
    q_over_p = generator.choice([-1.0, 1.0], count) / momentum
    crossings = crossings_from_vertex(generator.uniform(-VERTEX_U_HALF_MM, VERTEX_U_HALF_MM, count), generator.uniform(-VERTEX_V_HALF_MM, VERTEX_V_HALF_MM, count),
                                      generator.uniform(-SLOPE_HALF, SLOPE_HALF, count), generator.uniform(-SLOPE_HALF, SLOPE_HALF, count), q_over_p)
    hits_mm = crossings[:, :, :2] + generator.normal(0.0, HIT_SIGMA_MM, (count, 8, 2))
    return q_over_p, crossings, hits_mm


def hits_of_state(state):
    """The helix through a plane-1 state, at all eight planes."""
    count = len(state)
    position_mm = numpy.stack([numpy.zeros(count), state[:, 0], state[:, 1]], -1)
    hits_mm = numpy.zeros((count, 8, 2))
    hits_mm[:, 0] = state[:, :2]
    for plane in range(1, 8):
        loc0_mm, loc1_mm, _ = helix_to_plane(position_mm, state[:, 2], state[:, 3], state[:, 4], PLANE_X_MM[plane])
        hits_mm[:, plane] = numpy.stack([loc0_mm, loc1_mm], -1)
    return hits_mm


def least_squares_jacobian(state):
    jacobian = numpy.zeros((len(state), 16, 5))
    for column in range(5):
        step = numpy.zeros(5)
        step[column] = FINITE_STEPS[column]
        jacobian[:, :, column] = ((hits_of_state(state + step) - hits_of_state(state - step)) / (2.0 * FINITE_STEPS[column])).reshape(len(state), 16)
    return jacobian


def least_squares_fit(hits_mm, first_state, iterations: int = 4) -> tuple:
    """Gauss-Newton on the sixteen coordinates, with no prior: plane-1 state, sigmas, chi2."""
    state = first_state.copy()
    for _ in range(iterations):
        jacobian = least_squares_jacobian(state)
        residual = (hits_mm - hits_of_state(state)).reshape(len(state), 16)
        state = state + numpy.linalg.solve(jacobian.transpose(0, 2, 1) @ jacobian, numpy.einsum("nji,nj->ni", jacobian, residual)[..., None])[..., 0]
    jacobian = least_squares_jacobian(state)
    covariance = HIT_SIGMA_MM ** 2 * numpy.linalg.inv(jacobian.transpose(0, 2, 1) @ jacobian)
    residual = (hits_mm - hits_of_state(state)).reshape(len(state), 16)
    return state, diagonal_sigmas(covariance), (residual ** 2).sum(1) / HIT_SIGMA_MM ** 2


def truth_state(crossings, q_over_p):
    return numpy.concatenate([crossings[:, 0, :], q_over_p[:, None]], 1)


def filter_at_plane_one(hits_mm, q_over_p, prior_sigma) -> tuple:
    start_mm, direction = curve_start(hits_mm, q_over_p)
    result = independent_filter(hits_mm, start_mm, direction, q_over_p, prior_sigma)
    return result["smoothed"][0], diagonal_sigmas(result["smoothed_covariance"][0]), result["chi2"]


class ThePriorIsSettled(unittest.TestCase):
    """Replaces the guard that held the field shut until the prior moved (D1 stage 2 review, C-M1). The real test is FieldOnRefit below."""

    def setUp(self):
        self.driver = (NATIVE / "acts_tracking_driver.cpp").read_text(encoding="utf-8")
        self.header = (NATIVE / "kalman_refit.hpp").read_text(encoding="utf-8")
        self.refit = (NATIVE / "kalman_refit.cpp").read_text(encoding="utf-8")

    def test_the_sources_hold_the_settled_prior_and_the_gate(self):
        self.assertEqual(field_gate_defects(self.driver, self.header, self.refit), [])
        self.assertEqual(float(re.search(r"refit_prior_qop_sigma_per_gev = ([0-9.e+-]+);", self.header).group(1)), SETTLED_PRIOR_PER_GEV)

    def test_a_field_open_to_any_value_fails(self):
        opened = self.driver.replace("if (field != 0.0 && field != t07::field_tesla) {", "if (false) {")
        self.assertEqual(field_gate_defects(opened, self.header, self.refit), ["the driver takes a field the prior was not settled for"])

    def test_the_old_relative_prior_fails(self):
        old = self.header.replace("refit_prior_qop_sigma_per_gev = 1.0;", "refit_prior_relative_qop_sigma = 0.1;")
        self.assertEqual(field_gate_defects(self.driver, old, self.refit), ["no absolute prior on q/p"])

    def test_a_fit_that_scales_the_prior_with_the_assumed_value_fails(self):
        scaled = self.refit.replace("= refit_prior_qop_sigma_per_gev * refit_prior_qop_sigma_per_gev;", "= refit_prior_qop_sigma_per_gev * std::abs(hit_set.assumed_q_over_p);")
        self.assertEqual(field_gate_defects(self.driver, self.header, scaled), ["the fit does not use that prior"])

    def test_a_prior_too_narrow_or_too_wide_fails(self):
        self.assertEqual(prior_defects(SETTLED_PRIOR_PER_GEV), [])
        self.assertEqual(prior_defects(0.5), ["moves a pull with the assumed q/p"])
        self.assertEqual(prior_defects(0.1 / 24.0), ["narrows a pull", "hides a true bias", "moves a pull with the assumed q/p"])
        self.assertEqual(prior_defects(100.0), ["loses sigma(q/p) in the smoother"])

    def test_the_lower_limit_is_the_one_the_refit_header_states(self):
        self.assertAlmostEqual(SMALLEST_DESIGN_ERROR, 0.00146, delta=1e-5)
        self.assertAlmostEqual(math.sqrt(STATED_SIGMA_Q_OVER_P * WIDEST_BIN_IN_Q_OVER_P / SMALLEST_DESIGN_ERROR), 0.97, delta=0.005)
        self.assertAlmostEqual(1.0 - prior_shrink(1.0), 1.7e-5, delta=1e-6)
        self.assertAlmostEqual(1.0 - math.sqrt(prior_shrink(1.0)), 8.5e-6, delta=1e-7)


class GaussianArithmetic(unittest.TestCase):
    def test_the_old_prior_gives_the_review_table(self):
        for momentum_bin, expected in enumerate(PREDICTED_RMS_WIDTH_OLD_PRIOR):
            momentum = numpy.exp(numpy.linspace(math.log(MOMENTUM_BIN_EDGES[momentum_bin]), math.log(MOMENTUM_BIN_EDGES[momentum_bin + 1]), 2001))
            with self.subTest(momentum_bin=momentum_bin):
                self.assertAlmostEqual(math.sqrt(prior_shrink(OLD_RELATIVE_PRIOR / momentum).mean()), expected, delta=2e-3)
        self.assertAlmostEqual(math.sqrt(prior_shrink(OLD_RELATIVE_PRIOR / 24.0)), 0.71, delta=5e-3)
        self.assertAlmostEqual(prior_shrink(OLD_RELATIVE_PRIOR / 24.0), 0.51, delta=5e-3)

    def test_the_settled_prior_is_flat_in_momentum(self):
        self.assertAlmostEqual(math.sqrt(prior_shrink(SETTLED_PRIOR_PER_GEV)), 1.0, delta=1e-5)

    def test_section_4_1_sigma_is_the_least_squares_sigma(self):
        """A straight fast track at zero slope: 0.00412 per GeV, with no filter in the way."""
        state = numpy.array([[0.0, 0.0, 0.0, math.pi / 2.0, 1.0 / 1000.0]])
        jacobian = least_squares_jacobian(state)
        sigmas = diagonal_sigmas(HIT_SIGMA_MM ** 2 * numpy.linalg.inv(jacobian.transpose(0, 2, 1) @ jacobian))
        self.assertAlmostEqual(sigmas[0, 4], STATED_SIGMA_Q_OVER_P, delta=5e-6)


class IndependentFilter(unittest.TestCase):
    """What the filter says before any ACTS run with a field. Fixed seeds, so these are repeatable."""

    def probe_tracks(self) -> tuple:
        vertex_u, vertex_v, slope_u, slope_v, momentum, charge = PROBE_START_TRACKS.T
        q_over_p = charge / momentum
        return q_over_p, crossings_from_vertex(vertex_u, vertex_v, slope_u, slope_v, q_over_p)[:, :, :2]

    def chord_row(self, prior_sigma) -> tuple:
        q_over_p, hits_mm = self.probe_tracks()
        start_mm, direction = chord_start(hits_mm)
        whole = independent_filter(hits_mm, start_mm, direction, q_over_p, prior_sigma)
        measured = numpy.ones(8, bool)
        measured[3] = False
        left_out = independent_filter(hits_mm, start_mm, direction, q_over_p, prior_sigma, measured)
        residual = numpy.abs(hits_mm[:, 3, :] - left_out["smoothed"][3][:, :2]).max()
        return whole["chi2"].max(), numpy.abs(whole["smoothed"][0][:, 4] - q_over_p).max(), residual

    def test_it_reproduces_job_7492427_under_the_old_prior(self):
        q_over_p, _ = self.probe_tracks()
        chi2, q_over_p_error, residual = self.chord_row(OLD_RELATIVE_PRIOR * numpy.abs(q_over_p))
        self.assertAlmostEqual(chi2 / 0.401322, 1.0, delta=0.005)
        self.assertAlmostEqual(q_over_p_error / 1.04994e-3, 1.0, delta=0.005)
        self.assertAlmostEqual(residual / 1.41049e-3, 1.0, delta=0.005)

    def test_the_numbers_in_the_start_probe_are_this_filters(self):
        source = (NATIVE / "cai_refit_start_probe.cpp").read_text(encoding="utf-8")
        chi2, q_over_p_error, residual = self.chord_row(numpy.full(len(PROBE_START_TRACKS), SETTLED_PRIOR_PER_GEV))
        for name, value in (("chord.chi2", chi2), ("chord.q_over_p_error", q_over_p_error), ("chord.left_out_residual", residual)):
            with self.subTest(name=name):
                self.assertAlmostEqual(float(re.search(r"near_share\(" + re.escape(name) + r", ([0-9.e+-]+)\)", source).group(1)) / value, 1.0, delta=1e-4)

    def test_pull_width_against_momentum(self):
        generator = numpy.random.default_rng(7001)
        limit = PULL_Z / math.sqrt(2.0 * 4000)
        for momentum_bin in range(4):
            q_over_p, crossings, hits_mm = simulated_tracks(generator, momentum_bin, 4000)
            truth = truth_state(crossings, q_over_p)
            for prior_sigma, expected, label in ((numpy.full_like(q_over_p, SETTLED_PRIOR_PER_GEV), PREDICTED_RMS_WIDTH_SETTLED_PRIOR, "settled"),
                                                 (OLD_RELATIVE_PRIOR * numpy.abs(q_over_p), PREDICTED_RMS_WIDTH_OLD_PRIOR, "old")):
                states, sigmas, _ = filter_at_plane_one(hits_mm, q_over_p, prior_sigma)
                pulls = (states[:, 4] - truth[:, 4]) / sigmas[:, 4]
                with self.subTest(momentum_bin=momentum_bin, prior=label):
                    self.assertAlmostEqual(float(numpy.sqrt(numpy.mean(pulls ** 2))), expected[momentum_bin], delta=limit)

    def test_a_correct_fit_passes_every_judge_and_the_old_prior_does_not(self):
        generator = numpy.random.default_rng(7002)
        q_over_p, crossings, hits_mm = simulated_tracks(generator, 3, 2000)
        reference_states, reference_sigmas, _ = least_squares_fit(hits_mm, truth_state(crossings, q_over_p))
        settled = numpy.full_like(q_over_p, SETTLED_PRIOR_PER_GEV)
        old = OLD_RELATIVE_PRIOR * numpy.abs(q_over_p)
        states, sigmas, chi2 = filter_at_plane_one(hits_mm, q_over_p, settled)
        self.assertEqual(agreement_defects(states, sigmas, reference_states, reference_sigmas), [])
        self.assertEqual(chi2_defects(chi2), [])
        shifted_states, shifted_sigmas, _ = filter_at_plane_one(hits_mm, ASSUMPTION_FACTOR * q_over_p, settled)
        self.assertEqual(assumption_defects(states, sigmas, shifted_states, shifted_sigmas), [])
        old_states, old_sigmas, _ = filter_at_plane_one(hits_mm, q_over_p, old)
        self.assertEqual(len(agreement_defects(old_states, old_sigmas, reference_states, reference_sigmas)), 2)
        old_shifted_states, old_shifted_sigmas, _ = filter_at_plane_one(hits_mm, ASSUMPTION_FACTOR * q_over_p, ASSUMPTION_FACTOR * old)
        self.assertEqual(len(assumption_defects(old_states, old_sigmas, old_shifted_states, old_shifted_sigmas)), 2)

    def test_the_lowest_bin_holds_the_limits_on_an_assumption_too(self):
        generator = numpy.random.default_rng(7003)
        q_over_p, crossings, hits_mm = simulated_tracks(generator, 0, 2000)
        settled = numpy.full_like(q_over_p, SETTLED_PRIOR_PER_GEV)
        states, sigmas, _ = filter_at_plane_one(hits_mm, q_over_p, settled)
        reference_states, reference_sigmas, _ = least_squares_fit(hits_mm, truth_state(crossings, q_over_p))
        self.assertEqual(agreement_defects(states, sigmas, reference_states, reference_sigmas), [])
        shifted_states, shifted_sigmas, _ = filter_at_plane_one(hits_mm, ASSUMPTION_FACTOR * q_over_p, settled)
        self.assertEqual(assumption_defects(states, sigmas, shifted_states, shifted_sigmas), [])

    def test_a_far_wider_prior_loses_the_covariance(self):
        """WIDEST_SAFE_PRIOR_PER_GEV: the upper limit is a float64 one, and this filter shows it."""
        generator = numpy.random.default_rng(7004)
        q_over_p, crossings, hits_mm = simulated_tracks(generator, 0, 1000)
        _, reference_sigmas, _ = least_squares_fit(hits_mm, truth_state(crossings, q_over_p))
        offsets = {}
        for prior_sigma in (SETTLED_PRIOR_PER_GEV, WIDEST_SAFE_PRIOR_PER_GEV, 100.0):
            _, sigmas, _ = filter_at_plane_one(hits_mm, q_over_p, numpy.full_like(q_over_p, prior_sigma))
            offsets[prior_sigma] = float(numpy.abs(sigmas[:, 4] / reference_sigmas[:, 4] - 1.0).max())
        self.assertLess(offsets[SETTLED_PRIOR_PER_GEV], 5e-4)
        self.assertLess(offsets[WIDEST_SAFE_PRIOR_PER_GEV], SMALLEST_DESIGN_ERROR)
        self.assertGreater(offsets[100.0], COVARIANCE_AGREEMENT)

    def sagitta_error(self, prior_of) -> float:
        tracks = PROBE_START_TRACKS[:5]
        vertex_u, vertex_v, slope_u, slope_v, momentum, charge = tracks.T
        q_over_p = charge / momentum
        hits_mm = crossings_from_vertex(vertex_u, vertex_v, slope_u, slope_v, q_over_p)[:, :, :2].copy()
        expected_bias = 5.0 * STATED_SIGMA_Q_OVER_P
        curvature_per_mm = expected_bias * GEV_PER_TESLA_MM * FIELD_TESLA / 2.0
        hits_mm[:, :, 0] -= curvature_per_mm * ((PLANE_X_MM - 175.0) ** 2 - 13125.0)
        states, _, _ = filter_at_plane_one(hits_mm, q_over_p, prior_of(q_over_p))
        return float(numpy.abs((states[:, 4] - q_over_p - expected_bias) / expected_bias).max())

    def test_the_sagitta_mode_stays_unconstrained(self):
        """R37, CAI-T07-4: cai_payload_probe.cpp's line now reads every momentum, at its unchanged limit, and the old prior fails it."""
        settled = self.sagitta_error(lambda q_over_p: numpy.full_like(q_over_p, SETTLED_PRIOR_PER_GEV))
        old = self.sagitta_error(lambda q_over_p: OLD_RELATIVE_PRIOR * numpy.abs(q_over_p))
        self.assertAlmostEqual(settled, PREDICTED_SAGITTA_ERROR_SETTLED, delta=5e-4)
        self.assertAlmostEqual(old, PREDICTED_SAGITTA_ERROR_OLD, delta=5e-4)
        self.assertLess(settled, SAGITTA_LIMIT)
        self.assertGreater(old, SAGITTA_LIMIT)


class JudgesFailOnOneDefect(unittest.TestCase):
    def setUp(self):
        self.pulls = numpy.random.default_rng(7005).normal(0.0, 1.0, 18000)

    def test_honest_pulls_pass(self):
        self.assertEqual(pull_defects(pull_reading(self.pulls)), [])

    def test_a_narrowed_pull_fails_on_width(self):
        self.assertEqual(len(pull_defects(pull_reading(0.82 * self.pulls))), 2)  # the tail goes too
        self.assertIn("width", pull_defects(pull_reading(0.94 * self.pulls))[0])

    def test_a_shifted_pull_fails_on_centre(self):
        self.assertIn("centre", pull_defects(pull_reading(self.pulls + 0.05))[0])

    def test_a_tail_of_one_percent_fails_on_tail(self):
        tailed = self.pulls.copy()
        tailed[:180] = 20.0
        self.assertIn("tail", pull_defects(pull_reading(tailed))[-1])

    def test_a_bias_that_cancels_between_charges_shows_per_charge(self):
        """Section 8.2: a charge-dependent bias of plus or minus 0.40 cancels in the mixed sample."""
        half = len(self.pulls) // 2
        biased = numpy.concatenate([self.pulls[:half] + 0.40, self.pulls[half:] - 0.40])
        self.assertIn("centre", pull_defects(pull_reading(biased[:half]))[0])
        self.assertIn("centre", pull_defects(pull_reading(biased[half:]))[0])

    def test_chi2_reads_its_mean(self):
        chi2_values = numpy.random.default_rng(7006).chisquare(11, 18000)
        self.assertEqual(chi2_defects(chi2_values), [])
        self.assertEqual(len(chi2_defects(numpy.random.default_rng(7006).chisquare(12, 18000))), 1)

    def test_agreement_fails_on_one_track(self):
        states, sigmas = numpy.zeros((10, 5)), numpy.ones((10, 5))
        moved = states.copy()
        moved[3, 4] = 0.06
        resized = sigmas.copy()
        resized[3, 0] = 1.006
        self.assertEqual(agreement_defects(states, sigmas, states, sigmas), [])
        self.assertEqual(len(agreement_defects(moved, sigmas, states, sigmas)), 1)
        self.assertEqual(len(agreement_defects(states, resized, states, sigmas)), 1)

    def test_an_assumption_that_moves_one_track_fails(self):
        states, sigmas = numpy.zeros((10, 5)), numpy.ones((10, 5))
        moved = states.copy()
        moved[7, 4] = 0.03
        self.assertEqual(assumption_defects(states, sigmas, states, sigmas), [])
        self.assertEqual(len(assumption_defects(states, sigmas, moved, sigmas)), 1)

    def honest_document(self) -> dict:
        return {"header": {"recipe": "reco.track.acts-kf-refit/1", "stage": "refit-known-hit-set", "evidence_class": "truth-assisted", "qop_status": "measured",
                           "field_tesla": 1.0, "start_prior": [-50.0, 10.0, 0.1, 1.0, 1.0]}, "tracks": []}

    def test_a_refit_stays_counted_apart(self):
        self.assertEqual(counted_apart_defects(self.honest_document()), [])
        for name, wrong in (("evidence_class", "data-side"), ("stage", "finding"), ("recipe", "reco.track.acts-ckf-planar/1"), ("qop_status", "assumed-not-measured"), ("field_tesla", 2.0)):
            document = self.honest_document()
            document["header"][name] = wrong
            with self.subTest(name=name):
                self.assertEqual(len(counted_apart_defects(document)), 1)
        document = self.honest_document()
        document["header"]["start_prior"][3] = 0.1
        self.assertEqual(len(counted_apart_defects(document)), 1)

    def test_one_track_short_of_its_hits_fails(self):
        track = {"key": "one", "status": "fitted", "measurements": 8, "holes": 0, "outliers": 0, "measured_coordinates": 16}
        self.assertEqual(track_defects([track], 1), [])
        self.assertEqual(len(track_defects([dict(track, measurements=7)], 1)), 1)
        self.assertEqual(len(track_defects([dict(track, status="failed")], 1)), 1)
        self.assertEqual(len(track_defects([track], 2)), 1)

    def zero_field_document(self) -> dict:
        covariance = [0.0] * 21
        for index in COVARIANCE_DIAGONAL:
            covariance[index] = 1e-4
        return {"header": {"product_id": "straight.line", "start_prior": [-50.0, 10.0, 0.1, 0.1, 1.0]}, "states": [{"plane": 1, "chi2": 0.5}], "tracks": [{"key": "one", "chi2": 1.0}],
                "parameters": [{"track_key": "one", "state_index": 0, "state_type": "smoothed", "parameters": [0.0, 0.0, 0.0, 1.5, 0.25, 0.0], "covariance": covariance}]}

    def test_zero_field_may_differ_in_q_over_p_width_only(self):
        reference = self.zero_field_document()
        honest = self.zero_field_document()
        honest["header"]["start_prior"][3] = 1.0
        honest["parameters"][0]["covariance"][COVARIANCE_DIAGONAL[4]] = 1.0
        honest["parameters"][0]["covariance"][19] = 0.5  # q/p with time
        honest["tracks"][0]["chi2"] = 1.0 + 1e-7
        self.assertEqual(zero_field_defects(reference, honest), [])
        moved_state = self.zero_field_document()
        moved_state["parameters"][0]["parameters"][0] = 1e-3
        moved_covariance = self.zero_field_document()
        moved_covariance["parameters"][0]["covariance"][1] = 1e-7
        moved_q_over_p = self.zero_field_document()
        moved_q_over_p["parameters"][0]["parameters"][4] = 0.26
        moved_start = self.zero_field_document()
        moved_start["header"]["start_prior"][1] = 5.0
        moved_chi2 = self.zero_field_document()
        moved_chi2["states"][0]["chi2"] = 0.6
        moved_plane = self.zero_field_document()
        moved_plane["states"][0]["plane"] = 2
        for document in (moved_state, moved_covariance, moved_q_over_p, moved_start, moved_chi2, moved_plane):
            self.assertEqual(len(zero_field_defects(reference, document)), 1)


def run_program(arguments) -> None:
    finished = subprocess.run([str(item) for item in arguments], capture_output=True, text=True, timeout=3600)
    if finished.returncode != 0:
        raise AssertionError(f"{arguments[0]} exit {finished.returncode}: {finished.stdout}{finished.stderr}")


def plane_one_arrays(document: dict, track_keys) -> tuple:
    """Section 7: the smoothed state at plane 1, with its covariance, by track key. A set that lost its state stops here."""
    first_index = {state["track_key"]: state["index"] for state in document["states"] if state["plane"] == 1}
    records = {item["track_key"]: item for item in document["parameters"] if item["state_type"] == "smoothed" and item["state_index"] == first_index.get(item["track_key"])}
    states = numpy.array([records[key]["parameters"][:5] for key in track_keys])
    sigmas = numpy.sqrt(numpy.array([[records[key]["covariance"][index] for index in COVARIANCE_DIAGONAL[:5]] for key in track_keys]))
    return states, sigmas


def hit_coordinates(hits, hit_keys):
    return numpy.stack([hits["loc0_mm"][hit_keys], hits["loc1_mm"][hit_keys]], -1)


class BinSample:
    """One stratum of block 1, refitted at 1 T: truth and fit as arrays, so that a product of 250 MB need not stay in memory."""

    def __init__(self, folder: Path, momentum_bin: int):
        stratum = STRATA_OF_BINS[momentum_bin]
        started = time.monotonic()
        data_file, truth_file = folder / f"stratum-{stratum}.t07data", folder / f"stratum-{stratum}.t07truth"
        run_program([GENERATOR, "generate", "--fixture", "clean", "--block", CLEAN_BLOCK, "--stratum", stratum, "--first-event", 0, "--count", EVENTS_PER_BIN,
                     "--data-file", data_file, "--truth-file", truth_file])
        generated = time.monotonic()
        truth_header = truth_files.read_truth_header(truth_file)
        if (truth_header["block"], truth_header["stratum"], truth_header["fixture_id"]) != (CLEAN_BLOCK, stratum, 7001):
            raise AssertionError(f"the truth file says {truth_header}")
        hit_sets, truth_rows, hit_rows = [], [], []
        for ordinal, (truth_event, data_event) in enumerate(zip(truth_files.iter_truth_events(truth_file), fixture_files.iter_data_events(data_file))):
            if int(truth_event["momentum_bin"]) != momentum_bin:
                raise AssertionError(f"event {ordinal} is in momentum bin {truth_event['momentum_bin']}")
            for track in truth_event["tracks"]:
                hit_keys = [int(key) for key in track["hit_keys"]]
                if truth_files.NO_HIT_KEY in hit_keys:
                    raise AssertionError("a clean track lost a hit")
                hit_sets.append((f"event-{ordinal}-track-{int(track['particle_key'])}", ordinal, float(track["q_over_p"]), hit_keys))
                truth_rows.append(list(track["crossings"][0]) + [float(track["q_over_p"])])
                hit_rows.append(hit_coordinates(data_event["hits"], hit_keys))
        self.keys = [hit_set[0] for hit_set in hit_sets]
        self.truth, self.hits_mm = numpy.array(truth_rows), numpy.array(hit_rows)
        self.events = numpy.array([hit_set[1] for hit_set in hit_sets])
        data_sha256 = fixture_files.file_sha256(data_file)
        document = self.refit(folder, data_file, data_sha256, hit_sets, f"t07-dev-refit-stratum-{stratum}")
        fitted = time.monotonic()
        self.track_defects = track_defects(document["tracks"], EVENTS_PER_BIN * 6)
        self.counted_defects = counted_apart_defects(document)
        self.chi2 = numpy.array([track["chi2"] for track in document["tracks"]])
        self.states, self.sigmas = plane_one_arrays(document, self.keys)
        del document
        shifted_sets = [(key, ordinal, ASSUMPTION_FACTOR * q_over_p, hit_keys) for key, ordinal, q_over_p, hit_keys in hit_sets if ordinal < SHIFTED_EVENTS_PER_BIN]
        self.shifted_count = len(shifted_sets)
        document = self.refit(folder, data_file, data_sha256, shifted_sets, f"t07-dev-refit-shifted-stratum-{stratum}")
        self.shifted_track_defects = track_defects(document["tracks"], SHIFTED_EVENTS_PER_BIN * 6)
        self.shifted_states, self.shifted_sigmas = plane_one_arrays(document, [hit_set[0] for hit_set in shifted_sets])
        print(f"REFIT-COST momentum_bin {momentum_bin} stratum {stratum} events {EVENTS_PER_BIN} tracks {len(self.keys)} generate_seconds {generated - started:.1f} "
              f"refit_and_read_seconds {fitted - generated:.1f}", flush=True)

    @staticmethod
    def refit(folder: Path, data_file: Path, data_sha256: str, hit_sets, product_id: str) -> dict:
        hit_sets_file, product_file = folder / f"{product_id}.hitsets", folder / f"{product_id}.product"
        hit_sets_file.write_text(fixture_files.hit_sets_text(data_sha256, hit_sets), encoding="utf-8")
        run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", hit_sets_file, "--field-tesla", "1", "--product-id", product_id, "--product-file", product_file])
        document = native_product.parse_product(product_file.read_text(encoding="utf-8"))
        product_file.unlink()
        return document

    @property
    def pulls(self):
        return (self.states - self.truth) / self.sigmas

    @property
    def charge(self):
        return numpy.sign(self.truth[:, 4])


@unittest.skipUnless(BUILT, NOT_BUILT)
class FieldOnRefit(unittest.TestCase):
    """The real test the guard stood for: the refit at 1 T on the clean fixture's block 1, by momentum bin, against the expectations above."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.samples = [BinSample(Path(cls.folder.name), momentum_bin) for momentum_bin in range(4)]

    def judge(self, label: str, pulls) -> None:
        reading = pull_reading(pulls)
        print(f"REFIT-PULL truth-assisted, counted apart: {label} count {reading['count']} centre {reading['centre']:+.4f} width {reading['width']:.4f} "
              f"mean {reading['mean']:+.4f} rms {reading['rms']:.4f} tail {reading['tail']:.5f}", flush=True)
        with self.subTest(label=label):
            self.assertEqual(pull_defects(reading), [])

    def test_every_track_is_fitted_and_counted_apart(self):
        for momentum_bin, sample in enumerate(self.samples):
            with self.subTest(momentum_bin=momentum_bin):
                self.assertEqual(sample.track_defects + sample.shifted_track_defects + sample.counted_defects, [])

    def test_pulls_by_momentum_bin(self):
        for momentum_bin, sample in enumerate(self.samples):
            for index, name in enumerate(PARAMETER_NAMES):
                self.judge(f"bin {momentum_bin} {name}", sample.pulls[:, index])

    def test_q_over_p_pulls_per_charge(self):
        for momentum_bin, sample in enumerate(self.samples):
            for charge, label in ((1.0, "positive"), (-1.0, "negative")):
                self.judge(f"bin {momentum_bin} q/p {label}", sample.pulls[sample.charge == charge, 4])

    def test_the_top_of_the_momentum_range_keeps_its_width(self):
        """The old prior was tightest here: 0.71 at 24 GeV. The upper half of [12, 24) GeV in ln p."""
        sample = self.samples[3]
        self.judge("upper half of bin 3 q/p", sample.pulls[numpy.abs(sample.truth[:, 4]) < 1.0 / math.sqrt(12.0 * 24.0), 4])

    def test_mean_chi2_by_momentum_bin(self):
        for momentum_bin, sample in enumerate(self.samples):
            print(f"REFIT-CHI2 truth-assisted, counted apart: bin {momentum_bin} mean {sample.chi2.mean():.4f}", flush=True)
            with self.subTest(momentum_bin=momentum_bin):
                self.assertEqual(chi2_defects(sample.chi2), [])

    def test_each_track_is_the_least_squares_fit_of_its_hits(self):
        for momentum_bin, sample in enumerate(self.samples):
            kept = slice(0, LEAST_SQUARES_TRACKS_PER_BIN)
            reference_states, reference_sigmas, _ = least_squares_fit(sample.hits_mm[kept], sample.truth[kept])
            print(f"REFIT-LEAST-SQUARES bin {momentum_bin} largest state offset {numpy.abs((sample.states[kept] - reference_states) / reference_sigmas).max():.5f} sigma, "
                  f"largest sigma offset {numpy.abs(sample.sigmas[kept] / reference_sigmas - 1.0).max():.6f}", flush=True)
            with self.subTest(momentum_bin=momentum_bin):
                self.assertEqual(agreement_defects(sample.states[kept], sample.sigmas[kept], reference_states, reference_sigmas), [])

    def test_the_assumed_q_over_p_is_only_the_start(self):
        for momentum_bin, sample in enumerate(self.samples):
            kept = sample.events < SHIFTED_EVENTS_PER_BIN
            print(f"REFIT-ASSUMPTION bin {momentum_bin} tracks {sample.shifted_count} largest state move {numpy.abs((sample.shifted_states - sample.states[kept]) / sample.sigmas[kept]).max():.5f} sigma", flush=True)
            with self.subTest(momentum_bin=momentum_bin):
                self.assertEqual(assumption_defects(sample.states[kept], sample.sigmas[kept], sample.shifted_states, sample.shifted_sigmas), [])


@unittest.skipUnless(BUILT and bool(ZERO_FIELD_REFERENCE) and bool(EVIDENCE_DIR), NOT_BUILT)
class ZeroFieldKeepsItsLine(unittest.TestCase):
    """This job's straight-line product, from tests.adapters.test_acts_tracking, against the job of record's."""

    def test_only_the_width_of_q_over_p_moved(self):
        reference = native_product.parse_product(Path(ZERO_FIELD_REFERENCE).read_text(encoding="utf-8"))
        document = native_product.parse_product((Path(EVIDENCE_DIR) / "straight-line.product").read_text(encoding="utf-8"))
        self.assertEqual(zero_field_defects(reference, document), [])


if __name__ == "__main__":
    unittest.main()
