#!/usr/bin/env python3
"""Generator-agreement check of t07-telescope-clean/1, t07-telescope-noise/1 and t07-telescope-cai/1: t04-values-v4.md section 2.1,
adapted to T07 in the form it sets for T08 and T09. Seed block 6 only: this script creates no tuning, Freeze-B or evaluation event. Every constant
below is written here from version 4, apart from the generator, so a wrong constant there shows as a disagreement. Needs an
approved job, not a login node.

Usage: check_t07_generator.py --build-dir B --work-dir W [--events-per-stratum 3000] [--events-per-point 1000]
Exit 0 only if nothing printed FAIL. At other sizes than the section 2.1 ones the last line says SMALL-SAMPLE, and the run is a
development check of the check, not the generator check of section 2.1. Line prefixes, as check_generators.py prints them:

- AGREE: the criteria of section 2.1. The reference is the event's truth crossing and its variance sigma^2, not one draw. Per
  stratum and fixture, over the 16 cells (plane x coordinate), for mean and variance: every |z| below 5, and the sum of z^2
  inside its central 99.9 % chi-square range. Variance z from kappa4/N + 2 kappa2^2/(N - 1), with kappa4 = 0 for a Gaussian.
- TRUTH: the ACTS propagation of each truth track against a closed-form helix computed here, from the vertex, direction and q/p
  and the unit conversion of section 4. Recomputed from section 4.1's text: u_v, sigma(q/p), the reconstructable fraction, p_w,
  R_floor and the largest offset. Not recomputed: the overlap bound and the ideal wrong assignment, which depend on no generator
  output.
- DRAW-RANGE: hard defect checks on every event, draws inside their stated ranges, counts exact.
- DRAW-DIST: KS or a chi-square, each passing at p >= ALPHA. Per stratum, the marginal draws. Per fixture, pooled over the strata
  so the family stays small, on the section 2.1 sample of hits: the "Gaussian, two-dimensional" row of section 4.1 by the shape of
  residual / sigma in each coordinate (KS against the normal), the correlation of the two coordinates at each plane, and of each
  coordinate between every pair of planes, each on the residuals and on their squares, which see a shared radius with r = 0; on
  all events: hits per track against Binomial(8, efficiency), and independence of draws the text calls independent. A correlation
  z is r sqrt(n). On the noise fixture, truth labels against the data side: nothing in a hit's bits tells noise from track (A09),
  by the low bits and residues of its grid integer and by the tail of its IEEE mantissa in each binade.
- SMOKE: the seed rule against an independent Python digest and stream; each stratum regenerates alone, data and truth, in any
  call order; the data file holds only ALLOWED_DATA_FIELDS, its events run in seed-digest order, and the two file headers state
  what the text says.
- GOLDEN: SHA-256 of data and truth files for events 0 and 1 of each stratum. Later jobs compare these lines.

t07-telescope-cai/1 (fixtures cai-clean and cai-sagitta, Freeze A amendment 1) has the same lines, cut to what one track per event
leaves: four strata, one per momentum bin. Per stratum: DRAW-RANGE, TRUTH, and AGREE as above. In sagitta the truth crossing is on the
displaced plane, so TRUTH adds the displacement back before the helix, and a generator that shifted only its hits fails AGREE. Per
fixture, pooled over the strata so the family stays small: the shape and correlation tests above, one KS per draw, one independence
line. Charge follows event_index, so it is a DRAW-RANGE rule, not a test. The first three raw draws of each event must give its vertex,
which holds the seed stream and draw order to the independent Python stream.

The last lines count what the generators wrote to stderr, which section 18 row 4 reads, and how many lines can stop a correct
generator at row 3: FAMILY, one line per generator group and one for the run.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import shutil
import struct
import subprocess
import sys
import traceback
from pathlib import Path

import numpy
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t07_fixture_files as fixture_files  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402

BLOCK = 6                                   # section 3.2: generator checks
FULL_EVENTS_PER_STRATUM, FULL_EVENTS_PER_POINT = 3000, 1000  # section 2.1
ALPHA = 1e-4                                # as check_generators.py
CHI2_TAILS = (0.0005, 0.9995)               # section 2.1: 99.9 % range
Z_LIMIT = 5.0                               # section 2.1
# Not in version 4: the agreement allowed between the ACTS propagation and the helix, a twentieth of the hit sigma, and that
# length over the 100 mm from vertex to plane 1 for an angle. The stepper's error is expected far below it.
TRUTH_LOC_TOLERANCE_MM = 1e-3
TRUTH_ANGLE_TOLERANCE = 1e-5
NOISE_POSITION_SAMPLE = 100000              # noise hits per stratum in the KS test, so that memory stays small
TRACK_POSITION_SAMPLE = 100000              # track hits per stratum beside them in the bit tests
GRID_LOW_BITS = 16                          # low bits of the grid integer compared, noise against track
GRID_RESIDUE_MODULI = (3, 5, 7)
MINIMUM_HITS_PER_BINADE = 320               # both kinds, so that the smallest of six tail classes expects at least 5
LOW_BIT_ATTACK_STEPS_PER_MM = 2.0 ** 46     # D1 re-review N1: a coordinate off this grid was a track hit

FIXTURES = {"clean": (7001, "t07-telescope-clean/1", 1.0), "noise": (7002, "t07-telescope-noise/1", 0.98)}
CAI_FIXTURES = {"cai-clean": (7003, "t07-telescope-cai/1", 1.0), "cai-sagitta": (7004, "t07-telescope-cai/1", 1.0)}  # amendment 1, section 3.2
ALL_FIXTURES = {**FIXTURES, **CAI_FIXTURES}
GENERATOR_PROGRAM, CAI_GENERATOR_PROGRAM = "t07_fixture_generator", "t07_cai_fixture_generator"
PLANES = 8
PLANE_Z_MM = numpy.arange(PLANES) * 50.0
HALF_WIDTH_MM = 150.0
SIGMA_MM = 0.020
FIELD_T = 1.0
GEV_PER_TESLA_MM = 0.299792458e-3           # section 4: 0.299792458 GeV/(T m)
MOMENTUM_BINS_GEV = ((1.5, 3.0), (3.0, 6.0), (6.0, 12.0), (12.0, 24.0))
TRACKS = (6, 12, 36)
VERTICES = (2, 2, 3)
NOISE_MEANS = (100.0, 300.0, 1000.0)
VERTEX_U_HALF_MM, VERTEX_V_HALF_MM = 0.05, 30.0
VERTEX_Z_RANGE_MM = (-100.2, -99.8)
RESOLUTION_UNIT_MM = 0.0184
FAR_STEPS, NEAR_STEPS = (5.0, 25.0), (1.0, 5.0)
SLOPE_HALF = 0.15
SIGMA_Q_OVER_P_PER_GEV = 0.00412            # section 4.1, Closed-form facts
SAGITTA_BIAS_IN_SIGMA = 5.0                 # amendment 1, section 4.1
SAGITTA_TABLE_MM = (0.05404, 0.00772, -0.02316, -0.03860, -0.03860, -0.02316, 0.00772, 0.05404)  # amendment 1, section 4.1
SUM_ALPHA = 1.0 - (CHI2_TAILS[1] - CHI2_TAILS[0])  # a sum of z^2 leaves its range this often

MASK64 = (1 << 64) - 1
failures: list = []
generator_stderr_bytes = 0
family_counts = {"sums": 0, "tests": 0}     # lines that section 18 row 3 reads


def say(text: str) -> None:
    print(text, flush=True)


def verdict(label: str, passed: bool, detail: str) -> bool:
    say(f"{'PASS' if passed else 'FAIL'} {label}: {detail}")
    if not passed:
        failures.append(label)
    family_counts["sums"] += label.endswith("sum z^2 in range")
    family_counts["tests"] += label.startswith("DRAW-DIST")
    return bool(passed)


def false_stop_chance(sums: int, tests: int) -> float:
    """Section 18 row 3: the chance that a correct generator trips one of these lines, taking them as independent."""
    return 1.0 - (1.0 - SUM_ALPHA) ** sums * (1.0 - ALPHA) ** tests


def family_line(name: str, sums: int, tests: int) -> None:
    say(f"FAMILY {name}: {sums} sums of z^2 at {SUM_ALPHA:g}, {tests} tests at {ALPHA:g}, false stop {100.0 * false_stop_chance(sums, tests):.2f} %")


def criteria(tag: str, z_values) -> bool:
    """Section 2.1: every |z| below 5, and the sum of z^2 within its 99.9 % chi-square range, one d.o.f. per z."""
    z_values = numpy.asarray(z_values, float)
    if z_values.size == 0 or not numpy.all(numpy.isfinite(z_values)):
        return verdict(f"{tag} defined", False, f"{z_values.size} values, not all finite")
    largest = float(numpy.abs(z_values).max())
    first = verdict(f"{tag} every |z| below 5", largest < Z_LIMIT, f"largest {largest:.3f} of {z_values.size}")
    lower, upper = stats.chi2.ppf(CHI2_TAILS, z_values.size)
    total = float((z_values ** 2).sum())
    second = verdict(f"{tag} sum z^2 in range", lower <= total <= upper, f"{total:.1f}, range {lower:.1f} to {upper:.1f}, {z_values.size} d.o.f.")
    return first and second


def distribution_z(tag: str, z_values) -> bool:
    z_values = numpy.asarray(z_values, float)
    if z_values.size == 0 or not numpy.all(numpy.isfinite(z_values)):
        return verdict(f"DRAW-DIST {tag}", False, f"{z_values.size} values, not all finite")
    total = float((z_values ** 2).sum())
    p_value = 2.0 * min(float(stats.chi2.sf(total, z_values.size)), float(stats.chi2.cdf(total, z_values.size)))
    return verdict(f"DRAW-DIST {tag}", p_value >= ALPHA, f"p {p_value:.3g}, alpha {ALPHA:g}, sum z^2 {total:.1f}, {z_values.size} d.o.f.")


def uniform_test(tag: str, draws, lower: float, upper: float) -> bool:
    draws = numpy.asarray(draws, float)
    if draws.size == 0 or not numpy.all(numpy.isfinite(draws)):
        return verdict(f"DRAW-DIST {tag}", False, f"{draws.size} values, not all finite")
    p_value = float(stats.kstest((draws - lower) / (upper - lower), "uniform").pvalue)
    return verdict(f"DRAW-DIST {tag}", p_value >= ALPHA, f"KS p {p_value:.3g}, alpha {ALPHA:g}, {draws.size} draws")


def correlation_z(first, second) -> float:
    """r sqrt(n): unit normal for two independent samples."""
    first, second = numpy.asarray(first, float), numpy.asarray(second, float)
    return float(numpy.corrcoef(first, second)[0, 1] * math.sqrt(first.size))


def hit_shape_tests(tag: str, residuals, kept, sigma_mm: float = SIGMA_MM) -> dict:
    """Section 4.1, Measurement: two-dimensional, Gaussian, sigma in each coordinate, so independent between coordinates; one draw per
    hit, so independent between planes. residuals: (n, planes, 2); kept: (n, planes). Returns each test's verdict by name."""
    results = {}
    for coordinate, name in enumerate(("loc0", "loc1")):
        sample = residuals[:, :, coordinate][kept] / sigma_mm
        p_value = float(stats.kstest(sample, "norm", method="asymp").pvalue)
        results[f"shape {name}"] = verdict(f"DRAW-DIST {tag} hit shape {name}", p_value >= ALPHA, f"KS p {p_value:.3g}, alpha {ALPHA:g}, {sample.size} hits")
    planes = residuals.shape[1]
    results["coordinates"] = distribution_z(f"{tag} hit coordinates uncorrelated, per plane",
                                            [correlation_z(residuals[kept[:, plane], plane, 0], residuals[kept[:, plane], plane, 1]) for plane in range(planes)])
    between_planes = []
    for first_plane in range(planes):
        for second_plane in range(first_plane + 1, planes):
            both = kept[:, first_plane] & kept[:, second_plane]
            between_planes += [correlation_z(residuals[both, first_plane, coordinate], residuals[both, second_plane, coordinate]) for coordinate in range(2)]
    results["planes"] = distribution_z(f"{tag} hits uncorrelated between planes", between_planes)
    squares = residuals ** 2
    results["coordinates squared"] = distribution_z(f"{tag} squared hit coordinates uncorrelated, per plane",
                                                    [correlation_z(squares[kept[:, plane], plane, 0], squares[kept[:, plane], plane, 1]) for plane in range(planes)])
    between_planes = []
    for first_plane in range(planes):
        for second_plane in range(first_plane + 1, planes):
            both = kept[:, first_plane] & kept[:, second_plane]
            between_planes += [correlation_z(squares[both, first_plane, coordinate], squares[both, second_plane, coordinate]) for coordinate in range(2)]
    results["planes squared"] = distribution_z(f"{tag} squared hits uncorrelated between planes", between_planes)
    return results


