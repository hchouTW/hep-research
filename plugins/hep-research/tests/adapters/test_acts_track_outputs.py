"""adapters/acts-tracking: R33's track-fit outputs of the refit, CAI-T07-1 (rigid shift) and CAI-T07-2 (derivatives) (plan R33, R37; t07-t09-task-sheets.md, T07; D1 stage 8 brief).

Recipe reco.track.acts-kf-refit/1, truth-assisted and counted apart, as before. From D1 stage 8 the refit writes acts-tracking-product/2 (acts_native_product.py), whose R33 records
and conventions (t07-r33/1) are stated in native/track_fit_outputs.hpp: r = x_meas - x_pred in the plane's local frame, for the predicted, filtered, smoothed and unbiased states apart
(BP03), each with its covariance; the unbiased residual is the hit removed from the smoothed state, r* = V R_s^-1 r_s, R* = V R_s^-1 V; the alignment derivatives dr/da in
t07-plane-rigid/1 (payload_geometry.hpp's PlaneDelta, the placement route), at the smoothed state, from ACTS's alignmentToBoundDerivative with the path correction; incidence and path.
These are interface tests on synthetic fixtures, no calibration or alignment quality claim (R31, R37), and development readings of block 1 otherwise.

CAI fixture (t04-values-v4.md section 4.1, "CAI items"; section 3.2): t07-telescope-cai/1, fixture 7003 (CAI clean), block 1 for interface runs, the 4 strata (= momentum bins), one
track per event, 16 measurements. CAI_EVENTS events per stratum, events 0 to CAI_EVENTS - 1.

CAI-T07-1, rigid shift. Convention (R37: "whether the true or the reconstructed geometry is moved"): the TRUE plane SHIFTED_PLANE sits at +d along its local measurement direction,
the fit's geometry stays nominal and the hit set stays fixed. An in-plane shift leaves the plane the same set of points, so the true crossing is the same global point and reads
d less in the shifted plane's frame: the generator's own sagitta fixture moves its planes exactly so (t07_cai_event_generator.cpp, loc0 - d_i). The shifted data file is the frozen
generator's file with that plane's coordinate lowered by d; d is a multiple of the 2^-30 mm grid, so every shifted hit is the grid point the generator would have written, except at
an exact rounding tie. Then r = m - x_pred falls by d: the mean unbiased residual on the shifted plane is -d, which is the shift of the reconstruction geometry against the truth.
Both measurement directions are shifted, each in its own run: loc0 by +SHIFT_MM, loc1 by -SHIFT_MM, so both signs are seen. Overdetermined without the tested hit: 7 planes against
3 track parameters in the bending view (u) and 2 in the other (v) (fit_is_overdetermined).
- Asserted, statistical (R37): on the shifted plane, in the shifted coordinate, the mean is -d within MEAN_N_SIGMA sigma of the mean. In the other coordinate on every plane, and
  on every plane in both coordinates in the unshifted run, the mean is 0 within the same rule.
- Reported, not asserted (R37: "Residual shifts on the other surfaces are reported"): the shifted coordinate on the other planes, beside the linear expectation d x influence
  (closed_form_influence). The brief's "on the planes not shifted, the mean must stay at zero" would contradict R37 and the closed form: a correct fit moves those means by up to
  0.43 d (D1 stage 8 report, finding).
- sigma of the mean, fixed before the run from the fixture's generated statistics: the closed-form unbiased-residual width sigma sqrt(1 + h_j), h_j the leave-one-out leverage of plane
  j in its view (quadratic in u, linear in v, hits sigma 0.020 mm), over sqrt(CAI_EVENTS). The fit's own mean R* must equal sigma^2 (1 + h_j) within COVARIANCE_AGREEMENT
  (a deterministic check of the residual covariance; the priors and the coupling of the views move it by under 1e-4).

R33 checks on the nominal run: every measurement state holds its four residuals, its measurement output and every fitted track its track output (the reader refuses otherwise);
the product's residuals equal this module's recomputation from the product's own states (native_product.recomputed_residuals), to RECOMPUTE_RELATIVE; pull widths r / sqrt(R) are 1
within WIDTH_N_SIGMA / sqrt(2 N) for smoothed and unbiased on every plane and for predicted and filtered where the state before the hit already holds more hits than the view has
parameters (planes 4 to 8 in u, 3 to 8 in v): before that the start prior, centred on the hits' own curve, sets the covariance, not the hits (resolved_from).

CAI-T07-2, derivatives: cai_track_output_check refits the first DERIVATIVE_TRACKS_PER_STRATUM tracks of each stratum, holds each smoothed state fixed, and moves its plane through the
placement route (PlacedTelescope::with_deltas) by +-h, +-h/2, +-h/4 in each of the six degrees of freedom; the fixed helix through that state is re-intersected with the moved plane
(Newton on the exact helix in the uniform field), with no refit. Central differences of the local position against the derivatives the product holds (ACTS's, mapped) and against
the plugin's closed form. Steps, tolerances and the halving rule, fixed before the run and printed by the program on its CONFIG line, which must equal DERIVATIVE_CONFIG:
- steps: shifts 1e-3 mm, rotations 1e-3 rad; halving: h, h/2, h/4;
- agreement at h/4: shifts within 1e-8, rotations within 1e-5 mm per rad (numpy prediction, AlignmentDerivativeClosedForm: 3e-11 and 1.3e-6); ACTS's against the closed form
  within 1e-8 (1 + |a|);
- step-halving: |D(h) - D(h/2)| / |D(h/2) - D(h/4)| within RATIO_BAND where |D(h) - D(h/2)| exceeds ROUNDING_FLOOR (predicted 4.000: central differences are second order);
  where it does not, |D(h/2) - D(h/4)| stays under ROUNDING_FLOOR too (the shifts, exactly linear);
- ACTS's rotation helper read as rigid rotations, within 1e-12.
The same program holds the plugin's unbiased residual against ACTS's own calculateUnbiasedParametersCovariance (Utilities/TrackHelpers.hpp), within 1e-9 of sigma and 1e-7 relative
in the covariance, and reports a leave-one-out refit beside it (the second method R33 allows), predicted within 1e-3 of the residual's sigma.

D1 stage 8 fix round 1 (review d1-stage8-review.md, coordinator's rulings), fixed before the run; the text above stays where it is not superseded:
- m2: the orthogonal coordinate's zero mean is asserted on the tested plane only; on the other planes it is reported (R37), with expectation 0.
- M1: each measurement holds dr_k/dq_ref, against the reference state's bound parameters (the smoothed state at the first measurement), -H J_{k<-ref}
  from the fitter's transport Jacobians (track_fit_outputs.hpp). cai_track_output_check moves the reference state by +-h, +-h/2, +-h/4 per bound
  parameter (1e-3 mm, 1e-3 rad, 1e-2 per GeV, 1e-3 mm in time), re-intersects the fixed helix with each nominal plane, and holds the stored
  derivative, per column j, within 3e-3 max(|D_loc0,j|, |D_loc1,j|) + 1e-6 at h/4, under the same halving rule (REFERENCE_* below;
  ReferenceDerivativePrediction gives the halving and the linearization bound, 7.8e-4 at 4.5 sigma(q/p) if the whole chain sat there: the Jacobians are the forward filter's,
  whose q/p before the hits fix it is the assumed one).
- M2: each fitted track holds the full covariance of its residuals against the smoothed states, Cov(r_i, r_j) = V_i delta_ij - D_i C_ref D_j^T
  (derived in track_fit_outputs.hpp). Two checks: deterministic, each diagonal block equals that state's smoothed residual covariance (ACTS's
  smoother) within FULL_COVARIANCE_DIAGONAL relative; statistical, over the fixture's own smearing, the empirical covariance of the 16 smoothed
  residuals of each stratum's 3,000 tracks equals the mean stored covariance element by element within MEAN_N_SIGMA standard errors,
  se = sqrt(mean(S_ii S_jj + S_ij^2) / N), a Gaussian sample covariance's. 136 elements per stratum.
- n7: the paired difference, shifted minus nominal unbiased residual of the same event, is printed per plane beside its expectation (-d on the
  tested plane, d x influence elsewhere, 0 in the other coordinate): a reading, not a check.
The family of statistical checks becomes 80 means, 216 widths and 544 covariance elements: 840 at 6.8e-6 each, 0.57 %.
D1 stage 8 fix round 2 (coordinator's ruling on fix round 1's concern 1), superseding the M1 and M2 lines above where they differ:
- J_{k<-ref} is the propagator's transport Jacobian of the smoothed reference state carried to each surface (KalmanRefit::reference_transports), so the
  reference derivative and the full covariance are linearized at the fitted trajectory; the forward filter's stored Jacobians are not used. C_ref is
  recomputed from the same D's and the prior as carried to the reference (track_fit_outputs.hpp, reference_covariance_of).
- The reference-derivative check is plain: |stored - D(h/4)| <= 1e-6 (1 + |stored|), with the halving rule. The differences' truncation is at most
  5.2e-8 (1 + |D|); the stepper's error against the exact helix (RK4 over steps of at most 50 mm, the end point within 1e-4 mm of the plane) is of
  order 1e-8. Round 1's column-scaled 3e-3 is withdrawn.
- The diagonal identity against ACTS's smoothed residual covariance keeps a residual effect that is not rounding: ACTS's smoother is linearized along
  the forward filter's path. Its size, numpy (FullCovarianceLinearization): 5e-5 relative at 1 sigma(q/p), 2.3e-4 at 4.5. Tolerance 1e-3, for the
  coordinator's ruling. The empirical check sees 0.012 se of it at most.

Every built test needs the build job and skips without it; that job counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_track_outputs -v
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
DRIVER = Path(BUILD_DIR) / "acts_tracking_driver"
CAI_GENERATOR = Path(BUILD_DIR) / "t07_cai_fixture_generator"
CHECK_PROGRAM = Path(BUILD_DIR) / "cai_track_output_check"
BUILT = bool(BUILD_DIR) and DRIVER.is_file() and CAI_GENERATOR.is_file() and CHECK_PROGRAM.is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built program: this test needs the T07 build job, which runs it"

# Section 4.1.
HIT_SIGMA_MM = 0.020
PLANE_Z_MM = 50.0 * numpy.arange(8)
GEV_PER_TESLA_MM = 0.299792458e-3
FIELD_TESLA = 1.0
# Section 3.2 and 4.1, CAI items.
CAI_FIXTURE_ID = 7003
CAI_BLOCK = 1
CAI_STRATA = (0, 1, 2, 3)
CAI_EVENTS = 3000
MOMENTUM_BIN_EDGES = (1.5, 3.0, 6.0, 12.0, 24.0)  # section 4.1

# CAI-T07-1, fixed before the run.
SHIFTED_PLANE = 4
SHIFT_MM = 0.0625  # 2^-4 mm: 3.1 hit sigma, 145 sigma of the mean; on the 2^-30 mm hit grid
SHIFT_CASES = (("loc0", 0, SHIFT_MM), ("loc1", 1, -SHIFT_MM))  # coordinate, index, true displacement d
MEAN_N_SIGMA = 4.5
WIDTH_N_SIGMA = 4.5
COVARIANCE_AGREEMENT = 2e-3
VIEW_PARAMETERS = (3, 2)  # u bends: position, slope, curvature; v: position, slope
# R33, deterministic.
RECOMPUTE_RELATIVE = 1e-9
RECOMPUTE_ABSOLUTE_MM = 1e-12

# CAI-T07-2, fixed before the run: cai_track_output_check.cpp holds the same numbers and prints them.
DERIVATIVE_TRACKS_PER_STRATUM = 25
SHIFT_STEP_MM, ROTATION_STEP_RAD = 1e-3, 1e-3
SHIFT_TOLERANCE, ROTATION_TOLERANCE_MM_PER_RAD = 1e-8, 1e-5
ACTS_CLOSED_FORM_TOLERANCE = 1e-8
RATIO_BAND = (3.5, 4.5)
ROUNDING_FLOOR = 1e-9
RIGIDITY_TOLERANCE = 1e-12
UNBIASED_ACTS_TOLERANCE_SIGMA, UNBIASED_ACTS_COVARIANCE_RELATIVE = 1e-9, 1e-7
LEAVE_ONE_OUT_PREDICTED_SIGMA = 1e-3
REFERENCE_STEPS = (1e-3, 1e-3, 1e-3, 1e-3, 1e-2, 1e-3)  # loc0, loc1 mm; phi, theta rad; q/p per GeV; time mm
REFERENCE_RELATIVE, REFERENCE_ABSOLUTE = 1e-6, 1e-6  # fix round 2: plain, 1e-6 (1 + |a|); round 1's 3e-3 column-scaled rule is withdrawn
REFERENCE_RATIO_FLOOR = 1e-8  # fix round 4: the reference halving ratio is tested only above it; below it rounding dominates the ratio
FULL_COVARIANCE_DIAGONAL = 1e-3  # fix round 2: ACTS's smoother is linearized along the forward filter's path (FullCovarianceLinearization); round 1's 1e-6
DERIVATIVE_CONFIG = (f"CONFIG tracks {DERIVATIVE_TRACKS_PER_STRATUM} shift_step_mm 0.001 rotation_step_rad 0.001 halvings 2 shift_tolerance 1e-08 rotation_tolerance_mm_per_rad 1e-05 "
                     f"acts_closed_form_tolerance 1e-08 ratio_band 3.5 4.5 rounding_floor 1e-09 rigidity_tolerance 1e-12 unbiased_acts_sigma 1e-09 unbiased_acts_covariance 1e-07 "
                     f"leave_one_out_predicted_sigma 0.001 reference_steps 0.001 0.001 0.001 0.001 0.01 0.001 reference_relative 1e-06 reference_absolute 1e-06 reference_ratio_floor 1e-08")


# ---- The arithmetic, numpy only: nothing here reads ACTS.

def design_matrix(view: int) -> numpy.ndarray:
    """Rows of the linear track model in a view, at the eight planes: 1, z, z^2 in u (bending), 1, z in v."""
    return numpy.vander(PLANE_Z_MM, VIEW_PARAMETERS[view], increasing=True)


def leave_one_out_leverage(view: int, plane: int) -> float:
    """h_j = x_j^T (X_-j^T X_-j)^-1 x_j: the variance of the prediction at plane j from the other planes, in units of sigma^2."""
    design = design_matrix(view)
    kept = [index for index in range(8) if index != plane - 1]
    weight = numpy.linalg.inv(design[kept].T @ design[kept])
    return float(design[plane - 1] @ weight @ design[plane - 1])


def unbiased_sigma_mm(view: int, plane: int) -> float:
    return HIT_SIGMA_MM * math.sqrt(1.0 + leave_one_out_leverage(view, plane))


def sigma_of_mean_mm(view: int, plane: int, count: int = CAI_EVENTS) -> float:
    return unbiased_sigma_mm(view, plane) / math.sqrt(count)


def closed_form_influence(view: int, plane: int, moved_plane: int = SHIFTED_PLANE) -> float:
    """How much of a hit's move on moved_plane the prediction at plane takes, in the fit without plane: x_j^T (X_-j^T X_-j)^-1 x_k."""
    design = design_matrix(view)
    kept = [index for index in range(8) if index != plane - 1]
    weight = numpy.linalg.inv(design[kept].T @ design[kept])
    return float(design[plane - 1] @ weight @ design[moved_plane - 1])


