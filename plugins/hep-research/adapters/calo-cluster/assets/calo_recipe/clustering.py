"""t04-values-v4.md section 7.1, the T08 clustering definition, step by step. Every constant comes from the configuration
(section 4.2), and none is derived from pulls or targets (section 2.2).

Steps, in the words of section 7.1, with the choices this code makes where the text leaves a case open (the D2 stage 1
report lists each one, for the coordinator's ruling; R37's last paragraph):

- Cells: e_c from the cell chain. Dead or absent (off-grid) cells have no value and are never in a cluster.
- Components: cells with e_c >= T_c, 8-connected; kept if one cell is at or above T_s; all others unclustered. Components
  are numbered by their lowest flat index (open case O-order).
- Peaks: a cell of a kept component at or above T_s whose e_c is at least that of each of its 8 neighbours that has a value;
  a dead or off-grid neighbour has none and is not compared (open case O-neighbour). Candidates in ascending flat index
  ix * ny + iy; a candidate 8-adjacent (Chebyshev distance 1) to one already kept is dropped (O-adjacent). Of those kept,
  the two highest e_c, ties to the lower flat index (O-tie). Object 0 of a component is its highest peak (O-order).
- One peak, or none kept: one object, A = sum e_c over the component, x = sum e_c x_c / A, likewise y.
- Two peaks: 30 iterations of sharing, no early stop, from c_k = centre of peak cell k and A_k = its value. Each iteration:
  f_kc = A_k g_c(c_k) / sum_j A_j g_c(c_j), then A_k = sum_c f_kc e_c, c_k = sum_c f_kc e_c x_c / A_k, sums over the
  component. The fractions kept are those of the 30th iteration, the ones that gave the final A_k and c_k (O-last), so
  sum_k A_k = sum_c e_c holds to rounding. A zero or non-finite denominator, or an A_k of zero, makes the component a
  recorded sharing failure with no objects (O-denominator); it is not expected on this fixture. Its cells stay in the event
  sum with fractions summing to 0, and the product says so per component.
- Sharing fractions: kept per object; 1 for one-peak objects.
- Uncertainty, one peak: sigma_A^2 = sum_c v_c over the component, v_c = q max(e_c, 0) + sigma_n^2;
  sigma_x^2 = sum_c (x_c - x)^2 V_c / A^2 over the component and its 8-connected ring, dead and absent cells left out, with
  V_c the variance of e 1(e >= T_c) for e Gaussian of mean mu_c = A g_c(x, y) and variance s_c^2 = q mu_c + sigma_n^2.
  No x-y covariance is formed: section 7.1 defines none (O-covariance).
- Uncertainty, two peaks: the Fisher matrix on the component's cells, theta = (A_1, A_2, x_1, y_1, x_2, y_2),
  I_ij = sum_c (d mu_c/d theta_i)(d mu_c/d theta_j) / v_c, mu_c = sum_k A_k g_c(c_k), v_c = q mu_c + sigma_n^2, at the
  estimate; sigma_j^2 = (I^-1)_jj. I is singular when its Cholesky factorisation fails (O-singular). As the reference clusterer
  of job 7479146 does (coordinator's ruling, fix round 1): if I is singular, or any variance of either object is non-positive,
  or the inverse has a non-finite entry, neither object is kept; the component records the status (singular-fisher or
  non-positive-variance) for both, and its cells stay in the event sum with sharing fractions summing to 0.
- Event sum: S = sum of e_c over all kept components (= sum of A over the objects), sigma^2 = q S + n sigma_n^2, n its cells.
- Saturation: a clipped cell enters every step with its clipped value (O-saturated); an object with a clipped member, and
  an event sum with a clipped cell, are flagged and their energy is marked a lower bound (section 9.2).

Which sum enters which gate (section 7.1, last row) is the scoring side's: this module returns every object and the event sum.

A calo-cluster-configuration/2 without a profile and a response model (D2 stage 3, a labelled input from another simulation,
whose grid section 4.2 does not describe) changes two steps and nothing else: a component with two kept peaks is not shared but
kept as one object of kind "unsplit", with A, x and y as for one peak and every member at fraction 1; and no uncertainty is
formed, for any object or for the event sum (status "no-response-model", every sigma None), because there is no q or sigma_n to
form it from. Components, peaks, candidates, sums and saturation are as above. With a /1 configuration nothing changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy
from scipy import linalg, ndimage, special

from .configuration import Configuration
from .profile import axis_profile, axis_profile_derivative

EIGHT = numpy.ones((3, 3), dtype=bool)
RING_ONLY = numpy.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=bool)
INV_SQRT_2PI = 0.3989422804014327


@dataclass
class ClusterObject:
    component: int
    kind: str                      # one-peak, two-peak; unsplit without a profile (configuration /2)
    peak_channel: int
    energy: float                  # A, clustered deposited energy, MeV
    x: float
    y: float
    sigma_energy: float | None
    sigma_x: float | None
    sigma_y: float | None
    uncertainty_status: str        # ok, singular-fisher, non-positive-variance; no-response-model (configuration /2)
    members: list                  # [(channel, fraction)], ascending channel
    saturated: bool
    energy_bound: str              # estimate, lower-bound


@dataclass
class Component:
    index: int
    channels: list                 # ascending flat index
    candidates: list               # peak candidates after the neighbour test, ascending flat index
    peaks: list                    # kept peaks, highest first
    failure: str | None = None


@dataclass
class EventResult:
    components: list = field(default_factory=list)
    objects: list = field(default_factory=list)
    input_sum: float = 0.0          # sum of e_c over every live cell
    clustered_sum: float = 0.0      # sum of e_c over the kept components = event sum S
    unclustered_sum: float = 0.0    # sum of e_c over live cells outside kept components
    unclustered_cells: int = 0
    event_sum_sigma: float | None = 0.0   # None without a response model (configuration /2)
    event_sum_cells: int = 0
    event_sum_saturated: bool = False


def _phi(u):
    return INV_SQRT_2PI * numpy.exp(-0.5 * u * u)


def one_peak_object(cells_ix, cells_iy, e, ring_ix, ring_iy, cfg: Configuration):
    """A one-peak object of a component: energy, position and the section 7.1 uncertainties."""
    a = float(e.sum())
    xc, yc = cells_ix + 0.5, cells_iy + 0.5
    x, y = float((e * xc).sum() / a), float((e * yc).sum() / a)
    sigma_a2 = float((cfg.quantum * numpy.maximum(e, 0.0) + cfg.noise_sigma ** 2).sum())
    all_ix, all_iy = numpy.concatenate([cells_ix, ring_ix]), numpy.concatenate([cells_iy, ring_iy])
    g = axis_profile(x, cfg.cells_x, cfg.shower_width)[all_ix] * axis_profile(y, cfg.cells_y, cfg.shower_width)[all_iy]
    mu = a * g
    s = numpy.sqrt(cfg.quantum * mu + cfg.noise_sigma ** 2)
    t = (cfg.cell_threshold - mu) / s
    upper, density = special.ndtr(-t), _phi(t)
    m1 = mu * upper + s * density
    m2 = (mu * mu + s * s) * upper + s * (mu + cfg.cell_threshold) * density
    v = numpy.maximum(m2 - m1 * m1, 0.0)
    sx2 = float(((all_ix + 0.5 - x) ** 2 * v).sum() / a ** 2)
    sy2 = float(((all_iy + 0.5 - y) ** 2 * v).sum() / a ** 2)
    return a, x, y, sigma_a2, sx2, sy2


def share_two_peaks(cells_ix, cells_iy, e, peaks_ix, peaks_iy, cfg: Configuration):
    """The 30-iteration sharing of section 7.1. Returns (A, cx, cy, f) with f of shape (2, cells), or None on a zero denominator."""
    cx = peaks_ix.astype(float) + 0.5
    cy = peaks_iy.astype(float) + 0.5
    amplitude = numpy.array(peak_values(e, cells_ix, cells_iy, peaks_ix, peaks_iy), dtype=float)
    xc, yc = cells_ix + 0.5, cells_iy + 0.5
    f = None
    for _ in range(cfg.sharing_iterations):
        g = numpy.stack([axis_profile(cx[k], cfg.cells_x, cfg.shower_width)[cells_ix] * axis_profile(cy[k], cfg.cells_y, cfg.shower_width)[cells_iy]
                         for k in range(2)])
        weighted = amplitude[:, None] * g
        denominator = weighted.sum(axis=0)
        if not numpy.all(numpy.isfinite(denominator)) or numpy.any(denominator <= 0.0):
            return None
        f = weighted / denominator
        amplitude = (f * e).sum(axis=1)
        if not numpy.all(amplitude > 0.0):
            return None
        cx = (f * e * xc).sum(axis=1) / amplitude
        cy = (f * e * yc).sum(axis=1) / amplitude
    return amplitude, cx, cy, f


def centroid_object(component: int, kind: str, peak: int, cells, cells_ix, cells_iy, e, sat) -> ClusterObject:
    """The whole component as one object with no uncertainty: no response model (and, for kind unsplit, no profile) is given.
    A = sum e_c, x = sum e_c x_c / A, likewise y, as section 7.1's one-peak rule; every member at fraction 1."""
    a = float(e.sum())
    x = float((e * (cells_ix + 0.5)).sum() / a)
    y = float((e * (cells_iy + 0.5)).sum() / a)
    return ClusterObject(component=component, kind=kind, peak_channel=peak, energy=a, x=x, y=y, sigma_energy=None, sigma_x=None,
                         sigma_y=None, uncertainty_status="no-response-model", members=[(int(c), 1.0) for c in cells],
                         saturated=bool(sat.any()), energy_bound="lower-bound" if sat.any() else "estimate")