def low_bit_attack(positions) -> numpy.ndarray:
    """D1 re-review N1, as a rule on the data side alone: a hit with a coordinate off the 2^-46 mm grid is a track hit. positions: (n, 2)."""
    steps = numpy.asarray(positions, float) * LOW_BIT_ATTACK_STEPS_PER_MM
    return (steps != numpy.rint(steps)).any(axis=1)


def two_sample_chi2(tables) -> tuple:
    """Pearson chi-square over 2 x k tables, summed: (total, d.o.f.). A class neither sample holds counts for nothing."""
    total, degrees = 0.0, 0
    for table in tables:
        table = numpy.asarray(table, float)
        table = table[:, table.sum(axis=0) > 0]
        if table.shape[1] > 1:
            result = stats.chi2_contingency(table, correction=False)
            total, degrees = total + float(result[0]), degrees + int(result[2])
    return total, degrees


def mantissa_tail_tables(noise_values, track_values) -> list:
    """Per binade with enough hits of both kinds, the trailing zero bits of the IEEE mantissa, in six classes above the binade's floor."""
    def split(values):
        words = numpy.ascontiguousarray(values, dtype="<f8").view("<u8")
        mantissa = words & numpy.uint64((1 << 52) - 1)
        lowest = mantissa & (~mantissa + numpy.uint64(1))
        tail = numpy.where(mantissa == 0, 52, numpy.rint(numpy.log2(numpy.maximum(lowest, numpy.uint64(1)).astype(float)))).astype(int)
        return (words >> numpy.uint64(52)) & numpy.uint64(0x7FF), tail

    noise_binades, noise_tails = split(noise_values)
    track_binades, track_tails = split(track_values)
    tables = []
    for binade in numpy.intersect1d(noise_binades, track_binades):
        first, second = noise_tails[noise_binades == binade], track_tails[track_binades == binade]
        if min(first.size, second.size) >= MINIMUM_HITS_PER_BINADE:
            floor = min(first.min(), second.min())
            tables.append([numpy.bincount(numpy.minimum(sample - floor, 5), minlength=6) for sample in (first, second)])
    return tables