def fit_is_overdetermined(view: int, plane: int) -> bool:
    return 8 - 1 > VIEW_PARAMETERS[view] and numpy.linalg.matrix_rank(numpy.delete(design_matrix(view), plane - 1, axis=0)) == VIEW_PARAMETERS[view]


def expected_mean_mm(shifted_view: int, displacement_mm: float, view: int, plane: int) -> float | None:
    """CAI-T07-1's expectation, or None where R37 reports and does not assert. A true plane at +d reads d less: r falls by d."""
    if plane != SHIFTED_PLANE:
        return None  # fix round 1, m2: R37 asserts the tested surface only
    return -displacement_mm if view == shifted_view else 0.0


def reported_expectation_mm(shifted_view: int, displacement_mm: float, plane: int, view: int | None = None) -> float:
    """The linear expectation of a reported mean: the hit on SHIFTED_PLANE reads -d, the prediction at plane takes influence x -d, r = m - pred rises by influence x d.
    In the other coordinate, 0: the views couple only through u'v' terms, odd in v' and in charge."""
    if view is not None and view != shifted_view:
        return 0.0
    return closed_form_influence(shifted_view, plane) * displacement_mm


def mean_defects(mean: float, expected: float, sigma_of_mean: float, label: str) -> list:
    return [] if abs(mean - expected) <= MEAN_N_SIGMA * sigma_of_mean else [f"{label}: mean {mean:+.6f} mm, expected {expected:+.6f} within {MEAN_N_SIGMA * sigma_of_mean:.6f}"]


def width_defects(pulls, label: str) -> list:
    pulls = numpy.asarray(pulls, float)
    width = float(numpy.sqrt(numpy.mean(pulls ** 2)))
    limit = WIDTH_N_SIGMA / math.sqrt(2.0 * pulls.size)
    return [] if abs(width - 1.0) <= limit else [f"{label}: pull width {width:.4f}, expected 1 within {limit:.4f}"]


def resolved_from(view: int) -> int:
    """The first plane whose predicted state already holds more hits than the view has parameters."""
    return VIEW_PARAMETERS[view] + 1


def shifted_events(data_path, plane: int, coordinate: int, displacement_mm: float) -> list:
    """The data file's events as (plane, loc0, loc1) lists, with plane's coordinate lowered by the true displacement: the hit a plane truly at +d records."""
    events = []
    name = ("loc0_mm", "loc1_mm")[coordinate]
    for event in fixture_files.iter_data_events(data_path):
        hits = []
        for hit in event["hits"]:
            values = [float(hit["loc0_mm"]), float(hit["loc1_mm"])]
            if int(hit["plane"]) == plane:
                values[coordinate] = float(hit[name]) - displacement_mm
            hits.append((int(hit["plane"]), values[0], values[1]))
        events.append(hits)
    return events


def family_false_failure(check_count: int, n_sigma: float = MEAN_N_SIGMA) -> float:
    return check_count * math.erfc(n_sigma / math.sqrt(2.0))


# The exact helix of a uniform field along ACTS z, and the moved plane of payload_geometry.hpp, for the numpy prediction of CAI-T07-2.
PLANE_ROTATION = numpy.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])  # columns: loc0 = ACTS y, loc1 = ACTS z, normal = ACTS x


def axis_rotation(axis, angle: float) -> numpy.ndarray:
    x, y, z = axis
    cross = numpy.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return numpy.eye(3) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * cross @ cross


def moved_plane(centre, rotation, delta) -> tuple:
    """moved = nominal * shift * R(normal) * R(loc1) * R(loc0), as payload_geometry.cpp's moved_plane_transform."""
    change = axis_rotation((0, 0, 1), delta[5]) @ axis_rotation((0, 1, 0), delta[4]) @ axis_rotation((1, 0, 0), delta[3])
    return centre + rotation @ numpy.asarray(delta[:3]), rotation @ change


def helix_point(position, direction, bending_per_mm: float, path_mm: float) -> tuple:
    """dT/ds = w T x z: T turns by -w s about z. Stable for small w s."""
    turn = bending_per_mm * path_mm
    sine, versine = math.sin(turn), 2.0 * math.sin(0.5 * turn) ** 2
    if bending_per_mm == 0.0:
        return position + direction * path_mm, direction
    moved = position + numpy.array([(direction[0] * sine + direction[1] * versine) / bending_per_mm,
                                    (direction[1] * sine - direction[0] * versine) / bending_per_mm, direction[2] * path_mm])
    turned = numpy.array([direction[0] * math.cos(turn) + direction[1] * sine, direction[1] * math.cos(turn) - direction[0] * sine, direction[2]])
    return moved, turned


def local_crossing(position, direction, bending_per_mm: float, centre, rotation) -> numpy.ndarray:
    return crossing_state(position, direction, bending_per_mm, centre, rotation)[0]


def crossing_state(position, direction, bending_per_mm: float, centre, rotation) -> tuple:
    """The helix's crossing of a plane: its local position, the global point and the tangent there."""
    normal = rotation[:, 2]
    path = -float(normal @ (position - centre)) / float(normal @ direction)
    for _ in range(50):
        point, tangent = helix_point(position, direction, bending_per_mm, path)
        step = -float(normal @ (point - centre)) / float(normal @ tangent)
        path += step
        if abs(step) < 1e-15:
            break
    point, tangent = helix_point(position, direction, bending_per_mm, path)
    return (rotation.T @ (point - centre))[:2], point, tangent


def finite_difference(position, direction, bending_per_mm: float, centre, rotation, dof: int, step: float) -> numpy.ndarray:
    """-(l(+step) - l(-step)) / (2 step): dr/da with the hit fixed."""
    plus, minus = numpy.zeros(6), numpy.zeros(6)
    plus[dof], minus[dof] = step, -step
    return -(local_crossing(position, direction, bending_per_mm, *moved_plane(centre, rotation, plus))
             - local_crossing(position, direction, bending_per_mm, *moved_plane(centre, rotation, minus))) / (2.0 * step)


def fixture_state(generator) -> tuple:
    """A state on a random plane as section 4.1 makes them: vertex at z = -100 mm, u +-0.05 mm, v +-30 mm, slopes +-0.15, ln p uniform in [1.5, 24) GeV,
    the exact helix carried to the plane. Returns the plane's centre, the global position and direction on it, and the bending."""
    momentum = math.exp(generator.uniform(math.log(1.5), math.log(24.0)))
    bending = float(generator.choice((-1.0, 1.0))) / momentum * GEV_PER_TESLA_MM * FIELD_TESLA
    start = numpy.array([-100.0, generator.uniform(-0.05, 0.05), generator.uniform(-30.0, 30.0)])
    direction = numpy.array([1.0, *generator.uniform(-0.15, 0.15, 2)])
    direction /= numpy.linalg.norm(direction)
    centre = numpy.array([PLANE_Z_MM[generator.integers(8)], 0.0, 0.0])
    local, position, tangent = crossing_state(start, direction, bending, centre, PLANE_ROTATION)
    return centre, position, tangent, bending, local


