"""adapters/acts-tracking: the alignment payload of the refit, CAI-T07-3 (refit with the corrected payload) and CAI-T07-4 (sagitta weak mode) (plan R32, R33, R37;
t07-t09-task-sheets.md, T07; t04-values-v4.md section 4.1, "CAI items"; D1 stage 9 brief). Interface checks on synthetic fixtures, no alignment quality claim (R31, R37).

The payload. t07-alignment-payload/1 (fixture_tools/t07_alignment_payload.py states the format; native/alignment_payload.* is the driver's reader): per plane, its
t07-plane-rigid/1 delta (payload_geometry.hpp's PlaneDelta, the R32 parametrization of the R33 alignment derivatives), applied by `acts_tracking_driver refit
--alignment-payload FILE` through the placement route (PlacedTelescope::with_deltas; user's choice 16). Its content identity is the SHA-256 of its bytes and the product
records it (header line alignment_payload); a payload derived from another keeps the chosen parameters, puts every other one at nominal, and records its parent (R33).
A malformed payload, a plane the telescope has not, and a payload derived against another nominal geometry are refused, never applied (R32).

CAI-T07-3, fixed before the run (R37). CAI fixture 7003 (CAI clean), block 1, 4 strata of CAI_EVENTS events, one track per event, the hit sets from truth with the truth
q/p assumed, field 1 T, exactly as CAI-T07-1 (test_acts_track_outputs.py). Convention, as CAI-T07-1's: the TRUE plane 4 sits at +d along one local measurement
direction (loc0 by +SHIFT_MM, loc1 by -SHIFT_MM, each in its own run): the frozen generator's data file with that plane's coordinate lowered by d. Three fits per case:
the nominal fit of the unshifted file (CAI-T07-1's nominal run), the fit of the shifted file at nominal geometry (CAI-T07-1's shifted run, the fit "without the shift"),
and the refit of the shifted file with the payload that holds the shift: a payload derived from the parent payload {plane 4: shift-loc0 +d, shift-loc1 -d} keeping only
the case's coordinate. With the reconstruction plane placed at +d, the lowered hit is the same global point as the unshifted one, so the refit is expected to equal the
nominal fit up to rounding.
- Residual means, asserted: the unbiased residual mean of the payload refit is 0 within MEAN_N_SIGMA sigma of the mean on plane 4 in both coordinates and on every other plane
  in both coordinates (sigma of the mean from the fixture's generated statistics: sigma sqrt(1 + h_j) / sqrt(CAI_EVENTS), CAI-T07-1's). 16 means per case per stratum.
- chi2, asserted: chi2/ndf (ndf = measured coordinates - 5) of the payload refit against the nominal fit, per stratum: |difference of the means| <= MEAN_N_SIGMA x se, se
  sqrt(s_a^2 / N_a + s_b^2 / N_b) from the two samples (independent-sample; the samples share their events, so this is conservative); and the two-sample
  Kolmogorov-Smirnov distance <= KS_COEFFICIENT sqrt((N_a + N_b) / (N_a N_b)), KS_COEFFICIENT = sqrt(-ln(p / 2) / 2) at p = erfc(MEAN_N_SIGMA / sqrt 2), the same
  two-sided 6.8e-6 as each mean.
- q/p, asserted: the pull t = (q/p_fit - q/p_true) / sigma(q/p)_fit, per stratum, |difference of the means| <= MEAN_N_SIGMA x se, se as above.
- Control, asserted: the fit without the payload must fail what the payload refit must pass (otherwise the comparison has no power): its plane-4 mean in the shifted
  coordinate, its chi2/ndf (closed form +0.639 in loc0, +0.772 in loc1: d^2 (1 - H_jj) / sigma^2 / 11), and in loc0 its q/p pull (closed form -1.205: 2 d g_c / (k B sigma)).
- Paired, reported: per event, payload refit minus nominal fit, unbiased residuals, chi2 and q/p; predicted at most PAIRED_PREDICTED_MM, a rounding level.
The family: 128 means, 8 chi2 means, 8 KS distances, 8 q/p means: 152 checks at 6.8e-6, 0.10 %.

CAI-T07-4, fixed before the run (R37; v4 section 4.1). CAI fixture 7004 (CAI sagitta, plane i truly at nominal + d_i along +u, d_i = A ((z_i - 175)^2 - 13125 mm^2),
A = 5 sigma(q/p) k B / 2), the frozen generator, block 1, the same 4 strata and counts, field 1 T, fitted at nominal geometry with no vertex or beam constraint (none enters
the refit). Against fixture 7003's nominal fit. The closed form: a hit that reads u - d_i looks like q/p raised by 2 A / (k B) = 0.0206 per GeV, 5 stated sigma(q/p) (0.00412
per GeV), the same sign for both charges.
- Bins: per charge (the truth charge) and in the bending coordinate u, read as the fitted loc0 at the track's reference state (plane 1), edges BENDING_BIN_EDGES_MM, so
  4 x 2 = 8 cells over the 4 strata pooled (R37's bins), each about 1,500 tracks per fixture; and per stratum (32 cells) as readings, the lowest momentum bin among them.
- In each cell: Delta = mean(q/p_fit - q/p_true) over 7004 minus the same over 7003, divided by sigma_cell = sqrt(mean of the fitted variances over both samples): the
  change in q/p over the per-track resolution in that bin (R37); and divided by the stated 0.00412 (v4: "against that stated sigma(q/p)"). Beside it the change in mean
  chi2/ndf and its se, sqrt(s_a^2 / N_a + s_b^2 / N_b): the spread's definition.
- Self-check, asserted: in the most-affected cell (the largest Delta / sigma_cell), Delta / sigma_cell >= K_WEAK and Delta / 0.00412 >= K_WEAK, K_WEAK = 4.5 (below v4's 4.6),
  and the change in mean chi2/ndf within WEAK_N_SIGMA = 4.5 se, in that cell and over all tracks. If it fails, the step fails and nothing is changed (v4: a regeneration is
  the user's word).
- Expected (WeakModeDesign, an exact-helix least-squares fit of the fixture's tracks with the refit's q/p prior): Delta / sigma_cell 5.003 in every cell and every stratum, Delta /
  0.00412 4.92 (superseded by fix round 1, M1, below); the bins flat (v4: a rigid shift of each plane does not depend on u). Neglected by the closed form, with the size this module computes: the q/p prior's pull,
  (sigma / 1.0 per GeV)^2 = 1.7e-5 of the bias; the slope factor n (1 + u'^2) of the curvature, which scales the bias and sigma(q/p) alike and so cancels in Delta / sigma_cell but
  not in Delta / 0.00412 (hence 4.92); the second-order term, first order in curvature, exact minus linear at most 1.6e-4 sigma at 1.5 to 3 GeV, falling as 1/p; the
  one-pass linearization about the assumed (truth) q/p, at most about 0.003 sigma (kalman_refit.hpp: 0.003 sigma at 10 % off in [1.5, 3) GeV, and the sagitta moves q/p by
  0.0206 per GeV, under 10 % of q/p at 1.5 to 3 GeV); a second pass from each fit's own q/p is printed beside it. The chi2/ndf change: about 2e-4, under 0.02 of its se.
- Readings, not asserted: every cell, flatness (sum of squared deviations of the 8 cells' Delta / sigma_cell from their mean, in se, against 7 degrees of freedom), the
  charge-antisymmetric bias in |p|, and the second pass.

D1 stage 9 fix round 1 (review d1-stage9-review.md, the coordinator's rulings), fixed before the run; the text above stays and is superseded where it differs:
- M1: "Delta / 0.00412 4.92 in every bin; flat" is superseded. In stated sigma the bias scales as cos(lambda) / (1 + t_u^2)^{3/2}, and t_u sets the bending bin (u at plane 1 is
  about 100 mm x t_u), so the stated-unit cells are not flat: about 4.88 in the outer u bins and 4.96 in the inner ones (WeakModeDesign prints them per bin and pooled; 4.92
  is the pooled mean). In per-track units every cell is 5.003, flat.
- M2: the k criterion is asserted in EVERY cell, in both units (Delta / sigma_cell >= K_WEAK and Delta / 0.00412 >= K_WEAK), and the chi2 criterion in every cell and over all
  tracks: the bins are expected flat, so the most-affected bin is any bin (STATE.md, r37_uncovered_cases). The most-affected cell is still printed. Predicted margins
  (WeakModeDesign): about 13.8 se per track in every cell; in stated units about 10.6 se in the outer cells and 12.8 in the inner ones.
- m1: the driver's refusal test first runs the honest payload on the same files (exit 0, a product), and each refusal must name the payload on stderr.
- m2: the two sidecars' payload_id, origin and producer source are printed to the log. m4: the zero-payload reading (placement route with nothing moved gives the plain
  geometry's /1 records) is asserted: the refusal against another geometry rests on PlacedTelescope's nominal transforms being build_telescope_geometry()'s.
- m5: a payload labelled nominal that moves a plane is refused (R32: nominal is the ideal geometry). n4: the product line's identities are 64 lowercase hex, in both readers.
- n1: the bins are on the fitted loc0 at plane 1, which the sagitta moves by d_1 = 0.054 mm: about 0.4 % of tracks change bin, harmless since the bias does not depend on u.
- n2: the control q/p prediction -1.205 is in stated sigma; the rule compares pulls in fitted sigma, about -1.226 (x 0.00412 / 0.00405).

Every built test needs the build job and skips without it; that job counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_cai_refit -v
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy

from tests.adapters import test_acts_track_outputs as outputs_tests

native_product, fixture_files, truth_files = outputs_tests.native_product, outputs_tests.fixture_files, outputs_tests.truth_files
ROOT, NATIVE = outputs_tests.ROOT, outputs_tests.NATIVE
sys.path.insert(0, str(outputs_tests.ADAPTER / "assets" / "fixture_tools"))
import t07_alignment_payload as alignment_payload  # noqa: E402

from contracts.conditions import check_binding, payload_identity  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402

BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
DRIVER = Path(BUILD_DIR) / "acts_tracking_driver"
CAI_GENERATOR = Path(BUILD_DIR) / "t07_cai_fixture_generator"
BUILT = bool(BUILD_DIR) and DRIVER.is_file() and CAI_GENERATOR.is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built program: this test needs the T07 build job, which runs it"

# Section 4.1 and the CAI items.
HIT_SIGMA_MM = 0.020
PLANE_Z_MM = 50.0 * numpy.arange(8)
GEV_PER_TESLA_MM = 0.299792458e-3
FIELD_TESLA = 1.0
STATED_SIGMA_QOP = 0.00412
SAGITTA_BIAS_IN_SIGMA = 5.0
SAGITTA_A_PER_MM = SAGITTA_BIAS_IN_SIGMA * STATED_SIGMA_QOP * GEV_PER_TESLA_MM * FIELD_TESLA / 2.0
V4_DISPLACEMENTS_MM = (0.05404, 0.00772, -0.02316, -0.03860, -0.03860, -0.02316, 0.00772, 0.05404)
V4_A_PER_MM = 3.0879e-6
V4_CLOSED_FORM_RISE = 0.0206
SAGITTA_FIXTURE_ID = 7004
CAI_STRATA, CAI_EVENTS, CAI_BLOCK = outputs_tests.CAI_STRATA, outputs_tests.CAI_EVENTS, outputs_tests.CAI_BLOCK
MOMENTUM_BIN_EDGES = outputs_tests.MOMENTUM_BIN_EDGES
REFIT_PRIOR_QOP_SIGMA = 1.0  # kalman_refit.hpp, refit_prior_qop_sigma_per_gev

# CAI-T07-3, fixed before the run.
SHIFTED_PLANE, SHIFT_MM, SHIFT_CASES = outputs_tests.SHIFTED_PLANE, outputs_tests.SHIFT_MM, outputs_tests.SHIFT_CASES
MEAN_N_SIGMA = 4.5
TWO_SIDED_P = math.erfc(MEAN_N_SIGMA / math.sqrt(2.0))
KS_COEFFICIENT = math.sqrt(-math.log(TWO_SIDED_P / 2.0) / 2.0)
FIT_PARAMETERS = 5
PAIRED_PREDICTED_MM = 1e-9
CASE_PARAMETER = {"loc0": "shift-loc0", "loc1": "shift-loc1"}

# CAI-T07-4, fixed before the run.
K_WEAK = 4.5           # R37's k: below v4's 4.6, against the per-track resolution in the bin and against the stated 0.00412
WEAK_N_SIGMA = 4.5     # the chi2/ndf change within this many se
BENDING_BIN_EDGES_MM = (-7.5, 0.0, 7.5)  # fitted loc0 at plane 1: about a quarter of the tracks each (slopes +-0.15 over 100 mm)
SECOND_PASS_PREDICTED_SIGMA = 0.003


# ---- The arithmetic, numpy only: nothing here reads ACTS.

def sagitta_displacements_mm() -> numpy.ndarray:
    return SAGITTA_A_PER_MM * ((PLANE_Z_MM - 175.0) ** 2 - 13125.0)


def helix_hits(start_x_mm, parameters: numpy.ndarray) -> numpy.ndarray:
    """The exact helix of section 4.1's uniform field along ACTS z, crossing the eight planes x = PLANE_Z_MM: hits (u0, v0, u1, v1, ...) per track.
    parameters (N, 5): u, v at x = start_x_mm (one value, or one per track), du/dx, dv/dx there, q/p. dT/ds = w T x z, w = (q/p) k B (kalman_refit.cpp, start_of): the transverse angle
    falls at rate w per unit path, so u'' = -w at zero slope."""
    u_start, v_start, slope_u, slope_v, q_over_p = parameters.T
    bending = q_over_p * GEV_PER_TESLA_MM * FIELD_TESLA
    norm = numpy.sqrt(1.0 + slope_u ** 2 + slope_v ** 2)
    transverse, along_v = numpy.sqrt(1.0 + slope_u ** 2) / norm, slope_v / norm
    angle = numpy.arctan(slope_u)
    hits = numpy.empty((parameters.shape[0], 16))
    for index, plane_x in enumerate(PLANE_Z_MM):
        later = numpy.arcsin(numpy.sin(angle) - bending * (plane_x - start_x_mm) / transverse)
        path = (angle - later) / bending
        hits[:, 2 * index] = u_start + (transverse / bending) * (numpy.cos(later) - numpy.cos(angle))
        hits[:, 2 * index + 1] = v_start + along_v * path
    return hits


FIT_START_X_MM = -50.0
FIT_STEPS = numpy.array([1e-4, 1e-4, 1e-6, 1e-6, 1e-6])


def helix_jacobian(parameters: numpy.ndarray) -> numpy.ndarray:
    jacobian = numpy.empty((parameters.shape[0], 16, FIT_PARAMETERS))
    for column in range(FIT_PARAMETERS):
        step = numpy.zeros(FIT_PARAMETERS)
        step[column] = FIT_STEPS[column]
        jacobian[:, :, column] = (helix_hits(FIT_START_X_MM, parameters + step) - helix_hits(FIT_START_X_MM, parameters - step)) / (2.0 * FIT_STEPS[column])
    return jacobian


def least_squares_helix(hits: numpy.ndarray, start: numpy.ndarray, prior_centre: numpy.ndarray, iterations: int = 5) -> tuple:
    """Gauss-Newton on the exact helix with the refit's q/p prior (width REFIT_PRIOR_QOP_SIGMA, centred on the assumed q/p); its loc and angle priors are
    10 mm and 0.1 rad against 0.02 mm and 1e-4 rad, so left out. Returns the parameters, their covariance and the chi2 with the prior term."""
    weight, prior_weight = 1.0 / HIT_SIGMA_MM ** 2, 1.0 / REFIT_PRIOR_QOP_SIGMA ** 2
    parameters = start.copy()
    for _ in range(iterations):
        jacobian = helix_jacobian(parameters)
        normal = numpy.einsum("nik,nil->nkl", jacobian, jacobian) * weight
        normal[:, 4, 4] += prior_weight
        gradient = numpy.einsum("nik,ni->nk", jacobian, (hits - helix_hits(FIT_START_X_MM, parameters)) * weight)
        gradient[:, 4] += prior_weight * (prior_centre - parameters[:, 4])
        parameters = parameters + numpy.linalg.solve(normal, gradient[..., None])[..., 0]
    jacobian = helix_jacobian(parameters)
    normal = numpy.einsum("nik,nil->nkl", jacobian, jacobian) * weight
    normal[:, 4, 4] += prior_weight
    chi2 = numpy.sum((hits - helix_hits(FIT_START_X_MM, parameters)) ** 2, axis=1) * weight + prior_weight * (parameters[:, 4] - prior_centre) ** 2
    return parameters, numpy.linalg.inv(normal), chi2


def fixture_tracks(count: int, momentum_bin: int, seed: int) -> dict:
    """Tracks drawn as section 4.1 states them (vertex u +-0.05 mm at z -100 +- 0.2 mm, v +-30 mm; slopes +-0.15; log-uniform momentum in the bin; random charge)."""
    generator = numpy.random.default_rng(seed)
    low, high = MOMENTUM_BIN_EDGES[momentum_bin], MOMENTUM_BIN_EDGES[momentum_bin + 1]
    charge = numpy.where(generator.uniform(size=count) < 0.5, 1.0, -1.0)
    momentum = numpy.exp(generator.uniform(math.log(low), math.log(high), count))
    vertex = numpy.column_stack([generator.uniform(-0.05, 0.05, count), generator.uniform(-30.0, 30.0, count), generator.uniform(-0.15, 0.15, count),
                                 generator.uniform(-0.15, 0.15, count), charge / momentum])
    vertex_x = generator.uniform(-100.2, -99.8, count)
    return {"charge": charge, "q_over_p": charge / momentum, "hits": helix_hits(vertex_x, vertex), "vertex": vertex}


def weak_mode_design(count: int = 1200, seed: int = 41) -> dict:
    """Per momentum bin, the exact-helix fit of noiseless fixture tracks, clean and with the sagitta (hit u - d_i): the per-track bias, sigma(q/p), the linear prediction,
    the chi2 change, and the cell values the built test forms."""
    design = {}
    displacement = numpy.zeros(16)
    displacement[0::2] = -sagitta_displacements_mm()
    for momentum_bin in range(4):
        tracks = fixture_tracks(count, momentum_bin, seed + momentum_bin)
        first = numpy.column_stack([tracks["hits"][:, 0] + (tracks["hits"][:, 2] - tracks["hits"][:, 0]) * FIT_START_X_MM / 50.0,
                                    tracks["hits"][:, 1] + (tracks["hits"][:, 3] - tracks["hits"][:, 1]) * FIT_START_X_MM / 50.0,
                                    (tracks["hits"][:, 2] - tracks["hits"][:, 0]) / 50.0, (tracks["hits"][:, 3] - tracks["hits"][:, 1]) / 50.0, tracks["q_over_p"]])
        clean, covariance, _ = least_squares_helix(tracks["hits"], first, tracks["q_over_p"])
        deformed, _, chi2 = least_squares_helix(tracks["hits"] + displacement, clean, tracks["q_over_p"])
        sigma = numpy.sqrt(covariance[:, 4, 4])
        jacobian = helix_jacobian(clean)
        linear = numpy.einsum("nk,nik,i->n", covariance[:, 4, :], jacobian, displacement) / HIT_SIGMA_MM ** 2
        bias = deformed[:, 4] - clean[:, 4]
        u_plane_one = tracks["hits"][:, 0]
        cells, cells_stated = {}, {}
        for charge in (1.0, -1.0):
            for bending_bin in range(len(BENDING_BIN_EDGES_MM) + 1):
                chosen = (tracks["charge"] == charge) & (numpy.digitize(u_plane_one, BENDING_BIN_EDGES_MM) == bending_bin)
                cells[(int(charge), bending_bin)] = float(numpy.mean(bias[chosen]) / math.sqrt(numpy.mean(sigma[chosen] ** 2)))
                cells_stated[(int(charge), bending_bin)] = float(numpy.mean(bias[chosen]) / STATED_SIGMA_QOP)
        design[momentum_bin] = {"sigma": sigma, "bias": bias, "linear": linear, "chi2_change": chi2, "cells": cells, "cells_stated": cells_stated, "u_plane_one": u_plane_one,
                                "ratio": bias / sigma, "ratio_stated": bias / STATED_SIGMA_QOP, "second_order": numpy.abs(bias - linear) / sigma}
    return design


def weak_mode_expectation(design: dict, tracks_per_fixture: int = 4 * CAI_EVENTS) -> dict:
    """Fix round 1 (M1, M2): per bending bin, the 4 momentum bins pooled as the built test pools the strata, the expected Delta / sigma_cell and Delta / 0.00412, the share of
    tracks, the se of a cell (one charge: half the bin's share of tracks_per_fixture in each fixture) in both units, and the margin over K_WEAK in se."""
    bias = numpy.concatenate([entry["bias"] for entry in design.values()])
    sigma = numpy.concatenate([entry["sigma"] for entry in design.values()])
    bins = bending_bin_of(numpy.concatenate([entry["u_plane_one"] for entry in design.values()]))
    expected = {}
    for bending_bin in range(len(BENDING_BIN_EDGES_MM) + 1):
        chosen = bins == bending_bin
        sigma_cell = math.sqrt(float(numpy.mean(sigma[chosen] ** 2)))
        tracks = 0.5 * float(numpy.mean(chosen)) * tracks_per_fixture
        se = math.sqrt(2.0 / tracks)
        per_track, stated = float(numpy.mean(bias[chosen])) / sigma_cell, float(numpy.mean(bias[chosen])) / STATED_SIGMA_QOP
        se_stated = se * sigma_cell / STATED_SIGMA_QOP
        expected[bending_bin] = {"per_track": per_track, "stated": stated, "share": float(numpy.mean(chosen)), "se": se, "se_stated": se_stated,
                                 "margin": (per_track - K_WEAK) / se, "margin_stated": (stated - K_WEAK) / se_stated}
    return expected


def bending_bin_of(u_mm) -> numpy.ndarray:
    return numpy.digitize(numpy.asarray(u_mm, float), BENDING_BIN_EDGES_MM)


def weak_mode_cells(deformed: dict, clean: dict) -> dict:
    """deformed and clean: arrays charge, u_plane_one, residual (q/p_fit - q/p_true), variance (of the fitted q/p), chi2_per_ndf. One entry per (charge, bending bin)."""
    cells = {}
    for charge in (1, -1):
        for bending_bin in range(len(BENDING_BIN_EDGES_MM) + 1):
            chosen_d = (deformed["charge"] == charge) & (bending_bin_of(deformed["u_plane_one"]) == bending_bin)
            chosen_c = (clean["charge"] == charge) & (bending_bin_of(clean["u_plane_one"]) == bending_bin)
            residual_d, residual_c = deformed["residual"][chosen_d], clean["residual"][chosen_c]
            sigma = math.sqrt(float(numpy.mean(numpy.concatenate([deformed["variance"][chosen_d], clean["variance"][chosen_c]]))))
            delta = float(numpy.mean(residual_d) - numpy.mean(residual_c))
            se = math.sqrt(float(numpy.var(residual_d, ddof=1)) / residual_d.size + float(numpy.var(residual_c, ddof=1)) / residual_c.size)
            chi2_d, chi2_c = deformed["chi2_per_ndf"][chosen_d], clean["chi2_per_ndf"][chosen_c]
            cells[(charge, bending_bin)] = {"tracks": (int(residual_d.size), int(residual_c.size)), "ratio": delta / sigma, "ratio_stated": delta / STATED_SIGMA_QOP,
                                            "ratio_se": se / sigma, "sigma": sigma, "chi2_change": float(numpy.mean(chi2_d) - numpy.mean(chi2_c)),
                                            "chi2_se": math.sqrt(float(numpy.var(chi2_d, ddof=1)) / chi2_d.size + float(numpy.var(chi2_c, ddof=1)) / chi2_c.size)}
    return cells


def weak_mode_self_check(deformed: dict, clean: dict, k: float = K_WEAK, n_sigma: float = WEAK_N_SIGMA) -> dict:
    """R37's self-check: the curvature bias is at least k per-track resolutions and k stated sigmas, while the change in mean chi2/ndf stays within n_sigma of its se.
    Fix round 1 (M2): asserted in every cell (the bins are expected flat, so the most-affected bin is any bin), and the chi2 change over all tracks too; the most-affected
    cell (largest Delta / sigma_cell) is still named."""
    cells = weak_mode_cells(deformed, clean)
    most = max(cells, key=lambda key: cells[key]["ratio"])
    overall = float(numpy.mean(deformed["chi2_per_ndf"]) - numpy.mean(clean["chi2_per_ndf"]))
    overall_se = math.sqrt(float(numpy.var(deformed["chi2_per_ndf"], ddof=1)) / deformed["chi2_per_ndf"].size
                           + float(numpy.var(clean["chi2_per_ndf"], ddof=1)) / clean["chi2_per_ndf"].size)
    defects = []
    for key, each in sorted(cells.items()):
        if not (each["ratio"] >= k and each["ratio_stated"] >= k):
            defects.append(f"cell {key}: bias {each['ratio']:.3f} per-track sigmas and {each['ratio_stated']:.3f} stated sigmas, not both at least k = {k}")
        if abs(each["chi2_change"]) > n_sigma * each["chi2_se"]:
            defects.append(f"cell {key}: chi2/ndf changes by {each['chi2_change']:+.4f}, more than {n_sigma} x {each['chi2_se']:.4f}")
    if abs(overall) > n_sigma * overall_se:
        defects.append(f"all tracks: chi2/ndf changes by {overall:+.4f}, more than {n_sigma} x {overall_se:.4f}")
    return {"cells": cells, "most": most, "overall_chi2_change": overall, "overall_chi2_se": overall_se, "defects": defects}


def flatness(cells: dict) -> tuple:
    """Sum over the cells of ((ratio - mean ratio) / ratio_se)^2, and its degrees of freedom: a reading of whether the bending-coordinate bins are flat."""
    ratios = numpy.array([cell["ratio"] for cell in cells.values()])
    errors = numpy.array([cell["ratio_se"] for cell in cells.values()])
    return float(numpy.sum(((ratios - numpy.mean(ratios)) / errors) ** 2)), len(ratios) - 1


def weak_mode_toys(design: dict, amplitude_in_sigma: float, chi2_change_per_ndf: float, per_bin: int, seed: int, only_cell: tuple = None) -> tuple:
    """Gaussian toys of the two fits' outputs from the design's tracks: q/p residuals with the design's sigma, the bias scaled to amplitude_in_sigma / 5, and chi2/ndf
    from a chi2 with 11 degrees of freedom plus chi2_change_per_ndf."""
    generator = numpy.random.default_rng(seed)
    samples = []
    for deformed in (True, False):
        columns = {"charge": [], "u_plane_one": [], "residual": [], "variance": [], "chi2_per_ndf": []}
        for momentum_bin, entry in design.items():
            pick = generator.integers(0, entry["sigma"].size, per_bin)
            sigma = entry["sigma"][pick]
            bias = entry["bias"][pick] * amplitude_in_sigma / SAGITTA_BIAS_IN_SIGMA if deformed else numpy.zeros(per_bin)
            charge = numpy.where(generator.uniform(size=per_bin) < 0.5, 1, -1)
            if deformed and only_cell is not None:  # fix round 1 (M2): a deformation in one cell only
                bias = numpy.where((charge == only_cell[0]) & (bending_bin_of(entry["u_plane_one"][pick]) == only_cell[1]), bias, 0.0)
            columns["charge"].append(charge)
            columns["u_plane_one"].append(entry["u_plane_one"][pick])
            columns["residual"].append(bias + sigma * generator.standard_normal(per_bin))
            columns["variance"].append(sigma ** 2)
            columns["chi2_per_ndf"].append(generator.chisquare(11, per_bin) / 11.0 + (chi2_change_per_ndf if deformed else 0.0))
        samples.append({name: numpy.concatenate(values) for name, values in columns.items()})
    return samples[0], samples[1]


def mean_difference_defects(first, second, label: str, n_sigma: float = MEAN_N_SIGMA) -> list:
    first, second = numpy.asarray(first, float), numpy.asarray(second, float)
    difference = float(numpy.mean(first) - numpy.mean(second))
    se = math.sqrt(float(numpy.var(first, ddof=1)) / first.size + float(numpy.var(second, ddof=1)) / second.size)
    return [] if abs(difference) <= n_sigma * se else [f"{label}: means differ by {difference:+.5f}, more than {n_sigma} x {se:.5f}"]


def ks_distance(first, second) -> float:
    first, second = numpy.sort(numpy.asarray(first, float)), numpy.sort(numpy.asarray(second, float))
    points = numpy.concatenate([first, second])
    return float(numpy.max(numpy.abs(numpy.searchsorted(first, points, side="right") / first.size - numpy.searchsorted(second, points, side="right") / second.size)))


def ks_limit(first_count: int, second_count: int) -> float:
    return KS_COEFFICIENT * math.sqrt((first_count + second_count) / (first_count * second_count))


def ks_defects(first, second, label: str) -> list:
    distance, limit = ks_distance(first, second), ks_limit(len(first), len(second))
    return [] if distance <= limit else [f"{label}: KS distance {distance:.4f} over {limit:.4f}"]


def shift_chi2_change_per_ndf(view: int) -> float:
    """A hit moved by d raises the least-squares chi2 by d^2 (1 - H_jj) / sigma^2, H the hat matrix of the view's design."""
    design = outputs_tests.design_matrix(view)
    hat = design @ numpy.linalg.inv(design.T @ design) @ design.T
    return (SHIFT_MM / HIT_SIGMA_MM) ** 2 * (1.0 - hat[SHIFTED_PLANE - 1, SHIFTED_PLANE - 1]) / (16 - FIT_PARAMETERS)


def shift_q_over_p_pull() -> float:
    """loc0 of plane 4 read d lower: the fitted curvature c moves by -d g_c, u'' = 2 c = -k B q/p, so q/p moves by 2 d g_c / (k B); in units of the stated sigma."""
    design = outputs_tests.design_matrix(0)
    gain = numpy.linalg.inv(design.T @ design) @ design.T
    return 2.0 * SHIFT_MM * gain[2, SHIFTED_PLANE - 1] / (GEV_PER_TESLA_MM * FIELD_TESLA) / STATED_SIGMA_QOP


def honest_payload(geometry_id: str) -> str:
    return alignment_payload.encode_payload({SHIFTED_PLANE: [SHIFT_MM, -SHIFT_MM, 0.0, 0.0, 0.0, 0.0]}, geometry_id, "measured")


def wrong_payloads(geometry_id: str) -> dict:
    """One defect each: refused, never applied (R32)."""
    honest = honest_payload(geometry_id)
    other_geometry = hashlib.sha256(b"a telescope with one plane moved by 1 mm: another nominal geometry").hexdigest()
    return {"another nominal geometry": honest.replace(geometry_id, other_geometry),
            "malformed: five values": honest.replace(f"plane {SHIFTED_PLANE} 0.0625 -0.0625 0 0 0 0\n", f"plane {SHIFTED_PLANE} 0.0625 -0.0625 0 0 0\n"),
            "malformed: another first line": honest.replace("t07-alignment-payload/1\n", "t07-alignment-payload/0\n"),
            "malformed: no end record": honest.replace("end 1\n", ""),
            "malformed: not a decimal number": honest.replace(" 0.0625 -0.0625 ", " 0x1p-4 -0.0625 "),
            "a plane that does not exist": honest.replace(f"plane {SHIFTED_PLANE} ", "plane 9 "),
            "plane 0": honest.replace(f"plane {SHIFTED_PLANE} ", "plane 0 "),
            "labelled nominal, a plane moved": honest.replace("origin measured", "origin nominal")}


class PayloadFormat(unittest.TestCase):
    """t07-alignment-payload/1 in Python: the bytes the driver takes, the mapping to plane deltas, and every refusal (R32)."""

    def setUp(self):
        self.geometry = alignment_payload.nominal_geometry_id()

    def test_an_honest_payload_reads_back_and_maps_to_plane_deltas(self):
        text = honest_payload(self.geometry)
        self.assertEqual(text, "t07-alignment-payload/1\nparametrization t07-plane-rigid/1 local sensor\nderived_against " + self.geometry +
                         "\norigin measured\nderived_from none\nplane 4 0.0625 -0.0625 0 0 0 0\nend 1\n")
        payload = alignment_payload.parse_payload(text, self.geometry)
        deltas = alignment_payload.plane_deltas(payload)
        self.assertEqual(deltas[3], [SHIFT_MM, -SHIFT_MM, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual([index for index, delta in enumerate(deltas) if any(delta)], [3])
        self.assertEqual(payload["content_id"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(alignment_payload.PLANE_PARAMETERS, native_product.R32_PLANE_PARAMETERS)
        self.assertEqual(list(alignment_payload.PARAMETRIZATION), native_product.ALIGNMENT_PARAMETRIZATION)

    def test_each_wrong_payload_is_refused(self):
        for name, text in wrong_payloads(self.geometry).items():
            with self.subTest(name=name), self.assertRaises(alignment_payload.PayloadFormatError):
                alignment_payload.parse_payload(text, self.geometry)
        honest = honest_payload(self.geometry)
        for name, text in {"a plane twice": honest.replace("end 1\n", "plane 4 0 0 0 0 0 0\nend 2\n"),
                           "out of order": honest.replace("plane 4 ", "plane 5 ").replace("end 1\n", "plane 4 0 0 0 0 0 0\nend 2\n"),
                           "a wrong end count": honest.replace("end 1\n", "end 2\n"), "text after the end": honest + "plane 5 0 0 0 0 0 0\n",
                           "unfinished last line": honest[:-1], "another parametrization": honest.replace("t07-plane-rigid/1 local sensor", "t07-plane-rigid/1 global sensor"),
                           "an origin that is neither": honest.replace("origin measured", "origin simulated"), "an infinite value": honest.replace(" 0.0625 -0.0625 ", " 1e999 -0.0625 "),
                           "a short identity": honest.replace(self.geometry, self.geometry[:63]), "an upper-case identity": honest.replace(self.geometry, self.geometry.upper()),
                           "a leading zero": honest.replace("plane 4 ", "plane 04 "), "a source that is no identity": honest.replace("derived_from none", "derived_from parent")}.items():
            with self.subTest(name=name), self.assertRaises(alignment_payload.PayloadFormatError):
                alignment_payload.parse_payload(text, self.geometry)

    def test_the_native_reader_states_the_same_rules(self):
        native = (NATIVE / "alignment_payload.cpp").read_text(encoding="utf-8")
        header = (NATIVE / "alignment_payload.hpp").read_text(encoding="utf-8")
        self.assertIn(f'alignment_payload_format[] = "{alignment_payload.PAYLOAD_FORMAT}"', header)
        self.assertIn(f'nominal_geometry_format[] = "{alignment_payload.GEOMETRY_FORMAT}"', header)
        self.assertIn(f'decimal_number(R"({alignment_payload._DECIMAL.pattern})")', native)
        self.assertIn(f'count_text(R"({alignment_payload._COUNT.pattern})")', native)
        self.assertIn(f'identity_text(R"({alignment_payload._HEX.pattern})")', native)
        for words in ("twice or out of order", "does not count its plane records", "the telescope has planes 1 to", "derived against the geometry", "not a decimal number",
                      "text after the alignment payload's end record", "last line is not finished"):
            self.assertIn(words, native)

    def test_the_nominal_geometry_text_and_its_identity(self):
        text = alignment_payload.nominal_geometry_text()
        lines = text.split("\n")
        self.assertEqual(lines[:3], ["t07-telescope-nominal/1", "planes 8", "plane 1 rectangle -150 -150 150 150 0 0 1 1 0 0 0 1 0 0 0 0"])
        self.assertEqual(lines[9], "plane 8 rectangle -150 -150 150 150 0 0 1 1 0 0 0 1 0 350 0 0")
        self.assertRegex(alignment_payload.nominal_geometry_id(), r"^[0-9a-f]{64}$")


class DerivedPayloadIdentity(unittest.TestCase):
    """R33: a subset of a payload's parameters is a new payload, with the others at nominal, its own identity and the payload it came from (R32 sidecar too)."""

    def setUp(self):
        self.geometry = alignment_payload.nominal_geometry_id()
        self.parent = alignment_payload.encode_payload({2: [0.01, 0.0, 0.0, 0.0, 0.0, 2e-4], SHIFTED_PLANE: [SHIFT_MM, -SHIFT_MM, 0.0, 0.0, 0.0, 0.0]}, self.geometry)

    def test_a_subset_has_its_own_identity_and_names_its_parent(self):
        for name, parameter in CASE_PARAMETER.items():
            with self.subTest(case=name):
                child_text = alignment_payload.derive_subset(self.parent, {SHIFTED_PLANE: [parameter]})
                child, parent = alignment_payload.parse_payload(child_text, self.geometry), alignment_payload.parse_payload(self.parent, self.geometry)
                self.assertNotEqual(child["content_id"], parent["content_id"])
                self.assertEqual(child["derived_from"], parent["content_id"])
                deltas = alignment_payload.plane_deltas(child)
                kept = [SHIFT_MM if name == "loc0" else 0.0, -SHIFT_MM if name == "loc1" else 0.0, 0.0, 0.0, 0.0, 0.0]
                self.assertEqual(deltas[SHIFTED_PLANE - 1], kept)
                self.assertEqual(sum(1 for delta in deltas if any(delta)), 1)  # plane 2 at nominal
                self.assertEqual((child["derived_against"], child["origin"]), (parent["derived_against"], parent["origin"]))

    def test_the_sidecars_are_conditions_payloads_with_their_identities(self):
        parent_sidecar = alignment_payload.payload_sidecar(self.parent, "cai-t07-3-parent", "synthetic CAI-T07-3 fixture: the generated shift, no measurement")
        child_text = alignment_payload.derive_subset(self.parent, {SHIFTED_PLANE: ["shift-loc0"]})
        child_sidecar = alignment_payload.payload_sidecar(child_text, "cai-t07-3-loc0", "synthetic CAI-T07-3 fixture: the generated shift, no measurement", parent_sidecar)
        for sidecar in (parent_sidecar, child_sidecar):
            self.assertEqual([finding.code for finding in read_sidecar(sidecar).errors], [])
            self.assertEqual(sidecar["payload_id"], payload_identity(sidecar))
        self.assertEqual(child_sidecar["derived_from"], parent_sidecar["payload_id"])
        self.assertEqual(child_sidecar["content_sha256"], alignment_payload.payload_content_id(child_text))
        self.assertNotEqual(child_sidecar["payload_id"], parent_sidecar["payload_id"])
        self.assertEqual(child_sidecar["alignment"]["degrees_of_freedom"], [{"structure": "plane-4", "parameters": ["shift-loc0"], "frame": "local", "level": "sensor"}])
        self.assertEqual([finding.code for finding in check_binding(child_sidecar, {"origin": "measured", "geometry_id": self.geometry}).errors], [])
        self.assertIn("conditions.geometry_mismatch", [finding.code for finding in check_binding(child_sidecar, {"origin": "measured", "geometry_id": "0" * 64}).errors])
        with self.assertRaises(alignment_payload.PayloadFormatError):
            alignment_payload.payload_sidecar(child_text, "cai-t07-3-loc0", "synthetic", None)
        with self.assertRaises(alignment_payload.PayloadFormatError):
            alignment_payload.payload_sidecar(child_text, "cai-t07-3-loc0", "synthetic", child_sidecar)

    def test_a_subset_of_what_the_parent_lacks_is_refused(self):
        with self.assertRaises(alignment_payload.PayloadFormatError):
            alignment_payload.derive_subset(self.parent, {5: ["shift-loc0"]})
        with self.assertRaises(alignment_payload.PayloadFormatError):
            alignment_payload.derive_subset(self.parent, {SHIFTED_PLANE: ["shift-sideways"]})


class ProductRecordsThePayload(unittest.TestCase):
    """R32: a product records the identity and round of the payload it consumed. The line exists in /2 only, and only when a payload was applied."""

    def test_the_line_round_trips_and_is_refused_where_it_does_not_belong(self):
        document = outputs_tests.sample_r33_document()
        text = native_product.format_product(document)
        self.assertNotIn("alignment_payload ", text)
        with_payload = dict(document, header=dict(document["header"], alignment_payload={"content_sha256": "a" * 64, "origin": "measured", "derived_against": "b" * 64,
                                                                                        "derived_from": "c" * 64, "round": "none"}))
        payload_text = native_product.format_product(with_payload)
        self.assertIn(f"\nalignment_parametrization t07-plane-rigid/1 local sensor\nalignment_payload {'a' * 64} measured {'b' * 64} {'c' * 64} none\ntrack ", payload_text)
        self.assertEqual(native_product.format_product(native_product.parse_product(payload_text)), payload_text)
        self.assertEqual(native_product.parse_product(payload_text)["header"]["alignment_payload"]["content_sha256"], "a" * 64)
        version_one = native_product.version_one_of(native_product.parse_product(text))
        with self.assertRaises(native_product.ProductFormatError):
            native_product.format_product(dict(version_one, header=dict(version_one["header"], alignment_payload=with_payload["header"]["alignment_payload"])))
        for wrong in (payload_text.replace(" measured ", " simulated "), payload_text.replace(" none\ntrack ", "\ntrack "),
                      payload_text.replace(f"alignment_payload {'a' * 64}", f"alignment_payload {'a' * 63}"), payload_text.replace(f" {'b' * 64} ", f" {'B' * 64} "),
                      payload_text.replace(f" {'c' * 64} none\n", " parent none\n"), payload_text.replace(f" {'c' * 64} none\n", f" {'c' * 64} first\n")):
            with self.assertRaises(native_product.ProductFormatError):
                native_product.parse_product(wrong)
        other = dict(with_payload, header=dict(with_payload["header"], product_id="other"))
        with self.assertRaises(native_product.ProductFormatError):
            native_product.merge_products(document, other, "merged")


class RefitDesign(unittest.TestCase):
    """CAI-T07-3's numbers, fixed before the run: sigma of the mean, the controls' closed forms, and the judges on honest and shifted toys."""

    def test_the_tolerances_and_the_controls(self):
        limits = [[MEAN_N_SIGMA * outputs_tests.sigma_of_mean_mm(view, plane) for plane in range(1, 9)] for view in (0, 1)]
        print("CAI-T07-3-DESIGN limit of each residual mean, mm, loc0 " + " ".join(f"{value:.6f}" for value in limits[0]) + "; loc1 " +
              " ".join(f"{value:.6f}" for value in limits[1]), flush=True)
        print(f"CAI-T07-3-DESIGN control without the payload: chi2/ndf change loc0 {shift_chi2_change_per_ndf(0):+.4f} loc1 {shift_chi2_change_per_ndf(1):+.4f}; "
              f"q/p pull in loc0 {shift_q_over_p_pull():+.4f}; KS coefficient {KS_COEFFICIENT:.4f}, limit at 3,000 and 3,000 {ks_limit(CAI_EVENTS, CAI_EVENTS):.4f}; "
              f"family of 152 checks {152 * TWO_SIDED_P:.4%}", flush=True)
        self.assertAlmostEqual(limits[0][SHIFTED_PLANE - 1], 1.94e-3, delta=1e-5)
        self.assertAlmostEqual(shift_chi2_change_per_ndf(0), 0.6394, places=4)
        self.assertAlmostEqual(shift_chi2_change_per_ndf(1), 0.7715, places=4)
        self.assertAlmostEqual(shift_q_over_p_pull(), -1.2048, places=3)
        self.assertAlmostEqual(KS_COEFFICIENT, 2.509, places=3)
        self.assertLess(152 * TWO_SIDED_P, 1.1e-3)

    def test_the_judges_pass_honest_toys_and_fail_the_shift(self):
        generator = numpy.random.default_rng(7)
        chi2_a, chi2_b = generator.chisquare(11, CAI_EVENTS) / 11.0, generator.chisquare(11, CAI_EVENTS) / 11.0
        self.assertEqual(mean_difference_defects(chi2_a, chi2_b, "chi2") + ks_defects(chi2_a, chi2_b, "chi2"), [])
        shifted = chi2_a + shift_chi2_change_per_ndf(0)
        self.assertTrue(mean_difference_defects(shifted, chi2_b, "chi2"))
        self.assertTrue(ks_defects(shifted, chi2_b, "chi2"))
        pulls_a, pulls_b = generator.standard_normal(CAI_EVENTS), generator.standard_normal(CAI_EVENTS)
        self.assertEqual(mean_difference_defects(pulls_a, pulls_b, "q/p"), [])
        self.assertTrue(mean_difference_defects(pulls_a + shift_q_over_p_pull(), pulls_b, "q/p"))


class WeakModeDesign(unittest.TestCase):
    """CAI-T07-4's numbers from v4's closed form and from an exact-helix fit of the fixture's tracks, and the self-check on toys, fixed before the run."""

    @classmethod
    def setUpClass(cls):
        cls.design = weak_mode_design()

    def test_the_fixture_is_v4s(self):
        self.assertTrue(numpy.allclose(sagitta_displacements_mm(), V4_DISPLACEMENTS_MM, atol=5e-6))
        self.assertAlmostEqual(SAGITTA_A_PER_MM, V4_A_PER_MM, delta=1e-10)
        self.assertAlmostEqual(2.0 * SAGITTA_A_PER_MM / (GEV_PER_TESLA_MM * FIELD_TESLA), V4_CLOSED_FORM_RISE, delta=1e-4)
        self.assertAlmostEqual(float(numpy.mean(sagitta_displacements_mm())), 0.0, delta=1e-15)
        self.assertLess(K_WEAK, 4.6)

    def test_the_expected_bias_per_bin_and_what_the_closed_form_neglects(self):
        for momentum_bin, entry in self.design.items():
            cells = entry["cells"]
            second_order = float(numpy.max(entry["second_order"]))
            print(f"CAI-T07-4-DESIGN momentum bin {momentum_bin} ({MOMENTUM_BIN_EDGES[momentum_bin]} to {MOMENTUM_BIN_EDGES[momentum_bin + 1]} GeV) sigma(q/p) "
                  f"{float(numpy.mean(entry['sigma'])):.6f} ({float(numpy.min(entry['sigma'])):.6f} to {float(numpy.max(entry['sigma'])):.6f}) per GeV; bias per-track sigmas "
                  f"{float(numpy.mean(entry['ratio'])):.4f} ({float(numpy.min(entry['ratio'])):.4f} to {float(numpy.max(entry['ratio'])):.4f}); stated sigmas "
                  f"{float(numpy.mean(entry['ratio_stated'])):.4f} ({float(numpy.min(entry['ratio_stated'])):.4f} to {float(numpy.max(entry['ratio_stated'])):.4f}); "
                  f"exact minus linear at most {second_order:.2e} sigma; chi2 change {float(numpy.mean(entry['chi2_change'])):.2e} (at most "
                  f"{float(numpy.max(entry['chi2_change'])):.2e}); cells " + " ".join(f"{key[0]:+d}/{key[1]} {value:.4f}" for key, value in sorted(cells.items())) +
                  "; stated-sigma cells (fix round 1, M1) " + " ".join(f"{key[0]:+d}/{key[1]} {value:.3f}" for key, value in sorted(entry["cells_stated"].items())), flush=True)
            with self.subTest(momentum_bin=momentum_bin):
                for value in cells.values():
                    self.assertAlmostEqual(value, 5.0, delta=0.01)  # flat in the bending coordinate and in charge
                self.assertGreater(float(numpy.min(entry["ratio_stated"])), K_WEAK)
                self.assertLess(second_order, 5e-4)
                self.assertLess(float(numpy.max(entry["chi2_change"])), 0.05)
        expected = weak_mode_expectation(self.design)
        for bending_bin, entry in expected.items():
            print(f"CAI-T07-4-EXPECTATION bending bin {bending_bin} (fitted loc0 at plane 1, edges {BENDING_BIN_EDGES_MM} mm) share {entry['share']:.3f}: per-track sigmas "
                  f"{entry['per_track']:.3f} (se {entry['se']:.4f}, margin over k {entry['margin']:.1f} se), stated sigmas {entry['stated']:.3f} (se {entry['se_stated']:.4f}, "
                  f"margin over k {entry['margin_stated']:.1f} se); both charges alike", flush=True)
            self.assertAlmostEqual(entry["per_track"], 5.003, delta=0.002)
            self.assertGreater(min(entry["margin"], entry["margin_stated"]), 8.0)
        self.assertAlmostEqual(expected[0]["stated"], 4.88, delta=0.02)
        self.assertAlmostEqual(expected[3]["stated"], 4.88, delta=0.02)
        self.assertAlmostEqual(expected[1]["stated"], 4.96, delta=0.02)
        self.assertAlmostEqual(expected[2]["stated"], 4.96, delta=0.02)
        orders = [float(numpy.max(self.design[momentum_bin]["second_order"])) for momentum_bin in range(4)]
        self.assertGreater(orders[0], 2.5 * orders[2])  # first order in curvature: it falls with momentum, so the lowest bin bounds it
        pull_back = (STATED_SIGMA_QOP / REFIT_PRIOR_QOP_SIGMA) ** 2
        print(f"CAI-T07-4-DESIGN q/p prior pull on the bias {pull_back:.2e} of it ({pull_back * SAGITTA_BIAS_IN_SIGMA:.1e} sigma); the one-pass linearization at most "
              f"{SECOND_PASS_PREDICTED_SIGMA} sigma (kalman_refit.hpp); k = {K_WEAK}, n = {WEAK_N_SIGMA}, bending bins {BENDING_BIN_EDGES_MM} mm", flush=True)
        self.assertLess(pull_back * SAGITTA_BIAS_IN_SIGMA, 1e-3)

    def test_the_self_check_passes_honest_toys_and_fails_a_weak_or_visible_deformation(self):
        deformed, clean = weak_mode_toys(self.design, SAGITTA_BIAS_IN_SIGMA, 2e-4, CAI_EVENTS, seed=11)
        verdict = weak_mode_self_check(deformed, clean)
        cell = verdict["cells"][verdict["most"]]  # the most-affected cell, named
        print(f"CAI-T07-4-DESIGN toys, honest: most-affected cell {verdict['most']} {cell['ratio']:.3f} per-track sigmas (se {cell['ratio_se']:.3f}), {cell['ratio_stated']:.3f} "
              f"stated; margin over k {(cell['ratio'] - K_WEAK) / cell['ratio_se']:.1f} se; chi2/ndf change {cell['chi2_change']:+.4f} (se {cell['chi2_se']:.4f}), all tracks "
              f"{verdict['overall_chi2_change']:+.4f} (se {verdict['overall_chi2_se']:.4f}); flatness {flatness(verdict['cells'])[0]:.1f} on {flatness(verdict['cells'])[1]}", flush=True)
        self.assertEqual(verdict["defects"], [])
        lowest = min(min((cell["ratio"] - K_WEAK) / cell["ratio_se"], (cell["ratio_stated"] - K_WEAK) / (cell["ratio_se"] * cell["sigma"] / STATED_SIGMA_QOP))
                     for cell in verdict["cells"].values())
        print(f"CAI-T07-4-DESIGN toys, honest: smallest margin over k in any cell and either unit {lowest:.1f} se", flush=True)
        weak = weak_mode_self_check(*weak_mode_toys(self.design, 4.0, 2e-4, CAI_EVENTS, seed=12))
        self.assertEqual(len(weak["defects"]), 8, weak["defects"])
        self.assertTrue(all("not both at least k" in defect for defect in weak["defects"]))
        one_cell = weak_mode_self_check(*weak_mode_toys(self.design, SAGITTA_BIAS_IN_SIGMA, 2e-4, CAI_EVENTS, seed=14, only_cell=(1, 2)))
        self.assertEqual(len(one_cell["defects"]), 7, one_cell["defects"])  # fix round 1, M2: one deformed cell passes, the seven others fail
        self.assertEqual(one_cell["most"], (1, 2))
        visible = weak_mode_self_check(*weak_mode_toys(self.design, SAGITTA_BIAS_IN_SIGMA, shift_chi2_change_per_ndf(0), CAI_EVENTS, seed=13))
        self.assertEqual(len(visible["defects"]), 9, visible["defects"])  # every cell's chi2, and all tracks
        honest_cells = [cell["ratio"] for cell in verdict["cells"].values()]
        self.assertLess(max(honest_cells) - min(honest_cells), 0.5)


# ---- Built: the job runs these.

def run_program(arguments, check: bool = True) -> subprocess.CompletedProcess:
    finished = subprocess.run([str(item) for item in arguments], capture_output=True, text=True, timeout=3600)
    if check and finished.returncode != 0:
        raise AssertionError(f"{arguments[0]} exit {finished.returncode}: {finished.stdout[-4000:]}{finished.stderr[-4000:]}")
    return finished


class CaiFiles:
    """One CAI stratum of block 1 from the frozen generator, its hit sets from truth (truth q/p assumed, as CAI-T07-1), and its refits."""

    def __init__(self, folder: Path, fixture: str, stratum: int):
        self.folder, self.stratum, self.fixture = folder, stratum, fixture
        self.data_file, self.truth_file = folder / f"{fixture}-{stratum}.t07data", folder / f"{fixture}-{stratum}.t07truth"
        run_program([CAI_GENERATOR, "generate", "--fixture", fixture, "--block", CAI_BLOCK, "--stratum", stratum, "--first-event", 0, "--count", CAI_EVENTS,
                     "--data-file", self.data_file, "--truth-file", self.truth_file])
        header = truth_files.read_truth_header(self.truth_file)
        wanted = outputs_tests.CAI_FIXTURE_ID if fixture == "cai-clean" else SAGITTA_FIXTURE_ID
        if (header["fixture_id"], header["block"], header["stratum"]) != (wanted, CAI_BLOCK, stratum):
            raise AssertionError(f"the truth file says {header}")
        self.hit_sets, self.charge = [], {}
        for ordinal, event in enumerate(truth_files.iter_truth_events(self.truth_file)):
            (track,) = event["tracks"]
            self.hit_sets.append((f"event-{ordinal}", ordinal, float(track["q_over_p"]), [int(key) for key in track["hit_keys"]]))
            self.charge[f"event-{ordinal}"] = int(track["charge"])
        self.true_q_over_p = {key: q_over_p for key, _, q_over_p, _ in self.hit_sets}

    def refit(self, data_file: Path, name: str, payload: Path = None, hit_sets=None) -> dict:
        hit_sets_file, product = self.folder / f"{name}.hitsets", self.folder / f"{name}.product"
        hit_sets_file.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), hit_sets or self.hit_sets), encoding="utf-8")
        run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", hit_sets_file, "--field-tesla", FIELD_TESLA, "--product-id", name, "--product-file", product]
                    + (["--alignment-payload", payload] if payload else []))
        document = native_product.parse_product(product.read_text(encoding="utf-8"))
        product.unlink()
        hit_sets_file.unlink()
        return document


def fit_arrays(document: dict, files: CaiFiles) -> dict:
    """Per fitted track in track order: chi2/ndf, the q/p residual against truth, its variance, the truth charge, the fitted loc0 at the reference state; and the unbiased residuals."""
    reference = {item["track_key"]: item for item in document["track_outputs"]}
    smoothed = {(item["track_key"], item["state_index"]): item["parameters"] for item in document["parameters"] if item["state_type"] == "smoothed"}
    rows = []
    for track in document["tracks"]:
        if track["status"] != "fitted":
            continue
        track_output = reference[track["key"]]
        rows.append((track["key"], track["chi2"] / (track["measured_coordinates"] - FIT_PARAMETERS), track_output["q_over_p"] - files.true_q_over_p[track["key"]],
                     track_output["q_over_p_variance"], files.charge[track["key"]], smoothed[(track["key"], track_output["reference_state_index"])][0], track_output["q_over_p"]))
    keys = [row[0] for row in rows]
    columns = list(zip(*rows[:]))[1:] if rows else [[]] * 6
    arrays = {name: numpy.array(values, float) for name, values in zip(("chi2_per_ndf", "residual", "variance", "charge", "u_plane_one", "q_over_p"), columns)}
    arrays["keys"] = keys
    arrays["pull"] = arrays["residual"] / numpy.sqrt(arrays["variance"])
    arrays["failed"] = [track["key"] for track in document["tracks"] if track["status"] != "fitted"]
    arrays["unbiased"] = outputs_tests.unbiased_arrays(document)
    arrays["payload"] = document["header"].get("alignment_payload")
    return arrays


@unittest.skipUnless(BUILT, NOT_BUILT)
class CaiRefitRun(unittest.TestCase):
    """CAI-T07-3 and CAI-T07-4 on block 1 of fixtures 7003 and 7004, and the driver's refusals. Interface checks, no alignment quality claim (R31)."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.geometry = run_program([DRIVER, "geometry-id"]).stdout.strip()
        print(f"CAI-T07-3 nominal geometry identity {cls.geometry}; Python replica {'equal' if cls.geometry == alignment_payload.nominal_geometry_id() else 'DIFFERENT'} (a reading)",
              flush=True)
        cls.parent_text = honest_payload(cls.geometry)
        cls.parent_file = folder / "parent.t07payload"
        cls.parent_file.write_text(cls.parent_text, encoding="ascii")
        cls.parent_sidecar = alignment_payload.payload_sidecar(cls.parent_text, "cai-t07-3-parent", "synthetic CAI-T07-3 fixture: the generated shift, no measurement")
        cls.children, cls.sidecars = {}, {}
        for name, parameter in CASE_PARAMETER.items():
            text = alignment_payload.derive_subset(cls.parent_text, {SHIFTED_PLANE: [parameter]})
            path = folder / f"derived-{name}.t07payload"
            path.write_text(text, encoding="ascii")
            cls.children[name] = (path, alignment_payload.parse_payload(text, cls.geometry))
            cls.sidecars[name] = alignment_payload.payload_sidecar(text, f"cai-t07-3-{name}", "synthetic CAI-T07-3 fixture: the generated shift, no measurement", cls.parent_sidecar)
        for name, sidecar in [("parent", cls.parent_sidecar)] + sorted(cls.sidecars.items()):  # fix round 1, m2: what the sidecars say, in the job's evidence
            print(f"CAI-T07-3 sidecar {name} payload_id {sidecar['payload_id']} content_sha256 {sidecar['content_sha256']} origin {sidecar['origin']} derived_from "
                  f"{sidecar.get('derived_from', 'none')} producer {sidecar['producer']['kind']}: {sidecar['producer']['source']}", flush=True)
        cls.nominal, cls.shifted, cls.corrected, cls.clean_fits, cls.sagitta, cls.second_pass, cls.cost = {}, {}, {}, {}, {}, {}, {}
        cls.zero_payload_equal = None
        for stratum in CAI_STRATA:
            started = time.monotonic()
            clean = CaiFiles(folder, "cai-clean", stratum)
            cls.nominal[stratum] = fit_arrays(clean.refit(clean.data_file, f"nominal-{stratum}"), clean)
            if stratum == CAI_STRATA[0]:  # a reading: the placement route with nothing moved gives the nominal fit's /1 records
                zero_file = folder / "zero.t07payload"
                zero_file.write_text(alignment_payload.encode_payload({}, cls.geometry, "nominal"), encoding="ascii")
                plain = native_product.version_one_of(clean.refit(clean.data_file, "zero-plain"))
                placed = native_product.version_one_of(clean.refit(clean.data_file, "zero-placed", zero_file))
                plain["header"]["product_id"] = placed["header"]["product_id"] = "zero"
                cls.zero_payload_equal = native_product.format_product(plain) == native_product.format_product(placed)
            header = fixture_files.read_data_header(clean.data_file)
            for name, coordinate, displacement in SHIFT_CASES:
                shifted_file = folder / f"cai-clean-{stratum}-shifted-{name}.t07data"
                shifted_file.write_bytes(fixture_files.encode_data_file(header["sigma_loc0_mm"], outputs_tests.shifted_events(clean.data_file, SHIFTED_PLANE, coordinate, displacement)))
                if fixture_files.data_file_defects(shifted_file):
                    raise AssertionError("the shifted file is not a data file")
                cls.shifted[(stratum, name)] = fit_arrays(clean.refit(shifted_file, f"shifted-{name}-{stratum}"), clean)
                cls.corrected[(stratum, name)] = fit_arrays(clean.refit(shifted_file, f"corrected-{name}-{stratum}", cls.children[name][0]), clean)
                shifted_file.unlink()
            fitted_clean = time.monotonic()
            sagitta = CaiFiles(folder, "cai-sagitta", stratum)
            cls.sagitta[stratum] = fit_arrays(sagitta.refit(sagitta.data_file, f"sagitta-{stratum}"), sagitta)
            fitted_q_over_p = dict(zip(cls.sagitta[stratum]["keys"], cls.sagitta[stratum]["q_over_p"]))
            again = [(key, ordinal, float(fitted_q_over_p[key]), hits) for key, ordinal, _, hits in sagitta.hit_sets]
            cls.second_pass[stratum] = fit_arrays(sagitta.refit(sagitta.data_file, f"sagitta-again-{stratum}", hit_sets=again), sagitta)
            if stratum == CAI_STRATA[0]:  # fix round 1, m1: the refusal test's positive control refits ten of these hit sets
                cls.control_data, cls.control_hit_sets = clean.data_file, clean.hit_sets[:10]
            for path in (clean.truth_file, sagitta.data_file, sagitta.truth_file) + (() if stratum == CAI_STRATA[0] else (clean.data_file,)):
                path.unlink()
            cls.cost[stratum] = (fitted_clean - started, time.monotonic() - fitted_clean)
            print(f"CAI-COST stratum {stratum} events {CAI_EVENTS} clean_and_shifted_seconds {cls.cost[stratum][0]:.1f} sagitta_seconds {cls.cost[stratum][1]:.1f}", flush=True)

    def test_every_fit_is_fitted_and_each_payload_is_recorded(self):
        print(f"CAI-T07-3 zero payload through the placement route: /1 records {'equal' if self.zero_payload_equal else 'DIFFERENT'} to the plain geometry's (asserted, fix round 1 m4)", flush=True)
        self.assertTrue(self.zero_payload_equal)
        for stratum in CAI_STRATA:
            groups = [self.nominal[stratum], self.sagitta[stratum], self.second_pass[stratum]] + [self.shifted[(stratum, name)] for name in CASE_PARAMETER]
            for arrays in groups + [self.corrected[(stratum, name)] for name in CASE_PARAMETER]:
                with self.subTest(stratum=stratum):
                    self.assertEqual(arrays["failed"], [])
                    self.assertEqual(len(arrays["keys"]), CAI_EVENTS)
            for arrays in groups:
                self.assertIsNone(arrays["payload"])
            for name in CASE_PARAMETER:
                child = self.children[name][1]
                recorded = self.corrected[(stratum, name)]["payload"]
                with self.subTest(stratum=stratum, case=name):
                    self.assertEqual(recorded, {"content_sha256": child["content_id"], "origin": "measured", "derived_against": self.geometry,
                                                "derived_from": alignment_payload.payload_content_id(self.parent_text), "round": "none"})
                    self.assertEqual(self.sidecars[name]["content_sha256"], recorded["content_sha256"])
                    self.assertEqual(self.sidecars[name]["derived_from"], self.parent_sidecar["payload_id"])

    def test_cai_t07_3_residual_means_return_to_zero(self):
        defects = []
        for stratum in CAI_STRATA:
            for name, coordinate, displacement in SHIFT_CASES:
                corrected, shifted, nominal = self.corrected[(stratum, name)]["unbiased"], self.shifted[(stratum, name)]["unbiased"], self.nominal[stratum]["unbiased"]
                for plane in range(1, 9):
                    for view in (0, 1):
                        mean = float(numpy.mean(corrected[("unbiased", plane)][:, view]))
                        limit = MEAN_N_SIGMA * outputs_tests.sigma_of_mean_mm(view, plane)
                        before = float(numpy.mean(shifted[("unbiased", plane)][:, view]))
                        paired = float(numpy.max(numpy.abs(corrected[("unbiased", plane)][:, view] - nominal[("unbiased", plane)][:, view])))
                        print(f"CAI-T07-3 shift {name} {displacement:+.4f} stratum {stratum} plane {plane} {('loc0', 'loc1')[view]} mean with payload {mean:+.6f} mm expected +0.000000 "
                              f"limit {limit:.6f}; without {before:+.6f}; largest |with payload - nominal| per event {paired:.2e} mm (predicted at most {PAIRED_PREDICTED_MM:g})", flush=True)
                        defects += outputs_tests.mean_defects(mean, 0.0, limit / MEAN_N_SIGMA, f"stratum {stratum} {name} plane {plane} view {view}")
                plane_four = float(numpy.mean(shifted[("unbiased", SHIFTED_PLANE)][:, coordinate]))
                if not outputs_tests.mean_defects(plane_four, 0.0, outputs_tests.sigma_of_mean_mm(coordinate, SHIFTED_PLANE), "control"):
                    defects.append(f"control: stratum {stratum} {name} without the payload passes the return-to-zero rule on plane 4, so the check has no power")
        self.assertEqual(defects, [])

    def test_cai_t07_3_chi2_and_q_over_p_return(self):
        defects = []
        for stratum in CAI_STRATA:
            nominal = self.nominal[stratum]
            for name, coordinate, _ in SHIFT_CASES:
                corrected, shifted = self.corrected[(stratum, name)], self.shifted[(stratum, name)]
                label = f"stratum {stratum} {name}"
                print(f"CAI-T07-3 chi2 {label} mean chi2/ndf nominal {float(numpy.mean(nominal['chi2_per_ndf'])):.5f} with payload {float(numpy.mean(corrected['chi2_per_ndf'])):.5f} "
                      f"without {float(numpy.mean(shifted['chi2_per_ndf'])):.5f} (control predicted {shift_chi2_change_per_ndf(coordinate):+.4f}); KS with payload "
                      f"{ks_distance(corrected['chi2_per_ndf'], nominal['chi2_per_ndf']):.4f} without {ks_distance(shifted['chi2_per_ndf'], nominal['chi2_per_ndf']):.4f} limit "
                      f"{ks_limit(len(corrected['keys']), len(nominal['keys'])):.4f}; largest |chi2 with payload - nominal| per event "
                      f"{float(numpy.max(numpy.abs(corrected['chi2_per_ndf'] - nominal['chi2_per_ndf']))) * (16 - FIT_PARAMETERS):.2e}", flush=True)
                print(f"CAI-T07-3 q/p {label} mean pull nominal {float(numpy.mean(nominal['pull'])):+.4f} with payload {float(numpy.mean(corrected['pull'])):+.4f} without "
                      f"{float(numpy.mean(shifted['pull'])):+.4f} (control predicted {shift_q_over_p_pull() if coordinate == 0 else 0.0:+.4f} in stated sigmas, about "
                      f"{shift_q_over_p_pull() * STATED_SIGMA_QOP / 0.00405 if coordinate == 0 else 0.0:+.4f} in the fitted sigmas these pulls use); largest "
                      f"|q/p with payload - nominal| / sigma {float(numpy.max(numpy.abs(corrected['q_over_p'] - nominal['q_over_p']) / numpy.sqrt(nominal['variance']))):.2e}", flush=True)
                defects += mean_difference_defects(corrected["chi2_per_ndf"], nominal["chi2_per_ndf"], f"{label} chi2/ndf")
                defects += ks_defects(corrected["chi2_per_ndf"], nominal["chi2_per_ndf"], f"{label} chi2/ndf")
                defects += mean_difference_defects(corrected["pull"], nominal["pull"], f"{label} q/p pull")
                if not mean_difference_defects(shifted["chi2_per_ndf"], nominal["chi2_per_ndf"], "control"):
                    defects.append(f"control: {label} without the payload passes the chi2 rule, so the check has no power")
                if coordinate == 0 and not mean_difference_defects(shifted["pull"], nominal["pull"], "control"):
                    defects.append(f"control: {label} without the payload passes the q/p rule, so the check has no power")
        self.assertEqual(defects, [])

    def test_cai_t07_3_a_wrong_payload_is_refused_not_applied(self):
        """Fix round 1, m1: the honest payload on the same files is applied (exit 0, a product), so a refusal below is the payload's, and each names the payload."""
        folder = Path(self.folder.name)
        data_file = self.control_data
        hit_sets = folder / "refusal.hitsets"
        hit_sets.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), self.control_hit_sets), encoding="utf-8")
        honest, honest_product = folder / "honest.t07payload", folder / "honest.product"
        honest.write_text(self.parent_text, encoding="ascii")
        control = run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", FIELD_TESLA, "--product-id", "honest", "--product-file",
                               honest_product, "--alignment-payload", honest], check=False)
        print(f"CAI-T07-3 refusal control: the honest payload on the same files exit {control.returncode}, product {honest_product.exists()}", flush=True)
        self.assertEqual(control.returncode, 0, control.stderr[-2000:])
        self.assertTrue(honest_product.exists())
        for name, text in wrong_payloads(self.geometry).items():
            payload, product = folder / "wrong.t07payload", folder / "wrong.product"
            payload.write_text(text, encoding="ascii")
            finished = run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", FIELD_TESLA, "--product-id", "wrong", "--product-file", product,
                                    "--alignment-payload", payload], check=False)
            print(f"CAI-T07-3 refused {name}: exit {finished.returncode} {finished.stderr.strip()[:160]}", flush=True)
            with self.subTest(name=name):
                self.assertEqual(finished.returncode, 2)
                self.assertIn("refused", finished.stderr)
                self.assertTrue("alignment payload" in finished.stderr or "alignment-payload" in finished.stderr, finished.stderr)
                self.assertFalse(product.exists())
                with self.assertRaises(alignment_payload.PayloadFormatError):
                    alignment_payload.parse_payload(text, self.geometry)

    def test_cai_t07_4_self_check(self):
        deformed = {name: numpy.concatenate([self.sagitta[stratum][name] for stratum in CAI_STRATA]) for name in ("charge", "u_plane_one", "residual", "variance", "chi2_per_ndf")}
        clean = {name: numpy.concatenate([self.nominal[stratum][name] for stratum in CAI_STRATA]) for name in ("charge", "u_plane_one", "residual", "variance", "chi2_per_ndf")}
        verdict = weak_mode_self_check(deformed, clean)
        for key, cell in sorted(verdict["cells"].items()):
            print(f"CAI-T07-4 cell charge {key[0]:+d} bending bin {key[1]} tracks {cell['tracks'][0]} and {cell['tracks'][1]} change in q/p {cell['ratio']:.4f} per-track sigmas "
                  f"(se {cell['ratio_se']:.4f}, sigma {cell['sigma']:.6f} per GeV), {cell['ratio_stated']:.4f} stated sigmas; change in mean chi2/ndf {cell['chi2_change']:+.5f} "
                  f"(se {cell['chi2_se']:.5f}); expected 5.003 per-track, stated about 4.88 in the outer and 4.96 in the inner bins (fix round 1, M1), and about +0.0002", flush=True)
        statistic, freedom = flatness(verdict["cells"])
        print(f"CAI-T07-4 most-affected cell {verdict['most']}, k {K_WEAK}, n {WEAK_N_SIGMA}; all tracks chi2/ndf change {verdict['overall_chi2_change']:+.5f} (se "
              f"{verdict['overall_chi2_se']:.5f}); flatness {statistic:.1f} on {freedom} degrees of freedom (a reading: expected flat); defects {len(verdict['defects'])}", flush=True)
        for stratum in CAI_STRATA:
            cells = weak_mode_cells(self.sagitta[stratum], self.nominal[stratum])
            print(f"CAI-T07-4 stratum {stratum} ({MOMENTUM_BIN_EDGES[stratum]} to {MOMENTUM_BIN_EDGES[stratum + 1]} GeV) cells, per-track sigmas " +
                  " ".join(f"{key[0]:+d}/{key[1]} {cell['ratio']:.3f}" for key, cell in sorted(cells.items())) + "; expected 5.003 each (a reading)", flush=True)
            for charge in (1, -1):
                chosen = self.sagitta[stratum]["charge"] == charge
                momentum_shift = float(numpy.mean(1.0 / numpy.abs(self.sagitta[stratum]["q_over_p"][chosen]) * numpy.abs(self.sagitta[stratum]["q_over_p"][chosen] -
                                                                                                                         self.sagitta[stratum]["residual"][chosen])) - 1.0)
                print(f"CAI-T07-4 stratum {stratum} charge {charge:+d} mean |p_fit| / |p_true| - 1 {momentum_shift:+.5f} (a reading: the q/p offset is the same sign for both "
                      f"charges, so |p| moves opposite ways)", flush=True)
            passes = numpy.abs(self.second_pass[stratum]["q_over_p"] - self.sagitta[stratum]["q_over_p"]) / numpy.sqrt(self.sagitta[stratum]["variance"])
            print(f"CAI-T07-4 stratum {stratum} second pass from each fit's own q/p: mean |change| {float(numpy.mean(passes)):.2e} largest {float(numpy.max(passes)):.2e} sigma "
                  f"(predicted at most {SECOND_PASS_PREDICTED_SIGMA}; a reading)", flush=True)
        self.assertEqual(verdict["defects"], [])