def hit_bit_tests(tag: str, noise_positions, track_positions) -> dict:
    """Truth labels against the data side: no bit or grid statistic may tell noise from track (A09). positions: (n, 2) in mm."""
    results = {}
    noise_steps = numpy.rint(numpy.asarray(noise_positions) * fixture_files.HIT_GRID_STEPS_PER_MM).astype(numpy.int64)
    track_steps = numpy.rint(numpy.asarray(track_positions) * fixture_files.HIT_GRID_STEPS_PER_MM).astype(numpy.int64)
    z_values = []
    for coordinate in range(2):
        for bit in range(GRID_LOW_BITS):
            first, second = (noise_steps[:, coordinate] >> bit) & 1, (track_steps[:, coordinate] >> bit) & 1
            pooled = (first.sum() + second.sum()) / (first.size + second.size)
            z_values.append((first.mean() - second.mean()) / math.sqrt(pooled * (1.0 - pooled) * (1.0 / first.size + 1.0 / second.size)))
    results["low bits"] = distribution_z(f"{tag} noise and track hits agree in the low bits of the grid", z_values)
    tables = [[numpy.bincount(noise_steps[:, coordinate] % modulus, minlength=modulus), numpy.bincount(track_steps[:, coordinate] % modulus, minlength=modulus)]
              for modulus in GRID_RESIDUE_MODULI for coordinate in range(2)]
    total, degrees = two_sample_chi2(tables)
    p_value = float(stats.chi2.sf(total, degrees))
    results["residues"] = verdict(f"DRAW-DIST {tag} noise and track hits agree in grid residues", p_value >= ALPHA, f"p {p_value:.3g}, chi2 {total:.1f}, {degrees} d.o.f.")
    tables = [table for coordinate in range(2) for table in mantissa_tail_tables(noise_positions[:, coordinate], track_positions[:, coordinate])]
    total, degrees = two_sample_chi2(tables)
    p_value = float(stats.chi2.sf(total, degrees)) if degrees else math.nan
    results["mantissa tail"] = verdict(f"DRAW-DIST {tag} noise and track hits agree in the IEEE mantissa tail", p_value >= ALPHA, f"p {p_value:.3g}, chi2 {total:.1f}, {degrees} d.o.f.")
    return results


def hit_count_test(tag: str, kept, efficiency: float) -> bool:
    """Hits per track against Binomial(8, efficiency): classes 8, 7 and at most 6, a Pearson chi-square with 2 d.o.f."""
    hits_per_track = kept.sum(axis=1)
    observed = numpy.array([(hits_per_track == PLANES).sum(), (hits_per_track == PLANES - 1).sum(), (hits_per_track < PLANES - 1).sum()], float)
    top = stats.binom.pmf([PLANES, PLANES - 1], PLANES, efficiency)
    expected = numpy.array([top[0], top[1], 1.0 - top.sum()]) * hits_per_track.size
    total = float(((observed - expected) ** 2 / expected).sum())
    p_value = float(stats.chi2.sf(total, 2))
    return verdict(f"DRAW-DIST {tag} hits per track", p_value >= ALPHA, f"p {p_value:.3g}, alpha {ALPHA:g}, chi2 {total:.1f}, {hits_per_track.size} tracks")


def draw_independence_test(tag: str, pairs) -> bool:
    """Draws the text makes independent: each pair of arrays, one z each."""
    return distribution_z(f"{tag} draws independent", [correlation_z(first, second) for first, second in pairs])


def seed_digest(fixture_id: int, block: int, stratum: int, event_index: int) -> bytes:
    """Section 3.2, the four integers hashed: SHA-256 of four little-endian 64-bit words."""
    return hashlib.sha256(struct.pack("<4Q", fixture_id, block, stratum, event_index)).digest()


def stream_raw_draws(digest: bytes, count: int) -> list:
    """xoshiro256** from the digest, written here apart from the C++ one."""
    words = list(struct.unpack("<4Q", digest))
    rotate = lambda word, shift: ((word << shift) | (word >> (64 - shift))) & MASK64  # noqa: E731
    draws = []
    for _ in range(count):
        draws.append((rotate((words[1] * 5) & MASK64, 7) * 9) & MASK64)
        shifted = (words[1] << 17) & MASK64
        words[2] ^= words[0]
        words[3] ^= words[1]
        words[1] ^= words[2]
        words[0] ^= words[3]
        words[2] ^= shifted
        words[3] = rotate(words[3], 45)
    return draws


def helix_crossings(start_xyz, direction, q_over_p, plane_x_mm, field_tesla: float = FIELD_T):
    """Closed form in a uniform field along ACTS z: positions and direction at each plane x = const.

    start_xyz, direction: (n, 3); q_over_p: (n,). dT/ds = (q k B / p) T x z, so the azimuth falls with path at rate
    `omega` = q/p k B. Returns (n, planes) arrays y, z, phi, theta. ACTS frame: x = fixture z, y = fixture u, z = fixture v.
    """
    start_xyz, direction = numpy.asarray(start_xyz, float), numpy.asarray(direction, float)
    direction = direction / numpy.linalg.norm(direction, axis=1, keepdims=True)
    transverse = numpy.hypot(direction[:, 0], direction[:, 1])[:, None]
    phi_start = numpy.arctan2(direction[:, 1], direction[:, 0])[:, None]
    omega = (numpy.asarray(q_over_p, float) * GEV_PER_TESLA_MM * field_tesla)[:, None]
    distance = numpy.asarray(plane_x_mm, float)[None, :] - start_xyz[:, 0:1]
    phi_end = numpy.arcsin(numpy.sin(phi_start) - omega * distance / transverse)
    path = (phi_start - phi_end) / omega
    y_end = start_xyz[:, 1:2] + (transverse / omega) * (numpy.cos(phi_end) - numpy.cos(phi_start))
    z_end = start_xyz[:, 2:3] + path * direction[:, 2:3]
    theta = numpy.broadcast_to(numpy.arccos(direction[:, 2:3]), y_end.shape)
    return y_end, z_end, phi_end, theta


def truth_against_helix(tag: str, vertices_xyz, tracks) -> bool:
    """TRUTH: one row of vertices_xyz per track."""
    direction = numpy.stack([numpy.ones(len(tracks)), tracks["slope_u"], tracks["slope_v"]], axis=1)
    loc0, loc1, phi, theta = helix_crossings(vertices_xyz, direction, tracks["q_over_p"], PLANE_Z_MM)
    crossings = tracks["crossings"]
    position = max(float(numpy.abs(crossings[:, :, 0] - loc0).max()), float(numpy.abs(crossings[:, :, 1] - loc1).max()))
    angle = max(float(numpy.abs(crossings[:, :, 2] - phi).max()), float(numpy.abs(crossings[:, :, 3] - theta).max()))
    first = verdict(f"TRUTH {tag} crossings on the helix", position < TRUTH_LOC_TOLERANCE_MM, f"largest {position:.3g} mm, {len(tracks)} tracks")
    second = verdict(f"TRUTH {tag} directions on the helix", angle < TRUTH_ANGLE_TOLERANCE, f"largest {angle:.3g} rad")
    return first and second


