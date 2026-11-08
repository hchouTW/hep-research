"""Scoring side: an independent linear Kalman filter along each particle's truth helix, the replica of section 7's truth-seeded CKF (D1 stage 6c brief).

Job 7512409 (decisions.md, "Stage 6b diagnostic: results") showed ACTS's truth-seeded CKF losing clean particles because the own branch finds nothing under the chi2 cut at three
planes, and a replica of this kind reproducing ACTS's chi2 and its set of lost particles. The user chose to replace the module's clean tolerance by an exact check against such a
replica (decisions.md, "After stage 6b: the user's choices"); tests/adapters/test_acts_truth_seeded_replica.py holds the check. Pure Python and numpy; no ACTS, no truth reader.

What the replica does, per particle, in ACTS's bound parameters and units (loc0 mm, loc1 mm, phi, theta, q/p in e/GeV) on the plane surfaces:
- the start at plane 1 is the truth state, d = 0, with P = diag(sigma_loc0^2, sigma_loc1^2, sigma_phi^2, sigma_theta^2, (share |q/p|)^2), the start acts_truth_seeded_run sets;
- from plane k-1 to plane k, d = J d and P = J P J^T, with J the derivative of the helix in a field along loc1 (ACTS z), taken along the truth crossing at plane k-1, numerically;
- at each plane reached, r = own hit - truth crossing - d[:2], S = P[:2, :2] + V with V the data file's hit variances, and chi2 = r^T S^-1 r. chi2 < cut updates the state (ACTS's
  MeasurementSelector passes chi2 < chi2CutOff), otherwise the plane is a hole. The branch stops when its holes exceed most_holes (track_finding.cpp, stop_branch). A particle is
  kept when its branch never stopped and holds at least least_measurements hits;
- the particle's own hits only. Each other measurement of the event on a plane the branch reached is also tested against the own branch's prediction there: one under the cut is a
  possible split, a branch ACTS can take and the replica does not follow. That is the only way ACTS can keep a particle the replica loses. The reverse limitation: where the own
  hit fails and a foreign one passes, the replica counts a hole, but ACTS makes no hole branch when a measurement passes (MeasurementSelector.ipp), so the replica's path is not
  one ACTS has; the check prints such planes ("replica path not available to ACTS") and still fails the case.

The cut, the hole stop, the least measurements and the start are not held here: settings_from takes them from the configuration lines a truth-seeded record prints, which the
program writes from its own constants, and the hit sigmas from the data file the finder reads. The plane spacing and the field come from native/t07_fixture_constants.hpp. The
curvature constant (GeV per T mm per unit charge) is the caller's, so no physics number is written in this module. Linear: the filter is linearised along the truth helix, where ACTS
linearises along its estimate, a second-order difference. Measured on job 7512409's traces (D1 stage 6c review, M2): about 1e-3 relative; in absolute terms at most 0.0068 below
chi2 14 and up to 0.0128 within 0.33 of the cut of 16. Superseded: "chi2 agreed to about 1e-3", read as absolute, was wrong near the cut.

What checks what: the unit tests check the loc1 and theta block against hand arithmetic (theta = pi/2 decouples it); the loc0, phi and q/p block, where the q/p prior widens S at
low momentum, is checked only against ACTS: the regression on job 7512409's clean stratum 0, event 1556, particle 5 in the kept-strata check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy

START_PLANE = "1"  # section 7: the start is at plane 1; a record with another start is refused
CONFIGURATION_KEYS = ("finding_chi2_cut", "finding_most_holes", "finding_least_measurements", "truth_start_plane", "truth_start_sigma_loc0_mm", "truth_start_sigma_loc1_mm",
                      "truth_start_sigma_phi", "truth_start_sigma_theta", "truth_start_sigma_qop_share")
GEOMETRY_NAMES = ("plane_count", "plane_spacing_mm", "field_tesla")
DERIVATIVE_STEP = 1e-7          # absolute, for loc0, loc1, phi and theta
DERIVATIVE_STEP_QOP_SHARE = 1e-6  # of |q/p|


@dataclass(frozen=True)
class ReplicaSettings:
    chi2_cut: float
    most_holes: int  # a branch stops when its holes exceed this
    least_measurements: int
    start_sigmas: tuple  # loc0 mm, loc1 mm, phi, theta
    start_sigma_qop_share: float
    hit_sigmas_mm: tuple  # loc0, loc1
    planes: int
    plane_spacing_mm: float
    field_tesla: float
    gev_per_tesla_mm: float

    @property
    def turn_per_qop_mm(self) -> float:
        """The rate phi changes per mm of path, per unit q/p: phi' = -(q/p) k B for a field along loc1, the sign ACTS's frame gives."""
        return -self.gev_per_tesla_mm * self.field_tesla


@dataclass(frozen=True)
class ParticleReplica:
    kept: bool
    stop_plane: int  # the plane of the hole that stopped the branch; 0 if it never stopped
    own_chi2: tuple  # per plane, the own hit's chi2 against the prediction; None on planes not reached, inf where the particle left no hit
    holes: tuple  # (plane, chi2) of each hole: the chi2 that decided it
    foreign: tuple  # (plane, hit key, chi2) of each other measurement under the cut on a plane the branch reached: a possible split
    measurements: int

    def deciding_margin(self, cut: float) -> float:
        """The smallest |chi2 - cut| over the own hits of the planes reached: how near the cut the decisions of this branch were."""
        finite = [abs(value - cut) for value in self.own_chi2 if value is not None and numpy.isfinite(value)]
        return min(finite) if finite else numpy.inf


def header_constant(text: str, name: str) -> float:
    """A constexpr of a C++ header: `name = value;`."""
    found = re.search(rf"\b{name} = ([0-9.eE+-]+);", text)
    if found is None:
        raise ValueError(f"{name} is not in the header")
    return float(found.group(1))


def settings_from(configuration: dict, hit_sigmas_mm, fixture_constants_text: str, gev_per_tesla_mm: float) -> ReplicaSettings:
    """configuration: a truth-seeded record's configuration lines, name to text; hit_sigmas_mm: the data file's header; fixture_constants_text: native/t07_fixture_constants.hpp."""
    missing = [name for name in CONFIGURATION_KEYS if name not in configuration]
    if missing:
        raise ValueError(f"the configuration lacks {', '.join(missing)}")
    if configuration["truth_start_plane"] != START_PLANE:
        raise ValueError(f"the start is at plane {configuration['truth_start_plane']}, not plane {START_PLANE}")
    # acts_truth_seeded_run passes one angle sigma, sigma_phi, for both phi and theta (plane_starts_of), while the record prints theta's own constant: equal under section 7, so a
    # record where they differ would make the replica follow a value ACTS does not use (D1 stage 6c review, n2). Refused.
    if configuration["truth_start_sigma_phi"] != configuration["truth_start_sigma_theta"]:
        raise ValueError("truth_start_sigma_phi and truth_start_sigma_theta differ: the run uses phi's sigma for both angles")
    planes, spacing, field = (header_constant(fixture_constants_text, name) for name in GEOMETRY_NAMES)
    return ReplicaSettings(chi2_cut=float(configuration["finding_chi2_cut"]), most_holes=int(configuration["finding_most_holes"]),
                           least_measurements=int(configuration["finding_least_measurements"]),
                           start_sigmas=tuple(float(configuration[f"truth_start_sigma_{name}"]) for name in ("loc0_mm", "loc1_mm", "phi", "theta")),
                           start_sigma_qop_share=float(configuration["truth_start_sigma_qop_share"]), hit_sigmas_mm=tuple(float(value) for value in hit_sigmas_mm),
                           planes=int(planes), plane_spacing_mm=spacing, field_tesla=field, gev_per_tesla_mm=float(gev_per_tesla_mm))


def settings_text(settings: ReplicaSettings) -> str:
    return (f"finding_chi2_cut {settings.chi2_cut:g} (chi2 < cut passes) finding_most_holes {settings.most_holes} (a branch stops at hole {settings.most_holes + 1}) "
            f"finding_least_measurements {settings.least_measurements} start sigmas loc0 loc1 phi theta {' '.join(f'{value:g}' for value in settings.start_sigmas)} "
            f"q/p share {settings.start_sigma_qop_share:g} hit sigmas mm {' '.join(f'{value:g}' for value in settings.hit_sigmas_mm)} planes {settings.planes} "
            f"spacing mm {settings.plane_spacing_mm:g} field T {settings.field_tesla:g}")


def propagate(states, distance_mm: float, turn_per_qop_mm: float):
    """The helix from one plane to the next, distance_mm downstream along the plane normal (ACTS x), field along loc1 (ACTS z). states: (..., 5) loc0, loc1, phi, theta, q/p."""
    loc0, loc1, phi, theta, qop = (states[..., index] for index in range(5))
    turn = qop * turn_per_qop_mm  # dphi / ds
    sin_theta = numpy.sin(theta)
    straight = numpy.abs(turn) < 1e-15
    safe = numpy.where(straight, 1.0, turn)
    phi_next = numpy.where(straight, phi, numpy.arcsin(numpy.sin(phi) + safe * distance_mm / sin_theta))
    path = numpy.where(straight, distance_mm / (sin_theta * numpy.cos(phi)), (phi_next - phi) / safe)
    loc0_next = numpy.where(straight, loc0 + distance_mm * numpy.tan(phi), loc0 - (sin_theta / safe) * (numpy.cos(phi_next) - numpy.cos(phi)))
    loc1_next = loc1 + numpy.cos(theta) * path
    return numpy.stack([loc0_next, loc1_next, phi_next, theta, qop], axis=-1)


def jacobian(states, distance_mm: float, turn_per_qop_mm: float):
    """d(state at the next plane) / d(state), (..., 5, 5), by central differences along the given states."""
    states = numpy.asarray(states, float)
    result = numpy.zeros(states.shape[:-1] + (5, 5))
    for column in range(5):
        step = numpy.abs(states[..., 4]) * DERIVATIVE_STEP_QOP_SHARE if column == 4 else numpy.full(states.shape[:-1], DERIVATIVE_STEP)
        up, down = states.copy(), states.copy()
        up[..., column] += step
        down[..., column] -= step
        result[..., :, column] = (propagate(up, distance_mm, turn_per_qop_mm) - propagate(down, distance_mm, turn_per_qop_mm)) / (2.0 * step[..., None])
    return result


def filter_tracks(crossings, q_over_p, own_offsets, settings: ReplicaSettings) -> dict:
    """The filter for N particles at once. crossings (N, planes, 4): truth loc0, loc1, phi, theta per plane; q_over_p (N,); own_offsets (N, planes, 2): own hit less the truth
    crossing, NaN where the particle left no hit. Returns per particle and plane: the prediction's offset from truth (N, planes, 2), S^-1 (N, planes, 2, 2), the own chi2, whether
    the branch reached the plane and whether it took the hit there; per particle: kept, stop plane, holes, measurements."""
    crossings, q_over_p, own_offsets = (numpy.asarray(value, float) for value in (crossings, q_over_p, own_offsets))
    count, planes = len(q_over_p), settings.planes
    covariance = numpy.zeros((count, 5, 5))
    for index, sigma in enumerate(settings.start_sigmas):
        covariance[:, index, index] = sigma ** 2
    covariance[:, 4, 4] = (settings.start_sigma_qop_share * q_over_p) ** 2
    offset = numpy.zeros((count, 5))
    hit_variance = numpy.diag(numpy.square(settings.hit_sigmas_mm))
    alive = numpy.ones(count, bool)
    holes, measurements, stop_plane = numpy.zeros(count, int), numpy.zeros(count, int), numpy.zeros(count, int)
    predicted, inverse, chi2 = numpy.zeros((count, planes, 2)), numpy.zeros((count, planes, 2, 2)), numpy.full((count, planes), numpy.nan)
    reached, took = numpy.zeros((count, planes), bool), numpy.zeros((count, planes), bool)
    for plane in range(planes):
        if plane > 0:
            reference = numpy.concatenate([crossings[:, plane - 1, :4], q_over_p[:, None]], axis=1)
            step = jacobian(reference, settings.plane_spacing_mm, settings.turn_per_qop_mm)
            offset = numpy.einsum("nij,nj->ni", step, offset)
            covariance = step @ covariance @ numpy.transpose(step, (0, 2, 1))
        residual_inverse = numpy.linalg.inv(covariance[:, :2, :2] + hit_variance)
        residual = own_offsets[:, plane, :] - offset[:, :2]
        has_hit = numpy.all(numpy.isfinite(residual), axis=1)
        safe_residual = numpy.where(has_hit[:, None], residual, 0.0)
        value = numpy.where(has_hit, numpy.einsum("ni,nij,nj->n", safe_residual, residual_inverse, safe_residual), numpy.inf)
        predicted[:, plane], inverse[:, plane], chi2[:, plane], reached[:, plane] = offset[:, :2], residual_inverse, value, alive
        passed = alive & (value < settings.chi2_cut)
        took[:, plane] = passed
        gain = covariance[:, :, :2] @ residual_inverse
        offset = numpy.where(passed[:, None], offset + numpy.einsum("nij,nj->ni", gain, safe_residual), offset)
        covariance = numpy.where(passed[:, None, None], covariance - gain @ covariance[:, :2, :], covariance)
        hole = alive & ~passed
        holes += hole
        measurements += passed
        stopped = alive & (holes > settings.most_holes)
        stop_plane = numpy.where(stopped, plane + 1, stop_plane)
        alive &= ~stopped
    return {"predicted": predicted, "inverse": inverse, "chi2": chi2, "reached": reached, "took": took, "kept": alive & (measurements >= settings.least_measurements),
            "stop_plane": stop_plane, "holes": holes, "measurements": measurements}


def own_offsets_of(tracks, hit_positions: dict, no_hit_key: int):
    """tracks: rows with hit_keys (planes,) and crossings (planes, 4); hit_positions: hit key to (loc0, loc1). The own hit less the truth crossing, NaN where there is none."""
    offsets = numpy.full((len(tracks), tracks["hit_keys"].shape[1], 2), numpy.nan)
    for index, track in enumerate(tracks):
        for plane, key in enumerate(track["hit_keys"]):
            if int(key) != no_hit_key:
                offsets[index, plane] = numpy.asarray(hit_positions[int(key)]) - track["crossings"][plane, :2]
    return offsets


def replica_of_events(events, settings: ReplicaSettings, no_hit_key: int) -> list:
    """events: (tracks, hits) per event, tracks as the truth file's rows (hit_keys, crossings, q_over_p), hits as the data file's (hit_key, plane, loc0_mm, loc1_mm). One list of
    ParticleReplica per event, in track order. The filter runs on every particle of every event at once; the foreign measurements are read event by event."""
    events = list(events)
    offsets, crossings, rates, sizes = [], [], [], []
    for tracks, hits in events:
        positions = {int(key): (loc0, loc1) for key, loc0, loc1 in zip(hits["hit_key"], hits["loc0_mm"], hits["loc1_mm"])}
        offsets.append(own_offsets_of(tracks, positions, no_hit_key))
        crossings.append(numpy.asarray(tracks["crossings"], float))
        rates.append(numpy.asarray(tracks["q_over_p"], float))
        sizes.append(len(tracks))
    if not sizes or sum(sizes) == 0:
        return [[] for _ in events]
    run = filter_tracks(numpy.concatenate(crossings), numpy.concatenate(rates), numpy.concatenate(offsets), settings)
    results, start = [], 0
    for (tracks, hits), size in zip(events, sizes):
        rows = slice(start, start + size)
        foreign = foreign_under_cut(tracks, hits, {name: value[rows] for name, value in run.items()}, settings)
        event_results = []
        for index in range(size):
            row = start + index
            own = tuple(float(run["chi2"][row, plane]) if run["reached"][row, plane] else None for plane in range(settings.planes))
            holes = tuple((plane + 1, own[plane]) for plane in range(settings.planes) if run["reached"][row, plane] and not run["took"][row, plane])
            event_results.append(ParticleReplica(kept=bool(run["kept"][row]), stop_plane=int(run["stop_plane"][row]), own_chi2=own, holes=holes, foreign=tuple(foreign[index]),
                                                 measurements=int(run["measurements"][row])))
        results.append(event_results)
        start += size
    return results


def foreign_under_cut(tracks, hits, run: dict, settings: ReplicaSettings) -> list:
    """For each particle of one event: (plane, hit key, chi2) of every measurement not its own, on a plane its branch reached, under the cut against its own prediction there."""
    found = [[] for _ in range(len(tracks))]
    for plane in range(settings.planes):
        on_plane = hits["plane"] == plane + 1
        keys, positions = hits["hit_key"][on_plane], numpy.stack([hits["loc0_mm"][on_plane], hits["loc1_mm"][on_plane]], axis=-1)
        particles = numpy.flatnonzero(run["reached"][:, plane])
        if not len(keys) or not len(particles):
            continue
        centres = tracks["crossings"][particles, plane, :2] + run["predicted"][particles, plane]
        residuals = positions[None, :, :] - centres[:, None, :]
        values = numpy.einsum("pmi,pij,pmj->pm", residuals, run["inverse"][particles, plane], residuals)
        for row, hit in zip(*numpy.nonzero(values < settings.chi2_cut)):
            particle = particles[row]
            if int(keys[hit]) != int(tracks["hit_keys"][particle, plane]):
                found[particle].append((plane + 1, int(keys[hit]), float(values[row, hit])))
    return found


def frame_residual_mm(crossings, q_over_p, settings: ReplicaSettings) -> float:
    """The largest distance, over particles and planes, between the truth crossing and the helix carried from the crossing before: whether the frame and the field sign are ACTS's."""
    crossings, q_over_p = numpy.asarray(crossings, float), numpy.asarray(q_over_p, float)
    states = numpy.concatenate([crossings[:, :-1, :4], numpy.repeat(q_over_p[:, None, None], crossings.shape[1] - 1, axis=1)], axis=2)
    carried = propagate(states, settings.plane_spacing_mm, settings.turn_per_qop_mm)
    return float(numpy.max(numpy.abs(carried[..., :2] - crossings[:, 1:, :2]))) if len(q_over_p) else 0.0