def derivative_prediction(trials: int = 200, seed: int = 8, fixture_like: bool = False) -> dict:
    """Largest disagreement of the closed form with central differences at h and h/4, and the halving ratio per row, over random states inside
    section 4.1 (wide: positions +-140 mm, slopes +-0.25) or, with fixture_like, as the fixture makes them (fixture_state). Fix round 1, m3: the
    ratio is also kept apart for first differences above 1e-8 and for those between the floor and 1e-8."""
    generator = numpy.random.default_rng(seed)
    worst = {dof: {"error_h": 0.0, "error_quarter": 0.0, "ratio_low": math.inf, "ratio_high": 0.0, "largest": 0.0, "clear_low": math.inf, "clear_high": 0.0}
             for dof in range(6)}
    for _ in range(trials):
        if fixture_like:
            centre, position, direction, bending, local = fixture_state(generator)
        else:
            momentum = math.exp(generator.uniform(math.log(1.5), math.log(24.0)))
            bending = float(generator.choice((-1.0, 1.0))) / momentum * GEV_PER_TESLA_MM * FIELD_TESLA
            centre = numpy.array([PLANE_Z_MM[generator.integers(8)], 0.0, 0.0])
            local = generator.uniform(-140.0, 140.0, 2)
            direction = numpy.array([1.0, *generator.uniform(-0.25, 0.25, 2)])
            direction /= numpy.linalg.norm(direction)
            position = centre + PLANE_ROTATION @ numpy.array([local[0], local[1], 0.0])
        analytic = numpy.array(native_product.closed_form_residual_derivative(local, PLANE_ROTATION.T @ direction))
        for dof in range(6):
            step = SHIFT_STEP_MM if dof < 3 else ROTATION_STEP_RAD
            steps = [finite_difference(position, direction, bending, centre, PLANE_ROTATION, dof, step / 2 ** halving) for halving in range(3)]
            record = worst[dof]
            record["error_h"] = max(record["error_h"], float(numpy.abs(analytic[:, dof] - steps[0]).max()))
            record["error_quarter"] = max(record["error_quarter"], float(numpy.abs(analytic[:, dof] - steps[2]).max()))
            record["largest"] = max(record["largest"], float(numpy.abs(analytic[:, dof]).max()))
            for row in range(2):
                first, second = abs(steps[0][row] - steps[1][row]), abs(steps[1][row] - steps[2][row])
                if first > ROUNDING_FLOOR:
                    ratio = first / second if second > 0.0 else math.inf
                    record["ratio_low"], record["ratio_high"] = min(record["ratio_low"], ratio), max(record["ratio_high"], ratio)
                    if first > 1e-8:
                        record["clear_low"], record["clear_high"] = min(record["clear_low"], ratio), max(record["clear_high"], ratio)
    return worst


def reference_crossing(centre, rotation, bound, target_centre) -> numpy.ndarray:
    """The local crossing of the nominal plane at target_centre by the helix through the bound state (loc0, loc1, phi, theta, q/p, time) on the plane at centre."""
    position = centre + rotation @ numpy.array([bound[0], bound[1], 0.0])
    direction = numpy.array([math.cos(bound[2]) * math.sin(bound[3]), math.sin(bound[2]) * math.sin(bound[3]), math.cos(bound[3])])
    return local_crossing(position, direction, bound[4] * GEV_PER_TESLA_MM * FIELD_TESLA, target_centre, rotation)


def reference_derivative_prediction(trials: int = 100, seed: int = 9) -> dict:
    """CAI-T07-2's reference-derivative halving, without ACTS: per bound parameter, the largest |D(h/4) - D(h/64)| (truncation left at h/4) relative to
    1 + |D|, and the halving ratio where the first difference exceeds the floor, over fixture-like reference states on plane 1 and every later plane."""
    generator = numpy.random.default_rng(seed)
    worst = {parameter: {"truncation": 0.0, "ratio_low": math.inf, "ratio_high": 0.0, "at_floor": 0, "entries": 0, "clear_low": math.inf, "clear_high": 0.0}
             for parameter in range(6)}
    for _ in range(trials):
        momentum = math.exp(generator.uniform(math.log(1.5), math.log(24.0)))
        q_over_p = float(generator.choice((-1.0, 1.0))) / momentum
        slopes = generator.uniform(-0.15, 0.15, 2)
        bound = [generator.uniform(-20.0, 20.0), generator.uniform(-40.0, 40.0), math.atan(slopes[0]),
                 math.acos(slopes[1] / math.sqrt(1.0 + slopes[0] ** 2 + slopes[1] ** 2)), q_over_p, 0.0]
        for target in range(8):
            target_centre = numpy.array([PLANE_Z_MM[target], 0.0, 0.0])
            for parameter in range(6):
                differences = []
                for halving in (0, 1, 2, 6):
                    step = REFERENCE_STEPS[parameter] / 2 ** halving
                    plus, minus = list(bound), list(bound)
                    plus[parameter] += step
                    minus[parameter] -= step
                    differences.append(-(reference_crossing(numpy.zeros(3), PLANE_ROTATION, plus, target_centre)
                                         - reference_crossing(numpy.zeros(3), PLANE_ROTATION, minus, target_centre)) / (2.0 * step))
                record = worst[parameter]
                record["truncation"] = max(record["truncation"], float((numpy.abs(differences[2] - differences[3]) / (1.0 + numpy.abs(differences[3]))).max()))
                for row in range(2):
                    record["entries"] += 1
                    first, second = abs(differences[0][row] - differences[1][row]), abs(differences[1][row] - differences[2][row])
                    if first > ROUNDING_FLOOR:
                        ratio = first / second if second > 0.0 else math.inf
                        record["ratio_low"], record["ratio_high"] = min(record["ratio_low"], ratio), max(record["ratio_high"], ratio)
                        if first > 1e-8:
                            record["clear_low"], record["clear_high"] = min(record["clear_low"], ratio), max(record["clear_high"], ratio)
                    else:
                        record["at_floor"] += 1
    return worst


def column_scaled_error(stored, differences) -> numpy.ndarray:
    """|stored - differences| per column over that column's scale, max(|D_loc0,j|, |D_loc1,j|) of stored, plus REFERENCE_ABSOLUTE: the reference rule's measure."""
    stored, differences = numpy.asarray(stored, float), numpy.asarray(differences, float)
    return numpy.abs(stored - differences) / (numpy.abs(stored).max(axis=0) + REFERENCE_ABSOLUTE / REFERENCE_RELATIVE)


def linearization_sensitivity(q_over_p_shift: float = 4.5 * 0.00412, angle_shift: float = 3e-4, seed: int = 10, trials: int = 40, plain: bool = False) -> float:
    """How far the reference derivative moves, in column-scaled units, when it is taken at a state off the smoothed one by q_over_p_shift (4.5 sigma(q/p),
    section 4.1) and angle_shift in phi and theta: the fitter's Jacobians are the forward filter's, whose q/p before the hits fix it is the assumed one."""
    generator = numpy.random.default_rng(seed)
    worst = 0.0
    for _ in range(trials):
        q_over_p = float(generator.choice((-1.0, 1.0))) / math.exp(generator.uniform(math.log(1.5), math.log(24.0)))
        slopes = generator.uniform(-0.15, 0.15, 2)
        bound = [generator.uniform(-20.0, 20.0), generator.uniform(-40.0, 40.0), math.atan(slopes[0]),
                 math.acos(slopes[1] / math.sqrt(1.0 + slopes[0] ** 2 + slopes[1] ** 2)), q_over_p, 0.0]
        moved = list(bound)
        moved[2] += angle_shift * float(generator.choice((-1.0, 1.0)))
        moved[3] += angle_shift * float(generator.choice((-1.0, 1.0)))
        moved[4] += q_over_p_shift * float(generator.choice((-1.0, 1.0)))
        for target in range(1, 8):
            centre = numpy.array([PLANE_Z_MM[target], 0.0, 0.0])
            def derivative(state):
                columns = []
                for parameter in range(6):
                    step = REFERENCE_STEPS[parameter] / 4
                    plus, minus = list(state), list(state)
                    plus[parameter] += step
                    minus[parameter] -= step
                    columns.append(-(reference_crossing(numpy.zeros(3), PLANE_ROTATION, plus, centre) - reference_crossing(numpy.zeros(3), PLANE_ROTATION, minus, centre)) / (2 * step))
                return numpy.stack(columns, 1)
            first, second = derivative(bound), derivative(moved)
            measure = numpy.abs(first - second) / (1.0 + numpy.abs(first)) if plain else column_scaled_error(first, second)
            worst = max(worst, float(measure.max()))
    return worst


def empirical_covariance_defects(residuals, mean_covariance, mean_products, label: str) -> list:
    """M2's statistical check: the empirical second moments of N residual vectors (N x 2n) against the mean stored covariance, element by element,
    within MEAN_N_SIGMA se, se_ij = sqrt((mean(S_ii S_jj) + mean(S_ij^2)) / N), mean_products holding those two means."""
    residuals = numpy.asarray(residuals, float)
    count = residuals.shape[0]
    empirical = residuals.T @ residuals / count
    standard_error = numpy.sqrt(mean_products / count)
    excess = numpy.abs(empirical - mean_covariance) > MEAN_N_SIGMA * standard_error
    rows, columns = numpy.nonzero(numpy.triu(excess))
    return [f"{label}: element {row} {column} empirical {empirical[row, column]:.4e} stored {mean_covariance[row, column]:.4e} se {standard_error[row, column]:.2e}"
            for row, column in zip(rows, columns)]


# ---- Unbuilt tests: run anywhere in seconds.