def smearing_z(residuals, kept, sigma_mm: float = SIGMA_MM):
    """Mean and variance z per cell. residuals: (n, planes, 2); kept: (n, planes)."""
    mean_z, variance_z = [], []
    for plane in range(residuals.shape[1]):
        for coordinate in range(2):
            sample = residuals[kept[:, plane], plane, coordinate]
            count = sample.size
            mean_z.append(sample.mean() / (sigma_mm / math.sqrt(count)) if count > 1 else math.nan)
            kappa2 = sigma_mm ** 2
            variance_z.append((sample.var(ddof=1) - kappa2) / math.sqrt(2.0 * kappa2 ** 2 / (count - 1)) if count > 1 else math.nan)
    return numpy.array(mean_z), numpy.array(variance_z)


def closed_form_constants() -> dict:
    """u_v and sigma(q/p) of section 4.1, as calc-round2-small.py and calc-closed-form.py state them."""
    z_m = numpy.arange(PLANES) * 0.05
    sigma_m = SIGMA_MM * 1e-3
    line_design = numpy.vstack([numpy.ones(PLANES), z_m - z_m.mean()]).T
    line_covariance = numpy.linalg.inv(line_design.T @ line_design) * sigma_m ** 2
    at_vertex = numpy.array([1.0, -0.1 - z_m.mean()])
    parabola_design = numpy.vstack([numpy.ones(PLANES), z_m - z_m.mean(), (z_m - z_m.mean()) ** 2]).T
    parabola_covariance = numpy.linalg.inv(parabola_design.T @ parabola_design) * sigma_m ** 2
    window_fraction = math.pi * 0.15 ** 2 / (2.0 * HALF_WIDTH_MM) ** 2
    chance_in_window = [1.0 - math.exp(-mean_noise * window_fraction) for mean_noise in NOISE_MEANS]  # Poisson: at least one noise hit
    return {"u_v_mm": float((at_vertex @ line_covariance @ at_vertex) ** 0.5 * 1e3),
            "sigma_q_over_p_per_gev": float(2.0 * parabola_covariance[2, 2] ** 0.5 / (0.299792458 * FIELD_T)),
            "reconstructable": float(stats.binom.sf(5, PLANES, 0.98)), "p_w": chance_in_window, "r_floor": [(1.0 - chance) ** PLANES for chance in chance_in_window],
            "largest_offset_mm": VERTEX_U_HALF_MM + 0.2 * SLOPE_HALF}