def peak_values(e, cells_ix, cells_iy, peaks_ix, peaks_iy):
    """The value of each peak cell, looked up among the component's cells."""
    out = []
    for px, py in zip(peaks_ix, peaks_iy):
        where = numpy.flatnonzero((cells_ix == px) & (cells_iy == py))
        out.append(e[where[0]])
    return out


def fisher_uncertainty(cells_ix, cells_iy, amplitude, cx, cy, cfg: Configuration):
    """Section 7.1's two-peak Fisher matrix at the estimate. Returns (status, variances of theta) with theta = (A1, A2, x1, y1, x2, y2)."""
    columns_a, columns_pos = [], []
    for k in range(2):
        gx = axis_profile(cx[k], cfg.cells_x, cfg.shower_width)[cells_ix]
        gy = axis_profile(cy[k], cfg.cells_y, cfg.shower_width)[cells_iy]
        dgx = axis_profile_derivative(cx[k], cfg.cells_x, cfg.shower_width)[cells_ix]
        dgy = axis_profile_derivative(cy[k], cfg.cells_y, cfg.shower_width)[cells_iy]
        columns_a.append(gx * gy)
        columns_pos.extend([amplitude[k] * dgx * gy, amplitude[k] * gx * dgy])
    jacobian = numpy.stack(columns_a + columns_pos, axis=1)
    mu = jacobian[:, 0] * amplitude[0] + jacobian[:, 1] * amplitude[1]
    v = cfg.quantum * mu + cfg.noise_sigma ** 2
    information = jacobian.T @ (jacobian / v[:, None])
    try:
        factor = linalg.cho_factor(information, lower=True, check_finite=True)
        covariance = linalg.cho_solve(factor, numpy.eye(6), check_finite=True)
    except (linalg.LinAlgError, ValueError):
        return "singular-fisher", None
    variances = numpy.diag(covariance).copy()
    if not numpy.all(numpy.isfinite(covariance)) or numpy.any(variances <= 0.0):
        return "non-positive-variance", None
    return "ok", variances