class ResidualSignConvention(unittest.TestCase):
    """R37 and the glossary: r = x_meas - x_pred."""

    def test_a_hit_above_its_prediction_has_a_positive_residual(self):
        for holds_the_hit in (False, True):
            residual, covariance = native_product.residual_of((0.1, -0.05), (4e-4, 0.0, 4e-4), (0.0, 0.0), (1e-4, 0.0, 1e-4), holds_the_hit)
            self.assertAlmostEqual(residual[0], 0.1, delta=1e-15)
            self.assertAlmostEqual(residual[1], -0.05, delta=1e-15)
            self.assertAlmostEqual(covariance[0], 5e-4 if not holds_the_hit else 3e-4, delta=1e-15)

    def test_a_true_plane_at_plus_d_lowers_its_hits_and_so_its_residual(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "one.t07data"
            path.write_bytes(fixture_files.encode_data_file(HIT_SIGMA_MM, [[(plane, 1.0, -2.0) for plane in range(1, 9)]]))
            events = shifted_events(path, SHIFTED_PLANE, 0, SHIFT_MM)
        self.assertEqual(events[0][SHIFTED_PLANE - 1], (SHIFTED_PLANE, 1.0 - SHIFT_MM, -2.0))
        self.assertEqual([hit for index, hit in enumerate(events[0]) if index != SHIFTED_PLANE - 1], [(plane, 1.0, -2.0) for plane in range(1, 9) if plane != SHIFTED_PLANE])
        residual, _ = native_product.residual_of(events[0][SHIFTED_PLANE - 1][1:], (4e-4, 0.0, 4e-4), (1.0, -2.0), (0.0, 0.0, 0.0), False)
        self.assertAlmostEqual(residual[0], -SHIFT_MM, delta=1e-15)
        self.assertAlmostEqual(expected_mean_mm(0, SHIFT_MM, 0, SHIFTED_PLANE), -SHIFT_MM)

    def test_moving_the_reconstruction_plane_by_plus_a_raises_r_by_a(self):
        """cai_payload_probe.cpp's convention: the reconstruction plane at +a along loc0, the hit fixed, the prediction falls by a, r rises by a."""
        derivative = native_product.closed_form_residual_derivative((12.0, -30.0), (0.1, 0.05, 0.99))
        self.assertEqual((derivative[0][0], derivative[1][1], derivative[0][1], derivative[1][0]), (1.0, 1.0, 0.0, 0.0))

    def test_the_shift_is_on_the_hit_grid_and_so_are_the_shifted_hits(self):
        self.assertEqual(SHIFT_MM * fixture_files.HIT_GRID_STEPS_PER_MM, round(SHIFT_MM * fixture_files.HIT_GRID_STEPS_PER_MM))
        hits = fixture_files.on_hit_grid(numpy.linspace(-149.0, 149.0, 1001) + 1e-7)
        self.assertEqual(fixture_files.off_hit_grid(hits), 0)
        self.assertEqual(fixture_files.off_hit_grid(hits - SHIFT_MM), 0)
        self.assertGreater(fixture_files.off_hit_grid(hits - 0.05), 900)  # a shift off the grid would leave it


class UnbiasedResidualFormula(unittest.TestCase):
    """The hit removed from the smoothed state, r* = V R_s^-1 r_s, R* = V R_s^-1 V, against an explicit leave-one-out fit."""

    def test_a_hand_made_level_of_four_hits(self):
        hits, sigma = [0.03, -0.01, 0.02, 0.0], 0.02
        mean, count = sum(hits) / 4.0, 4
        for index, hit in enumerate(hits):
            smoothed = (hit - mean, sigma ** 2 - sigma ** 2 / count)  # r_s = m - mean, R_s = V - C_s with C_s = sigma^2 / n
            unbiased, variance = native_product.unbiased_from_smoothed_1d(smoothed[0], smoothed[1], sigma ** 2)
            others = [value for position, value in enumerate(hits) if position != index]
            self.assertAlmostEqual(unbiased, hit - sum(others) / 3.0, delta=1e-15)  # the explicit leave-one-out residual
            self.assertAlmostEqual(variance, sigma ** 2 + sigma ** 2 / 3.0, delta=1e-18)  # V + the variance of the others' mean
            self.assertAlmostEqual(unbiased, smoothed[0] * count / (count - 1), delta=1e-15)

    def test_a_line_against_its_leave_one_out_fit(self):
        z_values = numpy.array([0.0, 50.0, 100.0, 150.0, 200.0])
        hits, sigma = numpy.array([0.012, -0.031, 0.008, 0.027, -0.004]), 0.02
        design = numpy.stack([numpy.ones(5), z_values], 1)
        covariance = sigma ** 2 * numpy.linalg.inv(design.T @ design)
        state = covariance @ design.T @ hits / sigma ** 2
        for index in range(5):
            smoothed = hits[index] - design[index] @ state
            smoothed_variance = sigma ** 2 - design[index] @ covariance @ design[index]
            unbiased, variance = native_product.unbiased_from_smoothed_1d(smoothed, smoothed_variance, sigma ** 2)
            kept = [position for position in range(5) if position != index]
            weight = numpy.linalg.inv(design[kept].T @ design[kept])
            left_out = weight @ design[kept].T @ hits[kept]
            self.assertAlmostEqual(unbiased, hits[index] - design[index] @ left_out, delta=1e-14)
            self.assertAlmostEqual(variance, sigma ** 2 * (1.0 + design[index] @ weight @ design[index]), delta=1e-17)

    def test_two_correlated_coordinates_against_their_leave_one_out_fit(self):
        generator = numpy.random.default_rng(3)
        measurement_covariance = numpy.array([[4e-4, 1.2e-4], [1.2e-4, 2.5e-4]])
        design = generator.normal(size=(5, 2, 3))  # five 2-D hits of a 3-parameter state
        hits = generator.normal(scale=0.02, size=(5, 2))
        weight = numpy.linalg.inv(measurement_covariance)
        information = sum(block.T @ weight @ block for block in design)
        covariance = numpy.linalg.inv(information)
        state = covariance @ sum(block.T @ weight @ hit for block, hit in zip(design, hits))
        for index in range(5):
            smoothed = hits[index] - design[index] @ state
            smoothed_covariance = measurement_covariance - design[index] @ covariance @ design[index].T
            unbiased, unbiased_covariance = native_product.unbiased_from_smoothed(tuple(smoothed), (smoothed_covariance[0, 0], smoothed_covariance[0, 1], smoothed_covariance[1, 1]),
                                                                                   (measurement_covariance[0, 0], measurement_covariance[0, 1], measurement_covariance[1, 1]))
            others = [position for position in range(5) if position != index]
            left_information = sum(design[position].T @ weight @ design[position] for position in others)
            left_covariance = numpy.linalg.inv(left_information)
            left_state = left_covariance @ sum(design[position].T @ weight @ hits[position] for position in others)
            expected = hits[index] - design[index] @ left_state
            expected_covariance = measurement_covariance + design[index] @ left_covariance @ design[index].T
            numpy.testing.assert_allclose(unbiased, expected, rtol=1e-10, atol=1e-15)
            numpy.testing.assert_allclose(unbiased_covariance, (expected_covariance[0, 0], expected_covariance[0, 1], expected_covariance[1, 1]), rtol=1e-10)

    def test_the_wrong_sign_of_the_smoothed_covariance_is_caught(self):
        hits, sigma = [0.03, -0.01, 0.02, 0.0], 0.02
        mean = sum(hits) / 4.0
        wrong, _ = native_product.unbiased_from_smoothed_1d(hits[0] - mean, sigma ** 2 + sigma ** 2 / 4.0, sigma ** 2)
        self.assertGreater(abs(wrong - (hits[0] - sum(hits[1:]) / 3.0)), 1e-3)


def sample_r33_document() -> dict:
    """A small acts-tracking-product/2 with consistent residuals: one fitted track of two measurements and a hole, one failed track."""
    header = {"product_id": "refit.r33", "revision": 1, "recipe": "reco.track.acts-kf-refit/1", "stage": "refit-known-hit-set", "evidence_class": "truth-assisted",
              "data_product": "t07-measurements-0123456789abcdef", "data_sha256": "a" * 64, "hit_sets_sha256": "b" * 64, "field_tesla": 1.0, "qop_status": "measured",
              "material_model": "none", "start_prior": [-50.0, 10.0, 0.1, 0.1, 1.0], "acts_version": "48.2.0", "r33_conventions": native_product.R33_CONVENTIONS,
              "alignment_parametrization": list(native_product.ALIGNMENT_PARAMETRIZATION)}
    tracks = [{"key": "0", "event_ordinal": 0, "status": "fitted", "failure_category": "none", "measurements": 2, "holes": 1, "outliers": 0, "chi2": 1.5,
               "measured_coordinates": 4, "assumed_q_over_p": 0.5},
              {"key": "1", "event_ordinal": 1, "status": "failed", "failure_category": "fit", "measurements": 0, "holes": 0, "outliers": 0, "chi2": 0.0,
               "measured_coordinates": 0, "assumed_q_over_p": -0.25}]
    states = [{"track_key": "0", "index": index, "plane": plane, "kind": kind, "hit_key": hit, "loc0_mm": loc0, "loc1_mm": loc1, "covariance": [4e-4, 0.0, 4e-4],
               "path_length_mm": 50.0 * index, "chi2": 0.7}
              for index, plane, kind, hit, loc0, loc1 in ((0, 1, "measurement", 0, 1.0, -2.0), (1, 2, "hole", None, 0.0, 0.0), (2, 3, "measurement", 2, 11.0, -7.0))]
    parameters, residuals = [], []
    for index, loc in ((0, (0.99, -2.01)), (1, (6.0, -4.5)), (2, (11.02, -6.97))):
        for state_type, shift, variance in (("predicted", 0.004, 2e-4), ("filtered", 0.002, 1e-4), ("smoothed", 0.001, 8e-5)):
            covariance = [0.0] * 21
            for diagonal, value in zip((0, 6, 11, 15, 18, 20), (variance, variance * 1.1, 1e-6, 1e-6, 1e-6, 1.0)):
                covariance[diagonal] = value
            covariance[1] = 1e-5
            parameters.append({"track_key": "0", "state_index": index, "state_type": state_type, "parameters": [loc[0] + shift, loc[1] - shift, 0.1, 1.5, 0.5, 0.0],
                               "covariance": covariance})
    document = {"format": native_product.PRODUCT_FORMAT_R33, "header": header, "tracks": tracks, "states": states, "parameters": parameters}
    recomputed = native_product.recomputed_residuals(document)
    for (track_key, index, state_type), (value, covariance) in sorted(recomputed.items(), key=lambda item: (item[0][1], native_product.RESIDUAL_TYPES.index(item[0][2]))):
        residuals.append({"track_key": track_key, "state_index": index, "state_type": state_type, "residual": list(value), "covariance": list(covariance)})
    document["track_outputs"] = [{"track_key": "0", "charge": 1, "q_over_p": 0.5, "q_over_p_variance": 1e-6, "reference_state_index": 0, "topology": "collision",
                                  "constraint": "none", "field": "on"}]
    document["residuals"] = residuals
    document["measurement_outputs"] = [{"track_key": "0", "state_index": index, "geometry_id": 72057594037927936 + 256 * index, "projector": [0, 1], "local_slope": [0.1, -0.05],
                                        "incidence_rad": 0.1117, "thickness_mm": 0.0, "path_factor": 1.0062, "sensitive_path_mm": 0.0,
                                        "alignment_derivative": [1.0, 0.0, -0.1, 0.2, -0.1, -2.0, 0.0, 1.0, 0.05, -0.1, 0.05, 1.0],
                                        "reference_derivative": [-1.0, 0.0, -100.0 * index, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, -100.0 * index, -2.0 * index, 0.0]}
                                       for index in (0, 2)]
    # The diagonal blocks are the smoothed residual covariances, as t07-r33/1 requires; one off-diagonal block, made up.
    blocks = [next(item["covariance"] for item in residuals if item["state_index"] == index and item["state_type"] == "smoothed") for index in (0, 2)]
    matrix = numpy.zeros((4, 4))
    for position, block in enumerate(blocks):
        matrix[2 * position:2 * position + 2, 2 * position:2 * position + 2] = [[block[0], block[1]], [block[1], block[2]]]
    matrix[0, 2] = matrix[2, 0] = -2e-5
    document["residual_covariances"] = [{"track_key": "0", "measurement_count": 2, "covariance": [float(matrix[row, column]) for row in range(4) for column in range(row, 4)]}]
    return document


def renamed(document: dict, keys: dict, product_id: str) -> dict:
    """The same document under other track keys and another identity."""
    copied = {"format": document["format"], "header": dict(document["header"], product_id=product_id)}
    copied["tracks"] = [dict(track, key=keys[track["key"]]) for track in document["tracks"]]
    for collection in ("states", "parameters", "track_outputs", "residuals", "measurement_outputs", "residual_covariances"):
        copied[collection] = [dict(item, track_key=keys[item["track_key"]]) for item in document[collection]]
    return copied


class ProductReaderR33(unittest.TestCase):
    """acts-tracking-product/2: every R33 field the reader promises, the refusals, and /1 still read where earlier jobs compare."""

    def setUp(self):
        self.document = sample_r33_document()
        self.text = native_product.format_product(self.document)

    def test_round_trip_is_byte_exact(self):
        self.assertTrue(self.text.startswith("acts-tracking-product/2\n"))
        parsed = native_product.parse_product(self.text)
        self.assertEqual(native_product.format_product(parsed), self.text)
        self.assertEqual(parsed["format"], native_product.PRODUCT_FORMAT_R33)

    def test_every_r33_field_is_read_for_every_measurement_and_track(self):
        outputs = native_product.r33_outputs(native_product.parse_product(self.text))
        self.assertEqual(sorted(outputs["measurements"]), [("0", 0), ("0", 2)])
        for key, fields in outputs["measurements"].items():
            with self.subTest(state=key):
                self.assertEqual(set(fields), set(native_product.R33_MEASUREMENT_FIELDS))
                self.assertEqual(set(fields["residuals"]), set(native_product.RESIDUAL_TYPES))
                self.assertEqual(len(fields["alignment_derivative"]), 2)
                self.assertEqual(len(fields["alignment_derivative"][0]), len(native_product.R32_PLANE_PARAMETERS))
        self.assertEqual(sorted(outputs["tracks"]), ["0"])
        self.assertEqual(set(outputs["tracks"]["0"]), set(native_product.R33_TRACK_FIELDS))
        self.assertEqual(outputs["material_model"], "none")
        self.assertEqual(outputs["alignment_parametrization"], ["t07-plane-rigid/1", "local", "sensor"])
        self.assertEqual(outputs["tracks"]["0"]["charge_status"], "measured")
        self.assertEqual(len(outputs["tracks"]["0"]["residual_covariance"]), 4)

    def test_the_full_covariance_holds_its_identity_and_a_wrong_block_is_caught(self):
        parsed = native_product.parse_product(self.text)
        self.assertEqual(native_product.residual_covariance_defects(parsed, FULL_COVARIANCE_DIAGONAL), [])
        parsed["residual_covariances"][0]["covariance"][0] *= 1.0 + 1e-2
        self.assertEqual(len(native_product.residual_covariance_defects(parsed, FULL_COVARIANCE_DIAGONAL)), 1)

    def test_an_outlier_gets_its_records_with_covariances_that_add(self):
        document = sample_r33_document()
        document["states"][2]["kind"] = "outlier"
        recomputed = native_product.recomputed_residuals(document)
        smoothed, unbiased = recomputed[("0", 2, "smoothed")], recomputed[("0", 2, "unbiased")]
        self.assertEqual(smoothed, unbiased)
        self.assertGreater(smoothed[1][0], document["states"][2]["covariance"][0])  # V + H C H^T: the outlier's states never held its hit

    def test_each_missing_or_wrong_record_is_refused(self):
        lines = self.text.split("\n")
        def without(prefix: str) -> str:
            kept = [line for line in lines if not line.startswith(prefix)]
            return "\n".join(kept)
        cases = {"no unbiased residual": without("residual 0 2 unbiased"), "no measurement output": without("measurement_output 0 0 "),
                 "no track output": without("track_output 0 "), "no conventions line": without("r33_conventions"),
                 "no residual covariance": without("residual_covariance 0 "), "no alignment parametrization": without("alignment_parametrization"),
                 "a residual covariance of the wrong size": self.text.replace("residual_covariance 0 2 ", "residual_covariance 0 3 ", 1),
                 "an unknown alignment parametrization": self.text.replace("t07-plane-rigid/1 local sensor", "t07-plane-rigid/2 local sensor", 1),
                 "unknown residual type": self.text.replace("residual 0 2 unbiased", "residual 0 2 refitted", 1),
                 "residual of a hole": self.text.replace("residual 0 2 unbiased", "residual 0 1 unbiased", 1),
                 "charge against q/p": self.text.replace("track_output 0 1 ", "track_output 0 -1 ", 1),
                 "field against the header": self.text.replace("collision none on", "collision none off", 1),
                 "track output of a failed track": self.text.replace("track_output 0 ", "track_output 1 ", 1),
                 "R33 under the /1 name": self.text.replace("acts-tracking-product/2", "acts-tracking-product/1", 1),
                 "a /2 end with /1 counts": self.text.replace(lines[-2], " ".join(lines[-2].split(" ")[:4]), 1)}
        for label, text in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(native_product.ProductFormatError):
                    native_product.parse_product(text)

    def test_a_version_one_product_still_reads_and_writes_the_same_bytes(self):
        version_one = {"format": native_product.PRODUCT_FORMAT, "header": {name: value for name, value in self.document["header"].items() if name != "r33_conventions"},
                       "tracks": self.document["tracks"], "states": self.document["states"], "parameters": self.document["parameters"]}
        text = native_product.format_product(version_one)
        self.assertTrue(text.startswith("acts-tracking-product/1\n"))
        parsed = native_product.parse_product(text)
        self.assertEqual(native_product.format_product(parsed), text)
        self.assertNotIn("residuals", parsed)
        self.assertEqual(self.text.split("\n")[1:14], text.split("\n")[1:14])  # the same header lines; /2 adds its two after them

    def test_subset_and_merge_keep_the_r33_records_of_their_tracks(self):
        parsed = native_product.parse_product(self.text)
        subset = native_product.subset_tracks(parsed, ["0"], "refit.r33.subset")
        self.assertEqual(len(subset["residuals"]), 8)
        self.assertEqual(len(subset["residual_covariances"]), 1)
        self.assertEqual(native_product.parse_product(native_product.format_product(subset))["residuals"], subset["residuals"])
        other = renamed(sample_r33_document(), {"0": "9", "1": "8"}, "refit.r33b")
        native_product.parse_product(native_product.format_product(other))
        merged = native_product.merge_products(subset, native_product.subset_tracks(other, ["9"], "refit.r33.other"), "refit.r33.merged")
        self.assertEqual(len(merged["residuals"]), 16)
        native_product.parse_product(native_product.format_product(merged))

    def test_the_sidecars_name_the_version_they_map(self):
        sidecars = native_product.sidecars_for_product(native_product.parse_product(self.text), "refit.product")
        self.assertEqual({sidecar["native"]["type"] for sidecar in sidecars}, {native_product.PRODUCT_FORMAT_R33})

    def test_the_recomputation_agrees_with_honest_records_and_catches_a_sign(self):
        parsed = native_product.parse_product(self.text)
        self.assertEqual(native_product.residual_record_defects(parsed, RECOMPUTE_RELATIVE, RECOMPUTE_ABSOLUTE_MM), [])
        flipped = native_product.parse_product(self.text)
        record = next(item for item in flipped["residuals"] if item["state_type"] == "unbiased")
        record["residual"][0] = -record["residual"][0]
        self.assertEqual(len(native_product.residual_record_defects(flipped, RECOMPUTE_RELATIVE, RECOMPUTE_ABSOLUTE_MM)), 1)
        widened = native_product.parse_product(self.text)
        next(item for item in widened["residuals"] if item["state_type"] == "predicted")["covariance"][0] *= 1.0 + 1e-6
        self.assertEqual(len(native_product.residual_record_defects(widened, RECOMPUTE_RELATIVE, RECOMPUTE_ABSOLUTE_MM)), 1)


class AlignmentDerivativeClosedForm(unittest.TestCase):
    """CAI-T07-2's prediction, without ACTS: the closed form against central differences of the exact helix's crossing with the moved plane."""

    @classmethod
    def setUpClass(cls):
        cls.worst = derivative_prediction()

    def test_the_closed_form_agrees_within_the_tolerances_with_margin(self):
        for dof, record in self.worst.items():
            print(f"CAI-T07-2-PREDICTION {native_product.R32_PLANE_PARAMETERS[dof]} error at h {record['error_h']:.2e} at h/4 {record['error_quarter']:.2e} "
                  f"ratio {record['ratio_low']:.4f} to {record['ratio_high']:.4f} largest {record['largest']:.1f}", flush=True)
            tolerance = SHIFT_TOLERANCE if dof < 3 else ROTATION_TOLERANCE_MM_PER_RAD
            with self.subTest(dof=dof):
                self.assertLess(record["error_quarter"] * 5.0, tolerance)

    def test_halving_is_second_order_where_truncation_shows(self):
        for dof in range(3, 6):
            with self.subTest(dof=dof):
                self.assertGreater(self.worst[dof]["ratio_low"], RATIO_BAND[0] + 0.4)
                self.assertLess(self.worst[dof]["ratio_high"], RATIO_BAND[1] - 0.4)
        for dof in range(3):
            self.assertEqual(self.worst[dof]["ratio_high"], 0.0)  # shifts never leave the rounding floor

    def test_a_wrong_sign_or_a_swapped_rotation_fails(self):
        local, local_direction = numpy.array([40.0, -60.0]), numpy.array([0.12, -0.08, 1.0]) / math.sqrt(1.0208)
        position, direction = PLANE_ROTATION @ numpy.array([local[0], local[1], 0.0]), PLANE_ROTATION @ local_direction
        analytic = numpy.array(native_product.closed_form_residual_derivative(local, local_direction))
        differences = numpy.stack([finite_difference(position, direction, 1e-4, numpy.zeros(3), PLANE_ROTATION, dof, 1e-3 / 4) for dof in range(6)], 1)
        self.assertLess(numpy.abs(analytic - differences).max(), ROTATION_TOLERANCE_MM_PER_RAD)
        self.assertGreater(numpy.abs(-analytic - differences).max(), 1.0)
        self.assertGreater(numpy.abs(analytic[:, [0, 1, 2, 4, 3, 5]] - differences).max(), 1.0)


class FixtureLikeHalving(unittest.TestCase):
    """Fix round 1, m3: the halving ratio on states as the fixture makes them, per row, kept apart above 1e-8 and near the floor. P11 is restated on these."""

    @classmethod
    def setUpClass(cls):
        cls.worst = derivative_prediction(trials=300, seed=11, fixture_like=True)

    def test_the_rule_holds_with_margin_and_clear_entries_are_second_order(self):
        for dof in range(6):
            record = self.worst[dof]
            print(f"CAI-T07-2-PREDICTION fixture-like {native_product.R32_PLANE_PARAMETERS[dof]} error at h/4 {record['error_quarter']:.2e} ratio above floor "
                  f"{record['ratio_low']:.4f} to {record['ratio_high']:.4f}, above 1e-8 {record['clear_low']:.4f} to {record['clear_high']:.4f}", flush=True)
            tolerance = SHIFT_TOLERANCE if dof < 3 else ROTATION_TOLERANCE_MM_PER_RAD
            with self.subTest(dof=dof):
                self.assertLess(record["error_quarter"] * 5.0, tolerance)
                if dof >= 3:
                    self.assertTrue(RATIO_BAND[0] < record["ratio_low"] and record["ratio_high"] < RATIO_BAND[1])
                    self.assertTrue(3.98 < record["clear_low"] and record["clear_high"] < 4.02)


class ReferenceDerivativeBroadSample(unittest.TestCase):
    """Fix round 3 (N4): the halving ratios over 16 seeds (20 to 35), 25,600 entries per parameter, the re-reviewer's sample. The rule [3.5, 4.5] does
    not move; P15's ranges are restated from this sample, above the floor and above 1e-8 apart."""

    def test_the_ratios_over_a_broad_sample(self):
        names = ("loc0", "loc1", "phi", "theta", "q/p", "time")
        ranges = {parameter: [math.inf, 0.0, math.inf, 0.0] for parameter in range(6)}
        for seed in range(20, 36):
            for parameter, record in reference_derivative_prediction(seed=seed).items():
                low, high, clear_low, clear_high = ranges[parameter]
                ranges[parameter] = [min(low, record["ratio_low"]), max(high, record["ratio_high"]), min(clear_low, record["clear_low"]), max(clear_high, record["clear_high"])]
        for parameter in (2, 3, 4):
            low, high, clear_low, clear_high = ranges[parameter]
            edge = " AT THE RULE'S EDGE" if high >= RATIO_BAND[1] or low <= RATIO_BAND[0] else ""
            print(f"REFERENCE-DERIVATIVE-PREDICTION broad sample {names[parameter]} ratio above floor {low:.4f} to {high:.4f}, above 1e-8 {clear_low:.4f} to {clear_high:.4f}{edge}",
                  flush=True)
            with self.subTest(parameter=names[parameter]):
                # Fix round 4: the rule is tested above REFERENCE_RATIO_FLOOR only; there it must hold with a wide margin.
                self.assertTrue(RATIO_BAND[0] + 0.4 < clear_low and clear_high < RATIO_BAND[1] - 0.4)
                self.assertTrue(3.9 < clear_low and clear_high < 4.1)


class AlignmentHalvingFloor(unittest.TestCase):
    """Fix round 4: whether CAI-T07-2's alignment-derivative halving test has the reference test's floor issue. It does not: on fixture-like states the
    rotation ratios above the 1e-9 floor stay at least 0.4 inside the band, so its floor stays 1e-9."""

    def test_the_alignment_ratios_stay_inside_the_band_above_the_floor(self):
        worst = derivative_prediction(trials=300, seed=11, fixture_like=True)
        for dof in range(3, 6):
            record = worst[dof]
            print(f"CAI-T07-2-PREDICTION floor check {native_product.R32_PLANE_PARAMETERS[dof]} ratio above 1e-9 {record['ratio_low']:.4f} to {record['ratio_high']:.4f}", flush=True)
            with self.subTest(dof=dof):
                self.assertTrue(RATIO_BAND[0] + 0.4 < record["ratio_low"] and record["ratio_high"] < RATIO_BAND[1] - 0.4)


class ReferenceDerivativePrediction(unittest.TestCase):
    """Fix round 1, M1: the reference derivative's finite differences on the exact helix, without ACTS: truncation at h/4 far under the tolerance, and the
    halving rule met, so a failure in the job is the product's derivative, not the differences."""

    @classmethod
    def setUpClass(cls):
        cls.worst = reference_derivative_prediction()

    def test_the_differences_are_converged_far_under_the_tolerance(self):
        names = ("loc0", "loc1", "phi", "theta", "q/p", "time")
        for parameter, record in self.worst.items():
            print(f"REFERENCE-DERIVATIVE-PREDICTION {names[parameter]} truncation at h/4 {record['truncation']:.2e} relative, ratio {record['ratio_low']:.4f} to "
                  f"{record['ratio_high']:.4f}, at floor {record['at_floor']} of {record['entries']}", flush=True)
            with self.subTest(parameter=names[parameter]):
                self.assertLess(record["truncation"] * 10.0, REFERENCE_RELATIVE)  # fix round 2: 19 times under the plain tolerance at worst (phi)
                if record["ratio_high"] > 0.0:
                    self.assertTrue(RATIO_BAND[0] < record["ratio_low"] and record["ratio_high"] < RATIO_BAND[1])

    def test_the_plain_tolerance_holds_the_differences_and_refutes_another_linearization_point(self):
        """Fix round 2: the product's Jacobians are the propagator's from the smoothed reference state, the differences' too, so the rule is plain,
        |stored - D(h/4)| <= 1e-6 (1 + |stored|). The differences' own truncation stays 20 times under it. A derivative linearized one sigma(q/p) away,
        as the forward filter's chain of fix round 1 was, would fail it by far: the check tells the two linearization points apart."""
        for parameter, record in self.worst.items():
            self.assertLess(record["truncation"] * 10.0, REFERENCE_RELATIVE)
        shifted = linearization_sensitivity(q_over_p_shift=0.00412, angle_shift=1e-4, plain=True)
        print(f"REFERENCE-DERIVATIVE-PREDICTION a linearization 1 sigma(q/p) and 1e-4 rad off moves the derivative by {shifted:.2e} (1 + |a|)", flush=True)
        self.assertGreater(shifted, 100.0 * REFERENCE_RELATIVE)

    def test_a_wrong_chain_would_be_caught(self):
        """dr/dq_ref against plane 8 is not dr/dq_ref against plane 1: the phi column grows with the lever arm, 350 mm, far past the tolerance."""
        bound = [1.0, -2.0, 0.05, 1.5, 1.0 / 3.0, 0.0]
        def derivative(target: int) -> numpy.ndarray:
            plus, minus = list(bound), list(bound)
            plus[2] += 1e-5
            minus[2] -= 1e-5
            return -(reference_crossing(numpy.zeros(3), PLANE_ROTATION, plus, numpy.array([PLANE_Z_MM[target], 0.0, 0.0]))
                     - reference_crossing(numpy.zeros(3), PLANE_ROTATION, minus, numpy.array([PLANE_Z_MM[target], 0.0, 0.0]))) / 2e-5
        self.assertGreater(abs(derivative(7)[0] - derivative(0)[0]), 100.0 * (REFERENCE_RELATIVE * abs(derivative(7)[0]) + REFERENCE_ABSOLUTE))


# Fix round 3 (re-review N2): the forward filter's real linearization points. The fitter carries each step from the previous filtered state, whose
# sigma(q/p) after 3, 4, 5, 6, 7 hits is 16, 6.5, 3.5, 2.1, 1.4 times the eight-hit one, so a uniform shift of the whole chain (covariance_linearization_bound)
# does not bound it. This model: section 4.1 tracks, the hits smeared at 0.020 mm, filtered states as the linear least-squares estimate from the first j hits
# and the start prior (centred on the first hit and the chord to the last, with the assumed q/p), each step's Jacobian taken at that filtered state by
# central differences of the exact helix, against the chain taken along the smoothed trajectory; C from each chain's own D's, as each side forms it.
FILTER_MODEL_STEPS = numpy.array([1e-3, 1e-3, 1e-3, 1e-3, 1e-2]) / 4


def filter_model_transport(q, a, b):
    """Bound states q (N x 5: loc0=y, loc1=z, phi, theta, q/p) on plane x=a to plane x=b along the exact helix (field along z)."""
    y, z, phi, theta, qop = q.T
    tx, ty, tz = numpy.cos(phi) * numpy.sin(theta), numpy.sin(phi) * numpy.sin(theta), numpy.cos(theta)
    w = qop * GEV_PER_TESLA_MM * FIELD_TESLA
    s = (b - a) / tx
    for _ in range(30):
        ws = w * s
        x = a + (tx * numpy.sin(ws) + ty * 2 * numpy.sin(ws / 2) ** 2) / w
        dx = tx * numpy.cos(ws) + ty * numpy.sin(ws)
        s = s - (x - b) / dx
    ws = w * s
    sn, vs = numpy.sin(ws), 2 * numpy.sin(ws / 2) ** 2
    y2 = y + (ty * sn - tx * vs) / w
    z2 = z + tz * s
    tx2, ty2 = tx * numpy.cos(ws) + ty * sn, ty * numpy.cos(ws) - tx * sn
    return numpy.stack([y2, z2, numpy.arctan2(ty2, tx2), numpy.arccos(numpy.clip(tz, -1, 1)), qop], 1)

def filter_model_jacobian(q, a, b):
    cols = []
    for p in range(5):
        plus, minus = q.copy(), q.copy()
        plus[:, p] += FILTER_MODEL_STEPS[p]; minus[:, p] -= FILTER_MODEL_STEPS[p]
        cols.append((filter_model_transport(plus, a, b) - filter_model_transport(minus, a, b)) / (2 * FILTER_MODEL_STEPS[p]))
    return numpy.stack(cols, 2)  # N x 5 x 5

def forward_filter_covariance_model(count, momentum_low, momentum_high, seed):
    g = numpy.random.default_rng(seed)
    p = numpy.exp(g.uniform(math.log(momentum_low), math.log(momentum_high), count))
    qop = g.choice([-1.0, 1.0], count) / p
    su, sv = g.uniform(-0.15, 0.15, count), g.uniform(-0.15, 0.15, count)
    norm = numpy.sqrt(1 + su ** 2 + sv ** 2)
    start = numpy.stack([g.uniform(-0.05, 0.05, count), g.uniform(-30, 30, count), numpy.arctan2(su, 1.0), numpy.arccos(sv / norm), qop], 1)
    truth = filter_model_transport(start, -100.0, 0.0)
    V = HIT_SIGMA_MM ** 2
    truth_at = [truth] + [filter_model_transport(truth, 0.0, PLANE_Z_MM[k]) for k in range(1, 8)]
    design = numpy.concatenate([numpy.eye(5)[None, :2, :].repeat(count, 0)] + [filter_model_jacobian(truth, 0.0, PLANE_Z_MM[k])[:, :2, :] for k in range(1, 8)], 1)  # N x 16 x 5
    noise = g.normal(0.0, HIT_SIGMA_MM, (count, 16))
    prior = numpy.diag([1 / 125.0, 1 / 125.0, 1 / 0.01, 1 / 0.01, 1.0])
    centre = numpy.stack([noise[:, 0], noise[:, 1], (noise[:, 14] - noise[:, 0]) / 350.0, -(noise[:, 15] - noise[:, 1]) / 350.0, numpy.zeros(count)], 1)
    def estimate(hits):
        A = design[:, :2 * hits, :]
        info = prior[None] + numpy.einsum('nia,nib->nab', A, A) / V
        rhs = numpy.einsum('ab,nb->na', prior, centre) + numpy.einsum('nia,ni->na', A, noise[:, :2 * hits]) / V
        return truth + numpy.linalg.solve(info, rhs[..., None])[..., 0]
    smoothed = estimate(8)
    filtered = [filter_model_transport(estimate(j + 1), 0.0, PLANE_Z_MM[j]) if j else estimate(1) for j in range(7)]  # at plane j+1 (index j), after j+1 hits
    def chain_of(step_states):
        J = numpy.eye(5)[None].repeat(count, 0)
        rows = [J[:, :2, :]]
        for j in range(7):
            J = numpy.einsum('nab,nbc->nac', filter_model_jacobian(step_states[j], PLANE_Z_MM[j], PLANE_Z_MM[j + 1]), J)
            rows.append(J[:, :2, :])
        return -numpy.concatenate(rows, 1)
    smoothed_states = [smoothed] + [filter_model_transport(smoothed, 0.0, PLANE_Z_MM[k]) for k in range(1, 7)]
    worst = 0.0
    covs = []
    for states in (smoothed_states, filtered):
        D = chain_of(states)
        C = numpy.linalg.inv(prior[None] + numpy.einsum('nia,nib->nab', D, D) / V)
        covs.append(V * numpy.eye(16)[None] - numpy.einsum('nia,nab,njb->nij', D, C, D))
    S, F = covs
    for k in range(8):
        sl = slice(2 * k, 2 * k + 2)
        scale = numpy.sqrt(S[:, 2 * k, 2 * k] * S[:, 2 * k + 1, 2 * k + 1])
        worst = max(worst, float((numpy.abs(S[:, sl, sl] - F[:, sl, sl]).max(axis=(1, 2)) / scale).max()))
    return worst


def covariance_linearization_bound(q_over_p_shift: float, angle_shift: float, trials: int = 30, seed: int = 3) -> tuple:
    """How far the smoothed residual covariance, V delta - D C D^T with C from the same D's, moves when every D is taken at a state off the fitted one by
    q_over_p_shift and angle_shift: the largest change of a diagonal 2 x 2 block over sqrt(R00 R11), and of any element in 3,000-track se units."""
    generator = numpy.random.default_rng(seed)
    variance = HIT_SIGMA_MM ** 2
    def derivatives(bound):
        rows = []
        for target in range(8):
            centre = numpy.array([PLANE_Z_MM[target], 0.0, 0.0])
            columns = []
            for parameter in range(5):
                step = REFERENCE_STEPS[parameter] / 4
                plus, minus = list(bound), list(bound)
                plus[parameter] += step
                minus[parameter] -= step
                columns.append(-(reference_crossing(numpy.zeros(3), PLANE_ROTATION, plus, centre) - reference_crossing(numpy.zeros(3), PLANE_ROTATION, minus, centre)) / (2 * step))
            rows.append(numpy.stack(columns, 1))
        return numpy.vstack(rows)
    block_worst, element_worst = 0.0, 0.0
    for _ in range(trials):
        q_over_p = float(generator.choice((-1.0, 1.0))) / math.exp(generator.uniform(math.log(1.5), math.log(24.0)))
        slopes = generator.uniform(-0.15, 0.15, 2)
        bound = [generator.uniform(-20.0, 20.0), generator.uniform(-40.0, 40.0), math.atan(slopes[0]),
                 math.acos(slopes[1] / math.sqrt(1.0 + slopes[0] ** 2 + slopes[1] ** 2)), q_over_p, 0.0]
        moved = list(bound)
        moved[2] += angle_shift
        moved[3] -= angle_shift
        moved[4] += q_over_p_shift * float(generator.choice((-1.0, 1.0)))
        covariances = []
        for state in (bound, moved):
            stacked = derivatives(state)
            covariances.append(variance * numpy.eye(16) - stacked @ numpy.linalg.inv(stacked.T @ stacked / variance) @ stacked.T)
        fitted, other = covariances
        for plane in range(8):
            block = slice(2 * plane, 2 * plane + 2)
            block_worst = max(block_worst, float(numpy.abs(fitted[block, block] - other[block, block]).max() / math.sqrt(fitted[2 * plane, 2 * plane] * fitted[2 * plane + 1, 2 * plane + 1])))
        standard_error = numpy.sqrt((numpy.outer(numpy.diag(fitted), numpy.diag(fitted)) + fitted ** 2) / CAI_EVENTS)
        element_worst = max(element_worst, float((numpy.abs(fitted - other) / standard_error).max()))
    return block_worst, element_worst


class ForwardFilterLinearization(unittest.TestCase):
    """Fix round 3 (N2): the 1e-3 diagonal tolerance against the forward filter's real linearization points, one stratum's 3,000 tracks per momentum bin."""

    def test_the_bound_leaves_a_margin_under_the_tolerance(self):
        largest = []
        for low, high in zip(MOMENTUM_BIN_EDGES[:-1], MOMENTUM_BIN_EDGES[1:]):
            largest.append(forward_filter_covariance_model(CAI_EVENTS, low, high, seed=int(low * 10)))
        print("R33-FULL-COVARIANCE-PREDICTION forward-filter linearization, largest diagonal-block difference per momentum bin, 3,000 tracks each: "
              + " ".join(f"{value:.2e}" for value in largest) + f"; margin under {FULL_COVARIANCE_DIAGONAL:g}: {FULL_COVARIANCE_DIAGONAL / max(largest):.1f}", flush=True)
        self.assertLess(max(largest) * 2.5, FULL_COVARIANCE_DIAGONAL)


class FullCovarianceLinearization(unittest.TestCase):
    """Fix round 2: the residual effect left in the diagonal identity. The product's covariance is linearized at the fitted trajectory; ACTS's smoother
    forms its smoothed residual covariance along the forward filter's path, whose q/p before the hits fix it is the assumed one, about one sigma(q/p)
    from the smoothed q/p (4.5 at most). The diagonal blocks then differ by the change of linearization point, not by rounding."""

    def test_the_bound_and_the_tolerance(self):
        typical, largest = covariance_linearization_bound(0.00412, 3e-4 / 4.5), covariance_linearization_bound(4.5 * 0.00412, 3e-4)
        print(f"R33-FULL-COVARIANCE-PREDICTION linearization 1 sigma(q/p) off: diagonal blocks {typical[0]:.2e} relative, elements {typical[1]:.3f} se; "
              f"4.5 sigma off: {largest[0]:.2e} relative, {largest[1]:.3f} se", flush=True)
        self.assertLess(largest[0] * 4.0, FULL_COVARIANCE_DIAGONAL)
        self.assertLess(largest[1], 0.1)  # the empirical check cannot see it


class RigidShiftDesign(unittest.TestCase):
    """CAI-T07-1's numbers, fixed before the run."""

    def test_the_fit_without_the_tested_hit_is_overdetermined_in_both_views(self):
        for view in (0, 1):
            for plane in range(1, 9):
                self.assertTrue(fit_is_overdetermined(view, plane))

    def test_sigma_of_the_mean_and_the_reported_expectations(self):
        for view, name in ((0, "loc0"), (1, "loc1")):
            widths = [unbiased_sigma_mm(view, plane) for plane in range(1, 9)]
            influence = [closed_form_influence(view, plane) if plane != SHIFTED_PLANE else float("nan") for plane in range(1, 9)]
            print(f"CAI-T07-1-DESIGN {name} unbiased sigma mm " + " ".join(f"{width:.5f}" for width in widths) + " sigma of mean mm "
                  + " ".join(f"{sigma_of_mean_mm(view, plane):.6f}" for plane in range(1, 9)) + " influence of plane 4 " + " ".join(f"{value:+.4f}" for value in influence), flush=True)
            self.assertAlmostEqual(widths[SHIFTED_PLANE - 1], (0.023566, 0.021454)[view], delta=1e-6)
            self.assertLess(MEAN_N_SIGMA * sigma_of_mean_mm(view, SHIFTED_PLANE), SHIFT_MM / 20.0)
        self.assertAlmostEqual(closed_form_influence(0, 8), -0.42857, delta=1e-5)
        self.assertAlmostEqual(reported_expectation_mm(0, SHIFT_MM, 5), 0.3719 * SHIFT_MM, delta=1e-5 * SHIFT_MM)

    def test_the_family_of_asserted_means_and_widths_rarely_fails_a_correct_fit(self):
        means = len(CAI_STRATA) * (2 * 2 + 16)  # fix round 1, m2: both coordinates on the tested plane in each shifted run, every plane in the nominal one
        widths = len(CAI_STRATA) * sum(2 * 8 + 2 * (8 - resolved_from(view) + 1) for view in (0, 1))
        covariance_elements = len(CAI_STRATA) * 16 * 17 // 2
        self.assertEqual((means, widths, covariance_elements), (80, 216, 544))
        self.assertLess(family_false_failure(means + widths + covariance_elements), 0.01)

    def test_the_judges_pass_an_honest_mean_and_fail_a_shifted_one(self):
        sigma = sigma_of_mean_mm(0, SHIFTED_PLANE)
        self.assertEqual(mean_defects(-SHIFT_MM + 3.0 * sigma, -SHIFT_MM, sigma, "honest"), [])
        self.assertEqual(len(mean_defects(-SHIFT_MM + 5.0 * sigma, -SHIFT_MM, sigma, "off")), 1)
        self.assertEqual(len(mean_defects(SHIFT_MM, -SHIFT_MM, sigma, "wrong sign")), 1)
        generator = numpy.random.default_rng(5)
        self.assertEqual(width_defects(generator.normal(size=CAI_EVENTS), "honest"), [])
        self.assertEqual(len(width_defects(1.1 * generator.normal(size=CAI_EVENTS), "wide")), 1)

    def test_where_the_predicted_and_filtered_widths_are_read(self):
        self.assertEqual((resolved_from(0), resolved_from(1)), (4, 3))

    def test_the_expectation_rule_follows_r37(self):
        self.assertEqual(expected_mean_mm(0, SHIFT_MM, 0, SHIFTED_PLANE), -SHIFT_MM)
        self.assertEqual(expected_mean_mm(1, -SHIFT_MM, 1, SHIFTED_PLANE), SHIFT_MM)
        self.assertEqual(expected_mean_mm(0, SHIFT_MM, 1, SHIFTED_PLANE), 0.0)
        self.assertIsNone(expected_mean_mm(0, SHIFT_MM, 1, 2))  # fix round 1, m2: reported, not asserted
        self.assertIsNone(expected_mean_mm(0, SHIFT_MM, 0, 2))
        self.assertEqual(reported_expectation_mm(0, SHIFT_MM, 2, view=1), 0.0)

    def test_the_empirical_covariance_judge_passes_honest_toys_and_fails_a_wrong_correlation(self):
        generator = numpy.random.default_rng(12)
        covariance = numpy.array([[4e-4, -1e-4], [-1e-4, 3e-4]])
        products = numpy.outer(numpy.diag(covariance), numpy.diag(covariance)) + covariance ** 2
        sample = generator.multivariate_normal(numpy.zeros(2), covariance, size=CAI_EVENTS)
        self.assertEqual(empirical_covariance_defects(sample, covariance, products, "honest"), [])
        wrong = covariance.copy()
        wrong[0, 1] = wrong[1, 0] = 0.0
        self.assertEqual(len(empirical_covariance_defects(sample, wrong, numpy.outer(numpy.diag(wrong), numpy.diag(wrong)) + wrong ** 2, "uncorrelated")), 1)


class DerivativeCheckProgram(unittest.TestCase):
    """The check program states the numbers of this module, and the CMake file builds it as a data-side program that links no generator code."""

    def test_the_program_holds_the_numbers_of_this_module(self):
        text = (NATIVE / "cai_track_output_check.cpp").read_text(encoding="utf-8")
        for name, value in (("tracks_per_stratum", "25"), ("shift_step_mm", "1e-3"), ("rotation_step_rad", "1e-3"), ("halvings", "2"), ("shift_tolerance", "1e-8"),
                            ("rotation_tolerance_mm_per_rad", "1e-5"), ("acts_closed_form_tolerance", "1e-8"), ("ratio_low", "3.5"), ("ratio_high", "4.5"),
                            ("rounding_floor", "1e-9"), ("rigidity_tolerance", "1e-12"), ("unbiased_acts_sigma", "1e-9"), ("unbiased_acts_covariance", "1e-7"),
                            ("leave_one_out_predicted_sigma", "1e-3"), ("reference_relative", "1e-6"), ("reference_absolute", "1e-6"), ("reference_ratio_floor", "1e-8")):
            with self.subTest(name=name):
                self.assertRegex(text, rf"constexpr (double|int) {name} = {re.escape(value)};")
        self.assertIn("reference_steps{1e-3, 1e-3, 1e-3, 1e-3, 1e-2, 1e-3}", text)
        self.assertEqual(REFERENCE_STEPS, (1e-3, 1e-3, 1e-3, 1e-3, 1e-2, 1e-3))

    def test_the_target_is_data_side(self):
        cmake = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")
        target = re.search(r"add_executable\(cai_track_output_check ([^)]*)\)", cmake).group(1).split()
        self.assertEqual(target, ["cai_track_output_check.cpp", "payload_geometry.cpp", "kalman_refit.cpp"])


# ---- Built: the job runs these.

def run_program(arguments) -> subprocess.CompletedProcess:
    finished = subprocess.run([str(item) for item in arguments], capture_output=True, text=True, timeout=3600)
    if finished.returncode != 0:
        raise AssertionError(f"{arguments[0]} exit {finished.returncode}: {finished.stdout[-4000:]}{finished.stderr[-4000:]}")
    return finished


class StratumFiles:
    """One CAI clean stratum of block 1: the frozen generator's data and truth files, and the hit sets the scoring side derives from truth."""

    def __init__(self, folder: Path, stratum: int):
        self.folder, self.stratum = folder, stratum
        self.data_file, self.truth_file = folder / f"cai-clean-{stratum}.t07data", folder / f"cai-clean-{stratum}.t07truth"
        run_program([CAI_GENERATOR, "generate", "--fixture", "cai-clean", "--block", CAI_BLOCK, "--stratum", stratum, "--first-event", 0, "--count", CAI_EVENTS,
                     "--data-file", self.data_file, "--truth-file", self.truth_file])
        header = truth_files.read_truth_header(self.truth_file)
        if (header["fixture_id"], header["block"], header["stratum"]) != (CAI_FIXTURE_ID, CAI_BLOCK, stratum):
            raise AssertionError(f"the truth file says {header}")
        self.hit_sets = []
        for ordinal, event in enumerate(truth_files.iter_truth_events(self.truth_file)):
            (track,) = event["tracks"]
            self.hit_sets.append((f"event-{ordinal}", ordinal, float(track["q_over_p"]), [int(key) for key in track["hit_keys"]]))

    def hit_sets_file(self, data_file: Path, name: str) -> Path:
        path = self.folder / f"{name}.hitsets"
        path.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), self.hit_sets), encoding="utf-8")
        return path

    def refit(self, data_file: Path, name: str, keep: bool = False) -> tuple:
        product = self.folder / f"{name}.product"
        run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", self.hit_sets_file(data_file, name), "--field-tesla", FIELD_TESLA, "--product-id", name,
                     "--product-file", product])
        text = product.read_text(encoding="utf-8")
        if not keep:
            product.unlink()
        return native_product.parse_product(text), text