# ---- D1 stage 10, built: the wrapper's refit with the stage 9 payloads against the driver called directly.
WRAPPER = outputs_tests.ADAPTER / "assets" / "acts_tracking.py"
WRAPPER_TRACKS = 200  # hit sets of CAI clean stratum 0: enough for every plane and both charges, a second or so per refit


def run_wrapper(arguments) -> tuple:
    finished = subprocess.run([sys.executable, str(WRAPPER), *[str(item) for item in arguments], "--build-dir", BUILD_DIR], capture_output=True, text=True, timeout=3600)
    return finished.returncode, json.loads(finished.stdout)


@unittest.skipUnless(BUILT, NOT_BUILT)
class WrapperRefitRun(unittest.TestCase):
    """The wrapper forwards --alignment-payload and changes nothing: its product bytes are the driver's, and a refusal is the driver's own, passed through."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.work = Path(cls.folder.name)
        cls.geometry = run_program([DRIVER, "geometry-id"]).stdout.strip()
        clean = CaiFiles(cls.work, "cai-clean", CAI_STRATA[0])
        cls.data_file = clean.data_file
        cls.hit_sets = cls.work / "wrapper.hitsets"
        cls.hit_sets.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(cls.data_file), clean.hit_sets[:WRAPPER_TRACKS]), encoding="utf-8")
        parent = honest_payload(cls.geometry)
        cls.payloads = {"none": None, "stage 9 parent": parent}
        for name, parameter in CASE_PARAMETER.items():
            cls.payloads[f"stage 9 derived {name}"] = alignment_payload.derive_subset(parent, {SHIFTED_PLANE: [parameter]})

    def arguments(self, product: Path, payload: Path = None) -> list:
        return (["refit", "--data-file", self.data_file, "--hit-sets", self.hit_sets, "--field-tesla", FIELD_TESLA, "--product-id", "wrapper-check", "--product-file", product]
                + (["--alignment-payload", payload] if payload else []))

    def payload_file(self, name: str, text: str) -> Path:
        if text is None:
            return None
        path = self.work / f"{name.replace(' ', '-')}.t07payload"
        path.write_text(text, encoding="ascii")
        return path

    def test_the_products_are_the_drivers_bytes(self):
        for name, text in self.payloads.items():
            payload = self.payload_file(name, text)
            direct, through = self.work / "direct.product", self.work / "wrapper.product"
            finished = run_program([DRIVER, *self.arguments(direct, payload)])
            exit_code, report = run_wrapper(self.arguments(through, payload))
            equal = direct.read_bytes() == through.read_bytes()
            header = native_product.parse_product(through.read_text(encoding="utf-8"))["header"]
            print(f"WRAPPER-REFIT {name}: wrapper exit {exit_code} status {report['status']}, product bytes equal to the driver's {equal}, "
                  f"{len(through.read_bytes())} bytes, payload line {'present' if 'alignment_payload' in header else 'absent'}", flush=True)
            with self.subTest(payload=name):
                self.assertEqual((exit_code, report["status"], report["program_exit"]), (0, "ok", 0), report.get("reason"))
                self.assertEqual(report["command"], [str(item) for item in [DRIVER, *self.arguments(through, payload)]])
                self.assertEqual(report["program_stdout"], finished.stdout)
                self.assertTrue(equal)
                if text is None:
                    self.assertNotIn("alignment_payload", header)
                else:
                    self.assertEqual(header["alignment_payload"]["content_sha256"], alignment_payload.payload_content_id(text))
            direct.unlink()
            through.unlink()

    def test_a_wrong_payload_is_the_drivers_refusal(self):
        for name, text in wrong_payloads(self.geometry).items():
            payload = self.payload_file("wrong", text)
            direct, through = self.work / "wrong-direct.product", self.work / "wrong-wrapper.product"
            finished = run_program([DRIVER, *self.arguments(direct, payload)], check=False)
            exit_code, report = run_wrapper(self.arguments(through, payload))
            print(f"WRAPPER-REFIT refused {name}: driver exit {finished.returncode}, wrapper exit {exit_code} status {report['status']}, stderr equal "
                  f"{report.get('program_stderr') == finished.stderr}, reason {report['reason'][:120]}", flush=True)
            with self.subTest(payload=name):
                self.assertEqual(finished.returncode, 2, finished.stderr)
                self.assertEqual((exit_code, report["status"], report["program_exit"]), (2, "rejected", 2))
                self.assertEqual(report["program_stderr"], finished.stderr)
                self.assertEqual(report["reason"], finished.stderr.strip())
                self.assertTrue("alignment payload" in report["reason"] or "alignment-payload" in report["reason"], report["reason"])
                self.assertFalse(direct.exists() or through.exists())


if __name__ == "__main__":
    unittest.main()