def event_defects(truth, hits, fixture: str, stratum: int) -> list:
    """Every hard defect of one event, by the fixture text. Empty for an honest event."""
    fixture_id, _, efficiency = FIXTURES[fixture]
    momentum_bin, level = stratum // 3, stratum % 3
    tracks, vertices = truth["tracks"], truth["vertices"]
    defects = []
    if int(truth["momentum_bin"]) != momentum_bin or int(truth["occupancy_level"]) != level:
        defects.append("stratum fields")
    if truth["event_digest"] != seed_digest(fixture_id, BLOCK, stratum, int(truth["event_index"])):
        defects.append("seed digest")
    if len(tracks) != TRACKS[level]:
        defects.append("track count")
    if len(vertices) != VERTICES[level]:
        defects.append("vertex count")
    if int((tracks["charge"] == 1).sum()) * 2 != len(tracks) or int((tracks["charge"] == -1).sum()) * 2 != len(tracks):
        defects.append("charges not exactly half and half")
    if numpy.bincount(tracks["vertex_index"], minlength=len(vertices)).tolist() != [len(tracks) // len(vertices)] * len(vertices):
        defects.append("tracks per vertex")
    lower, upper = MOMENTUM_BINS_GEV[momentum_bin]
    if numpy.any(tracks["momentum_gev"] < lower) or numpy.any(tracks["momentum_gev"] >= upper):
        defects.append("momentum outside its bin")
    if numpy.any(numpy.abs(tracks["q_over_p"] * tracks["momentum_gev"] - tracks["charge"]) > 1e-12):
        defects.append("q/p against charge and momentum")
    if numpy.any(numpy.abs(tracks["slope_u"]) > SLOPE_HALF) or numpy.any(numpy.abs(tracks["slope_v"]) > SLOPE_HALF):
        defects.append("slope outside its range")
    if numpy.any(numpy.abs(vertices["u_mm"]) > VERTEX_U_HALF_MM) or numpy.any(vertices["z_mm"] < VERTEX_Z_RANGE_MM[0]) or numpy.any(vertices["z_mm"] > VERTEX_Z_RANGE_MM[1]):
        defects.append("vertex u or z outside its range")
    if abs(float(vertices["v_mm"][0])) > VERTEX_V_HALF_MM:
        defects.append("first vertex v outside its range")
    near = int(truth["event_index"]) % 5 == 0
    if bool(truth["near_separation"]) != near:
        defects.append("near or far against event_index mod 5")
    step_lower, step_upper = NEAR_STEPS if near else FAR_STEPS
    steps = numpy.diff(vertices["v_mm"]) / RESOLUTION_UNIT_MM
    if numpy.any(steps < step_lower * (1 - 1e-12)) or numpy.any(steps > step_upper * (1 + 1e-12)):
        defects.append("vertex step outside its range")
    if numpy.any(numpy.abs(tracks["crossings"][:, :, :2]) >= HALF_WIDTH_MM):
        defects.append("a track left the active area")
    if fixture_files.off_hit_grid(hits["loc0_mm"]) or fixture_files.off_hit_grid(hits["loc1_mm"]):
        defects.append("a coordinate is off the hit grid")

    keys = tracks["hit_keys"]
    claimed = keys[keys != truth_files.NO_HIT_KEY].astype(numpy.int64)
    noise_total = int(truth["noise_counts"].sum())
    if not numpy.array_equal(hits["hit_key"], numpy.arange(len(hits))):
        defects.append("hit keys are not positions")
    if len(set(claimed.tolist())) != claimed.size or claimed.size + noise_total != len(hits):
        defects.append("hits against truth keys and noise counts")
    else:
        planes_of_claimed = hits["plane"][claimed]
        expected_planes = numpy.broadcast_to(numpy.arange(1, PLANES + 1), keys.shape)[keys != truth_files.NO_HIT_KEY]
        if not numpy.array_equal(planes_of_claimed, expected_planes):
            defects.append("a truth hit on the wrong plane")
    order = numpy.lexsort((hits["loc1_mm"], hits["loc0_mm"], hits["plane"]))
    if not numpy.array_equal(order, numpy.arange(len(hits))):
        defects.append("hits not in plane and position order")
    if efficiency == 1.0 and (noise_total != 0 or claimed.size != keys.size):
        defects.append("the clean fixture lost a hit or holds noise")
    if not numpy.array_equal(numpy.bincount(hits["plane"], minlength=PLANES + 1)[1:] - (keys != truth_files.NO_HIT_KEY).sum(axis=0), truth["noise_counts"].astype(numpy.int64)):
        defects.append("noise per plane against truth")
    return defects


def file_identity_defects(data_file, truth_file, fixture: str, stratum: int, event_count: int) -> list:
    """Both file headers against the text, the truth file's hold on its data file, and the data file's allowed fields."""
    fixture_id, generator, _ = ALL_FIXTURES[fixture]
    data_header, truth_header = fixture_files.read_data_header(data_file), truth_files.read_truth_header(truth_file)
    expected = {"generator": generator, "fixture_id": fixture_id, "block": BLOCK, "stratum": stratum, "event_count": event_count, "sigma_loc0_mm": SIGMA_MM,
                "sigma_loc1_mm": SIGMA_MM, "data_sha256": fixture_files.file_sha256(data_file)}
    defects = [f"truth header {name}" for name, value in expected.items() if truth_header[name] != value]
    defects += [f"data header {name}" for name in ("event_count", "sigma_loc0_mm", "sigma_loc1_mm") if data_header[name] != expected[name]]
    return defects + fixture_files.data_file_defects(data_file)


class StratumSample:
    """What one (fixture, stratum) run keeps: arrays of tracks and vertices, residuals, noise positions."""

    def __init__(self):
        self.tracks, self.vertices_of_tracks, self.first_vertices, self.u_draws, self.z_draws = [], [], [], [], []
        self.far_steps, self.near_steps, self.noise_counts, self.residuals, self.kept = [], [], [], [], []
        self.noise_positions, self.track_positions = [], []
        self.vertex_pairs = []
        self.noise_kept = self.track_positions_kept = 0
        self.defects = 0
        self.defect_names = set()

    def add(self, truth, hits, fixture: str, stratum: int) -> None:
        found = event_defects(truth, hits, fixture, stratum)
        self.defects += len(found)
        self.defect_names.update(found)
        tracks, vertices = truth["tracks"], truth["vertices"]
        self.tracks.append(tracks)
        self.vertices_of_tracks.append(numpy.stack([vertices["z_mm"], vertices["u_mm"], vertices["v_mm"]], axis=1)[tracks["vertex_index"]])
        self.first_vertices.append(float(vertices["v_mm"][0]))
        self.u_draws.extend(vertices["u_mm"].tolist())
        self.z_draws.extend(vertices["z_mm"].tolist())
        steps = (numpy.diff(vertices["v_mm"]) / RESOLUTION_UNIT_MM).tolist()
        (self.near_steps if truth["near_separation"] else self.far_steps).extend(steps)
        step_lower, step_upper = NEAR_STEPS if truth["near_separation"] else FAR_STEPS
        self.vertex_pairs.append((float(vertices["u_mm"][0]), float(vertices["u_mm"][1]), float(vertices["z_mm"][0]), float(vertices["z_mm"][1]),
                                  float(vertices["v_mm"][0]), (steps[0] - step_lower) / (step_upper - step_lower)))
        self.noise_counts.append(truth["noise_counts"].astype(float))
        keys = tracks["hit_keys"]
        kept = keys != truth_files.NO_HIT_KEY
        residuals = numpy.zeros(keys.shape + (2,))
        residuals[kept, 0] = hits["loc0_mm"][keys[kept]] - tracks["crossings"][:, :, 0][kept]
        residuals[kept, 1] = hits["loc1_mm"][keys[kept]] - tracks["crossings"][:, :, 1][kept]
        self.residuals.append(residuals)
        self.kept.append(kept)
        if self.track_positions_kept < TRACK_POSITION_SAMPLE:
            claimed = keys[kept].astype(numpy.int64)
            self.track_positions.append(numpy.stack([hits["loc0_mm"][claimed], hits["loc1_mm"][claimed]], axis=1))
            self.track_positions_kept += int(claimed.size)
        if self.noise_kept < NOISE_POSITION_SAMPLE and truth["noise_counts"].sum():
            is_noise = numpy.ones(len(hits), bool)
            is_noise[keys[kept].astype(numpy.int64)] = False
            self.noise_positions.append(numpy.stack([hits["loc0_mm"][is_noise], hits["loc1_mm"][is_noise]], axis=1))
            self.noise_kept += int(is_noise.sum())


class FixturePool:
    """What the per-fixture tests read, across the strata of one fixture."""

    def __init__(self):
        self.residuals, self.kept, self.all_kept, self.tracks, self.scaled_log_momentum, self.vertex_pairs = [], [], [], [], [], []
        self.noise_positions, self.track_positions = [], []

    def add(self, sample: StratumSample, residuals, kept, momentum_bin: int) -> None:
        lower, upper = MOMENTUM_BINS_GEV[momentum_bin]
        tracks = numpy.concatenate(sample.tracks)
        self.residuals.append(residuals)
        self.kept.append(kept)
        self.all_kept.append(numpy.concatenate(sample.kept))
        self.tracks.append(tracks)
        self.scaled_log_momentum.append((numpy.log(tracks["momentum_gev"]) - math.log(lower)) / (math.log(upper) - math.log(lower)))
        self.vertex_pairs += sample.vertex_pairs
        self.noise_positions += sample.noise_positions
        self.track_positions += sample.track_positions


def judge_fixture(pool: FixturePool, fixture: str) -> None:
    efficiency = FIXTURES[fixture][2]
    hit_shape_tests(fixture, numpy.concatenate(pool.residuals), numpy.concatenate(pool.kept))
    if efficiency < 1.0:
        hit_count_test(fixture, numpy.concatenate(pool.all_kept), efficiency)
        hit_bit_tests(fixture, numpy.concatenate(pool.noise_positions), numpy.concatenate(pool.track_positions))
    tracks = numpy.concatenate(pool.tracks)
    log_momentum = numpy.concatenate(pool.scaled_log_momentum)
    vertex_columns = numpy.array(pool.vertex_pairs).T
    draw_independence_test(fixture, ((tracks["slope_u"], tracks["slope_v"]), (log_momentum, tracks["slope_u"]), (log_momentum, tracks["slope_v"]),
                                     (tracks["charge"], tracks["slope_u"]), (tracks["charge"], log_momentum), (vertex_columns[0], vertex_columns[1]),
                                     (vertex_columns[2], vertex_columns[3]), (vertex_columns[0], vertex_columns[2]), (vertex_columns[4], vertex_columns[5])))


def judge_stratum(sample: StratumSample, fixture: str, stratum: int, events_per_point: int, pool: FixturePool) -> None:
    tag = f"{fixture} stratum {stratum}"
    momentum_bin, level = stratum // 3, stratum % 3
    efficiency = FIXTURES[fixture][2]
    verdict(f"DRAW-RANGE {tag}", sample.defects == 0, f"{sample.defects} defects {sorted(sample.defect_names)}")

    tracks = numpy.concatenate(sample.tracks)
    start = numpy.concatenate(sample.vertices_of_tracks)
    truth_against_helix(tag, start, tracks)

    tracks_per_event = TRACKS[level]
    agreement_tracks = events_per_point * tracks_per_event
    residuals = numpy.concatenate(sample.residuals)[:agreement_tracks]
    kept = numpy.concatenate(sample.kept)[:agreement_tracks]
    mean_z, variance_z = smearing_z(residuals, kept)
    criteria(f"AGREE {tag} hit mean", mean_z)
    criteria(f"AGREE {tag} hit variance", variance_z)
    pool.add(sample, residuals, kept, momentum_bin)

    lower, upper = MOMENTUM_BINS_GEV[momentum_bin]
    uniform_test(f"{tag} ln p", numpy.log(tracks["momentum_gev"]), math.log(lower), math.log(upper))
    uniform_test(f"{tag} slope u", tracks["slope_u"], -SLOPE_HALF, SLOPE_HALF)
    uniform_test(f"{tag} slope v", tracks["slope_v"], -SLOPE_HALF, SLOPE_HALF)
    uniform_test(f"{tag} vertex u", sample.u_draws, -VERTEX_U_HALF_MM, VERTEX_U_HALF_MM)
    uniform_test(f"{tag} vertex z", sample.z_draws, *VERTEX_Z_RANGE_MM)
    uniform_test(f"{tag} first vertex v", sample.first_vertices, -VERTEX_V_HALF_MM, VERTEX_V_HALF_MM)
    uniform_test(f"{tag} far step", sample.far_steps, *FAR_STEPS)
    if sample.near_steps:
        uniform_test(f"{tag} near step", sample.near_steps, *NEAR_STEPS)
    per_position = numpy.stack([item["charge"] for item in sample.tracks]) == 1
    event_count = per_position.shape[0]
    distribution_z(f"{tag} charge against track position", (per_position.mean(axis=0) - 0.5) / math.sqrt(0.25 / event_count))

    all_kept = numpy.concatenate(sample.kept)
    if efficiency < 1.0:
        hit_fraction = all_kept.mean(axis=0)
        distribution_z(f"{tag} hit efficiency per plane", (hit_fraction - efficiency) / numpy.sqrt(efficiency * (1 - efficiency) / all_kept.shape[0]))
        counts = numpy.stack(sample.noise_counts)
        mean_count = NOISE_MEANS[level]
        distribution_z(f"{tag} noise mean per plane", (counts.mean(axis=0) - mean_count) / math.sqrt(mean_count / event_count))
        kappa_terms = mean_count / event_count + 2.0 * mean_count ** 2 / (event_count - 1)
        distribution_z(f"{tag} noise variance per plane", (counts.var(axis=0, ddof=1) - mean_count) / math.sqrt(kappa_terms))
        positions = numpy.concatenate(sample.noise_positions)[:NOISE_POSITION_SAMPLE]
        uniform_test(f"{tag} noise loc0", positions[:, 0], -HALF_WIDTH_MM, HALF_WIDTH_MM)
        uniform_test(f"{tag} noise loc1", positions[:, 1], -HALF_WIDTH_MM, HALF_WIDTH_MM)
    else:
        verdict(f"DRAW-RANGE {tag} every plane kept", bool(all_kept.all()), f"{all_kept.size} hits")


def sagitta_displacements_mm() -> numpy.ndarray:
    """Amendment 1, section 4.1: d_k = A ((z_k - z_c)^2 - mean), A set so that q/p rises by 5 sigma(q/p): 2 A / (k B)."""
    offsets_squared = (PLANE_Z_MM - PLANE_Z_MM.mean()) ** 2
    return SAGITTA_BIAS_IN_SIGMA * SIGMA_Q_OVER_P_PER_GEV * GEV_PER_TESLA_MM * FIELD_T / 2.0 * (offsets_squared - offsets_squared.mean())


def cai_displacements_mm(fixture: str) -> numpy.ndarray:
    return sagitta_displacements_mm() if fixture == "cai-sagitta" else numpy.zeros(PLANES)


def drawn_between(raw_draw: int, lower: float, upper: float) -> float:
    return lower + (upper - lower) * ((raw_draw >> 11) * 2.0 ** -53)


def cai_event_defects(truth, hits, fixture: str, stratum: int) -> list:
    """Every hard defect of one CAI event, by amendment 1's text. Empty for an honest event."""
    fixture_id = CAI_FIXTURES[fixture][0]
    tracks, vertices, event_index = truth["tracks"], truth["vertices"], int(truth["event_index"])
    defects = []
    if int(truth["momentum_bin"]) != stratum or int(truth["occupancy_level"]) != 0 or int(truth["near_separation"]) != 0:
        defects.append("stratum fields")
    if truth["event_digest"] != seed_digest(fixture_id, BLOCK, stratum, event_index):
        defects.append("seed digest")
    if len(tracks) != 1:
        defects.append("track count")
    if len(vertices) != 1:
        defects.append("vertex count")
    if len(tracks) != 1 or len(vertices) != 1:
        return defects
    track, vertex = tracks[0], vertices[0]
    if int(track["particle_key"]) != 0 or int(track["vertex_index"]) != 0:
        defects.append("track keys")
    if int(track["charge"]) != (1 if event_index % 2 == 0 else -1):
        defects.append("charge against event_index")
    lower, upper = MOMENTUM_BINS_GEV[stratum]
    if not lower <= float(track["momentum_gev"]) < upper:
        defects.append("momentum outside its bin")
    if abs(float(track["q_over_p"]) * float(track["momentum_gev"]) - float(track["charge"])) > 1e-12:
        defects.append("q/p against charge and momentum")
    if abs(float(track["slope_u"])) > SLOPE_HALF or abs(float(track["slope_v"])) > SLOPE_HALF:
        defects.append("slope outside its range")
    expected_vertex = [drawn_between(raw, *limits) for raw, limits in zip(stream_raw_draws(seed_digest(fixture_id, BLOCK, stratum, event_index), 3),
                                                                          ((-VERTEX_U_HALF_MM, VERTEX_U_HALF_MM), VERTEX_Z_RANGE_MM, (-VERTEX_V_HALF_MM, VERTEX_V_HALF_MM)))]
    if max(abs(float(vertex[name]) - value) for name, value in zip(("u_mm", "z_mm", "v_mm"), expected_vertex)) > 1e-12:
        defects.append("vertex against the first three draws")
    if numpy.any(numpy.abs(track["crossings"][:, :2]) >= HALF_WIDTH_MM):
        defects.append("a track left the active area")
    if fixture_files.off_hit_grid(hits["loc0_mm"]) or fixture_files.off_hit_grid(hits["loc1_mm"]):
        defects.append("a coordinate is off the hit grid")
    if int(truth["noise_counts"].sum()) != 0:
        defects.append("noise in a CAI fixture")
    if not numpy.array_equal(hits["hit_key"], numpy.arange(len(hits))) or not numpy.array_equal(hits["plane"], numpy.arange(1, PLANES + 1)):
        defects.append("not one hit per plane in plane order")
    if not numpy.array_equal(track["hit_keys"], numpy.arange(PLANES)):
        defects.append("truth keys against hits")
    return defects


class CaiSample:
    """What one (CAI fixture, stratum) run keeps."""

    def __init__(self):
        self.tracks, self.vertices, self.residuals, self.kept = [], [], [], []
        self.defects = 0
        self.defect_names = set()

    def add(self, truth, hits, fixture: str, stratum: int) -> None:
        found = cai_event_defects(truth, hits, fixture, stratum)
        self.defects += len(found)
        self.defect_names.update(found)
        tracks = truth["tracks"]
        keys = tracks["hit_keys"]
        kept = keys != truth_files.NO_HIT_KEY
        residuals = numpy.zeros(keys.shape + (2,))
        residuals[kept, 0] = hits["loc0_mm"][keys[kept]] - tracks["crossings"][:, :, 0][kept]
        residuals[kept, 1] = hits["loc1_mm"][keys[kept]] - tracks["crossings"][:, :, 1][kept]
        self.tracks.append(tracks)
        self.vertices.append(truth["vertices"])
        self.residuals.append(residuals)
        self.kept.append(kept)


class CaiPool:
    """What the per-fixture tests read, across the four strata."""

    def __init__(self):
        self.residuals, self.kept, self.tracks, self.vertices, self.scaled_log_momentum = [], [], [], [], []


def judge_cai_stratum(sample: CaiSample, fixture: str, stratum: int, events_per_point: int, pool: CaiPool) -> None:
    tag = f"{fixture} stratum {stratum}"
    verdict(f"DRAW-RANGE {tag}", sample.defects == 0, f"{sample.defects} defects {sorted(sample.defect_names)}")
    tracks, vertices = numpy.concatenate(sample.tracks), numpy.concatenate(sample.vertices)
    start = numpy.stack([vertices["z_mm"], vertices["u_mm"], vertices["v_mm"]], axis=1)
    on_nominal_planes = tracks.copy()
    on_nominal_planes["crossings"][:, :, 0] += cai_displacements_mm(fixture)
    truth_against_helix(tag, start, on_nominal_planes)

    residuals, kept = numpy.concatenate(sample.residuals)[:events_per_point], numpy.concatenate(sample.kept)[:events_per_point]
    mean_z, variance_z = smearing_z(residuals, kept)
    criteria(f"AGREE {tag} hit mean", mean_z)
    criteria(f"AGREE {tag} hit variance", variance_z)
    all_kept = numpy.concatenate(sample.kept)
    verdict(f"DRAW-RANGE {tag} every plane kept", bool(all_kept.all()), f"{all_kept.size} hits")

    lower, upper = MOMENTUM_BINS_GEV[stratum]
    pool.residuals.append(residuals)
    pool.kept.append(kept)
    pool.tracks.append(tracks)
    pool.vertices.append(vertices)
    pool.scaled_log_momentum.append((numpy.log(tracks["momentum_gev"]) - math.log(lower)) / (math.log(upper) - math.log(lower)))


def judge_cai_fixture(pool: CaiPool, fixture: str) -> None:
    hit_shape_tests(fixture, numpy.concatenate(pool.residuals), numpy.concatenate(pool.kept))
    tracks, vertices, log_momentum = numpy.concatenate(pool.tracks), numpy.concatenate(pool.vertices), numpy.concatenate(pool.scaled_log_momentum)
    uniform_test(f"{fixture} ln p in its bin", log_momentum, 0.0, 1.0)
    uniform_test(f"{fixture} slope u", tracks["slope_u"], -SLOPE_HALF, SLOPE_HALF)
    uniform_test(f"{fixture} slope v", tracks["slope_v"], -SLOPE_HALF, SLOPE_HALF)
    uniform_test(f"{fixture} vertex u", vertices["u_mm"], -VERTEX_U_HALF_MM, VERTEX_U_HALF_MM)
    uniform_test(f"{fixture} vertex z", vertices["z_mm"], *VERTEX_Z_RANGE_MM)
    uniform_test(f"{fixture} vertex v", vertices["v_mm"], -VERTEX_V_HALF_MM, VERTEX_V_HALF_MM)
    draw_independence_test(fixture, ((tracks["slope_u"], tracks["slope_v"]), (log_momentum, tracks["slope_u"]), (log_momentum, tracks["slope_v"]),
                                     (tracks["charge"], tracks["slope_u"]), (tracks["charge"], tracks["slope_v"]), (tracks["charge"], log_momentum),
                                     (vertices["u_mm"], vertices["z_mm"]), (vertices["u_mm"], vertices["v_mm"]), (vertices["z_mm"], vertices["v_mm"]),
                                     (vertices["v_mm"], tracks["slope_v"])))


def check_cai_closed_form() -> None:
    """Amendment 1's sagitta row against its own definition: plain arithmetic on the planes, no generator output."""
    displacements = sagitta_displacements_mm()
    verdict("TRUTH sagitta table of amendment 1", numpy.round(displacements, 5).tolist() == list(SAGITTA_TABLE_MM), f"{displacements.tolist()} mm")
    verdict("TRUTH sagitta displacements sum to zero", abs(float(displacements.sum())) < 1e-12, f"{float(displacements.sum()):.3g} mm")
    design = numpy.vstack([numpy.ones(PLANES), PLANE_Z_MM, PLANE_Z_MM ** 2]).T
    coefficients = numpy.linalg.lstsq(design, displacements, rcond=None)[0]
    leftover = float(numpy.abs(displacements - design @ coefficients).max())
    verdict("TRUTH sagitta mode is a parabola in plane position, all of it", leftover < 1e-12, f"leftover {leftover:.3g} mm")
    rise = 2.0 * float(coefficients[2]) / (GEV_PER_TESLA_MM * FIELD_T)
    verdict("TRUTH sagitta rise in q/p is 5 sigma(q/p)", abs(rise - SAGITTA_BIAS_IN_SIGMA * SIGMA_Q_OVER_P_PER_GEV) < 1e-9, f"{rise:.6f} per GeV")


def run_cai_check(build_dir: Path, work_dir: Path, events_per_stratum: int, events_per_point: int) -> None:
    check_cai_closed_form()
    for fixture in CAI_FIXTURES:
        pool = CaiPool()
        for stratum in range(len(MOMENTUM_BINS_GEV)):
            folder = work_dir / f"{fixture}-{stratum}"
            folder.mkdir(parents=True, exist_ok=True)
            data_file, truth_file = run_generator(build_dir, fixture, stratum, 0, events_per_stratum, folder, "draws")
            defects = file_identity_defects(data_file, truth_file, fixture, stratum, events_per_stratum)
            verdict(f"SMOKE {fixture} stratum {stratum} file fields and identities", not defects, f"{defects}")
            sample = CaiSample()
            first_events, digests = {}, []
            for data_event, truth_event in zip(fixture_files.iter_data_events(data_file), truth_files.iter_truth_events(truth_file), strict=True):
                digests.append(truth_event["event_digest"])
                if int(truth_event["event_index"]) < 2:
                    first_events[int(truth_event["event_index"])] = event_bytes(data_event, truth_event)
                sample.add(truth_event, data_event["hits"], fixture, stratum)
            verdict(f"SMOKE {fixture} stratum {stratum} events run in seed-digest order", digests == sorted(digests), f"{len(digests)} events")
            judge_cai_stratum(sample, fixture, stratum, events_per_point, pool)
            smoke_stratum(build_dir, fixture, stratum, folder, first_events)
            shutil.rmtree(folder)
        judge_cai_fixture(pool, fixture)


def call_generator(build_dir: Path, *arguments, program: str = GENERATOR_PROGRAM) -> subprocess.CompletedProcess:
    """Every call goes through here: section 18 row 4 reads the generator's stderr."""
    global generator_stderr_bytes
    finished = subprocess.run([str(build_dir / program), *arguments], capture_output=True, text=True)
    sys.stderr.write(finished.stderr)
    generator_stderr_bytes += len(finished.stderr)
    finished.check_returncode()
    return finished


def run_generator(build_dir: Path, fixture: str, stratum: int, first_event: int, count: int, folder: Path, label: str) -> tuple:
    data_file, truth_file = folder / f"{label}.t07data", folder / f"{label}{fixture_files.TRUTH_SUFFIX}"
    call_generator(build_dir, "generate", "--fixture", fixture, "--block", str(BLOCK), "--stratum", str(stratum), "--first-event", str(first_event),
                   "--count", str(count), "--data-file", str(data_file), "--truth-file", str(truth_file),
                   program=CAI_GENERATOR_PROGRAM if fixture in CAI_FIXTURES else GENERATOR_PROGRAM)
    return data_file, truth_file


def event_bytes(data_event: dict, truth_event: dict) -> bytes:
    return b"".join((data_event["hits"].tobytes(), truth_event["vertices"].tobytes(), truth_event["tracks"].tobytes()))


def smoke_stratum(build_dir: Path, fixture: str, stratum: int, folder: Path, full_events: dict) -> None:
    """Events 1 then 0, each alone, equal the same events of the full run, found by the truth file's event_index. Then the golden digests."""
    alone = {}
    for event_index in (1, 0):
        data_file, truth_file = run_generator(build_dir, fixture, stratum, event_index, 1, folder, f"alone-{event_index}")
        alone[event_index] = event_bytes(next(fixture_files.iter_data_events(data_file)), next(truth_files.iter_truth_events(truth_file)))
    verdict(f"SMOKE {fixture} stratum {stratum} regenerates alone, in any order", alone == full_events, "events 1, then 0")
    data_file, truth_file = run_generator(build_dir, fixture, stratum, 0, 2, folder, "golden")
    name = f"{CAI_FIXTURES[fixture][1]} {fixture}" if fixture in CAI_FIXTURES else FIXTURES[fixture][1]
    say(f"GOLDEN {name} stratum {stratum} data {fixture_files.file_sha256(data_file)} truth {fixture_files.file_sha256(truth_file)}")


def check_seed_rule(build_dir: Path) -> None:
    draws = 8
    finished = call_generator(build_dir, "seed-vector", "--fixture-id", "7001", "--block", str(BLOCK), "--stratum", "3", "--event-index", "17", "--draws", str(draws))
    fields = [line.split() for line in finished.stdout.splitlines()]
    digest = seed_digest(7001, BLOCK, 3, 17)
    verdict("SMOKE seed digest equals the independent digest", fields[0] == ["digest", digest.hex()], digest.hex())
    expected = [f"{draw:016x}" for draw in stream_raw_draws(digest, draws)]
    verdict("SMOKE seed stream equals the independent stream", [field[1] for field in fields[1:]] == expected, f"{draws} draws")


def check_closed_form() -> None:
    constants = closed_form_constants()
    verdict("TRUTH u_v of section 4.1", round(constants["u_v_mm"], 4) == RESOLUTION_UNIT_MM, f"{constants['u_v_mm']:.6f} mm")
    verdict("TRUTH sigma(q/p) of section 4.1", round(constants["sigma_q_over_p_per_gev"], 5) == 0.00412, f"{constants['sigma_q_over_p_per_gev']:.6f} per GeV")
    verdict("TRUTH reconstructable fraction of section 4.1", round(constants["reconstructable"], 5) == 0.99958, f"{constants['reconstructable']:.6f}")
    verdict("TRUTH p_w of section 4.1", [float(f"{chance:.1e}") for chance in constants["p_w"]] == [7.9e-5, 2.4e-4, 7.9e-4], f"{constants['p_w']}")
    verdict("TRUTH R_floor of section 4.1", [round(floor, 5) for floor in constants["r_floor"]] == [0.99937, 0.99812, 0.99374], f"{constants['r_floor']}")
    verdict("TRUTH largest offset of section 4.1", round(constants["largest_offset_mm"], 6) == 0.08, f"{constants['largest_offset_mm']} mm")


def run_check(build_dir: Path, work_dir: Path, events_per_stratum: int, events_per_point: int) -> None:
    check_seed_rule(build_dir)
    check_closed_form()
    for fixture in FIXTURES:
        pool = FixturePool()
        for stratum in range(12):
            folder = work_dir / f"{fixture}-{stratum}"
            folder.mkdir(parents=True, exist_ok=True)
            data_file, truth_file = run_generator(build_dir, fixture, stratum, 0, events_per_stratum, folder, "draws")
            defects = file_identity_defects(data_file, truth_file, fixture, stratum, events_per_stratum)
            verdict(f"SMOKE {fixture} stratum {stratum} file fields and identities", not defects, f"{defects}")
            sample = StratumSample()
            first_events, digests = {}, []
            for data_event, truth_event in zip(fixture_files.iter_data_events(data_file), truth_files.iter_truth_events(truth_file), strict=True):
                digests.append(truth_event["event_digest"])
                if int(truth_event["event_index"]) < 2:
                    first_events[int(truth_event["event_index"])] = event_bytes(data_event, truth_event)
                sample.add(truth_event, data_event["hits"], fixture, stratum)
            verdict(f"SMOKE {fixture} stratum {stratum} events run in seed-digest order", digests == sorted(digests), f"{len(digests)} events")
            judge_stratum(sample, fixture, stratum, events_per_point, pool)
            smoke_stratum(build_dir, fixture, stratum, folder, first_events)
            shutil.rmtree(folder)
        judge_fixture(pool, fixture)
    before_cai = dict(family_counts)
    run_cai_check(build_dir, work_dir, events_per_stratum, events_per_point)
    family_line("clean and noise", before_cai["sums"], before_cai["tests"])
    family_line("cai", family_counts["sums"] - before_cai["sums"], family_counts["tests"] - before_cai["tests"])
    family_line("whole run", family_counts["sums"], family_counts["tests"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--events-per-stratum", type=int, default=FULL_EVENTS_PER_STRATUM)
    parser.add_argument("--events-per-point", type=int, default=FULL_EVENTS_PER_POINT)
    arguments = parser.parse_args(argv)
    if arguments.events_per_stratum < 2 or not 1 < arguments.events_per_point <= arguments.events_per_stratum:
        parser.error("at least two events, and no more per point than per stratum")
    full_size = (arguments.events_per_stratum, arguments.events_per_point) == (FULL_EVENTS_PER_STRATUM, FULL_EVENTS_PER_POINT)
    say(f"SAMPLE {arguments.events_per_stratum} events per stratum, {arguments.events_per_point} per point, block {BLOCK}, numpy {numpy.__version__}")
    try:
        run_check(arguments.build_dir, arguments.work_dir, arguments.events_per_stratum, arguments.events_per_point)
    except Exception:  # row 1 of section 18: no criterion of a run that stopped is read
        traceback.print_exc()
        say("STOPPED: the check did not run to its end, so no criterion of this run is read")
        return 2
    say("ran to its end")
    say(f"GENERATOR-STDERR {generator_stderr_bytes} bytes")
    label = "RESULT" if full_size else "SMALL-SAMPLE RESULT, not the check of section 2.1:"
    say(f"{label} {'PASS' if not failures else 'FAIL'} ({len(failures)} failed lines)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