def full_covariance_sample(document: dict) -> tuple:
    """Each fitted track's 16 smoothed residuals in state order (loc0, loc1 of each), the mean of the stored covariances, and the mean of S_ii S_jj + S_ij^2."""
    smoothed = {(item["track_key"], item["state_index"]): item["residual"] for item in document["residuals"] if item["state_type"] == "smoothed"}
    measured = {}
    for state in document["states"]:
        if state["kind"] == "measurement":
            measured.setdefault(state["track_key"], []).append(state["index"])
    rows, total, products = [], numpy.zeros((16, 16)), numpy.zeros((16, 16))
    for item in document["residual_covariances"]:
        indices = sorted(measured[item["track_key"]])
        if len(indices) != 8:
            raise AssertionError(f"{item['track_key']} has {len(indices)} measurements, not 8")
        rows.append([value for index in indices for value in smoothed[(item["track_key"], index)]])
        matrix = numpy.array(native_product.residual_covariance_matrix(item))
        total += matrix
        products += numpy.outer(numpy.diag(matrix), numpy.diag(matrix)) + matrix ** 2
    return numpy.array(rows), total / len(rows), products / len(rows)


def unbiased_arrays(document: dict) -> dict:
    """Per plane: the unbiased residuals and their variances, in track order, from the product's records."""
    plane_of = {(state["track_key"], state["index"]): state["plane"] for state in document["states"]}
    arrays = {}
    for record in document["residuals"]:
        plane = plane_of[(record["track_key"], record["state_index"])]
        arrays.setdefault((record["state_type"], plane), []).append(list(record["residual"]) + [record["covariance"][0], record["covariance"][2]])
    return {key: numpy.array(rows) for key, rows in arrays.items()}