def largest_neighbour(energy, valued):
    """Per cell, the largest e_c among its 8 neighbours that have a value; -inf where none has one."""
    neighbour = numpy.where(valued, energy, -numpy.inf)
    return ndimage.maximum_filter(neighbour, footprint=RING_ONLY, mode="constant", cval=-numpy.inf)


def peak_candidates(energy, largest, comp_mask, cfg: Configuration):
    """Flat indices of the peak candidates of one component, ascending."""
    with numpy.errstate(invalid="ignore"):
        is_peak = comp_mask & (energy >= cfg.seed_threshold) & (energy >= largest)
    return [int(i) for i in numpy.flatnonzero(is_peak)]


def keep_peaks(candidates, energy_flat, ny: int, keep: int):
    """Drop a candidate 8-adjacent to one already kept, in ascending flat index; then the `keep` highest, ties to lower index."""
    kept = []
    for c in candidates:
        cx, cy = divmod(c, ny)
        if any(max(abs(cx - k // ny), abs(cy - k % ny)) <= 1 for k in kept):
            continue
        kept.append(c)
    return sorted(kept, key=lambda c: (-energy_flat[c], c))[:keep]


def cluster_event(energy: numpy.ndarray, live: numpy.ndarray, saturated: numpy.ndarray, cfg: Configuration) -> EventResult:
    """Section 7.1 on one event. energy: (nx, ny) e_c in MeV, NaN where there is no value."""
    if energy.shape != (cfg.cells_x, cfg.cells_y):
        raise ValueError(f"grid {energy.shape} is not the configuration's ({cfg.cells_x}, {cfg.cells_y})")
    valued = live & numpy.isfinite(energy)
    flat_e = numpy.where(valued, energy, 0.0).ravel()
    with numpy.errstate(invalid="ignore"):
        above = valued & (energy >= cfg.cell_threshold)
    labels, count = ndimage.label(above, structure=EIGHT)
    result = EventResult(input_sum=float(flat_e[valued.ravel()].sum()))
    kept_mask = numpy.zeros_like(above)
    largest = largest_neighbour(energy, valued) if count else None
    flat_labels = labels.ravel()
    order = numpy.argsort(flat_labels, kind="stable")
    bounds = numpy.searchsorted(flat_labels[order], numpy.arange(1, count + 2))
    for label in range(1, count + 1):
        cells = order[bounds[label - 1]:bounds[label]]       # ascending flat index (stable sort)
        if not numpy.any(flat_e[cells] >= cfg.seed_threshold):
            continue
        comp_mask = labels == label
        kept_mask |= comp_mask
        index = len(result.components)
        candidates = peak_candidates(energy, largest, comp_mask, cfg)
        peaks = keep_peaks(candidates, flat_e, cfg.cells_y, cfg.peaks_kept)
        component = Component(index=index, channels=[int(c) for c in cells], candidates=candidates, peaks=peaks)
        result.components.append(component)
        cells_ix, cells_iy = numpy.divmod(cells, cfg.cells_y)
        e = flat_e[cells]
        sat = saturated.ravel()[cells]
        if not cfg.response_model:
            # configuration /2 with no profile and no response model: one object per kept component, never split
            peak = peaks[0] if peaks else int(cells[numpy.argmax(e)])
            result.objects.append(centroid_object(index, "unsplit" if len(peaks) >= 2 else "one-peak", peak, cells, cells_ix,
                                                  cells_iy, e, sat))
            continue
        if len(peaks) < 2:
            ring = ndimage.binary_dilation(comp_mask, structure=EIGHT) & ~comp_mask & valued
            ring_ix, ring_iy = numpy.nonzero(ring)
            a, x, y, sa2, sx2, sy2 = one_peak_object(cells_ix, cells_iy, e, ring_ix, ring_iy, cfg)
            peak = peaks[0] if peaks else int(cells[numpy.argmax(e)])
            variances = (sa2, sx2, sy2)
            ok = all(numpy.isfinite(v) and v > 0 for v in variances)
            result.objects.append(ClusterObject(
                component=index, kind="one-peak", peak_channel=peak, energy=a, x=x, y=y,
                sigma_energy=float(numpy.sqrt(sa2)) if ok else None, sigma_x=float(numpy.sqrt(sx2)) if ok else None,
                sigma_y=float(numpy.sqrt(sy2)) if ok else None, uncertainty_status="ok" if ok else "non-positive-variance",
                members=[(int(c), 1.0) for c in cells], saturated=bool(sat.any()),
                energy_bound="lower-bound" if sat.any() else "estimate"))
            continue
        peaks_ix, peaks_iy = numpy.divmod(numpy.array(peaks), cfg.cells_y)
        shared = share_two_peaks(cells_ix, cells_iy, e, peaks_ix, peaks_iy, cfg)
        if shared is None:
            component.failure = "sharing-undefined"
            continue
        amplitude, cx, cy, f = shared
        status, variances = fisher_uncertainty(cells_ix, cells_iy, amplitude, cx, cy, cfg)
        if status != "ok":
            component.failure = status          # neither object is kept (O-singular, as the reference clusterer)
            continue
        for k in range(2):
            members = [(int(c), float(f[k, i])) for i, c in enumerate(cells)]
            flagged = bool((sat & (f[k] > 0.0)).any())
            sigmas = tuple(float(numpy.sqrt(v)) for v in (variances[k], variances[2 + 2 * k], variances[3 + 2 * k]))
            result.objects.append(ClusterObject(
                component=index, kind="two-peak", peak_channel=int(peaks[k]), energy=float(amplitude[k]), x=float(cx[k]),
                y=float(cy[k]), sigma_energy=sigmas[0], sigma_x=sigmas[1], sigma_y=sigmas[2], uncertainty_status="ok",
                members=members, saturated=flagged, energy_bound="lower-bound" if flagged else "estimate"))
    kept_flat = kept_mask.ravel()
    result.clustered_sum = float(flat_e[kept_flat].sum())
    outside = valued.ravel() & ~kept_flat
    result.unclustered_sum = float(flat_e[outside].sum())
    result.unclustered_cells = int(outside.sum())
    result.event_sum_cells = int(kept_flat.sum())
    if not cfg.response_model:
        result.event_sum_sigma = None
    else:
        result.event_sum_sigma = float(numpy.sqrt(cfg.quantum * result.clustered_sum + result.event_sum_cells * cfg.noise_sigma ** 2)) \
            if result.event_sum_cells else 0.0
    result.event_sum_saturated = bool((saturated.ravel() & kept_flat).any())
    return result