@unittest.skipUnless(BUILT, NOT_BUILT)
class TrackFitOutputsRun(unittest.TestCase):
    """The refit's R33 outputs on the CAI clean fixture, CAI-T07-1 and CAI-T07-2. Interface checks, no alignment quality claim (R31)."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.nominal, cls.shifted, cls.files, cls.defects, cls.full = {}, {}, {}, {}, {}
        cls.kept_text = None
        for stratum in CAI_STRATA:
            started = time.monotonic()
            files = StratumFiles(folder, stratum)
            cls.files[stratum] = files
            document, text = files.refit(files.data_file, f"cai-nominal-{stratum}", keep=stratum == 0)
            if stratum == 0:
                cls.kept_text, cls.kept_product = text, folder / "cai-nominal-0.product"
            cls.defects[stratum] = {"failed": [track["key"] for track in document["tracks"] if track["status"] != "fitted"],
                                    "records": native_product.residual_record_defects(document, RECOMPUTE_RELATIVE, RECOMPUTE_ABSOLUTE_MM),
                                    "outputs": len(native_product.r33_outputs(document)["measurements"]),
                                    "diagonal": native_product.residual_covariance_defects(document, FULL_COVARIANCE_DIAGONAL),
                                    "diagonal_largest": native_product.residual_covariance_largest_difference(document),
                                    "covariances": len(document["residual_covariances"])}
            cls.full[stratum] = full_covariance_sample(document)
            cls.nominal[stratum] = unbiased_arrays(document)
            del document, text
            fitted = time.monotonic()
            for name, coordinate, displacement in SHIFT_CASES:
                shifted_file = folder / f"cai-clean-{stratum}-shifted-{name}.t07data"
                header = fixture_files.read_data_header(files.data_file)  # fix round 1, n3: the source file's sigma, not this module's constant
                if header["sigma_loc0_mm"] != header["sigma_loc1_mm"]:
                    raise AssertionError("the data file states two sigmas, which encode_data_file cannot carry")
                shifted_file.write_bytes(fixture_files.encode_data_file(header["sigma_loc0_mm"], shifted_events(files.data_file, SHIFTED_PLANE, coordinate, displacement)))
                grid = fixture_files.data_file_defects(shifted_file)
                if grid:
                    raise AssertionError(f"the shifted file is not a data file: {grid}")
                document, _ = files.refit(shifted_file, f"cai-shifted-{name}-{stratum}")
                cls.shifted[(stratum, name)] = unbiased_arrays(document)
                del document
                shifted_file.unlink()
            print(f"R33-COST stratum {stratum} events {CAI_EVENTS} nominal_seconds {fitted - started:.1f} shifted_seconds {time.monotonic() - fitted:.1f}", flush=True)

    def test_every_fit_holds_every_r33_record_and_they_are_the_recomputed_ones(self):
        for stratum in CAI_STRATA:
            defects = self.defects[stratum]
            print(f"R33-RECORDS stratum {stratum} failed {len(defects['failed'])} measurement_outputs {defects['outputs']} recomputation_defects {len(defects['records'])}", flush=True)
            print(f"R33-FULL-COVARIANCE-DIAGONAL stratum {stratum} largest {defects['diagonal_largest']:.3e} relative, tolerance {FULL_COVARIANCE_DIAGONAL:g}, "
                  f"defects {len(defects['diagonal'])}", flush=True)
            with self.subTest(stratum=stratum):
                self.assertEqual(defects["failed"], [])
                self.assertEqual(defects["outputs"], 8 * CAI_EVENTS)
                self.assertEqual(defects["records"][:5], [])
                self.assertEqual(defects["covariances"], CAI_EVENTS)
                self.assertEqual(defects["diagonal"][:5], [])

    def test_the_full_residual_covariance_is_the_empirical_one(self):
        """Fix round 1, M2: over the fixture's own smearing, the 16 smoothed residuals of each stratum's tracks against the mean stored covariance."""
        defects = []
        for stratum in CAI_STRATA:
            residuals, mean_covariance, mean_products = self.full[stratum]
            empirical = residuals.T @ residuals / residuals.shape[0]
            standard_error = numpy.sqrt(mean_products / residuals.shape[0])
            largest = float(numpy.max(numpy.abs(empirical - mean_covariance) / standard_error))
            correlation = mean_covariance / numpy.sqrt(numpy.outer(numpy.diag(mean_covariance), numpy.diag(mean_covariance)))
            print(f"R33-FULL-COVARIANCE stratum {stratum} tracks {residuals.shape[0]} largest |empirical - stored| {largest:.2f} se, stored correlations "
                  f"{float(correlation[numpy.triu_indices(16, 1)].min()):+.3f} to {float(correlation[numpy.triu_indices(16, 1)].max()):+.3f}", flush=True)
            defects += empirical_covariance_defects(residuals, mean_covariance, mean_products, f"stratum {stratum}")
        self.assertEqual(defects, [])

    def test_a_real_product_survives_python_and_the_driver_byte_for_byte(self):
        self.assertEqual(native_product.format_product(native_product.parse_product(self.kept_text)), self.kept_text)
        again = Path(self.folder.name) / "again.product"
        run_program([DRIVER, "rewrite-product", "--product-in", self.kept_product, "--product-file", again])
        self.assertEqual(again.read_text(encoding="utf-8"), self.kept_text)

    def test_residual_pulls_have_unit_width(self):
        defects = []
        for stratum in CAI_STRATA:
            for state_type in native_product.RESIDUAL_TYPES:
                for plane in range(1, 9):
                    rows = self.nominal[stratum][(state_type, plane)]
                    for view in (0, 1):
                        if state_type in ("predicted", "filtered") and plane < resolved_from(view):
                            continue
                        pulls = rows[:, view] / numpy.sqrt(rows[:, 2 + view])
                        width = float(numpy.sqrt(numpy.mean(pulls ** 2)))
                        print(f"R33-PULL stratum {stratum} {state_type} plane {plane} {('loc0', 'loc1')[view]} width {width:.4f}", flush=True)
                        defects += width_defects(pulls, f"stratum {stratum} {state_type} plane {plane} view {view}")
        self.assertEqual(defects, [])

    def test_the_unbiased_covariance_is_the_closed_form(self):
        defects = []
        for stratum in CAI_STRATA:
            for plane in range(1, 9):
                rows = self.nominal[stratum][("unbiased", plane)]
                for view in (0, 1):
                    ratio = float(numpy.mean(rows[:, 2 + view])) / unbiased_sigma_mm(view, plane) ** 2
                    print(f"R33-UNBIASED-COVARIANCE stratum {stratum} plane {plane} {('loc0', 'loc1')[view]} mean R / closed form {ratio:.6f}", flush=True)
                    if abs(ratio - 1.0) > COVARIANCE_AGREEMENT:
                        defects.append(f"stratum {stratum} plane {plane} view {view}: {ratio:.6f}")
        self.assertEqual(defects, [])

    def test_cai_t07_1_nominal_means_are_zero(self):
        defects = []
        for stratum in CAI_STRATA:
            for plane in range(1, 9):
                rows = self.nominal[stratum][("unbiased", plane)]
                for view in (0, 1):
                    mean = float(numpy.mean(rows[:, view]))
                    print(f"CAI-T07-1 nominal stratum {stratum} plane {plane} {('loc0', 'loc1')[view]} mean {mean:+.6f} mm expected +0.000000 "
                          f"limit {MEAN_N_SIGMA * sigma_of_mean_mm(view, plane):.6f}", flush=True)
                    defects += mean_defects(mean, 0.0, sigma_of_mean_mm(view, plane), f"nominal stratum {stratum} plane {plane} view {view}")
        self.assertEqual(defects, [])

    def test_cai_t07_1_rigid_shift(self):
        defects = []
        for stratum in CAI_STRATA:
            for name, coordinate, displacement in SHIFT_CASES:
                arrays = self.shifted[(stratum, name)]
                for plane in range(1, 9):
                    for view in (0, 1):
                        mean = float(numpy.mean(arrays[("unbiased", plane)][:, view]))
                        expected = expected_mean_mm(coordinate, displacement, view, plane)
                        label = f"CAI-T07-1 shift {name} {displacement:+.4f} stratum {stratum} plane {plane} {('loc0', 'loc1')[view]} mean {mean:+.6f} mm"
                        paired = arrays[("unbiased", plane)][:, view] - self.nominal[stratum][("unbiased", plane)][:, view]
                        paired_expected = expected if expected is not None else reported_expectation_mm(coordinate, displacement, plane, view)
                        paired_text = (f"paired mean {float(numpy.mean(paired)):+.6f} largest |paired - expected| {float(numpy.max(numpy.abs(paired - paired_expected))):.2e}")
                        if expected is None:
                            print(f"{label} REPORTED linear expectation {reported_expectation_mm(coordinate, displacement, plane, view):+.6f} {paired_text}", flush=True)
                            continue
                        print(f"CAI-T07-1-PAIRED shift {name} stratum {stratum} plane {plane} {('loc0', 'loc1')[view]} {paired_text}", flush=True)
                        print(f"{label} expected {expected:+.6f} limit {MEAN_N_SIGMA * sigma_of_mean_mm(view, plane):.6f}", flush=True)
                        defects += mean_defects(mean, expected, sigma_of_mean_mm(view, plane), label)
        self.assertEqual(defects, [])

    def test_cai_t07_2_derivatives_and_the_unbiased_state_against_acts(self):
        for stratum in CAI_STRATA:
            files = self.files[stratum]
            first = files.hit_sets[:DERIVATIVE_TRACKS_PER_STRATUM]
            hit_sets = files.folder / f"derivative-{stratum}.hitsets"
            hit_sets.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(files.data_file), first), encoding="utf-8")
            finished = subprocess.run([str(CHECK_PROGRAM), "--data-file", str(files.data_file), "--hit-sets", str(hit_sets), "--field-tesla", "1"],
                                      capture_output=True, text=True, timeout=3600)
            lines = finished.stdout.splitlines()
            for line in lines:
                if not line.startswith("PASS"):
                    print(f"CAI-T07-2 stratum {stratum} {line}", flush=True)
            print(f"CAI-T07-2 stratum {stratum} PASS lines {sum(line.startswith('PASS') for line in lines)}, stderr bytes {len(finished.stderr)}", flush=True)
            with self.subTest(stratum=stratum):
                self.assertEqual(lines[0] if lines else "", DERIVATIVE_CONFIG)
                self.assertEqual(finished.returncode, 0, finished.stderr[-2000:])
                self.assertEqual([line for line in lines if line.startswith(("FAIL", "STOPPED"))], [])
                self.assertEqual(lines[-1], "RESULT PASS")


if __name__ == "__main__":
    unittest.main()
